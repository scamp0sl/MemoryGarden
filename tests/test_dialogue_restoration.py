import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from core.dialogue.dialogue_manager import DialogueManager
from database.models import Conversation

@pytest.mark.asyncio
async def test_restore_session_success():
    # 1. Setup
    dm = DialogueManager()
    user_id = str(uuid4())
    mock_db = AsyncMock()
    
    # Mock DB 결과 생성 (최근 2개 대화)
    mock_convs = [
        Conversation(
            id=1,
            user_id=user_id,
            message="두번째 질문 답변",
            response="두번째 AI 응답",
            category="daily_episodic",
            created_at=datetime(2025, 1, 1, 12, 10)
        ),
        Conversation(
            id=2,
            user_id=user_id,
            message="첫번째 질문 답변",
            response="첫번째 AI 응답",
            category="reminiscence",
            created_at=datetime(2025, 1, 1, 12, 0)
        )
    ]
    
    # execute 결과 mock
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_convs
    mock_db.execute.return_value = mock_result
    
    # Redis client mock
    with patch("core.dialogue.dialogue_manager.redis_client") as mock_redis:
        mock_redis.set_session = AsyncMock()
        
        # 2. Execute
        session_data = await dm.restore_session(user_id, mock_db)
        
        # 3. Verify
        assert session_data is not None
        assert session_data["user_id"] == user_id
        assert len(session_data["conversation_history"]) == 2
        
        # 정렬 확인 (오래된 순)
        assert session_data["conversation_history"][0]["user"] == "첫번째 질문 답변"
        assert session_data["conversation_history"][1]["user"] == "두번째 질문 답변"
        
        # Redis 저장 확인
        mock_redis.set_session.assert_called_once()
        args, kwargs = mock_redis.set_session.call_args
        assert kwargs["user_id"] == user_id
        assert kwargs["session_data"]["turn_count"] == 2

@pytest.mark.asyncio
async def test_restore_session_no_data():
    dm = DialogueManager()
    user_id = str(uuid4())
    mock_db = AsyncMock()
    
    # DB 결과가 없는 경우
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    session_data = await dm.restore_session(user_id, mock_db)
    
    assert session_data is None
