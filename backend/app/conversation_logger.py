import pymongo
from datetime import datetime
from typing import List, Dict, Optional
from app.config import MONGO_DB_URI

# --- Database Connection ---
try:
    print("Setting up conversation logger connection to MongoDB...")
    client = pymongo.MongoClient(MONGO_DB_URI, serverSelectionTimeoutMS=10000)
    client.admin.command('ismaster')
    db = client.supportDB
    conversations_collection = db.conversations
    print("✅ Conversation logger connected to MongoDB.")
except Exception as e:
    print(f"❌ Conversation logger MongoDB connection failed: {e}")
    conversations_collection = None


class ConversationLogger:
    """Helper class to log conversations to MongoDB"""
    
    @staticmethod
    def log_conversation(
        user_message: str,
        agent_response: str,
        conversation_history: List[Dict],
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Logs a conversation turn to MongoDB.
        
        Args:
            user_message: The user's input message
            agent_response: The agent's response
            conversation_history: Full conversation history
            metadata: Additional metadata (e.g., session_id, user_id, ip_address)
            
        Returns:
            str: The inserted document ID, or None if failed
        """
        if conversations_collection is None:
            print("⚠️ Cannot log conversation: Database not connected")
            return None
        
        try:
            # Prepare the conversation document
            conversation_doc = {
                "timestamp": datetime.utcnow(),
                "user_message": user_message,
                "agent_response": agent_response,
                "conversation_length": len(conversation_history),
                "full_history": conversation_history,
                "metadata": metadata or {},
                "response_length": len(agent_response),
                "message_length": len(user_message)
            }
            
            # Add metadata fields if provided
            if metadata:
                if "session_id" in metadata:
                    conversation_doc["session_id"] = metadata["session_id"]
                if "user_id" in metadata:
                    conversation_doc["user_id"] = metadata["user_id"]
                if "ip_address" in metadata:
                    conversation_doc["ip_address"] = metadata["ip_address"]
            
            # Insert into MongoDB
            result = conversations_collection.insert_one(conversation_doc)
            print(f"✅ Conversation logged with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"❌ Error logging conversation: {e}")
            return None
    
    @staticmethod
    def get_conversation_stats() -> Dict:
        """Get statistics about logged conversations"""
        if conversations_collection is None:
            return {"error": "Database not connected"}
        
        try:
            total_conversations = conversations_collection.count_documents({})
            
            # Get average response length
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "avg_response_length": {"$avg": "$response_length"},
                        "avg_message_length": {"$avg": "$message_length"},
                        "total_conversations": {"$sum": 1}
                    }
                }
            ]
            
            stats = list(conversations_collection.aggregate(pipeline))
            
            if stats:
                return {
                    "total_conversations": total_conversations,
                    "avg_response_length": round(stats[0].get("avg_response_length", 0), 2),
                    "avg_message_length": round(stats[0].get("avg_message_length", 0), 2)
                }
            else:
                return {"total_conversations": total_conversations}
                
        except Exception as e:
            print(f"❌ Error getting conversation stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_recent_conversations(limit: int = 10) -> List[Dict]:
        """Retrieve recent conversations"""
        if conversations_collection is None:
            return []
        
        try:
            conversations = conversations_collection.find().sort("timestamp", -1).limit(limit)
            result = []
            for conv in conversations:
                conv["_id"] = str(conv["_id"])  # Convert ObjectId to string
                result.append(conv)
            return result
        except Exception as e:
            print(f"❌ Error retrieving conversations: {e}")
            return []
    
    @staticmethod
    def search_conversations(query: str, limit: int = 20) -> List[Dict]:
        """Search conversations by text"""
        if conversations_collection is None:
            return []
        
        try:
            # Text search on user_message and agent_response
            search_filter = {
                "$or": [
                    {"user_message": {"$regex": query, "$options": "i"}},
                    {"agent_response": {"$regex": query, "$options": "i"}}
                ]
            }
            
            conversations = conversations_collection.find(search_filter).sort("timestamp", -1).limit(limit)
            result = []
            for conv in conversations:
                conv["_id"] = str(conv["_id"])
                result.append(conv)
            return result
        except Exception as e:
            print(f"❌ Error searching conversations: {e}")
            return []