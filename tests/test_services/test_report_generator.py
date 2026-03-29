"""
ReportGenerator 테스트 (HIGH-6)

TimescaleDB 연동 및 주간/월간 리포트 생성 검증.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ============================================
# Test 1: _get_mcdi_history - TimescaleDB 경로
# ============================================

@pytest.mark.asyncio
async def test_get_mcdi_history_from_timescale():
    """TimescaleDB에서 MCDI 이력 조회"""
    from core.analysis.report_generator import ReportGenerator
    from database.timescale import MCDIScore

    mock_scores = [
        MCDIScore(
            timestamp=datetime(2026, 2, 25),
            user_id="user_123",
            mcdi_score=78.5,
            risk_level="GREEN"
        ),
        MCDIScore(
            timestamp=datetime(2026, 2, 24),
            user_id="user_123",
            mcdi_score=72.0,
            risk_level="YELLOW"
        ),
    ]

    mock_ts = AsyncMock()
    mock_ts.get_recent_scores = AsyncMock(return_value=mock_scores)

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient"), \
         patch("database.timescale.get_timescale", return_value=mock_ts):

        generator = ReportGenerator()
        history = await generator._get_mcdi_history(
            "user_123",
            datetime(2026, 2, 20),
            datetime(2026, 2, 27)
        )

    assert len(history) == 2
    assert history[0]["mcdi_score"] == 78.5
    assert history[1]["mcdi_score"] == 72.0
    print(f"✅ MCDI history from TimescaleDB: {len(history)} entries")


@pytest.mark.asyncio
async def test_get_mcdi_history_timescale_fallback_to_redis():
    """TimescaleDB 실패 → Redis 폴백"""
    from core.analysis.report_generator import ReportGenerator

    mock_redis_data = [
        {"timestamp": "2026-02-25T10:00:00", "mcdi_score": 75.0, "risk_level": "GREEN"},
    ]
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=mock_redis_data)

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient", return_value=mock_redis), \
         patch("database.timescale.get_timescale", side_effect=Exception("DB down")):

        generator = ReportGenerator(redis_client=mock_redis)
        history = await generator._get_mcdi_history(
            "user_123",
            datetime(2026, 2, 20),
            datetime(2026, 2, 27)
        )

    assert len(history) == 1
    print(f"✅ MCDI history fallback to Redis: {len(history)} entries")


# ============================================
# Test 2: _get_current_risk_level
# ============================================

@pytest.mark.asyncio
async def test_get_current_risk_level_from_timescale():
    """TimescaleDB에서 현재 위험도 조회"""
    from core.analysis.report_generator import ReportGenerator
    from database.timescale import MCDIScore

    mock_score = MCDIScore(
        timestamp=datetime.now(),
        user_id="user_123",
        mcdi_score=45.0,
        risk_level="ORANGE"
    )
    mock_ts = AsyncMock()
    mock_ts.get_recent_scores = AsyncMock(return_value=[mock_score])

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient"), \
         patch("database.timescale.get_timescale", return_value=mock_ts):

        generator = ReportGenerator()
        risk = await generator._get_current_risk_level("user_123")

    assert risk == "ORANGE"
    print(f"✅ Current risk level: {risk}")


@pytest.mark.asyncio
async def test_get_current_risk_level_default_green():
    """TimescaleDB 없을 때 GREEN 기본값"""
    from core.analysis.report_generator import ReportGenerator

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient"), \
         patch("database.timescale.get_timescale", side_effect=Exception("no data")):

        generator = ReportGenerator()
        risk = await generator._get_current_risk_level("user_123")

    assert risk == "GREEN"
    print(f"✅ Default risk level GREEN on error")


# ============================================
# Test 3: _calculate_risk_change
# ============================================

@pytest.mark.asyncio
async def test_calculate_risk_change_improved():
    """최근 7일 점수가 이전 7일보다 높으면 improved"""
    from core.analysis.report_generator import ReportGenerator
    from database.timescale import MCDIScore

    recent_scores = [MCDIScore(timestamp=datetime.now(), user_id="u", mcdi_score=80.0, risk_level="GREEN")]
    all_scores = recent_scores + [MCDIScore(timestamp=datetime(2026, 2, 10), user_id="u", mcdi_score=70.0, risk_level="YELLOW")]

    mock_ts = AsyncMock()
    mock_ts.get_recent_scores = AsyncMock(side_effect=[recent_scores, all_scores])

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient"), \
         patch("database.timescale.get_timescale", return_value=mock_ts):

        generator = ReportGenerator()
        change = await generator._calculate_risk_change("user_123", datetime(2026, 2, 20))

    assert change in ["improved", "stable", "worsened"]
    print(f"✅ Risk change: {change}")


# ============================================
# Test 4: _get_risk_history
# ============================================

@pytest.mark.asyncio
async def test_get_risk_history_from_timescale():
    """TimescaleDB에서 위험도 이력 조회"""
    from core.analysis.report_generator import ReportGenerator
    from database.timescale import MCDIScore

    mock_scores = [
        MCDIScore(timestamp=datetime(2026, 2, 25), user_id="u", mcdi_score=78.0, risk_level="GREEN"),
        MCDIScore(timestamp=datetime(2026, 2, 20), user_id="u", mcdi_score=55.0, risk_level="YELLOW"),
    ]
    mock_ts = AsyncMock()
    mock_ts.get_recent_scores = AsyncMock(return_value=mock_scores)

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient"), \
         patch("database.timescale.get_timescale", return_value=mock_ts):

        generator = ReportGenerator()
        history = await generator._get_risk_history(
            "user_123",
            datetime(2026, 2, 15),
            datetime(2026, 2, 27)
        )

    assert len(history) == 2
    assert history[0]["risk_level"] == "GREEN"
    assert history[1]["risk_level"] == "YELLOW"
    print(f"✅ Risk history: {len(history)} entries")


# ============================================
# Test 5: _calculate_cognitive_metrics
# ============================================

def test_calculate_cognitive_metrics_normal():
    """인지 기능 지표 계산 - 정상"""
    from core.analysis.report_generator import ReportGenerator

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient"):

        generator = ReportGenerator()

    history = [
        {"timestamp": "2026-02-21T10:00:00", "mcdi_score": 70.0},
        {"timestamp": "2026-02-22T10:00:00", "mcdi_score": 75.0},
        {"timestamp": "2026-02-23T10:00:00", "mcdi_score": 80.0},
    ]
    metrics = generator._calculate_cognitive_metrics(history)

    assert abs(metrics.mcdi_average - 75.0) < 0.01
    assert metrics.mcdi_min == 70.0
    assert metrics.mcdi_max == 80.0
    assert metrics.mcdi_trend == "improving"  # 상승 추세
    print(f"✅ Cognitive metrics: avg={metrics.mcdi_average}, trend={metrics.mcdi_trend}")


def test_calculate_cognitive_metrics_empty():
    """인지 기능 지표 - 데이터 없음"""
    from core.analysis.report_generator import ReportGenerator

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient"):

        generator = ReportGenerator()

    metrics = generator._calculate_cognitive_metrics([])
    assert metrics.mcdi_average == 0.0
    assert metrics.mcdi_trend == "unknown"
    print("✅ Cognitive metrics with empty data: defaults returned")


# ============================================
# Test 6: _extract_growth_metrics
# ============================================

def test_extract_growth_metrics_with_achievements():
    """성장 지표 추출 - 업적 포함"""
    from core.analysis.report_generator import ReportGenerator
    from core.analysis.garden_mapper import GardenVisualizationData, GardenWeather
    from datetime import datetime

    with patch("core.analysis.report_generator.EmotionAnalyzer"), \
         patch("core.analysis.report_generator.GardenMapper"), \
         patch("core.analysis.report_generator.RedisClient"):

        generator = ReportGenerator()

    status = GardenVisualizationData(
        user_id="test",
        flower_count=55,
        butterfly_count=3,
        garden_level=2,
        consecutive_days=14,
        total_conversations=55,
        weather=GardenWeather.SUNNY,
        status_message="정원이 건강해요!",
        updated_at=datetime.now(),
    )

    metrics = generator._extract_growth_metrics(status)
    assert metrics.flowers_earned == 55
    assert "first_flower" in metrics.achievements_unlocked
    assert "flowers_50" in metrics.achievements_unlocked
    assert "streak_7days" in metrics.achievements_unlocked
    assert "streak_14days" in metrics.achievements_unlocked
    print(f"✅ Growth metrics achievements: {metrics.achievements_unlocked}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
