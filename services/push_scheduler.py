"""
푸시 알림 스케줄러

일일 정해진 시간에 자동으로 푸시 알림 전송.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from database.postgres import AsyncSessionLocal
from database.models import User, FCMToken
from services.firebase_service import get_firebase_service
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class PushScheduler:
    """
    푸시 알림 스케줄러

    Features:
        - 일일 3회 자동 발송 (오전 10시, 오후 3시, 저녁 8시)
        - 사용자별 활성 토큰 관리
        - 실패한 토큰 자동 비활성화
        - 발송 통계 로깅
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.firebase_service = get_firebase_service()

    def start(self):
        """스케줄러 시작"""
        try:
            # 일일 3회 스케줄 등록
            # 오전 10시
            self.scheduler.add_job(
                self.send_morning_prompt,
                trigger=CronTrigger(hour=10, minute=0),
                id="morning_prompt",
                name="오전 정원 가꾸기 알림",
                replace_existing=True
            )

            # 오후 3시
            self.scheduler.add_job(
                self.send_afternoon_prompt,
                trigger=CronTrigger(hour=15, minute=0),
                id="afternoon_prompt",
                name="오후 정원 가꾸기 알림",
                replace_existing=True
            )

            # 저녁 8시
            self.scheduler.add_job(
                self.send_evening_prompt,
                trigger=CronTrigger(hour=20, minute=0),
                id="evening_prompt",
                name="저녁 정원 가꾸기 알림",
                replace_existing=True
            )

            self.scheduler.start()
            logger.info("✅ Push notification scheduler started")
            logger.info("📅 Scheduled jobs:")
            logger.info("   - 오전 10:00 - 아침 인사 및 어제 회상")
            logger.info("   - 오후 15:00 - 오후 체크 및 대화")
            logger.info("   - 저녁 20:00 - 하루 마무리 회상")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            raise

    def shutdown(self):
        """스케줄러 종료"""
        try:
            self.scheduler.shutdown()
            logger.info("Push notification scheduler shut down")
        except Exception as e:
            logger.error(f"Failed to shutdown scheduler: {e}", exc_info=True)

    async def send_morning_prompt(self):
        """오전 10시 - 아침 인사 및 어제 회상"""
        await self._send_prompt(
            title="Memory Garden 🌱",
            body="좋은 아침입니다! 어제 저녁은 무엇을 드셨나요?",
            prompt_type="morning"
        )

    async def send_afternoon_prompt(self):
        """오후 3시 - 오후 체크"""
        await self._send_prompt(
            title="Memory Garden 🌿",
            body="오후 시간입니다. 점심은 어떤 것을 드셨나요?",
            prompt_type="afternoon"
        )

    async def send_evening_prompt(self):
        """저녁 8시 - 하루 마무리"""
        await self._send_prompt(
            title="Memory Garden 🌳",
            body="하루를 마무리하며, 오늘 기억에 남는 일이 있나요?",
            prompt_type="evening"
        )

    async def _send_prompt(self, title: str, body: str, prompt_type: str):
        """
        푸시 알림 전송 (내부 메서드)

        Args:
            title: 알림 제목
            body: 알림 내용
            prompt_type: 프롬프트 타입 (morning/afternoon/evening)
        """
        start_time = datetime.now()
        total_users = 0
        total_sent = 0
        total_failed = 0

        async with AsyncSessionLocal() as db:
            try:
                # 활성 사용자 조회
                result = await db.execute(
                    select(User).where(User.is_active == True)
                )
                users = result.scalars().all()
                total_users = len(users)

                logger.info(
                    f"🔔 Starting {prompt_type} prompt for {total_users} users"
                )

                # 각 사용자에게 전송
                for user in users:
                    try:
                        # 사용자의 활성 토큰 조회
                        result = await db.execute(
                            select(FCMToken)
                            .where(FCMToken.user_id == user.id)
                            .where(FCMToken.is_active == True)
                        )
                        tokens = result.scalars().all()

                        if not tokens:
                            logger.debug(f"No active tokens for user: {user.id}")
                            continue

                        # 각 토큰에 전송
                        for token in tokens:
                            try:
                                await self.firebase_service.send_push_notification(
                                    token=token.token,
                                    title=title,
                                    body=body,
                                    deep_link=settings.KAKAO_CHANNEL_DEEP_LINK,
                                    data={
                                        "prompt_type": prompt_type,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                )

                                # 성공 - last_used_at 업데이트
                                token.last_used_at = datetime.now()
                                total_sent += 1

                            except Exception as e:
                                logger.error(
                                    f"Failed to send to token {token.id}: {e}"
                                )
                                total_failed += 1

                                # 토큰 무효화 (unregistered 에러)
                                if "unregistered" in str(e).lower():
                                    token.is_active = False
                                    logger.info(
                                        f"Token {token.id} marked as inactive"
                                    )

                    except Exception as e:
                        logger.error(
                            f"Failed to process user {user.id}: {e}",
                            exc_info=True
                        )
                        total_failed += 1

                # 변경사항 커밋
                await db.commit()

                # 통계 로깅
                elapsed_time = (datetime.now() - start_time).total_seconds()

                logger.info(
                    f"✅ {prompt_type.capitalize()} prompt completed",
                    extra={
                        "prompt_type": prompt_type,
                        "total_users": total_users,
                        "sent_count": total_sent,
                        "failed_count": total_failed,
                        "elapsed_seconds": round(elapsed_time, 2)
                    }
                )

            except Exception as e:
                logger.error(
                    f"Prompt send failed: {e}",
                    extra={"prompt_type": prompt_type},
                    exc_info=True
                )
                await db.rollback()

    async def send_immediate_prompt(
        self,
        user_ids: List[str],
        title: str,
        body: str,
        deep_link: str = None
    ):
        """
        즉시 푸시 알림 전송 (수동 트리거용)

        Args:
            user_ids: 사용자 ID 리스트
            title: 알림 제목
            body: 알림 내용
            deep_link: 딥링크 URL

        Returns:
            {"sent_count": 5, "failed_count": 1}

        Example:
            >>> scheduler = PushScheduler()
            >>> await scheduler.send_immediate_prompt(
            ...     user_ids=["user_1", "user_2"],
            ...     title="긴급 알림",
            ...     body="중요한 메시지입니다"
            ... )
        """
        sent_count = 0
        failed_count = 0

        async with AsyncSessionLocal() as db:
            try:
                from uuid import UUID

                for user_id in user_ids:
                    try:
                        user_uuid = UUID(user_id)

                        # 사용자의 활성 토큰 조회
                        result = await db.execute(
                            select(FCMToken)
                            .where(FCMToken.user_id == user_uuid)
                            .where(FCMToken.is_active == True)
                        )
                        tokens = result.scalars().all()

                        # 각 토큰에 전송
                        for token in tokens:
                            try:
                                await self.firebase_service.send_push_notification(
                                    token=token.token,
                                    title=title,
                                    body=body,
                                    deep_link=deep_link or settings.KAKAO_CHANNEL_DEEP_LINK
                                )

                                token.last_used_at = datetime.now()
                                sent_count += 1

                            except Exception as e:
                                logger.error(f"Failed to send: {e}")
                                failed_count += 1

                                if "unregistered" in str(e).lower():
                                    token.is_active = False

                    except Exception as e:
                        logger.error(f"User processing failed: {e}")
                        failed_count += 1

                await db.commit()

                return {
                    "sent_count": sent_count,
                    "failed_count": failed_count
                }

            except Exception as e:
                logger.error(f"Immediate prompt failed: {e}", exc_info=True)
                await db.rollback()
                raise


# ============================================
# 싱글톤 인스턴스
# ============================================

_push_scheduler: PushScheduler = None


def get_push_scheduler() -> PushScheduler:
    """
    PushScheduler 싱글톤 인스턴스 가져오기

    Returns:
        PushScheduler 인스턴스
    """
    global _push_scheduler

    if _push_scheduler is None:
        _push_scheduler = PushScheduler()

    return _push_scheduler
