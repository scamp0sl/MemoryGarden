import asyncio
import os
import sys
from datetime import datetime
from uuid import UUID

# Add project root to sys.path
sys.path.append(os.getcwd())

from database.postgres import AsyncSessionLocal
from database.models import User
from database.redis_client import redis_client
from sqlalchemy import select

async def audit_users():
    async with AsyncSessionLocal() as db:
        # 1. Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        print(f"Total users in DB: {len(users)}")
        
        missing_oauth = []
        missing_schedule_redis = []
        active_users = []
        
        for user in users:
            user_id = str(user.id)
            
            # Check OAuth
            has_oauth = bool(user.kakao_access_token)
            if not has_oauth:
                missing_oauth.append(user)
            
            # Check Redis schedule
            schedule_key = f"schedule:{user_id}"
            schedule = await redis_client.get_json(schedule_key)
            if not schedule:
                missing_schedule_redis.append(user)
            
            has_phone = bool(user.phone)
            
            if has_oauth and schedule:
                active_users.append(user)

        print(f"\nUsers with OAuth token: {len(users) - len(missing_oauth)}")
        print(f"Users with Redis schedule entry: {len(users) - len(missing_schedule_redis)}")
        print(f"Users ready for scheduled dialogue (OAuth + Schedule): {len(active_users)}")
        
        print("\n--- Summary of Users NOT receiving messages ---")
        for u in users:
            if u in active_users: continue
            status = []
            if not u.kakao_access_token: status.append("No OAuth")
            if not await redis_client.get_json(f"schedule:{str(u.id)}"): status.append("No Schedule")
            if not u.phone: status.append("No Phone")
            
            print(f"- {u.name} (id: {u.id}): {', '.join(status)}")

if __name__ == "__main__":
    asyncio.run(audit_users())
