import asyncio
import os
import sys

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User
from sqlalchemy import select

async def find_all_emails():
    print("--- All Non-Empty Emails in Users Table ---")
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email.is_not(None))
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        for u in users:
            if u.email.strip():
                print(f"ID: {u.id} | Email: {u.email} | Name: {u.name}")

if __name__ == "__main__":
    asyncio.run(find_all_emails())
