"""
TimescaleDB 클라이언트 테스트

MCDI 시계열 데이터 저장/조회 및 통계 계산 검증
"""

import pytest
from datetime import datetime, timedelta
import random
import uuid

from database.timescale import TimescaleDB, MCDIScore, BaselineStats
from utils.exceptions import DatabaseError


# ============================================
# Fixtures
# ============================================

@pytest.fixture
async def timescale():
    """TimescaleDB 클라이언트"""
    ts = TimescaleDB()
    await ts.connect()
    yield ts
    await ts.close()


@pytest.fixture
def sample_scores():
    """테스트용 샘플 점수"""
    return {
        "LR": 78.5,
        "SD": 82.3,
        "NC": 75.0,
        "TO": 80.0,
        "ER": 72.5,
        "RT": 70.0
    }


@pytest.fixture
async def sample_data(timescale):
    """테스트용 샘플 데이터 생성"""
    user_id = str(uuid.uuid4())

    # 28일 동안의 데이터 생성
    base_date = datetime.now() - timedelta(days=28)
    for i in range(28):
        timestamp = base_date + timedelta(days=i)
        mcdi_score = 80.0 - i * 0.3  # 완만한 하락

        await timescale.store_mcdi(
            user_id=user_id,
            mcdi_score=mcdi_score,
            scores={
                "LR": mcdi_score + random.uniform(-2, 2),
                "SD": mcdi_score + random.uniform(-2, 2),
                "NC": mcdi_score + random.uniform(-2, 2),
                "TO": mcdi_score + random.uniform(-2, 2),
                "ER": mcdi_score + random.uniform(-2, 2),
                "RT": mcdi_score + random.uniform(-2, 2)
            },
            risk_level="GREEN",
            timestamp=timestamp
        )

    return user_id


# ============================================
# Test 1: store_mcdi() - MCDI 점수 저장
# ============================================

@pytest.mark.asyncio
async def test_store_mcdi(timescale, sample_scores):
    """정상 케이스: MCDI 점수 저장"""
    # Arrange
    user_id = str(uuid.uuid4())
    mcdi_score = 78.5
    risk_level = "GREEN"

    # Act
    await timescale.store_mcdi(
        user_id=user_id,
        mcdi_score=mcdi_score,
        scores=sample_scores,
        risk_level=risk_level,
        metadata={"test": True}
    )

    # Assert - 저장 후 조회
    scores = await timescale.get_recent_scores(user_id, days=1, limit=1)
    assert len(scores) == 1
    assert scores[0].mcdi_score == mcdi_score
    assert scores[0].risk_level == risk_level
    assert scores[0].lr_score == sample_scores["LR"]

    print(f"✅ MCDI stored and retrieved: {mcdi_score}")


# ============================================
# Test 2: get_recent_scores() - 최근 점수 조회
# ============================================

@pytest.mark.asyncio
async def test_get_recent_scores(timescale, sample_data):
    """정상 케이스: 최근 28일 점수 조회"""
    # Arrange
    user_id = sample_data

    # Act
    scores = await timescale.get_recent_scores(user_id, days=28)

    # Assert - 경계 조건으로 인해 27~28개 허용
    assert 27 <= len(scores) <= 28
    assert all(isinstance(s, MCDIScore) for s in scores)
    assert scores[0].timestamp > scores[-1].timestamp  # 최신순 정렬

    print(f"✅ Retrieved {len(scores)} scores")


@pytest.mark.asyncio
async def test_get_recent_scores_with_limit(timescale, sample_data):
    """제한 조회: limit 파라미터"""
    # Arrange
    user_id = sample_data

    # Act
    scores = await timescale.get_recent_scores(user_id, days=28, limit=10)

    # Assert
    assert len(scores) == 10

    print(f"✅ Retrieved {len(scores)} scores (limited)")


# ============================================
# Test 3: get_baseline() - Baseline 통계
# ============================================

@pytest.mark.asyncio
async def test_get_baseline_with_data(timescale, sample_data):
    """정상 케이스: Baseline 통계 계산"""
    # Arrange
    user_id = sample_data

    # Act
    baseline = await timescale.get_baseline(user_id, days=90)

    # Assert
    assert isinstance(baseline, BaselineStats)
    assert baseline.sample_size == 28
    assert 70.0 <= baseline.mean <= 80.0  # 80.0 - 0.3*28 = 71.6 근처
    assert baseline.std > 0
    assert baseline.start_date is not None
    assert baseline.end_date is not None

    print(f"✅ Baseline: mean={baseline.mean:.2f}, std={baseline.std:.2f}, n={baseline.sample_size}")


@pytest.mark.asyncio
async def test_get_baseline_without_data(timescale):
    """엣지 케이스: 데이터 없을 때 기본값 반환"""
    # Arrange
    user_id = str(uuid.uuid4())  # Use UUID for nonexistent user

    # Act
    baseline = await timescale.get_baseline(user_id, days=90)

    # Assert
    assert baseline.mean == 80.0  # 기본값
    assert baseline.std == 10.0   # 기본값
    assert baseline.sample_size == 0

    print(f"✅ Baseline (no data): mean={baseline.mean}, std={baseline.std}")


# ============================================
# Test 4: calculate_slope() - 기울기 계산
# ============================================

@pytest.mark.asyncio
async def test_calculate_slope_decreasing(timescale, sample_data):
    """하락 추세 케이스"""
    # Arrange
    user_id = sample_data  # 80.0 → 71.6 (하락)

    # Act
    slope, direction = await timescale.calculate_slope(user_id, weeks=4)

    # Assert
    assert slope < 0  # 하락
    assert direction == "decreasing"

    print(f"✅ Slope (decreasing): {slope:.2f}/week")


