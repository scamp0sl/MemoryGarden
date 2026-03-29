"""
대화 스케줄러

APScheduler를 사용하여 일일 3회 자동 대화 시작.
사용자별 최적 시간대 학습 기능 포함 (향후 구현).

Author: Memory Garden Team
Created: 2025-02-24
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from datetime import datetime, time
from typing import Dict, List, Optional, Any
import asyncio

# ============================================
# 2. Third-Party Imports
# ============================================
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings
from database.redis_client import redis_client
from utils.logger import get_logger
from utils.exceptions import MemoryGardenError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
DEFAULT_SCHEDULE_TIMES = [
    time(10, 0),  # 10:00 AM
    time(15, 0),  # 3:00 PM
    time(20, 0),  # 8:00 PM
]

TIMEZONE = "Asia/Seoul"


# ============================================
# 6. 예외 정의
# ============================================
class SchedulerError(MemoryGardenError):
    """스케줄러 관련 예외"""
    pass


# ============================================
# 7. DialogueScheduler 클래스
# ============================================
class DialogueScheduler:
    """
    대화 스케줄러

    일일 3회 자동 대화를 스케줄링하고 관리합니다.

    Attributes:
        scheduler: APScheduler 인스턴스
        is_running: 스케줄러 실행 상태

    Example:
        >>> scheduler = DialogueScheduler()
        >>> await scheduler.start()
        >>> await scheduler.add_user_schedule("user123")
        >>> await scheduler.stop()
    """

    def __init__(self):
        """스케줄러 초기화"""
        # REDIS_URL 파싱 (redis://localhost:6379 형식)
        from urllib.parse import urlparse

        redis_url = settings.REDIS_URL
        parsed = urlparse(redis_url)

        redis_host = parsed.hostname or "localhost"
        redis_port = parsed.port or 6379
        redis_password = parsed.password or None

        # APScheduler 설정
        jobstores = {
            'default': RedisJobStore(
                host=redis_host,
                port=redis_port,
                db=1,  # DB 1 사용 (메인과 분리)
                password=redis_password
            )
        }

        executors = {
            'default': AsyncIOExecutor()
        }

        job_defaults = {
            'coalesce': True,  # 누락된 작업 병합
            'max_instances': 3,  # 동시 실행 최대 3개
            'misfire_grace_time': 300  # 5분 이내 누락은 실행
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=TIMEZONE
        )

        self.is_running = False

        logger.info("DialogueScheduler initialized")

    async def start(self) -> None:
        """
        스케줄러 시작

        Raises:
            SchedulerError: 이미 실행 중이거나 시작 실패 시
        """
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        try:
            self.scheduler.start()
            self.is_running = True
            logger.info("✅ Scheduler started successfully")

            # C5: Proactive Messaging 스케줄 등록
            await self._register_proactive_messaging_job()

            # 현재 등록된 작업 수 로깅
            jobs = self.scheduler.get_jobs()
            logger.info(f"📋 Currently scheduled jobs: {len(jobs)}")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            raise SchedulerError(f"Scheduler start failed: {e}") from e

    async def _register_proactive_messaging_job(self) -> None:
        """C5: Proactive Messaging 스케줄 등록

        매일 10시, 15시, 20시에 비활성 사용자에게 메시지 발송
        """
        try:
            from tasks.dialogue import send_proactive_messages

            trigger_times = ["10:00", "15:00", "20:00"]

            for time_str in trigger_times:
                hour, minute = map(int, time_str.split(':'))

                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone=TIMEZONE
                )

                job_id = f"proactive_messaging_{time_str.replace(':', '')}"

                # 기존 작업 확인 후 추가
                existing_job = self.scheduler.get_job(job_id)
                if existing_job is None:
                    self.scheduler.add_job(
                        func=send_proactive_messages,
                        trigger=trigger,
                        id=job_id,
                        name=f"Proactive messaging at {time_str}",
                        replace_existing=True
                    )
                    logger.info(f"✅ Registered proactive messaging job at {time_str}")
                else:
                    logger.debug(f"Proactive messaging job already exists at {time_str}")

        except Exception as e:
            logger.error(f"Failed to register proactive messaging job: {e}", exc_info=True)

    async def stop(self) -> None:
        """
        스케줄러 정지

        Raises:
            SchedulerError: 정지 실패 시
        """
        if not self.is_running:
            logger.warning("Scheduler not running")
            return

        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("⏹️ Scheduler stopped successfully")

        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}", exc_info=True)
            raise SchedulerError(f"Scheduler stop failed: {e}") from e

    async def add_user_schedule(
        self,
        user_id: str,
        schedule_times: Optional[List[time]] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        사용자 스케줄 추가

        Args:
            user_id: 사용자 ID
            schedule_times: 커스텀 시간대 (None이면 기본값 사용)
            enabled: 활성화 여부

        Returns:
            {
                "user_id": "user123",
                "schedule_times": ["10:00", "15:00", "20:00"],
                "job_ids": ["user123_10:00", "user123_15:00", "user123_20:00"],
                "enabled": True
            }

        Raises:
            SchedulerError: 스케줄 추가 실패 시

        Example:
            >>> scheduler = DialogueScheduler()
            >>> result = await scheduler.add_user_schedule("user123")
            >>> print(result["job_ids"])
            ["user123_10:00", "user123_15:00", "user123_20:00"]
        """
        try:
            # 기본값 사용
            times = schedule_times or DEFAULT_SCHEDULE_TIMES

            # 기존 스케줄 제거 (중복 방지)
            await self.remove_user_schedule(user_id)

            job_ids = []

            for schedule_time in times:
                job_id = f"{user_id}_{schedule_time.strftime('%H:%M')}"

                # Cron 트리거 생성 (매일 해당 시간)
                trigger = CronTrigger(
                    hour=schedule_time.hour,
                    minute=schedule_time.minute,
                    timezone=TIMEZONE
                )

                # tasks/dialogue.py의 독립 함수 사용 (pickle 가능)
                from tasks.dialogue import send_scheduled_dialogue

                # 작업 추가
                self.scheduler.add_job(
                    func=send_scheduled_dialogue,
                    trigger=trigger,
                    args=[user_id],
                    id=job_id,
                    name=f"Daily dialogue for {user_id} at {schedule_time.strftime('%H:%M')}",
                    replace_existing=True
                )

                job_ids.append(job_id)

                logger.info(
                    f"✅ Scheduled dialogue for {user_id} at {schedule_time.strftime('%H:%M')}",
                    extra={"job_id": job_id}
                )

            # Redis에 스케줄 정보 저장
            schedule_data = {
                "user_id": user_id,
                "schedule_times": [t.strftime("%H:%M") for t in times],
                "job_ids": job_ids,
                "enabled": enabled,
                "created_at": datetime.now().isoformat()
            }

            await redis_client.set_json(
                f"schedule:{user_id}",
                schedule_data,
                ttl=None  # 영구 저장
            )

            return schedule_data

        except Exception as e:
            logger.error(f"Failed to add schedule for {user_id}: {e}", exc_info=True)
            raise SchedulerError(f"Add schedule failed: {e}") from e

    async def remove_user_schedule(self, user_id: str) -> bool:
        """
        사용자 스케줄 제거

        Args:
            user_id: 사용자 ID

        Returns:
            제거 성공 여부

        Example:
            >>> scheduler = DialogueScheduler()
            >>> success = await scheduler.remove_user_schedule("user123")
        """
        try:
            # Redis에서 스케줄 정보 조회
            schedule_data = await redis_client.get_json(f"schedule:{user_id}")

            if not schedule_data:
                logger.info(f"No schedule found for {user_id}")
                return False

            # 모든 작업 제거
            removed_count = 0
            for job_id in schedule_data.get("job_ids", []):
                try:
                    self.scheduler.remove_job(job_id)
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove job {job_id}: {e}")

            # Redis에서 스케줄 정보 삭제
            await redis_client.delete(f"schedule:{user_id}")

            logger.info(
                f"✅ Removed {removed_count} scheduled jobs for {user_id}",
                extra={"removed_count": removed_count}
            )

            return True

        except Exception as e:
            logger.error(f"Failed to remove schedule for {user_id}: {e}", exc_info=True)
            return False

    async def get_user_schedule(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 스케줄 조회

        Args:
            user_id: 사용자 ID

        Returns:
            스케줄 정보 또는 None

        Example:
            >>> scheduler = DialogueScheduler()
            >>> schedule = await scheduler.get_user_schedule("user123")
            >>> print(schedule["schedule_times"])
            ["10:00", "15:00", "20:00"]
        """
        try:
            schedule_data = await redis_client.get_json(f"schedule:{user_id}")
            return schedule_data

        except Exception as e:
            logger.error(f"Failed to get schedule for {user_id}: {e}")
            return None

    async def list_all_schedules(self) -> List[Dict[str, Any]]:
        """
        모든 스케줄 목록 조회

        Returns:
            스케줄 목록

        Example:
            >>> scheduler = DialogueScheduler()
            >>> schedules = await scheduler.list_all_schedules()
            >>> print(f"Total users: {len(schedules)}")
        """
        try:
            # Redis에서 모든 schedule:* 키 검색
            keys = await redis_client.keys("schedule:*")

            schedules = []
            for key in keys:
                schedule_data = await redis_client.get_json(key)
                if schedule_data:
                    schedules.append(schedule_data)

            logger.info(f"Retrieved {len(schedules)} schedules")
            return schedules

        except Exception as e:
            logger.error(f"Failed to list schedules: {e}", exc_info=True)
            return []

    async def _send_scheduled_message(self, user_id: str) -> None:
        """
        스케줄된 메시지 전송 (내부 메서드)

        Args:
            user_id: 사용자 ID

        Note:
            실제 구현은 tasks/dialogue.py에서 import
        """
        try:
            logger.info(f"📨 Sending scheduled message to {user_id}")

            # tasks/dialogue.py의 함수 import (순환 참조 방지)
            from tasks.dialogue import send_scheduled_dialogue

            # 비동기 함수 실행
            await send_scheduled_dialogue(user_id)

        except Exception as e:
            logger.error(
                f"Failed to send scheduled message to {user_id}: {e}",
                exc_info=True
            )

    def get_next_run_time(self, user_id: str) -> Optional[datetime]:
        """
        다음 실행 시간 조회

        Args:
            user_id: 사용자 ID

        Returns:
            다음 실행 시간 또는 None

        Example:
            >>> scheduler = DialogueScheduler()
            >>> next_time = scheduler.get_next_run_time("user123")
            >>> print(f"Next dialogue at: {next_time}")
        """
        try:
            jobs = self.scheduler.get_jobs()
            user_jobs = [job for job in jobs if job.id.startswith(f"{user_id}_")]

            if not user_jobs:
                return None

            # 가장 가까운 실행 시간 반환
            next_times = [job.next_run_time for job in user_jobs if job.next_run_time]

            if not next_times:
                return None

            return min(next_times)

        except Exception as e:
            logger.error(f"Failed to get next run time for {user_id}: {e}")
            return None


# ============================================
# 8. 싱글톤 인스턴스
# ============================================
_scheduler_instance: Optional[DialogueScheduler] = None


def get_scheduler() -> DialogueScheduler:
    """
    DialogueScheduler 싱글톤 인스턴스 반환

    Returns:
        DialogueScheduler 인스턴스

    Example:
        >>> scheduler = get_scheduler()
        >>> await scheduler.start()
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        _scheduler_instance = DialogueScheduler()
        logger.info("🏗️ DialogueScheduler singleton created")

    return _scheduler_instance
