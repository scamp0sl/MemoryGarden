import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User
from sqlalchemy import select

async def list_users():
    async with AsyncSessionLocal() as session:
        stmt = select(User).order_by(User.created_at)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        print(f"Total users: {len(users)}")
        for i, user in enumerate(users):
            print(f"{i+1}: ID={user.id}, NAME={user.name}, KAKAO_ID={user.kakao_id}")

if __name__ == "__main__":
    asyncio.run(list_users())
