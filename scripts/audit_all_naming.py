import asyncio
import os
import sys
from datetime import datetime, timedelta

# Configure path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.postgres import AsyncSessionLocal
from database.models import Conversation, User
from sqlalchemy import select, desc

async def audit_all_naming():
    print("--- Auditing All Naming/Addressing in Last 24 Hours ---")
    cutoff = datetime.now() - timedelta(hours=24)
    
    async with AsyncSessionLocal() as session:
        stmt = select(Conversation, User.name).join(User, Conversation.user_id == User.id).where(
            Conversation.created_at >= cutoff
        ).order_by(desc(Conversation.created_at))
        
        result = await session.execute(stmt)
        for conv, user_name in result.all():
            # Check if response mentions a name
            resp = conv.response or ""
            # Simple heuristic: look for honorifics or known nicknames
            if any(x in resp for x in ["님", "씨", "오빠", "누나", "언니", "동생", "로제", "7번", "용이"]):
                print(f"[{conv.created_at}] User ID: {conv.user_id} (DB Name: {user_name})")
                print(f"  Msg : {conv.message}")
                print(f"  Resp: {resp}")
                print("-" * 20)

if __name__ == "__main__":
    asyncio.run(audit_all_naming())
