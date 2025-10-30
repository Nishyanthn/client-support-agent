import pymongo
import os
import sys
import pathlib
from datetime import datetime, timedelta # Import datetime and timedelta

# --- Sample Data Definition ---
# More detailed sample tickets
SAMPLE_TICKETS = [
    {
        "_id": "T-123",
        "user_email": "john.doe@example.com",
        "user_name": "John Doe",
        "subject": "Cannot login to dashboard",
        "description": "I've been trying to log in for the past hour but keep getting 'Invalid credentials' error.",
        "category": "Authentication",
        "priority": "High",
        "status": "In Progress",
        "created_at": datetime.now() - timedelta(days=2),
        "updated_at": datetime.now() - timedelta(hours=3),
        "assigned_to": "support_agent_1"
    },
    {
        "_id": "T-124",
        "user_email": "sarah.smith@example.com",
        "user_name": "Sarah Smith",
        "subject": "Dashboard metrics not updating",
        "description": "My dashboard metrics haven't updated since yesterday. The last update shows 24 hours ago.",
        "category": "Technical Issue",
        "priority": "Medium",
        "status": "Open",
        "created_at": datetime.now() - timedelta(days=1),
        "updated_at": datetime.now() - timedelta(days=1),
        "assigned_to": None
    },
    {
        "_id": "T-125",
        "user_email": "mike.johnson@example.com",
        "user_name": "Mike Johnson",
        "subject": "Billing inquiry - double charge",
        "description": "I was charged twice this month. Can you please review my billing history?",
        "category": "Billing",
        "priority": "High",
        "status": "Resolved",
        "created_at": datetime.now() - timedelta(days=5),
        "updated_at": datetime.now() - timedelta(days=1),
        "assigned_to": "support_agent_2",
        "resolution": "Refund processed for duplicate charge"
    },
    {
        "_id": "T-126",
        "user_email": "emma.wilson@example.com",
        "user_name": "Emma Wilson",
        "subject": "Feature request - Export to CSV",
        "description": "It would be great to have an option to export reports to CSV format.",
        "category": "Feature Request",
        "priority": "Low",
        "status": "Under Review",
        "created_at": datetime.now() - timedelta(days=3),
        "updated_at": datetime.now() - timedelta(days=2),
        "assigned_to": "product_team"
    },
    {
        "_id": "T-127",
        "user_email": "david.brown@example.com",
        "user_name": "David Brown",
        "subject": "API integration help needed",
        "description": "I'm trying to integrate your API but getting 401 errors. My API key seems valid.",
        "category": "Technical Issue",
        "priority": "Medium",
        "status": "In Progress",
        "created_at": datetime.now() - timedelta(hours=12),
        "updated_at": datetime.now() - timedelta(hours=2),
        "assigned_to": "support_agent_1"
    },
    {
        "_id": "T-128",
        "user_email": "lisa.anderson@example.com",
        "user_name": "Lisa Anderson",
        "subject": "Password reset not working",
        "description": "I requested a password reset but haven't received any email. Checked spam folder too.",
        "category": "Authentication",
        "priority": "High",
        "status": "Open",
        "created_at": datetime.now() - timedelta(hours=6),
        "updated_at": datetime.now() - timedelta(hours=6),
        "assigned_to": None
    },
    {
        "_id": "T-129",
        "user_email": "robert.taylor@example.com",
        "user_name": "Robert Taylor",
        "subject": "Account upgrade question",
        "description": "What are the benefits of upgrading to the Pro plan? Is there a discount for annual billing?",
        "category": "Sales",
        "priority": "Low",
        "status": "Resolved",
        "created_at": datetime.now() - timedelta(days=4),
        "updated_at": datetime.now() - timedelta(days=3),
        "assigned_to": "sales_team",
        "resolution": "Provided pricing information and 20% annual discount details"
    },
    {
        "_id": "T-130",
        "user_email": "jennifer.white@example.com",
        "user_name": "Jennifer White",
        "subject": "Data export takes too long",
        "description": "When I try to export my data, the process times out after 5 minutes. I have about 50k records.",
        "category": "Performance",
        "priority": "Medium",
        "status": "In Progress",
        "created_at": datetime.now() - timedelta(days=1),
        "updated_at": datetime.now() - timedelta(hours=8),
        "assigned_to": "support_agent_2"
    }
]
DATABASE_NAME = "supportDB"
COLLECTION_NAME = "tickets"

