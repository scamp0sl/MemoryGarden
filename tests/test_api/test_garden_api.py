"""
Garden API 테스트 (MED-3)

정원 상태 조회/업적/히스토리/초기화 엔드포인트 검증.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from api.main import app
from core.analysis.garden_mapper import GardenVisualizationData, GardenWeather


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def user_id():
    return str(uuid.uuid4())


def _make_garden_status(user_id: str) -> GardenVisualizationData:
    """테스트용 GardenVisualizationData 생성"""
    from datetime import datetime
    return GardenVisualizationData(
        user_id=user_id,
        flower_count=15,
        butterfly_count=2,
        garden_level=2,
        consecutive_days=10,
        total_conversations=15,
        weather=GardenWeather.SUNNY,
        season_badge=None,
        status_message="정원이 건강하게 자라고 있어요! ☀️",
        next_milestone="🦋 2일 더 참여하면 나비가 날아와요!",
        updated_at=datetime.now(),
    )


# ============================================
# Test 1: GET /api/v1/garden/users/{user_id}/garden
# ============================================

@pytest.mark.asyncio
async def test_get_garden_status_success(user_id):
    """정원 상태 조회 성공"""
    mock_status = _make_garden_status(user_id)

    with patch("api.routes.garden.GardenMapper") as MockMapper:
        instance = AsyncMock()
        instance.get_garden_status = AsyncMock(return_value=mock_status)
        MockMapper.return_value = instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/garden/users/{user_id}/garden")

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["flower_count"] == 15
    assert data["weather"] == "sunny"
    assert data["garden_level"] == 2
    print(f"✅ Garden status: flower={data['flower_count']}, weather={data['weather']}")


@pytest.mark.asyncio
async def test_get_garden_status_default_user(user_id):
    """신규 사용자 기본 정원 상태 반환"""
    from datetime import datetime
    default_status = GardenVisualizationData(
        user_id=user_id,
        flower_count=0,
        butterfly_count=0,
        garden_level=1,
        consecutive_days=0,
        total_conversations=0,
        weather=GardenWeather.SUNNY,
        season_badge=None,
        status_message="정원을 처음 만드셨네요! 🌱 함께 가꿔나가요!",
        next_milestone="첫 대화를 완료하면 꽃이 피어나요!",
        updated_at=datetime.now(),
    )

    with patch("api.routes.garden.GardenMapper") as MockMapper:
        instance = AsyncMock()
        instance.get_garden_status = AsyncMock(return_value=default_status)
        MockMapper.return_value = instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/garden/users/{user_id}/garden")

    assert response.status_code == 200
    data = response.json()
    assert data["flower_count"] == 0
    assert data["garden_level"] == 1
    print("✅ Default garden status returned for new user")


# ============================================
# Test 2: GET /api/v1/garden/users/{user_id}/garden/history
# ============================================

@pytest.mark.asyncio
async def test_get_garden_history_with_timescale(user_id):
    """TimescaleDB 데이터 기반 히스토리 반환"""
    from database.timescale import MCDIScore
    from datetime import datetime

    mock_scores = [
        MCDIScore(
            timestamp=datetime(2026, 2, 25),
            user_id=user_id,
            mcdi_score=78.5,
            risk_level="GREEN"
        ),
        MCDIScore(
            timestamp=datetime(2026, 2, 24),
            user_id=user_id,
            mcdi_score=72.0,
            risk_level="GREEN"
        ),
    ]

    mock_ts = AsyncMock()
    mock_ts.get_recent_scores = AsyncMock(return_value=mock_scores)

    with patch("api.routes.garden.GardenMapper"), \
         patch("database.timescale.get_timescale", return_value=mock_ts):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/garden/users/{user_id}/garden/history",
                params={"limit": 7}
            )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert isinstance(data["history"], list)
    print(f"✅ Garden history: {len(data['history'])} entries")


@pytest.mark.asyncio
async def test_get_garden_history_timescale_unavailable(user_id):
    """TimescaleDB 없을 때 빈 히스토리 반환 (500 아님)"""
    with patch("database.timescale.get_timescale", side_effect=Exception("DB unavailable")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/garden/users/{user_id}/garden/history"
            )

    assert response.status_code == 200
    data = response.json()
    assert data["history"] == []
    assert data["total_entries"] == 0
    print("✅ Empty history on TimescaleDB failure (graceful)")


# ============================================
# Test 3: GET /api/v1/garden/users/{user_id}/achievements
# ============================================

@pytest.mark.asyncio
async def test_get_achievements_success(user_id):
    """업적 목록 조회"""
    mock_status = _make_garden_status(user_id)

    with patch("api.routes.garden.GardenMapper") as MockMapper:
        instance = AsyncMock()
        instance.get_garden_status = AsyncMock(return_value=mock_status)
        MockMapper.return_value = instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/garden/users/{user_id}/achievements")

    assert response.status_code == 200
    data = response.json()
    assert "achievements" in data
    assert "total_count" in data
    # flower_count=15 → first_flower, flowers_10 달성
    assert "first_flower" in data["achievements"]
    assert "flowers_10" in data["achievements"]
    print(f"✅ Achievements: {data['achievements']}")


@pytest.mark.asyncio
async def test_get_achievements_new_user(user_id):
    """신규 사용자 업적 없음"""
    from datetime import datetime
    zero_status = GardenVisualizationData(
        user_id=user_id,
        flower_count=0,
        butterfly_count=0,
        garden_level=1,
        consecutive_days=0,
        total_conversations=0,
        weather=GardenWeather.SUNNY,
        status_message="정원을 처음 만드셨네요!",
        updated_at=datetime.now(),
    )

    with patch("api.routes.garden.GardenMapper") as MockMapper:
        instance = AsyncMock()
        instance.get_garden_status = AsyncMock(return_value=zero_status)
        MockMapper.return_value = instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/garden/users/{user_id}/achievements")

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    print("✅ No achievements for new user")


# ============================================
# Test 4: POST /api/v1/garden/admin/users/{user_id}/garden/reset
# ============================================

@pytest.mark.asyncio
async def test_reset_garden_success(user_id):
    """정원 초기화 성공"""
    from datetime import datetime
    reset_status = GardenVisualizationData(
        user_id=user_id,
        flower_count=0,
        butterfly_count=0,
        garden_level=1,
        consecutive_days=0,
        total_conversations=0,
        weather=GardenWeather.SUNNY,
        status_message="정원을 처음 만드셨네요! 🌱 함께 가꿔나가요!",
        next_milestone="첫 대화를 완료하면 꽃이 피어나요!",
        updated_at=datetime.now(),
    )

    with patch("api.routes.garden.GardenMapper") as MockMapper:
        instance = AsyncMock()
        instance.reset_garden = AsyncMock()
        instance.get_garden_status = AsyncMock(return_value=reset_status)
        MockMapper.return_value = instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/garden/admin/users/{user_id}/garden/reset"
            )

    assert response.status_code == 200
    data = response.json()
    assert data["flower_count"] == 0
    assert data["garden_level"] == 1
    print(f"✅ Garden reset: flower={data['flower_count']}, level={data['garden_level']}")


# ============================================
# Test 5: _to_garden_response 변환 단위 테스트
# ============================================

def test_garden_response_enum_conversion():
    """GardenWeather enum → str 변환 확인"""
    from datetime import datetime
    from api.routes.garden import _to_garden_response
    from core.analysis.garden_mapper import SeasonBadge

    status = GardenVisualizationData(
        user_id="test",
        flower_count=5,
        butterfly_count=1,
        garden_level=1,
        consecutive_days=5,
        total_conversations=5,
        weather=GardenWeather.CLOUDY,
        season_badge=SeasonBadge.WINTER,
        status_message="흐림",
        updated_at=datetime.now(),
    )

    response = _to_garden_response(status)
    assert response.weather == "cloudy"
    assert response.season_badge == "winter"
    print(f"✅ Enum conversion: weather={response.weather}, badge={response.season_badge}")


def test_derive_achievements_milestones():
    """업적 파생 마일스톤 테스트"""
    from datetime import datetime
    from api.routes.garden import _derive_achievements

    status = GardenVisualizationData(
        user_id="test",
        flower_count=100,
        butterfly_count=3,
        garden_level=3,
        consecutive_days=30,
        total_conversations=100,
        weather=GardenWeather.SUNNY,
        status_message="정원이 건강해요!",
        updated_at=datetime.now(),
    )

    achievements = _derive_achievements(status)
    assert "first_flower" in achievements
    assert "flowers_10" in achievements
    assert "flowers_50" in achievements
    assert "flowers_100" in achievements
    assert "streak_7days" in achievements
    assert "streak_14days" in achievements
    assert "streak_30days" in achievements
    assert "garden_expansion" in achievements
    print(f"✅ Achievements derived: {achievements}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
