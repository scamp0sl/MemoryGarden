"""
분석 리포트 생성기

주간/월간 감정 요약 및 성장 지표 리포트 생성.
보호자 대시보드 및 의료기관 연계용 데이터 제공.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

# ============================================
# 2. Third-Party Imports
# ============================================
from pydantic import BaseModel, Field
import numpy as np

# ============================================
# 3. Local Imports
# ============================================
from core.analysis.emotion_analyzer import (
    EmotionAnalyzer,
    EmotionTrendAnalysis,
    EmotionTrend
)
from core.analysis.garden_mapper import GardenMapper, GardenVisualizationData
from database.redis_client import RedisClient
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
REPORT_PERIODS = ["weekly", "monthly"]
RISK_LEVEL_COLORS = {
    "GREEN": "#4CAF50",
    "YELLOW": "#FFC107",
    "ORANGE": "#FF9800",
    "RED": "#F44336"
}


# ============================================
# 6. Enum 정의
# ============================================
class ReportPeriod(str, Enum):
    """리포트 기간"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportType(str, Enum):
    """리포트 유형"""
    GUARDIAN = "guardian"  # 보호자용 (친근한 설명)
    CLINICAL = "clinical"  # 의료기관용 (전문 용어)


# ============================================
# 7. Pydantic 모델
# ============================================
class CognitiveMetrics(BaseModel):
    """인지 기능 지표"""
    mcdi_average: float = Field(description="평균 MCDI 점수")
    mcdi_min: float = Field(description="최저 MCDI 점수")
    mcdi_max: float = Field(description="최고 MCDI 점수")
    mcdi_trend: str = Field(description="추세 (improving/stable/declining)")
    slope: float = Field(description="주간 변화율")

    # 6개 하위 지표 (선택)
    lr_average: Optional[float] = None
    sd_average: Optional[float] = None
    nc_average: Optional[float] = None
    to_average: Optional[float] = None
    er_average: Optional[float] = None
    rt_average: Optional[float] = None


class EngagementMetrics(BaseModel):
    """참여도 지표"""
    total_conversations: int = Field(ge=0, description="총 대화 횟수")
    conversation_per_day: float = Field(description="일평균 대화 횟수")
    consecutive_days: int = Field(ge=0, description="연속 참여 일수")
    response_rate: float = Field(ge=0, le=1, description="응답률")
    average_response_time: float = Field(description="평균 응답 시간 (분)")


class GrowthMetrics(BaseModel):
    """성장 지표"""
    flowers_earned: int = Field(ge=0, description="획득한 꽃 개수")
    butterflies_earned: int = Field(ge=0, description="나비 방문 횟수")
    garden_level: int = Field(ge=1, le=10, description="정원 레벨")
    achievements_unlocked: List[str] = Field(default_factory=list, description="달성한 업적")
    season_badge: Optional[str] = None


