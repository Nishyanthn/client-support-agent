import os
from pathlib import Path
import faiss
import numpy as np
import asyncio

# Semantic Kernel imports
from semantic_kernel import Kernel

# CORRECTED: Use the proper import path
from semantic_kernel.connectors.ai.google.google_ai import (
    GoogleAIChatCompletion,
    GoogleAITextEmbedding,
)
print("✅ Imported Google AI connectors successfully.")

from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.memory.semantic_text_memory import SemanticTextMemory
# from semantic_kernel.connectors.memory.volatile_memory_store import VolatileMemoryStore
from semantic_kernel.exceptions import ServiceInitializationError

# Import configurations and native functions
from app.config import GOOGLE_API_KEY, MONGO_DB_URI
import app.native_functions as native_functions

# --- Configuration ---
INDEX_DIR = "faiss_index"
INDEX_PATH = os.path.join(INDEX_DIR, "main_index.faiss")
INDEX_TEXT_PATH = os.path.join(INDEX_DIR, "main_index.txt")
KNOWLEDGE_FILE = "data/knowledge_base.txt"
EMBEDDING_MODEL_ID = "models/text-embedding-004"
CHAT_MODEL_ID = "models/gemini-2.5-flash"

# Global variable for our FAISS retriever and embedding service
faiss_retriever = None
embedding_service = None

# --- RAG (FAISS) Setup ---

