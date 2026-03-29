import asyncio
import os
import sys
import uuid

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.redis_client import redis_client
from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION

TARGET_USER_ID = "1f729443-7b80-4d82-a227-c4751b3bf35f"

async def cleanup_memory():
    print(f"--- Cleaning up memory for User: {TARGET_USER_ID} (shingoony@gmail.com) ---")
    
    # 1. Redis Cleanup
    print("\n[1] Redis Cleanup:")
    # Delete 'name' biographical entry
    name_key = f"biographical:{TARGET_USER_ID}:name"
    await redis_client.delete(name_key)
    print(f"  Deleted Redis key: {name_key}")
    
    # Delete 'nickname' biographical entry (if exists)
    nickname_key = f"biographical:{TARGET_USER_ID}:nickname"
    await redis_client.delete(nickname_key)
    print(f"  Deleted Redis key: {nickname_key}")
    
    # Reset session to clear context
    session_key = f"session:{TARGET_USER_ID}"
    await redis_client.delete(session_key)
    print(f"  Deleted Redis session: {session_key}")
    
    # Set a flag to trigger apology/new nickname prompt
    cleanup_flag_key = f"nickname_cleaned:{TARGET_USER_ID}"
    await redis_client.set(cleanup_flag_key, "1", ttl=86400) # 24h
    print(f"  Set cleanup flag in Redis: {cleanup_flag_key}")

    # 2. Qdrant Cleanup
    print("\n[2] Qdrant Cleanup:")
    await qdrant_manager.initialize()
    if qdrant_manager.client:
        # Points found in earlier review
        points_to_delete = [
            "0a41b5c0-51a9-4891-99ae-c14c33118029",
            "666e363d-2e60-4055-82ec-98662c852d5a"
        ]
        try:
            await qdrant_manager.client.delete(
                collection_name=BIOGRAPHICAL_COLLECTION,
                points_selector=points_to_delete
            )
            print(f"  Deleted points from Qdrant {BIOGRAPHICAL_COLLECTION}: {points_to_delete}")
        except Exception as e:
            print(f"  Error deleting Qdrant points: {e}")
    else:
        print("  Qdrant client not available.")

    print("\nCleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_memory())
