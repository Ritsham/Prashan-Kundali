import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

dummy_requests = [
    {
        "id": "req-seed-1",
        "consultant_id": "founder-rupesh-kumar",
        "name": "Rahul Sharma",
        "topic": "Career",
        "status": "pending",
        "phone": "+919876543210",
        "email": "rahul@example.com",
        "date_of_birth": "1990-05-14",
        "time_of_birth": "14:30",
        "place_of_birth": "Mumbai",
        "question": "When will I get a promotion?",
        "payment_status": "Paid",
        "queue_number": 1
    },
    {
        "id": "req-seed-2",
        "consultant_id": "founder-rupesh-kumar",
        "name": "Priya Singh",
        "topic": "Marriage",
        "status": "accepted",
        "phone": "+919876500000",
        "email": "priya@example.com",
        "date_of_birth": "1995-10-22",
        "time_of_birth": "08:15",
        "place_of_birth": "Delhi",
        "question": "Will I have an arranged or love marriage?",
        "payment_status": "Pending",
        "queue_number": 2
    }
]

dummy_matchmaking = [
    {
        "id": "match-seed-1",
        "boy_name": "Rahul",
        "girl_name": "Priya",
        "status": "completed",
        "guna_score": 28.5,
        "max_score": 36.0,
        "result_category": "Excellent Match",
        "report_json": {"status": "ok"}
    }
]

print("Filling consultation admin dummy data to Supabase...")
for req in dummy_requests:
    try:
        supabase.table("consultation_requests").upsert(req).execute()
        print(f"Inserted consultation request: {req['name']}")
    except Exception as e:
        print(f"Error inserting consultation request: {e}")

for match in dummy_matchmaking:
    try:
        supabase.table("match_requests").upsert(match).execute()
        print(f"Inserted matchmaking request: {match['boy_name']} & {match['girl_name']}")
    except Exception as e:
        print(f"Error inserting matchmaking request: {e}")

print("Done.")
