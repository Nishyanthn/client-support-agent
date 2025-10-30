import pymongo
from config import MONGO_DB_URI

# Connect to MongoDB
try:
    print("Connecting to MongoDB Atlas...")
    client = pymongo.MongoClient(MONGO_DB_URI, serverSelectionTimeoutMS=10000)
    client.admin.command('ismaster')
    db = client.supportDB
    conversations_collection = db.conversations
    print("✅ Connected successfully!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# Create indexes for better query performance
try:
    print("\n📊 Creating indexes...")
    
    # Index on timestamp for sorting recent conversations
    conversations_collection.create_index([("timestamp", -1)])
    print("✅ Created index on 'timestamp'")
    
    # Index on session_id for session-based queries
    conversations_collection.create_index("session_id")
    print("✅ Created index on 'session_id'")
    
    # Index on user_id for user-based queries (if you use it)
    conversations_collection.create_index("user_id")
    print("✅ Created index on 'user_id'")
    
    # Text index for full-text search on user messages and agent responses
    conversations_collection.create_index([
        ("user_message", "text"),
        ("agent_response", "text")
    ])
    print("✅ Created text index on 'user_message' and 'agent_response'")
    
    print("\n✅ All indexes created successfully!")
    
    # List all indexes
    print("\n📋 Current indexes:")
    for index in conversations_collection.list_indexes():
        print(f"  - {index['name']}: {index.get('key', 'N/A')}")
    
except Exception as e:
    print(f"❌ Error creating indexes: {e}")
finally:
    client.close()
    print("\n🔒 Connection closed.")