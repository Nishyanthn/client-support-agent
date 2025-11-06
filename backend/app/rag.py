"""
Pure RAG Implementation with File Upload
Two Endpoints: /upload and /chat

Run: uvicorn vanilla_rag:app --reload --port 8001
Test:
  1. POST /upload (upload .txt file)
  2. POST /chat (ask questions)
"""

import os
import numpy as np
import faiss
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# ============================================================================
# CONFIGURATION
# ============================================================================

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBLRWTIv3yM_bgRW7lXFEQsiPAh7xbGz_4")

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)

# ============================================================================
# GLOBAL STATE
# ============================================================================

faiss_index = None
text_chunks = None
is_ready = False

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def chunk_text(content: str) -> list:
    """
    Split text into chunks by paragraphs (double newline).
    """
    print("📄 Chunking text...")
    normalized_content = content.replace('\r\n', '\n')
    chunks = normalized_content.split('\n\n')
    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    print(f"✅ Created {len(chunks)} chunks")
    return chunks


def generate_embeddings(texts: list) -> np.ndarray:
    """
    Generate embeddings for text chunks using Gemini.
    Returns: numpy array of shape (n_chunks, 768)
    """
    print(f"🔢 Generating embeddings for {len(texts)} chunks...")
    embeddings = []
    
    for i, text in enumerate(texts):
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        embeddings.append(result['embedding'])
        
        if (i + 1) % 10 == 0:
            print(f"   Progress: {i + 1}/{len(texts)}")
    
    embeddings_array = np.array(embeddings, dtype='float32')
    print(f"✅ Embeddings generated: {embeddings_array.shape}")
    return embeddings_array


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """
    Build FAISS index for similarity search.
    """
    print("🏗️  Building FAISS index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    print(f"✅ FAISS index built with {index.ntotal} vectors")
    return index


def search_faiss(query: str, k: int = 3) -> list:
    """
    Search FAISS index for similar chunks.
    Returns: list of retrieved chunks with metadata
    """
    if not is_ready:
        return []
    
    print(f"\n🔍 Searching for: '{query}'")
    
    # Generate query embedding
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )
    query_embedding = np.array([result['embedding']], dtype='float32')
    
    # Search FAISS
    distances, indices = faiss_index.search(query_embedding, k)
    
    # Retrieve chunks
    retrieved = []
    for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]), 1):
        if 0 <= idx < len(text_chunks):
            retrieved.append({
                "rank": rank,
                "text": text_chunks[idx],
                "distance": float(dist)
            })
            print(f"   Rank {rank}: distance={dist:.4f}")
    
    return retrieved


def generate_answer(query: str, context_chunks: list) -> str:
    """
    Generate answer using LLM with retrieved context.
    """
    print("✨ Generating answer with LLM...")
    
    # Combine context
    context = "\n\n".join([chunk["text"] for chunk in context_chunks])
    
    # Create prompt
    prompt = f"""You are an expert AI assistant with deep knowledge and analytical capabilities. Your role is to provide comprehensive, accurate, and well-structured answers based on the given context.

INSTRUCTIONS:
1. Analyze the provided context carefully and thoroughly
2. Answer the question with detailed explanations and relevant examples where applicable
3. Structure your response with clear paragraphs for better readability
4. If the context contains multiple relevant points, address them systematically
5. Use specific information from the context to support your answer
6. If you reference information, you can mention which source it comes from (e.g., "According to Source 1...")
7. Be informative but remain focused on answering the specific question asked
8. If the context doesn't fully answer the question, provide the most relevant information available and acknowledge any limitations

CONTEXT INFORMATION:
{context}

USER QUESTION:
{query}

DETAILED ANSWER:
Please provide a comprehensive and well-explained response based on the context above."""
    
    # Generate response
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    
    print(f"✅ Answer generated ({len(response.text)} chars)")
    return response.text


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="RAG API",
    description="Upload knowledge base and chat with it"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatRequest(BaseModel):
    question: str
    top_k: int = 3

class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Health check"""
    return {
        "status": "running",
        "ready": is_ready,
        "chunks_loaded": len(text_chunks) if text_chunks else 0,
        "endpoints": {
            "upload": "POST /upload (upload .txt file)",
            "chat": "POST /chat (ask questions)"
        }
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    ENDPOINT 1: Upload knowledge base file
    
    - Accepts: .txt files
    - Process: Reads file → Chunks → Embeddings → FAISS index
    - Returns: Success message with chunk count
    """
    global faiss_index, text_chunks, is_ready
    
    print("\n" + "="*70)
    print(f"📁 UPLOADING FILE: {file.filename}")
    print("="*70)
    
    # Validate file type
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="Only .txt files are supported"
        )
    
    try:
        # Read file
        content = await file.read()
        content = content.decode('utf-8')
        print(f"📖 File size: {len(content)} characters")
        
        if len(content) < 10:
            raise HTTPException(
                status_code=400,
                detail="File content is too short"
            )
        
        # Step 1: Chunk text
        text_chunks = chunk_text(content)
        
        # Step 2: Generate embeddings
        embeddings = generate_embeddings(text_chunks)
        
        # Step 3: Build FAISS index
        faiss_index = build_faiss_index(embeddings)
        
        is_ready = True
        
        print("="*70)
        print("✅ FILE PROCESSED SUCCESSFULLY")
        print("="*70)
        print(f"📊 Chunks: {len(text_chunks)}")
        print(f"📊 Index size: {faiss_index.ntotal}")
        print("="*70 + "\n")
        
        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded and indexed successfully",
            "chunks_created": len(text_chunks),
            "ready_for_chat": True
        }
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File encoding error. Please ensure file is UTF-8 encoded."
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    ENDPOINT 2: Chat with the knowledge base
    
    - Process: Question → Search FAISS → Retrieve context → LLM → Answer
    - Returns: Answer with source chunks
    """
    print("\n" + "="*70)
    print(f"💬 CHAT REQUEST: {request.question}")
    print("="*70)
    
    # Check if system is ready
    if not is_ready:
        raise HTTPException(
            status_code=400,
            detail="Please upload a knowledge base file first using /upload endpoint"
        )
    
    if not request.question or len(request.question.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Question is too short"
        )
    
    try:
        # Step 1: Search for similar chunks
        retrieved_chunks = search_faiss(request.question, k=request.top_k)
        
        if not retrieved_chunks:
            return ChatResponse(
                question=request.question,
                answer="I couldn't find relevant information in the knowledge base.",
                sources=[]
            )
        
        # Step 2: Generate answer
        answer = generate_answer(request.question, retrieved_chunks)
        
        # Step 3: Format sources
        sources = [
            {
                "rank": chunk["rank"],
                "text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                "relevance_score": round(1 / (1 + chunk["distance"]), 3)
            }
            for chunk in retrieved_chunks
        ]
        
        print("="*70)
        print("✅ CHAT COMPLETED")
        print("="*70 + "\n")
        
        return ChatResponse(
            question=request.question,
            answer=answer,
            sources=sources
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("""
╔══════════════════════════════════════════════════════════════╗
║                      RAG API SERVER                          ║
╚══════════════════════════════════════════════════════════════╝

📍 Server: http://localhost:8001
📖 Docs: http://localhost:8001/docs

🔹 STEP 1: POST /upload - Upload your .txt knowledge base
🔹 STEP 2: POST /chat - Ask questions

""")
    uvicorn.run(app, host="0.0.0.0", port=8001)