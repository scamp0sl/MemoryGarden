import asyncio
import os
import sys
import json

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client

async def check_redis_yong_i():
    print("Checking Redis for '용이'...")
    
    found_keys = []
    for pattern in ["biographical:*", "episodic:*", "session:*", "context:*"]:
        keys = await redis_client.keys(pattern)
        for key in keys:
            data = await redis_client.get(key)
            if data and "용이" in data:
                found_keys.append((key, data))
                print(f"Found '용이' in Redis key ({pattern}): {key}")
                
    if not found_keys:
        print("No Redis keys found containing '용이'")
    else:
        print(f"Total found in Redis: {len(found_keys)}")
        for key, data in found_keys:
            # Try to identify user_id from key
            user_id = key.split(":")[-1]
            print(f"Key: {key}, UserID: {user_id}")
            # print(f"Data snippet: {data[:200]}...")

if __name__ == "__main__":
    asyncio.run(check_redis_yong_i())
