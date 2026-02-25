"""
정원 상태 매핑기

감정 상태 및 MCDI 점수를 정원 시각화 데이터로 변환.
SPEC.md 2.2.1 게이미피케이션 규칙 적용.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from enum import Enum

# ============================================
# 2. Third-Party Imports
# ============================================
from pydantic import BaseModel, Field

# ============================================
# 3. Local Imports
# ============================================
from database.redis_client import RedisClient
from utils.logger import get_logger
from utils.exceptions import MemoryGardenError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
# 게임 메카닉 (SPEC.md 2.2.1)
FLOWER_PER_CONVERSATION = 1  # 1회 대화 = 1송이 꽃
BUTTERFLY_CONSECUTIVE_DAYS = 3  # 3일 연속 참여 = 나비 방문
GARDEN_EXPANSION_DAYS = 7  # 7일 연속 참여 = 정원 확장
SEASON_BADGE_DAYS = 30  # 한 달 참여 = 계절 뱃지

# MCDI 위험도 임계값 (SPEC.md 2.1.3)
MCDI_GREEN_THRESHOLD = 70
MCDI_YELLOW_THRESHOLD = 50
MCDI_ORANGE_THRESHOLD = 30


# ============================================
# 6. Enum 정의
# ============================================
class RiskLevel(str, Enum):
    """위험도 레벨"""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"


class GardenWeather(str, Enum):
    """정원 날씨 상태"""
    SUNNY = "sunny"  # 맑음 (GREEN)
    CLOUDY = "cloudy"  # 흐림 (YELLOW)
    RAINY = "rainy"  # 비 (ORANGE)
    STORMY = "stormy"  # 폭풍 (RED)


class SeasonBadge(str, Enum):
    """계절 뱃지"""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


# ============================================
# 7. Pydantic 모델
# ============================================
class GardenVisualizationData(BaseModel):
    """정원 시각화 데이터

    프론트엔드에서 정원을 렌더링하는데 필요한 모든 정보.
    """
    user_id: str

    # 게임 메카닉
    flower_count: int = Field(ge=0, description="총 꽃 개수 (1대화=1꽃)")
    butterfly_count: int = Field(ge=0, description="나비 방문 횟수 (3일연속=1나비)")
    garden_level: int = Field(ge=1, le=10, description="정원 레벨 (7일연속마다 +1)")
    consecutive_days: int = Field(ge=0, description="연속 참여 일수")
    total_conversations: int = Field(ge=0, description="총 대화 횟수")

    # 정원 상태
    weather: GardenWeather = Field(description="날씨 상태 (MCDI 기반)")
    season_badge: Optional[SeasonBadge] = Field(None, description="계절 뱃지")

    # 메시지
    status_message: str = Field(description="정원 상태 메시지")
    achievement_message: Optional[str] = Field(None, description="업적 달성 메시지")

    # 메타데이터
    last_interaction_at: Optional[datetime] = None
    next_milestone: Optional[str] = Field(None, description="다음 목표")
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GardenStatusUpdate(BaseModel):
    """정원 상태 업데이트 결과"""
    previous_status: GardenVisualizationData
    current_status: GardenVisualizationData
    achievements_unlocked: list[str] = Field(default_factory=list)
    level_up: bool = False
    new_badge: Optional[SeasonBadge] = None


# ============================================
# 8. GardenMapper 클래스
# ============================================
class GardenMapper:
    """정원 상태 매핑기

    MCDI 점수, 감정 상태, 대화 이력을 정원 시각화 데이터로 변환.
    게이미피케이션 로직 적용 (꽃, 나비, 정원 확장).

    Attributes:
        redis_client: Redis 클라이언트 (임시 저장소)

    Example:
        >>> mapper = GardenMapper()
        >>> status = await mapper.update_garden_status(
        ...     user_id="user123",
        ...     mcdi_score=75.0,
        ...     risk_level="GREEN"
        ... )
        >>> print(status.flower_count)
        42
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        GardenMapper 초기화

        Args:
            redis_client: Redis 클라이언트 (None이면 생성)
        """
        self.redis = redis_client or RedisClient()
        logger.info("GardenMapper initialized")

    async def update_garden_status(
        self,
        user_id: str,
        mcdi_score: Optional[float] = None,
        risk_level: Optional[str] = None,
        emotion: Optional[str] = None
    ) -> GardenStatusUpdate:
        """
        정원 상태 업데이트

        대화 완료 시 호출되어 정원 상태를 업데이트하고 업적을 체크.

        Args:
            user_id: 사용자 ID
            mcdi_score: MCDI 점수 (선택)
            risk_level: 위험도 레벨 (선택)
            emotion: 현재 감정 (선택)

        Returns:
            업데이트 결과 (이전/현재 상태, 업적)

        Example:
            >>> status = await mapper.update_garden_status(
            ...     user_id="user123",
            ...     mcdi_score=75.0,
            ...     risk_level="GREEN"
            ... )
            >>> print(status.achievements_unlocked)
            ["butterfly_visit", "garden_expansion"]
        """
        logger.info(f"Updating garden status for user: {user_id}")

        # 1. 현재 상태 조회
        previous_status = await self.get_garden_status(user_id)

        # 2. 대화 횟수 증가 (꽃 심기)
        new_flower_count = previous_status.flower_count + FLOWER_PER_CONVERSATION
        new_total_conversations = previous_status.total_conversations + 1

        # 3. 연속 참여 일수 계산
        new_consecutive_days = await self._calculate_consecutive_days(
            user_id,
            previous_status.last_interaction_at
        )

        # 4. 나비 방문 횟수 계산
        new_butterfly_count = new_consecutive_days // BUTTERFLY_CONSECUTIVE_DAYS

        # 5. 정원 레벨 계산
        new_garden_level = min(10, 1 + (new_consecutive_days // GARDEN_EXPANSION_DAYS))

        # 6. 계절 뱃지 체크
        new_season_badge = await self._check_season_badge(user_id, new_total_conversations)

        # 7. 날씨 상태 매핑 (MCDI 기반)
        weather = self._map_risk_to_weather(risk_level or "GREEN")

        # 8. 상태 메시지 생성
        status_message = self._generate_status_message(weather, new_consecutive_days)

        # 9. 다음 목표 메시지
        next_milestone = self._generate_next_milestone(
            new_consecutive_days,
            new_garden_level
        )

        # 10. 현재 상태 생성
        current_status = GardenVisualizationData(
            user_id=user_id,
            flower_count=new_flower_count,
            butterfly_count=new_butterfly_count,
            garden_level=new_garden_level,
            consecutive_days=new_consecutive_days,
            total_conversations=new_total_conversations,
            weather=weather,
            season_badge=new_season_badge,
            status_message=status_message,
            next_milestone=next_milestone,
            last_interaction_at=datetime.now()
        )

        # 11. 업적 체크
        achievements_unlocked = self._check_achievements(
            previous_status, current_status
        )

        # 12. 레벨 업 체크
        level_up = current_status.garden_level > previous_status.garden_level

        # 13. 업적 메시지 생성
        achievement_message = self._generate_achievement_message(achievements_unlocked)
        if achievement_message:
            current_status.achievement_message = achievement_message

        # 14. Redis 저장
        await self._save_garden_status(current_status)

        # 15. 결과 반환
        result = GardenStatusUpdate(
            previous_status=previous_status,
            current_status=current_status,
            achievements_unlocked=achievements_unlocked,
            level_up=level_up,
            new_badge=new_season_badge if new_season_badge != previous_status.season_badge else None
        )

        logger.info(
            f"Garden status updated",
            extra={
                "user_id": user_id,
                "flower_count": new_flower_count,
                "consecutive_days": new_consecutive_days,
                "achievements": achievements_unlocked
            }
        )

        return result

    async def get_garden_status(self, user_id: str) -> GardenVisualizationData:
        """
        현재 정원 상태 조회

        Args:
            user_id: 사용자 ID

        Returns:
            정원 시각화 데이터

        Example:
            >>> status = await mapper.get_garden_status("user123")
            >>> print(status.flower_count)
            42
        """
        key = f"garden:{user_id}"
        data = await self.redis.get(key)

        if data:
            return GardenVisualizationData(**data)

        # 첫 방문: 기본 상태 생성
        default_status = GardenVisualizationData(
            user_id=user_id,
            flower_count=0,
            butterfly_count=0,
            garden_level=1,
            consecutive_days=0,
            total_conversations=0,
            weather=GardenWeather.SUNNY,
            status_message="정원을 처음 만드셨네요! 🌱 함께 가꿔나가요!",
            next_milestone="첫 대화를 완료하면 꽃이 피어나요!"
        )

        await self._save_garden_status(default_status)
        return default_status

    def _map_risk_to_weather(self, risk_level: str) -> GardenWeather:
        """
        위험도를 날씨로 매핑

        SPEC.md 2.1.3 기준:
        - GREEN: 맑음 (건강하게 자라고 있어요)
        - YELLOW: 흐림 (구름이 조금 낀 것 같아요)
        - ORANGE: 비 (비가 내리고 있어요)
        - RED: 폭풍 (긴급 상태)
        """
        mapping = {
            "GREEN": GardenWeather.SUNNY,
            "YELLOW": GardenWeather.CLOUDY,
            "ORANGE": GardenWeather.RAINY,
            "RED": GardenWeather.STORMY
        }
        return mapping.get(risk_level, GardenWeather.SUNNY)

    def _generate_status_message(
        self,
        weather: GardenWeather,
        consecutive_days: int
    ) -> str:
        """정원 상태 메시지 생성"""
        weather_messages = {
            GardenWeather.SUNNY: "정원이 건강하게 자라고 있어요! ☀️",
            GardenWeather.CLOUDY: "정원에 구름이 조금 낀 것 같아요 ☁️",
            GardenWeather.RAINY: "정원에 비가 내리고 있어요 🌧️",
            GardenWeather.STORMY: "정원에 폭풍이 불고 있어요 ⛈️"
        }

        base_message = weather_messages.get(weather, weather_messages[GardenWeather.SUNNY])

        # 연속 일수 축하 메시지 추가
        if consecutive_days > 0 and consecutive_days % 7 == 0:
            base_message += f" {consecutive_days}일 연속 참여 중이에요! 🎉"

        return base_message

    def _generate_next_milestone(
        self,
        consecutive_days: int,
        garden_level: int
    ) -> str:
        """다음 목표 메시지 생성"""
        # 나비 방문까지 남은 일수
        days_to_butterfly = BUTTERFLY_CONSECUTIVE_DAYS - (consecutive_days % BUTTERFLY_CONSECUTIVE_DAYS)
        if days_to_butterfly == BUTTERFLY_CONSECUTIVE_DAYS:
            days_to_butterfly = 0

        # 정원 확장까지 남은 일수
        days_to_expansion = GARDEN_EXPANSION_DAYS - (consecutive_days % GARDEN_EXPANSION_DAYS)
        if days_to_expansion == GARDEN_EXPANSION_DAYS:
            days_to_expansion = 0

        if days_to_butterfly > 0 and days_to_butterfly <= days_to_expansion:
            return f"🦋 {days_to_butterfly}일 더 참여하면 나비가 날아와요!"
        elif days_to_expansion > 0 and garden_level < 10:
            return f"🌳 {days_to_expansion}일 더 참여하면 정원이 확장돼요!"
        elif garden_level >= 10:
            return "🏆 최고 레벨 정원이에요! 계속 가꿔주세요!"
        else:
            return "매일 방문해서 정원을 가꿔주세요! 🌱"

    def _check_achievements(
        self,
        previous: GardenVisualizationData,
        current: GardenVisualizationData
    ) -> list[str]:
        """업적 달성 체크"""
        achievements = []

        # 첫 꽃 심기
        if previous.flower_count == 0 and current.flower_count == 1:
            achievements.append("first_flower")

        # 나비 방문 (새로 생김)
        if current.butterfly_count > previous.butterfly_count:
            achievements.append("butterfly_visit")

        # 정원 확장 (레벨 업)
        if current.garden_level > previous.garden_level:
            achievements.append("garden_expansion")

        # 꽃 개수 마일스톤
        flower_milestones = [10, 50, 100, 200, 500]
        for milestone in flower_milestones:
            if previous.flower_count < milestone <= current.flower_count:
                achievements.append(f"flowers_{milestone}")

        # 연속 일수 마일스톤
        consecutive_milestones = [7, 14, 30, 60, 100]
        for milestone in consecutive_milestones:
            if previous.consecutive_days < milestone <= current.consecutive_days:
                achievements.append(f"streak_{milestone}days")

        return achievements

    def _generate_achievement_message(self, achievements: list[str]) -> Optional[str]:
        """업적 메시지 생성"""
        if not achievements:
            return None

        messages = {
            "first_flower": "🌸 첫 번째 꽃이 피었어요!",
            "butterfly_visit": "🦋 나비가 날아왔어요!",
            "garden_expansion": "🌳 정원이 확장되었어요!",
            "flowers_10": "🌺 꽃 10송이 달성!",
            "flowers_50": "🌻 꽃 50송이 달성!",
            "flowers_100": "🌹 꽃 100송이 달성!",
            "flowers_200": "💐 꽃 200송이 달성!",
            "flowers_500": "🏵️ 꽃 500송이 달성!",
            "streak_7days": "⭐ 7일 연속 참여!",
            "streak_14days": "⭐⭐ 2주 연속 참여!",
            "streak_30days": "🏅 한 달 연속 참여!",
            "streak_60days": "🏆 두 달 연속 참여!",
            "streak_100days": "👑 100일 연속 참여!"
        }

        # 가장 중요한 업적 하나만 표시
        priority = [
            "streak_100days", "streak_60days", "streak_30days",
            "flowers_500", "flowers_200", "flowers_100",
            "garden_expansion", "butterfly_visit", "first_flower"
        ]

        for key in priority:
            if key in achievements:
                return messages.get(key)

        # 그 외 첫 번째 업적
        return messages.get(achievements[0], "🎉 새로운 업적 달성!")

    async def _calculate_consecutive_days(
        self,
        user_id: str,
        last_interaction_at: Optional[datetime]
    ) -> int:
        """
        연속 참여 일수 계산

        - 오늘 첫 방문: 연속 일수 +1
        - 어제 방문 후 오늘 방문: 연속 유지
        - 2일 이상 공백: 연속 초기화 (1부터 시작)
        """
        if not last_interaction_at:
            return 1  # 첫 방문

        now = datetime.now()
        last_date = last_interaction_at.date()
        today = now.date()

        # 오늘 이미 방문했는지 체크
        if last_date == today:
            # 오늘 이미 대화했음 → 연속 일수 유지
            key = f"garden:{user_id}"
            data = await self.redis.get(key)
            return data.get("consecutive_days", 1) if data else 1

        # 어제 방문했는지 체크
        yesterday = today - timedelta(days=1)
        if last_date == yesterday:
            # 연속 참여 중 → +1
            key = f"garden:{user_id}"
            data = await self.redis.get(key)
            return data.get("consecutive_days", 0) + 1

        # 2일 이상 공백 → 초기화
        return 1

    async def _check_season_badge(
        self,
        user_id: str,
        total_conversations: int
    ) -> Optional[SeasonBadge]:
        """
        계절 뱃지 체크

        한 달(30일) 이상 참여 시 계절 뱃지 부여.
        """
        if total_conversations < SEASON_BADGE_DAYS:
            return None

        # 현재 계절 결정
        month = datetime.now().month
        if month in [3, 4, 5]:
            return SeasonBadge.SPRING
        elif month in [6, 7, 8]:
            return SeasonBadge.SUMMER
        elif month in [9, 10, 11]:
            return SeasonBadge.AUTUMN
        else:  # 12, 1, 2
            return SeasonBadge.WINTER

    async def _save_garden_status(self, status: GardenVisualizationData) -> None:
        """정원 상태 Redis 저장"""
        key = f"garden:{status.user_id}"
        await self.redis.set(
            key,
            status.model_dump(mode='json'),
            ttl=None  # 영구 저장
        )

    async def reset_garden(self, user_id: str) -> None:
        """
        정원 초기화 (테스트/관리자용)

        Args:
            user_id: 사용자 ID
        """
        logger.warning(f"Resetting garden for user: {user_id}")
        key = f"garden:{user_id}"
        await self.redis.delete(key)


# ============================================
# 9. Export
# ============================================
__all__ = [
    "GardenMapper",
    "GardenVisualizationData",
    "GardenStatusUpdate",
    "RiskLevel",
    "GardenWeather",
    "SeasonBadge",
]

logger.info("Garden mapper module loaded")
