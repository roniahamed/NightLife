import asyncio
import websockets
import json
import urllib.request
import urllib.parse
from uuid import uuid4

async def test_websocket():
    # First, let's create a standard user and a venue user via Django shell or just assume we have tokens.
    # Actually, we can just connect without a token and check if it closes.
    uri = "ws://localhost:8000/ws/inbox/"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            print(f"Received: {response}")
    except Exception as e:
        print(f"Connection failed (expected if no token): {e}")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(test_websocket())
