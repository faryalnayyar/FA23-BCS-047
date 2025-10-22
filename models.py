import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')

if not MONGO_URI:
    raise EnvironmentError("MONGO_URI not found in .env file. Please check your .env file.")

# Create a single, reusable client instance
try:
    client = MongoClient(MONGO_URI)
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful.")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    client = None

def get_db():
    """
    Returns the database instance.
    """
    if client:
        return client['flight_tracker_db'] # Your database name
    else:
        raise ConnectionError("MongoDB client is not connected.")

def get_tracked_flights_collection():
    """
    Returns the 'tracked_flights' collection.
    """
    db = get_db()
    return db['tracked_flights']

def get_price_history_collection():
    """
    Returns the 'price_history' collection.
    """
    db = get_db()
    return db['price_history']