"""
정원 시각화 서비스

감정 상태, 대화 기록, MCDI 점수를 기반으로
정원의 시각적 요소(꽃, 나무, 날씨, 계절)를 결정하고
JSON 형태의 정원 상태를 생성합니다.

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
import random

# ============================================
# 3. Local Imports
# ============================================
from utils.logger import get_logger
from utils.exceptions import MemoryGardenError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)


# ============================================
# 5. 상수 정의
# ============================================

# 날씨 타입
class WeatherType(str, Enum):
    """날씨 유형"""
    SUNNY = "sunny"           # 맑음 (긍정적)
    PARTLY_CLOUDY = "partly_cloudy"  # 약간 흐림 (보통)
    CLOUDY = "cloudy"         # 흐림 (부정적)
    RAINY = "rainy"           # 비 (매우 부정적)
    FOGGY = "foggy"           # 안개 (혼란/불안)


# 꽃 상태
class FlowerState(str, Enum):
    """꽃 상태"""
    BLOOMING = "blooming"     # 활짝 핌
    GROWING = "growing"       # 성장 중
    WILTING = "wilting"       # 시들어감
    DORMANT = "dormant"       # 휴면 상태


# 나무 성장 단계
class TreeGrowth(str, Enum):
    """나무 성장 단계"""
    SEED = "seed"             # 씨앗 (0-7일)
    SPROUT = "sprout"         # 새싹 (8-21일)
    SAPLING = "sapling"       # 어린 나무 (22-60일)
    YOUNG_TREE = "young_tree" # 젊은 나무 (61-180일)
    MATURE_TREE = "mature_tree" # 성숙한 나무 (181일+)


# 계절
class Season(str, Enum):
    """계절"""
    SPRING = "spring"   # 봄 (3-5월)
    SUMMER = "summer"   # 여름 (6-8월)
    AUTUMN = "autumn"   # 가을 (9-11월)
    WINTER = "winter"   # 겨울 (12-2월)


# 감정 -> 날씨 매핑
EMOTION_WEATHER_MAP = {
    "joy": WeatherType.SUNNY,
    "contentment": WeatherType.PARTLY_CLOUDY,
    "neutral": WeatherType.PARTLY_CLOUDY,
    "sadness": WeatherType.CLOUDY,
    "anxiety": WeatherType.FOGGY,
    "anger": WeatherType.RAINY,
    "confusion": WeatherType.FOGGY,
}

# MCDI 점수 범위 -> 정원 건강도
MCDI_HEALTH_MAP = [
    (80, 100, "excellent"),  # 우수
    (60, 79, "good"),        # 양호
    (40, 59, "fair"),        # 보통
    (20, 39, "poor"),        # 나쁨
    (0, 19, "critical"),     # 위험
]


# ============================================
# 6. 클래스 정의
# ============================================

class VisionServiceError(MemoryGardenError):
    """Vision Service 에러"""
    pass


class VisionService:
    """정원 시각화 서비스

    사용자의 감정 상태, 대화 일수, MCDI 점수를 기반으로
    정원의 시각적 요소를 결정합니다.

    게이미피케이션 규칙:
    - 1대화 = 1꽃
    - 3일 연속 = 1나비
    - 7일 연속 = 레벨업
    - 30일 = 계절 뱃지

    Attributes:
        None (stateless service)
    """

    def __init__(self):
        """초기화"""
        logger.info("VisionService initialized")

    async def generate_garden_visualization(
        self,
        user_id: str,
        total_conversations: int,
        consecutive_days: int,
        current_streak: int,
        current_level: int,
        flowers_count: int,
        butterflies_count: int,
        trees_count: int,
        season_badges: List[str],
        mcdi_score: Optional[float] = None,
        recent_emotion: Optional[str] = None,
        last_conversation_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        정원 시각화 데이터 생성

        Args:
            user_id: 사용자 ID
            total_conversations: 총 대화 수
            consecutive_days: 연속 대화 일수
            current_streak: 현재 연속 기록
            current_level: 현재 레벨
            flowers_count: 꽃 개수
            butterflies_count: 나비 개수
            trees_count: 나무 개수
            season_badges: 계절 뱃지 목록
            mcdi_score: 최근 MCDI 점수 (선택)
            recent_emotion: 최근 감정 (선택)
            last_conversation_date: 마지막 대화 날짜 (선택)

        Returns:
            {
                "weather": "sunny",
                "season": "spring",
                "time_of_day": "morning",
                "garden_health": "good",
                "flowers": [...],
                "butterflies": [...],
                "trees": [...],
                "decorations": [...],
                "special_effects": [...],
                "metadata": {...}
            }

        Raises:
            VisionServiceError: 시각화 생성 실패

        Example:
            >>> service = VisionService()
            >>> result = await service.generate_garden_visualization(
            ...     user_id="user123",
            ...     total_conversations=50,
            ...     consecutive_days=15,
            ...     current_streak=15,
            ...     current_level=2,
            ...     flowers_count=50,
            ...     butterflies_count=5,
            ...     trees_count=1,
            ...     season_badges=["spring_2025"],
            ...     mcdi_score=78.5,
            ...     recent_emotion="joy"
            ... )
            >>> print(result["weather"])
            "sunny"
        """
        try:
            logger.info(
                f"Generating garden visualization for user: {user_id}",
                extra={
                    "user_id": user_id,
                    "total_conversations": total_conversations,
                    "consecutive_days": consecutive_days,
                    "mcdi_score": mcdi_score
                }
            )

            # 1. 현재 시각 및 계절 결정
            now = datetime.now()
            current_season = self._determine_season(now)
            time_of_day = self._determine_time_of_day(now)

            # 2. 날씨 결정 (감정 기반)
            weather = self._determine_weather(recent_emotion, mcdi_score)

            # 3. 정원 건강도 계산 (MCDI 점수 기반)
            garden_health = self._calculate_garden_health(
                mcdi_score,
                consecutive_days,
                last_conversation_date
            )

            # 4. 꽃 상태 결정
            flowers = self._generate_flowers(
                flowers_count,
                garden_health,
                current_season
            )

            # 5. 나비 생성
            butterflies = self._generate_butterflies(
                butterflies_count,
                weather,
                time_of_day
            )

            # 6. 나무 상태 결정
            trees = self._generate_trees(
                trees_count,
                total_conversations,
                current_season
            )

            # 7. 장식 요소 (레벨 기반)
            decorations = self._generate_decorations(
                current_level,
                season_badges
            )

            # 8. 특수 효과 (연속 일수 기반)
            special_effects = self._generate_special_effects(
                current_streak,
                consecutive_days,
                weather
            )

            result = {
                "weather": weather,
                "season": current_season,
                "time_of_day": time_of_day,
                "garden_health": garden_health,
                "flowers": flowers,
                "butterflies": butterflies,
                "trees": trees,
                "decorations": decorations,
                "special_effects": special_effects,
                "metadata": {
                    "generated_at": now.isoformat(),
                    "user_id": user_id,
                    "total_conversations": total_conversations,
                    "consecutive_days": consecutive_days,
                    "current_level": current_level
                }
            }

            logger.info(
                f"Garden visualization generated successfully",
                extra={
                    "user_id": user_id,
                    "weather": weather,
                    "garden_health": garden_health,
                    "elements_count": len(flowers) + len(butterflies) + len(trees)
                }
            )

            return result

        except Exception as e:
            logger.error(
                f"Failed to generate garden visualization: {e}",
                extra={"user_id": user_id},
                exc_info=True
            )
            raise VisionServiceError(f"Visualization generation failed: {e}") from e

    def _determine_season(self, date: datetime) -> str:
        """
        현재 계절 결정

        Args:
            date: 기준 날짜

        Returns:
            Season enum 값
        """
        month = date.month

        if 3 <= month <= 5:
            return Season.SPRING
        elif 6 <= month <= 8:
            return Season.SUMMER
        elif 9 <= month <= 11:
            return Season.AUTUMN
        else:  # 12, 1, 2
            return Season.WINTER

    def _determine_time_of_day(self, date: datetime) -> str:
        """
        하루 중 시간대 결정

        Args:
            date: 기준 날짜

        Returns:
            시간대 문자열 (morning/afternoon/evening/night)
        """
        hour = date.hour

        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 20:
            return "evening"
        else:
            return "night"

    def _determine_weather(
        self,
        emotion: Optional[str],
        mcdi_score: Optional[float]
    ) -> str:
        """
        날씨 결정 (감정 + MCDI 점수 기반)

        Args:
            emotion: 최근 감정
            mcdi_score: MCDI 점수

        Returns:
            WeatherType enum 값
        """
        # 감정 기반 날씨 (우선순위 1)
        if emotion and emotion in EMOTION_WEATHER_MAP:
            base_weather = EMOTION_WEATHER_MAP[emotion]
        else:
            base_weather = WeatherType.PARTLY_CLOUDY

        # MCDI 점수로 미세 조정 (우선순위 2)
        if mcdi_score is not None:
            if mcdi_score >= 80:
                # 높은 점수 -> 좋은 날씨
                if base_weather in [WeatherType.CLOUDY, WeatherType.RAINY]:
                    base_weather = WeatherType.PARTLY_CLOUDY
            elif mcdi_score < 40:
                # 낮은 점수 -> 나쁜 날씨
                if base_weather == WeatherType.SUNNY:
                    base_weather = WeatherType.PARTLY_CLOUDY

        return base_weather

    def _calculate_garden_health(
        self,
        mcdi_score: Optional[float],
        consecutive_days: int,
        last_conversation_date: Optional[datetime]
    ) -> str:
        """
        정원 건강도 계산

        3가지 요소 반영:
        1. MCDI 점수 (가중치 60%)
        2. 연속 대화 보너스 (가중치 20%)
        3. 최근 활동 (가중치 20%)

        Args:
            mcdi_score: MCDI 점수
            consecutive_days: 연속 대화 일수
            last_conversation_date: 마지막 대화 날짜

        Returns:
            건강도 문자열 (excellent/good/fair/poor/critical)
        """
        # 1. MCDI 점수 기반 (가중치 60%)
        if mcdi_score is not None:
            for min_score, max_score, health in MCDI_HEALTH_MAP:
                if min_score <= mcdi_score <= max_score:
                    base_health = health
                    break
        else:
            base_health = "fair"

        # 2. 연속 대화 보너스 (가중치 20%)
        if consecutive_days >= 30:
            health_boost = 2
        elif consecutive_days >= 7:
            health_boost = 1
        elif consecutive_days >= 3:
            health_boost = 0.5
        else:
            health_boost = 0

        # 3. 최근 활동 체크 (가중치 20%)
        if last_conversation_date:
            days_since_last = (datetime.now() - last_conversation_date).days
            if days_since_last > 7:
                health_penalty = 2  # 1주일 이상 방치
            elif days_since_last > 3:
                health_penalty = 1  # 3일 이상 방치
            else:
                health_penalty = 0
        else:
            health_penalty = 0

        # 최종 점수 계산
        health_levels = ["critical", "poor", "fair", "good", "excellent"]
        current_index = health_levels.index(base_health)

        adjusted_index = current_index + int(health_boost) - int(health_penalty)
        adjusted_index = max(0, min(len(health_levels) - 1, adjusted_index))

        return health_levels[adjusted_index]

    def _generate_flowers(
        self,
        count: int,
        garden_health: str,
        season: str
    ) -> List[Dict[str, Any]]:
        """
        꽃 생성

        Args:
            count: 꽃 개수
            garden_health: 정원 건강도
            season: 현재 계절

        Returns:
            꽃 리스트
        """
        flowers = []

        # 건강도에 따른 상태 분포
        health_state_map = {
            "excellent": [0.8, 0.2, 0.0, 0.0],  # [blooming, growing, wilting, dormant]
            "good": [0.6, 0.3, 0.1, 0.0],
            "fair": [0.4, 0.3, 0.2, 0.1],
            "poor": [0.2, 0.2, 0.4, 0.2],
            "critical": [0.0, 0.1, 0.5, 0.4],
        }

        state_distribution = health_state_map.get(garden_health, [0.4, 0.3, 0.2, 0.1])

        # 계절별 꽃 종류
        seasonal_flowers = {
            Season.SPRING: ["cherry_blossom", "tulip", "daffodil", "magnolia"],
            Season.SUMMER: ["sunflower", "rose", "lily", "hydrangea"],
            Season.AUTUMN: ["cosmos", "chrysanthemum", "marigold", "dahlia"],
            Season.WINTER: ["camellia", "snowdrop", "hellebore", "winterberry"],
        }

        flower_types = seasonal_flowers.get(season, seasonal_flowers[Season.SPRING])

        for i in range(count):
            # 상태 랜덤 결정 (확률 분포 사용)
            state_choice = random.choices(
                [FlowerState.BLOOMING, FlowerState.GROWING, FlowerState.WILTING, FlowerState.DORMANT],
                weights=state_distribution,
                k=1
            )[0]

            flower = {
                "id": f"flower_{i+1}",
                "type": random.choice(flower_types),
                "state": state_choice,
                "position": {
                    "x": random.uniform(0.1, 0.9),
                    "y": random.uniform(0.3, 0.7)
                },
                "size": random.uniform(0.8, 1.2),
                "color_intensity": self._get_color_intensity(state_choice)
            }

            flowers.append(flower)

        return flowers

    def _get_color_intensity(self, state: str) -> float:
        """꽃 상태에 따른 색상 강도"""
        intensity_map = {
            FlowerState.BLOOMING: 1.0,
            FlowerState.GROWING: 0.7,
            FlowerState.WILTING: 0.4,
            FlowerState.DORMANT: 0.2,
        }
        return intensity_map.get(state, 0.7)

    def _generate_butterflies(
        self,
        count: int,
        weather: str,
        time_of_day: str
    ) -> List[Dict[str, Any]]:
        """
        나비 생성

        Args:
            count: 나비 개수
            weather: 현재 날씨
            time_of_day: 시간대

        Returns:
            나비 리스트
        """
        butterflies = []

        # 날씨와 시간에 따라 활동성 결정
        if weather in [WeatherType.RAINY, WeatherType.FOGGY] or time_of_day == "night":
            active_count = max(1, count // 3)  # 날씨 나쁘거나 밤이면 활동 감소
        else:
            active_count = count

        butterfly_colors = ["yellow", "orange", "blue", "purple", "white", "pink"]

        for i in range(active_count):
            butterfly = {
                "id": f"butterfly_{i+1}",
                "color": random.choice(butterfly_colors),
                "position": {
                    "x": random.uniform(0.2, 0.8),
                    "y": random.uniform(0.2, 0.8)
                },
                "animation": random.choice(["flutter", "circle", "zigzag"]),
                "speed": random.uniform(0.5, 1.5),
                "is_active": True
            }

            butterflies.append(butterfly)

        # 비활동 나비 추가 (밤/나쁜 날씨)
        for i in range(active_count, count):
            butterfly = {
                "id": f"butterfly_{i+1}",
                "color": random.choice(butterfly_colors),
                "position": {
                    "x": random.uniform(0.1, 0.9),
                    "y": 0.1  # 나무나 꽃에 앉아있음
                },
                "animation": "rest",
                "speed": 0.0,
                "is_active": False
            }

            butterflies.append(butterfly)

        return butterflies

    def _generate_trees(
        self,
        count: int,
        total_conversations: int,
        season: str
    ) -> List[Dict[str, Any]]:
        """
        나무 생성

        Args:
            count: 나무 개수
            total_conversations: 총 대화 수
            season: 현재 계절

        Returns:
            나무 리스트
        """
        trees = []

        # 대화 수를 날짜로 환산 (평균 하루 2대화 가정)
        equivalent_days = total_conversations / 2

        # 나무 성장 단계 결정
        if equivalent_days < 7:
            growth_stage = TreeGrowth.SEED
        elif equivalent_days < 21:
            growth_stage = TreeGrowth.SPROUT
        elif equivalent_days < 60:
            growth_stage = TreeGrowth.SAPLING
        elif equivalent_days < 180:
            growth_stage = TreeGrowth.YOUNG_TREE
        else:
            growth_stage = TreeGrowth.MATURE_TREE

        # 계절별 나무 모습
        seasonal_appearance = {
            Season.SPRING: {"leaves": "bright_green", "flowers": True},
            Season.SUMMER: {"leaves": "dark_green", "flowers": False},
            Season.AUTUMN: {"leaves": "orange_red", "flowers": False},
            Season.WINTER: {"leaves": "bare", "flowers": False},
        }

        appearance = seasonal_appearance.get(season, seasonal_appearance[Season.SPRING])

        for i in range(count):
            tree = {
                "id": f"tree_{i+1}",
                "growth_stage": growth_stage,
                "position": {
                    "x": random.uniform(0.1, 0.9),
                    "y": 0.2  # 배경
                },
                "size": self._get_tree_size(growth_stage),
                "appearance": appearance,
                "age_days": int(equivalent_days)
            }

            trees.append(tree)

        return trees

    def _get_tree_size(self, growth_stage: str) -> float:
        """나무 성장 단계별 크기"""
        size_map = {
            TreeGrowth.SEED: 0.1,
            TreeGrowth.SPROUT: 0.3,
            TreeGrowth.SAPLING: 0.5,
            TreeGrowth.YOUNG_TREE: 0.8,
            TreeGrowth.MATURE_TREE: 1.0,
        }
        return size_map.get(growth_stage, 0.5)

    def _generate_decorations(
        self,
        level: int,
        season_badges: List[str]
    ) -> List[Dict[str, Any]]:
        """
        장식 요소 생성 (레벨 보상)

        Args:
            level: 현재 레벨
            season_badges: 계절 뱃지 리스트

        Returns:
            장식 리스트
        """
        decorations = []

        # 레벨별 해금 장식
        if level >= 5:
            decorations.append({
                "type": "bench",
                "position": {"x": 0.7, "y": 0.5}
            })

        if level >= 10:
            decorations.append({
                "type": "fountain",
                "position": {"x": 0.5, "y": 0.5},
                "is_active": True
            })

        if level >= 15:
            decorations.append({
                "type": "gazebo",
                "position": {"x": 0.3, "y": 0.3}
            })

        # 계절 뱃지 장식 (30일 달성)
        for badge in season_badges:
            decorations.append({
                "type": "badge",
                "season": badge,
                "position": {"x": random.uniform(0.05, 0.15), "y": 0.1}
            })

        return decorations

    def _generate_special_effects(
        self,
        current_streak: int,
        consecutive_days: int,
        weather: str
    ) -> List[Dict[str, Any]]:
        """
        특수 효과 생성

        Args:
            current_streak: 현재 연속 기록
            consecutive_days: 연속 대화 일수
            weather: 현재 날씨

        Returns:
            특수 효과 리스트
        """
        effects = []

        # 3일 연속 달성 (나비 생성 효과)
        if current_streak % 3 == 0 and current_streak > 0:
            effects.append({
                "type": "butterfly_spawn",
                "animation": "sparkle_burst",
                "duration": 3.0
            })

        # 7일 연속 달성 (레벨업 효과)
        if current_streak % 7 == 0 and current_streak > 0:
            effects.append({
                "type": "level_up",
                "animation": "golden_light",
                "duration": 5.0
            })

        # 날씨 효과
        if weather == WeatherType.SUNNY:
            effects.append({
                "type": "sunbeams",
                "intensity": 0.7
            })
        elif weather == WeatherType.RAINY:
            effects.append({
                "type": "rain",
                "intensity": 0.8
            })
        elif weather == WeatherType.FOGGY:
            effects.append({
                "type": "fog",
                "intensity": 0.5
            })

        # 장기 연속 기록 특수 효과
        if consecutive_days >= 30:
            effects.append({
                "type": "rainbow",
                "animation": "arc",
                "position": {"x": 0.5, "y": 0.2}
            })

        return effects

    # ============================================
    # Legacy: 음식 이미지 분석 (기존 기능 유지)
    # ============================================

    async def analyze_meal_image(self, image_url: str, context: str) -> dict:
        """
        GPT-4o Vision API로 음식 분석

        Note: 이 메서드는 기존 레거시 기능입니다.
        향후 별도 ImageAnalysisService로 분리 예정.

        Args:
            image_url: 이미지 URL
            context: 컨텍스트 정보

        Returns:
            분석 결과 딕셔너리
        """
        logger.warning(
            "analyze_meal_image is a legacy method. "
            "Consider using separate ImageAnalysisService."
        )

        # TODO: OpenAI API 호출 구현 필요
        # response = await openai.ChatCompletion.create(...)

        raise NotImplementedError(
            "analyze_meal_image requires OpenAI API integration. "
            "Please implement or use separate ImageAnalysisService."
        )
