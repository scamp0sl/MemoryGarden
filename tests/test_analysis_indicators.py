"""
6개 MCDI 지표 통합 테스트

각 지표의 정상 동작, 에러 처리, 점수 범위를 검증합니다.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from core.analysis.lexical_richness import LexicalRichnessAnalyzer
from core.analysis.semantic_drift import SemanticDriftAnalyzer
from core.analysis.narrative_coherence import NarrativeCoherenceAnalyzer
from core.analysis.temporal_orientation import TemporalOrientationAnalyzer
from core.analysis.episodic_recall import EpisodicRecallAnalyzer
from core.analysis.response_time import ResponseTimeAnalyzer
from core.analysis.mcdi_calculator import MCDICalculator
from core.analysis.analyzer import Analyzer
from utils.exceptions import AnalysisError, MCDICalculationError


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_llm_service():
    """Mock LLM 서비스"""
    llm = AsyncMock()

    # Topic drift: 0 (no drift)
    # Logic score: 4 (good)
    # Temporal order: 5 (excellent)
    # Structure: 4 (good)
    # Consistency: 4 (good)
    # Contradiction: 0 (no contradiction)

    async def mock_call(prompt, **kwargs):
        # 텍스트 추출 (프롬프트에서)
        text_match = None
        if "텍스트:" in prompt:
            text_match = prompt.split("텍스트:")[1].split("\n")[0].strip()

        # 단편적 응답 감지 (짧은 문장, 단어만 나열)
        is_fragmented = False
        if text_match:
            # 10자 이하 또는 단어만 나열된 경우
            if len(text_match) < 10 or text_match.count('.') >= 2:
                is_fragmented = True

        if "주제" in prompt or "관련성" in prompt:
            return "0"  # No drift
        elif "논리성" in prompt:
            return "1" if is_fragmented else "4"  # Poor logic for fragmented
        elif "시간적 순서" in prompt or "시간 순서" in prompt:
            return "1" if is_fragmented else "5"  # Poor order for fragmented
        elif "서사 구조" in prompt:
            return "1" if is_fragmented else "4"  # Poor structure for fragmented
        elif "일관성" in prompt:
            return "1" if is_fragmented else "4"  # Poor consistency for fragmented
        elif "모순" in prompt:
            return "0"  # No contradiction
        else:
            return "3"  # Default neutral

    llm.call = mock_call
    return llm


@pytest.fixture
def mock_embedder():
    """Mock Embedder"""
    embedder = AsyncMock()

    # 고정된 임베딩 벡터 반환 (유사도 0.9로 가정)
    async def mock_embed(text):
        import numpy as np
        # 간단한 벡터 생성 (길이 기반)
        base = [0.1] * 1536
        base[0] = len(text) * 0.01  # 텍스트 길이 반영
        return np.array(base)

    embedder.embed = mock_embed
    return embedder


@pytest.fixture
def sample_message():
    """테스트용 샘플 메시지"""
    return "지난 봄에 엄마와 뒷산에서 쑥을 뜯었어요. 쑥이 많이 나 있었고 햇살이 따뜻했어요."


@pytest.fixture
def sample_context():
    """테스트용 샘플 컨텍스트"""
    return {
        "question": "어머니와 함께 했던 봄철 추억이 있나요?",
        "current_datetime": datetime(2025, 3, 17, 10, 30),
        "episodic": [
            {"fact": "봄에 쑥을 뜯었다", "verified": True},
            {"fact": "엄마와 함께였다", "verified": True}
        ],
        "biographical": {"mother_name": "이순자"},
        "previous_statements": ["엄마는 선생님이셨어요"],
        "response_latency": 3.5,
        "typing_pauses": [0.5, 0.8, 1.2],
        "historical_latencies": [2.8, 3.1, 3.2, 4.5]
    }


# ============================================
# Test 1: LR (Lexical Richness)
# ============================================

@pytest.mark.asyncio
async def test_lr_normal_case(sample_message):
    """LR 정상 케이스: 구체적인 응답"""
    analyzer = LexicalRichnessAnalyzer()

    result = await analyzer.analyze(sample_message)

    # 구조 검증
    assert "score" in result
    assert "components" in result
    assert "details" in result

    # 점수 범위 검증
    assert 0 <= result["score"] <= 100

    # 컴포넌트 검증
    assert "pronoun_ratio" in result["components"]
    assert "mattr" in result["components"]
    assert "concreteness" in result["components"]
    assert "empty_speech_ratio" in result["components"]

    # 세부 정보 검증
    assert "total_tokens" in result["details"]
    assert "unique_tokens" in result["details"]

    print(f"✅ LR Test Passed - Score: {result['score']:.2f}")


@pytest.mark.asyncio
async def test_lr_vague_response():
    """LR 비정상 케이스: 모호한 응답"""
    analyzer = LexicalRichnessAnalyzer()

    result = await analyzer.analyze("그거 있잖아요. 그거 말이에요. 뭐더라...")

    # 점수가 낮아야 함 (모호한 표현 많음)
    assert result["score"] < 60
    assert result["components"]["empty_speech_ratio"] > 0.3

    print(f"✅ LR Vague Test Passed - Score: {result['score']:.2f}")


@pytest.mark.asyncio
async def test_lr_empty_input():
    """LR 에러 케이스: 빈 입력"""
    analyzer = LexicalRichnessAnalyzer()

    with pytest.raises(AnalysisError, match="cannot be empty"):
        await analyzer.analyze("")


# ============================================
# Test 2: SD (Semantic Drift)
# ============================================

@pytest.mark.asyncio
async def test_sd_normal_case(mock_llm_service, mock_embedder, sample_message):
    """SD 정상 케이스: 질문과 관련된 응답"""
    analyzer = SemanticDriftAnalyzer(mock_llm_service, mock_embedder)

    context = {
        "question": "어머니와 함께 했던 봄철 추억이 있나요?"
    }

    result = await analyzer.analyze(sample_message, context)

    # 구조 검증
    assert "score" in result
    assert "components" in result
    assert "details" in result

    # 점수 범위 검증
    assert 0 <= result["score"] <= 100

    # 컴포넌트 검증
    assert "relevance" in result["components"]
    assert "coherence" in result["components"]
    assert "topic_drift" in result["components"]
    assert "logical_flow" in result["components"]

    print(f"✅ SD Test Passed - Score: {result['score']:.2f}")


@pytest.mark.asyncio
async def test_sd_without_question(mock_llm_service, mock_embedder, sample_message):
    """SD 엣지 케이스: 질문 없음"""
    analyzer = SemanticDriftAnalyzer(mock_llm_service, mock_embedder)

    result = await analyzer.analyze(sample_message, {})

    # 질문이 없으면 relevance는 1.0 (중립)
    assert result["components"]["relevance"] == 1.0
    assert result["score"] > 0

    print(f"✅ SD No Question Test Passed - Score: {result['score']:.2f}")


# ============================================
# Test 3: NC (Narrative Coherence)
# ============================================

@pytest.mark.asyncio
async def test_nc_normal_case(mock_llm_service, sample_message):
    """NC 정상 케이스: 완결된 서사"""
    analyzer = NarrativeCoherenceAnalyzer(mock_llm_service)

    result = await analyzer.analyze(sample_message)

    # 구조 검증
    assert "score" in result
    assert "components" in result
    assert "details" in result

    # 점수 범위 검증
    assert 0 <= result["score"] <= 100

    # 컴포넌트 검증
    assert "coverage_5w1h" in result["components"]
    assert "temporal_order" in result["components"]
    assert "repetitiveness" in result["components"]
    assert "narrative_structure" in result["components"]

    # 5W1H 검증
    assert "w5h1_present" in result["details"]
    assert "w5h1_missing" in result["details"]

    print(f"✅ NC Test Passed - Score: {result['score']:.2f}")
    print(f"   5W1H Present: {result['details']['w5h1_present']}")


@pytest.mark.asyncio
async def test_nc_fragmented_response(mock_llm_service):
    """NC 비정상 케이스: 단편적 응답"""
    analyzer = NarrativeCoherenceAnalyzer(mock_llm_service)

    result = await analyzer.analyze("쑥. 산. 엄마.")

    # 점수가 낮아야 함 (서사 구조 부족)
    assert result["score"] < 50
    assert result["components"]["coverage_5w1h"] < 0.5

    print(f"✅ NC Fragmented Test Passed - Score: {result['score']:.2f}")


# ============================================
# Test 4: TO (Temporal Orientation)
# ============================================

@pytest.mark.asyncio
async def test_to_normal_case(mock_llm_service):
    """TO 정상 케이스: 정확한 시간 표현"""
    analyzer = TemporalOrientationAnalyzer(mock_llm_service)

    # 2025년 3월 17일 월요일, 오전 10시
    context = {
        "current_datetime": datetime(2025, 3, 17, 10, 0)
    }

    message = "오늘은 월요일이고 봄이라 날씨가 좋아요. 아침에 산책했어요."

    result = await analyzer.analyze(message, context)

    # 구조 검증
    assert "score" in result
    assert "components" in result
    assert "details" in result

    # 점수 범위 검증
    assert 0 <= result["score"] <= 100

    # 컴포넌트 검증
    assert "date_accuracy" in result["components"]
    assert "season_score" in result["components"]
    assert "time_consistency" in result["components"]
    assert "temporal_consistency" in result["components"]

    # 정확한 표현이므로 높은 점수
    assert result["score"] > 80
    assert result["details"]["weekday_match"] == True
    assert result["details"]["season_match"] == True

    print(f"✅ TO Test Passed - Score: {result['score']:.2f}")


@pytest.mark.asyncio
async def test_to_incorrect_weekday(mock_llm_service):
    """TO 비정상 케이스: 잘못된 요일"""
    analyzer = TemporalOrientationAnalyzer(mock_llm_service)

    # 실제는 월요일인데 화요일이라고 함
    context = {
        "current_datetime": datetime(2025, 3, 17, 10, 0)  # 월요일
    }

    message = "오늘은 화요일이에요"

    result = await analyzer.analyze(message, context)

    # 요일이 틀렸으므로 점수 낮음
    assert result["details"]["weekday_match"] == False
    assert result["components"]["date_accuracy"] < 1.0

    print(f"✅ TO Incorrect Test Passed - Score: {result['score']:.2f}")


# ============================================
# Test 5: ER (Episodic Recall)
# ============================================

@pytest.mark.asyncio
async def test_er_normal_case(mock_llm_service, sample_message):
    """ER 정상 케이스: 정확한 회상"""
    analyzer = EpisodicRecallAnalyzer(mock_llm_service)

    context = {
        "episodic": [
            {"fact": "봄에 쑥을 뜯었다", "verified": True},
            {"fact": "엄마와 함께였다", "verified": True}
        ],
        "biographical": {"mother_name": "이순자"},
        "previous_statements": ["엄마는 선생님이셨어요"]
    }

    result = await analyzer.analyze(sample_message, context)

    # 구조 검증
    assert "score" in result
    assert "components" in result
    assert "details" in result

    # 점수 범위 검증
    assert 0 <= result["score"] <= 100

    # 컴포넌트 검증
    assert "recall_accuracy" in result["components"]
    assert "detail_richness" in result["components"]
    assert "contradiction_rate" in result["components"]
    assert "consistency_score" in result["components"]

    # 정확한 회상이므로 높은 점수
    assert result["components"]["recall_accuracy"] > 0.8
    assert result["components"]["detail_richness"] > 0.5

    print(f"✅ ER Test Passed - Score: {result['score']:.2f}")


@pytest.mark.asyncio
async def test_er_without_context(mock_llm_service):
    """ER 엣지 케이스: 컨텍스트 없음"""
    analyzer = EpisodicRecallAnalyzer(mock_llm_service)

    result = await analyzer.analyze("엄마와 쑥을 뜯었어요", {})

    # 컨텍스트 없어도 detail_richness는 계산 가능
    assert result["components"]["recall_accuracy"] == 1.0  # 중립
    assert result["components"]["detail_richness"] > 0

    print(f"✅ ER No Context Test Passed - Score: {result['score']:.2f}")


# ============================================
# Test 6: RT (Response Time)
# ============================================

@pytest.mark.asyncio
async def test_rt_normal_case(sample_message):
    """RT 정상 케이스: 적절한 응답 시간"""
    analyzer = ResponseTimeAnalyzer()

    context = {
        "response_latency": 3.5,
        "typing_pauses": [0.5, 0.8, 1.2],
        "historical_latencies": [2.8, 3.1, 3.2, 4.5]
    }

    result = await analyzer.analyze(sample_message, context)

    # 구조 검증
    assert "score" in result
    assert "components" in result
    assert "details" in result

    # 점수 범위 검증
    assert 0 <= result["score"] <= 100

    # 컴포넌트 검증
    assert "latency_score" in result["components"]
    assert "efficiency" in result["components"]
    assert "pause_score" in result["components"]
    assert "consistency" in result["components"]

    # 세부 정보 검증
    assert result["details"]["latency_category"] in ["excellent", "good", "moderate", "slow", "very_slow"]

    print(f"✅ RT Test Passed - Score: {result['score']:.2f}")


@pytest.mark.asyncio
async def test_rt_missing_latency(sample_message):
    """RT 에러 케이스: response_latency 누락"""
    analyzer = ResponseTimeAnalyzer()

    with pytest.raises(AnalysisError, match="response_latency is required"):
        await analyzer.analyze(sample_message, {})


@pytest.mark.asyncio
async def test_rt_slow_response(sample_message):
    """RT 비정상 케이스: 매우 느린 응답"""
    analyzer = ResponseTimeAnalyzer()

    context = {
        "response_latency": 25.0,  # 25초 (매우 느림)
        "typing_pauses": [2.5, 3.0, 4.0],  # 긴 중단들
        "historical_latencies": [3.0, 4.0, 20.0, 25.0]
    }

    result = await analyzer.analyze(sample_message, context)

    # 느린 응답이므로 점수 낮음
    assert result["score"] < 50
    assert result["details"]["latency_category"] == "very_slow"

    print(f"✅ RT Slow Test Passed - Score: {result['score']:.2f}")


# ============================================
# Test 7: MCDI Calculator
# ============================================

def test_mcdi_calculator_full_scores():
    """MCDI 계산기: 6개 지표 모두 있음"""
    calculator = MCDICalculator()

    scores = {
        "LR": 78.5,
        "SD": 82.3,
        "NC": 75.0,
        "TO": 80.0,
        "ER": 72.5,
        "RT": 70.0
    }

    result = calculator.calculate_with_confidence(scores)

    # 구조 검증
    assert "mcdi_score" in result
    assert "reliability" in result
    assert "risk_category" in result

    # 신뢰도 100%
    assert result["reliability"] == 1.0

    # 위험도 분류
    assert result["risk_category"] in ["GREEN", "YELLOW", "ORANGE", "RED"]

    # 점수 범위
    assert 0 <= result["mcdi_score"] <= 100

    print(f"✅ MCDI Full Test Passed - Score: {result['mcdi_score']:.2f}, Risk: {result['risk_category']}")


def test_mcdi_calculator_partial_scores():
    """MCDI 계산기: 3개 지표만 있음 (최소)"""
    calculator = MCDICalculator()

    scores = {
        "LR": 80.0,
        "SD": 85.0,
        "NC": 75.0
    }

    result = calculator.calculate_with_confidence(scores)

    # 신뢰도 50%
    assert result["reliability"] == 0.5

    # 누락 지표
    assert set(result["missing_metrics"]) == {"TO", "ER", "RT"}

    # 여전히 계산 가능
    assert 0 <= result["mcdi_score"] <= 100

    print(f"✅ MCDI Partial Test Passed - Score: {result['mcdi_score']:.2f}, Reliability: {result['reliability']:.1%}")


def test_mcdi_calculator_insufficient_scores():
    """MCDI 계산기: 지표 부족 (2개)"""
    calculator = MCDICalculator()

    scores = {"LR": 80.0, "SD": 85.0}

    with pytest.raises(MCDICalculationError, match="At least 3 metrics required"):
        calculator.calculate(scores)


# ============================================
# Test 8: Integrated Analyzer
# ============================================

@pytest.mark.asyncio
async def test_analyzer_full_integration(mock_llm_service, mock_embedder, sample_message, sample_context):
    """통합 분석기: 전체 파이프라인"""
    analyzer = Analyzer(mock_llm_service, mock_embedder)

    result = await analyzer.analyze(sample_message, sample_context)

    # 구조 검증
    assert "scores" in result
    assert "mcdi_score" in result
    assert "mcdi_details" in result
    assert "failed_metrics" in result

    # 6개 지표 모두 실행됨
    assert "LR" in result["scores"]
    assert "SD" in result["scores"]
    assert "NC" in result["scores"]
    assert "TO" in result["scores"]
    assert "ER" in result["scores"]
    assert "RT" in result["scores"]

    # 세부 결과 존재
    assert "lr_detail" in result
    assert "sd_detail" in result
    assert "nc_detail" in result
    assert "to_detail" in result
    assert "er_detail" in result
    assert "rt_detail" in result

    # MCDI 점수 범위
    assert 0 <= result["mcdi_score"] <= 100

    # 실패한 지표 확인
    print(f"✅ Integrated Analyzer Test Passed")
    print(f"   MCDI Score: {result['mcdi_score']:.2f}")
    print(f"   Risk: {result['mcdi_details']['risk_category']}")
    print(f"   Reliability: {result['mcdi_details']['reliability']:.1%}")
    print(f"   Failed: {result['failed_metrics']}")


@pytest.mark.asyncio
async def test_analyzer_partial_failure(mock_llm_service, mock_embedder, sample_message):
    """통합 분석기: 일부 지표 실패 (RT 없음)"""
    analyzer = Analyzer(mock_llm_service, mock_embedder)

    # RT에 필요한 response_latency 누락
    context = {
        "question": "어머니와 함께 했던 봄철 추억이 있나요?",
        "current_datetime": datetime(2025, 3, 17, 10, 30)
    }

    result = await analyzer.analyze(sample_message, context)

    # RT만 실패, 나머지 5개 성공
    assert "RT" in result["failed_metrics"]
    assert len(result["failed_metrics"]) == 1

    # MCDI는 5개로 계산됨
    assert result["mcdi_score"] > 0
    assert result["mcdi_details"]["reliability"] < 1.0

    print(f"✅ Partial Failure Test Passed")
    print(f"   Failed: {result['failed_metrics']}")
    print(f"   MCDI: {result['mcdi_score']:.2f} (5/6 indicators)")


# ============================================
# Test Summary
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("6개 MCDI 지표 테스트 시작")
    print("="*60 + "\n")

    import asyncio

    # Run all tests
    pytest.main([__file__, "-v", "-s"])
