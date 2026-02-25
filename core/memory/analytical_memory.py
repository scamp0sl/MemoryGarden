"""
분석 메모리 (Layer 4)

MCDI 시계열 데이터 저장 및 통계 분석.
TimescaleDB 기반.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from database.timescale import TimescaleDB, MCDIScore, BaselineStats
from utils.logger import get_logger
from utils.exceptions import MemoryError

logger = get_logger(__name__)


class AnalyticalMemory:
    """
    분석 메모리 Layer 4

    기능:
        - MCDI 점수 시계열 저장
        - Baseline 통계 계산
        - 추세 분석 (기울기)
        - 시계열 데이터 조회
    """

    def __init__(self, timescale: TimescaleDB):
        """
        Args:
            timescale: TimescaleDB 클라이언트
        """
        self.timescale = timescale

    # ============================================
    # 저장 (Store)
    # ============================================

    async def store(
        self,
        user_id: str,
        analysis: Dict[str, Any]
    ):
        """
        분석 결과 저장

        Args:
            user_id: 사용자 ID
            analysis: 분석 결과
                {
                    "mcdi_score": 78.5,
                    "scores": {"LR": 78.5, "SD": 82.3, ...},
                    "risk_level": "GREEN",
                    "contradictions": [...],
                    "failed_metrics": [...]
                }

        Returns:
            None

        Raises:
            MemoryError: 저장 실패 시

        Example:
            >>> await analytical.store(
            ...     user_id="user_123",
            ...     analysis={
            ...         "mcdi_score": 78.5,
            ...         "scores": {"LR": 78.5, "SD": 82.3},
            ...         "risk_level": "GREEN"
            ...     }
            ... )
        """
        try:
            # MCDI 점수 저장
            await self.timescale.store_mcdi(
                user_id=user_id,
                mcdi_score=analysis["mcdi_score"],
                scores=analysis["scores"],
                risk_level=analysis.get("risk_level", "GREEN"),
                metadata={
                    "contradictions": analysis.get("contradictions", []),
                    "failed_metrics": analysis.get("failed_metrics", []),
                    "reliability": analysis.get("reliability", 1.0)
                }
            )

            logger.info(
                f"Analysis stored in Layer 4",
                extra={
                    "user_id": user_id,
                    "mcdi_score": analysis["mcdi_score"],
                    "risk_level": analysis.get("risk_level")
                }
            )

        except Exception as e:
            logger.error(f"Failed to store analysis: {e}", exc_info=True)
            raise MemoryError(f"Analytical memory storage failed: {e}") from e

    # ============================================
    # 조회 (Retrieve)
    # ============================================

    async def retrieve(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        최근 분석 결과 조회

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (일)

        Returns:
            {
                "recent_scores": [...],
                "baseline": {...},
                "slope": -0.5,
                "trend": "decreasing",
                "stats": {...}
            }

        Example:
            >>> data = await analytical.retrieve("user_123", days=30)
            >>> print(data["baseline"]["mean"])
            78.5
        """
        try:
            # 1. 최근 점수 조회
            scores = await self.timescale.get_recent_scores(
                user_id=user_id,
                days=days
            )

            # 2. Baseline 통계
            baseline = await self.timescale.get_baseline(
                user_id=user_id,
                days=90  # Baseline은 90일 기준
            )

            # 3. 4주 기울기
            slope, trend = await self.timescale.calculate_slope(
                user_id=user_id,
                weeks=4
            )

            # 4. 집계 통계
            stats = await self.timescale.get_aggregate_stats(
                user_id=user_id,
                days=days
            )

            return {
                "recent_scores": [score.to_dict() for score in scores],
                "baseline": baseline.to_dict(),
                "slope": slope,
                "trend": trend,
                "stats": stats,
                "data_points": len(scores)
            }

        except Exception as e:
            logger.error(f"Failed to retrieve analysis: {e}", exc_info=True)
            raise MemoryError(f"Analytical memory retrieval failed: {e}") from e

    # ============================================
    # Baseline 조회
    # ============================================

    async def get_baseline(
        self,
        user_id: str,
        days: int = 90
    ) -> BaselineStats:
        """
        Baseline 통계 조회

        Args:
            user_id: 사용자 ID
            days: Baseline 계산 기간 (기본 90일)

        Returns:
            BaselineStats 객체

        Example:
            >>> baseline = await analytical.get_baseline("user_123")
            >>> print(f"Mean: {baseline.mean}, Std: {baseline.std}")
        """
        try:
            return await self.timescale.get_baseline(user_id, days)
        except Exception as e:
            logger.error(f"Failed to get baseline: {e}")
            raise MemoryError(f"Baseline retrieval failed: {e}") from e

    # ============================================
    # 추세 분석
    # ============================================

    async def get_trend(
        self,
        user_id: str,
        weeks: int = 4
    ) -> Dict[str, Any]:
        """
        추세 분석 (기울기)

        Args:
            user_id: 사용자 ID
            weeks: 분석 기간 (주)

        Returns:
            {
                "slope": -0.5,
                "direction": "decreasing",
                "weeks": 4
            }

        Example:
            >>> trend = await analytical.get_trend("user_123", weeks=4)
            >>> print(trend["direction"])
            "decreasing"
        """
        try:
            slope, direction = await self.timescale.calculate_slope(user_id, weeks)

            return {
                "slope": slope,
                "direction": direction,
                "weeks": weeks
            }

        except Exception as e:
            logger.error(f"Failed to get trend: {e}")
            raise MemoryError(f"Trend analysis failed: {e}") from e

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
            시계열 데이터 리스트
            [
                {"time": "2025-01-01T10:00:00", "value": 78.5},
                ...
            ]

        Example:
            >>> data = await analytical.get_timeseries("user_123", metric="mcdi_score")
            >>> for point in data:
            ...     print(f"{point['time']}: {point['value']}")
        """
        try:
            return await self.timescale.get_timeseries(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                metric=metric
            )
        except Exception as e:
            logger.error(f"Failed to get timeseries: {e}")
            raise MemoryError(f"Timeseries retrieval failed: {e}") from e

    # ============================================
    # 최근 MCDI 점수 조회
    # ============================================

    async def get_latest_score(self, user_id: str) -> Optional[float]:
        """
        최신 MCDI 점수 조회

        Args:
            user_id: 사용자 ID

        Returns:
            최신 MCDI 점수 (없으면 None)

        Example:
            >>> score = await analytical.get_latest_score("user_123")
            >>> print(score)
            78.5
        """
        try:
            scores = await self.timescale.get_recent_scores(
                user_id=user_id,
                days=7,
                limit=1
            )

            if scores:
                return scores[0].mcdi_score
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get latest score: {e}")
            return None

    # ============================================
    # 과거 데이터 조회 (Risk Evaluator용)
    # ============================================

    async def get_historical_scores(
        self,
        user_id: str,
        days: int = 28
    ) -> List[tuple]:
        """
        과거 데이터 조회 (Risk Evaluator용)

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (일)

        Returns:
            (datetime, score) 튜플 리스트

        Example:
            >>> history = await analytical.get_historical_scores("user_123", days=28)
            >>> for date, score in history:
            ...     print(f"{date}: {score}")
        """
        try:
            scores = await self.timescale.get_recent_scores(
                user_id=user_id,
                days=days,
                limit=1000
            )

            # (datetime, score) 튜플로 변환 (시간 순서대로 정렬)
            history = [(score.time, score.mcdi_score) for score in reversed(scores)]

            logger.debug(
                f"Retrieved {len(history)} historical scores for user {user_id}"
            )

            return history

        except Exception as e:
            logger.error(f"Failed to get historical scores: {e}")
            # 실패 시 빈 리스트 반환 (Risk Evaluator가 처리 가능)
            return []

    # ============================================
    # 통계 조회
    # ============================================

    async def get_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        집계 통계 조회

        Args:
            user_id: 사용자 ID
            days: 조회 기간 (일)

        Returns:
            집계 통계 딕셔너리

        Example:
            >>> stats = await analytical.get_stats("user_123", days=30)
            >>> print(stats["mcdi"]["mean"])
            78.5
        """
        try:
            return await self.timescale.get_aggregate_stats(user_id, days)
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise MemoryError(f"Stats retrieval failed: {e}") from e


# ============================================
# 팩토리 함수
# ============================================

async def create_analytical_memory() -> AnalyticalMemory:
    """
    AnalyticalMemory 인스턴스 생성

    Returns:
        AnalyticalMemory 인스턴스

    Example:
        >>> analytical = await create_analytical_memory()
        >>> await analytical.store(user_id, analysis)
    """
    from database.timescale import get_timescale

    timescale = await get_timescale()
    return AnalyticalMemory(timescale)
