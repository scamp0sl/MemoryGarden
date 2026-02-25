"""
감정 트렌드 분석기

일간/주간/월간 감정 변화 추적 및 패턴 감지.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
from enum import Enum

# ============================================
# 2. Third-Party Imports
# ============================================
from pydantic import BaseModel, Field
import numpy as np

# ============================================
# 3. Local Imports
# ============================================
from core.nlp.emotion_detector import EmotionCategory
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 및 Enum 정의
# ============================================

class EmotionTrend(str, Enum):
    """감정 트렌드"""
    IMPROVING = "improving"       # 개선 중
    STABLE = "stable"            # 안정적
    DECLINING = "declining"      # 악화 중
    VOLATILE = "volatile"        # 변동성 높음


class EmotionPattern(str, Enum):
    """감정 패턴"""
    CONSISTENT = "consistent"         # 일관적
    DAILY_CYCLE = "daily_cycle"      # 일일 주기
    WEEKLY_CYCLE = "weekly_cycle"    # 주간 주기
    RANDOM = "random"                # 무작위


# ============================================
# 6. 응답 모델
# ============================================

class EmotionDistribution(BaseModel):
    """감정 분포"""
    joy: float = Field(default=0.0, ge=0.0, le=1.0)
    sadness: float = Field(default=0.0, ge=0.0, le=1.0)
    anger: float = Field(default=0.0, ge=0.0, le=1.0)
    fear: float = Field(default=0.0, ge=0.0, le=1.0)
    surprise: float = Field(default=0.0, ge=0.0, le=1.0)
    neutral: float = Field(default=0.0, ge=0.0, le=1.0)


class EmotionTrendAnalysis(BaseModel):
    """감정 트렌드 분석 결과"""
    period: str = Field(..., description="분석 기간 (daily/weekly/monthly)")
    start_date: str = Field(..., description="시작 날짜")
    end_date: str = Field(..., description="종료 날짜")

    # 감정 분포
    emotion_distribution: EmotionDistribution
    dominant_emotion: str = Field(..., description="주요 감정")

    # 트렌드
    trend: EmotionTrend = Field(..., description="감정 트렌드")
    trend_score: float = Field(..., ge=-1.0, le=1.0, description="트렌드 점수 (-1~1)")

    # 패턴
    pattern: EmotionPattern = Field(..., description="감정 패턴")
    volatility: float = Field(..., ge=0.0, le=1.0, description="변동성 (0~1)")

    # 통계
    total_interactions: int = Field(..., description="총 상호작용 수")
    positive_ratio: float = Field(..., ge=0.0, le=1.0, description="긍정 비율")
    negative_ratio: float = Field(..., ge=0.0, le=1.0, description="부정 비율")

    # 상세 데이터
    daily_emotions: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)


# ============================================
# 7. EmotionAnalyzer 클래스
# ============================================

class EmotionAnalyzer:
    """감정 트렌드 분석기

    일간/주간/월간 감정 변화 추적 및 패턴 감지.

    Example:
        >>> analyzer = EmotionAnalyzer()
        >>> analysis = await analyzer.analyze_trend(
        ...     user_id="user123",
        ...     period="weekly",
        ...     emotion_history=[...]
        ... )
        >>> print(analysis.dominant_emotion)
        "joy"
    """

    def __init__(self):
        """EmotionAnalyzer 초기화"""
        logger.info("EmotionAnalyzer initialized")

    async def analyze_trend(
        self,
        user_id: str,
        emotion_history: List[Dict[str, Any]],
        period: str = "weekly"
    ) -> EmotionTrendAnalysis:
        """
        감정 트렌드 분석

        Args:
            user_id: 사용자 ID
            emotion_history: 감정 히스토리
                [
                    {
                        "timestamp": "2025-02-10T10:00:00",
                        "emotion": "joy",
                        "intensity": 0.8
                    },
                    ...
                ]
            period: 분석 기간 (daily/weekly/monthly)

        Returns:
            EmotionTrendAnalysis: 트렌드 분석 결과

        Raises:
            AnalysisError: 분석 실패 시

        Example:
            >>> analyzer = EmotionAnalyzer()
            >>> analysis = await analyzer.analyze_trend(
            ...     user_id="user123",
            ...     emotion_history=[
            ...         {"timestamp": "2025-02-10T10:00:00", "emotion": "joy", "intensity": 0.8},
            ...         {"timestamp": "2025-02-09T15:00:00", "emotion": "neutral", "intensity": 0.5}
            ...     ],
            ...     period="weekly"
            ... )
        """
        try:
            logger.debug(
                f"Analyzing emotion trend for user {user_id}",
                extra={"period": period, "history_count": len(emotion_history)}
            )

            if not emotion_history:
                raise AnalysisError("Empty emotion history")

            # 날짜 범위 계산
            start_date, end_date = self._calculate_date_range(emotion_history, period)

            # 감정 분포 계산
            emotion_distribution = self._calculate_emotion_distribution(emotion_history)
            dominant_emotion = self._get_dominant_emotion(emotion_distribution)

            # 트렌드 분석
            trend, trend_score = self._analyze_trend(emotion_history)

            # 패턴 감지
            pattern = self._detect_pattern(emotion_history)

            # 변동성 계산
            volatility = self._calculate_volatility(emotion_history)

            # 긍정/부정 비율
            positive_ratio, negative_ratio = self._calculate_sentiment_ratios(
                emotion_history
            )

            # 일별 감정 집계
            daily_emotions = self._aggregate_daily_emotions(emotion_history)

            # 인사이트 생성
            insights = self._generate_insights(
                emotion_distribution=emotion_distribution,
                trend=trend,
                pattern=pattern,
                volatility=volatility,
                positive_ratio=positive_ratio
            )

            result = EmotionTrendAnalysis(
                period=period,
                start_date=start_date,
                end_date=end_date,
                emotion_distribution=emotion_distribution,
                dominant_emotion=dominant_emotion,
                trend=trend,
                trend_score=trend_score,
                pattern=pattern,
                volatility=volatility,
                total_interactions=len(emotion_history),
                positive_ratio=positive_ratio,
                negative_ratio=negative_ratio,
                daily_emotions=daily_emotions,
                insights=insights
            )

            logger.info(
                "Emotion trend analyzed",
                extra={
                    "user_id": user_id,
                    "dominant_emotion": dominant_emotion,
                    "trend": trend.value,
                    "pattern": pattern.value
                }
            )

            return result

        except Exception as e:
            logger.error(f"Emotion trend analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to analyze emotion trend: {e}") from e

    async def compare_periods(
        self,
        user_id: str,
        current_period: List[Dict[str, Any]],
        previous_period: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        두 기간의 감정 비교

        Args:
            user_id: 사용자 ID
            current_period: 현재 기간 감정 히스토리
            previous_period: 이전 기간 감정 히스토리

        Returns:
            비교 결과
            {
                "emotion_shift": {...},
                "improvement_score": 0.15,
                "significant_changes": [...]
            }

        Example:
            >>> analyzer = EmotionAnalyzer()
            >>> comparison = await analyzer.compare_periods(
            ...     user_id="user123",
            ...     current_period=[...],  # 이번 주
            ...     previous_period=[...]  # 지난 주
            ... )
        """
        try:
            # 각 기간 분석
            current_dist = self._calculate_emotion_distribution(current_period)
            previous_dist = self._calculate_emotion_distribution(previous_period)

            # 감정 변화 계산
            emotion_shift = self._calculate_emotion_shift(
                current_dist,
                previous_dist
            )

            # 개선 점수 계산 (-1~1)
            improvement_score = self._calculate_improvement_score(
                current_period,
                previous_period
            )

            # 유의미한 변화 감지
            significant_changes = self._detect_significant_changes(
                current_dist,
                previous_dist,
                threshold=0.1
            )

            return {
                "user_id": user_id,
                "current_dominant": self._get_dominant_emotion(current_dist),
                "previous_dominant": self._get_dominant_emotion(previous_dist),
                "emotion_shift": emotion_shift,
                "improvement_score": improvement_score,
                "significant_changes": significant_changes,
                "comparison_summary": self._generate_comparison_summary(
                    improvement_score,
                    significant_changes
                )
            }

        except Exception as e:
            logger.error(f"Period comparison failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to compare periods: {e}") from e

    # ============================================
    # Private Helper Methods
    # ============================================

    def _calculate_date_range(
        self,
        emotion_history: List[Dict[str, Any]],
        period: str
    ) -> Tuple[str, str]:
        """날짜 범위 계산"""
        if not emotion_history:
            now = datetime.now()
            return now.isoformat(), now.isoformat()

        timestamps = [
            datetime.fromisoformat(e["timestamp"])
            for e in emotion_history
        ]
        start_date = min(timestamps).date().isoformat()
        end_date = max(timestamps).date().isoformat()

        return start_date, end_date

    def _calculate_emotion_distribution(
        self,
        emotion_history: List[Dict[str, Any]]
    ) -> EmotionDistribution:
        """감정 분포 계산"""
        emotion_counts = Counter(e["emotion"] for e in emotion_history)
        total = len(emotion_history)

        if total == 0:
            return EmotionDistribution()

        return EmotionDistribution(
            joy=emotion_counts.get("joy", 0) / total,
            sadness=emotion_counts.get("sadness", 0) / total,
            anger=emotion_counts.get("anger", 0) / total,
            fear=emotion_counts.get("fear", 0) / total,
            surprise=emotion_counts.get("surprise", 0) / total,
            neutral=emotion_counts.get("neutral", 0) / total
        )

    def _get_dominant_emotion(self, distribution: EmotionDistribution) -> str:
        """주요 감정 추출"""
        emotions = {
            "joy": distribution.joy,
            "sadness": distribution.sadness,
            "anger": distribution.anger,
            "fear": distribution.fear,
            "surprise": distribution.surprise,
            "neutral": distribution.neutral
        }
        return max(emotions, key=emotions.get)

    def _analyze_trend(
        self,
        emotion_history: List[Dict[str, Any]]
    ) -> Tuple[EmotionTrend, float]:
        """트렌드 분석 (선형 회귀)"""
        if len(emotion_history) < 3:
            return EmotionTrend.STABLE, 0.0

        # 감정을 긍정 점수로 변환 (joy=1, neutral=0, negative=-1)
        emotion_scores = []
        for e in emotion_history:
            emotion = e["emotion"]
            if emotion == "joy":
                score = 1.0
            elif emotion == "surprise":
                score = 0.5
            elif emotion == "neutral":
                score = 0.0
            elif emotion in ["sadness", "fear", "anger"]:
                score = -1.0
            else:
                score = 0.0

            emotion_scores.append(score)

        # 선형 회귀로 기울기 계산
        x = np.arange(len(emotion_scores))
        slope = np.polyfit(x, emotion_scores, 1)[0]

        # 기울기로 트렌드 판단
        if slope > 0.1:
            trend = EmotionTrend.IMPROVING
        elif slope < -0.1:
            trend = EmotionTrend.DECLINING
        else:
            # 변동성 확인
            volatility = np.std(emotion_scores)
            if volatility > 0.5:
                trend = EmotionTrend.VOLATILE
            else:
                trend = EmotionTrend.STABLE

        return trend, float(slope)

    def _detect_pattern(
        self,
        emotion_history: List[Dict[str, Any]]
    ) -> EmotionPattern:
        """감정 패턴 감지"""
        if len(emotion_history) < 7:
            return EmotionPattern.RANDOM

        # 감정을 숫자로 변환
        emotion_map = {
            "joy": 4, "surprise": 3, "neutral": 2,
            "sadness": 1, "fear": 0, "anger": 0
        }
        scores = [emotion_map.get(e["emotion"], 2) for e in emotion_history]

        # 표준편차로 일관성 판단
        std = np.std(scores)
        if std < 0.5:
            return EmotionPattern.CONSISTENT

        # 자기상관으로 주기 감지 (간단한 방법)
        # 실제로는 FFT나 ACF 사용
        if len(scores) >= 7:
            # 주간 패턴 확인 (7일 주기)
            weekly_corr = np.corrcoef(scores[:7], scores[-7:])[0, 1] if len(scores) >= 14 else 0
            if abs(weekly_corr) > 0.7:
                return EmotionPattern.WEEKLY_CYCLE

        return EmotionPattern.RANDOM

    def _calculate_volatility(
        self,
        emotion_history: List[Dict[str, Any]]
    ) -> float:
        """변동성 계산 (표준편차 정규화)"""
        if len(emotion_history) < 2:
            return 0.0

        emotion_map = {
            "joy": 1.0, "surprise": 0.5, "neutral": 0.0,
            "sadness": -0.5, "fear": -1.0, "anger": -1.0
        }
        scores = [emotion_map.get(e["emotion"], 0.0) for e in emotion_history]

        std = np.std(scores)
        # 0~2 범위를 0~1로 정규화
        return min(1.0, std / 2.0)

    def _calculate_sentiment_ratios(
        self,
        emotion_history: List[Dict[str, Any]]
    ) -> Tuple[float, float]:
        """긍정/부정 비율 계산"""
        if not emotion_history:
            return 0.0, 0.0

        positive = ["joy", "surprise"]
        negative = ["sadness", "fear", "anger"]

        positive_count = sum(1 for e in emotion_history if e["emotion"] in positive)
        negative_count = sum(1 for e in emotion_history if e["emotion"] in negative)
        total = len(emotion_history)

        return positive_count / total, negative_count / total

    def _aggregate_daily_emotions(
        self,
        emotion_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """일별 감정 집계"""
        daily_data = {}

        for e in emotion_history:
            date = datetime.fromisoformat(e["timestamp"]).date().isoformat()
            if date not in daily_data:
                daily_data[date] = []
            daily_data[date].append(e["emotion"])

        # 일별 주요 감정
        result = []
        for date, emotions in sorted(daily_data.items()):
            emotion_counts = Counter(emotions)
            dominant = emotion_counts.most_common(1)[0][0]
            result.append({
                "date": date,
                "dominant_emotion": dominant,
                "emotion_counts": dict(emotion_counts),
                "total_interactions": len(emotions)
            })

        return result

    def _generate_insights(
        self,
        emotion_distribution: EmotionDistribution,
        trend: EmotionTrend,
        pattern: EmotionPattern,
        volatility: float,
        positive_ratio: float
    ) -> List[str]:
        """인사이트 생성"""
        insights = []

        # 긍정 비율
        if positive_ratio > 0.7:
            insights.append("대부분의 시간을 긍정적인 감정으로 보내고 계세요 😊")
        elif positive_ratio < 0.3:
            insights.append("최근 부정적인 감정이 많으셨어요. 괜찮으신가요?")

        # 트렌드
        if trend == EmotionTrend.IMPROVING:
            insights.append("감정 상태가 점점 개선되고 있어요! 🌱")
        elif trend == EmotionTrend.DECLINING:
            insights.append("최근 감정이 조금 힘들어 보이네요")

        # 변동성
        if volatility > 0.7:
            insights.append("감정 변화가 크네요. 안정이 필요할 수 있어요")
        elif volatility < 0.3:
            insights.append("감정이 안정적으로 유지되고 있어요")

        # 패턴
        if pattern == EmotionPattern.CONSISTENT:
            insights.append("일관된 감정 패턴을 보이고 있어요")

        return insights

    def _calculate_emotion_shift(
        self,
        current: EmotionDistribution,
        previous: EmotionDistribution
    ) -> Dict[str, float]:
        """감정 변화 계산"""
        return {
            "joy": current.joy - previous.joy,
            "sadness": current.sadness - previous.sadness,
            "anger": current.anger - previous.anger,
            "fear": current.fear - previous.fear,
            "surprise": current.surprise - previous.surprise,
            "neutral": current.neutral - previous.neutral
        }

    def _calculate_improvement_score(
        self,
        current: List[Dict[str, Any]],
        previous: List[Dict[str, Any]]
    ) -> float:
        """개선 점수 계산 (-1~1)"""
        current_positive = sum(
            1 for e in current if e["emotion"] in ["joy", "surprise"]
        )
        previous_positive = sum(
            1 for e in previous if e["emotion"] in ["joy", "surprise"]
        )

        current_ratio = current_positive / len(current) if current else 0
        previous_ratio = previous_positive / len(previous) if previous else 0

        return current_ratio - previous_ratio

    def _detect_significant_changes(
        self,
        current: EmotionDistribution,
        previous: EmotionDistribution,
        threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """유의미한 변화 감지"""
        changes = []
        shift = self._calculate_emotion_shift(current, previous)

        for emotion, change in shift.items():
            if abs(change) >= threshold:
                changes.append({
                    "emotion": emotion,
                    "change": round(change, 3),
                    "direction": "increase" if change > 0 else "decrease"
                })

        return changes

    def _generate_comparison_summary(
        self,
        improvement_score: float,
        significant_changes: List[Dict[str, Any]]
    ) -> str:
        """비교 요약 생성"""
        if improvement_score > 0.1:
            summary = "이전 기간보다 감정 상태가 개선되었어요"
        elif improvement_score < -0.1:
            summary = "이전 기간보다 감정 상태가 저하되었어요"
        else:
            summary = "이전 기간과 비슷한 감정 상태를 유지하고 있어요"

        if significant_changes:
            top_change = max(significant_changes, key=lambda x: abs(x["change"]))
            summary += f" ({top_change['emotion']} {top_change['direction']})"

        return summary


# ============================================
# 8. Export
# ============================================
__all__ = [
    "EmotionAnalyzer",
    "EmotionTrendAnalysis",
    "EmotionDistribution",
    "EmotionTrend",
    "EmotionPattern",
]

logger.info("Emotion analyzer module loaded")