class WeeklyReport(BaseModel):
    """주간 리포트

    보호자가 매주 받는 요약 리포트.
    """
    user_id: str
    user_name: str
    period_start: datetime
    period_end: datetime
    report_type: ReportType = ReportType.GUARDIAN

    # 감정 분석
    emotion_analysis: EmotionTrendAnalysis

    # 인지 기능
    cognitive_metrics: CognitiveMetrics

    # 참여도
    engagement_metrics: EngagementMetrics

    # 성장
    growth_metrics: GrowthMetrics

    # 관찰 사항
    observations: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # 위험도
    current_risk_level: str
    risk_change: Optional[str] = None  # "improved", "worsened", "stable"

    generated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MonthlyReport(BaseModel):
    """월간 리포트

    더 상세한 분석 및 임상 데이터 포함.
    """
    user_id: str
    user_name: str
    period_start: datetime
    period_end: datetime
    report_type: ReportType = ReportType.CLINICAL

    # 주간 리포트 요약
    weekly_summaries: List[WeeklyReport]

    # 월간 감정 분석
    emotion_analysis: EmotionTrendAnalysis

    # 월간 인지 기능
    cognitive_metrics: CognitiveMetrics

    # 월간 참여도
    engagement_metrics: EngagementMetrics

    # 월간 성장
    growth_metrics: GrowthMetrics

    # 상세 분석
    detailed_observations: str
    clinical_summary: str

    # 위험도 변화
    risk_level_history: List[Dict[str, Any]]

    # 권장 조치
    medical_recommendations: List[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# 8. ReportGenerator 클래스
# ============================================
class ReportGenerator:
    """분석 리포트 생성기

    주간/월간 감정 요약, 성장 지표, 권장 조치 리포트 생성.

    Attributes:
        emotion_analyzer: 감정 분석기
        garden_mapper: 정원 매핑기
        redis_client: Redis 클라이언트

    Example:
        >>> generator = ReportGenerator()
        >>> report = await generator.generate_weekly_report("user123")
        >>> print(report.cognitive_metrics.mcdi_average)
        75.5
    """

    def __init__(
        self,
        emotion_analyzer: Optional[EmotionAnalyzer] = None,
        garden_mapper: Optional[GardenMapper] = None,
        redis_client: Optional[RedisClient] = None
    ):
        """
        ReportGenerator 초기화

        Args:
            emotion_analyzer: 감정 분석기 (None이면 생성)
            garden_mapper: 정원 매핑기 (None이면 생성)
            redis_client: Redis 클라이언트 (None이면 생성)
        """
        self.emotion_analyzer = emotion_analyzer or EmotionAnalyzer()
        self.garden_mapper = garden_mapper or GardenMapper()
        self.redis = redis_client or RedisClient()
        logger.info("ReportGenerator initialized")

    async def generate_weekly_report(
        self,
        user_id: str,
        user_name: str,
        period: str = "last_week",
        report_type: ReportType = ReportType.GUARDIAN
    ) -> WeeklyReport:
        """
        주간 리포트 생성

        Args:
            user_id: 사용자 ID
            user_name: 사용자 이름
            period: "last_week" 또는 커스텀 기간
            report_type: guardian(보호자용) / clinical(의료기관용)

        Returns:
            주간 리포트

        Example:
            >>> report = await generator.generate_weekly_report(
            ...     user_id="user123",
            ...     user_name="홍길동"
            ... )
            >>> print(report.cognitive_metrics.mcdi_average)
            75.5
        """
        logger.info(f"Generating weekly report for user: {user_id}")

        # 1. 기간 계산
        period_end = datetime.now()
        period_start = period_end - timedelta(days=7)

        # 2. 데이터 수집
        emotion_history = await self._get_emotion_history(
            user_id, period_start, period_end
        )
        mcdi_history = await self._get_mcdi_history(
            user_id, period_start, period_end
        )
        garden_status = await self.garden_mapper.get_garden_status(user_id)

        # 3. 감정 분석
        emotion_analysis = await self.emotion_analyzer.analyze_trend(
            user_id, emotion_history, period="weekly"
        )

        # 4. 인지 기능 지표
        cognitive_metrics = self._calculate_cognitive_metrics(mcdi_history)

        # 5. 참여도 지표
        engagement_metrics = await self._calculate_engagement_metrics(
            user_id, period_start, period_end
        )

        # 6. 성장 지표
        growth_metrics = self._extract_growth_metrics(garden_status)

        # 7. 관찰 사항 생성
        observations = self._generate_observations(
            emotion_analysis, cognitive_metrics, engagement_metrics
        )

        # 8. 우려 사항 체크
        concerns = self._identify_concerns(
            cognitive_metrics, engagement_metrics
        )

        # 9. 권장 조치
        recommendations = self._generate_recommendations(
            concerns, report_type
        )

        # 10. 위험도
        current_risk = await self._get_current_risk_level(user_id)
        risk_change = await self._calculate_risk_change(user_id, period_start)

        # 11. 리포트 생성
        report = WeeklyReport(
            user_id=user_id,
            user_name=user_name,
            period_start=period_start,
            period_end=period_end,
            report_type=report_type,
            emotion_analysis=emotion_analysis,
            cognitive_metrics=cognitive_metrics,
            engagement_metrics=engagement_metrics,
            growth_metrics=growth_metrics,
            observations=observations,
            concerns=concerns,
            recommendations=recommendations,
            current_risk_level=current_risk,
            risk_change=risk_change
        )

        logger.info(
            f"Weekly report generated",
            extra={
                "user_id": user_id,
                "mcdi_average": cognitive_metrics.mcdi_average,
                "risk_level": current_risk
            }
        )

        return report

    async def generate_monthly_report(
        self,
        user_id: str,
        user_name: str,
        report_type: ReportType = ReportType.CLINICAL
    ) -> MonthlyReport:
        """
        월간 리포트 생성

        Args:
            user_id: 사용자 ID
            user_name: 사용자 이름
            report_type: guardian(보호자용) / clinical(의료기관용)

        Returns:
            월간 리포트

        Example:
            >>> report = await generator.generate_monthly_report(
            ...     user_id="user123",
            ...     user_name="홍길동",
            ...     report_type=ReportType.CLINICAL
            ... )
        """
        logger.info(f"Generating monthly report for user: {user_id}")

        # 1. 기간 계산
        period_end = datetime.now()
        period_start = period_end - timedelta(days=30)

        # 2. 주간 리포트 수집 (최근 4주)
        weekly_summaries = []
        for week in range(4):
            week_end = period_end - timedelta(days=week * 7)
            week_start = week_end - timedelta(days=7)

            # 각 주간 리포트 생성
            try:
                weekly_report = await self.generate_weekly_report(
                    user_id=user_id,
                    user_name=user_name,
                    report_type=report_type
                )
                weekly_summaries.append(weekly_report)
            except Exception as e:
                logger.warning(f"Failed to generate week {week} report: {e}")

        # 3. 월간 데이터 수집
        emotion_history = await self._get_emotion_history(
            user_id, period_start, period_end
        )
        mcdi_history = await self._get_mcdi_history(
            user_id, period_start, period_end
        )
        garden_status = await self.garden_mapper.get_garden_status(user_id)

        # 4. 월간 분석
        emotion_analysis = await self.emotion_analyzer.analyze_trend(
            user_id, emotion_history, period="monthly"
        )
        cognitive_metrics = self._calculate_cognitive_metrics(mcdi_history)
        engagement_metrics = await self._calculate_engagement_metrics(
            user_id, period_start, period_end
        )
        growth_metrics = self._extract_growth_metrics(garden_status)

        # 5. 상세 관찰 (의료기관용)
        detailed_observations = self._generate_detailed_observations(
            emotion_analysis,
            cognitive_metrics,
            engagement_metrics,
            weekly_summaries
        )

        # 6. 임상 요약
        clinical_summary = self._generate_clinical_summary(
            cognitive_metrics,
            emotion_analysis
        )

        # 7. 위험도 변화 이력
        risk_history = await self._get_risk_history(user_id, period_start, period_end)

        # 8. 의료 권장 조치
        medical_recommendations = self._generate_medical_recommendations(
            cognitive_metrics,
            emotion_analysis,
            risk_history
        )

        # 9. 월간 리포트 생성
        report = MonthlyReport(
            user_id=user_id,
            user_name=user_name,
            period_start=period_start,
            period_end=period_end,
            report_type=report_type,
            weekly_summaries=weekly_summaries,
            emotion_analysis=emotion_analysis,
            cognitive_metrics=cognitive_metrics,
            engagement_metrics=engagement_metrics,
            growth_metrics=growth_metrics,
            detailed_observations=detailed_observations,
            clinical_summary=clinical_summary,
            risk_level_history=risk_history,
            medical_recommendations=medical_recommendations
        )

        logger.info(
            f"Monthly report generated",
            extra={
                "user_id": user_id,
                "weeks_included": len(weekly_summaries),
                "mcdi_average": cognitive_metrics.mcdi_average
            }
        )

        return report

    # ============================================
    # Private Helper Methods
    # ============================================

    async def _get_emotion_history(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """감정 이력 조회 (Redis에서)"""
        # TODO: 실제로는 TimescaleDB에서 조회
        # 현재는 Redis 임시 저장소 사용
        key = f"emotion_history:{user_id}"
        data = await self.redis.get(key) or []

        # 기간 필터링
        filtered = [
            entry for entry in data
            if start_date <= datetime.fromisoformat(entry["timestamp"]) <= end_date
        ]

        return filtered

    async def _get_mcdi_history(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """MCDI 점수 이력 조회"""
        # TODO: 실제로는 TimescaleDB에서 조회
        key = f"mcdi_history:{user_id}"
        data = await self.redis.get(key) or []

        filtered = [
            entry for entry in data
            if start_date <= datetime.fromisoformat(entry["timestamp"]) <= end_date
        ]

        return filtered

    def _calculate_cognitive_metrics(
        self,
        mcdi_history: List[Dict[str, Any]]
    ) -> CognitiveMetrics:
        """인지 기능 지표 계산"""
        if not mcdi_history:
            return CognitiveMetrics(
                mcdi_average=0.0,
                mcdi_min=0.0,
                mcdi_max=0.0,
                mcdi_trend="unknown",
                slope=0.0
            )

        scores = [entry["mcdi_score"] for entry in mcdi_history]

        # 평균, 최소, 최대
        mcdi_avg = np.mean(scores)
        mcdi_min = np.min(scores)
        mcdi_max = np.max(scores)

        # 선형 회귀 (추세)
        if len(scores) >= 2:
            x = np.arange(len(scores))
            slope, _ = np.polyfit(x, scores, 1)

            if slope > 0.5:
                trend = "improving"
            elif slope < -0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            slope = 0.0
            trend = "stable"

        return CognitiveMetrics(
            mcdi_average=round(mcdi_avg, 2),
            mcdi_min=round(mcdi_min, 2),
            mcdi_max=round(mcdi_max, 2),
            mcdi_trend=trend,
            slope=round(slope, 3)
        )

    async def _calculate_engagement_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> EngagementMetrics:
        """참여도 지표 계산"""
        # TODO: 실제로는 PostgreSQL에서 조회
        key = f"conversations:{user_id}"
        conversations = await self.redis.get(key) or []

        # 기간 필터링
        period_conversations = [
            conv for conv in conversations
            if start_date <= datetime.fromisoformat(conv["timestamp"]) <= end_date
        ]

        total_count = len(period_conversations)
        days = (end_date - start_date).days or 1
        conv_per_day = total_count / days

        # 연속 일수 (정원에서 가져오기)
        garden_status = await self.garden_mapper.get_garden_status(user_id)
        consecutive_days = garden_status.consecutive_days

        # 응답률 (보낸 질문 대비 응답)
        # TODO: 실제 구현 필요
        response_rate = 0.9  # 임시값

        # 평균 응답 시간
        response_times = [
            conv.get("response_time_minutes", 10)
            for conv in period_conversations
        ]
        avg_response_time = np.mean(response_times) if response_times else 10.0

        return EngagementMetrics(
            total_conversations=total_count,
            conversation_per_day=round(conv_per_day, 2),
            consecutive_days=consecutive_days,
            response_rate=round(response_rate, 2),
            average_response_time=round(avg_response_time, 1)
        )

    def _extract_growth_metrics(
        self,
        garden_status: GardenVisualizationData
    ) -> GrowthMetrics:
        """성장 지표 추출"""
        return GrowthMetrics(
            flowers_earned=garden_status.flower_count,
            butterflies_earned=garden_status.butterfly_count,
            garden_level=garden_status.garden_level,
            achievements_unlocked=[],  # TODO: Redis에서 조회
            season_badge=garden_status.season_badge
        )

    def _generate_observations(
        self,
        emotion: EmotionTrendAnalysis,
        cognitive: CognitiveMetrics,
        engagement: EngagementMetrics
    ) -> List[str]:
        """관찰 사항 생성 (보호자용)"""
        observations = []

        # 감정 관찰
        if emotion.dominant_emotion:
            observations.append(
                f"이번 주 주된 감정은 '{emotion.dominant_emotion}' 이었어요"
            )

        if emotion.trend == EmotionTrend.IMPROVING:
            observations.append("감정 상태가 점점 좋아지고 있어요 😊")
        elif emotion.trend == EmotionTrend.DECLINING:
            observations.append("감정 상태가 다소 저조해 보여요")

        # 인지 기능 관찰
        if cognitive.mcdi_trend == "improving":
            observations.append("인지 기능이 개선되고 있어요 👍")
        elif cognitive.mcdi_trend == "declining":
            observations.append("인지 기능이 조금 낮아졌어요")

        # 참여도 관찰
        if engagement.consecutive_days >= 7:
            observations.append(
                f"7일 연속 참여 중이에요! ({engagement.consecutive_days}일) 🎉"
            )

        return observations

    def _identify_concerns(
        self,
        cognitive: CognitiveMetrics,
        engagement: EngagementMetrics
    ) -> List[str]:
        """우려 사항 체크"""
        concerns = []

        # MCDI 급격한 하락
        if cognitive.slope < -1.5:
            concerns.append("인지 기능 점수가 빠르게 낮아지고 있어요")

        # MCDI 낮은 점수
        if cognitive.mcdi_average < 50:
            concerns.append("인지 기능 점수가 평균보다 낮아요")

        # 참여도 낮음
        if engagement.conversation_per_day < 1.0:
            concerns.append("대화 참여가 줄어들고 있어요")

        # 응답 지연
        if engagement.average_response_time > 30:
            concerns.append("응답 시간이 길어지고 있어요")

        return concerns

    def _generate_recommendations(
        self,
        concerns: List[str],
        report_type: ReportType
    ) -> List[str]:
        """권장 조치 생성"""
        if not concerns:
            return ["현재 상태가 양호합니다. 계속 대화를 이어가주세요! 😊"]

        recommendations = []

        if report_type == ReportType.GUARDIAN:
            recommendations.extend([
                "매일 규칙적인 시간에 대화해보세요",
                "어르신이 좋아하는 주제로 대화를 유도해보세요",
                "변화가 계속되면 전문가 상담을 권장드려요"
            ])
        else:  # CLINICAL
            recommendations.extend([
                "Cognitive screening recommended",
                "Monitor for further decline over 2 weeks",
                "Consider referral to memory clinic if trend continues"
            ])

        return recommendations

    async def _get_current_risk_level(self, user_id: str) -> str:
        """현재 위험도 조회"""
        # TODO: 실제 구현
        return "GREEN"

    async def _calculate_risk_change(
        self,
        user_id: str,
        period_start: datetime
    ) -> Optional[str]:
        """위험도 변화 계산"""
        # TODO: 실제 구현
        return "stable"

    async def _get_risk_history(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """위험도 변화 이력"""
        # TODO: TimescaleDB에서 조회
        return []

    def _generate_detailed_observations(
        self,
        emotion: EmotionTrendAnalysis,
        cognitive: CognitiveMetrics,
        engagement: EngagementMetrics,
        weekly_summaries: List[WeeklyReport]
    ) -> str:
        """상세 관찰 (의료기관용)"""
        observations = []

        observations.append(f"## Cognitive Function\n")
        observations.append(f"- Average MCDI: {cognitive.mcdi_average}")
        observations.append(f"- Trend: {cognitive.mcdi_trend} (slope: {cognitive.slope}/week)")

        observations.append(f"\n## Emotional State\n")
        observations.append(f"- Dominant emotion: {emotion.dominant_emotion}")
        observations.append(f"- Trend: {emotion.trend.value}")
        observations.append(f"- Volatility: {emotion.volatility:.2f}")

        observations.append(f"\n## Engagement\n")
        observations.append(f"- Total conversations: {engagement.total_conversations}")
        observations.append(f"- Average per day: {engagement.conversation_per_day}")
        observations.append(f"- Consecutive days: {engagement.consecutive_days}")

        return "\n".join(observations)

    def _generate_clinical_summary(
        self,
        cognitive: CognitiveMetrics,
        emotion: EmotionTrendAnalysis
    ) -> str:
        """임상 요약"""
        summary = f"""
Patient demonstrates:
- MCDI score: {cognitive.mcdi_average} ({cognitive.mcdi_trend})
- Emotional state: {emotion.trend.value}
- Pattern: {emotion.pattern.value}

Clinical interpretation:
"""

        if cognitive.mcdi_average >= 70:
            summary += "Normal cognitive function maintained.\n"
        elif cognitive.mcdi_average >= 50:
            summary += "Mild cognitive changes observed. Monitoring recommended.\n"
        else:
            summary += "Significant cognitive decline. Clinical assessment recommended.\n"

        return summary.strip()

    def _generate_medical_recommendations(
        self,
        cognitive: CognitiveMetrics,
        emotion: EmotionTrendAnalysis,
        risk_history: List[Dict[str, Any]]
    ) -> List[str]:
        """의료 권장 조치"""
        recommendations = []

        if cognitive.mcdi_average < 50:
            recommendations.append("Recommend comprehensive cognitive assessment (MMSE/MoCA)")

        if cognitive.slope < -1.5:
            recommendations.append("Monitor closely for rapid decline")

        if emotion.volatility > 0.5:
            recommendations.append("Consider mood disorder screening")

        if not recommendations:
            recommendations.append("Continue routine monitoring")

        return recommendations


# ============================================
# 9. Export
# ============================================
__all__ = [
    "ReportGenerator",
    "WeeklyReport",
    "MonthlyReport",
    "CognitiveMetrics",
    "EngagementMetrics",
    "GrowthMetrics",
    "ReportPeriod",
    "ReportType",
]

logger.info("Report generator module loaded")
