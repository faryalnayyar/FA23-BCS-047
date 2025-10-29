import json
from datetime import datetime
from models import get_tracked_flights_collection, get_price_history_collection

def seed_database():
    try:
        print("Getting database collections...")
        tracked_flights_collection = get_tracked_flights_collection()
        price_history_collection = get_price_history_collection()

        print("Clearing old data...")
        tracked_flights_collection.delete_many({})
        price_history_collection.delete_many({})

        print("Loading data from dataset.json...")
        with open('dataset.json', 'r') as f:
            data = json.load(f)

        # Convert date strings to Python datetime objects
        for item in data:
            item['departureDate'] = datetime.fromisoformat(item['departureDate'].replace('Z', '+00:00'))
            item['trackingStartDate'] = datetime.fromisoformat(item['trackingStartDate'].replace('Z', '+00:00'))
            if 'lastCheckedTimestamp' in item:
                 
                 item['lastCheckedTimestamp'] = datetime.fromisoformat(item['lastCheckedTimestamp'].replace('Z', '+00:00'))


        print(f"Seeding {len(data)} flight tracking jobs...")
        result = tracked_flights_collection.insert_many(data)
        print(f"Successfully seeded {len(result.inserted_ids)} jobs.")

    except Exception as e:
        print(f"An error occurred during seeding: {e}")

if __name__ == "__main__":
    seed_database()
    print("Seeding complete.")
