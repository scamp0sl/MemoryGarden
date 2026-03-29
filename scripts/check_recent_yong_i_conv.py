import asyncio
import os
import sys

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from sqlalchemy import select, desc

async def check_recent_yong_i_convs():
    async with AsyncSessionLocal() as session:
        # Search recent conversations with 용이님 or 용이 in response
        stmt = (
            select(Conversation, User.name, User.kakao_id, User.email)
            .join(User, Conversation.user_id == User.id)
            .where(Conversation.response.like("%용이%"))
            .order_by(desc(Conversation.created_at))
            .limit(5)
        )
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            print("No recent conversations found addressed to '용이'")
            return
            
        print(f"Recent {len(rows)} conversations involving '용이':")
        for conv, name, kakao_id, email in rows:
            print(f"- UserID: {conv.user_id}")
            print(f"  DB Name: {name}, KakaoID: {kakao_id}, Email: {email}")
            print(f"  Response: {conv.response}")
            print(f"  Created At: {conv.created_at}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_recent_yong_i_convs())
