import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')

if not MONGO_URI:
    raise EnvironmentError("MONGO_URI not found in .env file. Please check your .env file.")

try:
    client = MongoClient(MONGO_URI)
 
    client.admin.command('ping')
    print("MongoDB connection successful.")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    client = None

def get_db():
  
    if client:
        return client['flight_tracker_db'] 
    else:
        raise ConnectionError("MongoDB client is not connected.")

def get_tracked_flights_collection():

    db = get_db()
    return db['tracked_flights']

def get_price_history_collection():
 
    db = get_db()
    return db['price_history']
