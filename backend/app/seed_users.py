# seed_users.py

import pymongo
import hashlib
from datetime import datetime
from app.config import MONGO_DB_URI

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_DB_URI)
db = client.supportDB
users_collection = db.users

# Sample users
sample_users = [
    {
        "email": "john.doe@example.com",
        "name": "John Doe",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "created_at": datetime.utcnow(),
        "status": "active"
    },
    {
        "email": "your-email@gmail.com",  # ← Use your real email for testing!
        "name": "Test User",
        "password_hash": hashlib.sha256("test123".encode()).hexdigest(),
        "created_at": datetime.utcnow(),
        "status": "active"
    }
]

# Clear existing users (optional)
users_collection.delete_many({})

# Insert sample users
result = users_collection.insert_many(sample_users)
print(f"✅ Inserted {len(result.inserted_ids)} users")

for user in sample_users:
    print(f"  - {user['email']} (name: {user['name']})")

client.close()