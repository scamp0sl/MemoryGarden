import asyncio
import os
import sys
import json

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client

async def global_redis_search_rose():
    print("--- Global Redis Search for '로제' in Biographical Facts ---")
    keys = await redis_client.keys("biographical:*")
    print(f"Total biographical keys: {len(keys)}")
    
    found = 0
    for key in keys:
        val = await redis_client.get(key)
        if "로제" in val:
            print(f"  MATCH in {key}: {val}")
            found += 1
    
    print(f"\nTotal matches found: {found}")

if __name__ == "__main__":
    asyncio.run(global_redis_search_rose())