class FaissRetriever:
    """A custom retriever class to build, save, load, and search a FAISS index."""

    def __init__(self, index_path, text_path, knowledge_file, embedding_svc):
        self.index_path = index_path
        self.text_path = text_path
        self.knowledge_file = knowledge_file
        self.embedding_service = embedding_svc
        self.index = None
        self.chunks_with_content = []

        # Ensure directory exists
        os.makedirs(os.path.dirname(index_path), exist_ok=True)

        # Don't build/load in __init__, just initialize
        self._initialized = False

    async def initialize(self):
        """Async initialization method to be called after construction."""
        if self._initialized:
            return
            
        if os.path.exists(self.index_path) and os.path.exists(self.text_path):
            print(f"Loading existing FAISS index from {self.index_path}")
            await self.load()
        else:
            print(f"No index found. Building new FAISS index from {self.knowledge_file}...")
            await self.build()
        
        self._initialized = True

    async def build(self):
        """Builds the FAISS index from the knowledge file."""
        if not self.embedding_service:
            print("Error: Embedding service not available for building index.")
            return
        try:
            with open(self.knowledge_file, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = content.split("\n\n")
            self.chunks_with_content = [chunk.strip() for chunk in chunks if chunk.strip()]

            if not self.chunks_with_content:
                print("Warning: No text chunks found in knowledge file.")
                return

            print(f"Generating {len(self.chunks_with_content)} embeddings...")

            # Generate embeddings asynchronously
            embeddings = await self.embedding_service.generate_embeddings(self.chunks_with_content)

            embeddings_np = np.array(embeddings, dtype="float32")
            d = embeddings_np.shape[1]
            print(f"Embedding dimension: {d}")

            self.index = faiss.IndexFlatL2(d)
            self.index.add(embeddings_np)

            print(f"FAISS index built with {self.index.ntotal} vectors.")
            self.save()

        except Exception as e:
            print(f"❌ Error building FAISS index: {e}")
            import traceback
            traceback.print_exc()

    def save(self):
        """Saves the index and text chunks to disk."""
        if self.index is None:
            print("Error: Index not built, cannot save.")
            return
        print(f"Saving index to {self.index_path}...")
        faiss.write_index(self.index, self.index_path)
        with open(self.text_path, "w", encoding="utf-8") as f:
            separator = "\n<---CHUNK_SEPARATOR--->\n"
            f.write(separator.join(self.chunks_with_content))
        print("Index and text chunks saved.")

    async def load(self):
        """Loads the index and text chunks from disk."""
        try:
            self.index = faiss.read_index(self.index_path)

            with open(self.text_path, "r", encoding="utf-8") as f:
                content = f.read()

            separator = "\n<---CHUNK_SEPARATOR--->\n"
            self.chunks_with_content = [chunk.strip() for chunk in content.split(separator) if chunk.strip()]

            if not self.chunks_with_content or (self.index and len(self.chunks_with_content) != self.index.ntotal):
                raise ValueError("Mismatch between index size and text chunks count or index not loaded.")

            print(f"FAISS index ({getattr(self.index, 'ntotal', 'N/A')} vectors) and {len(self.chunks_with_content)} text chunks loaded.")
        except Exception as e:
            print(f"Error loading FAISS index or text chunks: {e}")
            print("Will attempt to rebuild.")
            await self.build()

    async def search(self, query: str, k: int = 2) -> str:
        """Searches the index for the top k similar chunks."""
        if not self._initialized:
            await self.initialize()
            
        if self.index is None or self.embedding_service is None:
            return "Error: FAISS index or embedding service is not initialized."

        print(f"RAG: Searching for query: '{query}'")
        try:
           # Use generate_embeddings (plural) by passing the query in a list
            embedding_list = await self.embedding_service.generate_embeddings([query])
            query_embedding = embedding_list[0] # Get the first (and only) embedding from the list
            query_np = np.array([query_embedding], dtype="float32")

            distances, indices = self.index.search(query_np, k)

            results = []
            for i in indices[0]:
                if 0 <= i < len(self.chunks_with_content):
                    results.append(self.chunks_with_content[i])
                else:
                    print(f"Warning: Index {i} out of bounds for text chunks.")

            if not results:
                print("RAG: No relevant documents found.")
                return "No relevant information found in the knowledge base."

            context = "\n\n".join(results)
            print(f"RAG: Found context:\n---\n{context}\n---")
            return context
        except Exception as e:
            print(f"❌ Error during FAISS search: {e}")
            import traceback
            traceback.print_exc()
            return "Error occurred during knowledge base search."

# --- RAG Kernel Function (Agent Tool) ---
@kernel_function(
    description="Retrieves relevant information from the company's knowledge base or help documents when a user asks a 'how-to' or informational question.",
    name="retrieve_knowledge"
)
async def retrieve_knowledge(query: str) -> str:
    """
    This function is called by the agent to get context for a user's question.
    It uses the FaissRetriever instance to perform the search.
    """
    if faiss_retriever:
        return await faiss_retriever.search(query)
    return "Error: Knowledge base retriever is not initialized."

# --- Agent Setup Function ---

async def load_system_prompt() -> str:
    """Loads the system prompt from the markdown file."""
    try:
        # Get the directory where this script is located
        current_dir = Path(__file__).parent
        prompt_file = current_dir / "system_prompt.md"
        
        # Read the markdown file
        with open(prompt_file, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
        
        print(f"✅ System prompt loaded from {prompt_file}")
        return system_prompt
    
    except FileNotFoundError:
        print(f"❌ Error: system_prompt.md not found in {current_dir}")
        raise
    except Exception as e:
        print(f"❌ Error loading system prompt: {e}")
        raise


async def setup_agent() -> ChatCompletionAgent:
    """Initializes and returns the main ChatCompletionAgent."""
    global faiss_retriever, embedding_service

    print("🚀 Setting up Semantic Kernel and Agent...")
    kernel = Kernel()

    print("Initializing Google AI services...")
    print(f" - Chat Model: {CHAT_MODEL_ID.split('/')[-1]}")
    print(f" - Embedding Model: {EMBEDDING_MODEL_ID.split('/')[-1]}")
    
    try:
        # Initialize services with correct parameter names
        # Set service_id during initialization to reference it later
        embedding_service = GoogleAITextEmbedding(
            embedding_model_id=EMBEDDING_MODEL_ID,
            api_key=GOOGLE_API_KEY,
            service_id="embedding_service"
        )
        
        chat_service = GoogleAIChatCompletion(
            gemini_model_id=CHAT_MODEL_ID,
            api_key=GOOGLE_API_KEY,
            service_id="chat_service"
        )
        
        # Register services with the kernel
        kernel.add_service(embedding_service)
        kernel.add_service(chat_service)
        print("✅ Gemini services added.")
        
    except ServiceInitializationError as e:
        print(f"❌ Error adding Gemini services: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error adding Gemini services: {e}")
        import traceback
        traceback.print_exc()
        raise

    print("Initializing FAISS Retriever...")
    try:
        if embedding_service is None:
            raise ValueError("Embedding service failed to initialize, cannot create FaissRetriever.")
        
        faiss_retriever = FaissRetriever(
            INDEX_PATH,
            INDEX_TEXT_PATH,
            KNOWLEDGE_FILE,
            embedding_service
        )
        
        # Initialize the retriever asynchronously
        await faiss_retriever.initialize()
        print("✅ FAISS Retriever initialized.")
    except Exception as e:
        print(f"❌ Error initializing FAISS Retriever: {e}")
        raise

    print("Loading system prompt from markdown file...")
    try:
        system_prompt = await load_system_prompt()
        print("✅ System prompt loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading system prompt: {e}")
        raise

    print("Creating ChatCompletionAgent...")
    try:
        # Use the chat_service instance directly
        agent = ChatCompletionAgent(
            kernel=kernel,
            service=chat_service,
            instructions=system_prompt,
            name="iNextLabsSupportAgent"
        )
        print("✅ ChatCompletionAgent created.")
    except Exception as e:
        print(f"❌ Error creating ChatCompletionAgent: {e}")
        raise

    print("Registering functions (tools) with the kernel...")
    try:
        # Import KernelPlugin for creating plugins
        from semantic_kernel.functions import KernelPlugin
        
        # Create a plugin from the native_functions object
        actions_plugin = KernelPlugin.from_object(
            plugin_instance=native_functions,
            plugin_name="Actions"
        )
        kernel.add_plugin(actions_plugin)
        
        # Add the RAG function directly to the kernel
        kernel.add_function(
            plugin_name="RAG",
            function=retrieve_knowledge
        )
        
        # Add TimePlugin
        from semantic_kernel.core_plugins import TimePlugin
        time_plugin = KernelPlugin.from_object(
            plugin_instance=TimePlugin(),
            plugin_name="time"
        )
        kernel.add_plugin(time_plugin)

        print("✅ Native functions, RAG function, and Time plugin registered.")
    except Exception as e:
        print(f"❌ Error registering functions/plugins: {e}")
        import traceback
        traceback.print_exc()
        raise

    print("✅ Agent setup complete.")
    return agent