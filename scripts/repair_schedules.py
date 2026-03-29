import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from database.postgres import AsyncSessionLocal
from database.models import User
from database.redis_client import redis_client
from core.dialogue.scheduler import get_scheduler
from sqlalchemy import select

async def repair_schedules():
    async with AsyncSessionLocal() as db:
        # 1. Get all users who have OAuth
        result = await db.execute(select(User).where(User.kakao_access_token != None))
        users = result.scalars().all()
        
        print(f"Total users with OAuth: {len(users)}")
        
        scheduler = get_scheduler()
        # Important: apscheduler might not be started if we just get the instance here without a running event loop
        # But APScheduler inside DialogueScheduler is AsyncIOScheduler, so it needs a loop.
        
        repaired_count = 0
        for user in users:
            user_id = str(user.id)
            schedule = await redis_client.get_json(f"schedule:{user_id}")
            
            if not schedule:
                print(f"Repairing schedule for {user.name} ({user_id})...")
                await scheduler.add_user_schedule(user_id)
                repaired_count += 1
            else:
                print(f"Schedule already exists for {user.name} ({user_id}).")

        print(f"\nRepaired {repaired_count} user schedules.")

if __name__ == "__main__":
    asyncio.run(repair_schedules())
