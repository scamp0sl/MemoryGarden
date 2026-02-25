"""
위험도 평가기 (Risk Evaluator)

MCDI 점수의 시계열 분석을 통해 인지 기능 저하 위험도를 4단계로 판정합니다.

Scientific Basis:
    - Baseline Comparison: 개인 맞춤형 기준선 대비 변화율
    - Z-Score Analysis: 통계적 유의성 판단
    - Trend Analysis: 선형 회귀로 4주 기울기 계산
    - Clinical Thresholds: MMSE, MoCA 등 임상 기준 참조

Risk Levels:
    GREEN (정상):
        - MCDI ≥ 80
        - Z-score > -1.0
        - 안정적 또는 상승 추세

    YELLOW (경미한 저하):
        - MCDI 60-80
        - Z-score -1.0 ~ -1.5
        - 완만한 하락 추세

    ORANGE (중등도 저하):
        - MCDI 40-60
        - Z-score -1.5 ~ -2.0
        - 중간 하락 추세
        - 교란 변수 확인 필요

    RED (심각한 저하):
        - MCDI < 40
        - Z-score < -2.0
        - 급격한 하락 추세 (>2점/주)
        - 즉시 전문가 상담 필요

Confounding Variables:
    점수 하락 시 다음 요인 확인:
    - 수면 부족 (최근 7일 수면 시간)
    - 우울감 (PHQ-2 스크리닝)
    - 약물 변경 (신규 처방, 용량 변경)
    - 신체 질환 (감기, 염증 등)
    - 생활 스트레스 (가족, 경제 문제)

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

# ============================================
# 2. Third-Party Imports
# ============================================
import numpy as np
from scipy import stats

# ============================================
# 3. Local Imports
# ============================================
from database.postgres import AsyncSessionLocal
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# 4. Logger Setup
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. Constants
# ============================================
# MCDI 점수 임계값
MCDI_THRESHOLDS = {
    "GREEN": 80.0,
    "YELLOW": 60.0,
    "ORANGE": 40.0,
    "RED": 0.0
}

# Z-Score 임계값
Z_SCORE_THRESHOLDS = {
    "normal": -1.0,      # 정상 범위
    "mild": -1.5,        # 경미한 저하
    "moderate": -2.0,    # 중등도 저하
    "severe": -3.0       # 심각한 저하
}

# 기울기 임계값 (점수/주)
SLOPE_THRESHOLDS = {
    "stable": -0.5,      # 안정적
    "mild_decline": -1.5,   # 완만한 하락
    "moderate_decline": -2.5,  # 중간 하락
    "steep_decline": -4.0     # 급격한 하락
}

# Baseline 계산 기간
BASELINE_DAYS = 14  # 첫 2주
MIN_BASELINE_SAMPLES = 5  # 최소 5개 데이터 필요

# 추세 분석 기간
TREND_DAYS = 28  # 최근 4주
MIN_TREND_SAMPLES = 7  # 최소 7개 데이터 필요

# 교란 변수 체크 기준
CONFOUND_CHECK_Z_SCORE = -1.5  # Z-score < -1.5일 때 체크
CONFOUND_CHECK_SLOPE = -2.0    # 기울기 < -2.0일 때 체크


# ============================================
# 6. Data Classes
# ============================================
@dataclass
class RiskEvaluation:
    """위험도 평가 결과"""
    risk_level: str  # GREEN/YELLOW/ORANGE/RED
    confidence: float  # 0-1 범위 신뢰도

    # 점수 정보
    current_score: float
    baseline_mean: Optional[float]
    baseline_std: Optional[float]

    # 통계 지표
    z_score: Optional[float]
    slope: Optional[float]  # 점수/주
    trend_direction: str  # increasing/stable/decreasing

    # 판정 근거
    primary_reason: str  # 주요 판정 이유
    contributing_factors: List[str]  # 기여 요인들

    # 액션
    alert_needed: bool  # 보호자 알림 필요 여부
    check_confounds: bool  # 교란 변수 확인 필요 여부
    recommendation: str  # 권장 조치

    # 메타데이터
    data_points_used: int
    evaluation_timestamp: datetime


# ============================================
# 7. RiskEvaluator Class
# ============================================
class RiskEvaluator:
    """
    위험도 평가기

    MCDI 점수의 시계열 데이터를 분석하여 인지 기능 저하 위험도를 판정합니다.

    Attributes:
        db_session: 데이터베이스 세션 팩토리

    Example:
        >>> evaluator = RiskEvaluator()
        >>> evaluation = await evaluator.evaluate(
        ...     user_id="user_123",
        ...     current_score=72.5,
        ...     analysis={"scores": {...}}
        ... )
        >>> print(evaluation.risk_level)
        "YELLOW"
    """

    def __init__(self):
        """초기화"""
        self.db_session = AsyncSessionLocal

        logger.info("RiskEvaluator initialized")

    async def evaluate(
        self,
        user_id: str,
        current_score: float,
        analysis: Dict[str, Any]
    ) -> RiskEvaluation:
        """
        위험도 평가 수행

        Args:
            user_id: 사용자 ID
            current_score: 현재 MCDI 점수
            analysis: 분석 결과 (6개 지표 등)

        Returns:
            RiskEvaluation 객체

        Raises:
            AnalysisError: 평가 실패 시

        Example:
            >>> evaluation = await evaluator.evaluate(
            ...     user_id="user_123",
            ...     current_score=72.5,
            ...     analysis={"scores": {"LR": 75.0, ...}}
            ... )
        """
        try:
            logger.info(
                f"Starting risk evaluation",
                extra={
                    "user_id": user_id,
                    "current_score": current_score
                }
            )

            # ============================================
            # 1. 과거 점수 데이터 조회
            # ============================================
            historical_scores = await self._fetch_historical_scores(user_id)

            # ============================================
            # 2. Baseline 계산
            # ============================================
            baseline_mean, baseline_std = self._calculate_baseline(
                historical_scores
            )

            # ============================================
            # 3. Z-Score 계산
            # ============================================
            z_score = self._calculate_z_score(
                current_score, baseline_mean, baseline_std
            )

            # ============================================
            # 4. 추세 분석 (4주 기울기)
            # ============================================
            slope, trend_direction = self._calculate_trend(
                historical_scores, current_score
            )

            # ============================================
            # 5. 위험도 판정
            # ============================================
            risk_level, confidence, primary_reason, contributing_factors = (
                self._determine_risk_level(
                    current_score, z_score, slope, trend_direction
                )
            )

            # ============================================
            # 6. 액션 결정
            # ============================================
            alert_needed = risk_level in ["ORANGE", "RED"]
            check_confounds = self._should_check_confounds(z_score, slope)
            recommendation = self._generate_recommendation(
                risk_level, z_score, slope
            )

            # ============================================
            # 7. 결과 반환
            # ============================================
            evaluation = RiskEvaluation(
                risk_level=risk_level,
                confidence=confidence,
                current_score=current_score,
                baseline_mean=baseline_mean,
                baseline_std=baseline_std,
                z_score=z_score,
                slope=slope,
                trend_direction=trend_direction,
                primary_reason=primary_reason,
                contributing_factors=contributing_factors,
                alert_needed=alert_needed,
                check_confounds=check_confounds,
                recommendation=recommendation,
                data_points_used=len(historical_scores) + 1,
                evaluation_timestamp=datetime.now()
            )

            logger.info(
                f"Risk evaluation completed",
                extra={
                    "user_id": user_id,
                    "risk_level": risk_level,
                    "confidence": f"{confidence:.2f}",
                    "z_score": f"{z_score:.2f}" if z_score else "N/A",
                    "slope": f"{slope:.2f}" if slope else "N/A"
                }
            )

            return evaluation

        except Exception as e:
            logger.error(
                f"Risk evaluation failed: {e}",
                extra={"user_id": user_id},
                exc_info=True
            )
            raise AnalysisError(f"Risk evaluation failed: {e}") from e

    async def _fetch_historical_scores(
        self,
        user_id: str,
        days: int = TREND_DAYS + BASELINE_DAYS
    ) -> List[Tuple[datetime, float]]:
        """
        과거 MCDI 점수 데이터 조회 (TimescaleDB)

        Args:
            user_id: 사용자 ID
            days: 조회할 일수

        Returns:
            [(timestamp, mcdi_score), ...] 리스트 (시간순 정렬)

        Example:
            >>> scores = await evaluator._fetch_historical_scores("user_123")
            >>> print(len(scores))
            42
        """
        try:
            # AnalyticalMemory를 통해 TimescaleDB 조회
            from core.memory.analytical_memory import create_analytical_memory

            analytical = await create_analytical_memory()

            logger.debug(
                f"Fetching historical scores for user {user_id} "
                f"(last {days} days)"
            )

            # TimescaleDB에서 과거 데이터 조회
            scores = await analytical.get_historical_scores(
                user_id=user_id,
                days=days
            )

            logger.debug(f"Found {len(scores)} historical scores")

            return scores

        except Exception as e:
            logger.error(f"Failed to fetch historical scores: {e}")
            # 실패 시 빈 리스트 반환 (Baseline 계산 시 None 처리)
            return []

    def _calculate_baseline(
        self,
        historical_scores: List[Tuple[datetime, float]]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Baseline 계산 (첫 2주 평균 및 표준편차)

        Args:
            historical_scores: 과거 점수 데이터

        Returns:
            (baseline_mean, baseline_std) 또는 (None, None)

        Example:
            >>> scores = [(datetime.now(), 85.0), ...]
            >>> mean, std = evaluator._calculate_baseline(scores)
            >>> print(mean, std)
            82.5 3.2
        """
        if not historical_scores:
            logger.debug("No historical scores for baseline calculation")
            return None, None

        # 첫 2주 데이터만 추출
        baseline_cutoff = historical_scores[0][0] + timedelta(days=BASELINE_DAYS)
        baseline_scores = [
            score for timestamp, score in historical_scores
            if timestamp <= baseline_cutoff
        ]

        if len(baseline_scores) < MIN_BASELINE_SAMPLES:
            logger.debug(
                f"Insufficient baseline samples: {len(baseline_scores)} "
                f"(minimum: {MIN_BASELINE_SAMPLES})"
            )
            return None, None

        # 평균 및 표준편차 계산
        baseline_mean = np.mean(baseline_scores)
        baseline_std = np.std(baseline_scores, ddof=1)  # 표본 표준편차

        # 표준편차가 너무 작으면 최소값 설정 (0으로 나누기 방지)
        if baseline_std < 1.0:
            baseline_std = 1.0

        logger.debug(
            f"Baseline calculated: mean={baseline_mean:.2f}, "
            f"std={baseline_std:.2f} (n={len(baseline_scores)})"
        )

        return baseline_mean, baseline_std

    def _calculate_z_score(
        self,
        current_score: float,
        baseline_mean: Optional[float],
        baseline_std: Optional[float]
    ) -> Optional[float]:
        """
        Z-Score 계산

        Formula:
            z = (x - μ) / σ
            where x = current_score, μ = baseline_mean, σ = baseline_std

        Args:
            current_score: 현재 점수
            baseline_mean: Baseline 평균
            baseline_std: Baseline 표준편차

        Returns:
            Z-Score 또는 None

        Example:
            >>> z = evaluator._calculate_z_score(70.0, 80.0, 5.0)
            >>> print(z)
            -2.0
        """
        if baseline_mean is None or baseline_std is None:
            return None

        z_score = (current_score - baseline_mean) / baseline_std

        logger.debug(
            f"Z-score calculated: {z_score:.2f} "
            f"(current={current_score:.2f}, baseline={baseline_mean:.2f}±{baseline_std:.2f})"
        )

        return z_score

    def _calculate_trend(
        self,
        historical_scores: List[Tuple[datetime, float]],
        current_score: float
    ) -> Tuple[Optional[float], str]:
        """
        추세 분석 (4주 기울기 계산)

        선형 회귀를 사용하여 기울기(slope)를 계산합니다.

        Formula:
            slope = Σ((x - x̄)(y - ȳ)) / Σ((x - x̄)²)
            where x = days, y = mcdi_scores

        Args:
            historical_scores: 과거 점수 데이터
            current_score: 현재 점수

        Returns:
            (slope, trend_direction)
            - slope: 점수/주 (주당 변화율)
            - trend_direction: "increasing"/"stable"/"decreasing"

        Example:
            >>> slope, direction = evaluator._calculate_trend(scores, 72.5)
            >>> print(slope, direction)
            -2.3 decreasing
        """
        # 최근 4주 데이터 + 현재 점수
        if not historical_scores:
            logger.debug("No historical scores for trend analysis")
            return None, "unknown"

        trend_cutoff = datetime.now() - timedelta(days=TREND_DAYS)
        trend_data = [
            (timestamp, score) for timestamp, score in historical_scores
            if timestamp >= trend_cutoff
        ]

        # 현재 점수 추가
        trend_data.append((datetime.now(), current_score))

        if len(trend_data) < MIN_TREND_SAMPLES:
            logger.debug(
                f"Insufficient trend samples: {len(trend_data)} "
                f"(minimum: {MIN_TREND_SAMPLES})"
            )
            return None, "unknown"

        # 선형 회귀
        timestamps = [ts.timestamp() for ts, _ in trend_data]
        scores = [score for _, score in trend_data]

        # scipy.stats.linregress 사용
        slope_per_second, intercept, r_value, p_value, std_err = stats.linregress(
            timestamps, scores
        )

        # 초당 기울기 → 주당 기울기 변환
        seconds_per_week = 7 * 24 * 60 * 60
        slope_per_week = slope_per_second * seconds_per_week

        # 추세 방향 판정
        if slope_per_week > SLOPE_THRESHOLDS["stable"]:
            trend_direction = "increasing"
        elif slope_per_week > SLOPE_THRESHOLDS["mild_decline"]:
            trend_direction = "stable"
        else:
            trend_direction = "decreasing"

        logger.debug(
            f"Trend calculated: slope={slope_per_week:.2f} points/week, "
            f"direction={trend_direction}, r²={r_value**2:.3f}, p={p_value:.3f}"
        )

        return slope_per_week, trend_direction

    def _determine_risk_level(
        self,
        current_score: float,
        z_score: Optional[float],
        slope: Optional[float],
        trend_direction: str
    ) -> Tuple[str, float, str, List[str]]:
        """
        위험도 판정

        MCDI 점수, Z-score, 기울기를 종합하여 위험도를 판정합니다.

        Args:
            current_score: 현재 MCDI 점수
            z_score: Z-score
            slope: 기울기 (점수/주)
            trend_direction: 추세 방향

        Returns:
            (risk_level, confidence, primary_reason, contributing_factors)

        Example:
            >>> risk, conf, reason, factors = evaluator._determine_risk_level(
            ...     72.5, -1.2, -1.8, "decreasing"
            ... )
            >>> print(risk, conf)
            "YELLOW" 0.85
        """
        contributing_factors = []

        # ============================================
        # 1. MCDI 점수 기반 초기 판정
        # ============================================
        if current_score >= MCDI_THRESHOLDS["GREEN"]:
            base_risk = "GREEN"
            primary_reason = "MCDI 점수가 정상 범위입니다"
        elif current_score >= MCDI_THRESHOLDS["YELLOW"]:
            base_risk = "YELLOW"
            primary_reason = "MCDI 점수가 경미하게 저하되었습니다"
        elif current_score >= MCDI_THRESHOLDS["ORANGE"]:
            base_risk = "ORANGE"
            primary_reason = "MCDI 점수가 중등도로 저하되었습니다"
        else:
            base_risk = "RED"
            primary_reason = "MCDI 점수가 심각하게 저하되었습니다"

        # ============================================
        # 2. Z-Score 기반 조정
        # ============================================
        if z_score is not None:
            if z_score < Z_SCORE_THRESHOLDS["severe"]:
                # Z-score가 매우 낮으면 위험도 상향
                base_risk = self._escalate_risk(base_risk, 2)
                contributing_factors.append(
                    f"Baseline 대비 매우 낮은 점수 (z={z_score:.2f})"
                )
            elif z_score < Z_SCORE_THRESHOLDS["moderate"]:
                base_risk = self._escalate_risk(base_risk, 1)
                contributing_factors.append(
                    f"Baseline 대비 낮은 점수 (z={z_score:.2f})"
                )
            elif z_score < Z_SCORE_THRESHOLDS["mild"]:
                contributing_factors.append(
                    f"Baseline 대비 약간 낮은 점수 (z={z_score:.2f})"
                )
            else:
                contributing_factors.append(
                    f"Baseline 범위 내 (z={z_score:.2f})"
                )

        # ============================================
        # 3. 기울기 기반 조정
        # ============================================
        if slope is not None:
            if slope < SLOPE_THRESHOLDS["steep_decline"]:
                # 급격한 하락 → 위험도 상향
                base_risk = self._escalate_risk(base_risk, 2)
                contributing_factors.append(
                    f"급격한 하락 추세 ({slope:.2f} 점/주)"
                )
            elif slope < SLOPE_THRESHOLDS["moderate_decline"]:
                base_risk = self._escalate_risk(base_risk, 1)
                contributing_factors.append(
                    f"중간 하락 추세 ({slope:.2f} 점/주)"
                )
            elif slope < SLOPE_THRESHOLDS["mild_decline"]:
                contributing_factors.append(
                    f"완만한 하락 추세 ({slope:.2f} 점/주)"
                )
            else:
                contributing_factors.append(
                    f"안정적 또는 상승 추세 ({slope:.2f} 점/주)"
                )

        # ============================================
        # 4. 신뢰도 계산
        # ============================================
        confidence = self._calculate_confidence(z_score, slope)

        logger.debug(
            f"Risk determined: {base_risk} (confidence={confidence:.2f})"
        )

        return base_risk, confidence, primary_reason, contributing_factors

    def _escalate_risk(self, current_risk: str, levels: int) -> str:
        """
        위험도 상향 조정

        Args:
            current_risk: 현재 위험도
            levels: 상향할 단계 수

        Returns:
            조정된 위험도

        Example:
            >>> new_risk = evaluator._escalate_risk("GREEN", 2)
            >>> print(new_risk)
            "ORANGE"
        """
        risk_order = ["GREEN", "YELLOW", "ORANGE", "RED"]
        current_index = risk_order.index(current_risk)
        new_index = min(current_index + levels, len(risk_order) - 1)
        return risk_order[new_index]

    def _calculate_confidence(
        self,
        z_score: Optional[float],
        slope: Optional[float]
    ) -> float:
        """
        판정 신뢰도 계산

        데이터의 충분성과 통계적 유의성을 기반으로 신뢰도를 계산합니다.

        Args:
            z_score: Z-score
            slope: 기울기

        Returns:
            0-1 범위의 신뢰도

        Example:
            >>> conf = evaluator._calculate_confidence(-2.1, -2.5)
            >>> print(conf)
            0.92
        """
        confidence = 0.5  # 기본 신뢰도

        # Z-score 있으면 +0.25
        if z_score is not None:
            confidence += 0.25

        # 기울기 있으면 +0.25
        if slope is not None:
            confidence += 0.25

        return confidence

    def _should_check_confounds(
        self,
        z_score: Optional[float],
        slope: Optional[float]
    ) -> bool:
        """
        교란 변수 체크 필요 여부 판단

        Args:
            z_score: Z-score
            slope: 기울기

        Returns:
            True if 체크 필요

        Example:
            >>> need_check = evaluator._should_check_confounds(-1.8, -2.3)
            >>> print(need_check)
            True
        """
        # Z-score가 낮거나 급격한 하락 시 체크
        if z_score is not None and z_score < CONFOUND_CHECK_Z_SCORE:
            return True

        if slope is not None and slope < CONFOUND_CHECK_SLOPE:
            return True

        return False

    def _generate_recommendation(
        self,
        risk_level: str,
        z_score: Optional[float],
        slope: Optional[float]
    ) -> str:
        """
        권장 조치 생성

        Args:
            risk_level: 위험도 레벨
            z_score: Z-score
            slope: 기울기

        Returns:
            권장 조치 메시지

        Example:
            >>> rec = evaluator._generate_recommendation("ORANGE", -1.8, -2.3)
            >>> print(rec)
            "교란 변수 확인 후 전문가 상담을 권장합니다."
        """
        if risk_level == "GREEN":
            return "현재 인지 기능이 정상 범위입니다. 계속 기록을 유지해주세요."

        elif risk_level == "YELLOW":
            return "경미한 저하가 관찰됩니다. 꾸준한 모니터링을 권장합니다."

        elif risk_level == "ORANGE":
            if self._should_check_confounds(z_score, slope):
                return "교란 변수(수면, 우울, 약물 등)를 확인한 후 전문가 상담을 권장합니다."
            else:
                return "중등도 저하가 관찰됩니다. 전문가 상담을 권장합니다."

        else:  # RED
            return "심각한 저하가 관찰됩니다. 즉시 전문가 상담을 받으시기 바랍니다."

    def to_dict(self, evaluation: RiskEvaluation) -> Dict[str, Any]:
        """
        RiskEvaluation을 딕셔너리로 변환

        Args:
            evaluation: RiskEvaluation 객체

        Returns:
            딕셔너리 형태의 평가 결과

        Example:
            >>> result_dict = evaluator.to_dict(evaluation)
            >>> print(result_dict["risk_level"])
            "YELLOW"
        """
        return {
            "risk_level": evaluation.risk_level,
            "confidence": evaluation.confidence,
            "current_score": evaluation.current_score,
            "baseline_mean": evaluation.baseline_mean,
            "baseline_std": evaluation.baseline_std,
            "z_score": evaluation.z_score,
            "slope": evaluation.slope,
            "trend_direction": evaluation.trend_direction,
            "primary_reason": evaluation.primary_reason,
            "contributing_factors": evaluation.contributing_factors,
            "alert_needed": evaluation.alert_needed,
            "check_confounds": evaluation.check_confounds,
            "recommendation": evaluation.recommendation,
            "data_points_used": evaluation.data_points_used,
            "evaluation_timestamp": evaluation.evaluation_timestamp.isoformat()
        }
