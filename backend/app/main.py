import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid

# Semantic Kernel imports for history management
from semantic_kernel.contents import ChatHistory, ChatMessageContent, AuthorRole
from semantic_kernel.agents import ChatCompletionAgent

# Import the agent setup function
from app.agent_setup import setup_agent

# Import conversation logger
from app.conversation_logger import ConversationLogger

# --- Lifespan Function for Async Startup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code here runs BEFORE the application starts accepting requests
    print("🚀 Application Startup: Initializing Agent...")
    try:
        # Run the async setup_agent function and wait for it to complete
        agent_instance: ChatCompletionAgent = await setup_agent()
        # Store the initialized agent in the application state
        app.state.agent = agent_instance
        print("✅ Agent Initialized Successfully and stored in app state.")
    except Exception as e:
        print(f"❌ Critical Error: Failed to initialize agent during startup: {e}")
        app.state.agent = None
        # Depending on severity, you might want to raise the exception
        # raise e

    yield # This signals that the startup is complete

    # Code here runs AFTER the application is shutting down (optional cleanup)
    print("👋 Application Shutdown.")
    app.state.agent = None

# --- App Initialization with Lifespan ---

app = FastAPI(
    title="Client Support Knowledge Agent",
    description="A RAG + Function Calling agent using Semantic Kernel and Gemini",
    lifespan=lifespan
)

# --- CORS Middleware ---
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for API ---

class HistoryMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[HistoryMessage]] = []
    session_id: Optional[str] = None  # NEW: Optional session tracking
    user_id: Optional[str] = None      # NEW: Optional user tracking

class ChatResponse(BaseModel):
    response: str
    history: List[HistoryMessage]
    session_id: Optional[str] = None   # NEW: Return session ID

class ConversationStatsResponse(BaseModel):
    total_conversations: int
    avg_response_length: Optional[float] = None
    avg_message_length: Optional[float] = None

# --- API Endpoints ---

@app.get("/")
def read_root(request: Request):
    """Basic health check endpoint."""
    agent_status = request.app.state.agent is not None
    return {
        "message": "Support Agent API is running.",
        "status": "online",
        "agent_initialized": agent_status
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: Request, payload: ChatRequest):
    """
    Main chat endpoint.
    Receives user message and history, invokes the agent, returns the response.
    Now also logs conversations to MongoDB.
    """
    # Get the agent instance from the application state
    agent: Optional[ChatCompletionAgent] = request.app.state.agent

    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Agent failed to initialize. Cannot process chat requests."
        )

    # Generate or use provided session_id
    session_id = payload.session_id or str(uuid.uuid4())

    print(f"\n{'='*70}")
    print(f"📨 New Chat Request")
    print(f"{'='*70}")
    print(f"Session ID: {session_id}")
    print(f"User Message: {payload.message}")
    print(f"History Length: {len(payload.history)} messages")

    try:
        # 1. Rebuild ChatHistory
        chat_history = ChatHistory()
        
        # Add history messages
        if payload.history:
            for msg in payload.history:
                role = AuthorRole.USER if msg.role.lower() == 'user' else AuthorRole.ASSISTANT
                chat_history.add_message(ChatMessageContent(role=role, content=msg.content))

        # 2. Add current user message
        chat_history.add_user_message(payload.message)

        # 3. Invoke agent - pass the chat_history directly
        full_response = ""
        print(f"\n🤖 Agent Processing...")
        
        async for response in agent.invoke(chat_history):
            # Handle different response types
            if hasattr(response, 'content'):
                chunk = str(response.content)
                print(f"   Streaming chunk: {chunk[:100]}{'...' if len(chunk) > 100 else ''}")
                full_response += chunk
            elif isinstance(response, str):
                print(f"   Streaming chunk (str): {response[:100]}{'...' if len(response) > 100 else ''}")
                full_response += response
            else:
                # Try to convert to string
                chunk = str(response)
                print(f"   Streaming chunk (converted): {chunk[:100]}{'...' if len(chunk) > 100 else ''}")
                full_response += chunk

        print(f"\n✅ Agent Response Complete")
        print(f"Response Length: {len(full_response)} characters")
        print(f"Response Preview: {full_response[:200]}{'...' if len(full_response) > 200 else ''}")

        # 4. Add agent's response to history
        chat_history.add_assistant_message(full_response)

        # 5. Format history for response
        response_history = []
        for msg in chat_history.messages:
            if msg.role != AuthorRole.SYSTEM:
                response_history.append(
                    HistoryMessage(
                        role=msg.role.value,
                        content=str(msg.content)
                    )
                )

        # 6. LOG CONVERSATION TO MONGODB
        print(f"\n💾 Logging conversation to MongoDB...")
        metadata = {
            "session_id": session_id,
            "ip_address": request.client.host if request.client else "unknown",
        }
        if payload.user_id:
            metadata["user_id"] = payload.user_id
        
        # Convert response_history to dict format for MongoDB
        history_dict = [{"role": msg.role, "content": msg.content} for msg in response_history]
        
        log_id = ConversationLogger.log_conversation(
            user_message=payload.message,
            agent_response=full_response,
            conversation_history=history_dict,
            metadata=metadata
        )
        
        if log_id:
            print(f"✅ Conversation logged with ID: {log_id}")
        else:
            print(f"⚠️ Failed to log conversation (non-critical)")

        print(f"{'='*70}\n")
        return ChatResponse(
            response=full_response, 
            history=response_history,
            session_id=session_id
        )

    except Exception as e:
        print(f"\n❌ Error during chat processing: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/health")
def health_check(request: Request):
    """Detailed health check endpoint."""
    agent_status = request.app.state.agent is not None
    return {
        "status": "healthy",
        "agent_initialized": agent_status,
        "services": {
            "fastapi": "running",
            "semantic_kernel": agent_status,
            "rag_index": "ready" if agent_status else "not_loaded"
        }
    }

@app.get("/conversations/stats", response_model=ConversationStatsResponse)
def get_conversation_stats():
    """Get statistics about logged conversations"""
    try:
        stats = ConversationLogger.get_conversation_stats()
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
        return ConversationStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@app.get("/conversations/recent")
def get_recent_conversations(limit: int = 10):
    """Get recent conversations"""
    try:
        conversations = ConversationLogger.get_recent_conversations(limit=limit)
        return {"conversations": conversations, "count": len(conversations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")

@app.get("/conversations/search")
def search_conversations(query: str, limit: int = 20):
    """Search conversations by text"""
    try:
        conversations = ConversationLogger.search_conversations(query=query, limit=limit)
        return {"conversations": conversations, "count": len(conversations), "query": query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching conversations: {str(e)}")

# --- Run the App (Optional: For direct execution) ---
if __name__ == "__main__":
    print("Starting FastAPI server directly (use 'uvicorn' for development)...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)