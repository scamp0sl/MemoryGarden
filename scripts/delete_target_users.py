import asyncio
import os
import sys
from uuid import UUID

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User
from database.redis_client import redis_client
from qdrant_client import QdrantClient
from config.settings import settings
from sqlalchemy import delete

async def delete_user_completely(user_id_str):
    print(f"\n{'='*60}")
    print(f"🗑️ Deleting User: {user_id_str}")
    print(f"{'='*60}")
    
    user_id = UUID(user_id_str)
    
    # 1. PostgreSQL Deletion (Cascades to other tables)
    async with AsyncSessionLocal() as session:
        try:
            stmt = delete(User).where(User.id == user_id)
            result = await session.execute(stmt)
            await session.commit()
            print(f"✅ PostgreSQL: User deleted (affected rows: {result.rowcount})")
        except Exception as e:
            print(f"❌ PostgreSQL Error: {e}")
            await session.rollback()

    # 2. Redis Deletion
    try:
        # Scan and delete all keys containing the user_id
        patterns = [
            f"*:{user_id_str}*",
            f"{user_id_str}:*",
            f"*{user_id_str}"
        ]
        total_deleted = 0
        for pattern in patterns:
            keys = await redis_client.keys(pattern)
            if keys:
                for key in keys:
                    await redis_client.delete(key)
                    total_deleted += 1
        print(f"✅ Redis: Deleted {total_deleted} keys associated with user.")
    except Exception as e:
        print(f"❌ Redis Error: {e}")

    # 3. Qdrant Deletion
    try:
        from qdrant_client.http import models
        q_client = QdrantClient(url=settings.QDRANT_URL)
        collections = ["episodic_memory", "biographical_memory"]
        for coll in collections:
            q_client.delete(
                collection_name=coll,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="user_id",
                                match=models.MatchValue(value=user_id_str),
                            ),
                        ],
                    )
                ),
            )
            print(f"✅ Qdrant {coll}: Deletion request sent.")
    except Exception as e:
        print(f"❌ Qdrant Error: {e}")

async def main():
    target_ids = [
        "e3c61f48-509b-4ef8-a88a-651ea9467e34",
        "1828534c-7a0f-41e8-ba0b-a0a057738f44"
    ]
    for uid in target_ids:
        await delete_user_completely(uid)
    print("\n🎉 All target users processed.")

if __name__ == "__main__":
    asyncio.run(main())
