"""대화 피로도 방지 기능 테스트

1. _count_recent_turns() 윈도우 기반 턴 카운트 정확성
2. SYSTEM_PROMPT Rule 9 사용자 의도 파악 시나리오 포함
3. suppress_questions 프롬프트 마무리 가이드 포함
"""

import pytest
from datetime import datetime, timedelta
from core.dialogue.dialogue_manager import DialogueManager, TURN_WINDOW_SECONDS, MAX_TURNS_PER_WINDOW


class TestCountRecentTurns:
    """_count_recent_turns() 윈도우 기반 턴 카운트 테스트"""

    def setup_method(self):
        self.dm = DialogueManager()

    def test_empty_history(self):
        """빈 히스토리 → 0 반환"""
        assert self.dm._count_recent_turns({"conversation_history": []}) == 0

    def test_no_timestamp(self):
        """타임스탬프 없는 턴 → 카운트 제외"""
        history = [
            {"user": "안녕", "assistant": "반가워요"},
            {"user": "뭐해", "assistant": "인사하네요"},
        ]
        assert self.dm._count_recent_turns({"conversation_history": history}) == 0

    def test_recent_turns_only(self):
        """최근 1시간 내 턴만 카운트"""
        now = datetime.now()
        history = [
            {"user": "1", "assistant": "r", "timestamp": (now - timedelta(minutes=30)).isoformat()},
            {"user": "2", "assistant": "r", "timestamp": (now - timedelta(minutes=10)).isoformat()},
            {"user": "3", "assistant": "r", "timestamp": (now - timedelta(minutes=2)).isoformat()},
        ]
        assert self.dm._count_recent_turns({"conversation_history": history}) == 3

    def test_old_turns_excluded(self):
        """1시간 이전 턴은 제외"""
        now = datetime.now()
        history = [
            {"user": "old", "assistant": "r", "timestamp": (now - timedelta(hours=2)).isoformat()},
            {"user": "recent", "assistant": "r", "timestamp": (now - timedelta(minutes=5)).isoformat()},
        ]
        assert self.dm._count_recent_turns({"conversation_history": history}) == 1

    def test_mixed_turns(self):
        """최근/과거 혼합"""
        now = datetime.now()
        history = [
            {"user": "old1", "assistant": "r", "timestamp": (now - timedelta(hours=3)).isoformat()},
            {"user": "recent1", "assistant": "r", "timestamp": (now - timedelta(minutes=40)).isoformat()},
            {"user": "old2", "assistant": "r", "timestamp": (now - timedelta(hours=5)).isoformat()},
            {"user": "recent2", "assistant": "r", "timestamp": (now - timedelta(minutes=1)).isoformat()},
        ]
        assert self.dm._count_recent_turns({"conversation_history": history}) == 2

    def test_window_boundary(self):
        """윈도우 경계 (정확히 1시간 전은 제외)"""
        now = datetime.now()
        # 3599초 전 = 윈도우 내
        just_inside = (now - timedelta(seconds=3599)).isoformat()
        # 3601초 전 = 윈도우 외
        just_outside = (now - timedelta(seconds=3601)).isoformat()

        history_inside = [{"user": "a", "assistant": "r", "timestamp": just_inside}]
        assert self.dm._count_recent_turns({"conversation_history": history_inside}) == 1

        history_outside = [{"user": "a", "assistant": "r", "timestamp": just_outside}]
        assert self.dm._count_recent_turns({"conversation_history": history_outside}) == 0


class TestSystemPromptRule9:
    """SYSTEM_PROMPT Rule 9 대화 의도 파악 시나리오"""

    @pytest.mark.asyncio
    async def test_intent_awareness_in_prompt(self):
        """사용자 발화 의도 판단 시나리오가 프롬프트에 포함되어야 함"""
        from core.dialogue.prompt_builder import PromptBuilder, SYSTEM_PROMPT
        prompt = SYSTEM_PROMPT

        # 동의/확인형
        assert "동의" in prompt or "확인형" in prompt
        # 감탄/정리형
        assert "감탄" in prompt or "정리형" in prompt
        # 무관심
        assert "무관심" in prompt or "글쎄" in prompt
        # 마무리형
        assert "마무리형" in prompt or "딱히" in prompt

    @pytest.mark.asyncio
    async def test_good_example_no_question_closure(self):
        """질문 없이 자연 종료하는 좋은 예시 포함"""
        from core.dialogue.prompt_builder import SYSTEM_PROMPT
        # Rule 9 예시에 "자연 종료" 예시 포함
        assert "양념 잘 베일 때" in SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_bad_example_unnecessary_question(self):
        """이어갈 의도 없는데 질문하는 나쁜 예시 포함"""
        from core.dialogue.prompt_builder import SYSTEM_PROMPT
        assert "이어갈 의도" in SYSTEM_PROMPT


class TestSuppressQuestionsPrompt:
    """suppress_questions 플래그 시 프롬프트 가이드 테스트"""

    @pytest.mark.asyncio
    async def test_suppress_prompt_includes_closure_guide(self):
        """suppress_questions=True → 자연스러운 마무리 가이드 포함"""
        from core.dialogue.prompt_builder import PromptBuilder
        pb = PromptBuilder()
        prompt = await pb.build_system_prompt(suppress_questions=True)

        assert "피로도 방지" in prompt
        assert "자연스럽게 멈추세요" in prompt
        # 상담사 느낌의 나쁜 예시도 포함
        assert "상담사 느낌" in prompt or "디딱" in prompt

    @pytest.mark.asyncio
    async def test_suppress_prompt_bans_questions(self):
        """suppress_questions=True → 질문 완전 금지 가이드 포함"""
        from core.dialogue.prompt_builder import PromptBuilder
        pb = PromptBuilder()
        prompt = await pb.build_system_prompt(suppress_questions=True)

        assert "절대 새로운 질문" in prompt
        assert "의문형 어미" in prompt

    @pytest.mark.asyncio
    async def test_no_suppress_flag(self):
        """suppress_questions=False → 피로도 방지 블록 미포함"""
        from core.dialogue.prompt_builder import PromptBuilder
        pb = PromptBuilder()
        prompt = await pb.build_system_prompt(suppress_questions=False)

        assert "피로도 방지" not in prompt


class TestConstants:
    """상수값 검증"""

    def test_turn_window_is_one_hour(self):
        assert TURN_WINDOW_SECONDS == 3600

    def test_max_turns_per_window(self):
        assert MAX_TURNS_PER_WINDOW == 5
