"""
이브닝 퀴즈 시스템 테스트 (방안 D)

1. 17:50 스케줄러로 퀴즈 미리 생성
2. 저녁 시간 첫 메시지에 퀴즈만 전송
3. 퀴즈 답변 평가
4. MCDI RT 점수 반영

Author: Memory Garden Team
Created: 2026-03-29
Updated: 2026-03-29 (방안 D 구현)
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class TestEveningQuizFunction:
    """함수 존재 검증"""

    def test_function_exists(self):
        """필요한 함수들이 존재해야 함"""
        from api.routes.kakao_webhook import (
            _pre_generate_evening_quiz,
            _evaluate_quiz_answer,
            _adjust_mcdi_rt_score
        )
        from tasks.dialogue import pre_generate_evening_quizzes

        assert callable(_pre_generate_evening_quiz)
        assert callable(_evaluate_quiz_answer)
        assert callable(_adjust_mcdi_rt_score)
        assert callable(pre_generate_evening_quizzes)


@pytest.mark.asyncio
class TestEveningQuizPreGeneration:
    """퀴즈 사전 생성 테스트"""

    async def test_pre_generate_quiz_creates_cache(self, redis_client):
        """퀴즈가 정상적으로 생성되고 캐시되는지 테스트"""
        from api.routes.kakao_webhook import _pre_generate_evening_quiz

        user_id = "test_user_123"

        # Mock DB session
        with patch('api.routes.kakao_webhook.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # Mock conversations
            mock_conv = Mock()
            mock_conv.message = "아침에 등산 갔다 왔어요"
            mock_conv.response = "무슨 꽃을 보셨나요?"
            mock_conv.category = "DAILY_EPISODIC"

            mock_result = Mock()
            mock_result.scalars().all.return_value = [mock_conv]
            mock_db.execute.return_value = mock_result

            # Mock LLM
            with patch('api.routes.kakao_webhook.LLMService') as mock_llm:
                mock_instance = AsyncMock()
                mock_instance.call.return_value = "아침에 등산하면서 본 꽃이 뭔지 얘기해줘요"
                mock_llm.return_value = mock_instance

                # 퀴즈 생성
                await _pre_generate_evening_quiz(user_id)

        # 캐시 확인
        from zoneinfo import ZoneInfo
        today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
        cache_key = f"evening_quiz_cache:{user_id}:{today_str}"
        done_key = f"evening_quiz_done:{user_id}:{today_str}"

        cached_data = await redis_client.get(cache_key)
        done_exists = await redis_client.exists(done_key)

        assert cached_data is not None, "퀴즈가 캐시되어야 함"
        assert done_exists, "done 플래그가 설정되어야 함"

    async def test_pre_generate_quiz_respects_done_flag(self, redis_client):
        """done 플래그가 있으면 중복 생성하지 않는지 테스트"""
        from api.routes.kakao_webhook import _pre_generate_evening_quiz

        user_id = "test_user_456"

        from zoneinfo import ZoneInfo
        today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
        done_key = f"evening_quiz_done:{user_id}:{today_str}"

        # done 플래그 미리 설정
        await redis_client.set(done_key, "1", ttl=86400)

        # 퀴즈 생성 시도
        await _pre_generate_evening_quiz(user_id)

        # 캐시 확인 (LLM 호출 안 됨)
        cache_key = f"evening_quiz_cache:{user_id}:{today_str}"
        cached_data = await redis_client.get(cache_key)

        # done 플래그 있으면 함수가 early return
        assert cached_data is None, "done 플래그가 있으면 퀴즈를 생성하면 안 됨"


@pytest.mark.asyncio
class TestQuizAnswerEvaluation:
    """퀴즈 답변 평가 테스트"""

    async def test_evaluate_correct_answer(self, redis_client):
        """정답 평가 테스트"""
        from api.routes.kakao_webhook import _evaluate_quiz_answer

        user_id = "test_user_789"
        today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")

        # 퀴즈 캐시 설정
        quiz_context = {
            "quiz_text": "아침에 등산하면서 본 꽃이 뭔지 얘기해줘요",
            "source_convos": "사용자: 아침에 등산 갔다 왔어요 / AI: 무슨 꽃을 보셨나요?",
            "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
        }
        cache_key = f"evening_quiz_cache:{user_id}:{today_str}"
        await redis_client.set(cache_key, json.dumps(quiz_context, ensure_ascii=False), ttl=86400)

        # Mock LLM 응답 (정답)
        with patch('api.routes.kakao_webhook.LLMService') as mock_llm:
            mock_instance = AsyncMock()
            mock_instance.call_json.return_value = {
                "relevance": 95,
                "accuracy": 90,
                "feedback": "진달래였군요"
            }
            mock_llm.return_value = mock_instance

            # 답변 평가
            is_quiz, feedback, rt_adj = await _evaluate_quiz_answer(
                user_id=user_id,
                user_answer="진달래 봤어요"
            )

        assert is_quiz is True
        assert feedback is not None
        assert rt_adj == 5  # 90점 이상이면 +5
        assert "기억력이 아주 좋으시네요" in feedback

        # 캐시 삭제 확인
        cached_data = await redis_client.get(cache_key)
        assert cached_data is None, "평가 후 캐시가 삭제되어야 함"

    async def test_evaluate_partial_answer(self, redis_client):
        """부분 정답 평가 테스트"""
        from api.routes.kakao_webhook import _evaluate_quiz_answer

        user_id = "test_user_partial"
        today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")

        quiz_context = {
            "quiz_text": "아침에 등산하면서 본 꽃이 뭔지 얘기해줘요",
            "source_convos": "사용자: 아침에 등산 갔다 왔어요",
            "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
        }
        cache_key = f"evening_quiz_cache:{user_id}:{today_str}"
        await redis_client.set(cache_key, json.dumps(quiz_context, ensure_ascii=False), ttl=86400)

        # Mock LLM 응답 (부분 정답)
        with patch('api.routes.kakao_webhook.LLMService') as mock_llm:
            mock_instance = AsyncMock()
            mock_instance.call_json.return_value = {
                "relevance": 60,
                "accuracy": 55,
                "feedback": "꽃이 참 예쁘셨겠어요"
            }
            mock_llm.return_value = mock_instance

            is_quiz, feedback, rt_adj = await _evaluate_quiz_answer(
                user_id=user_id,
                user_answer="꽃이 예쁘더라고요"
            )

        assert is_quiz is True
        assert rt_adj == 0  # 50~69점이면 0

    async def test_evaluate_incorrect_answer(self, redis_client):
        """오답 평가 테스트"""
        from api.routes.kakao_webhook import _evaluate_quiz_answer

        user_id = "test_user_incorrect"
        today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")

        quiz_context = {
            "quiz_text": "아침에 등산하면서 본 꽃이 뭔지 얘기해줘요",
            "source_convos": "사용자: 아침에 등산 갔다 왔어요",
            "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
        }
        cache_key = f"evening_quiz_cache:{user_id}:{today_str}"
        await redis_client.set(cache_key, json.dumps(quiz_context, ensure_ascii=False), ttl=86400)

        # Mock LLM 응답 (오답)
        with patch('api.routes.kakao_webhook.LLMService') as mock_llm:
            mock_instance = AsyncMock()
            mock_instance.call_json.return_value = {
                "relevance": 20,
                "accuracy": 10,
                "feedback": "다시 생각해보세요"
            }
            mock_llm.return_value = mock_instance

            is_quiz, feedback, rt_adj = await _evaluate_quiz_answer(
                user_id=user_id,
                user_answer="오늘 날씨가 좋네요"
            )

        assert is_quiz is True
        assert rt_adj == -5  # 30점 미만이면 -5
        assert "기억나시면" in feedback or "다시 얘기해 주시면" in feedback


@pytest.mark.asyncio
class TestMCDIRTAdjustment:
    """MCDI RT 점수 조정 테스트"""

    async def test_adjust_rt_positive(self):
        """RT 점수 정수 조정 테스트"""
        from api.routes.kakao_webhook import _adjust_mcdi_rt_score

        user_id = "test_user_rt_pos"

        # Mock DB session
        with patch('api.routes.kakao_webhook.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_result = Mock()
            mock_analysis = Mock()
            mock_analysis.scores = {"LR": 75, "SD": 80, "NC": 70, "TO": 75, "ER": 72, "RT": 50}
            mock_analysis.mcdi_score = 70.0
            mock_analysis.risk_level = "GREEN"
            mock_result.scalars().first.return_value = mock_analysis
            mock_db.execute.return_value = mock_result

            # RT 점수 조정
            await _adjust_mcdi_rt_score(user_id, rt_adjustment=5)

            # 점수가 조정되었는지 확인
            assert mock_analysis.scores["RT"] == 55  # 50 + 5
            assert mock_db.commit.called

    async def test_adjust_rt_negative(self):
        """RT 점수 감수 조정 테스트"""
        from api.routes.kakao_webhook import _adjust_mcdi_rt_score

        user_id = "test_user_rt_neg"

        with patch('api.routes.kakao_webhook.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_result = Mock()
            mock_analysis = Mock()
            mock_analysis.scores = {"LR": 75, "SD": 80, "NC": 70, "TO": 75, "ER": 72, "RT": 50}
            mock_analysis.mcdi_score = 70.0
            mock_analysis.risk_level = "GREEN"
            mock_result.scalars().first.return_value = mock_analysis
            mock_db.execute.return_value = mock_result

            # RT 점수 감소
            await _adjust_mcdi_rt_score(user_id, rt_adjustment=-5)

            # 점수가 조정되고 0 미만으로 내려가지 않는지 확인
            assert mock_analysis.scores["RT"] == 45  # 50 - 5
            assert mock_analysis.scores["RT"] >= 0

    async def test_adjust_rt_clamps_to_bounds(self):
        """RT 점수가 0~100 범위 내에 있는지 테스트"""
        from api.routes.kakao_webhook import _adjust_mcdi_rt_score

        user_id = "test_user_rt_clamp"

        with patch('api.routes.kakao_webhook.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_result = Mock()
            mock_analysis = Mock()
            mock_analysis.scores = {"LR": 75, "SD": 80, "NC": 70, "TO": 75, "ER": 72, "RT": 2}
            mock_analysis.mcdi_score = 70.0
            mock_analysis.risk_level = "GREEN"
            mock_result.scalars().first.return_value = mock_analysis
            mock_db.execute.return_value = mock_result

            # 큰 감수 조정
            await _adjust_mcdi_rt_score(user_id, rt_adjustment=-10)

            # 0 미만으로 내려가지 않아야 함
            assert mock_analysis.scores["RT"] == 0


@pytest.mark.asyncio
class TestQuizScheduler:
    """퀴즈 스케줄러 테스트"""

    async def test_pre_generate_quizzes_for_active_users(self):
        """활성 사용자들에게 퀴즈가 생성되는지 테스트"""
        from tasks.dialogue import pre_generate_evening_quizzes

        with patch('tasks.dialogue.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            # 활성 사용자 mock
            mock_user1 = Mock()
            mock_user1.id = "user-1"
            mock_user2 = Mock()
            mock_user2.id = "user-2"

            mock_result = Mock()
            mock_result.scalars().all.return_value = [mock_user1, mock_user2]
            mock_db.execute.return_value = mock_result

            # 퀴즈 생성 mock
            with patch('tasks.dialogue._pre_generate_evening_quiz') as mock_gen:
                mock_gen.return_value = asyncio.sleep(0)

                # 스케줄러 실행
                result = await pre_generate_evening_quizzes()

            assert result["generated"] >= 0
            assert "total" in result


@pytest.mark.asyncio
class TestQuizRedisKeys:
    """Redis 키 포맷 검증"""

    def test_redis_keys_format(self):
        """Redis 키 포맷 검증"""
        mock_time = datetime(2026, 3, 29, 18, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        today_str = mock_time.strftime("%Y-%m-%d")

        cache_key = f"evening_quiz_cache:user123:{today_str}"
        done_key = f"evening_quiz_done:user123:{today_str}"
        sent_key = f"evening_quiz_sent:user123:{today_str}"

        assert "user123" in cache_key
        assert "2026-03-29" in cache_key
        assert cache_key != done_key
        assert sent_key != done_key
        assert sent_key != cache_key


@pytest.mark.asyncio
class TestQuizIntegration:
    """통합 테스트 (간소화)"""

    async def test_full_quiz_flow_simplified(self, redis_client):
        """간단한 전체 흐름 테스트"""
        from api.routes.kakao_webhook import _pre_generate_evening_quiz, _evaluate_quiz_answer

        user_id = "integration_test_user"
        today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")

        # 1. 퀴즈 생성
        with patch('api.routes.kakao_webhook.AsyncSessionLocal') as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db

            mock_conv = Mock()
            mock_conv.message = "아침에 산책 갔다 왔어요"
            mock_conv.response = "어디를 가셨나요?"
            mock_conv.category = "DAILY_EPISODIC"

            mock_result = Mock()
            mock_result.scalars().all.return_value = [mock_conv]
            mock_db.execute.return_value = mock_result

            with patch('api.routes.kakao_webhook.LLMService') as mock_llm:
                mock_instance = AsyncMock()
                mock_instance.call.return_value = "아침에 산책하면서 본 게 뭔지 얘기해줘요"
                mock_llm.return_value = mock_instance

                await _pre_generate_evening_quiz(user_id)

        # 2. 캐시 확인
        cache_key = f"evening_quiz_cache:{user_id}:{today_str}"
        cached_data = await redis_client.get(cache_key)
        assert cached_data is not None

        # 3. 답변 평가
        with patch('api.routes.kakao_webhook.LLMService') as mock_llm:
            mock_instance = AsyncMock()
            mock_instance.call_json.return_value = {
                "relevance": 85,
                "accuracy": 80,
                "feedback": "벚꽃이었군요"
            }
            mock_llm.return_value = mock_instance

            is_quiz, feedback, rt_adj = await _evaluate_quiz_answer(
                user_id=user_id,
                user_answer="벚꽃이 핀 거 봤어요"
            )

        assert is_quiz is True
        assert rt_adj == 2  # 70~89점이면 +2
        assert "벚꽃이었군요" in feedback

        # 4. 캐시 삭제 확인
        cached_data = await redis_client.get(cache_key)
        assert cached_data is None


# Fixtures
@pytest.fixture
def redis_client():
    """Redis 클라이언트"""
    from database.redis_client import redis_client
    return redis_client
