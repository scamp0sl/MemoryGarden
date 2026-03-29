import asyncio
import os
import sys

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from sqlalchemy import select, desc

async def check_all_recent_convs():
    async with AsyncSessionLocal() as session:
        # Get the 10 most recent conversations across all users
        stmt = (
            select(Conversation, User.name, User.kakao_id, User.email)
            .join(User, Conversation.user_id == User.id)
            .order_by(desc(Conversation.created_at))
            .limit(10)
        )
        result = await session.execute(stmt)
        rows = result.all()
        
        print("10 Most Recent Conversations:")
        for conv, name, kakao_id, email in rows:
            print(f"- UserID: {conv.user_id}")
            print(f"  DB Name: {name}, KakaoID: {kakao_id}, Email: {email}")
            print(f"  Response: {conv.response}")
            print(f"  Created At: {conv.created_at}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_all_recent_convs())
