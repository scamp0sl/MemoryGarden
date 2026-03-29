"""
중도 이탈 방지 모니터링 태스크

24시간 이상 비활성 사용자를 감지하여 단계별 재참여 메시지를 전송합니다.
SPEC §2.4.4 기반 구현.

재참여 단계:
    Day 1: 가벼운 인사 메시지
    Day 3: 걱정 메시지 + 정원 현황 공유
    Day 7: 가족 알림 (보호자에게도 통보)

Author: Memory Garden Team
Created: 2026-02-27
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from datetime import datetime, timedelta
from typing import List, Optional
import asyncio

# ============================================
# 2. Third-Party Imports
# ============================================
from sqlalchemy import select, and_

# ============================================
# 3. Local Imports
# ============================================
from database.postgres import AsyncSessionLocal
from database.models import User
from services.kakao_client import get_kakao_client
from services.notification_service import NotificationService
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
INACTIVE_THRESHOLDS_HOURS = [24, 72, 168, 336]  # 1일, 3일, 7일, 14일 (C5: 14일 추가)

REENGAGEMENT_MESSAGES = {
    24: "안녕하세요 🌱 오늘 정원에 물 주는 것 잊지 않으셨나요? 잠깐 이야기 나눠요!",
    72: "정원이 기다리고 있어요 🌸 3일간 비가 오지 않았어요. 오늘 정원에 오셔서 꽃에 물 한 번 주세요!",
    168: "한 주가 지났어요 🌿 정원의 꽃들이 보고 싶어 한답니다. 잠깐만 들러주세요!",
    336: "오랫동안 정원이 비어있어요 🌺 많이 보고 싶어요. 그동안 어떻게 지내셨나요?",
}

# C5: 카테고리별 재참여 유도 메시지
CATEGORY_REENGAGEMENT = {
    "REMINISCENCE": "옛날 이야기 나누고 싶어요. 그때 좋았던 기억들을 다시 생각해보면 어떨까요? 🌸",
    "DAILY_EPISODIC": "오늘 하루 어떠셨나요? 일상 이야기를 들려주시면 정원이 더 활기를 찾아요 🌱",
    "NAMING": "이름 생각해보는 시간 가져요래요. 자주 묻던 이름들이 기억나나요? 🌿",
    "TEMPORAL": "요즘 날씨도 좋고 하루가 어떻게 흘러가는지 같이 느껴볼까요? 🕐",
    "VISUAL": "좋은 사진이나 그림 보면 기분이 좋아지는데, 함께 보실까요? 🖼️",
    "CHOICE": "가볼까 하고 고민되는 게 있나요? 둘 중에 하나를 골라볼까요? 🤔",
}

# C5: 사용자 취향 분석 기간
PREFERENCE_ANALYSIS_DAYS = 30


# ============================================
# 6. 비활성 사용자 조회
# ============================================

async def get_inactive_users(hours: int) -> List[User]:
    """
    마지막 상호작용으로부터 `hours`시간 이상 비활성인 사용자 목록 반환.

    Args:
        hours: 비활성 기준 시간 (예: 24, 72, 168)

    Returns:
        비활성 사용자 목록 (onboarding_day >= 1, 채널 또는 OAuth 사용자)
    """
    cutoff = datetime.now() - timedelta(hours=hours)
    # 정확히 `hours` 구간만 (이전 단계 사용자 제외)
    lower_cutoff = datetime.now() - timedelta(hours=hours + 24)

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(
                    and_(
                        User.last_interaction_at <= cutoff,
                        User.last_interaction_at > lower_cutoff,
                        User.onboarding_day >= 1,          # 온보딩 시작 이후만
                        User.kakao_channel_user_key.isnot(None),  # 채널 연결된 사용자
                    )
                )
            )
            users = result.scalars().all()
            logger.info(
                f"Inactive users ({hours}h): {len(users)}명",
                extra={"hours": hours, "count": len(users)}
            )
            return list(users)

    except Exception as e:
        logger.error(f"Failed to fetch inactive users ({hours}h): {e}", exc_info=True)
        return []


# ============================================
# 7. 재참여 메시지 전송
# ============================================

async def send_reengagement_message(user: User, hours: int) -> bool:
    """
    비활성 사용자에게 재참여 메시지 전송.

    Args:
        user: 대상 사용자
        hours: 비활성 시간 (24 / 72 / 168)

    Returns:
        전송 성공 여부
    """
    message = REENGAGEMENT_MESSAGES.get(hours)
    if not message:
        logger.warning(f"No reengagement message for {hours}h")
        return False

    # 토큰 상태 체크 및 링크 결정
    link_url = None
    button_title = None
    
    now = datetime.now()
    needs_reauth = False
    
    if not user.kakao_access_token:
        # OAuth 연동 안 된 사용자 (채널 전용 가입자)
        needs_reauth = True
    elif user.kakao_token_expires_at and user.kakao_token_expires_at <= now:
        # 액세스 토큰 만료됨
        if user.kakao_refresh_token_expires_at and user.kakao_refresh_token_expires_at <= now:
            # 리프레시 토큰까지 만료됨 -> 재로그인 필요
            needs_reauth = True
        else:
            # 리프레시 토큰은 살아있음 -> 자동 갱신 시도 가능하지만, 
            # 여기서 직접 갱신하지 않고 안전하게 로그인 페이지로 유도하거나 자동 갱신 태스크에 맡김.
            # 사용자 경험을 위해 버튼은 제공.
            needs_reauth = True
            
    if needs_reauth:
        link_url = "https://n8n.softline.co.kr/api/v1/auth/kakao/login"
        button_title = "카카오 연동/로그인 🌱"
        message += "\n\n(카카오 계정을 다시 한번 연동하시면 이메일 정보가 안전하게 업데이트됩니다.)"
    else:
        # 토큰이 정상이면 단순히 채널로 유도
        link_url = "https://n8n.softline.co.kr/kakao/channel"
        button_title = "정원 방문하기 🌿"

    try:
        kakao_client = get_kakao_client()

        # 채널 사용자: 비즈메시지 친구톡 시도
        if user.kakao_channel_user_key:
            result = await kakao_client.send_bizmessage_friend_talk(
                plus_friend_user_key=user.kakao_channel_user_key,
                message=message,
                link_url=link_url,
                button_title=button_title
            )
            success = result.get("result_code") == 0

        else:
            logger.info(f"No channel key for user {user.kakao_id}, skipping")
            return False

        if success:
            logger.info(
                f"✅ Reengagement sent ({hours}h): user={user.kakao_id}"
            )
        else:
            logger.warning(
                f"Reengagement send failed ({hours}h): user={user.kakao_id}, result={result}"
            )

        # 7일 비활성은 보호자에게도 알림
        if hours >= 168:
            await _notify_guardian_inactive(user)

        return success

    except Exception as e:
        logger.error(
            f"Reengagement message error ({hours}h) for {user.kakao_id}: {e}",
            exc_info=True
        )
        return False


async def _notify_guardian_inactive(user: User) -> None:
    """
    7일 이상 비활성 사용자의 보호자에게 알림 전송.

    Args:
        user: 비활성 사용자
    """
    try:
        notification_service = NotificationService()
        result = await notification_service.send_guardian_alert(
            user_id=str(user.id),
            risk_level="YELLOW",
            mcdi_score=user.baseline_mcdi or 75.0,
            analysis={
                "scores": {},
                "reason": "7일 비활성",
                "last_interaction": (
                    user.last_interaction_at.isoformat()
                    if user.last_interaction_at else None
                )
            }
        )
        logger.info(
            f"Guardian notified for inactive user {user.kakao_id}: "
            f"alert_sent={result.get('alert_sent')}"
        )
    except Exception as e:
        logger.error(f"Failed to notify guardian for {user.kakao_id}: {e}")


# ============================================
# 8. C5: Proactive Messaging (능동적 메시징)
# ============================================

async def get_user_preferred_topics(user_id: str) -> List[str]:
    """
    사용자의 선호 카테고리 분석 (최근 30일 대화 기반)

    Args:
        user_id: 사용자 ID

    Returns:
        선호 카테고리 리스트 (빈도 높은 순)
    """
    try:
        from database.postgres import AsyncSessionLocal
        from database.models import Conversation
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=PREFERENCE_ANALYSIS_DAYS)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Conversation.category)
                .where(
                    and_(
                        Conversation.user_id == int(user_id),
                        Conversation.created_at >= cutoff,
                        Conversation.category.isnot(None)
                    )
                )
                .group_by(Conversation.category)
                .order_by(Conversation.category.desc())
            )
            categories = result.scalars().all()

            # 빈도 계산을 위해 SQL에서 집계하거나 Python에서 계산
            # 여기서는 간단히 조회된 카테고리 반환
            logger.debug(f"User {user_id} preferred topics: {categories}")
            return list(categories) if categories else ["DAILY_EPISODIC"]  # 기본값

    except Exception as e:
        logger.error(f"Failed to get user preferences for {user_id}: {e}")
        return ["DAILY_EPISODIC"]


async def get_follow_up_topics(user_id: str) -> List[str]:
    """
    사용자의 후속 화제 추출 (Episodic Memory에서)

    Args:
        user_id: 사용자 ID

    Returns:
        후속 화제 리스트
    """
    try:
        from database.redis_client import redis_client as redis

        # Redis에서 최근 episodic 메모리 조회
        # 실제 구현에서는 Qdrant에서 follow_up_notes 필터링
        key_pattern = f"episodic:{user_id}:*"

        follow_ups = []
        # TODO: Qdrant에서 follow_up_notes 포인트 검색
        # 현재는 간단 구현

        return follow_ups[:3] if follow_ups else []

    except Exception as e:
        logger.error(f"Failed to get follow-up topics for {user_id}: {e}")
        return []


async def generate_personalized_reengagement_message(
    user: User,
    hours: int,
    use_follow_up: bool = True
) -> str:
    """
    개인화된 재참여 메시지 생성 (C5)

    Args:
        user: 대상 사용자
        hours: 비활성 시간
        use_follow_up: 후속 화제 사용 여부

    Returns:
        개인화된 메시지
    """
    # 기본 메시지
    base_message = REENGAGEMENT_MESSAGES.get(hours, REENGAGEMENT_MESSAGES[24])

    # C5: 사용자 선호 카테고리 기반 메시지 추가
    preferred_topics = await get_user_preferred_topics(str(user.id))
    if preferred_topics:
        top_category = preferred_topics[0]
        category_message = CATEGORY_REENGAGEMENT.get(top_category, "")
        if category_message:
            return f"{base_message}\n\n{category_message}"

    # C5: 후속 화제 기반 메시지
    if use_follow_up:
        follow_ups = await get_follow_up_topics(str(user.id))
        if follow_ups:
            import random
            topic = random.choice(follow_ups)
            return f"{base_message}\n\n아까 하려던 이야기 있었죠? {topic}에 대해서도 이어서 이야기해요!"

    return base_message


async def send_proactive_message(user: User, hours: int) -> bool:
    """
    개인화된 능동적 메시지 전송 (C5)

    Args:
        user: 대상 사용자
        hours: 비활성 시간

    Returns:
        전송 성공 여부
    """
    try:
        # 개인화된 메시지 생성
        message = await generate_personalized_reengagement_message(user, hours)

        # 토큰 상태 체크 및 링크 결정
        link_url = None
        button_title = None

        now = datetime.now()
        needs_reauth = False

        if not user.kakao_access_token:
            needs_reauth = True
        elif user.kakao_token_expires_at and user.kakao_token_expires_at <= now:
            if user.kakao_refresh_token_expires_at and user.kakao_refresh_token_expires_at <= now:
                needs_reauth = True
            else:
                needs_reauth = True

        if needs_reauth:
            link_url = "https://n8n.softline.co.kr/api/v1/auth/kakao/login"
            button_title = "카카오 연동/로그인 🌱"
        else:
            link_url = "https://n8n.softline.co.kr/kakao/channel"
            button_title = "정원 방문하기 🌿"

        kakao_client = get_kakao_client()

        # C5: 선호 카테고리를 메시지에 반영
        if user.kakao_channel_user_key:
            result = await kakao_client.send_bizmessage_friend_talk(
                plus_friend_user_key=user.kakao_channel_user_key,
                message=message,
                link_url=link_url,
                button_title=button_title
            )
            success = result.get("result_code") == 0

            if success:
                logger.info(
                    f"✅ Proactive message sent ({hours}h): user={user.kakao_id}"
                )
            else:
                logger.warning(
                    f"Proactive message send failed ({hours}h): user={user.kakao_id}"
                )

            return success
        else:
            return False

    except Exception as e:
        logger.error(
            f"Proactive message error ({hours}h) for {user.kakao_id}: {e}",
            exc_info=True
        )
        return False


# ============================================
# 9. 메인 모니터링 태스크
# ============================================

async def check_inactive_users() -> None:
    """
    비활성 사용자 체크 메인 태스크.

    APScheduler에서 24시간마다 호출됩니다.
    24h / 72h / 168h / 336h 비활성 사용자를 각각 처리합니다.
    C5: 개인화된 능동적 메시징 적용.
    """
    logger.info("🔍 Starting inactive user check...")
    total_sent = 0
    total_failed = 0

    for hours in INACTIVE_THRESHOLDS_HOURS:
        users = await get_inactive_users(hours)
        if not users:
            continue

        logger.info(f"Processing {len(users)} users inactive for {hours}h")

        for user in users:
            # C5: 개인화된 능동적 메시지 사용 (336h/14일 이상부터 적용)
            use_proactive = hours >= 336
            if use_proactive:
                success = await send_proactive_message(user, hours)
            else:
                success = await send_reengagement_message(user, hours)

            if success:
                total_sent += 1
            else:
                total_failed += 1

            # Rate limit 방지: 사용자 간 0.5초 지연
            await asyncio.sleep(0.5)

    logger.info(
        f"✅ Inactive user check complete: sent={total_sent}, failed={total_failed}"
    )


# ============================================
# 9. 스케줄 등록 헬퍼
# ============================================

def register_engagement_monitor_schedule(scheduler) -> None:
    """
    APScheduler에 비활성 사용자 모니터링 스케줄 등록.

    Args:
        scheduler: APScheduler AsyncIOScheduler 인스턴스

    Usage:
        from tasks.engagement_monitor import register_engagement_monitor_schedule
        register_engagement_monitor_schedule(scheduler)
    """
    from apscheduler.triggers.cron import CronTrigger

    scheduler.add_job(
        check_inactive_users,
        trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),  # 매일 09:00
        id="engagement_monitor",
        replace_existing=True,
        misfire_grace_time=3600
    )
    logger.info("✅ Engagement monitor scheduled: daily at 09:00 KST")
