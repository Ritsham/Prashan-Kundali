import httpx
import asyncio

async def test():
    try:
        resp = await httpx.post('http://localhost:8001/calculate', json={'chart_type': 'lagna', 'name': 'test', 'gender': 'male', 'birth_datetime_local': '1990-01-01T10:00:00', 'location': {'latitude': 28.6, 'longitude': 77.2, 'place_name': 'Delhi'}})
        print(resp.json()['chart'].keys() if resp.status_code == 200 else resp.status_code)
    except Exception as e:
        print(e)
asyncio.run(test())