@pytest.mark.asyncio
async def test_calculate_slope_stable(timescale):
    """안정 추세 케이스"""
    # Arrange
    user_id = str(uuid.uuid4())

    # 안정적인 데이터 생성 (80±2)
    base_date = datetime.now() - timedelta(days=28)
    for i in range(28):
        timestamp = base_date + timedelta(days=i)
        mcdi_score = 80.0 + random.uniform(-2, 2)

        await timescale.store_mcdi(
            user_id=user_id,
            mcdi_score=mcdi_score,
            scores={"LR": 80.0},
            timestamp=timestamp
        )

    # Act
    slope, direction = await timescale.calculate_slope(user_id, weeks=4)

    # Assert
    assert -0.5 < slope < 0.5  # 안정적
    assert direction == "stable"

    print(f"✅ Slope (stable): {slope:.2f}/week")


@pytest.mark.asyncio
async def test_calculate_slope_insufficient_data(timescale):
    """엣지 케이스: 데이터 부족 (1개)"""
    # Arrange
    user_id = str(uuid.uuid4())

    await timescale.store_mcdi(
        user_id=user_id,
        mcdi_score=80.0,
        scores={"LR": 80.0}
    )

    # Act
    slope, direction = await timescale.calculate_slope(user_id, weeks=4)

    # Assert
    assert slope == 0.0  # 기본값
    assert direction == "stable"

    print(f"✅ Slope (insufficient data): {slope:.2f}/week")


# ============================================
# Test 5: get_timeseries() - 시계열 데이터
# ============================================

@pytest.mark.asyncio
async def test_get_timeseries(timescale, sample_data):
    """정상 케이스: 시계열 데이터 조회"""
    # Arrange
    user_id = sample_data
    start_date = datetime.now() - timedelta(days=14)
    end_date = datetime.now()

    # Act
    data = await timescale.get_timeseries(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        metric="mcdi_score"
    )

    # Assert - 경계 조건으로 인해 13~14개 허용
    assert 13 <= len(data) <= 14
    assert all("timestamp" in point and "value" in point for point in data)
    assert all(isinstance(point["value"], float) for point in data)

    print(f"✅ Timeseries retrieved: {len(data)} points")


@pytest.mark.asyncio
async def test_get_timeseries_invalid_metric(timescale, sample_data):
    """에러 케이스: 잘못된 metric"""
    # Arrange
    user_id = sample_data

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid metric"):
        await timescale.get_timeseries(
            user_id=user_id,
            metric="invalid_metric"
        )

    print("✅ Invalid metric rejected")


# ============================================
# Test 6: get_aggregate_stats() - 집계 통계
# ============================================

@pytest.mark.asyncio
async def test_get_aggregate_stats(timescale, sample_data):
    """정상 케이스: 집계 통계 계산"""
    # Arrange
    user_id = sample_data

    # Act
    stats = await timescale.get_aggregate_stats(user_id, days=28)

    # Assert
    assert "mcdi" in stats
    assert "mean" in stats["mcdi"]
    assert "min" in stats["mcdi"]
    assert "max" in stats["mcdi"]
    assert "median" in stats["mcdi"]
    assert "risk_distribution" in stats

    # 값 검증
    assert 70.0 <= stats["mcdi"]["mean"] <= 80.0
    assert stats["mcdi"]["min"] < stats["mcdi"]["max"]
    # 경계 조건으로 인해 27~28개 허용
    assert 27 <= stats["risk_distribution"]["GREEN"] <= 28

    print(f"✅ Aggregate stats: mean={stats['mcdi']['mean']:.2f}")


# ============================================
# Test 7: AnalyticalMemory 통합 테스트
# ============================================

@pytest.mark.asyncio
async def test_analytical_memory_integration():
    """통합 테스트: AnalyticalMemory 전체 플로우"""
    from core.memory.analytical_memory import create_analytical_memory

    # Arrange
    analytical = await create_analytical_memory()
    user_id = str(uuid.uuid4())

    analysis = {
        "mcdi_score": 78.5,
        "scores": {
            "LR": 78.5,
            "SD": 82.3,
            "NC": 75.0,
            "TO": 80.0,
            "ER": 72.5,
            "RT": 70.0
        },
        "risk_level": "GREEN",
        "contradictions": [],
        "failed_metrics": []
    }

    # Act 1: 저장
    await analytical.store(user_id, analysis)

    # Act 2: 조회
    data = await analytical.retrieve(user_id, days=7)

    # Assert
    assert len(data["recent_scores"]) == 1
    assert data["recent_scores"][0]["mcdi_score"] == 78.5
    assert data["baseline"]["mean"] >= 0
    assert data["slope"] is not None
    assert data["trend"] in ["increasing", "stable", "decreasing"]

    # Act 3: 최신 점수
    latest = await analytical.get_latest_score(user_id)
    assert latest == 78.5

    # Act 4: 통계
    stats = await analytical.get_stats(user_id, days=7)
    assert stats["mcdi"]["mean"] >= 0

    print("✅ AnalyticalMemory integration test passed")


# ============================================
# Test 8: 에러 처리
# ============================================

@pytest.mark.asyncio
async def test_store_mcdi_with_invalid_data(timescale):
    """에러 케이스: 잘못된 데이터"""
    # Arrange
    user_id = "test_user"

    # Act & Assert - mcdi_score가 None이면 DatabaseError
    with pytest.raises(DatabaseError):
        await timescale.store_mcdi(
            user_id=user_id,
            mcdi_score=None,  # 잘못된 값
            scores={}
        )

    print("✅ Invalid data rejected")


# ============================================
# Test Summary
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TimescaleDB 테스트 시작")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
