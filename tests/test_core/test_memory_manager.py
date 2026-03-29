"""
Memory Manager 테스트

4계층 메모리 시스템의 통합 관리를 테스트합니다.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from core.memory.memory_manager import MemoryManager
from core.memory.memory_extractor import MemoryExtractor


# ============================================
# Fixtures
# ============================================
@pytest.fixture
def mock_memory_extractor():
    """Mock MemoryExtractor"""
    extractor = MagicMock(spec=MemoryExtractor)

    # Mock extract_from_message
    async def mock_extract(user_message, assistant_message, context):
        from core.memory.memory_extractor import (
            MemoryExtractionResult,
            ExtractedMemory,
            ExtractedFact,
            MemoryType,
            EntityCategory,
            FactType
        )

        return MemoryExtractionResult(
            episodic_memories=[
                ExtractedMemory(
                    memory_type=MemoryType.EPISODIC,
                    content=user_message,
                    category=EntityCategory.EVENT,
                    confidence=0.9,
                    importance=0.8,
                    timestamp=datetime.now().isoformat(),
                    metadata={}
                )
            ],
            biographical_facts=[
                ExtractedFact(
                    entity="test_entity",
                    value="test_value",
                    category=EntityCategory.PERSON,
                    fact_type=FactType.IMMUTABLE,
                    confidence=0.9,
                    context=user_message,
                    timestamp=datetime.now().isoformat()
                )
            ],
            summary="Test extraction"
        )

    extractor.extract_from_message = mock_extract
    return extractor


@pytest.fixture
def memory_manager(mock_memory_extractor):
    """MemoryManager 인스턴스"""
    return MemoryManager(memory_extractor=mock_memory_extractor)


@pytest.fixture
def sample_analysis():
    """샘플 분석 결과"""
    return {
        "mcdi_score": 82.5,
        "scores": {
            "LR": 80.0,
            "SD": 85.0,
            "NC": 78.0,
            "TO": 84.0,
            "ER": 81.0,
            "RT": 87.0
        },
        "risk_level": "GREEN",
        "emotion": "neutral"
    }


# ============================================
# 1. Initialization Tests
# ============================================
def test_memory_manager_initialization():
    """정상 케이스: MemoryManager 초기화"""
    # Act
    manager = MemoryManager()

    # Assert
    assert manager is not None
    assert manager.memory_extractor is not None
    print("✅ MemoryManager initialized successfully")


def test_memory_manager_with_custom_extractor(mock_memory_extractor):
    """정상 케이스: 커스텀 extractor로 초기화"""
    # Act
    manager = MemoryManager(memory_extractor=mock_memory_extractor)

    # Assert
    assert manager.memory_extractor == mock_memory_extractor
    print("✅ MemoryManager with custom extractor initialized")


# ============================================
# 2. Store All Tests
# ============================================
@pytest.mark.asyncio
async def test_store_all_basic(memory_manager, sample_analysis):
    """정상 케이스: 4계층 통합 저장"""
    # Arrange
    user_id = "test_user_123"
    message = "봄에 엄마와 쑥을 뜯으러 갔어요"
    response = "좋은 추억이네요!"

    # Act
    result = await memory_manager.store_all(
        user_id=user_id,
        message=message,
        response=response,
        analysis=sample_analysis
    )

    # Assert
    assert result is not None
    assert "session_stored" in result
    assert "episodic_stored" in result
    assert "biographical_stored" in result
    assert "analytical_stored" in result

    print(f"✅ Store All - Session: {result['session_stored']}, "
          f"Episodic: {result['episodic_stored']}, "
          f"Biographical: {result['biographical_stored']}, "
          f"Analytical: {result['analytical_stored']}")


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis integration test - run individually for testing")
async def test_store_all_without_analysis(memory_manager):
    """정상 케이스: 분석 결과 없이 저장"""
    # Arrange
    user_id = "test_user_456"
    message = "오늘 날씨가 좋네요"
    response = "네, 맑은 날씨예요"

    # Act
    result = await memory_manager.store_all(
        user_id=user_id,
        message=message,
        response=response,
        analysis=None
    )

    # Assert
    assert result is not None
    assert result["session_stored"] == True
    print("✅ Store All without analysis completed")


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis integration test - run individually for testing")
async def test_store_all_multiple_times(memory_manager, sample_analysis):
    """정상 케이스: 여러 번 저장"""
    # Arrange
    user_id = "test_user_789"
    messages = [
        ("첫 번째 메시지", "첫 번째 응답"),
        ("두 번째 메시지", "두 번째 응답"),
        ("세 번째 메시지", "세 번째 응답")
    ]

    # Act
    results = []
    for message, response in messages:
        result = await memory_manager.store_all(
            user_id=user_id,
            message=message,
            response=response,
            analysis=sample_analysis
        )
        results.append(result)

    # Assert
    assert len(results) == 3
    assert all(r["session_stored"] for r in results)
    print(f"✅ Multiple stores completed: {len(results)} times")


# ============================================
# 3. Retrieve All Tests
# ============================================
@pytest.mark.asyncio
async def test_retrieve_all_basic(memory_manager):
    """정상 케이스: 4계층 통합 검색"""
    # Arrange
    user_id = "test_user_retrieve"

    # Act
    memories = await memory_manager.retrieve_all(user_id=user_id)

    # Assert
    assert memories is not None
    assert "session" in memories
    assert "episodic" in memories
    assert "biographical" in memories
    assert "analytical" in memories
    assert memories["user_id"] == user_id

    print(f"✅ Retrieve All - Retrieved from 4 layers")


@pytest.mark.asyncio
async def test_retrieve_all_with_query(memory_manager):
    """정상 케이스: 쿼리로 검색"""
    # Arrange
    user_id = "test_user_search"
    query = "봄"

    # Act
    memories = await memory_manager.retrieve_all(
        user_id=user_id,
        query=query,
        limit=5
    )

    # Assert
    assert memories is not None
    assert memories["query"] == query
    print(f"✅ Retrieve with query: '{query}'")


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis integration test - run individually for testing")
async def test_retrieve_all_selective_layers(memory_manager):
    """정상 케이스: 특정 계층만 검색"""
    # Arrange
    user_id = "test_user_selective"

    # Act - Session만
    memories = await memory_manager.retrieve_all(
        user_id=user_id,
        include_episodic=False,
        include_biographical=False,
        include_analytical=False
    )

    # Assert
    assert "session" in memories
    assert isinstance(memories.get("episodic", []), list)
    print("✅ Selective layer retrieval (session only)")


# ============================================
# 4. Session Memory Tests
# ============================================
@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis integration test - run individually for testing")
async def test_store_and_retrieve_session(memory_manager):
    """정상 케이스: Session Memory 저장 및 검색"""
    # Arrange
    user_id = "test_session_user"
    message = "안녕하세요"
    response = "반갑습니다"

    # Act - Store
    await memory_manager._store_session_memory(user_id, message, response)

    # Act - Retrieve
    session = await memory_manager._retrieve_session_memory(user_id)

    # Assert
    assert session is not None
    assert session.get("user_id") == user_id
    assert len(session.get("conversation_history", [])) > 0

    last_turn = session["conversation_history"][-1]
    assert last_turn["user"] == message
    assert last_turn["assistant"] == response

    print("✅ Session Memory: Store and Retrieve")


# ============================================
# 5. Search Methods Tests
# ============================================
@pytest.mark.asyncio
async def test_search_memories_by_keyword(memory_manager):
    """정상 케이스: 키워드로 검색"""
    # Arrange
    user_id = "test_keyword_user"
    keyword = "딸"

    # Act
    results = await memory_manager.search_memories_by_keyword(
        user_id=user_id,
        keyword=keyword,
        limit=10
    )

    # Assert
    assert isinstance(results, list)
    print(f"✅ Keyword search: '{keyword}' - {len(results)} results")


@pytest.mark.asyncio
async def test_search_memories_by_time_range(memory_manager):
    """정상 케이스: 시간 범위로 검색"""
    # Arrange
    user_id = "test_time_user"
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()

    # Act
    results = await memory_manager.search_memories_by_time_range(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    # Assert
    assert isinstance(results, list)
    print(f"✅ Time range search: {len(results)} results")


@pytest.mark.asyncio
async def test_search_memories_by_emotion(memory_manager):
    """정상 케이스: 감정으로 검색"""
    # Arrange
    user_id = "test_emotion_user"
    emotion = "joy"

    # Act
    results = await memory_manager.search_memories_by_emotion(
        user_id=user_id,
        emotion=emotion,
        limit=10
    )

    # Assert
    assert isinstance(results, list)
    print(f"✅ Emotion search: '{emotion}' - {len(results)} results")


@pytest.mark.asyncio
async def test_get_recent_memories(memory_manager):
    """정상 케이스: 최근 기억 조회"""
    # Arrange
    user_id = "test_recent_user"
    days = 7

    # Act
    results = await memory_manager.get_recent_memories(
        user_id=user_id,
        days=days,
        limit=20
    )

    # Assert
    assert isinstance(results, list)
    print(f"✅ Recent memories: Last {days} days - {len(results)} results")


# ============================================
# 6. Integration Tests
# ============================================
@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis integration test - run individually for testing")
async def test_full_workflow(memory_manager, sample_analysis):
    """통합 테스트: 저장 → 검색 → 재검색"""
    # Arrange
    user_id = "test_integration_user"
    message = "아버지는 의사셨고 어머니는 선생님이셨어요"
    response = "가족 이야기를 들려주셔서 감사해요"

    # Act 1: Store
    store_result = await memory_manager.store_all(
        user_id=user_id,
        message=message,
        response=response,
        analysis=sample_analysis
    )

    # Act 2: Retrieve All
    memories = await memory_manager.retrieve_all(user_id=user_id)

    # Act 3: Keyword Search
    search_results = await memory_manager.search_memories_by_keyword(
        user_id=user_id,
        keyword="아버지"
    )

    # Assert
    assert store_result["session_stored"] == True
    assert memories is not None
    assert memories["user_id"] == user_id
    assert isinstance(search_results, list)

    print(f"✅ Full Workflow - Store → Retrieve → Search completed")


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis integration test - run individually for testing")
async def test_concurrent_operations(memory_manager, sample_analysis):
    """통합 테스트: 동시 다발적 작업"""
    # Arrange
    users = ["user_1", "user_2", "user_3"]
    message = "테스트 메시지"
    response = "테스트 응답"

    # Act - 병렬 저장
    import asyncio
    tasks = [
        memory_manager.store_all(
            user_id=user_id,
            message=f"{message} for {user_id}",
            response=response,
            analysis=sample_analysis
        )
        for user_id in users
    ]
    results = await asyncio.gather(*tasks)

    # Act - 병렬 검색
    retrieve_tasks = [
        memory_manager.retrieve_all(user_id=user_id)
        for user_id in users
    ]
    memories_list = await asyncio.gather(*retrieve_tasks)

    # Assert
    assert len(results) == len(users)
    assert len(memories_list) == len(users)
    assert all(r["session_stored"] for r in results)

    print(f"✅ Concurrent operations for {len(users)} users")


# ============================================
# 7. Error Handling Tests
# ============================================
@pytest.mark.asyncio
async def test_retrieve_nonexistent_user(memory_manager):
    """엣지 케이스: 존재하지 않는 사용자 검색"""
    # Arrange
    user_id = "nonexistent_user_xyz"

    # Act
    memories = await memory_manager.retrieve_all(user_id=user_id)

    # Assert
    assert memories is not None
    assert memories["user_id"] == user_id
    assert memories["session"] == {}
    assert memories["episodic"] == []

    print("✅ Nonexistent user handled gracefully")


@pytest.mark.asyncio
async def test_store_empty_message(memory_manager):
    """엣지 케이스: 빈 메시지 저장"""
    # Arrange
    user_id = "test_empty_user"
    message = ""
    response = "응답"

    # Act
    result = await memory_manager.store_all(
        user_id=user_id,
        message=message,
        response=response
    )

    # Assert
    assert result is not None
    # 빈 메시지도 저장은 되어야 함
    print("✅ Empty message handled")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
