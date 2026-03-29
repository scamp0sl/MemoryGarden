"""Phase S: 질문 패턴 재설계 테스트"""

import pytest
from core.dialogue.dialogue_manager import DialogueManager


@pytest.mark.asyncio
@pytest.mark.slow  # [결함 #20] LLM 응답 기반이므로 비결정적
class TestQuestionFrequencyControl:
    """S-1: 질문 빈도 제어 테스트"""

    async def test_fatigue_signal_no_question(self):
        """피로 신호 시 질문 자제"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_fatigue",
            user_message="너무 피곤해요"
        )

        # 물음표 0-1개만 허용
        question_count = response.count("?")
        assert question_count <= 1, f"Too many questions: {question_count}"

        # 피로를 공감하는 표현 포함
        assert any(kw in response for kw in ["피곤", "힘드", "쉬", "휴식"])

    async def test_user_complaint_response(self):
        """"질문이 많아" 불만에 대한 반응"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_complaint",
            user_message="너무 질문이 많아"
        )

        # 사과/이해 표현
        assert any(kw in response for kw in ["죄송", "미안", "이해", "알겠"])

        # 추가 질문 없음
        assert not response.strip().endswith("?")

    async def test_short_answer_no_followup(self):
        """짧은 답변 후 추가 질문 자제"""
        manager = DialogueManager()

        # 짧은 답변 3회
        for _ in range(3):
            response = await manager.generate_response(
                user_id="test_s_short",
                user_message="응"
            )

        # 3턴 후에는 질문 빈도 감소
        assert response.count("?") <= 1

    async def test_active_conversation_questions_ok(self):
        """활발한 대화에서는 질문 허용"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_active",
            user_message="오늘 딸이랑 벚꽃 구경하러 다녀왔어요. 정말 예쁘더라고요."
        )

        # 적절한 질문 1개 허용
        question_count = response.count("?")
        assert 0 <= question_count <= 2


@pytest.mark.asyncio
@pytest.mark.slow  # [결함 #20] LLM 응답 기반
class TestConversationClosure:
    """S-2: 대화 종료 패턴 테스트"""

    async def test_fatigue_closure(self):
        """피로 신호 시 자연스러운 종료"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_closure",
            user_message="힘들어서 그만 얘기하고 싶어요"
        )

        # 종료 키워드
        assert any(kw in response for kw in ["쉬세요", "나중에", "편안한", "안녕"])

        # 종료 후 질문 없음
        assert not response.strip().endswith("?")

    async def test_goodbye_no_followup(self):
        """작별 인사 후 추가 질문 없음"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_goodbye",
            user_message="그럼 안녕히 계세요"
        )

        # 응답이 짧고 종료적이어야 함
        assert len(response) < 100
        assert "안녕" in response or "좋은" in response

    async def test_multiple_fatigue_signals(self):
        """반복적인 피로 신호에 일관된 대응"""
        manager = DialogueManager()

        fatigue_messages = ["피곤해", "힘들어", "쉬고싶어"]

        for msg in fatigue_messages:
            response = await manager.generate_response(
                user_id="test_s_multi_fatigue",
                user_message=msg
            )

            # 모든 경우에 종료 패턴
            assert not response.strip().endswith("?")
