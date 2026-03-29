import asyncio
import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo
from core.dialogue.prompt_builder import PromptBuilder

class TestTemporalLogic(unittest.TestCase):
    def setUp(self):
        self.builder = PromptBuilder()

    async def _get_prompt(self, mock_now):
        with patch('core.dialogue.prompt_builder.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)
            return await self.builder.build_system_prompt()

    def test_morning_logic(self):
        mock_now = datetime(2026, 3, 25, 10, 0, tzinfo=ZoneInfo('Asia/Seoul'))
        prompt = asyncio.get_event_loop().run_until_complete(self._get_prompt(mock_now))

        self.assertIn("지금은 **아침** 시간대입니다", prompt)
        self.assertIn("**골든 룰:** 사용자의 인사(예: '좋은 아침', '안녕')가 현재 시간대(아침)와 일치하면 절대 시간을 지적하지 마세요", prompt)
        self.assertIn("엥? 지금 아침인데 혹시 피곤해서 낮밤이 바뀌셨어요?", prompt)

    def test_afternoon_logic(self):
        mock_now = datetime(2026, 3, 25, 14, 0, tzinfo=ZoneInfo('Asia/Seoul'))
        prompt = asyncio.get_event_loop().run_until_complete(self._get_prompt(mock_now))

        self.assertIn("지금은 **오후** 시간대입니다", prompt)
        self.assertIn("**골든 룰:** 사용자의 인사(예: '좋은 아침', '안녕')가 현재 시간대(오후)와 일치하면 절대 시간을 지적하지 마세요", prompt)
        self.assertIn("엥? 지금 오후인데 혹시 피곤해서 낮밤이 바뀌셨어요?", prompt)

    def test_evening_logic(self):
        mock_now = datetime(2026, 3, 25, 20, 0, tzinfo=ZoneInfo('Asia/Seoul'))
        prompt = asyncio.get_event_loop().run_until_complete(self._get_prompt(mock_now))

        self.assertIn("지금은 **저녁** 시간대입니다", prompt)
        self.assertIn("엥? 지금 저녁인데 혹시 피곤해서 낮밤이 바뀌셨어요?", prompt)

    def test_night_logic(self):
        mock_now = datetime(2026, 3, 25, 23, 0, tzinfo=ZoneInfo('Asia/Seoul'))
        prompt = asyncio.get_event_loop().run_until_complete(self._get_prompt(mock_now))

        self.assertIn("지금은 **밤** 시간대입니다", prompt)
        self.assertIn("엥? 지금 밤인데 혹시 피곤해서 낮밤이 바뀌셨어요?", prompt)

if __name__ == '__main__':
    unittest.main()
