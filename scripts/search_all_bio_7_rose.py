import asyncio
import os
import sys
import json

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client

async def search_all_bio():
    print("--- Searching All Redis Biographical Facts for '7' or '로제' ---")
    keys = await redis_client.keys("biographical:*")
    for key in keys:
        data = await redis_client.get(key)
        if data and ("7" in data or "로제" in data):
            print(f"  Key: {key}, Data: {data}")

if __name__ == "__main__":
    asyncio.run(search_all_bio())
