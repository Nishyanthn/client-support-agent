import os
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
CHAT_MODEL_ID = "gemini-1.5-flash-latest"

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

        if os.path.exists(self.index_path) and os.path.exists(self.text_path):
            print(f"Loading existing FAISS index from {self.index_path}")
            self.load()
        else:
            print(f"No index found. Building new FAISS index from {self.knowledge_file}...")
            try:
                loop = asyncio.get_running_loop()
                loop.run_until_complete(self.build())
            except RuntimeError:
                asyncio.run(self.build())

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

    def load(self):
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
            try:
                loop = asyncio.get_running_loop()
                loop.run_until_complete(self.build())
            except RuntimeError:
                asyncio.run(self.build())

    async def search(self, query: str, k: int = 2) -> str:
        """Searches the index for the top k similar chunks."""
        if self.index is None or self.embedding_service is None:
            return "Error: FAISS index or embedding service is not initialized."

        print(f"RAG: Searching for query: '{query}'")
        try:
            query_embedding = await self.embedding_service.generate_embedding(query)
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

def setup_agent() -> ChatCompletionAgent:
    """Initializes and returns the main ChatCompletionAgent."""
    global faiss_retriever, embedding_service

    print("🚀 Setting up Semantic Kernel and Agent...")
    kernel = Kernel()

    print("Initializing Google AI services...")
    print(f" - Chat Model: {CHAT_MODEL_ID.split('/')[-1]}")
    print(f" - Embedding Model: {EMBEDDING_MODEL_ID.split('/')[-1]}")
    
    try:
        # Initialize services with proper parameters
        embedding_service = GoogleAITextEmbedding(
            ai_model_id=EMBEDDING_MODEL_ID,
            api_key=GOOGLE_API_KEY
        )
        
        chat_service = GoogleAIChatCompletion(
            ai_model_id=CHAT_MODEL_ID,
            api_key=GOOGLE_API_KEY
        )
        
        # Register services with the kernel
        kernel.add_service(embedding_service)
        kernel.add_service(chat_service, service_id=CHAT_MODEL_ID)
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
        print("✅ FAISS Retriever initialized.")
    except Exception as e:
        print(f"❌ Error initializing FAISS Retriever: {e}")
        raise

    print("Defining system prompt...")
    system_prompt = f"""
    You are a friendly and professional client support agent for our SaaS company.
    Your goal is to help users by answering their questions and performing specific tasks.

    **TOOL USAGE RULES:**

    1.  **For informational questions** (e.g., "how do I...", "what is...", "explain...", "tell me about..."), you MUST FIRST use the `retrieve_knowledge` tool to search the company knowledge base.
        * Base your answer *strictly* on the information returned by the `retrieve_knowledge` tool.
        * If the tool returns "No relevant information found...", inform the user politely that you couldn't find the answer in the knowledge base. Do not make up answers.

    2.  **For specific action requests**, use the appropriate action tool:
        * To check a support ticket's status (e.g., "what's the status of ticket...", "check my ticket..."), use the `check_ticket_status` tool. You MUST have the `ticket_id` to use this tool. If the user doesn't provide it, ASK them for the ticket ID first.
        * To request a password reset (e.g., "reset my password", "forgot password"), use the `request_password_reset` tool. You MUST have the user's `email` address. If the user doesn't provide it, ASK them for their email address first.

    3.  **For simple greetings, farewells, or chit-chat** (e.g., "hello", "thank you", "how are you?"), you can respond directly without using any tools.

    **RESPONSE GUIDELINES:**
    * Be polite, concise, and helpful.
    * Do not mention the names of the tools you are using (e.g., don't say "I will use the retrieve_knowledge tool"). Just perform the action and give the answer.
    * If you need information from the user (like a ticket ID or email), ask clearly.
    * Today's date is {{{{time.today}}}} and the current time is {{{{time.now}}}}. You can use this if needed, for example when discussing support hours or recent events.
    """

    print("Creating ChatCompletionAgent...")
    try:
        agent = ChatCompletionAgent(
            kernel=kernel,
            service_id=CHAT_MODEL_ID,
            instructions=system_prompt,
            name="SupportAgent"
        )
        print("✅ ChatCompletionAgent created.")
    except Exception as e:
        print(f"❌ Error creating ChatCompletionAgent: {e}")
        raise

    print("Registering functions (tools) with the kernel...")
    try:
        kernel.add_plugin_from_object(native_functions, plugin_name="Actions")
        kernel.add_function_to_kernel(retrieve_knowledge, plugin_name="RAG")
        
        from semantic_kernel.core_plugins import TimePlugin
        kernel.add_plugin_from_object(TimePlugin(), plugin_name="time")

        print("✅ Native functions, RAG function, and Time plugin registered.")
    except Exception as e:
        print(f"❌ Error registering functions/plugins: {e}")
        raise

    print("✅ Agent setup complete.")
    return agent