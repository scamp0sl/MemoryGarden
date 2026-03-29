"""
SessionWorkflow 통합 테스트

전체 8단계 워크플로우의 통합 동작을 테스트합니다.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.workflow.session_workflow import SessionWorkflow
from core.workflow.context import ProcessingContext
from core.memory.memory_manager import MemoryManager
from core.analysis.analyzer import Analyzer
from core.analysis.risk_evaluator import RiskEvaluator, RiskEvaluation
from core.dialogue.dialogue_manager import DialogueManager
from services.notification_service import NotificationService


# ============================================
# Fixtures
# ============================================
@pytest.fixture
def mock_memory_manager():
    """Mock MemoryManager"""
    manager = MagicMock(spec=MemoryManager)

    # retrieve_all
    async def mock_retrieve(user_id, query=None, limit=10):
        return {
            "session": {
                "conversation_history": [
                    {"user": "안녕하세요", "assistant": "반갑습니다"}
                ]
            },
            "episodic": [
                {"content": "봄에 쑥을 뜯었다", "similarity": 0.85}
            ],
            "biographical": [
                {"entity": "daughter_name", "value": "수진"}
            ],
            "analytical": [
                {"mcdi_score": 82.5, "timestamp": datetime.now().isoformat()}
            ]
        }

    # store_all
    async def mock_store(user_id, message, response, analysis):
        return {
            "session_stored": True,
            "episodic_stored": True,
            "biographical_stored": True,
            "analytical_stored": True
        }

    manager.retrieve_all = mock_retrieve
    manager.store_all = mock_store

    return manager


@pytest.fixture
def mock_analyzer():
    """Mock Analyzer"""
    analyzer = MagicMock(spec=Analyzer)

    async def mock_analyze(message, memory, message_type="text", image_url=None):
        return {
            "scores": {
                "LR": 78.5,
                "SD": 82.3,
                "NC": 75.0,
                "TO": 80.0,
                "ER": 65.0,  # Weakest
                "RT": 85.0
            },
            "mcdi_score": 77.6,
            "lr_detail": {},
            "sd_detail": {},
            "nc_detail": {},
            "to_detail": {},
            "er_detail": {},
            "rt_detail": {},
            "contradictions": [],
            "failed_metrics": [],
            "timestamp": datetime.now().isoformat()
        }

    analyzer.analyze = mock_analyze
    return analyzer


@pytest.fixture
def mock_risk_evaluator():
    """Mock RiskEvaluator"""
    evaluator = MagicMock(spec=RiskEvaluator)

    async def mock_evaluate(user_id, current_score, analysis):
        return RiskEvaluation(
            risk_level="YELLOW",
            confidence=0.85,
            current_score=77.6,
            baseline_mean=80.0,
            baseline_std=5.0,
            z_score=-0.48,
            slope=-0.8,
            trend_direction="decreasing",
            primary_reason="경미한 저하",
            contributing_factors=["ER 낮음"],
            alert_needed=False,
            check_confounds=False,
            recommendation="모니터링 지속",
            data_points_used=15,
            evaluation_timestamp=datetime.now()
        )

    evaluator.evaluate = mock_evaluate
    return evaluator


@pytest.fixture
def mock_dialogue_manager():
    """Mock DialogueManager"""
    manager = MagicMock(spec=DialogueManager)

    # plan_next
    manager.plan_next = AsyncMock(return_value={
        "category": "episodic_recall",
        "difficulty": "medium",
        "question_type": "free_recall"
    })

    # generate_confound_question
    manager.generate_confound_question = AsyncMock(
        return_value="요즘 잠은 잘 주무시나요? 🌙"
    )

    # generate_next_question
    manager.generate_next_question = AsyncMock(
        return_value="어릴 적 가장 기억에 남는 명절은 언제인가요? 🎊"
    )

    # generate_response
    async def mock_response(user_id, user_message, next_question=None, **kwargs):
        return f"좋은 이야기네요! 😊 오늘은 여기까지 하고, 다음에 또 이야기 나눠요."

    manager.generate_response = AsyncMock(side_effect=mock_response)

    return manager


@pytest.fixture
def mock_notification_service():
    """Mock NotificationService"""
    service = MagicMock(spec=NotificationService)

    service.send_guardian_alert = AsyncMock(
        return_value={"alert_sent": True, "channel": "kakao"}
    )

    return service


@pytest.fixture
def workflow(
    mock_memory_manager,
    mock_analyzer,
    mock_risk_evaluator,
    mock_dialogue_manager,
    mock_notification_service
):
    """SessionWorkflow 인스턴스"""
    return SessionWorkflow(
        memory_manager=mock_memory_manager,
        analyzer=mock_analyzer,
        risk_evaluator=mock_risk_evaluator,
        dialogue_manager=mock_dialogue_manager,
        notification_service=mock_notification_service
    )


# ============================================
# 1. Full Workflow Tests
# ============================================
@pytest.mark.asyncio
async def test_process_message_full_workflow(workflow):
    """정상 케이스: 전체 8단계 워크플로우"""
    # Arrange
    user_id = "user123"
    message = "봄에 엄마와 쑥을 뜯으러 갔어요"

    # Act
    response = await workflow.process_message(
        user_id=user_id,
        message=message
    )

    # Assert (process_message returns ProcessingContext)
    assert response is not None
    assert response.response is not None
    assert isinstance(response.response, str)
    assert len(response.response) > 0
    assert "좋은 이야기" in response.response or "여기까지" in response.response

    print(f"✅ Full Workflow Response: {response.response}")


@pytest.mark.asyncio
async def test_process_message_with_metadata(workflow):
    """정상 케이스: 메타데이터 포함"""
    # Arrange
    user_id = "user456"
    message = "오늘 날씨가 좋네요"
    metadata = {
        "response_latency": 2.5,
        "device_type": "mobile"
    }

    # Act
    response = await workflow.process_message(
        user_id=user_id,
        message=message,
        metadata=metadata
    )

    # Assert
    assert response is not None
    print(f"✅ Workflow with Metadata: {response}")


@pytest.mark.asyncio
async def test_process_message_with_image(workflow):
    """정상 케이스: 이미지 메시지"""
    # Arrange
    user_id = "user789"
    message = "오늘 점심 메뉴예요"
    image_url = "https://example.com/image.jpg"

    # Act
    response = await workflow.process_message(
        user_id=user_id,
        message=message,
        message_type="image",
        image_url=image_url
    )

    # Assert
    assert response is not None
    print(f"✅ Workflow with Image: {response}")


# ============================================
# 2. Step-by-Step Tests
# ============================================
@pytest.mark.asyncio
async def test_step_retrieve_memory(workflow):
    """Step 2: 메모리 검색"""
    # Arrange
    ctx = ProcessingContext(
        user_id="user123",
        message="봄에 쑥을 뜯었어요"
    )

    # Act
    ctx_updated = await workflow._step_retrieve_memory(ctx)

    # Assert
    assert ctx_updated.memory is not None
    assert "session" in ctx_updated.memory
    assert "episodic" in ctx_updated.memory
    assert "biographical" in ctx_updated.memory
    assert "analytical" in ctx_updated.memory

    print(f"✅ Memory Retrieved: {len(ctx_updated.memory['episodic'])} episodic")


@pytest.mark.asyncio
async def test_step_analyze_response(workflow):
    """Step 3: 응답 분석"""
    # Arrange
    ctx = ProcessingContext(
        user_id="user123",
        message="봄에 쑥을 뜯었어요"
    )
    ctx.memory = {}

    # Act
    ctx_updated = await workflow._step_analyze_response(ctx)

    # Assert
    assert ctx_updated.analysis is not None
    assert ctx_updated.mcdi_score is not None
    assert 0 <= ctx_updated.mcdi_score <= 100

    print(f"✅ Analysis Completed: MCDI {ctx_updated.mcdi_score}")


@pytest.mark.asyncio
async def test_step_evaluate_risk(workflow):
    """Step 4: 위험도 평가"""
    # Arrange
    ctx = ProcessingContext(
        user_id="user123",
        message="봄에 쑥을 뜯었어요"
    )
    ctx.mcdi_score = 77.6
    ctx.analysis = {"scores": {}}

    # Act
    ctx_updated = await workflow._step_evaluate_risk(ctx)

    # Assert
    assert ctx_updated.risk_level in ["GREEN", "YELLOW", "ORANGE", "RED"]
    assert ctx_updated.alert_needed in [True, False]
    assert ctx_updated.should_check_confounds in [True, False]

    print(f"✅ Risk Evaluated: {ctx_updated.risk_level}")


@pytest.mark.asyncio
async def test_step_plan_next_interaction(workflow):
    """Step 7: 다음 상호작용 계획"""
    # Arrange
    ctx = ProcessingContext(
        user_id="user123",
        message="봄에 쑥을 뜯었어요"
    )
    ctx.analysis = {"scores": {"ER": 65.0}}
    ctx.risk_level = "YELLOW"

    # Act
    ctx_updated = await workflow._step_plan_next_interaction(ctx)

    # Assert
    assert ctx_updated.next_category is not None
    assert ctx_updated.next_difficulty is not None

    print(f"✅ Next Interaction: {ctx_updated.next_category}/{ctx_updated.next_difficulty}")


@pytest.mark.asyncio
async def test_step_generate_and_store(workflow):
    """Step 8: 응답 생성 및 메모리 저장"""
    # Arrange
    ctx = ProcessingContext(
        user_id="user123",
        message="봄에 쑥을 뜯었어요"
    )
    ctx.next_category = "episodic_recall"
    ctx.next_difficulty = "medium"
    ctx.analysis = {}
    ctx.confound_question_scheduled = None

    # Act
    ctx_updated = await workflow._step_generate_and_store(ctx)

    # Assert
    assert ctx_updated.response is not None
    assert len(ctx_updated.response) > 0

    print(f"✅ Response Generated: {ctx_updated.response[:50]}...")


# ============================================
# 3. Conditional Branch Tests
# ============================================
@pytest.mark.asyncio
async def test_alert_triggered_for_orange_risk(
    mock_memory_manager,
    mock_analyzer,
    mock_dialogue_manager,
    mock_notification_service
):
    """조건부 분기: ORANGE 레벨 알림 전송"""
    # Arrange - RiskEvaluator를 ORANGE 레벨로 설정
    mock_risk_evaluator = MagicMock(spec=RiskEvaluator)

    async def mock_evaluate(user_id, current_score, analysis):
        return RiskEvaluation(
            risk_level="ORANGE",
            confidence=0.85,
            current_score=55.0,
            baseline_mean=80.0,
            baseline_std=5.0,
            z_score=-5.0,
            slope=-3.5,
            trend_direction="decreasing",
            primary_reason="중등도 저하",
            contributing_factors=["급격한 하락"],
            alert_needed=True,
            check_confounds=True,
            recommendation="전문가 상담",
            data_points_used=15,
            evaluation_timestamp=datetime.now()
        )

    mock_risk_evaluator.evaluate = mock_evaluate

    workflow = SessionWorkflow(
        memory_manager=mock_memory_manager,
        analyzer=mock_analyzer,
        risk_evaluator=mock_risk_evaluator,
        dialogue_manager=mock_dialogue_manager,
        notification_service=mock_notification_service
    )

    # Act
    response = await workflow.process_message(
        user_id="user123",
        message="뭐더라... 그게..."
    )

    # Assert
    assert response is not None
    # 알림 서비스가 호출되었는지 확인
    mock_notification_service.send_guardian_alert.assert_called_once()

    print(f"✅ Alert Triggered for ORANGE: {response}")


@pytest.mark.asyncio
async def test_confound_check_triggered(
    mock_memory_manager,
    mock_analyzer,
    mock_dialogue_manager,
    mock_notification_service
):
    """조건부 분기: 교란 변수 체크 트리거"""
    # Arrange - RiskEvaluator를 check_confounds=True로 설정
    mock_risk_evaluator = MagicMock(spec=RiskEvaluator)

    async def mock_evaluate(user_id, current_score, analysis):
        return RiskEvaluation(
            risk_level="YELLOW",
            confidence=0.85,
            current_score=70.0,
            baseline_mean=80.0,
            baseline_std=5.0,
            z_score=-2.0,
            slope=-2.5,
            trend_direction="decreasing",
            primary_reason="점수 하락",
            contributing_factors=["최근 저하"],
            alert_needed=False,
            check_confounds=True,  # 교란 변수 체크 필요
            recommendation="교란 변수 확인",
            data_points_used=15,
            evaluation_timestamp=datetime.now()
        )

    mock_risk_evaluator.evaluate = mock_evaluate

    workflow = SessionWorkflow(
        memory_manager=mock_memory_manager,
        analyzer=mock_analyzer,
        risk_evaluator=mock_risk_evaluator,
        dialogue_manager=mock_dialogue_manager,
        notification_service=mock_notification_service
    )

    # Act
    response = await workflow.process_message(
        user_id="user123",
        message="오늘은 좀 피곤해요"
    )

    # Assert
    assert response is not None
    # 교란 변수 질문이 호출되었는지 확인
    mock_dialogue_manager.generate_confound_question.assert_called_once()

    print(f"✅ Confound Check Triggered: {response}")


# ============================================
# 4. Error Handling Tests
# ============================================
@pytest.mark.asyncio
async def test_workflow_with_memory_retrieval_failure(workflow):
    """에러 케이스: 메모리 검색 실패"""
    # Arrange - MemoryManager를 실패하도록 설정
    workflow.memory_manager.retrieve_all = AsyncMock(
        side_effect=Exception("Memory retrieval failed")
    )

    # Act
    response = await workflow.process_message(
        user_id="user123",
        message="안녕하세요"
    )

    # Assert - 워크플로우는 계속 진행되어야 함 (ProcessingContext 반환)
    assert response is not None
    assert response.response is not None
    assert len(response.response) > 0

    print(f"✅ Workflow continues despite memory failure: {response.response}")


@pytest.mark.asyncio
async def test_workflow_with_analysis_failure(workflow):
    """에러 케이스: 분석 실패"""
    # Arrange - Analyzer를 실패하도록 설정
    workflow.analyzer.analyze = AsyncMock(
        side_effect=Exception("Analysis failed")
    )

    # Act
    response = await workflow.process_message(
        user_id="user123",
        message="안녕하세요"
    )

    # Assert - Fallback 응답이 반환되어야 함 (ProcessingContext 반환)
    assert response is not None
    assert response.response is not None
    assert "좋은 이야기" in response.response or "여기까지" in response.response

    print(f"✅ Fallback Response on Analysis Failure: {response.response}")


@pytest.mark.asyncio
async def test_workflow_with_response_generation_failure(workflow):
    """에러 케이스: 응답 생성 실패"""
    # Arrange - DialogueManager의 generate_response를 실패하도록 설정
    workflow.dialogue_manager.generate_response = AsyncMock(
        side_effect=Exception("Response generation failed")
    )

    # Act
    response = await workflow.process_message(
        user_id="user123",
        message="안녕하세요"
    )

    # Assert - 기본 응답이 설정되어야 함 (ProcessingContext 반환)
    assert response is not None
    assert response.response is not None
    assert "생각을 정리" in response.response or "정원" in response.response

    print(f"✅ Default Response on Generation Failure: {response.response}")


# ============================================
# 5. Performance Tests
# ============================================
@pytest.mark.asyncio
async def test_workflow_performance(workflow):
    """성능 테스트: 전체 처리 시간"""
    # Arrange
    user_id = "perf_test_user"
    message = "성능 테스트 메시지"

    import time
    start = time.time()

    # Act
    response = await workflow.process_message(
        user_id=user_id,
        message=message
    )

    elapsed = (time.time() - start) * 1000

    # Assert
    assert response is not None
    assert elapsed < 5000  # 5초 이내

    print(f"✅ Workflow Performance: {elapsed:.2f}ms")


# ============================================
# 6. Integration Tests
# ============================================
@pytest.mark.asyncio
async def test_full_conversation_flow(workflow):
    """통합 테스트: 연속 대화 플로우"""
    user_id = "integration_test_user"

    # Message 1
    response1 = await workflow.process_message(
        user_id=user_id,
        message="안녕하세요"
    )
    assert response1 is not None

    # Message 2
    response2 = await workflow.process_message(
        user_id=user_id,
        message="봄에 엄마와 쑥을 뜯으러 갔어요"
    )
    assert response2 is not None

    # Message 3
    response3 = await workflow.process_message(
        user_id=user_id,
        message="쑥떡을 만들어 먹었어요"
    )
    assert response3 is not None

    print(f"✅ Full Conversation Flow:")
    print(f"  1: {response1.response[:30]}...")
    print(f"  2: {response2.response[:30]}...")
    print(f"  3: {response3.response[:30]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
