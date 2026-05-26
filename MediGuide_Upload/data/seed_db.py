import os
import json
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = "medical_db"
COLLECTION_NAME = "guidelines"

def seed_db():
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Clear existing data to avoid duplicates in hackathon
        collection.delete_many({})
        print("Existing guidelines cleared.")

        # Read JSON
        data_path = os.path.join(os.path.dirname(__file__), "medical_dummy_data.json")
        if not os.path.exists(data_path):
            # Fallback path if run from backend/
            data_path = os.path.join(os.path.dirname(__file__), "..", "data", "medical_dummy_data.json")

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        result = collection.insert_many(data)
        print(f"Successfully seeded {len(result.inserted_ids)} medical guidelines!")
        
    except Exception as e:
        print(f"Database seeding failed: {e}")
        print("Tip: Make sure MongoDB is running locally on port 27017 (default).")

if __name__ == "__main__":
    seed_db()
