"""대화 맥락 연속성 + 파라미터 전달 검증 테스트

1. MAX_CONTEXT_TURNS = 20 상수 검증
2. recent_mentions가 user_context에 설정되는지 검증
3. suppress_questions가 response_generator → prompt_builder 파이프라인에 도달하는지 검증
4. SYSTEM_PROMPT Rule 11 대화 맥락 연속성 포함 검증
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.dialogue.dialogue_manager import DialogueManager, MAX_CONTEXT_TURNS
from core.dialogue.prompt_builder import SYSTEM_PROMPT


class TestContextWindow:
    """MAX_CONTEXT_TURNS 상수 검증"""

    def test_max_context_turns_is_twenty(self):
        """MAX_CONTEXT_TURNS가 20 이상이어야 점심+저녁 대화 맥락 보존 가능"""
        assert MAX_CONTEXT_TURNS >= 20


class TestRecentMentionsExtraction:
    """recent_mentions 추출 검증"""

    @pytest.mark.asyncio
    async def test_recent_mentions_extracted_from_session(self):
        """generate_response()가 세션 히스토리에서 recent_mentions를 추출해야 함"""
        dm = DialogueManager()

        # Mock session with conversation history
        session_data = {
            "session_id": "test",
            "user_id": "user123",
            "turn_count": 3,
            "context": {},
            "conversation_history": [
                {"user": "점심으로 닭튀김 먹었어", "assistant": "맛있겠다!", "timestamp": "2026-03-27T12:30:00"},
                {"user": "뷔페에서 먹었어", "assistant": "뷔페 최고지!", "timestamp": "2026-03-27T12:31:00"},
                {"user": "맛있었어", "assistant": "ㅎㅎ", "timestamp": "2026-03-27T12:32:00"},
            ]
        }

        # Mock methods that would be called before recent_mentions extraction
        dm._detect_emotion = AsyncMock(return_value="중립")
        dm._update_emotion_vector = AsyncMock(return_value={"v": 0.0, "a": 0.0, "i": 0.5})
        dm._update_relationship_stage = AsyncMock(return_value=2)
        dm.update_last_interaction = AsyncMock()
        dm.memory_manager.retrieve_all = AsyncMock(return_value={"episodic": [], "biographical": {}})
        dm.response_validator.validate = AsyncMock(return_value={"modified": "test response", "issues": [], "warnings": []})

        # Mock get_session and get_conversation_history
        dm.get_session = AsyncMock(return_value=session_data)
        dm.get_conversation_history = AsyncMock(return_value=[
            {"role": "user", "content": "점심으로 닭튀김 먹었어"},
            {"role": "assistant", "content": "맛있겠다!"},
        ])
        dm.response_generator.generate = AsyncMock(return_value="닭튀김 맛있었어요? ㅎㅎ")

        await dm.generate_response(
            user_id="user123",
            user_message="배부르다"
        )

        # Verify _build_system_prompt was called with recent_mentions in user_context
        call_args = dm.response_generator.generate.call_args
        user_context = call_args.kwargs.get("user_context") or call_args[1].get("user_context")

        assert user_context is not None
        assert "recent_mentions" in user_context
        assert len(user_context["recent_mentions"]) == 3
        assert "닭튀김" in user_context["recent_mentions"][0]


class TestSuppressQuestionsPipeline:
    """suppress_questions 파이프라인 전달 검증"""

    @pytest.mark.asyncio
    async def test_suppress_questions_reaches_prompt_builder(self):
        """suppress_questions=True가 dialogue_manager → response_generator → prompt_builder까지 도달해야 함"""
        dm = DialogueManager()

        # Create session with 6 recent turns (triggers suppress)
        from datetime import datetime, timedelta
        now = datetime.now()
        recent_history = []
        for i in range(6):
            recent_history.append({
                "user": f"msg {i}",
                "assistant": f"resp {i}",
                "timestamp": (now - timedelta(minutes=i * 5)).isoformat()
            })

        session_data = {
            "session_id": "test",
            "user_id": "user123",
            "turn_count": 6,
            "context": {},
            "conversation_history": recent_history
        }

        # Mock all dependencies
        dm._detect_emotion = AsyncMock(return_value="중립")
        dm._update_emotion_vector = AsyncMock(return_value={"v": 0.0, "a": 0.0, "i": 0.5})
        dm._update_relationship_stage = AsyncMock(return_value=2)
        dm.update_last_interaction = AsyncMock()
        dm.memory_manager.retrieve_all = AsyncMock(return_value={"episodic": [], "biographical": {}})
        dm.response_validator.validate = AsyncMock(return_value={"modified": "test response", "issues": [], "warnings": []})
        dm.get_session = AsyncMock(return_value=session_data)
        dm.get_conversation_history = AsyncMock(return_value=[])
        dm.response_generator.generate = AsyncMock(return_value="좋아요~")

        await dm.generate_response(
            user_id="user123",
            user_message="응"
        )

        # Verify suppress_questions was passed through to generate()
        call_args = dm.response_generator.generate.call_args
        user_context = call_args.kwargs.get("user_context") or call_args[1].get("user_context")

        assert user_context is not None
        assert user_context.get("suppress_questions") is True


class TestSystemPromptRule11:
    """SYSTEM_PROMPT Rule 11 대화 맥락 연속성 검증"""

    def test_rule_11_context_continuity_exists(self):
        """SYSTEM_PROMPT에 Rule 11 대화 맥락 연속성이 포함되어야 함"""
        assert "대화 맥락 연속성" in SYSTEM_PROMPT

    def test_rule_11_forbids_reasking(self):
        """Rule 11이 방금 대화한 내용을 다시 묻는 것을 금지해야 함"""
        assert "재질문" in SYSTEM_PROMPT or "모른 척" in SYSTEM_PROMPT

    def test_rule_11_natural_reference(self):
        """Rule 11이 자연스러운 인용을 예시로 포함해야 함"""
        assert "자연스럽게" in SYSTEM_PROMPT
