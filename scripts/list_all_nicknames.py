import asyncio
import os
import sys
import json

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client

async def list_all_nicknames():
    print("--- Listing All Nicknames and Names for All Users ---")
    
    # Use redis_client.keys to find all nickname and name keys
    nickname_keys = await redis_client.keys("biographical:*:nickname")
    name_keys = await redis_client.keys("biographical:*:name")
    
    all_keys = nickname_keys + name_keys
    
    for key in all_keys:
        data = await redis_client.get(key)
        if data:
            data_json = json.loads(data)
            user_id = data_json.get("user_id")
            entity = data_json.get("entity")
            value = data_json.get("value")
            print(f"User: {user_id} | {entity}: {value}")

if __name__ == "__main__":
    asyncio.run(list_all_nicknames())
