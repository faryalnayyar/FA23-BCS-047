import random
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta
from models import get_tracked_flights_collection, get_price_history_collection

# Get collections once when the script starts
try:
    tracked_flights_collection = get_tracked_flights_collection()
    price_history_collection = get_price_history_collection()
except Exception as e:
    print(f"Failed to connect to collections: {e}")
    exit(1)


def fetch_and_log_price(flight_job):
    """MIMICS fetching a price and logging it to the database."""
    try:
        print(f"Checking price for: {flight_job['origin']}->{flight_job['destination']} (ID: {flight_job['_id']})")

        # 1. MIMIC EXTERNAL API CALL
        mock_price = round(random.uniform(500, 800), 2)

        # 2. Log the new price
        price_log = {
            "trackedFlightId": flight_job['_id'],
            "timestamp": datetime.utcnow(),
            "price": mock_price,
            "currency": "USD",
            "source": "MockFetcher"
        }
        price_history_collection.insert_one(price_log)

        # 3. Update the flight's lastCheckedTimestamp
        tracked_flights_collection.update_one(
            {"_id": flight_job['_id']},
            {"$set": {"lastCheckedTimestamp": datetime.utcnow()}}
        )
        print(f"Logged new price: ${mock_price}")

    except Exception as e:
        print(f"Error fetching price for job {flight_job['_id']}: {e}")


def run_scheduler_jobs():
    """Finds all jobs that are due to be run."""
    print(f"\nScheduler running at {datetime.utcnow()}...")
    now = datetime.utcnow()

    query = {
        "status": "ACTIVE",
        "trackingStartDate": {"$lte": now},
        "departureDate": {"$gt": now}
    }

    flights_to_track = list(tracked_flights_collection.find(query))
    jobs_to_run = []

    for flight in flights_to_track:
        if 'lastCheckedTimestamp' not in flight:
            jobs_to_run.append(flight)
        else:
            minutes_to_wait = flight.get('trackingIntervalMinutes', 1440)  # Default 1 day
            next_run_time = flight['lastCheckedTimestamp'] + timedelta(minutes=minutes_to_wait)

            if now >= next_run_time:
                jobs_to_run.append(flight)

    if not jobs_to_run:
        print("No jobs are due for a price check.")
        return

    print(f"Found {len(jobs_to_run)} jobs to check...")

    for job in jobs_to_run:
        fetch_and_log_price(job)


# --- Start the Scheduler ---
if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(run_scheduler_jobs, 'interval', seconds=30)

    print("Scheduler started. Press Ctrl+C to exit.")
    run_scheduler_jobs()  # Run once immediately on start

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass