import asyncio
import os
import sys

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.qdrant_client import qdrant_manager, BIOGRAPHICAL_COLLECTION

async def check_qdrant_yong_i():
    print("Checking Qdrant for '용이'...")
    await qdrant_manager.initialize()
    if not qdrant_manager.client:
        print("Qdrant client not available.")
        return

    try:
        # Scroll all points in BIOGRAPHICAL_COLLECTION
        results, _ = await qdrant_manager.client.scroll(
            collection_name=BIOGRAPHICAL_COLLECTION,
            limit=1000,
            with_payload=True
        )
        
        found_users = set()
        for point in results:
            payload_str = str(point.payload)
            if "용이" in payload_str:
                user_id = point.payload.get("user_id")
                found_users.add(user_id)
                print(f"Found '용이' in Qdrant {BIOGRAPHICAL_COLLECTION}: UserID={user_id}, Payload={point.payload}")
                
        if not found_users:
            print("No matching records found in Qdrant.")
        else:
            print(f"Total Unique Users found in Qdrant: {len(found_users)}")
            
    except Exception as e:
        print(f"Error checking Qdrant: {e}")

if __name__ == "__main__":
    asyncio.run(check_qdrant_yong_i())
