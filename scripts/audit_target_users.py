import asyncio
import os
import sys
from uuid import UUID

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User, Conversation, AnalysisResult, GardenStatus, MemoryEvent
from database.redis_client import redis_client
from core.nlp.embedder import Embedder
from qdrant_client import QdrantClient
from config.settings import settings
from sqlalchemy import select, func

async def audit_user(user_id_str):
    print(f"\n{'='*60}")
    print(f"🔍 Auditing User: {user_id_str}")
    print(f"{'='*60}")
    
    user_id = UUID(user_id_str)
    
    async with AsyncSessionLocal() as session:
        # 1. Basic User Info
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            print("❌ User not found in DB.")
            return

        print(f"Name: {user.name}")
        print(f"Kakao ID: {user.kakao_id}")
        print(f"Created At: {user.created_at}")
        
        # 2. Conversation Count
        conv_count = (await session.execute(select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id))).scalar()
        print(f"Conversation Count: {conv_count}")
        
        # 3. Analysis Results
        analysis_count = (await session.execute(select(func.count()).select_from(AnalysisResult).where(AnalysisResult.user_id == user_id))).scalar()
        print(f"Analysis Results: {analysis_count}")
        
        # 4. Garden Status
        garden = (await session.execute(select(GardenStatus).where(GardenStatus.user_id == user_id))).scalar_one_or_none()
        if garden:
            print(f"Garden: Level {garden.garden_level}, Flowers {garden.flower_count}, Last Interaction: {garden.last_interaction_at}")
        else:
            print("Garden: No record")

        # 5. Memory Events
        events_count = (await session.execute(select(func.count()).select_from(MemoryEvent).where(MemoryEvent.user_id == user_id))).scalar()
        print(f"Memory Events (Audit): {events_count}")

    # 6. Redis Schedule
    schedule = await redis_client.get_json(f"schedule:{user_id_str}")
    if schedule:
        print(f"Redis Schedule: Found ({len(schedule.get('job_ids', []))} jobs)")
    else:
        print("Redis Schedule: Not found")

    # 7. Redis Biographical Facts
    bio_keys = await redis_client.keys(f"biographical:{user_id_str}:*")
    print(f"Redis Bio Facts: {len(bio_keys)} entries")

    # 8. Qdrant Episodic Memory
    try:
        q_client = QdrantClient(url=settings.QDRANT_URL)
        collections = ["episodic_memory", "biographical_memory"]
        for coll in collections:
            count_res = q_client.count(
                collection_name=coll,
                count_filter={"must": [{"key": "user_id", "match": {"value": user_id_str}}]}
            )
            print(f"Qdrant {coll}: {count_res.count} points")
    except Exception as e:
        print(f"Qdrant Search Error: {e}")

async def main():
    target_ids = [
        "e3c61f48-509b-4ef8-a88a-651ea9467e34",
        "1828534c-7a0f-41e8-ba0b-a0a057738f44"
    ]
    for uid in target_ids:
        await audit_user(uid)

if __name__ == "__main__":
    asyncio.run(main())
