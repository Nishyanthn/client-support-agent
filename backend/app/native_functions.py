import pymongo
import os
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from app.config import MONGO_DB_URI # Imports the connection string from config.py

# --- Database Connection ---
# Attempt to set up the MongoDB connection once when the app starts.
try:
    print("Attempting to connect to MongoDB Atlas...")
    # Increase timeout for potentially slower cloud connections
    client = pymongo.MongoClient(MONGO_DB_URI, serverSelectionTimeoutMS=10000)
    # The ismaster command is cheap and does not require auth.
    client.admin.command('ismaster')
    db = client.supportDB # Replace 'supportDB' if your database name is different
    tickets_collection = db.tickets # Replace 'tickets' if your collection name is different
    print("✅ MongoDB connection successful.")
except pymongo.errors.ConfigurationError:
    print("❌ MongoDB connection failed: Invalid connection string or configuration.")
    client = None
    tickets_collection = None
except pymongo.errors.ServerSelectionTimeoutError as err:
    print(f"❌ MongoDB connection failed: Timeout or server not reachable. Error: {err}")
    client = None
    tickets_collection = None
except Exception as e:
    print(f"❌ An unexpected error occurred with MongoDB connection: {e}")
    client = None
    tickets_collection = None

# --- Native "Action" Functions ---

@kernel_function(
    description="Gets the current status of a specific customer support ticket using its unique ticket ID.",
    name="check_ticket_status"
)
def check_ticket_status(ticket_id: str) -> str:
    """
    Fetches the status of a given ticket_id from the MongoDB 'tickets' collection.
    This function acts as a tool for the AI agent.
    Args:
        ticket_id (str): The unique identifier of the support ticket (e.g., 'T-123').
    Returns:
        str: A message indicating the ticket's status or if it wasn't found/error occurred.
    """
    print(f"🤖 Action: Running 'check_ticket_status' for ID: {ticket_id}")

    if tickets_collection is None:
        print("Error: check_ticket_status called but database is not connected.")
        return "Error: Database connection is not available. Cannot check ticket status."

    if not ticket_id:
        return "Error: No ticket ID was provided."

    try:
        # Query the 'tickets' collection for the document with _id = ticket_id
        # Ensure your tickets in MongoDB actually use '_id' for the ticket identifier.
        ticket = tickets_collection.find_one({"_id": ticket_id})

        if ticket:
            # Found the ticket, return its status
            status = ticket.get("status", "Status not available") # Safely get status
            print(f"Ticket {ticket_id} found. Status: {status}")
            return f"The status for ticket {ticket_id} is: {status}"
        else:
            # No ticket found with that ID
            print(f"Ticket {ticket_id} not found in the database.")
            return f"Ticket {ticket_id} was not found in the system."

    except Exception as e:
        print(f"❌ Error during MongoDB query in check_ticket_status: {e}")
        return f"An error occurred while trying to check the status for ticket {ticket_id}."


@kernel_function(
    description="Initiates a password reset process for a user identified by their email address.",
    name="request_password_reset"
)
def request_password_reset(email: str) -> str:
    """
    Simulates sending a password reset email to the provided user email.
    In a real application, this would involve more steps like token generation,
    database updates, and calling an email service.
    Args:
        email (str): The email address of the user requesting the password reset.
    Returns:
        str: A confirmation message or an error message.
    """
    print(f"🤖 Action: Running 'request_password_reset' for email: {email}")

    # Basic email format validation (not exhaustive)
    if not email or "@" not in email or "." not in email:
        print(f"Invalid email format provided: {email}")
        return "Invalid email address format provided. Please provide a valid email."

    # --- Simulation Placeholder ---
    # In a real-world app, you would add logic here to:
    # 1. Check if the email exists in a 'users' collection in MongoDB.
    # 2. Generate a secure, time-limited reset token.
    # 3. Store the token associated with the user account (e.g., in the user document or a separate collection).
    # 4. Use an email library (like smtplib, SendGrid, Mailgun) to send an email
    #    containing a reset link (e.g., your-app.com/reset?token=...).
    print(f"SIMULATION: Pretending to generate reset token for {email} and send email...")
    # --- End Simulation ---

    # Return a success message to the agent (and ultimately the user)
    return f"A password reset link has been successfully sent to {email}. Please check your inbox."

# You can add more native functions here following the same pattern:
# - Define the Python function.
# - Decorate it with @kernel_function, providing a clear 'description' and a unique 'name'.
# - The description is crucial for the AI to know when to use the function.
