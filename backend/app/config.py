import os
from dotenv import load_dotenv
import pathlib

# Determine the path to the .env file relative to this config.py file
# Assumes .env is in the 'backend' directory, one level up from 'app'
# config.py -> app/ -> backend/ -> .env
env_path = pathlib.Path(__file__).parent.parent / '.env'

# Load the environment variables from the .env file
print(f"Attempting to load .env file from: {env_path}")
load_dotenv(dotenv_path=env_path)

# Retrieve the Google AI API Key (using the new name)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Changed variable name here

# Retrieve the MongoDB Connection String
MONGO_DB_URI = os.getenv("MONGO_DB_URI")

# --- Validation (Optional but Recommended) ---
if not GOOGLE_API_KEY: # Check the new variable name
    print("⚠️ Warning: GOOGLE_API_KEY not found in environment variables.")
    # Depending on your setup, you might want to raise an error here
    # raise ValueError("GOOGLE_API_KEY is not set. Please check your .env file.")

if not MONGO_DB_URI:
    print("⚠️ Warning: MONGO_DB_URI not found in environment variables.")
    # Depending on your setup, you might want to raise an error here
    # raise ValueError("MONGO_DB_URI is not set. Please check your .env file.")
else:
    # Basic check to see if it looks like an Atlas connection string
    if not MONGO_DB_URI.startswith("mongodb+srv://"):
            print("⚠️ Warning: MONGO_DB_URI does not look like an Atlas connection string (mongodb+srv://...).")

print("Config loaded.") # Confirm that the config file was executed


