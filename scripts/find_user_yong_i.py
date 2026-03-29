import asyncio
import os
import sys

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User
from sqlalchemy import select

async def find_user_yong_i():
    async with AsyncSessionLocal() as session:
        # Search for name containing '용이'
        stmt = select(User).where(User.name.ilike("%용이%"))
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        if not users:
            print("No users found with name containing '용이'")
            return
            
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"- ID: {user.id}, KAKAO_ID: {user.kakao_id}, NAME: {user.name}, CREATED_AT: {user.created_at}")

if __name__ == "__main__":
    asyncio.run(find_user_yong_i())
