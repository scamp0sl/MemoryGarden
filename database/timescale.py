"""
TimescaleDB 클라이언트

MCDI 시계열 데이터 저장/조회 및 통계 계산
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json

import asyncpg
import numpy as np

from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import DatabaseError

logger = get_logger(__name__)


# ============================================
# 데이터 모델
# ============================================

@dataclass
class MCDIScore:
    """MCDI 점수 레코드"""

    timestamp: datetime
    user_id: str
    mcdi_score: float
    lr_score: Optional[float] = None
    sd_score: Optional[float] = None
    nc_score: Optional[float] = None
    to_score: Optional[float] = None
    er_score: Optional[float] = None
    rt_score: Optional[float] = None
    risk_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "mcdi_score": self.mcdi_score,
            "lr_score": self.lr_score,
            "sd_score": self.sd_score,
            "nc_score": self.nc_score,
            "to_score": self.to_score,
            "er_score": self.er_score,
            "rt_score": self.rt_score,
            "risk_level": self.risk_level
        }


@dataclass
class BaselineStats:
    """Baseline 통계"""

    mean: float
    std: float
    sample_size: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "mean": self.mean,
            "std": self.std,
            "sample_size": self.sample_size,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None
        }


# ============================================
# TimescaleDB 클라이언트
# ============================================

class TimescaleDB:
    """TimescaleDB 클라이언트"""

    def __init__(self, pool: asyncpg.Pool = None):
        """
        Args:
            pool: asyncpg connection pool (optional)
        """
        self.pool = pool
        self._own_pool = False

    async def connect(self):
        """연결 풀 생성"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    host=settings.DATABASE_HOST,
                    port=settings.DATABASE_PORT,
                    user=settings.DATABASE_USER,
                    password=settings.DATABASE_PASSWORD,
                    database=settings.DATABASE_NAME,
                    min_size=2,
                    max_size=10,
                    command_timeout=30
                )
                self._own_pool = True
                logger.info("✅ TimescaleDB connection pool created")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise DatabaseError(f"TimescaleDB connection failed: {e}") from e

    async def close(self):
        """연결 풀 종료"""
        if self.pool and self._own_pool:
            await self.pool.close()
            logger.info("✅ TimescaleDB connection pool closed")

    async def __aenter__(self):
        """Async context manager 진입"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager 종료"""
        await self.close()

    # ============================================
    # MCDI 점수 저장
    # ============================================

    async def store_mcdi(
        self,
        user_id: str,
        mcdi_score: float,
        scores: Dict[str, float],
        risk_level: str = "GREEN",
        metadata: Dict = None,
        timestamp: datetime = None
    ):
        """
        MCDI 점수 저장

        Args:
            user_id: 사용자 ID
            mcdi_score: MCDI 종합 점수
            scores: 개별 지표 점수 {"LR": 78.5, "SD": 82.3, ...}
            risk_level: 위험도 (GREEN/YELLOW/ORANGE/RED)
            metadata: 추가 정보 (실패 지표, 모순 등)
            timestamp: 기록 시각 (None이면 현재 시각)

        Returns:
            None

        Raises:
            DatabaseError: 저장 실패 시

        Example:
            >>> await timescale.store_mcdi(
            ...     user_id="user_123",
            ...     mcdi_score=78.5,
            ...     scores={"LR": 78.5, "SD": 82.3, "NC": 75.0},
            ...     risk_level="GREEN"
            ... )
        """
        if not self.pool:
            await self.connect()

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO analysis_timeseries (
                        timestamp, user_id, mcdi_score,
                        lr_score, sd_score, nc_score,
                        to_score, er_score, rt_score,
                        risk_level
                    ) VALUES (
                        COALESCE($1, NOW()), $2, $3, $4, $5, $6, $7, $8, $9, $10
                    )
                    """,
                    timestamp or datetime.now(),
                    user_id,
                    mcdi_score,
                    scores.get("LR"),
                    scores.get("SD"),
                    scores.get("NC"),
                    scores.get("TO"),
                    scores.get("ER"),
                    scores.get("RT"),
                    risk_level
                )

            logger.info(
                f"MCDI stored",
                extra={
                    "user_id": user_id,
                    "mcdi_score": mcdi_score,
                    "risk_level": risk_level
                }
            )

        except Exception as e:
            logger.error(f"Failed to store MCDI: {e}", exc_info=True)
            raise DatabaseError(f"MCDI storage failed: {e}") from e

    # ============================================
    # 최근 점수 조회
    # ============================================

    async def get_recent_scores(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[MCDIScore]:
        """
        최근 N일 점수 조회

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (일)
            limit: 최대 레코드 수

        Returns:
            MCDIScore 리스트 (최신순)

        Example:
            >>> scores = await timescale.get_recent_scores("user_123", days=30)
            >>> print(len(scores))
            25
        """
        if not self.pool:
            await self.connect()

        try:
            # cutoff_time 계산
            cutoff_time = datetime.now() - timedelta(days=days)

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        timestamp, user_id, mcdi_score,
                        lr_score, sd_score, nc_score,
                        to_score, er_score, rt_score,
                        risk_level
                    FROM analysis_timeseries
                    WHERE user_id = $1
                      AND timestamp >= $2
                    ORDER BY timestamp DESC
                    LIMIT $3
                    """,
                    user_id,
                    cutoff_time,
                    limit
                )

            scores = [MCDIScore(**dict(row)) for row in rows]
            logger.debug(
                f"Retrieved {len(scores)} scores for user {user_id} (last {days} days)"
            )

            return scores

        except Exception as e:
            logger.error(f"Failed to get recent scores: {e}", exc_info=True)
            raise DatabaseError(f"Score retrieval failed: {e}") from e

    # ============================================
    # Baseline 통계 계산
    # ============================================

    async def get_baseline(
        self,
        user_id: str,
        days: int = 90
    ) -> BaselineStats:
        """
        Baseline 통계 계산

        최근 N일 데이터의 평균, 표준편차, 샘플 개수를 계산합니다.

        Args:
            user_id: 사용자 ID
            days: Baseline 계산 기간 (기본 90일)

        Returns:
            BaselineStats 객체

        Example:
            >>> baseline = await timescale.get_baseline("user_123", days=90)
            >>> print(f"Mean: {baseline.mean:.2f}, Std: {baseline.std:.2f}")
            Mean: 78.50, Std: 5.23
        """
        if not self.pool:
            await self.connect()

        try:
            # cutoff_time 계산
            cutoff_time = datetime.now() - timedelta(days=days)

            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        AVG(mcdi_score) AS mean,
                        STDDEV(mcdi_score) AS std,
                        COUNT(*) AS sample_size,
                        MIN(timestamp) AS start_date,
                        MAX(timestamp) AS end_date
                    FROM analysis_timeseries
                    WHERE user_id = $1
                      AND timestamp >= $2
                    """,
                    user_id,
                    cutoff_time
                )

            # 데이터가 없으면 기본값 반환
            if row["sample_size"] == 0:
                logger.warning(f"No baseline data for user {user_id}")
                return BaselineStats(
                    mean=80.0,  # 기본 평균
                    std=10.0,   # 기본 표준편차
                    sample_size=0
                )

            # 표준편차가 None이면 (데이터 1개) 기본값
            std = row["std"] if row["std"] is not None else 10.0

            baseline = BaselineStats(
                mean=float(row["mean"]),
                std=float(std),
                sample_size=int(row["sample_size"]),
                start_date=row["start_date"],
                end_date=row["end_date"]
            )

            logger.info(
                f"Baseline calculated",
                extra={
                    "user_id": user_id,
                    "mean": baseline.mean,
                    "std": baseline.std,
                    "sample_size": baseline.sample_size,
                    "days": days
                }
            )

            return baseline

        except Exception as e:
            logger.error(f"Failed to calculate baseline: {e}", exc_info=True)
            raise DatabaseError(f"Baseline calculation failed: {e}") from e

    # ============================================
    # 기울기 계산 (Linear Regression)
    # ============================================

    async def calculate_slope(
        self,
        user_id: str,
        weeks: int = 4
    ) -> Tuple[float, str]:
        """
        기울기 계산 (Linear Regression)

        최근 N주 데이터에 선형 회귀를 적용하여 주당 점수 변화량을 계산합니다.

        Args:
            user_id: 사용자 ID
            weeks: 분석 기간 (주)

        Returns:
            (slope, direction) 튜플
            - slope: 주당 점수 변화량 (양수: 상승, 음수: 하락)
            - direction: "increasing" | "stable" | "decreasing"

        Example:
            >>> slope, direction = await timescale.calculate_slope("user_123", weeks=4)
            >>> print(f"Slope: {slope:.2f}/week, Direction: {direction}")
            Slope: -1.23/week, Direction: decreasing
        """
        if not self.pool:
            await self.connect()

        try:
            # cutoff_time 계산 (weeks → days)
            cutoff_time = datetime.now() - timedelta(weeks=weeks)

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        EXTRACT(EPOCH FROM timestamp) AS x,
                        mcdi_score AS y
                    FROM analysis_timeseries
                    WHERE user_id = $1
                      AND timestamp >= $2
                    ORDER BY timestamp
                    """,
                    user_id,
                    cutoff_time
                )

            # 데이터가 부족하면 0 반환
            if len(rows) < 2:
                logger.warning(
                    f"Insufficient data for slope calculation: {len(rows)} points (need 2+)"
                )
                return 0.0, "stable"

            # 데이터 추출
            x = np.array([float(row["x"]) for row in rows])
            y = np.array([float(row["y"]) for row in rows])

            # 최소자승법 (Least Squares)
            n = len(x)
            slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / \
                    (n * np.sum(x ** 2) - np.sum(x) ** 2)

            # 초당 기울기 → 주당 기울기로 변환 (7일 * 24시간 * 3600초)
            slope_per_week = slope * (7 * 24 * 3600)

            # 방향 판정
            if slope_per_week < -0.5:
                direction = "decreasing"
            elif slope_per_week > 0.5:
                direction = "increasing"
            else:
                direction = "stable"

            logger.info(
                f"Slope calculated",
                extra={
                    "user_id": user_id,
                    "slope": slope_per_week,
                    "direction": direction,
                    "data_points": n,
                    "weeks": weeks
                }
            )

            return round(slope_per_week, 3), direction

        except Exception as e:
            logger.error(f"Failed to calculate slope: {e}", exc_info=True)
            raise DatabaseError(f"Slope calculation failed: {e}") from e

    # ============================================
    # 시계열 데이터 조회 (그래프용)
    # ============================================

    async def get_timeseries(
        self,
        user_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
        metric: str = "mcdi_score"
    ) -> List[Dict[str, Any]]:
        """
        시계열 데이터 조회 (그래프용)

        Args:
            user_id: 사용자 ID
            start_date: 시작일 (None이면 30일 전)
            end_date: 종료일 (None이면 현재)
            metric: 조회 지표 (mcdi_score, lr_score, ...)

        Returns:
            시계열 데이터 리스트 [{"time": "2025-01-01T10:00:00", "value": 78.5}, ...]

        Example:
            >>> data = await timescale.get_timeseries("user_123", metric="mcdi_score")
            >>> for point in data:
            ...     print(f"{point['time']}: {point['value']}")
        """
        if not self.pool:
            await self.connect()

        # 기본값 설정
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        # 허용된 지표 확인
        allowed_metrics = [
            "mcdi_score", "lr_score", "sd_score", "nc_score",
            "to_score", "er_score", "rt_score"
        ]
        if metric not in allowed_metrics:
            raise ValueError(f"Invalid metric: {metric}. Allowed: {allowed_metrics}")

        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT
                        timestamp,
                        {metric} AS value
                    FROM analysis_timeseries
                    WHERE user_id = $1
                      AND timestamp >= $2
                      AND timestamp <= $3
                      AND {metric} IS NOT NULL
                    ORDER BY timestamp
                """

                rows = await conn.fetch(query, user_id, start_date, end_date)

            data = [
                {"timestamp": row["timestamp"].isoformat(), "value": float(row["value"])}
                for row in rows
            ]

            logger.debug(
                f"Retrieved {len(data)} timeseries points for {metric}"
            )

            return data

        except Exception as e:
            logger.error(f"Failed to get timeseries: {e}", exc_info=True)
            raise DatabaseError(f"Timeseries retrieval failed: {e}") from e

    # ============================================
    # 집계 통계 조회
    # ============================================

    async def get_aggregate_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        집계 통계 조회

        최근 N일 데이터의 평균, 최소, 최대, 중앙값을 계산합니다.

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (일)

        Returns:
            집계 통계 딕셔너리
            {
                "mcdi": {"mean": 78.5, "min": 65.0, "max": 85.0, "median": 80.0},
                "lr": {...},
                "risk_distribution": {"GREEN": 20, "YELLOW": 5, ...}
            }
        """
        if not self.pool:
            await self.connect()

        try:
            # cutoff_time 계산
            cutoff_time = datetime.now() - timedelta(days=days)

            async with self.pool.acquire() as conn:
                # 1. 지표별 통계
                row = await conn.fetchrow(
                    """
                    SELECT
                        AVG(mcdi_score) AS mcdi_mean,
                        MIN(mcdi_score) AS mcdi_min,
                        MAX(mcdi_score) AS mcdi_max,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY mcdi_score) AS mcdi_median,
                        AVG(lr_score) AS lr_mean,
                        AVG(sd_score) AS sd_mean,
                        AVG(nc_score) AS nc_mean,
                        AVG(to_score) AS to_mean,
                        AVG(er_score) AS er_mean,
                        AVG(rt_score) AS rt_mean
                    FROM analysis_timeseries
                    WHERE user_id = $1
                      AND timestamp >= $2
                    """,
                    user_id,
                    cutoff_time
                )

                # 2. 위험도 분포
                risk_rows = await conn.fetch(
                    """
                    SELECT risk_level, COUNT(*) AS count
                    FROM analysis_timeseries
                    WHERE user_id = $1
                      AND timestamp >= $2
                    GROUP BY risk_level
                    """,
                    user_id,
                    cutoff_time
                )

                risk_distribution = {
                    row["risk_level"]: int(row["count"])
                    for row in risk_rows
                }

            stats = {
                "mcdi": {
                    "mean": round(float(row["mcdi_mean"] or 0), 2),
                    "min": round(float(row["mcdi_min"] or 0), 2),
                    "max": round(float(row["mcdi_max"] or 0), 2),
                    "median": round(float(row["mcdi_median"] or 0), 2)
                },
                "lr": {"mean": round(float(row["lr_mean"] or 0), 2)},
                "sd": {"mean": round(float(row["sd_mean"] or 0), 2)},
                "nc": {"mean": round(float(row["nc_mean"] or 0), 2)},
                "to": {"mean": round(float(row["to_mean"] or 0), 2)},
                "er": {"mean": round(float(row["er_mean"] or 0), 2)},
                "rt": {"mean": round(float(row["rt_mean"] or 0), 2)},
                "risk_distribution": risk_distribution
            }

            logger.debug(f"Aggregate stats calculated for user {user_id}")

            return stats

        except Exception as e:
            logger.error(f"Failed to get aggregate stats: {e}", exc_info=True)
            raise DatabaseError(f"Aggregate stats retrieval failed: {e}") from e

    # ============================================
    # 어댑티브 대화 지원 메서드 (B3-1)
    # ============================================

    async def get_latest_mcdi(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        최신 MCDI 분석 결과 조회 (어댑티브 대화용)

        가장 최근 MCDI 점수와 6개 지표 점수를 반환합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            최신 MCDI 데이터 또는 None
            {
                "mcdi_score": 78.5,
                "risk_level": "GREEN",
                "lr_score": 80.0,
                "sd_score": 75.0,
                "nc_score": 82.0,
                "to_score": 78.0,
                "er_score": 76.0,
                "rt_score": 70.0,
                "timestamp": "2025-03-26T10:30:00"
            }
            또는 None (데이터 없음)

        Example:
            >>> latest = await timescale.get_latest_mcdi("user_123")
            >>> if latest:
            ...     print(f"Risk: {latest['risk_level']}, Score: {latest['mcdi_score']}")
        """
        if not self.pool:
            await self.connect()

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        mcdi_score,
                        risk_level,
                        lr_score, sd_score, nc_score,
                        to_score, er_score, rt_score,
                        timestamp
                    FROM analysis_timeseries
                    WHERE user_id = $1
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    user_id
                )

            if row is None:
                logger.debug(f"No MCDI data found for user {user_id}")
                return None

            return {
                "mcdi_score": float(row["mcdi_score"]) if row["mcdi_score"] else None,
                "risk_level": row["risk_level"] or "GREEN",
                "lr_score": float(row["lr_score"]) if row["lr_score"] else None,
                "sd_score": float(row["sd_score"]) if row["sd_score"] else None,
                "nc_score": float(row["nc_score"]) if row["nc_score"] else None,
                "to_score": float(row["to_score"]) if row["to_score"] else None,
                "er_score": float(row["er_score"]) if row["er_score"] else None,
                "rt_score": float(row["rt_score"]) if row["rt_score"] else None,
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None
            }

        except Exception as e:
            logger.warning(f"Failed to get latest MCDI for {user_id}: {e}")
            return None

    async def get_mcdi_history(
        self,
        user_id: str,
        days: int = 14
    ) -> List[Dict[str, Any]]:
        """
        MCDI 점수 히스토리 조회 (추이 분석용)

        최근 N일간의 MCDI 점수 목록을 시간 순서대로 반환합니다.

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (일)

        Returns:
            MCDI 히스토리 리스트 (오래된 순)
            [
                {"mcdi_score": 80.0, "timestamp": "2025-03-12T10:00:00"},
                {"mcdi_score": 78.5, "timestamp": "2025-03-13T10:00:00"},
                ...
            ]

        Example:
            >>> history = await timescale.get_mcdi_history("user_123", days=14)
            >>> scores = [h["mcdi_score"] for h in history]
        """
        if not self.pool:
            await self.connect()

        try:
            cutoff_time = datetime.now() - timedelta(days=days)

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        mcdi_score,
                        timestamp
                    FROM analysis_timeseries
                    WHERE user_id = $1
                      AND timestamp >= $2
                      AND mcdi_score IS NOT NULL
                    ORDER BY timestamp ASC
                    """,
                    user_id,
                    cutoff_time
                )

            history = [
                {
                    "mcdi_score": float(row["mcdi_score"]),
                    "timestamp": row["timestamp"].isoformat()
                }
                for row in rows
            ]

            logger.debug(
                f"Retrieved {len(history)} MCDI history points for user {user_id}"
            )

            return history

        except Exception as e:
            logger.warning(f"Failed to get MCDI history for {user_id}: {e}")
            return []


# ============================================
# 싱글톤 인스턴스
# ============================================

_timescale_instance: Optional[TimescaleDB] = None


async def get_timescale() -> TimescaleDB:
    """
    TimescaleDB 싱글톤 인스턴스 가져오기

    Returns:
        TimescaleDB 인스턴스

    Example:
        >>> timescale = await get_timescale()
        >>> await timescale.store_mcdi(...)
    """
    global _timescale_instance

    if _timescale_instance is None:
        _timescale_instance = TimescaleDB()
        await _timescale_instance.connect()

    return _timescale_instance
