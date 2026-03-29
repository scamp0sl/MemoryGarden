"""
TimescaleDB 초기화 스크립트

analysis_timeseries 테이블을 Hypertable로 변환하고
성능 최적화를 위한 인덱스와 Continuous Aggregate를 설정합니다.

Usage:
    python scripts/init_timescale.py

실행 조건:
    - PostgreSQL에 TimescaleDB 확장이 설치되어 있어야 함
    - analysis_timeseries 테이블이 존재해야 함 (alembic migrate 후 실행)
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

TABLE_NAME = "analysis_timeseries"
TIME_COLUMN = "timestamp"
CHUNK_INTERVAL = "7 days"  # 주 단위 청크


async def ensure_timescaledb_extension(conn: asyncpg.Connection):
    """TimescaleDB 확장 활성화"""
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        version = await conn.fetchval(
            "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';"
        )
        logger.info(f"✅ TimescaleDB 확장 활성화: v{version}")
    except Exception as e:
        logger.error(f"❌ TimescaleDB 확장 활성화 실패: {e}")
        raise


async def convert_to_hypertable(conn: asyncpg.Connection):
    """
    analysis_timeseries를 Hypertable로 변환

    - 이미 hypertable이면 스킵
    - migrate_data=TRUE로 기존 데이터 보존
    - 복합 PK (user_id, timestamp) 유지
    """
    # 이미 hypertable인지 확인
    is_hypertable = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM timescaledb_information.hypertables
            WHERE hypertable_name = $1
        );
        """,
        TABLE_NAME
    )

    if is_hypertable:
        logger.info(f"✅ {TABLE_NAME}는 이미 hypertable입니다")
        return

    # 테이블 존재 확인
    table_exists = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = $1
        );
        """,
        TABLE_NAME
    )

    if not table_exists:
        logger.error(f"❌ {TABLE_NAME} 테이블이 없습니다. 먼저 alembic upgrade head 실행 필요")
        raise RuntimeError(f"{TABLE_NAME} table not found")

    try:
        # Hypertable 변환 (기존 데이터 보존)
        await conn.execute(
            f"""
            SELECT create_hypertable(
                '{TABLE_NAME}',
                '{TIME_COLUMN}',
                chunk_time_interval => INTERVAL '{CHUNK_INTERVAL}',
                migrate_data => TRUE,
                if_not_exists => TRUE
            );
            """
        )
        logger.info(f"✅ {TABLE_NAME} → Hypertable 변환 완료 (chunk: {CHUNK_INTERVAL})")
    except Exception as e:
        logger.error(f"❌ Hypertable 변환 실패: {e}")
        raise


async def create_indexes(conn: asyncpg.Connection):
    """
    성능 최적화 인덱스 생성

    Indexes:
        1. idx_timeseries_user_ts: user_id + timestamp DESC (사용자별 최근 조회)
        2. idx_timeseries_risk_ts: risk_level + timestamp DESC (위험도별 통계)
    """
    index_definitions = [
        (
            "idx_timeseries_user_ts",
            f"CREATE INDEX IF NOT EXISTS idx_timeseries_user_ts "
            f"ON {TABLE_NAME} (user_id, {TIME_COLUMN} DESC);"
        ),
        (
            "idx_timeseries_risk_ts",
            f"CREATE INDEX IF NOT EXISTS idx_timeseries_risk_ts "
            f"ON {TABLE_NAME} (risk_level, {TIME_COLUMN} DESC);"
        ),
    ]

    for idx_name, ddl in index_definitions:
        try:
            await conn.execute(ddl)
            logger.info(f"✅ 인덱스 생성: {idx_name}")
        except Exception as e:
            logger.warning(f"⚠️ 인덱스 생성 실패 (무시): {idx_name} - {e}")


async def create_continuous_aggregates(conn: asyncpg.Connection):
    """
    Continuous Aggregate 뷰 생성 (일일 평균 MCDI)

    - mcdi_daily_avg: 일별 사용자 평균 MCDI + 6개 지표
    - 1시간마다 자동 갱신
    """
    view_name = "mcdi_daily_avg"

    # 이미 존재하는지 확인
    exists = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM timescaledb_information.continuous_aggregates
            WHERE view_name = $1
        );
        """,
        view_name
    )

    if exists:
        logger.info(f"✅ {view_name} Continuous Aggregate 이미 존재")
        return

    try:
        await conn.execute(
            f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name}
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 day', {TIME_COLUMN}) AS bucket,
                user_id,
                AVG(mcdi_score)  AS avg_mcdi,
                AVG(lr_score)    AS avg_lr,
                AVG(sd_score)    AS avg_sd,
                AVG(nc_score)    AS avg_nc,
                AVG(to_score)    AS avg_to,
                AVG(er_score)    AS avg_er,
                AVG(rt_score)    AS avg_rt,
                COUNT(*)         AS data_points,
                MAX(mcdi_score)  AS max_mcdi,
                MIN(mcdi_score)  AS min_mcdi
            FROM {TABLE_NAME}
            GROUP BY bucket, user_id
            WITH NO DATA;
            """
        )
        logger.info(f"✅ Continuous Aggregate 생성: {view_name}")

        # Refresh Policy 설정 (1시간마다 자동 갱신)
        await conn.execute(
            f"""
            SELECT add_continuous_aggregate_policy(
                '{view_name}',
                start_offset => INTERVAL '3 days',
                end_offset   => INTERVAL '1 hour',
                schedule_interval => INTERVAL '1 hour',
                if_not_exists => TRUE
            );
            """
        )
        logger.info(f"✅ Refresh Policy 등록: {view_name} (1시간 주기)")

    except Exception as e:
        logger.warning(f"⚠️ Continuous Aggregate 생성 실패 (선택 사항, 무시): {e}")


async def setup_retention_policy(conn: asyncpg.Connection, days: int = 365):
    """
    데이터 보존 정책 설정 (1년 후 자동 삭제)

    SPEC: 개인정보보호법 준수 (수집 목적 달성 시 삭제)
    """
    try:
        await conn.execute(
            f"""
            SELECT add_retention_policy(
                '{TABLE_NAME}',
                INTERVAL '{days} days',
                if_not_exists => TRUE
            );
            """
        )
        logger.info(f"✅ Retention Policy 설정: {days}일 후 자동 삭제")
    except Exception as e:
        logger.warning(f"⚠️ Retention Policy 설정 실패 (무시): {e}")


async def verify_setup(conn: asyncpg.Connection):
    """설정 검증"""
    print("\n" + "=" * 50)
    print("  검증 결과")
    print("=" * 50)

    # 1. TimescaleDB 버전
    version = await conn.fetchval(
        "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';"
    )
    print(f"  TimescaleDB: v{version}")

    # 2. Hypertable 확인
    ht = await conn.fetchrow(
        """
        SELECT hypertable_name, num_dimensions, num_chunks
        FROM timescaledb_information.hypertables
        WHERE hypertable_name = $1;
        """,
        TABLE_NAME
    )
    if ht:
        print(f"  Hypertable: ✅ {ht['hypertable_name']} "
              f"(dimensions={ht['num_dimensions']}, chunks={ht['num_chunks']})")
    else:
        print(f"  Hypertable: ❌ NOT FOUND")

    # 3. 인덱스 목록
    indexes = await conn.fetch(
        "SELECT indexname FROM pg_indexes WHERE tablename = $1 ORDER BY indexname;",
        TABLE_NAME
    )
    print(f"  인덱스: {[r['indexname'] for r in indexes]}")

    # 4. Continuous Aggregate
    agg = await conn.fetchval(
        """
        SELECT COUNT(*) FROM timescaledb_information.continuous_aggregates
        WHERE view_schema = 'public';
        """
    )
    print(f"  Continuous Aggregates: {agg}개")

    # 5. 현재 데이터 수
    count = await conn.fetchval(
        f"SELECT COUNT(*) FROM {TABLE_NAME};"
    )
    print(f"  현재 레코드 수: {count}개")
    print("=" * 50 + "\n")


async def main():
    """TimescaleDB 초기화 메인"""
    print("\n" + "=" * 50)
    print("  TimescaleDB 초기화 시작")
    print("=" * 50 + "\n")

    try:
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        logger.info(f"✅ PostgreSQL 연결: {settings.DATABASE_NAME}")
    except Exception as e:
        logger.error(f"❌ DB 연결 실패: {e}")
        sys.exit(1)

    try:
        await ensure_timescaledb_extension(conn)
        await convert_to_hypertable(conn)
        await create_indexes(conn)
        await create_continuous_aggregates(conn)
        await setup_retention_policy(conn, days=365)
        await verify_setup(conn)

        print("✅ TimescaleDB 초기화 완료!\n")

    except Exception as e:
        logger.error(f"❌ 초기화 실패: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
