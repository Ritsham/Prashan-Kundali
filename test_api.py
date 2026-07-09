import asyncio
import json
from httpx import AsyncClient

async def run():
    payload = {
        "boy": {
            "name": "Boy",
            "date_of_birth": "2000-01-01",
            "time_of_birth": "12:00",
            "birth_place": "Delhi",
            "gender": "male",
            "birth_time_accuracy": "exact"
        },
        "girl": {
            "name": "Girl",
            "date_of_birth": "2002-05-10",
            "time_of_birth": "14:30",
            "birth_place": "Mumbai",
            "gender": "female",
            "birth_time_accuracy": "exact"
        }
    }
    async with AsyncClient() as client:
        # Assuming the backend is running on port 8000
        res = await client.post("http://localhost:8000/api/matchmaking/requests", json=payload, headers={"Authorization": "Bearer TEST"})
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            dashas = data.get("report", {}).get("charts", {}).get("boy", {}).get("dashas")
            print(f"dashas in API response: type={type(dashas)}, length={len(dashas) if dashas else 0}")
            print(f"keys: {dashas.keys() if isinstance(dashas, dict) else dashas}")

if __name__ == "__main__":
    asyncio.run(run())