MONGO_DB_URI = None

def load_config_if_needed():
    """Loads config if MONGO_DB_URI is not already set."""
    global MONGO_DB_URI
    if MONGO_DB_URI is None:
        try:
            # Try importing within the function context
            from app.config import MONGO_DB_URI as CONFIG_MONGO_DB_URI
            MONGO_DB_URI = CONFIG_MONGO_DB_URI
            print("   - Successfully loaded MONGO_DB_URI from app.config")
        except ImportError:
             print("   - Warning: Could not import MONGO_DB_URI from app.config.")
        except Exception as e:
            print(f"   - Error importing config: {e}")

def seed_database():
    """
    Connects to MongoDB and inserts sample tickets if they don't already exist.
    """
    load_config_if_needed() # Ensure URI is loaded

    print("🌱 Checking/Seeding MongoDB sample data...")
    mongo_client = None
    try:
        if not MONGO_DB_URI or not MONGO_DB_URI.startswith("mongodb+srv://"):
             print("   - ⚠️ Warning: MONGO_DB_URI not configured correctly for seeding. Skipping.")
             return

        mongo_client = pymongo.MongoClient(MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        print("   - MongoDB connection verified for seeding.")
        db = mongo_client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        # --- Optional: Clear existing tickets ---
        # Uncomment the next two lines if you want to clear the collection on every startup
        # print("   - ⚠️ Clearing existing tickets (optional)...")
        # collection.delete_many({})
        # --- End Optional Clear ---

        inserted_count = 0
        skipped_count = 0
        print(f"   - Checking {len(SAMPLE_TICKETS)} sample tickets...")
        for ticket in SAMPLE_TICKETS:
            # Check if ticket with this _id already exists
            exists = collection.find_one({"_id": ticket["_id"]}, {"_id": 1})
            if not exists:
                try:
                    collection.insert_one(ticket)
                    inserted_count += 1
                except Exception as insert_error:
                    print(f"   - ❌ Error inserting ticket {ticket['_id']}: {insert_error}")
            else:
                skipped_count += 1

        if inserted_count > 0:
            print(f"   - ✅ Inserted {inserted_count} new sample ticket(s).")
        if skipped_count > 0:
            print(f"   - ⏩ Skipped {skipped_count} existing sample ticket(s).")
        print("✅ MongoDB data seeding check complete.")

    except pymongo.errors.ConfigurationError as ce:
        print(f"   - ❌ MongoDB Seeding Error (Configuration): {ce}")
    except pymongo.errors.ServerSelectionTimeoutError as sste:
        print(f"   - ❌ MongoDB Seeding Error (Connection Timeout): {sste}")
        print("      (Check Atlas IP Whitelist, Cluster Status, Connection String)")
    except Exception as e:
        print(f"   - ❌ Unexpected error during MongoDB seeding: {e}")
    finally:
        if mongo_client:
            mongo_client.close()
            print("   - MongoDB connection for seeding closed.")

# Allow running this script directly for manual seeding if needed
if __name__ == "__main__":
    print("Running DB Seeder directly...")

    # --- Path Adjustment for Direct Execution ---
    current_dir = pathlib.Path(__file__).parent.resolve()
    backend_dir = current_dir.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
        print(f"   - Added '{backend_dir}' to sys.path for direct execution.")
    # --- End Path Adjustment ---

    # Load .env variables if run directly
    try:
        from dotenv import load_dotenv
        env_path = backend_dir / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"   - Loaded environment variables from {env_path}")
            # Now attempt to load the config which reads from os.getenv
            load_config_if_needed() # This will now find app.config
        else:
            print(f"   - Warning: .env file not found at {env_path}")

    except ImportError:
        print("   - Warning: python-dotenv not installed. Ensure MONGO_DB_URI is set in environment.")
    except Exception as e:
        print(f"   - Error loading .env for direct run: {e}")

    # Now call the seeder function
    seed_database()
    print("Direct seeding finished.")

