import asyncio
from app.services.matchmaking_service import build_match_report

async def run():
    payload_boy = {
        "name": "Boy",
        "date_of_birth": "2000-01-01",
        "time_of_birth": "12:00",
        "birth_place": "Delhi",
        "gender": "male",
        "birth_time_accuracy": "exact",
        "latitude": 28.6,
        "longitude": 77.2
    }
    payload_girl = {
        "name": "Girl",
        "date_of_birth": "2002-05-10",
        "time_of_birth": "14:30",
        "birth_place": "Mumbai",
        "gender": "female",
        "birth_time_accuracy": "exact",
        "latitude": 19.0,
        "longitude": 72.8
    }
    res = await build_match_report(payload_boy, payload_girl)
    dashas = res.get("charts", {}).get("boy", {}).get("dashas")
    print(f"dashas type: {type(dashas)}, value: {dashas}")

if __name__ == "__main__":
    asyncio.run(run())
