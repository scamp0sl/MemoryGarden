import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User
from database.redis_client import redis_client
from sqlalchemy import select

async def list_all_user_info():
    print(f"{'User ID':<40} | {'PG Name':<15} | {'Email':<30} | {'Redis Name':<15} | {'Redis Nickname':<15}")
    print("-" * 125)
    
    async with AsyncSessionLocal() as session:
        # 1. Get all users from PostgreSQL
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        for user in users:
            user_id = str(user.id)
            pg_name = user.name or ""
            pg_email = user.email or ""
            
            # 2. Get from Redis
            redis_name_data = await redis_client.get_json(f"biographical:{user_id}:name")
            redis_name = redis_name_data.get("value", "") if redis_name_data else ""
            
            # Also check 'user_name' key in Redis as some users have it there
            if not redis_name:
                redis_user_name_data = await redis_client.get_json(f"biographical:{user_id}:user_name")
                redis_name = redis_user_name_data.get("value", "") if redis_user_name_data else ""

            redis_nickname_data = await redis_client.get_json(f"biographical:{user_id}:nickname")
            redis_nickname = redis_nickname_data.get("value", "") if redis_nickname_data else ""
            
            print(f"{user_id:<40} | {pg_name:<15} | {pg_email:<30} | {redis_name:<15} | {redis_nickname:<15}")

if __name__ == "__main__":
    asyncio.run(list_all_user_info())
