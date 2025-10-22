from flask import Flask, request, jsonify
from bson.objectid import ObjectId
from datetime import datetime
from models import get_tracked_flights_collection, get_price_history_collection

app = Flask(__name__)

# --- Helper Function ---
def serialize_doc(doc):
    """Converts a MongoDB doc to a JSON-serializable format."""
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    if 'trackedFlightId' in doc:
        doc['trackedFlightId'] = str(doc['trackedFlightId'])
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc

# --- API Endpoints ---
@app.route("/")
def home():
    return "Flight Tracker API is running!"

@app.route("/api/v1/track", methods=['POST'])
def create_track_request():
    """Creates a new flight tracking job."""
    try:
        data = request.json
        tracked_flights_collection = get_tracked_flights_collection()
        data['departureDate'] = datetime.fromisoformat(data['departureDate'])
        data['trackingStartDate'] = datetime.fromisoformat(data['trackingStartDate'])
        data['status'] = 'ACTIVE'
        result = tracked_flights_collection.insert_one(data)
        return jsonify({
            "message": "Tracking job created!",
            "inserted_id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/v1/track/<string:job_id>/history", methods=['GET'])
def get_price_history(job_id):
    """Gets the price history for a specific tracking job."""
    try:
        price_history_collection = get_price_history_collection()
        history_docs = price_history_collection.find({
            "trackedFlightId": ObjectId(job_id)
        }).sort("timestamp", 1)
        history_list = [serialize_doc(doc) for doc in history_docs]
        if not history_list:
            return jsonify({"message": "No history found for this job."}), 404
        return jsonify(history_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/search", methods=['GET'])
def search_flights():
    """
    Performs a hybrid search for flight jobs with weighted ranking.
    Query params:
    - q (string): Text to search in description (e.g., "trip")
    - origin (string): Exact origin airport (e.g., "LHE")
    - airline (string): Exact airline (e.g., "Saudia")
    """
    try:
        tracked_flights_collection = get_tracked_flights_collection()
        query_text = request.args.get('q')
        query_origin = request.args.get('origin')
        query_airline = request.args.get('airline')

        if not query_text and not query_origin and not query_airline:
            return jsonify({"error": "Please provide at least one search parameter."}), 400

        search_pipeline = []

        # --- 1. $search (Hybrid Search) ---
        search_stage = {
            "$search": {
                "index": "flight_search",
                "compound": {}
            }
        }
        if query_text:
            search_stage["$search"]["compound"]["must"] = [{"text": {"query": query_text, "path": "description", "fuzzy": {"maxEdits": 1}}}]

        filters = []
        if query_origin:
            filters.append({"term": {"path": "origin", "query": query_origin}})
        if query_airline:
            filters.append({"term": {"path": "airline", "query": query_airline}})

        if filters:
            search_stage["$search"]["compound"]["filter"] = filters

        search_pipeline.append(search_stage)

        # --- 2. $addFields (Calculate Scores) ---
        search_pipeline.append({
            "$addFields": {
                "searchScore": {"$ifNull": [{"$meta": "searchScore"}, 0]},
                "daysToDeparture": {
                    "$max": [
                        0,
                        {"$divide": [
                            {"$subtract": ["$departureDate", datetime.now(datetime.now().astimezone().tzinfo)]},
                            1000 * 60 * 60 * 24
                        ]}
                    ]
                }
            }
        })

        # --- 3. $addFields (Calculate Urgency Score) ---
        search_pipeline.append({
            "$addFields": {
                "urgencyScore": {
                    "$cond": {
                        "if": {"$lte": ["$daysToDeparture", 30]},
                        "then": 1.0,
                        "else": {
                            "$max": [0, {"$subtract": [1, {"$divide": ["$daysToDeparture", 180]}]}]
                        }
                    }
                }
            }
        })

        # --- 4. $addFields (Calculate Final Weighted Score) ---
        search_pipeline.append({
            "$addFields": {
                "finalRankScore": {
                    "$add": [
                        {"$multiply": ["$searchScore", 0.7]},
                        {"$multiply": ["$urgencyScore", 0.3]}
                    ]
                }
            }
        })

        # --- 5. $sort (Final Ranking) ---
        search_pipeline.append({
            "$sort": {"finalRankScore": -1}
        })

        # --- 6. Run the search ---
        results = list(tracked_flights_collection.aggregate(search_pipeline))
        return jsonify([serialize_doc(doc) for doc in results]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Run the App (This MUST be at the end) ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)