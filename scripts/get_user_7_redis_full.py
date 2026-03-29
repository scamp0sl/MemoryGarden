import asyncio
import os
import sys
import json

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client

TARGET_USER_ID = "6d7c59af-b8da-485f-8510-430e4f39dfaa"

async def get_user_7_session():
    print(f"--- Full Redis Data for User: {TARGET_USER_ID} (Nickname: 7번) ---")
    
    # 1. Session
    print("\n[1] Session:")
    session_data = await redis_client.get(f"session:{TARGET_USER_ID}")
    if session_data:
        print(json.dumps(json.loads(session_data), indent=2, ensure_ascii=False))
    else:
        print("No session data")

    # 2. Context
    print("\n[2] Context:")
    context_data = await redis_client.get(f"context:{TARGET_USER_ID}")
    if context_data:
        print(json.dumps(json.loads(context_data), indent=2, ensure_ascii=False))
    else:
        print("No context data")

    # 3. All Biographical keys
    print("\n[3] Biographical Facts:")
    keys = await redis_client.keys(f"biographical:{TARGET_USER_ID}:*")
    for key in keys:
        val = await redis_client.get(key)
        print(f"  {key}: {val}")

if __name__ == "__main__":
    asyncio.run(get_user_7_session())
