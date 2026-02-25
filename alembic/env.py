"""
Alembic 마이그레이션 환경 설정

동기 SQLAlchemy 엔진 사용 (Alembic 표준).
config/settings.py에서 DATABASE_URL 읽기.

Author: Memory Garden Team
Created: 2025-01-15
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import sys
from logging.config import fileConfig
from pathlib import Path

# ============================================
# 2. Third-Party Imports
# ============================================
from sqlalchemy import engine_from_config, pool
from alembic import context

# ============================================
# 3. 프로젝트 루트를 sys.path에 추가
# ============================================
# alembic이 실행되는 위치에 관계없이 models import 가능하도록
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ============================================
# 4. Local Imports
# ============================================
from config.settings import settings
from models import Base  # 모든 모델이 포함된 Base

# ============================================
# 5. Alembic Config
# ============================================
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================
# 6. MetaData 설정 (autogenerate 지원)
# ============================================
target_metadata = Base.metadata

# ============================================
# 7. DATABASE_URL 설정
# ============================================
# config/settings.py에서 DATABASE_URL 읽기
# Alembic은 동기 마이그레이션이므로 postgresql:// 형식 사용
database_url = settings.DATABASE_URL

# asyncpg가 포함되어 있으면 제거 (Alembic은 psycopg2 사용)
if "+asyncpg" in database_url:
    database_url = database_url.replace("+asyncpg", "")

# alembic.ini의 sqlalchemy.url 덮어쓰기
config.set_main_option("sqlalchemy.url", database_url)


# ============================================
# 8. Offline Migration
# ============================================
def run_migrations_offline() -> None:
    """
    Offline 모드에서 마이그레이션 실행

    - URL만 사용 (Engine 생성 안 함)
    - SQL 파일 생성용
    - DBAPI 불필요

    Example:
        ```bash
        alembic upgrade head --sql > migration.sql
        ```
    """
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # PostgreSQL 특정 설정
        compare_type=True,  # 타입 변경 감지
        compare_server_default=True,  # 기본값 변경 감지
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================
# 9. Online Migration (동기)
# ============================================
def run_migrations_online() -> None:
    """
    Online 모드에서 마이그레이션 실행

    - 동기 엔진 사용 (psycopg2)
    - 실제 DB 연결

    Example:
        ```bash
        alembic upgrade head
        alembic downgrade -1
        alembic revision --autogenerate -m "Add new table"
        ```
    """
    # Alembic config를 SQLAlchemy 엔진 설정으로 변환
    configuration = config.get_section(config.config_ini_section, {})

    # 동기 엔진 생성
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # 마이그레이션에서는 연결 풀 불필요
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # PostgreSQL 특정 설정
            compare_type=True,
            compare_server_default=True,
            # Include schemas (필요 시)
            # include_schemas=True,
            # version_table_schema="mg_schm",  # 스키마 지정
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================
# 10. Main Execution
# ============================================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
