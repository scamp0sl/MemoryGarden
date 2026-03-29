"""
Task 7 - Conversations History API 테스트

PostgreSQL 기반 대화 목록 조회 검증
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import uuid


# ============================================
# Helper Functions
# ============================================

def setup_mock_session(conversations_data, total_count):
    """Mock session setup helper"""
    mock_session = AsyncMock()

    # Mock count query
    count_result = MagicMock()
    count_result.scalar.return_value = total_count

    # Mock conversations query
    conv_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = conversations_data
    conv_result.scalars.return_value = scalars_mock

    # Create async function that returns the appropriate mock
    async def execute_mock(query):
        query_str = str(query)
        if "count" in query_str.lower():
            return count_result
        return conv_result

    # Set side_effect instead of direct assignment
    mock_session.execute = AsyncMock(side_effect=execute_mock)
    return mock_session


# ============================================
# Test 1: 대화 목록 조회
# ============================================

@pytest.mark.asyncio
async def test_list_user_conversations_success():
    """정상 케이스: 대화 목록 조회"""
    from fastapi.testclient import TestClient
    from api.main import app
    from database.postgres import get_db

    user_id = str(uuid.uuid4())

    # Arrange
    conv1 = MagicMock()
    conv1.id = 1
    conv1.user_id = user_id
    conv1.message = "안녕하세요"
    conv1.response = "반갑습니다"
    conv1.created_at = datetime.now()
    conv1.analysis_result = None

    conv2 = MagicMock()
    conv2.id = 2
    conv2.user_id = user_id
    conv2.message = "오늘 날씨 좋네요"
    conv2.response = "네, 맑은 날씨입니다"
    conv2.created_at = datetime.now() - timedelta(hours=1)
    analysis = MagicMock()
    analysis.mcdi_score = 80.0
    conv2.analysis_result = analysis

    mock_session = setup_mock_session([conv1, conv2], 2)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/conversations/users/{user_id}/conversations")

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["conversations"]) == 2

        print(f"✅ Retrieved {len(data['conversations'])} conversations")

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_conversations_with_pagination():
    """페이지네이션 테스트"""
    from fastapi.testclient import TestClient
    from api.main import app
    from database.postgres import get_db

    user_id = str(uuid.uuid4())

    conversations = []
    for i in range(3):
        conv = MagicMock()
        conv.id = i
        conv.user_id = user_id
        conv.message = f"Message {i}"
        conv.response = f"Response {i}"
        conv.created_at = datetime.now() - timedelta(hours=i)
        conv.analysis_result = None
        conversations.append(conv)

    mock_session = setup_mock_session(conversations, 10)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/conversations/users/{user_id}/conversations",
            params={"skip": 0, "limit": 3}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 10
        assert data["skip"] == 0
        assert data["limit"] == 3
        assert len(data["conversations"]) == 3

        print(f"✅ Pagination works: showing {len(data['conversations'])} of {data['total']}")

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_conversations_empty_result():
    """엣지 케이스: 대화 없음"""
    from fastapi.testclient import TestClient
    from api.main import app
    from database.postgres import get_db

    user_id = str(uuid.uuid4())

    mock_session = setup_mock_session([], 0)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/conversations/users/{user_id}/conversations")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert len(data["conversations"]) == 0

        print("✅ Empty result handled correctly")

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_conversations_with_mcdi_score():
    """MCDI 점수 포함 검증"""
    from fastapi.testclient import TestClient
    from api.main import app
    from database.postgres import get_db

    user_id = str(uuid.uuid4())

    conv = MagicMock()
    conv.id = 1
    conv.user_id = user_id
    conv.message = "테스트 메시지"
    conv.response = "테스트 응답"
    conv.created_at = datetime.now()

    analysis = MagicMock()
    analysis.mcdi_score = 85.5
    analysis.risk_level = "GREEN"
    conv.analysis_result = analysis

    mock_session = setup_mock_session([conv], 1)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/conversations/users/{user_id}/conversations")

        assert response.status_code == 200
        data = response.json()

        turn = data["conversations"][0]["turns"][0]
        assert turn["mcdi_score"] == 85.5

        print(f"✅ MCDI score included: {turn['mcdi_score']}")

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_conversations_with_date_filter():
    """날짜 필터링 테스트"""
    from fastapi.testclient import TestClient
    from api.main import app
    from database.postgres import get_db

    user_id = str(uuid.uuid4())

    conv = MagicMock()
    conv.id = 1
    conv.user_id = user_id
    conv.message = "필터링된 메시지"
    conv.response = "필터링된 응답"
    conv.created_at = datetime(2026, 2, 10, 12, 0, 0)
    conv.analysis_result = None

    mock_session = setup_mock_session([conv], 1)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/conversations/users/{user_id}/conversations",
            params={
                "start_date": "2026-02-01",
                "end_date": "2026-02-15"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["conversations"]) == 1

        print(f"✅ Date filter works: found {data['total']} conversations")

    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Conversations History API 테스트 시작")
    print("=" * 60 + "\n")

    pytest.main([__file__, "-v", "-s"])
