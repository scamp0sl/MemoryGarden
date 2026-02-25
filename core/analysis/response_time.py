"""
반응 시간 (RT - Response Time) 분석기

응답 지연 시간 및 효율성 평가를 통한 인지 처리 속도 측정

Scientific Basis:
    Salthouse (1996) Processing Speed Theory
    Nebes & Brady (1988) Cognitive Slowing in Dementia

    - 응답 지연 증가 = 인지 처리 속도 저하
    - 효율성 저하 = 단어 인출 장애
    - 긴 중단 = 작업 기억 부족
    - 변동성 증가 = 주의력 불안정

Analysis Metrics:
    1. Response Latency (응답 지연): 질문 후 응답까지의 시간
       Formula: latency_score = 1 - (latency / threshold)

    2. Response Efficiency (응답 효율성): 응답 시간 대비 내용 길이
       Formula: efficiency = message_length / response_time

    3. Pause Pattern (중단 패턴): 응답 중 긴 중단 발생 빈도
       Formula: pause_score = 1 - (long_pauses / total_segments)

    4. Response Consistency (응답 일관성): 응답 시간 변동성
       Formula: consistency = 1 - (std_dev / mean)

Scoring Formula:
    RT_Score = LatencyScore × 35 + Efficiency × 30 + PauseScore × 15 + Consistency × 20

    Range: 0-100 (높을수록 좋음)

    - LatencyScore: 0-1 범위 (빠를수록 좋음)
    - Efficiency: 정규화된 0-1 범위 (효율적일수록 좋음)
    - PauseScore: 0-1 범위 (중단 적을수록 좋음)
    - Consistency: 0-1 범위 (일관될수록 좋음)

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2025-02-10
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics

from utils.logger import get_logger
from utils.exceptions import AnalysisError

logger = get_logger(__name__)


class ResponseTimeAnalyzer:
    """
    반응 시간 (Response Time) 분석기

    사용자의 응답 지연 시간, 효율성, 중단 패턴, 일관성을 분석하여
    인지 처리 속도 및 주의력을 평가합니다.

    Attributes:
        None (stateless analyzer)

    Example:
        >>> analyzer = ResponseTimeAnalyzer()
        >>> result = await analyzer.analyze(
        ...     message="봄에는 엄마와 뒷산에서 쑥을 뜯었어요",
        ...     context={
        ...         "response_latency": 3.5,  # 3.5초
        ...         "typing_pauses": [0.5, 0.8, 1.2],
        ...         "historical_latencies": [2.8, 3.1, 3.2, 4.5]
        ...     }
        ... )
        >>> print(result["score"])
        82.5
        >>> print(result["components"]["latency_score"])
        0.88

    Note:
        - response_latency: 질문 후 첫 응답까지의 시간 (초)
        - typing_pauses: 타이핑 중 중단 시간 목록 (초)
        - historical_latencies: 과거 응답 시간 목록 (초)
    """

    # ============================================
    # 기준 임계값
    # ============================================

    # 응답 지연 임계값 (초)
    LATENCY_THRESHOLDS = {
        "excellent": 3.0,      # 3초 이내: 우수
        "good": 5.0,           # 5초 이내: 양호
        "moderate": 10.0,      # 10초 이내: 보통
        "slow": 20.0,          # 20초 이내: 느림
        "very_slow": 30.0,     # 30초 이상: 매우 느림
    }

    # 효율성 기준 (글자/초)
    EFFICIENCY_THRESHOLDS = {
        "excellent": 10.0,     # 10 글자/초 이상: 우수
        "good": 5.0,           # 5 글자/초 이상: 양호
        "moderate": 2.0,       # 2 글자/초 이상: 보통
        "slow": 1.0,           # 1 글자/초 이상: 느림
    }

    # 중단 임계값 (초)
    PAUSE_THRESHOLD = 2.0      # 2초 이상: 긴 중단

    def __init__(self):
        """
        반응 시간 분석기 초기화
        """
        logger.info("ResponseTimeAnalyzer initialized")

    async def analyze(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        반응 시간 종합 분석

        사용자의 응답 지연, 효율성, 중단 패턴, 일관성을 평가하여
        인지 처리 속도 및 주의력을 측정합니다.

        Args:
            message: 사용자 응답 텍스트
            context: 분석 컨텍스트 (필수)
                - response_latency: 응답 지연 시간 (초, 필수)
                - typing_pauses: 타이핑 중 중단 시간 목록 (초, 선택)
                  [0.5, 0.8, 1.2, 2.5, ...]
                - historical_latencies: 과거 응답 시간 목록 (초, 선택)
                  [2.8, 3.1, 3.2, 4.5, ...]
                - question_sent_at: 질문 전송 시각 (datetime, 선택)
                - response_received_at: 응답 수신 시각 (datetime, 선택)

        Returns:
            분석 결과 딕셔너리
            {
                "score": 82.5,  # RT 종합 점수 (0-100)
                "components": {
                    "latency_score": 0.88,       # 응답 지연 점수 (0-1)
                    "efficiency": 0.85,          # 응답 효율성 (0-1)
                    "pause_score": 0.90,         # 중단 패턴 점수 (0-1)
                    "consistency": 0.75          # 응답 일관성 (0-1)
                },
                "details": {
                    "response_latency": 3.5,
                    "latency_category": "good",
                    "message_length": 22,
                    "chars_per_second": 6.3,
                    "long_pauses": 1,
                    "total_pauses": 4,
                    "latency_std_dev": 0.8,
                    "latency_mean": 3.4
                }
            }

        Raises:
            AnalysisError: 분석 실패 시 또는 필수 컨텍스트 누락 시

        Example:
            >>> result = await analyzer.analyze(
            ...     "봄에는 엄마와 쑥을 뜯었어요",
            ...     context={
            ...         "response_latency": 3.5,
            ...         "typing_pauses": [0.5, 0.8, 1.2],
            ...         "historical_latencies": [2.8, 3.1, 3.2, 4.5]
            ...     }
            ... )
            >>> print(result["score"])
            82.5
            >>> print(result["details"]["latency_category"])
            "good"

        Note:
            - response_latency는 필수 (없으면 AnalysisError)
            - typing_pauses 없으면 pause_score는 1.0 (중립)
            - historical_latencies 없으면 consistency는 1.0 (중립)
        """
        logger.debug(f"Starting RT analysis for message (length={len(message)})")

        # ============================================
        # 0. 입력 검증
        # ============================================
        if not message or not message.strip():
            logger.warning("Empty message provided for RT analysis")
            raise AnalysisError("Message cannot be empty")

        if not context:
            logger.error("Context is required for RT analysis")
            raise AnalysisError("Context with response_latency is required")

        response_latency = context.get("response_latency")
        if response_latency is None:
            logger.error("response_latency not found in context")
            raise AnalysisError("response_latency is required in context")

        try:
            # ============================================
            # 1. 컨텍스트 추출
            # ============================================
            typing_pauses = context.get("typing_pauses", [])
            historical_latencies = context.get("historical_latencies", [])

            logger.debug(
                f"Context: latency={response_latency:.2f}s, "
                f"pauses={len(typing_pauses)}, "
                f"historical={len(historical_latencies)}"
            )

            # ============================================
            # 2. 4개 지표 계산
            # ============================================

            # 2.1 응답 지연 점수 (Response Latency Score)
            # Formula: latency_score = 1 - (latency / threshold)
            # 낮을수록 좋음 → 점수는 높을수록 좋음 (역전)
            logger.debug("Calculating latency score...")
            latency_result = self._calculate_latency_score(response_latency)
            latency_score = latency_result["score"]
            logger.debug(f"Latency score: {latency_score:.3f} ({latency_result['category']})")

            # 2.2 응답 효율성 (Response Efficiency)
            # Formula: efficiency = message_length / response_time
            # 높을수록 좋음 (0-1 범위로 정규화)
            logger.debug("Calculating response efficiency...")
            efficiency_result = self._calculate_efficiency(message, response_latency)
            efficiency = efficiency_result["efficiency"]
            logger.debug(f"Efficiency: {efficiency:.3f} ({efficiency_result['details']['chars_per_second']:.2f} chars/s)")

            # 2.3 중단 패턴 점수 (Pause Pattern Score)
            # Formula: pause_score = 1 - (long_pauses / total_pauses)
            # 긴 중단 적을수록 좋음 (0-1 범위)
            logger.debug("Calculating pause pattern score...")
            pause_result = self._calculate_pause_score(typing_pauses)
            pause_score = pause_result["score"]
            logger.debug(f"Pause score: {pause_score:.3f}")

            # 2.4 응답 일관성 (Response Consistency)
            # Formula: consistency = 1 - (std_dev / mean)
            # 변동성 적을수록 좋음 (0-1 범위)
            logger.debug("Calculating response consistency...")
            consistency_result = self._calculate_consistency(
                response_latency, historical_latencies
            )
            consistency = consistency_result["score"]
            logger.debug(f"Consistency: {consistency:.3f}")

            # ============================================
            # 3. 종합 점수 계산
            # ============================================
            # Formula: RT = LatencyScore×35 + Efficiency×30 + PauseScore×15 + Consistency×20
            # Range: 0-100
            score = (
                latency_score * 100 * 0.35 +        # 응답 지연 (35%)
                efficiency * 100 * 0.30 +           # 응답 효율성 (30%)
                pause_score * 100 * 0.15 +          # 중단 패턴 (15%)
                consistency * 100 * 0.20            # 응답 일관성 (20%)
            )

            logger.info(
                f"RT analysis completed: score={score:.2f}",
                extra={
                    "latency_score": latency_score,
                    "efficiency": efficiency,
                    "pause_score": pause_score,
                    "consistency": consistency
                }
            )

            # ============================================
            # 4. 결과 반환
            # ============================================
            return {
                "score": round(score, 2),
                "components": {
                    "latency_score": round(latency_score, 3),
                    "efficiency": round(efficiency, 3),
                    "pause_score": round(pause_score, 3),
                    "consistency": round(consistency, 3)
                },
                "details": {
                    **latency_result["details"],
                    **efficiency_result["details"],
                    **pause_result["details"],
                    **consistency_result["details"],
                }
            }

        except Exception as e:
            logger.error(f"RT analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Response Time analysis failed: {e}") from e

    def _calculate_latency_score(self, latency: float) -> Dict[str, Any]:
        """
        응답 지연 점수 계산

        응답 지연 시간을 임계값과 비교하여 점수를 산출합니다.

        Formula:
            latency_score = 1 - (latency / threshold)
            with adaptive threshold based on category

        Args:
            latency: 응답 지연 시간 (초)

        Returns:
            {
                "score": 0.88,
                "category": "good",
                "details": {
                    "response_latency": 3.5,
                    "latency_category": "good",
                    "threshold_used": 5.0
                }
            }

        Example:
            >>> result = self._calculate_latency_score(3.5)
            >>> print(result["score"])
            0.88
            >>> print(result["category"])
            "good"

        Note:
            - 0-3초: excellent (1.0)
            - 3-5초: good (0.7-1.0)
            - 5-10초: moderate (0.5-0.7)
            - 10-20초: slow (0.25-0.5)
            - 20초+: very_slow (0.0-0.25)
        """
        # 카테고리 판정
        if latency <= self.LATENCY_THRESHOLDS["excellent"]:
            category = "excellent"
            score = 1.0
            threshold = self.LATENCY_THRESHOLDS["excellent"]
        elif latency <= self.LATENCY_THRESHOLDS["good"]:
            category = "good"
            threshold = self.LATENCY_THRESHOLDS["good"]
            # 3-5초: 선형 스케일 (1.0 → 0.7)
            score = 1.0 - ((latency - self.LATENCY_THRESHOLDS["excellent"]) /
                          (threshold - self.LATENCY_THRESHOLDS["excellent"])) * 0.3
        elif latency <= self.LATENCY_THRESHOLDS["moderate"]:
            category = "moderate"
            threshold = self.LATENCY_THRESHOLDS["moderate"]
            # 5-10초: 선형 스케일 (0.7 → 0.5)
            score = 0.7 - ((latency - self.LATENCY_THRESHOLDS["good"]) /
                          (threshold - self.LATENCY_THRESHOLDS["good"])) * 0.2
        elif latency <= self.LATENCY_THRESHOLDS["slow"]:
            category = "slow"
            threshold = self.LATENCY_THRESHOLDS["slow"]
            # 10-20초: 선형 스케일 (0.5 → 0.25)
            score = 0.5 - ((latency - self.LATENCY_THRESHOLDS["moderate"]) /
                          (threshold - self.LATENCY_THRESHOLDS["moderate"])) * 0.25
        else:
            category = "very_slow"
            threshold = self.LATENCY_THRESHOLDS["very_slow"]
            # 20초+: 선형 스케일 (0.25 → 0.0)
            score = max(0.0, 0.25 - ((latency - self.LATENCY_THRESHOLDS["slow"]) /
                                     (threshold - self.LATENCY_THRESHOLDS["slow"])) * 0.25)

        logger.debug(f"Latency: {latency:.2f}s → {category} (score={score:.3f})")

        return {
            "score": score,
            "category": category,
            "details": {
                "response_latency": round(latency, 2),
                "latency_category": category,
                "threshold_used": threshold
            }
        }

    def _calculate_efficiency(
        self,
        message: str,
        latency: float
    ) -> Dict[str, Any]:
        """
        응답 효율성 계산

        응답 시간 대비 메시지 길이를 비교하여 효율성을 평가합니다.

        Formula:
            chars_per_second = message_length / response_time
            efficiency = min(1.0, chars_per_second / threshold)

        Args:
            message: 응답 메시지
            latency: 응답 시간 (초)

        Returns:
            {
                "efficiency": 0.85,
                "details": {
                    "message_length": 22,
                    "chars_per_second": 6.3,
                    "efficiency_category": "good"
                }
            }

        Example:
            >>> result = self._calculate_efficiency("봄에는 엄마와 쑥을 뜯었어요", 3.5)
            >>> print(result["efficiency"])
            0.85
            >>> print(result["details"]["chars_per_second"])
            6.3

        Note:
            - 10+ 글자/초: excellent (1.0)
            - 5-10 글자/초: good (0.5-1.0)
            - 2-5 글자/초: moderate (0.2-0.5)
            - <2 글자/초: slow (<0.2)
        """
        message_length = len(message.strip())

        if latency == 0:
            # 즉시 응답 (비현실적이지만 방어적 처리)
            chars_per_second = float('inf')
            efficiency = 1.0
        else:
            chars_per_second = message_length / latency

            # 정규화 (10 글자/초를 1.0으로 기준)
            efficiency = min(1.0, chars_per_second / self.EFFICIENCY_THRESHOLDS["excellent"])

        # 카테고리 판정
        if chars_per_second >= self.EFFICIENCY_THRESHOLDS["excellent"]:
            category = "excellent"
        elif chars_per_second >= self.EFFICIENCY_THRESHOLDS["good"]:
            category = "good"
        elif chars_per_second >= self.EFFICIENCY_THRESHOLDS["moderate"]:
            category = "moderate"
        else:
            category = "slow"

        logger.debug(
            f"Efficiency: {message_length} chars / {latency:.2f}s = "
            f"{chars_per_second:.2f} chars/s → {category}"
        )

        return {
            "efficiency": efficiency,
            "details": {
                "message_length": message_length,
                "chars_per_second": round(chars_per_second, 2),
                "efficiency_category": category
            }
        }

    def _calculate_pause_score(self, pauses: List[float]) -> Dict[str, Any]:
        """
        중단 패턴 점수 계산

        타이핑 중 긴 중단(2초 이상)의 비율을 평가합니다.

        Formula:
            pause_score = 1 - (long_pauses / total_pauses)
            no pauses = 1.0 (neutral)

        Args:
            pauses: 타이핑 중 중단 시간 목록 (초)
                [0.5, 0.8, 1.2, 2.5, ...]

        Returns:
            {
                "score": 0.90,
                "details": {
                    "long_pauses": 1,
                    "total_pauses": 4,
                    "long_pause_ratio": 0.25,
                    "max_pause": 2.5
                }
            }

        Example:
            >>> result = self._calculate_pause_score([0.5, 0.8, 1.2, 2.5])
            >>> print(result["score"])
            0.75
            >>> print(result["details"]["long_pauses"])
            1

        Note:
            - 긴 중단 기준: 2초 이상
            - 중단 없으면: 1.0 (중립)
            - 긴 중단 많을수록: 점수 낮음
        """
        if not pauses:
            return {
                "score": 1.0,
                "details": {
                    "long_pauses": 0,
                    "total_pauses": 0,
                    "long_pause_ratio": 0.0,
                    "max_pause": 0.0
                }
            }

        # 긴 중단 카운트 (2초 이상)
        long_pauses = [p for p in pauses if p >= self.PAUSE_THRESHOLD]
        long_pause_count = len(long_pauses)
        total_pause_count = len(pauses)

        # 점수 계산
        long_pause_ratio = long_pause_count / total_pause_count
        score = 1.0 - long_pause_ratio

        max_pause = max(pauses) if pauses else 0.0

        logger.debug(
            f"Pauses: {long_pause_count}/{total_pause_count} long pauses "
            f"(max={max_pause:.2f}s)"
        )

        return {
            "score": score,
            "details": {
                "long_pauses": long_pause_count,
                "total_pauses": total_pause_count,
                "long_pause_ratio": round(long_pause_ratio, 3),
                "max_pause": round(max_pause, 2)
            }
        }

    def _calculate_consistency(
        self,
        current_latency: float,
        historical_latencies: List[float]
    ) -> Dict[str, Any]:
        """
        응답 일관성 계산

        과거 응답 시간과 비교하여 일관성(변동성 역수)을 평가합니다.

        Formula:
            consistency = 1 - (std_dev / mean)
            no history = 1.0 (neutral)

        Args:
            current_latency: 현재 응답 시간 (초)
            historical_latencies: 과거 응답 시간 목록 (초)
                [2.8, 3.1, 3.2, 4.5, ...]

        Returns:
            {
                "score": 0.75,
                "details": {
                    "latency_mean": 3.4,
                    "latency_std_dev": 0.8,
                    "latency_cv": 0.24,
                    "historical_count": 4
                }
            }

        Example:
            >>> result = self._calculate_consistency(3.5, [2.8, 3.1, 3.2, 4.5])
            >>> print(result["score"])
            0.76
            >>> print(result["details"]["latency_std_dev"])
            0.8

        Note:
            - 변동성 낮을수록 점수 높음
            - CV (Coefficient of Variation) = std_dev / mean
            - 과거 데이터 없으면: 1.0 (중립)
        """
        # 과거 데이터에 현재 값 추가
        all_latencies = historical_latencies + [current_latency]

        if len(all_latencies) < 2:
            return {
                "score": 1.0,
                "details": {
                    "latency_mean": current_latency,
                    "latency_std_dev": 0.0,
                    "latency_cv": 0.0,
                    "historical_count": 0
                }
            }

        # 통계 계산
        mean = statistics.mean(all_latencies)
        std_dev = statistics.stdev(all_latencies)

        # CV (Coefficient of Variation)
        cv = std_dev / mean if mean > 0 else 0.0

        # 점수 (CV가 낮을수록 일관적)
        # CV 1.0을 기준으로 정규화 (CV > 1.0이면 0점)
        score = max(0.0, 1.0 - cv)

        logger.debug(
            f"Consistency: mean={mean:.2f}s, std={std_dev:.2f}s, "
            f"CV={cv:.3f}, score={score:.3f}"
        )

        return {
            "score": score,
            "details": {
                "latency_mean": round(mean, 2),
                "latency_std_dev": round(std_dev, 2),
                "latency_cv": round(cv, 3),
                "historical_count": len(historical_latencies)
            }
        }
