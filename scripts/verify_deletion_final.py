import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User
from sqlalchemy import select, func

async def check():
    async with AsyncSessionLocal() as session:
        count = (await session.execute(select(func.count(User.id)))).scalar()
        print(f"Total Users: {count}")
        
        users = (await session.execute(select(User.id, User.name, User.email))).scalars().all()
        # Note: scalars().all() with select(User.id...) will only give the first col if not careful
        # Let's do it properly
        res = await session.execute(select(User))
        all_users = res.scalars().all()
        for u in all_users:
            print(f"- {u.id}: {u.name} ({u.email or 'no email'})")

if __name__ == "__main__":
    asyncio.run(check())
