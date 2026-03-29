"""
DialogueManager Workflow 통합 테스트

message_processor.py에서 호출하는 workflow 메서드들을 테스트합니다.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.dialogue.dialogue_manager import DialogueManager
from core.dialogue.response_generator import ResponseGenerator
from core.dialogue.prompt_builder import PromptBuilder
from database.redis_client import RedisClient


# ============================================
# Fixtures
# ============================================
@pytest.fixture
def mock_redis():
    """Mock Redis Client"""
    # Mock session data
    async def mock_get_session(user_id):
        return {
            "session_id": "test_session",
            "user_id": user_id,
            "turn_count": 5,
            "conversation_history": [],
            "context": {
                "last_confound_index": 1
            },
            "started_at": datetime.now().isoformat(),
            "last_updated_at": datetime.now().isoformat()
        }

    async def mock_set_session(user_id, session_data, ttl=None):
        return True

    mock_client = MagicMock()
    mock_client.get_session = mock_get_session
    mock_client.set_session = mock_set_session
    mock_client.update_session = AsyncMock(return_value=True)

    return mock_client


@pytest.fixture
def mock_response_generator():
    """Mock ResponseGenerator"""
    generator = MagicMock(spec=ResponseGenerator)

    async def mock_generate(user_message, system_prompt, conversation_history):
        return "좋은 추억이네요! 😊"

    generator.generate = mock_generate
    return generator


@pytest.fixture
def prompt_builder():
    """Real PromptBuilder (not mocked)"""
    return PromptBuilder()


@pytest.fixture
def dialogue_manager(mock_redis, mock_response_generator, prompt_builder):
    """DialogueManager 인스턴스 with mocked redis_client"""
    # Patch the global redis_client in dialogue_manager module
    with patch('core.dialogue.dialogue_manager.redis_client', mock_redis):
        manager = DialogueManager(
            response_generator=mock_response_generator,
            prompt_builder=prompt_builder
        )
        # Keep the mock redis_client accessible
        manager._redis_mock = mock_redis
        yield manager


@pytest.fixture
def sample_analysis():
    """샘플 분석 결과"""
    return {
        "scores": {
            "LR": 78.5,
            "SD": 82.3,
            "NC": 75.0,
            "TO": 80.0,
            "ER": 65.0,  # Weakest
            "RT": 85.0
        },
        "mcdi_score": 77.6
    }


# ============================================
# 1. plan_next() Tests
# ============================================
@pytest.mark.asyncio
async def test_plan_next_finds_weakest_metric(dialogue_manager, sample_analysis):
    """정상 케이스: weakest metric 찾기"""
    # Arrange
    user_id = "test_user"
    risk_level = "YELLOW"

    # Act
    plan = await dialogue_manager.plan_next(
        user_id=user_id,
        current_analysis=sample_analysis,
        risk_level=risk_level
    )

    # Assert
    assert plan is not None
    assert plan["category"] == "episodic_recall"  # ER이 65로 최저
    assert plan["difficulty"] == "medium"  # YELLOW → medium
    assert "question_type" in plan

    print(f"✅ Plan Next - Weakest: ER (65.0) → Category: {plan['category']}")


@pytest.mark.asyncio
async def test_plan_next_adjusts_difficulty_by_risk(dialogue_manager, sample_analysis):
    """정상 케이스: 위험도별 난이도 조정"""
    user_id = "test_user"

    # Test 1: RED → easy
    plan_red = await dialogue_manager.plan_next(
        user_id=user_id,
        current_analysis=sample_analysis,
        risk_level="RED"
    )
    assert plan_red["difficulty"] == "easy"

    # Test 2: GREEN → medium/hard
    plan_green = await dialogue_manager.plan_next(
        user_id=user_id,
        current_analysis=sample_analysis,
        risk_level="GREEN"
    )
    assert plan_green["difficulty"] in ["medium", "hard"]

    print(f"✅ Difficulty Adjustment - RED: easy, GREEN: {plan_green['difficulty']}")


@pytest.mark.asyncio
async def test_plan_next_with_empty_scores(dialogue_manager):
    """엣지 케이스: 점수 없음"""
    # Arrange
    user_id = "test_user"
    analysis = {"scores": {}, "mcdi_score": 0}

    # Act
    plan = await dialogue_manager.plan_next(
        user_id=user_id,
        current_analysis=analysis,
        risk_level="GREEN"
    )

    # Assert
    assert plan["category"] == "general"  # 기본값
    assert plan["question_type"] == "open_ended"

    print("✅ Empty Scores → Default: general/open_ended")


# ============================================
# 2. generate_confound_question() Tests
# ============================================
@pytest.mark.asyncio
async def test_generate_confound_question_rotates(dialogue_manager):
    """정상 케이스: 질문 순환"""
    # Arrange
    user_id = "test_user"

    # Act - 여러 번 호출
    questions = []
    for _ in range(3):
        question = await dialogue_manager.generate_confound_question(user_id)
        questions.append(question)

    # Assert
    assert len(questions) == 3
    assert all(q for q in questions)  # 모두 비어있지 않음

    # 순환 확인 (마지막 인덱스가 1에서 시작했으므로 2, 3, 4 순서)
    print(f"✅ Confound Questions:")
    for i, q in enumerate(questions, start=1):
        print(f"  {i}. {q}")


@pytest.mark.asyncio
async def test_generate_confound_question_types(mock_response_generator, prompt_builder):
    """정상 케이스: 5가지 질문 유형 (stateful mock)"""
    user_id = "test_user"

    # Create a truly stateful mock that stores the entire session
    stored_sessions = {}

    async def stateful_get_session(user_id):
        # Return the stored session for this user
        return stored_sessions.get(user_id)

    async def stateful_set_session(user_id, session_data, ttl=None):
        # Store the session
        stored_sessions[user_id] = session_data
        return True

    # Create mock redis
    stateful_mock = MagicMock()
    stateful_mock.get_session = stateful_get_session
    stateful_mock.set_session = stateful_set_session

    # Create dialogue_manager with stateful mock
    with patch('core.dialogue.dialogue_manager.redis_client', stateful_mock):
        dialogue_manager = DialogueManager(
            response_generator=mock_response_generator,
            prompt_builder=prompt_builder
        )

        # Start a session first to ensure stateful updates work
        await dialogue_manager.start_session(user_id)

        # Act - 5개 모두 생성
        questions = []
        for i in range(5):
            question = await dialogue_manager.generate_confound_question(user_id)
            questions.append(question)
            print(f"  Question {i+1}: {question}")

        # Assert - 5개 모두 다름
        unique_questions = set(questions)
        assert len(unique_questions) == 5, f"Expected 5 unique questions, got {len(unique_questions)}: {unique_questions}"

        # 카테고리 확인
        keywords = ["잠", "기분", "약", "불편", "걱정"]
        for keyword in keywords:
            assert any(keyword in q for q in questions), f"'{keyword}' 질문 누락"

        print("✅ All 5 Confound Types Present")


# ============================================
# 3. generate_next_question() Tests
# ============================================
@pytest.mark.asyncio
async def test_generate_next_question_episodic_recall(dialogue_manager):
    """정상 케이스: 일화 기억 질문 생성"""
    # Arrange
    user_id = "test_user"
    category = "episodic_recall"
    difficulty = "medium"
    question_type = "free_recall"

    # Act
    question = await dialogue_manager.generate_next_question(
        user_id=user_id,
        category=category,
        difficulty=difficulty,
        question_type=question_type
    )

    # Assert
    assert question is not None
    assert len(question) > 0
    assert isinstance(question, str)

    print(f"✅ ER Question Generated: {question}")


@pytest.mark.asyncio
async def test_generate_next_question_all_categories(dialogue_manager):
    """정상 케이스: 모든 카테고리 질문 생성"""
    # Arrange
    user_id = "test_user"
    categories = [
        "episodic_recall",
        "temporal_orientation",
        "narrative",
        "lexical_richness",
        "semantic_focus",
        "general"
    ]

    # Act & Assert
    for category in categories:
        question = await dialogue_manager.generate_next_question(
            user_id=user_id,
            category=category,
            difficulty="medium",
            question_type="open_ended"
        )

        assert question is not None
        assert len(question) > 0
        print(f"✅ {category}: {question}")


@pytest.mark.asyncio
async def test_generate_next_question_all_difficulties(dialogue_manager):
    """정상 케이스: 모든 난이도 질문 생성"""
    # Arrange
    user_id = "test_user"
    category = "episodic_recall"
    difficulties = ["easy", "medium", "hard"]

    # Act & Assert
    for difficulty in difficulties:
        question = await dialogue_manager.generate_next_question(
            user_id=user_id,
            category=category,
            difficulty=difficulty,
            question_type="free_recall"
        )

        assert question is not None
        assert len(question) > 0
        print(f"✅ {difficulty}: {question}")


# ============================================
# 4. Full Workflow Integration Test
# ============================================
@pytest.mark.asyncio
async def test_full_workflow_integration(dialogue_manager, sample_analysis):
    """
    통합 테스트: 전체 워크플로우

    시나리오:
    1. 분석 결과 → plan_next()
    2. 위험도 하락 → generate_confound_question()
    3. 다음 질문 → generate_next_question()
    """
    # Arrange
    user_id = "test_user"
    risk_level = "ORANGE"

    # Step 1: Plan Next Interaction
    plan = await dialogue_manager.plan_next(
        user_id=user_id,
        current_analysis=sample_analysis,
        risk_level=risk_level
    )

    print(f"\n📋 Step 1 - Plan:")
    print(f"  Category: {plan['category']}")
    print(f"  Difficulty: {plan['difficulty']}")
    print(f"  Type: {plan['question_type']}")

    # Step 2: Confound Check (점수 하락 가정)
    confound_question = await dialogue_manager.generate_confound_question(user_id)

    print(f"\n⚠️ Step 2 - Confound Check:")
    print(f"  Question: {confound_question}")

    # Step 3: Next Question
    next_question = await dialogue_manager.generate_next_question(
        user_id=user_id,
        category=plan["category"],
        difficulty=plan["difficulty"],
        question_type=plan["question_type"]
    )

    print(f"\n❓ Step 3 - Next Question:")
    print(f"  {next_question}")

    # Assert
    assert plan is not None
    assert confound_question is not None
    assert next_question is not None

    print("\n✅ Full Workflow Integration Passed!")


@pytest.mark.asyncio
async def test_workflow_with_different_risk_levels(dialogue_manager, sample_analysis):
    """통합 테스트: 위험도별 워크플로우"""
    user_id = "test_user"
    risk_levels = ["GREEN", "YELLOW", "ORANGE", "RED"]

    print("\n📊 Workflow by Risk Level:")

    for risk_level in risk_levels:
        # Plan
        plan = await dialogue_manager.plan_next(
            user_id=user_id,
            current_analysis=sample_analysis,
            risk_level=risk_level
        )

        # Generate Question
        question = await dialogue_manager.generate_next_question(
            user_id=user_id,
            category=plan["category"],
            difficulty=plan["difficulty"],
            question_type=plan["question_type"]
        )

        print(f"\n  {risk_level}:")
        print(f"    Difficulty: {plan['difficulty']}")
        print(f"    Question: {question[:50]}...")

        # Validate difficulty matches risk
        if risk_level == "RED":
            assert plan["difficulty"] == "easy"
        elif risk_level == "GREEN":
            assert plan["difficulty"] in ["medium", "hard"]

    print("\n✅ All Risk Levels Validated!")


# ============================================
# 5. Error Handling Tests
# ============================================
@pytest.mark.asyncio
async def test_plan_next_handles_missing_metrics(dialogue_manager):
    """엣지 케이스: 일부 지표 누락"""
    # Arrange
    user_id = "test_user"
    analysis = {
        "scores": {
            "LR": 80.0,
            "SD": None,  # 누락
            "NC": 75.0,
            "TO": None,  # 누락
            "ER": 70.0,
            "RT": 85.0
        },
        "mcdi_score": 77.5
    }

    # Act
    plan = await dialogue_manager.plan_next(
        user_id=user_id,
        current_analysis=analysis,
        risk_level="YELLOW"
    )

    # Assert
    assert plan is not None
    # None 값 제외하고 최저 점수 찾기 → NC(75) 또는 ER(70)
    assert plan["category"] in ["narrative", "episodic_recall"]

    print(f"✅ Handles Missing Metrics - Category: {plan['category']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
