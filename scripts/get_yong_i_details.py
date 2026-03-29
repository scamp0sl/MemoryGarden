import asyncio
import os
import sys
import uuid

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import User
from sqlalchemy import select

async def get_user_details(user_ids):
    async with AsyncSessionLocal() as session:
        # Convert strings to UUID objects if they aren't already
        uuid_list = [uuid.UUID(uid) for uid in user_ids]
        stmt = select(User).where(User.id.in_(uuid_list))
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        if not users:
            print("No users found in database for these IDs.")
            return
            
        print(f"Details for {len(users)} users:")
        for user in users:
            print(f"- ID: {user.id}")
            print(f"  KAKAO_ID: {user.kakao_id}")
            print(f"  NAME: {user.name}")
            print(f"  GARDEN_NAME: {user.garden_name}")
            print(f"  EMAIL: {user.email}")
            print(f"  CREATED_AT: {user.created_at}")
            print("-" * 20)

if __name__ == "__main__":
    ids = [
        "1f729443-7b80-4d82-a227-c4751b3bf35f",
        "a98d44bc-9cd4-43fd-b7de-109c514ef540",
        "45346cb1-2f52-4ff4-bc6d-5872bcc65988"
    ]
    asyncio.run(get_user_details(ids))
