"""
Risk Evaluator 테스트

위험도 평가 로직을 검증합니다.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from core.analysis.risk_evaluator import (
    RiskEvaluator,
    RiskEvaluation,
    MCDI_THRESHOLDS,
    Z_SCORE_THRESHOLDS,
    SLOPE_THRESHOLDS
)
from utils.exceptions import AnalysisError


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def evaluator():
    """RiskEvaluator 인스턴스"""
    return RiskEvaluator()


@pytest.fixture
def sample_analysis():
    """테스트용 분석 결과"""
    return {
        "scores": {
            "LR": 78.5,
            "SD": 82.3,
            "NC": 75.0,
            "TO": 80.0,
            "ER": 72.5,
            "RT": 70.0
        },
        "mcdi_score": 76.5
    }


# ============================================
# Test 1: evaluate() - GREEN (정상)
# ============================================

@pytest.mark.asyncio
async def test_evaluate_green_normal_case(evaluator, sample_analysis):
    """
    GREEN 케이스: 높은 MCDI 점수, 정상 범위
    """
    # Arrange
    user_id = "test_user"
    current_score = 85.0

    # Mock historical scores (안정적 추세)
    with patch.object(evaluator, '_fetch_historical_scores') as mock_fetch:
        # 과거 14일 데이터 (Baseline: 82-88)
        base_date = datetime.now() - timedelta(days=14)
        mock_fetch.return_value = [
            (base_date + timedelta(days=i), 82.0 + i * 0.5)
            for i in range(14)
        ]

        # Act
        result = await evaluator.evaluate(user_id, current_score, sample_analysis)

    # Assert
    assert result.risk_level == "GREEN"
    assert result.current_score == 85.0
    assert result.baseline_mean is not None
    assert result.z_score is not None
    assert result.z_score > -1.0  # 정상 범위
    assert result.alert_needed == False
    assert result.confidence > 0.5

    print(f"✅ GREEN Test Passed - Score: {result.current_score}, Z: {result.z_score:.2f}")


# ============================================
# Test 2: evaluate() - YELLOW (경미한 저하)
# ============================================

@pytest.mark.asyncio
async def test_evaluate_yellow_mild_decline(evaluator, sample_analysis):
    """
    저하 케이스: 중간 MCDI 점수, 하락 추세 (YELLOW 이상)
    """
    # Arrange
    user_id = "test_user"
    current_score = 72.0  # YELLOW 범위 (60-80)

    # Mock historical scores (안정적 baseline: 78±3)
    import random
    with patch.object(evaluator, '_fetch_historical_scores') as mock_fetch:
        base_date = datetime.now() - timedelta(days=28)
        random.seed(42)  # 재현 가능성
        # Baseline 14일: 78±3 (안정)
        # 이후 14일: 완만히 하락
        mock_fetch.return_value = (
            [(base_date + timedelta(days=i), 78.0 + random.uniform(-3, 3)) for i in range(14)] +
            [(base_date + timedelta(days=i), 76.0 - (i-14) * 0.2 + random.uniform(-2, 2)) for i in range(14, 28)]
        )

        # Act
        result = await evaluator.evaluate(user_id, current_score, sample_analysis)

    # Assert - 하락 추세 감지되어야 함 (정확한 레벨은 escalate 로직에 따라 변동 가능)
    assert result.risk_level in ["YELLOW", "ORANGE", "RED"]
    assert result.current_score == 72.0
    assert result.risk_level != "GREEN"  # 최소한 GREEN은 아님
    assert result.z_score < -1.0  # 저하 감지

    print(f"✅ Decline Detected - Score: {result.current_score}, Risk: {result.risk_level}, Z: {result.z_score:.2f}")


# ============================================
# Test 3: evaluate() - ORANGE (중등도 저하)
# ============================================

@pytest.mark.asyncio
async def test_evaluate_orange_moderate_decline(evaluator, sample_analysis):
    """
    중등도 저하 케이스: 낮은 MCDI 점수, 알림 필요 (ORANGE 이상)
    """
    # Arrange
    user_id = "test_user"
    current_score = 58.0  # ORANGE 범위 (40-60)

    # Mock historical scores (안정적 baseline: 70±3)
    import random
    with patch.object(evaluator, '_fetch_historical_scores') as mock_fetch:
        base_date = datetime.now() - timedelta(days=28)
        random.seed(100)  # 재현 가능성
        # Baseline 14일: 70±3 (안정)
        # 이후 14일: 중간 하락
        mock_fetch.return_value = (
            [(base_date + timedelta(days=i), 70.0 + random.uniform(-3, 3)) for i in range(14)] +
            [(base_date + timedelta(days=i), 66.0 - (i-14) * 0.3 + random.uniform(-2, 2)) for i in range(14, 28)]
        )

        # Act
        result = await evaluator.evaluate(user_id, current_score, sample_analysis)

    # Assert - 중등도 이상 저하 감지되어야 함
    assert result.risk_level in ["ORANGE", "RED"]
    assert result.current_score == 58.0
    assert result.alert_needed == True  # 알림 필요
    assert result.z_score < -1.5  # 중등도 이상 저하

    print(f"✅ Moderate Decline Detected - Score: {result.current_score}, Risk: {result.risk_level}, Z: {result.z_score:.2f}")


# ============================================
# Test 4: evaluate() - RED (심각한 저하)
# ============================================

@pytest.mark.asyncio
async def test_evaluate_red_severe_decline(evaluator, sample_analysis):
    """
    RED 케이스: 매우 낮은 MCDI 점수, 심각한 저하
    """
    # Arrange
    user_id = "test_user"
    current_score = 32.0

    # Mock historical scores (Baseline: 85-90, 매우 급격한 하락)
    with patch.object(evaluator, '_fetch_historical_scores') as mock_fetch:
        base_date = datetime.now() - timedelta(days=28)
        mock_fetch.return_value = [
            (base_date + timedelta(days=i), 88.0 - i * 2.0)
            for i in range(28)
        ]

        # Act
        result = await evaluator.evaluate(user_id, current_score, sample_analysis)

    # Assert
    assert result.risk_level == "RED"
    assert result.current_score == 32.0
    assert result.z_score < -3.0  # 심각한 저하
    assert result.slope < -2.5  # 매우 급격한 하락
    assert result.alert_needed == True
    assert result.check_confounds == True
    assert "즉시" in result.recommendation

    print(f"✅ RED Test Passed - Score: {result.current_score}, Z: {result.z_score:.2f}")


# ============================================
# Test 5: evaluate() - 낮은 Baseline 데이터
# ============================================

@pytest.mark.asyncio
async def test_evaluate_with_low_baseline_data(evaluator, sample_analysis):
    """
    Baseline 데이터 부족 케이스 (신규 사용자)
    """
    # Arrange
    user_id = "new_user"
    # Phase 2 임계값: GREEN≥70, YELLOW 50-70 → 65점은 YELLOW
    current_score = 65.0

    # Mock historical scores (3개만 - 부족)
    with patch.object(evaluator, '_fetch_historical_scores') as mock_fetch:
        base_date = datetime.now() - timedelta(days=3)
        mock_fetch.return_value = [
            (base_date + timedelta(days=i), 64.0 + i * 0.5)
            for i in range(3)
        ]

        # Act
        result = await evaluator.evaluate(user_id, current_score, sample_analysis)

    # Assert
    # Baseline 데이터 부족으로 z_score/slope가 None
    assert result.z_score is None
    assert result.slope is None

    # MCDI 점수만으로 판정 (65 → YELLOW, Phase 2 임계값 기준)
    assert result.risk_level == "YELLOW"
    assert result.confidence == 0.5  # 낮은 신뢰도
    assert result.data_points_used == 4  # 3 + 1(current)

    print(f"✅ Low Baseline Test Passed - Confidence: {result.confidence:.2f}")


# ============================================
# Test 6: _calculate_z_score()
# ============================================

def test_calculate_z_score(evaluator):
    """Z-score 계산 정확도"""
    # Arrange
    current_score = 70.0
    baseline_mean = 80.0
    baseline_std = 5.0

    # Act
    z_score = evaluator._calculate_z_score(
        current_score, baseline_mean, baseline_std
    )

    # Assert
    expected_z = (70.0 - 80.0) / 5.0  # -2.0
    assert z_score == pytest.approx(expected_z, abs=0.01)

    print(f"✅ Z-score Test Passed - Z: {z_score:.2f}")


# ============================================
# Test 7: _calculate_baseline()
# ============================================

def test_calculate_baseline(evaluator):
    """Baseline 계산 정확도"""
    # Arrange
    base_date = datetime.now() - timedelta(days=14)
    historical_scores = [
        (base_date + timedelta(days=i), 80.0 + i * 0.5)
        for i in range(14)
    ]

    # Act
    baseline_mean, baseline_std = evaluator._calculate_baseline(historical_scores)

    # Assert
    assert baseline_mean is not None
    assert baseline_std is not None
    assert 80.0 <= baseline_mean <= 87.0
    assert baseline_std > 0

    print(f"✅ Baseline Test Passed - Mean: {baseline_mean:.2f}, Std: {baseline_std:.2f}")


# ============================================
# Test 8: _calculate_trend() - 하락 추세
# ============================================

def test_calculate_slope_decreasing(evaluator):
    """하락 추세 기울기 계산"""
    # Arrange
    base_date = datetime.now() - timedelta(days=28)
    historical_scores = [
        (base_date + timedelta(days=i), 85.0 - i * 0.7)
        for i in range(28)
    ]
    current_score = 65.0

    # Act
    slope, trend_direction = evaluator._calculate_trend(historical_scores, current_score)

    # Assert
    assert slope is not None
    assert slope < -0.5  # 하락 추세
    assert trend_direction == "decreasing"

    print(f"✅ Decreasing Trend Test Passed - Slope: {slope:.2f}/week")


# ============================================
# Test 9: _calculate_trend() - 안정 추세
# ============================================

def test_calculate_slope_stable(evaluator):
    """안정적 추세 기울기 계산"""
    # Arrange
    base_date = datetime.now() - timedelta(days=28)
    historical_scores = [
        (base_date + timedelta(days=i), 80.0 + (i % 2) * 0.3)
        for i in range(28)
    ]
    current_score = 80.5

    # Act
    slope, trend_direction = evaluator._calculate_trend(historical_scores, current_score)

    # Assert
    assert slope is not None
    assert slope > -0.5  # 안정적
    assert trend_direction in ["stable", "increasing"]

    print(f"✅ Stable Trend Test Passed - Slope: {slope:.2f}/week")


# ============================================
# Test 10: _should_check_confounds()
# ============================================

def test_confound_check_trigger(evaluator):
    """교란 변수 체크 트리거"""
    # Case 1: 낮은 z-score
    assert evaluator._should_check_confounds(-1.8, -1.0) == True

    # Case 2: 급격한 하락
    assert evaluator._should_check_confounds(-1.0, -2.5) == True

    # Case 3: 정상 범위
    assert evaluator._should_check_confounds(-0.5, -0.3) == False

    print("✅ Confound Check Test Passed")


# ============================================
# Test 11: _calculate_confidence()
# ============================================

def test_confidence_calculation(evaluator):
    """신뢰도 계산"""
    # Case 1: z-score와 slope 모두 있음
    conf1 = evaluator._calculate_confidence(-1.5, -2.0)
    assert conf1 == 1.0

    # Case 2: z-score만 있음
    conf2 = evaluator._calculate_confidence(-1.5, None)
    assert conf2 == 0.75

    # Case 3: slope만 있음
    conf3 = evaluator._calculate_confidence(None, -2.0)
    assert conf3 == 0.75

    # Case 4: 둘 다 없음
    conf4 = evaluator._calculate_confidence(None, None)
    assert conf4 == 0.5

    print("✅ Confidence Calculation Test Passed")


# ============================================
# Test 12: _escalate_risk()
# ============================================

def test_escalate_risk(evaluator):
    """위험도 상향 조정"""
    assert evaluator._escalate_risk("GREEN", 1) == "YELLOW"
    assert evaluator._escalate_risk("GREEN", 2) == "ORANGE"
    assert evaluator._escalate_risk("GREEN", 3) == "RED"
    assert evaluator._escalate_risk("YELLOW", 1) == "ORANGE"
    assert evaluator._escalate_risk("ORANGE", 1) == "RED"
    assert evaluator._escalate_risk("RED", 1) == "RED"  # 최대값 유지

    print("✅ Escalate Risk Test Passed")


# ============================================
# Test 13: _generate_recommendation()
# ============================================

def test_generate_recommendation(evaluator):
    """권장 조치 생성"""
    # GREEN
    rec_green = evaluator._generate_recommendation("GREEN", -0.5, -0.2)
    assert "정상" in rec_green

    # YELLOW
    rec_yellow = evaluator._generate_recommendation("YELLOW", -1.2, -0.8)
    assert "경미" in rec_yellow

    # ORANGE
    rec_orange = evaluator._generate_recommendation("ORANGE", -1.8, -2.3)
    assert "교란" in rec_orange or "전문가" in rec_orange

    # RED
    rec_red = evaluator._generate_recommendation("RED", -3.5, -4.0)
    assert "즉시" in rec_red

    print("✅ Recommendation Test Passed")


# ============================================
# Test 14: to_dict()
# ============================================

def test_to_dict(evaluator):
    """딕셔너리 변환"""
    # Arrange
    evaluation = RiskEvaluation(
        risk_level="YELLOW",
        confidence=0.85,
        current_score=65.0,
        baseline_mean=78.0,
        baseline_std=5.2,
        z_score=-2.5,
        slope=-1.8,
        trend_direction="decreasing",
        primary_reason="경미한 저하",
        contributing_factors=["낮은 z-score", "하락 추세"],
        alert_needed=False,
        check_confounds=True,
        recommendation="모니터링 권장",
        data_points_used=28,
        evaluation_timestamp=datetime.now()
    )

    # Act
    result_dict = evaluator.to_dict(evaluation)

    # Assert
    assert result_dict["risk_level"] == "YELLOW"
    assert result_dict["current_score"] == 65.0
    assert result_dict["z_score"] == -2.5
    assert isinstance(result_dict["evaluation_timestamp"], str)

    print("✅ to_dict Test Passed")


# ============================================
# Test Summary
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Risk Evaluator 테스트 시작")
    print("="*60 + "\n")

    pytest.main([__file__, "-v", "-s"])
