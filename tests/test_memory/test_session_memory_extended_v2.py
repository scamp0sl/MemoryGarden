"""
SessionMemory 확장 기능 테스트 (Mock 기반)

Task 5용 추가 메서드 검증 - Redis Mock 사용
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json

from core.memory.session_memory import SessionMemory


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('core.memory.session_memory.redis_client') as mock:
        # get_client() returns AsyncMock
        client = AsyncMock()
        mock.get_client = AsyncMock(return_value=client)

        # Redis 명령 Mock 설정
        client.rpush = AsyncMock(return_value=1)
        client.expire = AsyncMock(return_value=True)
        client.lrange = AsyncMock(return_value=[])
        client.hgetall = AsyncMock(return_value={})
        client.exists = AsyncMock(return_value=0)
        client.hset = AsyncMock(return_value=1)
        client.llen = AsyncMock(return_value=0)

        yield client


@pytest.fixture
def session_id():
    """테스트용 세션 ID"""
    return "test_session_123"


@pytest.fixture
def session_memory():
    """SessionMemory 인스턴스"""
    return SessionMemory(user_id=123)


# ============================================
# Test 1: add_turn() - 대화 턴 추가
# ============================================

@pytest.mark.asyncio
async def test_add_turn(session_memory, session_id, mock_redis):
    """정상 케이스: 대화 턴 추가"""
    # Act
    await session_memory.add_turn(
        session_id=session_id,
        role="user",
        content="안녕하세요"
    )

    # Assert
    # rpush가 호출되었는지 확인
    assert mock_redis.rpush.called
    call_args = mock_redis.rpush.call_args

    # 첫 번째 인자는 키
    assert f"session:{session_id}:turns" in call_args[0]

    # 두 번째 인자는 JSON 데이터
    turn_data = json.loads(call_args[0][1])
    assert turn_data["role"] == "user"
    assert turn_data["content"] == "안녕하세요"
    assert "timestamp" in turn_data

    print("✅ Turn added successfully")


@pytest.mark.asyncio
async def test_add_turn_with_metadata(session_memory, session_id, mock_redis):
    """메타데이터 포함 턴 추가"""
    # Act
    await session_memory.add_turn(
        session_id=session_id,
        role="user",
        content="이미지 분석",
        metadata={"image_id": "img_123"}
    )

    # Assert
    call_args = mock_redis.rpush.call_args
    turn_data = json.loads(call_args[0][1])

    assert turn_data["role"] == "user"
    assert turn_data["image_id"] == "img_123"

    print("✅ Turn with metadata added")


# ============================================
# Test 2: get_all_turns() - 대화 턴 조회
# ============================================

@pytest.mark.asyncio
async def test_get_all_turns(session_memory, session_id, mock_redis):
    """정상 케이스: 모든 턴 조회"""
    # Arrange - Mock 데이터 설정
    turn1 = json.dumps({"role": "user", "content": "Message 1", "timestamp": "2026-01-01T00:00:00"})
    turn2 = json.dumps({"role": "assistant", "content": "Message 2", "timestamp": "2026-01-01T00:01:00"})
    turn3 = json.dumps({"role": "user", "content": "Message 3", "timestamp": "2026-01-01T00:02:00"})

    mock_redis.lrange.return_value = [turn1.encode(), turn2.encode(), turn3.encode()]

    # Act
    turns = await session_memory.get_all_turns(session_id, limit=100)

    # Assert
    assert len(turns) == 3
    # 최신순으로 정렬되어야 함
    assert turns[0]["content"] == "Message 3"
    assert turns[-1]["content"] == "Message 1"

    print(f"✅ Retrieved {len(turns)} turns (latest first)")


@pytest.mark.asyncio
async def test_get_all_turns_empty(session_memory, session_id, mock_redis):
    """엣지 케이스: 빈 세션"""
    # Arrange
    mock_redis.lrange.return_value = []

    # Act
    turns = await session_memory.get_all_turns(session_id, limit=10)

    # Assert
    assert turns == []

    print("✅ Empty session returns empty list")


# ============================================
# Test 3: get_metadata() - 메타데이터 조회
# ============================================

@pytest.mark.asyncio
async def test_get_metadata(session_memory, session_id, mock_redis):
    """정상 케이스: 메타데이터 조회"""
    # Arrange
    mock_redis.hgetall.return_value = {
        b"created_at": b"2026-01-01T00:00:00",
        b"updated_at": b"2026-01-01T00:05:00",
        b"turn_count": b"5"
    }

    # Act
    metadata = await session_memory.get_metadata(session_id)

    # Assert
    assert metadata is not None
    assert metadata["created_at"] == "2026-01-01T00:00:00"
    assert metadata["updated_at"] == "2026-01-01T00:05:00"
    assert metadata["turn_count"] == "5"

    print(f"✅ Metadata retrieved: {metadata}")


@pytest.mark.asyncio
async def test_get_metadata_nonexistent(session_memory, session_id, mock_redis):
    """엣지 케이스: 존재하지 않는 세션"""
    # Arrange
    mock_redis.hgetall.return_value = {}

    # Act
    metadata = await session_memory.get_metadata(session_id)

    # Assert
    assert metadata is None

    print("✅ Nonexistent session returns None")


# ============================================
# Test 4: exists() - 세션 존재 확인
# ============================================

@pytest.mark.asyncio
async def test_exists_true(session_memory, session_id, mock_redis):
    """정상 케이스: 세션 존재"""
    # Arrange
    mock_redis.exists.return_value = 1

    # Act
    exists = await session_memory.exists(session_id)

    # Assert
    assert exists is True

    print("✅ Session exists: True")


@pytest.mark.asyncio
async def test_exists_false(session_memory, session_id, mock_redis):
    """세션 없음"""
    # Arrange
    mock_redis.exists.return_value = 0

    # Act
    exists = await session_memory.exists(session_id)

    # Assert
    assert exists is False

    print("✅ Session exists: False")


# ============================================
# Test 5: _update_session_metadata() 호출 확인
# ============================================

@pytest.mark.asyncio
async def test_metadata_auto_update_on_add_turn(session_memory, session_id, mock_redis):
    """턴 추가 시 메타데이터 자동 업데이트"""
    # Arrange
    mock_redis.hgetall.return_value = {}  # 기존 메타데이터 없음
    mock_redis.llen.return_value = 1

    # Act
    await session_memory.add_turn(session_id, "user", "Hello")

    # Assert
    # hset이 호출되었는지 확인 (created_at, updated_at, turn_count)
    assert mock_redis.hset.called
    assert mock_redis.hset.call_count >= 3  # created_at, updated_at, turn_count

    print("✅ Metadata auto-updated on add_turn")


# ============================================
# Test 6: 통합 시나리오 (Mock)
# ============================================

@pytest.mark.asyncio
async def test_full_conversation_flow_mock(session_memory, session_id, mock_redis):
    """통합 테스트: 전체 대화 플로우 (Mock)"""
    # 1. 세션 존재 확인 (없음)
    mock_redis.exists.return_value = 0
    assert await session_memory.exists(session_id) is False

    # 2. 대화 시작
    await session_memory.add_turn(session_id, "user", "안녕하세요")
    await session_memory.add_turn(session_id, "assistant", "반갑습니다!")

    # 3. 세션 존재 확인 (있음)
    mock_redis.exists.return_value = 1
    assert await session_memory.exists(session_id) is True

    # 4. 대화 턴 조회
    turn1 = json.dumps({"role": "user", "content": "안녕하세요", "timestamp": "2026-01-01T00:00:00"})
    turn2 = json.dumps({"role": "assistant", "content": "반갑습니다!", "timestamp": "2026-01-01T00:01:00"})
    mock_redis.lrange.return_value = [turn1.encode(), turn2.encode()]

    turns = await session_memory.get_all_turns(session_id)
    assert len(turns) == 2

    # 5. 메타데이터 확인
    mock_redis.hgetall.return_value = {
        b"created_at": b"2026-01-01T00:00:00",
        b"updated_at": b"2026-01-01T00:01:00",
        b"turn_count": b"2"
    }

    metadata = await session_memory.get_metadata(session_id)
    assert metadata["turn_count"] == "2"

    print("✅ Full conversation flow test passed (Mock)")


# ============================================
# Test Summary
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SessionMemory 확장 기능 테스트 시작 (Mock)")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
