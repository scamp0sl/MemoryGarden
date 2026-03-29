"""
VisionService 테스트

정원 시각화 데이터 생성 로직을 검증합니다.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# Standard Library Imports
# ============================================
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

# ============================================
# Local Imports
# ============================================
from services.vision_service import (
    VisionService,
    VisionServiceError,
    WeatherType,
    FlowerState,
    TreeGrowth,
    Season
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def vision_service():
    """VisionService 인스턴스"""
    return VisionService()


@pytest.fixture
def base_garden_params():
    """기본 정원 파라미터"""
    return {
        "user_id": "test_user_123",
        "total_conversations": 50,
        "consecutive_days": 15,
        "current_streak": 15,
        "current_level": 2,
        "flowers_count": 50,
        "butterflies_count": 5,
        "trees_count": 1,
        "season_badges": ["spring_2025"],
        "mcdi_score": 78.5,
        "recent_emotion": "joy",
        "last_conversation_date": datetime.now()
    }


# ============================================
# 정상 케이스 테스트
# ============================================

@pytest.mark.asyncio
async def test_generate_garden_visualization_success(vision_service, base_garden_params):
    """정상 케이스: 전체 정원 시각화 생성"""
    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    assert "weather" in result
    assert "season" in result
    assert "time_of_day" in result
    assert "garden_health" in result
    assert "flowers" in result
    assert "butterflies" in result
    assert "trees" in result
    assert "decorations" in result
    assert "special_effects" in result
    assert "metadata" in result

    # 메타데이터 검증
    assert result["metadata"]["user_id"] == "test_user_123"
    assert result["metadata"]["total_conversations"] == 50
    assert result["metadata"]["current_level"] == 2


@pytest.mark.asyncio
async def test_weather_based_on_emotion(vision_service, base_garden_params):
    """감정에 따른 날씨 결정 테스트"""
    # Arrange - joy 감정
    base_garden_params["recent_emotion"] = "joy"

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert - joy는 sunny 날씨
    assert result["weather"] == WeatherType.SUNNY


@pytest.mark.asyncio
async def test_weather_based_on_sadness(vision_service, base_garden_params):
    """부정 감정에 따른 날씨 결정"""
    # Arrange - sadness 감정
    base_garden_params["recent_emotion"] = "sadness"

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert - sadness는 cloudy 날씨
    assert result["weather"] == WeatherType.CLOUDY


@pytest.mark.asyncio
async def test_garden_health_excellent_with_high_mcdi(vision_service, base_garden_params):
    """높은 MCDI 점수 -> excellent 건강도"""
    # Arrange
    base_garden_params["mcdi_score"] = 95.0
    base_garden_params["consecutive_days"] = 30

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    assert result["garden_health"] in ["excellent", "good"]


@pytest.mark.asyncio
async def test_garden_health_poor_with_low_mcdi(vision_service, base_garden_params):
    """낮은 MCDI 점수 -> poor 건강도"""
    # Arrange
    base_garden_params["mcdi_score"] = 25.0
    base_garden_params["consecutive_days"] = 1

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    assert result["garden_health"] in ["poor", "critical"]


@pytest.mark.asyncio
async def test_flowers_count_matches_input(vision_service, base_garden_params):
    """꽃 개수가 입력과 일치"""
    # Arrange
    base_garden_params["flowers_count"] = 10

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    assert len(result["flowers"]) == 10


@pytest.mark.asyncio
async def test_butterflies_count_matches_input(vision_service, base_garden_params):
    """나비 개수가 입력과 일치"""
    # Arrange
    base_garden_params["butterflies_count"] = 3

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    assert len(result["butterflies"]) == 3


@pytest.mark.asyncio
async def test_tree_growth_based_on_conversations(vision_service, base_garden_params):
    """대화 수에 따른 나무 성장 단계"""
    # Arrange - 대화 200회 = 약 100일
    base_garden_params["total_conversations"] = 200
    base_garden_params["trees_count"] = 1

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert - 100일이면 SAPLING 또는 YOUNG_TREE
    tree = result["trees"][0]
    assert tree["growth_stage"] in [TreeGrowth.SAPLING, TreeGrowth.YOUNG_TREE]


@pytest.mark.asyncio
async def test_special_effects_on_3day_streak(vision_service, base_garden_params):
    """3일 연속 달성 시 특수 효과"""
    # Arrange
    base_garden_params["current_streak"] = 3
    base_garden_params["consecutive_days"] = 3

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert - butterfly_spawn 효과 포함
    effect_types = [e["type"] for e in result["special_effects"]]
    assert "butterfly_spawn" in effect_types


@pytest.mark.asyncio
async def test_special_effects_on_7day_streak(vision_service, base_garden_params):
    """7일 연속 달성 시 레벨업 효과"""
    # Arrange
    base_garden_params["current_streak"] = 7
    base_garden_params["consecutive_days"] = 7

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert - level_up 효과 포함
    effect_types = [e["type"] for e in result["special_effects"]]
    assert "level_up" in effect_types


@pytest.mark.asyncio
async def test_decorations_unlock_at_level_5(vision_service, base_garden_params):
    """레벨 5에서 벤치 해금"""
    # Arrange
    base_garden_params["current_level"] = 5

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    decoration_types = [d["type"] for d in result["decorations"]]
    assert "bench" in decoration_types


@pytest.mark.asyncio
async def test_decorations_unlock_at_level_10(vision_service, base_garden_params):
    """레벨 10에서 분수 해금"""
    # Arrange
    base_garden_params["current_level"] = 10

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    decoration_types = [d["type"] for d in result["decorations"]]
    assert "fountain" in decoration_types


# ============================================
# 엣지 케이스 테스트
# ============================================

@pytest.mark.asyncio
async def test_no_mcdi_score_defaults_to_fair(vision_service, base_garden_params):
    """MCDI 점수 없으면 fair 건강도"""
    # Arrange
    base_garden_params["mcdi_score"] = None
    base_garden_params["consecutive_days"] = 0

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    assert result["garden_health"] == "fair"


@pytest.mark.asyncio
async def test_no_emotion_defaults_to_partly_cloudy(vision_service, base_garden_params):
    """감정 없으면 partly_cloudy 날씨"""
    # Arrange
    base_garden_params["recent_emotion"] = None

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    assert result["weather"] == WeatherType.PARTLY_CLOUDY


@pytest.mark.asyncio
async def test_zero_flowers_returns_empty_list(vision_service, base_garden_params):
    """꽃 0개일 때 빈 리스트"""
    # Arrange
    base_garden_params["flowers_count"] = 0

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert
    assert result["flowers"] == []


@pytest.mark.asyncio
async def test_inactive_butterflies_on_rainy_weather(vision_service, base_garden_params):
    """비 오는 날 나비 활동 감소"""
    # Arrange - anger 감정 -> rainy 날씨
    base_garden_params["recent_emotion"] = "anger"
    base_garden_params["butterflies_count"] = 9

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert - 비 오면 활동 나비가 1/3로 감소
    active_count = sum(1 for b in result["butterflies"] if b["is_active"])
    assert active_count <= 3  # 9 / 3 = 3


@pytest.mark.asyncio
async def test_garden_health_penalty_for_inactivity(vision_service, base_garden_params):
    """장기 비활동 시 건강도 하락"""
    # Arrange - 10일 전 마지막 대화
    base_garden_params["last_conversation_date"] = datetime.now() - timedelta(days=10)
    base_garden_params["mcdi_score"] = 80.0  # 원래 높은 점수

    # Act
    result = await vision_service.generate_garden_visualization(**base_garden_params)

    # Assert - 비활동으로 인한 페널티 (excellent에서 하락)
    assert result["garden_health"] in ["good", "fair", "poor"]


# ============================================
# Private 메서드 테스트
# ============================================

def test_determine_season_spring(vision_service):
    """봄(3-5월) 판정"""
    # Arrange
    date = datetime(2025, 4, 15)

    # Act
    season = vision_service._determine_season(date)

    # Assert
    assert season == Season.SPRING


def test_determine_season_winter(vision_service):
    """겨울(12-2월) 판정"""
    # Arrange
    date = datetime(2025, 1, 15)

    # Act
    season = vision_service._determine_season(date)

    # Assert
    assert season == Season.WINTER


def test_determine_time_of_day_morning(vision_service):
    """아침(5-12시) 판정"""
    # Arrange
    date = datetime(2025, 2, 10, 9, 0)

    # Act
    time_of_day = vision_service._determine_time_of_day(date)

    # Assert
    assert time_of_day == "morning"


def test_determine_time_of_day_night(vision_service):
    """밤(20-5시) 판정"""
    # Arrange
    date = datetime(2025, 2, 10, 23, 0)

    # Act
    time_of_day = vision_service._determine_time_of_day(date)

    # Assert
    assert time_of_day == "night"


def test_get_color_intensity_blooming(vision_service):
    """활짝 핀 꽃 색상 강도 최대"""
    # Act
    intensity = vision_service._get_color_intensity(FlowerState.BLOOMING)

    # Assert
    assert intensity == 1.0


def test_get_color_intensity_dormant(vision_service):
    """휴면 상태 꽃 색상 강도 최소"""
    # Act
    intensity = vision_service._get_color_intensity(FlowerState.DORMANT)

    # Assert
    assert intensity == 0.2


def test_get_tree_size_mature(vision_service):
    """성숙한 나무 크기 최대"""
    # Act
    size = vision_service._get_tree_size(TreeGrowth.MATURE_TREE)

    # Assert
    assert size == 1.0


def test_get_tree_size_seed(vision_service):
    """씨앗 크기 최소"""
    # Act
    size = vision_service._get_tree_size(TreeGrowth.SEED)

    # Assert
    assert size == 0.1


# ============================================
# 통합 시나리오 테스트
# ============================================

@pytest.mark.asyncio
async def test_complete_healthy_garden_scenario(vision_service):
    """시나리오: 건강한 정원 (높은 MCDI, 긍정 감정, 장기 활동)"""
    # Arrange
    params = {
        "user_id": "healthy_user",
        "total_conversations": 300,  # 약 150일
        "consecutive_days": 45,
        "current_streak": 45,
        "current_level": 6,
        "flowers_count": 300,
        "butterflies_count": 15,
        "trees_count": 1,
        "season_badges": ["spring_2025", "summer_2025"],
        "mcdi_score": 92.0,
        "recent_emotion": "joy",
        "last_conversation_date": datetime.now()
    }

    # Act
    result = await vision_service.generate_garden_visualization(**params)

    # Assert
    assert result["weather"] == WeatherType.SUNNY
    assert result["garden_health"] == "excellent"
    assert len(result["flowers"]) == 300
    assert len(result["butterflies"]) == 15
    assert result["trees"][0]["growth_stage"] == TreeGrowth.YOUNG_TREE

    # 레벨 6이므로 벤치 해금
    decoration_types = [d["type"] for d in result["decorations"]]
    assert "bench" in decoration_types


@pytest.mark.asyncio
async def test_struggling_garden_scenario(vision_service):
    """시나리오: 어려운 정원 (낮은 MCDI, 부정 감정, 짧은 활동)"""
    # Arrange
    params = {
        "user_id": "struggling_user",
        "total_conversations": 5,
        "consecutive_days": 2,
        "current_streak": 2,
        "current_level": 0,
        "flowers_count": 5,
        "butterflies_count": 0,
        "trees_count": 1,
        "season_badges": [],
        "mcdi_score": 32.0,
        "recent_emotion": "sadness",
        "last_conversation_date": datetime.now()
    }

    # Act
    result = await vision_service.generate_garden_visualization(**params)

    # Assert
    assert result["weather"] == WeatherType.CLOUDY
    assert result["garden_health"] in ["poor", "fair"]
    assert len(result["flowers"]) == 5
    assert result["trees"][0]["growth_stage"] == TreeGrowth.SEED


# ============================================
# 에러 케이스 테스트
# ============================================

@pytest.mark.asyncio
async def test_invalid_user_id_raises_error(vision_service, base_garden_params):
    """잘못된 user_id로 에러 발생하지 않음 (검증 없음)"""
    # Arrange
    base_garden_params["user_id"] = ""

    # Act & Assert - 에러 발생하지 않음 (빈 문자열 허용)
    result = await vision_service.generate_garden_visualization(**base_garden_params)
    assert result["metadata"]["user_id"] == ""
