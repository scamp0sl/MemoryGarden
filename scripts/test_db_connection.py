#!/usr/bin/env python3
"""
데이터베이스 연결 테스트 스크립트

PostgreSQL 연결 및 모델 로딩 테스트.

Usage:
    python scripts/test_db_connection.py
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.postgres import check_database_connection, AsyncSessionLocal
from models import User, Conversation, AnalysisResult
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_connection():
    """데이터베이스 연결 테스트"""
    print("=" * 60)
    print("🔍 Database Connection Test")
    print("=" * 60)

    # 1. 연결 테스트
    print("\n1️⃣ Testing database connection...")
    is_connected = await check_database_connection()

    if is_connected:
        print("✅ Database connection successful!")
    else:
        print("❌ Database connection failed!")
        return False

    # 2. 테이블 확인 (쿼리 실행)
    print("\n2️⃣ Testing table access...")
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text

            # 테이블 존재 확인
            result = await session.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
                )
            )

            tables = [row[0] for row in result.fetchall()]

            if tables:
                print(f"✅ Found {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("⚠️  No tables found. Run 'alembic upgrade head' first.")

    except Exception as e:
        print(f"❌ Table access failed: {e}")
        return False

    # 3. 모델 테스트
    print("\n3️⃣ Testing SQLAlchemy models...")
    try:
        print(f"✅ User model: {User.__tablename__}")
        print(f"✅ Conversation model: {Conversation.__tablename__}")
        print(f"✅ AnalysisResult model: {AnalysisResult.__tablename__}")
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\n📌 Next steps:")
    print("   1. Run migrations: alembic upgrade head")
    print("   2. Start API server: uvicorn api.main:app --reload")
    print("=" * 60)

    return True


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
