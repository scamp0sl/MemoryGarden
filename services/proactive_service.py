"""Proactive Messaging Service (C5)

36시간 이상 비활성 사용자에게 자동으로 메시지 발송
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import select
from database.models import User
from database.redis_client import redis_client
from database.postgres import AsyncSessionLocal
from services.kakao_client import KakaoClient
from utils.logger import get_logger

logger = get_logger(__name__)


class ProactiveService:
    """Proactive 메시징 서비스"""

    INACTIVE_THRESHOLD_HOURS = 36
    SENDING_START_HOUR = 9
    SENDING_END_HOUR = 21

    async def get_inactive_users(self, hours: int = 36) -> List[dict]:
        """비활성 사용자 조회

        [결함 #13 수정] User.is_active → User.deleted_at == None 사용
        (User 모델에 is_active 필드 없음, models.py 확인 완료)
        """
        inactive_list = []
        threshold = datetime.now() - timedelta(hours=hours)

        async with AsyncSessionLocal() as session:
            # [결함 #13] deleted_at == None으로 활성 사용자 필터
            stmt = select(User).where(
                User.deleted_at == None,
                User.last_interaction_at < threshold
            )
            result = await session.execute(stmt)
            users = result.scalars().all()

            for user in users:
                if user.last_interaction_at:
                    hours_since = (datetime.now() - user.last_interaction_at).total_seconds() / 3600
                    inactive_list.append({
                        "user_id": str(user.id),
                        "kakao_id": user.kakao_id,
                        "last_interaction": user.last_interaction_at.isoformat(),
                        "hours_since": round(hours_since, 1)
                    })

            logger.info(f"Found {len(inactive_list)} inactive users ({hours}h+)")
            return inactive_list

    async def generate_proactive_message(self, user_context: dict) -> str:
        """Proactive 메시지 생성"""
        hours_since = user_context.get("hours_since", 36)

        if hours_since < 48:
            templates = [
                "안녕하세요 ㅎㅎ 오늘 하루는 어떻게 지내고 계세요?",
                "오늘 날씨가 추워진 것 같아요. 따뜻하게 지내고 계시나요?",
                "오랜만에 인사드려요 ㅎㅎ 별일 없으신가요?"
            ]
        elif hours_since < 72:
            templates = [
                "안녕하세요 ㅎㅎ 어떻게 지내고 계셔는지 궁금해요.",
                "오늘은 어떤 일 하고 계세요? ㅎㅎ",
                "혹시 우리 정원, 가끔 생각나시나요 ㅎㅎ"
            ]
        else:
            templates = [
                "안녕하세요... 정말 오랜만이네요 ㅠㅠ",
                "혹시 무슨 일 있으신 건 아닌지 저도 좀 걱정이 되고요.",
                "저 기다리고 있어요 ㅠㅠ 편할 때 연락 주세요 ㅎㅎ"
            ]

        import random
        return random.choice(templates)

    async def send_proactive_message(self, user_id: str) -> dict:
        """특정 사용자에게 Proactive 메시지 발송

        [결함 #2-3, #12 수정] 카카오 API 파라미터 교차 검증 완료
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

        context = {"user_id": str(user.id), "hours_since": 36.0}
        message = await self.generate_proactive_message(context)

        kakao_client = KakaoClient()

        # [결함 #2, #12 수정] kakao_access_token 사용 (NOT oauth_access_token)
        if user.kakao_access_token:  # [결함 #12] 필드명 수정
            result = await kakao_client.send_to_me(
                access_token=user.kakao_access_token,
                message=message
            )
            method = "oauth"
        elif user.kakao_channel_user_key:
            result = await kakao_client.send_bizmessage_friend_talk(
                plus_friend_user_key=user.kakao_channel_user_key,
                message=message
            )
            method = "channel"
        else:
            return {"success": False, "error": "No messaging method available"}

        if result.get("success"):
            logger.info(f"Proactive message sent via {method}", extra={"user_id": user_id})

        return {
            "success": result.get("success", False),
            "method": method,
            "message": message,
            "result_code": result.get("result_code")
        }

    async def send_batch_proactive_messages(self, limit: int = 10) -> dict:
        """비활성 사용자에게 일괄 Proactive 메시지 발송"""
        now_hour = datetime.now().hour
        if not (self.SENDING_START_HOUR <= now_hour <= self.SENDING_END_HOUR):
            logger.info(f"Outside sending hours ({now_hour}), skipping")
            return {"total": 0, "sent": 0, "skipped": True}

        inactive_users = await self.get_inactive_users()
        if not inactive_users:
            return {"total": 0, "sent": 0}

        results = []
        sent_count = 0
        failed_count = 0

        for user_context in inactive_users[:limit]:
            result = await self.send_proactive_message(user_context["user_id"])
            results.append({"user_id": user_context["user_id"], "result": result})

            if result.get("success"):
                sent_count += 1
            else:
                failed_count += 1

            await asyncio.sleep(0.5)

        logger.info(f"Proactive batch completed: {sent_count}/{len(inactive_users[:limit])} sent")

        return {
            "total": len(inactive_users[:limit]),
            "sent": sent_count,
            "failed": failed_count,
            "results": results
        }
