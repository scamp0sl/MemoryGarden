"""시간 주입 (KST) 검증 테스트"""

import pytest
from zoneinfo import ZoneInfo
from datetime import datetime
from unittest.mock import patch
from core.dialogue.prompt_builder import PromptBuilder, SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_prompt_contains_current_time():
    """프롬프트에 현재 시간(HH:MM)과 시간대(오전/오후/저녁)이 포함되어야 함"""
    pb = PromptBuilder()
    KST = ZoneInfo("Asia/Seoul")
    # 15:30 테스트
    with patch('core.dialogue.prompt_builder.datetime') as mock_dt:
        test_time = datetime(2026, 3, 27, 15, 30, tzinfo=KST)
        mock_dt.now.return_value = test_time
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw, tzinfo=KST) if not kw.get('tzinfo') else datetime(*a, **kw)

        prompt = await pb.build_system_prompt()
        assert "15시" in prompt or "15시 30분" in prompt
        assert "오후" in prompt
        assert "2026년 3월 27일" in prompt


@pytest.mark.asyncio
async def test_prompt_prevents_morning_greeting_in_afternoon():
    """오후 시간에 '좋은 아침'이 오면 시간 어긋남 안내 포함"""
    pb = PromptBuilder()
    KST = ZoneInfo("Asia/Seoul")
    with patch('core.dialogue.prompt_builder.datetime') as mock_dt:
        test_time = datetime(2026, 3, 27, 16, 34, tzinfo=KST)
        mock_dt.now.return_value = test_time
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw, tzinfo=KST) if not kw.get('tzinfo') else datetime(*a, **kw)

        prompt = await pb.build_system_prompt()
        # 시간 어긋남 안내 포함
        assert "어긋나면" in prompt or "현재" in prompt
        assert "16시" in prompt
        assert "오후" in prompt


@pytest.mark.asyncio
async def test_prompt_uses_kst():
    """KST (Asia/Seoul) 기준으로 시간 표시"""
    pb = PromptBuilder()
    with patch('core.dialogue.prompt_builder.datetime') as mock_dt:
        KST = ZoneInfo("Asia/Seoul")
        test_time = datetime(2026, 3, 27, 9, 5, tzinfo=KST)
        mock_dt.now.return_value = test_time
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw, tzinfo=KST) if not kw.get('tzinfo') else datetime(*a, **kw)

        prompt = await pb.build_system_prompt()
        assert "9시" in prompt
        assert "오전" in prompt
