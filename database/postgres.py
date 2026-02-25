"""
PostgreSQL 데이터베이스 연결 설정

SQLAlchemy async engine 및 session 관리.
FastAPI dependency injection용 get_db() 제공.

Author: Memory Garden Team
Created: 2025-01-15
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import AsyncGenerator

# ============================================
# 2. Third-Party Imports
# ============================================
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import event

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
# PostgreSQL URL을 asyncpg용으로 변환
# postgresql:// → postgresql+asyncpg://
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://",
    "postgresql+asyncpg://"
)

# ============================================
# 6. Engine 설정
# ============================================

def create_engine_with_settings() -> AsyncEngine:
    """
    SQLAlchemy async engine 생성

    Returns:
        AsyncEngine: 비동기 데이터베이스 엔진

    Notes:
        - echo: 개발 환경에서만 쿼리 로깅
        - pool_pre_ping: 연결 유효성 자동 체크
        - pool_size: 기본 연결 풀 크기
        - max_overflow: 추가 연결 허용 수

    Example:
        >>> engine = create_engine_with_settings()
        >>> async with engine.begin() as conn:
        ...     await conn.execute(text("SELECT 1"))
    """
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DEBUG,  # 개발 모드에서만 쿼리 로깅
        pool_pre_ping=True,  # 연결 유효성 자동 체크
        pool_size=10,  # 기본 연결 풀 크기
        max_overflow=20,  # 추가 연결 허용
        pool_recycle=3600,  # 1시간마다 연결 재생성
        # 테스트 환경에서는 NullPool 사용 (연결 재사용 안 함)
        poolclass=NullPool if settings.APP_ENV == "test" else None,
    )

    logger.info(
        f"Database engine created",
        extra={
            "database_url": DATABASE_URL.split("@")[-1],  # 비밀번호 제외
            "pool_size": 10,
            "echo": settings.DEBUG
        }
    )

    return engine


# 전역 engine 인스턴스
engine: AsyncEngine = create_engine_with_settings()


# ============================================
# 7. Session Factory
# ============================================

# async_sessionmaker: SQLAlchemy 2.0 스타일
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 커밋 후에도 객체 사용 가능
    autoflush=False,  # 자동 flush 비활성화 (명시적 제어)
    autocommit=False,  # 자동 커밋 비활성화
)

logger.info("AsyncSessionLocal factory created")


# ============================================
# 8. Dependency Injection (FastAPI)
# ============================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency용 DB 세션 생성 함수

    Yields:
        AsyncSession: 비동기 데이터베이스 세션

    Raises:
        Exception: 세션 생성 실패 시

    Example:
        ```python
        from fastapi import Depends

        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
        ```

    Notes:
        - yield 패턴으로 세션 생명주기 관리
        - 요청 종료 시 자동으로 세션 종료
        - 에러 발생 시에도 정상적으로 세션 종료 보장
    """
    async with AsyncSessionLocal() as session:
        try:
            logger.debug("Database session created")
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}", exc_info=True)
            await session.rollback()
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")


# ============================================
# 9. Health Check
# ============================================

async def check_database_connection() -> bool:
    """
    데이터베이스 연결 상태 확인

    Returns:
        bool: 연결 성공 여부

    Example:
        >>> is_healthy = await check_database_connection()
        >>> print(f"Database healthy: {is_healthy}")
        Database healthy: True
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            logger.info("Database connection check: OK")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}", exc_info=True)
        return False


# ============================================
# 10. Lifecycle Management
# ============================================

async def init_db() -> None:
    """
    데이터베이스 초기화 (애플리케이션 시작 시)

    - 연결 테스트
    - 필요 시 확장 기능 설치 (TimescaleDB 등)

    Raises:
        Exception: 초기화 실패 시
    """
    try:
        logger.info("Initializing database connection...")

        # 연결 테스트
        is_connected = await check_database_connection()

        if not is_connected:
            raise Exception("Failed to connect to database")

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.critical(f"Database initialization failed: {e}", exc_info=True)
        raise


async def close_db() -> None:
    """
    데이터베이스 연결 종료 (애플리케이션 종료 시)

    - 모든 활성 연결 종료
    - 연결 풀 정리
    """
    try:
        logger.info("Closing database connections...")

        await engine.dispose()

        logger.info("Database connections closed successfully")

    except Exception as e:
        logger.error(f"Error closing database connections: {e}", exc_info=True)
        raise


# ============================================
# 11. Event Listeners (선택적)
# ============================================

@event.listens_for(engine.sync_engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    """
    PostgreSQL 스키마 설정 (필요 시)

    Args:
        dbapi_connection: DB-API 연결 객체
        connection_record: SQLAlchemy 연결 레코드

    Notes:
        - 기본 스키마를 public 대신 다른 스키마로 설정 가능
        - 현재는 주석 처리 (필요 시 활성화)
    """
    # 예: mg_schm 스키마 사용 시
    cursor = dbapi_connection.cursor()
    cursor.execute("SET search_path TO mg_schm, public")
    cursor.close()
    pass


# ============================================
# 12. Export
# ============================================
__all__ = [
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "check_database_connection",
    "init_db",
    "close_db",
]
