import asyncio
import os
import sys
from datetime import datetime, timedelta

# Configure path so we can import from the app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config.settings import settings

async def get_stats():
    # Create engine and session maker
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    user_id = 'aa96e75d-70e2-4546-9001-043cc5db047d'
    
    # Dates: Yesterday (Mar 12) and Today (Mar 13)
    # The timezone is +09:00, let's filter based on timestamp >= '2026-03-12 00:00:00+09'
    
    query = text("""
        SELECT 
            DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul') as chat_date,
            category,
            COUNT(*) as count
        FROM conversations
        WHERE user_id = :user_id
        AND created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul' >= '2026-03-12 00:00:00'
        GROUP BY chat_date, category
        ORDER BY chat_date, category
    """)
    
    async with async_session() as session:
        result = await session.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        print(f"Stats for user {user_id} (주인님) on March 12 and March 13:")
        print("-" * 50)
        
        # MCDI mapping if exists, but we'll show the raw category names
        stats_by_date = {}
        for row in rows:
            date_str = str(row.chat_date)
            cat = row.category or 'UNKNOWN'
            count = row.count
            
            if date_str not in stats_by_date:
                stats_by_date[date_str] = {}
            stats_by_date[date_str][cat] = count
            
        for date, cats in stats_by_date.items():
            print(f"Date: {date}")
            for cat, count in cats.items():
                print(f"  - {cat}: {count} turns")
            print("-" * 50)
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(get_stats())
