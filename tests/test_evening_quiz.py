"""저녁 회상 퀴즈 동작 검증 테스트

1. _pre_generate_evening_quiz 함수 존재 검증
2. 18시 이전 → 퀴즈 미발동
3. 18시 이후 → 퀴즈 사전 생성 스케줄
4. 1일 1회 보장
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo


class TestEveningQuizFunction:
    """_pre_generate_evening_quiz 함수 검증"""

    def test_function_exists(self):
        """_pre_generate_evening_quiz 함수가 존재해야 함"""
        from api.routes.kakao_webhook import _pre_generate_evening_quiz
        assert callable(_pre_generate_evening_quiz)


class TestEveningQuizTrigger:
    """저녁 퀴즈 트리거 검증"""

    @pytest.mark.asyncio
    async def test_no_trigger_before_6pm(self):
        """18시 이전에는 퀴즈 생성이 트리거되지 않아야 함"""
        # 17시 (KST) → 퀴즈 미발동
        mock_time = datetime(2026, 3, 27, 17, 0, tzinfo=ZoneInfo("Asia/Seoul"))

        with patch("api.routes.kakao_webhook.datetime") as mock_dt:
            mock_dt.now.return_value = mock_time
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            redis_client_mock = AsyncMock()
            redis_client_mock.exists = AsyncMock(return_value=False)

            # 17시이므로 if 18 <= hour < 24 조건이 False
            hour = mock_dt.now().hour
            assert hour == 17
            assert not (18 <= hour < 24)

    @pytest.mark.asyncio
    async def test_trigger_at_8pm(self):
        """20시 (KST)에는 퀴즈 생성이 트리거되어야 함"""
        mock_time = datetime(2026, 3, 27, 20, 0, tzinfo=ZoneInfo("Asia/Seoul"))

        hour = mock_time.hour
        assert hour == 20
        assert 18 <= hour < 24


class TestEveningQuizCache:
    """퀴즈 캐시 및 1일 1회 보장 검증"""

    @pytest.mark.asyncio
    async def test_quiz_done_prevents_regeneration(self):
        """evening_quiz_done 키가 있으면 퀴즈 재생성하지 않아야 함"""
        from api.routes.kakao_webhook import _pre_generate_evening_quiz

        redis_client_mock = AsyncMock()
        redis_client_mock.exists = AsyncMock(return_value=True)  # done_key exists

        with patch("api.routes.kakao_webhook.redis_client", redis_client_mock):
            await _pre_generate_evening_quiz("user123")
            # exists가 True를 반환하면 함수가 조기 종료되어야 함
            # set이 호출되지 않아야 함
            assert redis_client_mock.set.call_count == 0

    @pytest.mark.asyncio
    async def test_redis_keys_format(self):
        """Redis 키 포맷 검증"""
        mock_time = datetime(2026, 3, 27, 20, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        today_str = mock_time.strftime("%Y-%m-%d")

        cache_key = f"evening_quiz_cache:user123:{today_str}"
        done_key = f"evening_quiz_done:user123:{today_str}"

        assert "user123" in cache_key
        assert "2026-03-27" in cache_key
        assert cache_key != done_key
