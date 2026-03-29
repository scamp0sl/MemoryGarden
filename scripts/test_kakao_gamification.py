import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Mock definitions before imports to avoid side effects
import sys
from types import ModuleType

# Create dummy modules if needed or mock specific components
from api.routes.kakao_webhook import _build_kakao_response, ACHIEVEMENTS_CONFIG
from core.analysis.garden_mapper import GardenStatusUpdate, GardenVisualizationData, GardenWeather

class TestKakaoGamification(unittest.IsolatedAsyncioTestCase):
    
    def test_build_kakao_response_single(self):
        """텍스트 응답 하나만 있을 때 기존 하위 호환성 확인"""
        res = _build_kakao_response(["안녕하세요"])
        self.assertEqual(res["template"]["outputs"][0]["simpleText"]["text"], "안녕하세요")
        
    def test_build_kakao_response_multiple(self):
        """카드 + 텍스트 복합 응답 확인"""
        card = {"basicCard": {"title": "축하합니다"}}
        res = _build_kakao_response([card, "감사합니다"])
        self.assertEqual(len(res["template"]["outputs"]), 2)
        self.assertEqual(res["template"]["outputs"][0]["basicCard"]["title"], "축하합니다")
        self.assertEqual(res["template"]["outputs"][1]["simpleText"]["text"], "감사합니다")

    @patch("core.analysis.garden_mapper.GardenMapper")
    @patch("api.routes.kakao_webhook.get_dialogue_manager")
    @patch("api.routes.kakao_webhook._get_or_create_user")
    async def test_webhook_with_achievement(self, mock_get_user, mock_get_dm, mock_garden_mapper_cls):
        """업적 달성 시 웹훅이 카드를 포함하는지 확인"""
        from api.routes.kakao_webhook import kakao_webhook
        
        # 1. Setup Mock User
        mock_user = MagicMock()
        mock_user.id = "test-uuid"
        mock_user.onboarding_day = 20
        mock_user.kakao_access_token = "token"
        mock_get_user.return_value = (mock_user, False, False)
        
        # 2. Setup Mock DM
        mock_dm = AsyncMock()
        mock_dm.generate_response.return_value = "오늘 기분은 어떠세요?"
        mock_dm.get_last_conversation_mode.return_value = "normal"
        mock_get_dm.return_value = mock_dm
        
        # 3. Setup Mock GardenMapper (Achievement: butterfly_visit)
        mock_mapper = AsyncMock()
        mock_garden_mapper_cls.return_value = mock_mapper
        
        viz_data = GardenVisualizationData(
            user_id="test-uuid",
            flower_count=10,
            butterfly_count=1,
            garden_level=1,
            consecutive_days=3,
            total_conversations=10,
            weather=GardenWeather.SUNNY,
            status_message="맑음",
            next_milestone="7일 연속 대화하기"
        )
        
        mock_update = GardenStatusUpdate(
            previous_status=viz_data,
            current_status=viz_data,
            achievements_unlocked=["butterfly_visit"],
            level_up=False
        )
        mock_mapper.update_garden_status.return_value = mock_update
        
        # 4. Execute Webhook
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "userRequest": {
                "utterance": "안녕",
                "user": {"id": "bot-key", "properties": {"plusfriendUserKey": "user-key"}}
            }
        })
        
        mock_bg_tasks = MagicMock()
        mock_db = AsyncMock()
        
        response = await kakao_webhook(mock_request, mock_bg_tasks, mock_db)
        
        # 5. Verify Response
        outputs = response["template"]["outputs"]
        self.assertEqual(len(outputs), 2)
        # First output should be basicCard (achievement)
        self.assertIn("basicCard", outputs[0])
        self.assertEqual(outputs[0]["basicCard"]["title"], ACHIEVEMENTS_CONFIG["butterfly_visit"]["title"])
        self.assertIn("(다음 목표: 7일 연속 대화하기)", outputs[0]["basicCard"]["description"])
        # Second output should be simpleText (AI response)
        self.assertEqual(outputs[1]["simpleText"]["text"], "오늘 기분은 어떠세요?")

if __name__ == "__main__":
    unittest.main()
