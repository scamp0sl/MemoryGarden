"""
메모리 관리 테스트

4계층 메모리 시스템 테스트:
- Layer 1: Session Memory (Redis)
- Layer 2: Episodic Memory (Qdrant)
- Layer 3: Biographical Memory (Qdrant + PostgreSQL)
- Layer 4: Analytical Memory (TimescaleDB)

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# Standard Library Imports
# ============================================
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
from datetime import datetime, timedelta
import json

# ============================================
# Third-Party Imports
# ============================================
import pytest
import pytest_asyncio

# ============================================
# Local Imports
# ============================================
from core.memory.session_memory import SessionMemory
from core.memory.memory_manager import MemoryManager
from core.memory.memory_extractor import (
    MemoryExtractor,
    MemoryExtractionResult,
    ExtractedMemory,
    ExtractedFact,
    MemoryType,
)
from database.redis_client import redis_client
from utils.exceptions import WorkflowError, AnalysisError


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_context() -> Dict[str, Any]:
    """샘플 세션 컨텍스트"""
    return {
        "user_id": "test_user",
        "last_message": "오늘 점심 먹었어요",
        "conversation_count": 5,
        "last_emotion": "neutral",
        "current_category": "daily_episodic",
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def sample_extraction_result():
    """샘플 기억 추출 결과"""
    from core.memory.memory_extractor import EntityCategory, FactType

    return MemoryExtractionResult(
        episodic_memories=[
            ExtractedMemory(
                content="오늘 점심에 김치찌개 먹음",
                memory_type=MemoryType.EPISODIC,
                category=EntityCategory.FOOD,
                confidence=0.9,
                importance=0.8,
                timestamp=datetime.now().isoformat(),
                metadata={"tags": ["food", "meal"]}
            )
        ],
        biographical_facts=[
            ExtractedFact(
                entity="daughter_name",
                value="수진",
                category=EntityCategory.PERSON,
                fact_type=FactType.IMMUTABLE,
                confidence=0.95,
                context="가족 관계",
                timestamp=datetime.now().isoformat()
            )
        ],
        emotional_memories=[],
        key_entities=[
            {"entity": "김치찌개", "category": "food"},
            {"entity": "딸", "category": "person"}
        ],
        summary="가족과 식사에 대한 대화"
    )


@pytest.fixture
def mock_memory_extractor(sample_extraction_result):
    """Mock MemoryExtractor"""
    extractor = AsyncMock(spec=MemoryExtractor)
    extractor.extract.return_value = sample_extraction_result
    extractor.extract_from_message.return_value = sample_extraction_result
    return extractor


# ============================================
# SessionMemory Tests
# ============================================

@pytest.mark.asyncio
async def test_session_memory_save_context(mock_redis, sample_context):
    """정상 케이스: 세션 컨텍스트 저장"""
    # Arrange
    user_id = "test_user"

    with patch('database.redis_client.redis_client.get_client', return_value=mock_redis):
        session_memory = SessionMemory(user_id=user_id, ttl=1800)

        # Act
        await session_memory.save_context(sample_context)

        # Assert
        # Redis set 호출 확인
        saved_key = f"session:{user_id}"
        saved_value = await mock_redis.get(saved_key)
        assert saved_value is not None

        # JSON 파싱 확인
        saved_data = json.loads(saved_value)
        assert saved_data["user_id"] == "test_user"
        assert saved_data["conversation_count"] == 5


@pytest.mark.asyncio
async def test_session_memory_get_context(mock_redis, sample_context):
    """정상 케이스: 세션 컨텍스트 조회"""
    # Arrange
    user_id = "test_user"

    with patch('database.redis_client.redis_client.get_client', return_value=mock_redis):
        session_memory = SessionMemory(user_id=user_id, ttl=1800)

        # 먼저 저장
        await session_memory.save_context(sample_context)

        # Act
        retrieved_context = await session_memory.get_context()

        # Assert
        assert retrieved_context["user_id"] == "test_user"
        assert retrieved_context["conversation_count"] == 5
        assert retrieved_context["last_emotion"] == "neutral"


@pytest.mark.asyncio
async def test_session_memory_get_context_empty(mock_redis):
    """엣지 케이스: 저장된 컨텍스트가 없을 때"""
    # Arrange
    user_id = "nonexistent_user"

    with patch('database.redis_client.redis_client.get_client', return_value=mock_redis):
        session_memory = SessionMemory(user_id=user_id, ttl=1800)

        # Act
        retrieved_context = await session_memory.get_context()

        # Assert
        assert retrieved_context == {}  # 빈 딕셔너리 반환


@pytest.mark.asyncio
async def test_session_memory_update_context(mock_redis, sample_context):
    """정상 케이스: 세션 컨텍스트 부분 업데이트"""
    # Arrange
    user_id = "test_user"

    with patch('database.redis_client.redis_client.get_client', return_value=mock_redis):
        session_memory = SessionMemory(user_id=user_id, ttl=1800)

        # 먼저 저장
        await session_memory.save_context(sample_context)

        # Act
        updates = {
            "conversation_count": 6,
            "last_message": "새로운 메시지",
            "new_field": "추가된 필드"
        }
        await session_memory.update_context(updates)

        # Assert
        updated_context = await session_memory.get_context()
        assert updated_context["conversation_count"] == 6
        assert updated_context["last_message"] == "새로운 메시지"
        assert updated_context["new_field"] == "추가된 필드"
        assert updated_context["user_id"] == "test_user"  # 기존 필드 유지


@pytest.mark.asyncio
async def test_session_memory_clear(mock_redis, sample_context):
    """정상 케이스: 세션 초기화"""
    # Arrange
    user_id = "test_user"

    with patch('database.redis_client.redis_client.get_client', return_value=mock_redis):
        session_memory = SessionMemory(user_id=user_id, ttl=1800)

        # 먼저 저장
        await session_memory.save_context(sample_context)

        # Act
        await session_memory.clear()

        # Assert
        retrieved_context = await session_memory.get_context()
        assert retrieved_context == {}  # 빈 딕셔너리 반환


# ============================================
# MemoryManager Tests
# ============================================

@pytest.mark.asyncio
async def test_memory_manager_store_all(mock_memory_extractor, mock_redis):
    """정상 케이스: 4계층 기억 저장"""
    # Arrange
    manager = MemoryManager(memory_extractor=mock_memory_extractor)

    user_id = "test_user"
    message = "오늘 딸 수진이랑 김치찌개 먹었어요"
    response = "맛있게 드셨나요?"
    analysis = {"emotion": "joy", "mcdi_score": 78.5}

    # Mock internal storage methods
    with patch.object(manager, '_store_session_memory', new_callable=AsyncMock) as mock_session, \
         patch.object(manager, '_store_episodic_memories', new_callable=AsyncMock) as mock_episodic, \
         patch.object(manager, '_store_biographical_facts', new_callable=AsyncMock) as mock_bio, \
         patch.object(manager, '_store_analytical_data', new_callable=AsyncMock) as mock_analytical:

        mock_session.return_value = True
        mock_episodic.return_value = 2
        mock_bio.return_value = 1
        mock_analytical.return_value = True

        # Act
        result = await manager.store_all(
            user_id=user_id,
            message=message,
            response=response,
            analysis=analysis
        )

        # Assert
        # MemoryExtractor 호출 확인
        mock_memory_extractor.extract_from_message.assert_called_once()

        # 호출 인자 확인
        call_args = mock_memory_extractor.extract_from_message.call_args
        assert call_args.kwargs['user_message'] == message
        assert call_args.kwargs['assistant_message'] == response

        # 4계층 저장 메서드 호출 확인
        mock_session.assert_called_once()
        mock_episodic.assert_called_once()
        mock_bio.assert_called_once()
        mock_analytical.assert_called_once()

        # 결과 확인
        assert result["session_stored"] is True
        assert result["episodic_stored"] == 2
        assert result["biographical_stored"] == 1
        assert result["analytical_stored"] is True


@pytest.mark.asyncio
async def test_memory_manager_store_all_with_partial_failure(mock_memory_extractor):
    """에러 케이스: 일부 계층 저장 실패"""
    # Arrange
    manager = MemoryManager(memory_extractor=mock_memory_extractor)

    user_id = "test_user"
    message = "테스트 메시지"
    response = "테스트 응답"
    analysis = {}

    # Mock internal storage methods - 일부 실패
    with patch.object(manager, '_store_session_memory', new_callable=AsyncMock) as mock_session, \
         patch.object(manager, '_store_episodic_memories', new_callable=AsyncMock) as mock_episodic, \
         patch.object(manager, '_store_biographical_facts', new_callable=AsyncMock) as mock_bio, \
         patch.object(manager, '_store_analytical_data', new_callable=AsyncMock) as mock_analytical:

        mock_session.return_value = True
        mock_episodic.side_effect = Exception("Qdrant connection failed")
        mock_bio.return_value = 0
        mock_analytical.return_value = True

        # Act
        result = await manager.store_all(
            user_id=user_id,
            message=message,
            response=response,
            analysis=analysis
        )

        # Assert
        # 성공한 계층은 정상 저장
        assert result["session_stored"] is True
        assert result["analytical_stored"] is True

        # 실패한 계층은 0 반환 (에러 발생 시 기본값)
        assert result["episodic_stored"] == 0


@pytest.mark.asyncio
async def test_memory_manager_retrieve_all(mock_memory_extractor):
    """정상 케이스: 4계층 기억 검색"""
    # Arrange
    manager = MemoryManager(memory_extractor=mock_memory_extractor)

    user_id = "test_user"
    query = "점심"

    # Mock internal retrieval methods
    with patch.object(manager, '_retrieve_session_memory', new_callable=AsyncMock) as mock_session, \
         patch.object(manager, '_retrieve_episodic_memories', new_callable=AsyncMock) as mock_episodic, \
         patch.object(manager, '_retrieve_biographical_facts', new_callable=AsyncMock) as mock_bio, \
         patch.object(manager, '_retrieve_analytical_data', new_callable=AsyncMock) as mock_analytical:

        mock_session.return_value = {"last_message": "오늘 점심 먹었어요"}
        mock_episodic.return_value = [
            {"content": "김치찌개 먹음", "timestamp": "2025-02-10T12:00:00"}
        ]
        mock_bio.return_value = {"daughter_name": "수진"}
        mock_analytical.return_value = {"recent_mcdi": [78.5, 79.0, 77.5]}

        # Act
        result = await manager.retrieve_all(user_id=user_id, query=query)

        # Assert
        # 4계층 검색 메서드 호출 확인
        mock_session.assert_called_once()
        mock_episodic.assert_called_once()
        mock_bio.assert_called_once()
        mock_analytical.assert_called_once()

        # 결과 확인
        assert "session" in result
        assert "episodic" in result
        assert "biographical" in result
        assert "analytical" in result

        assert result["session"]["last_message"] == "오늘 점심 먹었어요"
        assert len(result["episodic"]) == 1
        assert result["biographical"]["daughter_name"] == "수진"


@pytest.mark.asyncio
async def test_memory_manager_retrieve_all_with_empty_query():
    """엣지 케이스: 빈 쿼리로 검색"""
    # Arrange
    manager = MemoryManager()

    user_id = "test_user"
    query = ""

    # Mock internal retrieval methods
    with patch.object(manager, '_retrieve_session_memory', new_callable=AsyncMock) as mock_session, \
         patch.object(manager, '_retrieve_episodic_memories', new_callable=AsyncMock) as mock_episodic, \
         patch.object(manager, '_retrieve_biographical_facts', new_callable=AsyncMock) as mock_bio, \
         patch.object(manager, '_retrieve_analytical_data', new_callable=AsyncMock) as mock_analytical:

        mock_session.return_value = {}
        mock_episodic.return_value = []
        mock_bio.return_value = {}
        mock_analytical.return_value = {}

        # Act
        result = await manager.retrieve_all(user_id=user_id, query=query)

        # Assert
        # 빈 쿼리라도 모든 계층 조회
        mock_session.assert_called_once()
        mock_episodic.assert_called_once()
        mock_bio.assert_called_once()
        mock_analytical.assert_called_once()

        # 빈 결과 확인
        assert result["session"] == {}
        assert result["episodic"] == []
        assert result["biographical"] == {}
        assert result["analytical"] == {}


# ============================================
# MemoryExtractor Tests
# ============================================

@pytest.mark.asyncio
async def test_memory_extractor_extract_from_message(mock_llm_service):
    """정상 케이스: 대화에서 기억 추출"""
    # Arrange
    from services.llm_service import LLMService
    from core.memory.memory_extractor import EntityCategory, FactType

    mock_llm = AsyncMock(spec=LLMService)
    mock_llm.call_json.return_value = {
        "episodic_memories": [
            {
                "content": "김치찌개 먹음",
                "memory_type": "episodic",
                "category": "food",
                "confidence": 0.9,
                "importance": 0.7,
                "metadata": {"tags": ["food"]}
            }
        ],
        "biographical_facts": [
            {
                "entity": "lunch_menu",
                "value": "김치찌개",
                "category": "food",
                "fact_type": "temporary",
                "confidence": 0.9,
                "context": "오늘 점심"
            }
        ],
        "emotional_memories": [],
        "key_entities": [{"entity": "김치찌개", "category": "food"}],
        "summary": "점심 식사에 대한 대화"
    }

    extractor = MemoryExtractor(llm_service=mock_llm)

    conversation_history = [
        {"role": "user", "content": "오늘 점심에 김치찌개 먹었어요"},
        {"role": "assistant", "content": "맛있게 드셨나요?"}
    ]

    # Act
    result = await extractor.extract(
        conversation_history=conversation_history
    )

    # Assert
    assert isinstance(result, MemoryExtractionResult)
    # The real extractor processes this as biographical facts (temporary facts)
    assert len(result.biographical_facts) >= 1 or len(result.episodic_memories) >= 1
    assert result.summary != ""

    # LLM 호출 확인
    mock_llm.call_json.assert_called_once()


@pytest.mark.asyncio
async def test_memory_extractor_extract_empty_message(mock_llm_service):
    """엣지 케이스: 빈 대화"""
    # Arrange
    mock_llm = AsyncMock()
    mock_llm.call_json.return_value = {
        "episodic_memories": [],
        "biographical_facts": [],
        "emotional_memories": [],
        "key_entities": [],
        "summary": ""
    }

    extractor = MemoryExtractor(llm_service=mock_llm)

    conversation_history = []

    # Act
    result = await extractor.extract(
        conversation_history=conversation_history
    )

    # Assert
    # 빈 대화는 빈 결과 반환
    assert len(result.episodic_memories) == 0
    assert len(result.biographical_facts) == 0
    assert len(result.emotional_memories) == 0


@pytest.mark.asyncio
async def test_memory_extractor_with_llm_failure(mock_llm_service):
    """에러 케이스: LLM 호출 실패"""
    # Arrange
    mock_llm = AsyncMock()
    mock_llm.call_json.side_effect = Exception("API Error")

    extractor = MemoryExtractor(llm_service=mock_llm)

    conversation_history = [
        {"role": "user", "content": "테스트 메시지"},
        {"role": "assistant", "content": "테스트 응답"}
    ]

    # Act & Assert
    with pytest.raises(AnalysisError, match="Failed to extract memories"):
        await extractor.extract(conversation_history=conversation_history)


# ============================================
# Integration Tests
# ============================================

@pytest.mark.asyncio
async def test_full_memory_workflow(mock_redis, mock_memory_extractor):
    """통합 테스트: 전체 메모리 워크플로우"""
    # Arrange
    manager = MemoryManager(memory_extractor=mock_memory_extractor)

    user_id = "test_user"
    message = "오늘 딸 수진이랑 김치찌개 먹었어요"
    response = "가족과 함께 드셔서 좋으셨겠어요"
    analysis = {"emotion": "joy", "mcdi_score": 80.0}

    # Mock all storage layers
    with patch.object(manager, '_store_session_memory', new_callable=AsyncMock) as mock_session, \
         patch.object(manager, '_store_episodic_memories', new_callable=AsyncMock) as mock_episodic, \
         patch.object(manager, '_store_biographical_facts', new_callable=AsyncMock) as mock_bio, \
         patch.object(manager, '_store_analytical_data', new_callable=AsyncMock) as mock_analytical, \
         patch.object(manager, '_retrieve_session_memory', new_callable=AsyncMock) as mock_retrieve_session, \
         patch.object(manager, '_retrieve_episodic_memories', new_callable=AsyncMock) as mock_retrieve_episodic, \
         patch.object(manager, '_retrieve_biographical_facts', new_callable=AsyncMock) as mock_retrieve_bio, \
         patch.object(manager, '_retrieve_analytical_data', new_callable=AsyncMock) as mock_retrieve_analytical:

        # Setup storage mocks
        mock_session.return_value = True
        mock_episodic.return_value = 2
        mock_bio.return_value = 1
        mock_analytical.return_value = True

        # Setup retrieval mocks
        mock_retrieve_session.return_value = {"last_message": message}
        mock_retrieve_episodic.return_value = [
            {"content": "김치찌개 먹음", "tags": ["food", "family"]}
        ]
        mock_retrieve_bio.return_value = {"daughter_name": "수진"}
        mock_retrieve_analytical.return_value = {"recent_mcdi": [80.0]}

        # Act 1: 저장
        store_result = await manager.store_all(
            user_id=user_id,
            message=message,
            response=response,
            analysis=analysis
        )

        # Act 2: 검색
        retrieve_result = await manager.retrieve_all(
            user_id=user_id,
            query="김치찌개"
        )

        # Assert
        # 저장 성공
        assert store_result["session_stored"] is True
        assert store_result["episodic_stored"] == 2
        assert store_result["biographical_stored"] == 1

        # 검색 성공
        assert retrieve_result["session"]["last_message"] == message
        assert len(retrieve_result["episodic"]) == 1
        assert retrieve_result["biographical"]["daughter_name"] == "수진"
        assert retrieve_result["analytical"]["recent_mcdi"] == [80.0]
