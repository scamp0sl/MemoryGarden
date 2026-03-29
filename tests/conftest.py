"""
테스트 공통 Fixture

pytest 테스트에서 사용하는 공통 fixture를 정의합니다.
- 테스트 DB (SQLite in-memory)
- Redis/Qdrant mock
- OpenAI/Claude API mock
- 샘플 데이터

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# Standard Library Imports
# ============================================
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================
# Third-Party Imports
# ============================================
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

# ============================================
# Local Imports
# ============================================
from api.main import app


# ============================================
# Pytest 설정
# ============================================

def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


@pytest.fixture(scope="function")
def event_loop():
    """
    이벤트 루프 fixture (함수 스코프)

    각 async 테스트마다 새로운 이벤트 루프 사용
    Redis 비동기 연결 문제 방지
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop

    # 정리: 모든 태스크 취소 및 루프 종료
    try:
        # 남은 태스크들 취소
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        # 취소된 태스크 완료 대기
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    finally:
        loop.close()


# ============================================
# 테스트 DB Fixtures
# ============================================

# In-memory SQLite for fast testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    테스트용 비동기 DB 세션

    각 테스트마다 독립적인 in-memory DB 사용
    테스트 후 자동으로 정리됨
    """
    # 비동기 엔진 생성
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )

    # 테이블 생성
    # TODO: Base.metadata.create_all 비동기 버전
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    # 세션 팩토리 생성
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    # 정리
    await engine.dispose()


@pytest.fixture(scope="function")
def mock_db_session():
    """
    Mock DB 세션 (실제 DB 없이 테스트)

    DB 연결 없이 빠른 단위 테스트용
    """
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.query = MagicMock()
    session.close = MagicMock()

    return session


# ============================================
# Redis/Qdrant Mock Fixtures
# ============================================

@pytest.fixture(scope="function")
def mock_redis():
    """
    Mock Redis 클라이언트

    실제 Redis 없이 테스트 가능
    """
    redis_mock = AsyncMock()

    # 간단한 in-memory 저장소
    storage = {}

    async def mock_set(key: str, value: str, ex: int = None):
        storage[key] = value
        return True

    async def mock_get(key: str):
        return storage.get(key)

    async def mock_delete(key: str):
        if key in storage:
            del storage[key]
        return 1

    async def mock_ping():
        return True

    redis_mock.set = mock_set
    redis_mock.setex = mock_set
    redis_mock.get = mock_get
    redis_mock.delete = mock_delete
    redis_mock.ping = mock_ping
    redis_mock.close = AsyncMock()

    return redis_mock


@pytest_asyncio.fixture(scope="function")
async def redis_for_test():
    """
    실제 Docker Redis 연결 (통합 테스트용)

    Redis 통합 테스트에서 사용.
    테스트 전: test_ prefix 키만 정리
    테스트 후: 자동 정리

    Example:
        @pytest.mark.asyncio
        async def test_something(redis_for_test):
            client = redis_for_test
            await client.set("test_key", "value")
    """
    from database.redis_client import redis_client

    try:
        # Redis 연결
        client = await redis_client.get_client()

        # 연결 확인
        await client.ping()

        # 테스트 전 정리: test_ prefix 키만 삭제
        test_keys = await client.keys("test_*")
        if test_keys:
            await client.delete(*test_keys)

        yield client

    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    finally:
        # 테스트 후 정리: test_ prefix 키 삭제
        try:
            test_keys = await client.keys("test_*")
            if test_keys:
                await client.delete(*test_keys)
        except Exception:
            pass  # Cleanup 실패는 무시


@pytest.fixture(scope="function")
def mock_qdrant():
    """
    Mock Qdrant 클라이언트

    실제 Qdrant 없이 테스트 가능
    """
    qdrant_mock = AsyncMock()

    # 간단한 in-memory 벡터 저장소
    vectors = {}

    async def mock_upsert(collection_name: str, points: list):
        if collection_name not in vectors:
            vectors[collection_name] = []
        vectors[collection_name].extend(points)
        return True

    async def mock_search(collection_name: str, query_vector: list, limit: int = 10, **kwargs):
        # Mock 검색 결과
        return [
            {
                "id": f"point_{i}",
                "score": 0.9 - (i * 0.1),
                "payload": {"text": f"Mock result {i}"}
            }
            for i in range(min(limit, 3))
        ]

    async def mock_get_collections():
        return MagicMock(collections=[])

    qdrant_mock.upsert = mock_upsert
    qdrant_mock.search = mock_search
    qdrant_mock.get_collections = mock_get_collections

    return qdrant_mock


# ============================================
# AI API Mock Fixtures
# ============================================

@pytest.fixture(scope="function")
def mock_openai():
    """
    Mock OpenAI API

    실제 API 호출 없이 테스트 가능
    """
    with patch('openai.ChatCompletion.acreate') as mock:
        # Mock 응답 구조
        mock.return_value = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4o-2024-08-06",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Mock OpenAI response"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }

        yield mock


@pytest.fixture(scope="function")
def mock_claude():
    """
    Mock Claude API (Anthropic)

    실제 API 호출 없이 테스트 가능
    """
    with patch('anthropic.AsyncAnthropic') as mock_client:
        # Mock 응답
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="Mock Claude response")
        ]
        mock_response.usage = MagicMock(
            input_tokens=10,
            output_tokens=20
        )

        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=mock_response)

        mock_client.return_value = mock_instance

        yield mock_instance


@pytest.fixture(scope="function")
def mock_embeddings():
    """
    Mock OpenAI Embeddings API

    고정된 벡터 반환
    """
    with patch('openai.Embedding.acreate') as mock:
        # 1536 차원 벡터 (OpenAI text-embedding-3-small)
        mock.return_value = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1] * 1536,  # Mock 벡터
                    "index": 0
                }
            ],
            "model": "text-embedding-3-small",
            "usage": {
                "prompt_tokens": 5,
                "total_tokens": 5
            }
        }

        yield mock


# ============================================
# FastAPI Test Client Fixtures
# ============================================

@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    비동기 FastAPI 테스트 클라이언트

    실제 HTTP 요청을 시뮬레이션
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================
# 샘플 데이터 Fixtures
# ============================================

@pytest.fixture(scope="function")
def sample_user() -> Dict[str, Any]:
    """샘플 사용자 데이터"""
    return {
        "user_id": "test_user_123",
        "name": "테스트 사용자",
        "birth_date": "1950-01-01",
        "kakao_id": "kakao_test_123",
        "baseline_mcdi": 78.5,
        "baseline_established_at": datetime.now().isoformat()
    }


@pytest.fixture(scope="function")
def sample_session() -> Dict[str, Any]:
    """샘플 세션 데이터"""
    return {
        "session_id": "test_session_456",
        "user_id": "test_user_123",
        "category": "daily_episodic",
        "difficulty": "medium",
        "status": "active",
        "started_at": datetime.now().isoformat()
    }


@pytest.fixture(scope="function")
def sample_message() -> Dict[str, Any]:
    """샘플 메시지 데이터"""
    return {
        "message_id": "test_msg_789",
        "session_id": "test_session_456",
        "user_id": "test_user_123",
        "content": "오늘 점심에 김치찌개를 먹었어요",
        "message_type": "text",
        "sender": "user",
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture(scope="function")
def sample_context() -> Dict[str, Any]:
    """샘플 처리 컨텍스트"""
    return {
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "message": "오늘 점심에 김치찌개를 먹었어요",
        "message_type": "text",
        "conversation_count": 50,
        "consecutive_days": 15,
        "current_streak": 15
    }


@pytest.fixture(scope="function")
def sample_analysis_result() -> Dict[str, Any]:
    """샘플 분석 결과"""
    return {
        "scores": {
            "LR": 78.5,
            "SD": 82.3,
            "NC": 75.0,
            "TO": 80.0,
            "ER": 72.5,
            "RT": 74.0
        },
        "mcdi_score": 77.2,
        "lr_detail": {
            "score": 78.5,
            "components": {
                "pronoun_ratio": 0.15,
                "mattr": 0.72,
                "concreteness": 0.85,
                "empty_speech_ratio": 0.05
            }
        },
        "risk_level": "GREEN",
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture(scope="function")
def sample_garden_status() -> Dict[str, Any]:
    """샘플 정원 상태"""
    return {
        "user_id": "test_user_123",
        "total_conversations": 50,
        "consecutive_days": 15,
        "current_streak": 15,
        "current_level": 2,
        "flowers_count": 50,
        "butterflies_count": 5,
        "trees_count": 1,
        "season_badges": ["spring_2025"]
    }


# ============================================
# Mock Service Fixtures
# ============================================

@pytest.fixture(scope="function")
def mock_llm_service():
    """Mock LLM Service"""
    service = AsyncMock()
    service.call = AsyncMock(return_value="Mock LLM response")
    service.call_with_json = AsyncMock(return_value={"key": "value"})
    return service


@pytest.fixture(scope="function")
def mock_memory_manager():
    """Mock Memory Manager"""
    manager = AsyncMock()

    # retrieve_all mock
    manager.retrieve_all = AsyncMock(return_value={
        "session": {"context": "mock session data"},
        "episodic": [{"content": "mock episodic memory"}],
        "biographical": {"facts": ["fact1", "fact2"]},
        "analytical": {"mcdi_score": 78.5}
    })

    # store_all mock
    manager.store_all = AsyncMock(return_value=True)

    # extract_facts mock
    manager.extract_facts = AsyncMock(return_value=[
        {"fact": "user had kimchi stew for lunch", "timestamp": datetime.now().isoformat()}
    ])

    return manager


@pytest.fixture(scope="function")
def mock_analyzer():
    """Mock Analyzer"""
    analyzer = AsyncMock()

    analyzer.analyze = AsyncMock(return_value={
        "scores": {
            "LR": 78.5,
            "SD": 82.3,
            "NC": 75.0,
            "TO": 80.0,
            "ER": 72.5,
            "RT": 74.0
        },
        "mcdi_score": 77.2,
        "risk_level": "GREEN"
    })

    return analyzer


@pytest.fixture(scope="function")
def mock_dialogue_manager():
    """Mock Dialogue Manager"""
    manager = AsyncMock()

    manager.generate_response = AsyncMock(return_value="Mock dialogue response")
    manager.generate_question = AsyncMock(return_value="Mock question")
    manager.plan_next = AsyncMock(return_value={
        "category": "daily_episodic",
        "difficulty": "medium"
    })

    return manager


@pytest.fixture(scope="function")
def mock_vision_service():
    """Mock Vision Service"""
    service = AsyncMock()

    service.generate_garden_visualization = AsyncMock(return_value={
        "weather": "sunny",
        "season": "spring",
        "time_of_day": "morning",
        "garden_health": "good",
        "flowers": [{"id": "flower_1", "type": "tulip", "state": "blooming"}],
        "butterflies": [{"id": "butterfly_1", "color": "yellow", "is_active": True}],
        "trees": [{"id": "tree_1", "growth_stage": "sapling", "size": 0.5}],
        "decorations": [],
        "special_effects": []
    })

    return service


# ============================================
# 유틸리티 Fixtures
# ============================================

@pytest.fixture(scope="function")
def freeze_time():
    """시간 고정 (테스트용)"""
    fixed_time = datetime(2025, 2, 10, 12, 0, 0)

    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        yield fixed_time


@pytest.fixture(scope="function")
def capture_logs():
    """로그 캡처 (테스트 검증용)"""
    import logging
    from io import StringIO

    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)

    logger = logging.getLogger()
    logger.addHandler(handler)

    yield log_stream

    logger.removeHandler(handler)


# ============================================
# Cleanup Hooks
# ============================================

@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_after_test(event_loop):
    """각 테스트 전후 자동 정리"""
    # 테스트 전: Redis 클라이언트 완전 리셋
    from database.redis_client import RedisClient

    # 기존 연결 강제 종료
    if RedisClient._client is not None:
        try:
            await RedisClient._client.close()
        except Exception:
            pass

    if RedisClient._pool is not None:
        try:
            await RedisClient._pool.disconnect()
        except Exception:
            pass

    # Singleton 인스턴스 완전 리셋
    RedisClient._client = None
    RedisClient._pool = None
    RedisClient._initialized = False

    yield

    # 테스트 후: Redis 테스트 키 정리 및 연결 종료
    try:
        from database.redis_client import redis_client

        # 새로운 이벤트 루프에서 새 연결 생성
        client = await redis_client.get_client()

        # test_ prefix 키만 삭제
        try:
            test_keys = await client.keys("test_*")
            if test_keys:
                await client.delete(*test_keys)
        except Exception:
            pass

        # session:test_ prefix 키도 삭제
        try:
            session_keys = await client.keys("session:test_*")
            if session_keys:
                await client.delete(*session_keys)
        except Exception:
            pass

        # 연결 종료
        try:
            await client.close()
        except Exception:
            pass

        if RedisClient._pool is not None:
            try:
                await RedisClient._pool.disconnect()
            except Exception:
                pass

    except Exception:
        pass  # Redis 연결 실패는 무시

    finally:
        # 최종 정리
        RedisClient._client = None
        RedisClient._pool = None
        RedisClient._initialized = False
