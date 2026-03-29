import asyncio
import os
import sys
from datetime import datetime

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.postgres import AsyncSessionLocal
from database.models import Conversation

async def fetch_conversations():
    user_id = 'aa96e75d-70e2-4546-9001-043cc5db047d'
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.created_at >= datetime(2026, 3, 13, 14, 0, 0)) # After the fix
            .order_by(Conversation.created_at.asc())
        )
        conversations = result.scalars().all()
        
        cats = {}
        for conv in conversations:
            cat = conv.category
            if cat not in cats:
                cats[cat] = []
            
            cats[cat].append({
                'turn': len(cats[cat]) + 1,
                'user_msg': conv.message,
                'ai_msg': conv.response
            })
            
        return cats

async def main():
    cats = await fetch_conversations()
    for cat, convs in cats.items():
        print(f"=== {cat} ===")
        for i, c in enumerate(convs[-2:]): # Print up to last 2 per category
            print(f"[Question {i+1} from AI]:", c['ai_msg'])
            print(f"[User Reply {i+1}]:", c['user_msg'])
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
