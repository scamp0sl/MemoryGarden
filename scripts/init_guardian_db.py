"""
보호자 테이블 초기화 스크립트

guardians, user_guardians, notification_logs 테이블 생성
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


async def create_guardian_tables():
    """보호자 관련 테이블 생성"""
    logger.info("=" * 60)
    logger.info("보호자 테이블 초기화 시작")
    logger.info("=" * 60)

    # PostgreSQL 연결
    try:
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        logger.info(f"✅ Connected to PostgreSQL: {settings.DATABASE_NAME}")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)

    try:
        # SQL 파일 읽기
        sql_file = Path(__file__).parent / "init_guardian_tables.sql"

        if not sql_file.exists():
            logger.error(f"❌ SQL file not found: {sql_file}")
            sys.exit(1)

        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        # SQL 실행
        await conn.execute(sql)

        logger.info("=" * 60)
        logger.info("✅ 보호자 테이블 초기화 완료!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("생성된 테이블:")
        logger.info("  - guardians (보호자 정보)")
        logger.info("  - user_guardians (사용자-보호자 연결)")
        logger.info("  - notification_logs (알림 전송 로그)")
        logger.info("")
        logger.info("샘플 데이터:")
        logger.info("  - 보호자 2명 (홍길동, 김영희)")
        logger.info("  - 테스트 사용자 연결 (test_user)")

    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await conn.close()
        logger.info("✅ Database connection closed")


if __name__ == "__main__":
    asyncio.run(create_guardian_tables())
