"""
카카오 채널 Webhook 엔드포인트

사용자가 카카오 채널에 메시지를 보내면 자동으로 호출됨.
AI 응답 생성 + 대화 DB 저장 + MCDI 분석 (백그라운드).
"""

import asyncio
import hashlib
import time
from typing import Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.postgres import get_db, AsyncSessionLocal
from database.models import User, Conversation, AnalysisResult
from database.redis_client import redis_client
from core.dialogue.dialogue_manager import DialogueManager
from core.dialogue.time_aware import TimeAwareDialogue  # B4-1: Gap 메시지 생성
from core.analysis.analyzer import Analyzer
from services.llm_service import LLMService
from services.image_analysis_service import get_image_analysis_service
from core.nlp.embedder import Embedder
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/kakao", tags=["kakao"])

# ── 싱글톤 인스턴스 ────────────────────────────────────
_dialogue_manager: DialogueManager = None
_analyzer: Analyzer = None


def get_dialogue_manager() -> DialogueManager:
    global _dialogue_manager
    if _dialogue_manager is None:
        _dialogue_manager = DialogueManager()
    return _dialogue_manager


def get_analyzer() -> Analyzer:
    global _analyzer
    if _analyzer is None:
        llm = LLMService()
        embedder = Embedder()
        _analyzer = Analyzer(llm, embedder)
    return _analyzer


# ── 사용자 조회/생성 ──────────────────────────────────

async def _get_or_create_user(
    db: AsyncSession,
    plus_friend_user_key: str,
    bot_user_key: str
) -> tuple:
    """plusfriendUserKey로 사용자 조회, 없으면 OAuth 계정 연동 시도 또는 신규 생성

    Returns:
        (user, is_new, just_linked): 사용자 객체, 신규 여부, 방금 연동 여부
    """
    # ── OAuth 계정 자동 연동 체크 (기존 채널 계정 조회보다 우선) ─────────────────────────
    # /kakao/channel-auth/{token} 클릭 후 채널 메시지를 보낸 경우
    # 기존 채널 전용 계정이 있더라도 OAuth 연동 대기가 있으면 우선 처리
    try:
        from uuid import UUID
        pending_keys = await redis_client.keys("channel_auth_pending:*")

        for pending_key in pending_keys:
            oauth_user_id = pending_key.replace("channel_auth_pending:", "")
            try:
                result = await db.execute(
                    select(User).where(User.id == UUID(oauth_user_id))
                )
                oauth_user = result.scalar_one_or_none()

                if oauth_user and not oauth_user.kakao_channel_user_key:
                    # 동일 channel_user_key를 가진 기존 채널 전용 계정이 있으면 먼저 해제
                    dup_result = await db.execute(
                        select(User).where(User.kakao_channel_user_key == plus_friend_user_key)
                    )
                    dup_user = dup_result.scalar_one_or_none()
                    if dup_user and dup_user.id != oauth_user.id:
                        # OAuth 계정(access_token 보유)은 덮어쓰지 않음 - 채널 전용 ch_ 계정만 해제
                        if dup_user.kakao_access_token:
                            logger.warning(
                                f"채널 key 충돌: {dup_user.kakao_id}는 OAuth 계정이므로 해제 생략 "
                                f"(이미 다른 OAuth 계정이 연동됨)"
                            )
                            continue
                        dup_user.kakao_channel_user_key = None
                        await db.flush()
                        logger.info(f"기존 채널 전용 계정에서 key 해제: {dup_user.kakao_id}")

                    # 연동 실행
                    oauth_user.kakao_channel_user_key = plus_friend_user_key
                    await db.commit()
                    await db.refresh(oauth_user)

                    # pending 키 삭제 (일회용)
                    await redis_client.delete(pending_key)

                    logger.info(
                        "채널 계정 연동 완료",
                        extra={
                            "oauth_user_id": oauth_user_id,
                            "plus_friend_user_key": plus_friend_user_key
                        }
                    )
                    return oauth_user, False, True  # just_linked=True

            except Exception as e:
                logger.warning(f"연동 시도 실패 (키: {pending_key}): {e}")
                continue

    except Exception as e:
        logger.warning(f"채널 연동 체크 실패 (무시): {e}")

    # ── 기존 채널 사용자 조회 ─────────────────────────
    result = await db.execute(
        select(User).where(User.kakao_channel_user_key == plus_friend_user_key)
    )
    user = result.scalar_one_or_none()

    if user:
        return user, False, False

    # 신규 채널 사용자 생성
    user = User(
        kakao_id=f"ch_{plus_friend_user_key}",
        name="정원 친구",
        kakao_channel_user_key=plus_friend_user_key
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"신규 채널 사용자 생성: {plus_friend_user_key}")
    return user, True, False


# ── 신규 사용자 스케줄 등록 ──────────────────────────

async def _register_user_schedule(user_id: str) -> None:
    """신규 사용자 대화 스케줄 자동 등록 (백그라운드)"""
    try:
        from core.dialogue.scheduler import get_scheduler
        scheduler = get_scheduler()
        await scheduler.add_user_schedule(user_id)
        logger.info(f"신규 사용자 스케줄 등록 완료: {user_id}")
    except Exception as e:
        logger.error(f"신규 사용자 스케줄 등록 실패 {user_id}: {e}", exc_info=True)


# ── MCDI 백그라운드 분석 ──────────────────────────────

async def _analyze_and_reply_image(
    user_id: str,
    image_url: str,
    channel_user_key: str
) -> None:
    """
    이미지 분석 2턴 플로우 백그라운드 태스크

    Turn 2 처리 (Turn 1: 봇이 VISUAL 카테고리로 사진 요청):
    1. 카카오 CDN에서 이미지 다운로드 (base64)
    2. GPT-4o Vision으로 사진 내용 분석
    3. 이미지 컨텍스트 Redis 저장 (ER 후속 질문용)
    4. ER 후속 질문 포함한 AI 응답 생성
    5. 대화 DB 저장 (Conversation 레코드)
    6. 채널로 응답 전송 (OAuth send_to_me or 비즈메시지)
    """
    import httpx, base64

    try:
        logger.info(f"이미지 분석 2턴 시작: user={user_id}")

        # 1. 이미지 다운로드
        async with httpx.AsyncClient(timeout=10.0) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            image_base64 = base64.b64encode(img_resp.content).decode("utf-8")

        # 2. GPT-4o Vision으로 분석
        image_service = get_image_analysis_service()
        analysis = await image_service.analyze_image(
            image_base64=image_base64,
            analysis_type="memory"
        )
        analysis_data = analysis.get("analysis", {})
        objects = ", ".join(analysis_data.get("main_objects", []))
        mood = analysis_data.get("mood", "")
        time_of_day = analysis_data.get("time_of_day", "")
        scene = analysis_data.get("scene", "")
        image_description = (
            f"[사진 공유] 사진 속 주요 내용: {objects}."
            + (f" 분위기: {mood}." if mood else "")
            + (f" 시간대: {time_of_day}." if time_of_day else "")
            + (f" 장면: {scene}." if scene else "")
        )
        logger.info(f"이미지 분석 완료: {image_description[:80]}")

        # 3. 이미지 컨텍스트 Redis 저장 (ER 후속 질문에서 활용)
        visual_context = {
            "image_url": image_url,
            "objects": objects,
            "mood": mood,
            "time_of_day": time_of_day,
            "scene": scene,
            "description": image_description,
            "timestamp": datetime.now().isoformat(),
        }
        await redis_client.set_json(
            f"visual_context:{user_id}",
            visual_context,
            ttl=3600  # 1시간 유지
        )

        # 4. ER 후속 질문 포함 AI 응답 생성
        #    dialogue_manager에 image_description을 user_message로 전달 →
        #    VISUAL 카테고리 시스템 프롬프트가 사물/상황에 대한 기억 탐색 질문 생성
        dialogue_manager = get_dialogue_manager()
        ai_response = await dialogue_manager.generate_response(
            user_id=user_id,
            user_message=image_description
        )

        # 5. 대화 DB 저장 (이미지 2턴 기록)
        try:
            async with AsyncSessionLocal() as db:
                from database.models import User, Conversation
                result = await db.execute(
                    select(User).where(User.kakao_channel_user_key == channel_user_key)
                )
                user_obj = result.scalar_one_or_none()
                if user_obj:
                    conv = Conversation(
                        user_id=user_obj.id,
                        message="[사진 공유]",
                        response=ai_response,
                        message_type="image",
                        image_url=image_url,
                        category="VISUAL",
                        response_latency_ms=0,
                    )
                    db.add(conv)
                    await db.commit()
                    logger.info(f"이미지 대화 DB 저장 완료: user={user_id}")
        except Exception as db_err:
            logger.warning(f"이미지 대화 DB 저장 실패 (응답은 전송): {db_err}")

        # 6. 채널로 응답 전송
        from services.kakao_client import KakaoClient
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.kakao_channel_user_key == channel_user_key)
            )
            user_obj = result.scalar_one_or_none()
            if user_obj and user_obj.kakao_access_token:
                kakao_client = KakaoClient()
                await kakao_client.send_to_me(
                    access_token=user_obj.kakao_access_token,
                    message=ai_response
                )
                logger.info(f"이미지 분석 결과 전송 완료: user={user_id}")
            else:
                logger.warning(
                    f"이미지 응답 전송 불가 - OAuth 토큰 없음: user={user_id}. "
                    "채널 전용 사용자는 OAuth 연동 필요"
                )

    except Exception as e:
        logger.error(f"이미지 분석 2턴 플로우 실패: {e}", exc_info=True)


async def _run_mcdi_analysis(
    user_id: str,
    message: str,
    conversation_id: int,
    response_latency_sec: float,
    conversation_mode: str = "normal"
) -> None:
    """
    MCDI 분석 백그라운드 태스크

    웹훅 응답 후 비동기로 실행 (카카오 5초 타임아웃 영향 없음).
    6개 지표 분석 → MCDI 점수 → DB 저장.

    Args:
        conversation_mode: 대화 모드 ("normal" | "story" | "role_reversal")
                           스토리 모드일 때 SD 점수 과대평가 가능성 플래그 저장
    """
    try:
        logger.info(f"MCDI 분석 시작 - user: {user_id}, conv: {conversation_id}, mode: {conversation_mode}")

        analyzer = get_analyzer()
        result = await analyzer.analyze(
            message=message,
            memory={"response_latency": response_latency_sec}
        )

        mcdi_score = result["mcdi_score"]
        risk_level = result["mcdi_details"]["risk_category"]
        scores = result["scores"]

        logger.info(
            f"MCDI 분석 완료",
            extra={
                "user_id": user_id,
                "mcdi_score": mcdi_score,
                "risk_level": risk_level,
                "scores": scores
            }
        )

        # 보완 2: 스토리 모드 SD 편향 플래그 (주제 연속성으로 SD 점수 과대평가 가능)
        sd_detail = result.get("sd_detail") or {}
        if conversation_mode == "story":
            sd_detail = {
                **sd_detail,
                "story_mode_active": True,
                "score_note": "스토리 모드 활성화 - 주제 연속성으로 SD 점수가 과대평가될 수 있음"
            }

        # DB 저장 (별도 세션 - 백그라운드)
        async with AsyncSessionLocal() as db:
            analysis = AnalysisResult(
                conversation_id=conversation_id,
                user_id=user_id,
                mcdi_score=mcdi_score,
                risk_level=risk_level,
                lr_score=scores.get("LR"),
                lr_detail=result.get("lr_detail"),
                sd_score=scores.get("SD"),
                sd_detail=sd_detail,
                nc_score=scores.get("NC"),
                nc_detail=result.get("nc_detail"),
                to_score=scores.get("TO"),
                to_detail=result.get("to_detail"),
                er_score=scores.get("ER"),
                er_detail=result.get("er_detail"),
                rt_score=scores.get("RT"),
                rt_detail=result.get("rt_detail"),
                contradictions=result.get("contradictions", []),
                processing_time_ms=int(response_latency_sec * 1000)
            )
            db.add(analysis)
            await db.commit()
            logger.info(f"MCDI 분석 결과 저장 완료 - score: {mcdi_score}, risk: {risk_level}")

            # TimescaleDB 시계열 저장 (MCDI 트렌드 추적)
            try:
                from database.timescale import get_timescale
                timescale = await get_timescale()
                await timescale.store_mcdi(
                    user_id=user_id,
                    mcdi_score=mcdi_score,
                    scores=scores,
                    risk_level=risk_level
                )
                logger.info(f"TimescaleDB 시계열 저장 완료 - user: {user_id}")
            except Exception as te:
                logger.warning(f"TimescaleDB 저장 실패 (무시): {te}")

            # 게이미피케이션 업데이트 (꽃 심기 + DB 동기화)
            try:
                from core.analysis.garden_mapper import GardenMapper
                garden_mapper = GardenMapper()  # redis_client는 내부에서 생성
                garden_update = await garden_mapper.update_garden_status(
                    user_id=user_id,
                    mcdi_score=mcdi_score,
                    risk_level=risk_level
                )
                logger.info(
                    f"정원 업데이트 완료",
                    extra={
                        "user_id": user_id,
                        "flower_count": garden_update.current_status.flower_count,
                        "consecutive_days": garden_update.current_status.consecutive_days,
                        "achievements": garden_update.achievements_unlocked
                    }
                )
            except Exception as ge:
                logger.warning(f"게이미피케이션 업데이트 실패 (무시): {ge}")

            # ============================================
            # 4계층 메모리 저장 (Episodic → Qdrant, Biographical → Qdrant+Redis)
            # ============================================
            try:
                from core.memory.memory_manager import MemoryManager
                from core.nlp.embedder import Embedder
                from sqlalchemy import select

                # 대화 응답 가져오기 (conversation_id로 조회)
                conv_result = await db.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                conversation = conv_result.scalar_one_or_none()
                ai_response = conversation.response if conversation else ""

                # 4계층 메모리 저장 (store_all이 내부적으로 추출 처리)
                memory_manager = MemoryManager(embedder=Embedder())

                # 분석 결과를 통합
                analysis_with_emotion = result.copy()
                # 감정 벡터가 없으면 기본값 추가
                if "emotion_vector" not in analysis_with_emotion:
                    analysis_with_emotion["emotion_vector"] = {
                        "v": 0.5, "a": 0.3, "i": 0.5  # 중립 감정
                    }

                stored = await memory_manager.store_all(
                    user_id=str(user_id),
                    message=message,
                    response=ai_response,
                    analysis=analysis_with_emotion
                )

                logger.info(
                    f"4계층 메모리 저장 완료",
                    extra={
                        "user_id": user_id,
                        "stored_episodic": stored.get("episodic_stored", 0),
                        "stored_biographical": stored.get("biographical_stored", 0),
                        "session_stored": stored.get("session_stored", False)
                    }
                )

            except Exception as me:
                logger.warning(f"메모리 저장 실패 (무시): {me}", exc_info=True)

    except Exception as e:
        logger.error(f"MCDI 분석 실패 - user: {user_id}: {e}", exc_info=True)


# ── MCDI 컨텍스트 조회 (B3-1) ─────────────────────────

async def _get_mcdi_context(user_id: str) -> dict:
    """
    MCDI 컨텍스트 캐시 조회 (5분 TTL)

    Redis 캐시 우선 확인 후, 캐시 miss 시 TimescaleDB 조회.
    slope < -2.0이면 risk_level 한 단계 상향 조정.

    Args:
        user_id: 사용자 ID

    Returns:
        MCDI 컨텍스트 딕셔너리
        {
            "latest_risk_level": "GREEN",
            "latest_mcdi_score": 78.5,
            "score_trend": "stable",
            "slope_per_week": -0.5,
            "latest_scores": {"LR": 80.0, "SD": 75.0, ...},
            "has_data": False
        }

    Example:
        >>> ctx = await _get_mcdi_context("user_123")
        >>> print(ctx["latest_risk_level"])
        'GREEN'
    """
    logger.info(f"[MCDI_CONTEXT] _get_mcdi_context called for user_id: {user_id}")
    cache_key = f"mcdi_context:{user_id}"

    # 1. Redis 캐시 우선 확인
    try:
        cached = await redis_client.get_json(cache_key)
        if cached:
            logger.debug(f"MCDI context cache hit for user {user_id}")
            # B3-6: 캐시에서도 slope 체크 (조기 경보)
            level_map = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
            rev_map = {0: "GREEN", 1: "YELLOW", 2: "ORANGE", 3: "RED"}
            slope = cached.get("slope_per_week", 0.0)
            if slope and slope < -2.0:
                current_idx = level_map.get(cached.get("latest_risk_level", "GREEN"), 0)
                cached["latest_risk_level"] = rev_map.get(min(current_idx + 1, 3), "RED")
                logger.info(
                    f"Early warning (cached): slope {slope} < -2.0, "
                    f"upgrading risk to {cached['latest_risk_level']}"
                )
                # 캐시 업데이트
                await redis_client.set_json(cache_key, cached, ttl=300)
            return cached
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")

    # 2. 캐시 없으면 TimescaleDB 조회
    try:
        from core.memory.memory_manager import MemoryManager
        mm = MemoryManager()
        analytics = await mm.get_mcdi_analytics(user_id, days=14)

        context = {
            "latest_risk_level": analytics.get("latest_risk_level", "GREEN"),
            "latest_mcdi_score": analytics.get("latest_mcdi_score"),
            "score_trend": analytics.get("score_trend", "stable"),
            "slope_per_week": analytics.get("slope_per_week", 0.0),
            "latest_scores": analytics.get("latest_scores", {}),
            "has_data": analytics.get("has_data", False)
        }

        # 조기 경보: slope < -2.0이면 risk_level 한 단계 상향
        level_map = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
        rev_map = {0: "GREEN", 1: "YELLOW", 2: "ORANGE", 3: "RED"}
        if context["slope_per_week"] and context["slope_per_week"] < -2.0:
            current_idx = level_map.get(context["latest_risk_level"], 0)
            context["latest_risk_level"] = rev_map.get(min(current_idx + 1, 3), "RED")
            logger.info(
                f"Early warning: slope {context['slope_per_week']} < -2.0, "
                f"upgrading risk to {context['latest_risk_level']}"
            )

        # 5분 캐시 저장
        try:
            await redis_client.set_json(cache_key, context, ttl=300)
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

        logger.info(
            f"MCDI context loaded for user {user_id}",
            extra={
                "risk_level": context["latest_risk_level"],
                "mcdi_score": context["latest_mcdi_score"],
                "trend": context["score_trend"]
            }
        )

        return context

    except Exception as e:
        logger.warning(f"MCDI context fetch failed for {user_id}: {e}")
        return {"latest_risk_level": "GREEN", "has_data": False}


# ── 인지 도메인 질문 쿨다운 체크 (B3-4) ───────────────

async def _check_probe_cooldown(user_id: str, domain: str) -> bool:
    """
    동일 도메인 2턴 내 재삽입 방지 (B3-4)

    Args:
        user_id: 사용자 ID
        domain: MCDI 도메인 (LR, SD, NC, TO, ER, RT)

    Returns:
        True: 삽입 허용, False: 쿨다운 중

    Example:
        >>> if await _check_probe_cooldown("user_123", "TO"):
        ...     # 시간 지남력 질문 삽입 가능
        ...     pass
    """
    key = f"probe_used:{user_id}:{domain}"
    try:
        exists = await redis_client.get_json(key)
        if exists:
            logger.debug(f"Probe cooldown active for {user_id}:{domain}")
            return False  # 쿨다운 중
        # 사용 기록 저장 (TTL=30분 ≈ 2턴)
        await redis_client.set_json(key, {"used": True}, ttl=1800)
        return True  # 삽입 허용
    except Exception as e:
        logger.warning(f"Probe cooldown check failed: {e}")
        return True  # 실패 시 허용 (보수적 기본값)


# ── 반복 발화 감지 (B3-5) ───────────────────────────

def _detect_repetition(user_message: str, recent_mentions: list) -> bool:
    """
    사용자 메시지가 최근 2턴 발화와 70% 이상 겹치는지 감지 (B3-5)

    Args:
        user_message: 현재 사용자 메시지
        recent_mentions: 최근 사용자 발화 리스트

    Returns:
        True: 반복 감지됨, False: 정상

    Example:
        >>> if _detect_repetition("배고파", ["밥 먹을래", "배고파"]):
        ...     # 반복 발화 처리
        ...     pass
    """
    if not recent_mentions or len(recent_mentions) < 2:
        return False

    recent = recent_mentions[-2:]  # 최근 2개
    words_new = set(user_message.split())
    for prev in recent:
        words_prev = set(prev.split())
        if len(words_prev) == 0:
            continue
        overlap = len(words_new & words_prev) / len(words_prev)
        if overlap >= 0.7:
            logger.info(f"Repetition detected: {overlap:.1%} overlap")
            return True
    return False


# ── 저녁 회상 퀴즈 사전 생성 ────────────────────────────

async def _pre_generate_evening_quiz(user_id: str) -> None:
    """저녁 시간대(18~24시) 회상 퀴즈를 Redis에 사전 생성 (Zero-Latency)

    MCDI 분석 이후에 호출되어 최신 DB 데이터를 보장.
    캐시된 퀴즈는 다음 메시지 처리 시 generate_response(next_question=quiz)로 전달.

    Redis 키:
    - evening_quiz_cache:{user_id}:{date} — 생성된 퀴즈 (24h TTL)
    - evening_quiz_done:{user_id}:{date} — 1일 1회 보장 (24h TTL)
    """
    from zoneinfo import ZoneInfo
    from sqlalchemy import select, desc

    today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    cache_key = f"evening_quiz_cache:{user_id}:{today_str}"
    done_key = f"evening_quiz_done:{user_id}:{today_str}"

    try:
        # 이미 완료 표시 확인
        if await redis_client.exists(done_key):
            return

        # 최근 3일 대화 기록 조회
        async with AsyncSessionLocal() as session:
            # timezone-aware를 naive로 변환 (DB 컬럼과 일치)
            kst = ZoneInfo("Asia/Seoul")
            three_days_ago = datetime.now(kst) - __import__("datetime").timedelta(days=3)
            # naive datetime으로 변환 (tzinfo 제거)
            three_days_ago = three_days_ago.replace(tzinfo=None)
            result = await session.execute(
                select(Conversation)
                .where(
                    Conversation.user_id == user_id,
                    Conversation.created_at >= three_days_ago,
                    Conversation.category.in_(["DAILY_EPISODIC", "REMINISCENCE", "VISUAL", "CHOICE", "NAMING"])
                )
                .order_by(desc(Conversation.created_at))
                .limit(8)
            )
            recent_convos = result.scalars().all()

        if not recent_convos:
            logger.info(f"No recent conversations for evening quiz: {user_id}")
            return

        # 대화 내용을 기반으로 퀴즈 프롬프트 구성
        convos_text = "\n".join([
            f"- [{c.category}] 사용자: {c.message[:80]} / AI: {c.response[:80]}"
            for c in recent_convos
        ])

        quiz_prompt = (
            f"다음은 사용자와의 최근 대화 기록입니다:\n{convos_text}\n\n"
            f"이 대화 내용 중에서 사용자가 기억했으면 하는 것을 하나 골라 짧은 회상 퀴즈를 만드세요.\n\n"
            f"중요: '기억나시나요?' 같은 힌트 주는 말은 쓰지 말고, 구체적으로 얘기해 달라고 하세요.\n\n"
            f"좋은 예시:\n"
            f"- 아침에 등산하면서 본 꽃이 뭔지 얘기해줘요\n"
            f"- 옛날에 집 마당에 어떤 나무가 있었는지 말씀해 주시겠어요?\n"
            f"- 봄에 김치 담갔을 때 어떤 반찬이 함께 나왔는지 얘기해 보세요\n\n"
            f"나쁜 예시 (피할 것):\n"
            f"- 아침에 등산하셨는데 기억나시나요? (너무 힌트가 많음)\n"
            f"- 집 마당 기억나세요? (너무 모호함)\n\n"
            f"형식: '○○이 뭔지 얘기해줘요' 또는 '어떤 ○○이 있었는지 말씀해 주시겠어요?'처럼\n"
            f"반드시 1문장으로만 출력하세요. 추가 설명이나 물음표 이외의 기호 없이."
        )

        llm_service = LLMService()  # 기본 모델: sonnet-4-6
        quiz_text = await asyncio.wait_for(
            llm_service.call(prompt=quiz_prompt),
            timeout=8.0
        )

        if quiz_text and quiz_text.strip():
            # 퀴즈 컨텍스트도 함께 저장 (답변 평가용)
            import json
            quiz_context = {
                "quiz_text": quiz_text.strip(),
                "source_convos": convos_text[:500],  # 평가용 참고 텍스트
                "created_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
            }
            # 퀴즈 캐시 저장 (24시간) - JSON 형식
            await redis_client.set(cache_key, json.dumps(quiz_context, ensure_ascii=False), ttl=86400)
            # 완료 표시 (24시간)
            await redis_client.set(done_key, "1", ttl=86400)
            logger.info(
                f"Evening quiz generated for {user_id}: {quiz_text.strip()[:50]}",
                extra={"user_id": user_id, "quiz_preview": quiz_text.strip()[:50]}
            )
        else:
            logger.warning(f"Empty quiz generated for {user_id}")

    except asyncio.TimeoutError:
        logger.warning(f"Evening quiz generation timeout for {user_id}")
    except Exception as e:
        logger.error(f"Evening quiz generation failed for {user_id}: {e}", exc_info=True)


# ── 퀴즈 답변 평가 ────────────────────────────────────

async def _evaluate_quiz_answer(user_id: str, user_answer: str) -> tuple[bool, str, float | None]:
    """저녁 회상 퀴즈 답변 평가

    Returns:
        (is_quiz_response, feedback_message, rt_adjustment)
        - is_quiz_response: 퀴즈에 대한 답변인지 여부
        - feedback_message: 피드백 메시지 (없으면 None)
        - rt_adjustment: MCDI RT 점수 조정값 (-10 ~ +10, None이면 조정 없음)
    """
    from zoneinfo import ZoneInfo

    today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    quiz_cache_key = f"evening_quiz_cache:{user_id}:{today_str}"

    # 캐시된 퀴즈 확인
    cached_data = await redis_client.get(quiz_cache_key)
    if not cached_data:
        return False, None, None

    # JSON 파싱
    import json
    try:
        if isinstance(cached_data, str):
            quiz_context = json.loads(cached_data)
        else:
            quiz_context = cached_data
    except (json.JSONDecodeError, TypeError):
        return False, None, None

    quiz_text = quiz_context.get("quiz_text", "")
    source_convos = quiz_context.get("source_convos", "")

    # 답변 평가 프롬프트
    eval_prompt = f"""다음은 저녁 회상 퀴즈와 사용자의 답변입니다.

[퀴즈]: {quiz_text}

[사용자 답변]: {user_answer}

[참고 대화 기록]:
{source_convos}

위 정보를 바탕으로 답변을 평가해주세요:

1. 답변 관련성 (0~100점): 사용자가 퀴즈와 관련된 내용으로 답변했는가?
2. 기억 정확도 (0~100점): 참고 대화 기록과 일치하는가?

평가 기준:
- 90점 이상: 정확히 기억함 (RT +5)
- 70~89점: 대체로 기억함 (RT +2)
- 50~69점: 부분적으로 기억 (RT 0)
- 30~49점: 기억 흐릿 (RT -3)
- 30점 미만: 기억하지 못함 (RT -5)

반드시 JSON 형식으로만 출력:
{{"relevance": 점수, "accuracy": 점수, "feedback": "짧은 피드백 (1문장)"}}
"""

    try:
        llm_service = LLMService()
        result = await asyncio.wait_for(
            llm_service.call_json(prompt=eval_prompt),
            timeout=10.0
        )

        relevance = result.get("relevance", 50)
        accuracy = result.get("accuracy", 50)
        feedback = result.get("feedback", "")

        # 평균 점수로 RT 조정값 계산
        avg_score = (relevance + accuracy) / 2

        if avg_score >= 90:
            rt_adjustment = 5
            feedback_msg = f"{feedback} 기억력이 아주 좋으시네요! 🌟"
        elif avg_score >= 70:
            rt_adjustment = 2
            feedback_msg = f"{feedback} 잘 기억하고 계시네요! 👍"
        elif avg_score >= 50:
            rt_adjustment = 0
            feedback_msg = f"{feedback} 그렇군요."
        elif avg_score >= 30:
            rt_adjustment = -3
            feedback_msg = f"{feedback} 기억이 조금 흐릿하신가 봐요. 🌱"
        else:
            rt_adjustment = -5
            feedback_msg = f"{feedback} 다시 얘기해 주시면 기억나실 수도 있어요."

        # 퀴즈 캐시 삭제 (평가 완료)
        await redis_client.delete(quiz_cache_key)

        logger.info(
            f"Quiz answer evaluated for {user_id}: score={avg_score:.1f}, RT={rt_adjustment:+d}",
            extra={"user_id": user_id, "quiz_score": avg_score, "rt_adjustment": rt_adjustment}
        )

        return True, feedback_msg, rt_adjustment

    except asyncio.TimeoutError:
        logger.warning(f"Quiz evaluation timeout for {user_id}")
        return False, None, None
    except Exception as e:
        logger.error(f"Quiz evaluation failed for {user_id}: {e}", exc_info=True)
        return False, None, None


async def _adjust_mcdi_rt_score(user_id: str, rt_adjustment: int) -> None:
    """퀴즈 답변 평가 결과를 MCDI RT 점수에 반영

    Args:
        user_id: 사용자 ID
        rt_adjustment: RT 점수 조정값 (-10 ~ +10)
    """
    from sqlalchemy import select, desc
    from database.models import AnalysisResult

    try:
        async with AsyncSessionLocal() as session:
            # 가장 최근 MCDI 분석 결과 조회
            result = await session.execute(
                select(AnalysisResult)
                .where(AnalysisResult.user_id == user_id)
                .order_by(desc(AnalysisResult.created_at))
                .limit(1)
            )
            latest_analysis = result.scalars().first()

            if not latest_analysis:
                logger.info(f"No MCDI analysis found for {user_id}, skipping RT adjustment")
                return

            # RT 점수 조정
            scores = latest_analysis.scores or {}
            current_rt = scores.get("RT", 50)
            new_rt = max(0, min(100, current_rt + rt_adjustment))

            scores["RT"] = new_rt
            latest_analysis.scores = scores

            # MCDI 점수 재계산
            from core.analysis.mcdi_calculator import MCDICalculator
            calculator = MCDICalculator()
            new_mcdi_score = calculator.calculate(
                lr_score=scores.get("LR", 50),
                sd_score=scores.get("SD", 50),
                nc_score=scores.get("NC", 50),
                to_score=scores.get("TO", 50),
                er_score=scores.get("ER", 50),
                rt_score=new_rt
            )

            latest_analysis.mcdi_score = new_mcdi_score

            # 위험도 재평가
            from core.analysis.risk_evaluator import RiskEvaluator
            evaluator = RiskEvaluator()
            new_risk_level = evaluator.evaluate(new_mcdi_score)
            latest_analysis.risk_level = new_risk_level

            await session.commit()

            logger.info(
                f"RT score adjusted for {user_id}: {current_rt} → {new_rt} (adjustment: {rt_adjustment:+d}), MCDI: {new_mcdi_score:.1f}",
                extra={"user_id": user_id, "rt_adjustment": rt_adjustment, "new_mcdi": new_mcdi_score}
            )

    except Exception as e:
        logger.error(f"Failed to adjust RT score for {user_id}: {e}", exc_info=True)


# ── 카카오 응답 형식 ──────────────────────────────────

def _build_kakao_response(text: str) -> Dict[str, Any]:
    """카카오 i 오픈빌더 응답 형식 생성"""
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": text}}]
        }
    }


def _build_kakao_response_with_button(
    text: str,
    button_text: str,
    button_url: str
) -> Dict[str, Any]:
    """카카오 i 오픈빌더 응답 형식 생성 (버튼 포함)

    카카오 채널에서 버튼을 표시하려면 quickReplies 사용.
    """
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {"text": text}
            }],
            "quickReplies": [{
                "action": "webLink",
                "label": button_text,
                "webLinkUrl": button_url
            }]
        }
    }


# ── 메인 웹훅 ─────────────────────────────────────────

@router.post("/webhook")
async def kakao_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    카카오 채널 메시지 수신 → AI 응답 → MCDI 분석

    플로우:
    1. 페이로드 파싱
    2. 사용자 조회/생성
    3. AI 응답 생성 (DialogueManager)
    4. 대화 Redis + PostgreSQL 저장
    5. 카카오 응답 반환 (즉시)
    6. MCDI 분석 백그라운드 실행 (응답 후)
    """
    start_time = time.time()

    try:
        data = await request.json()

        # ── 1. 페이로드 파싱 ──────────────────────────
        user_request = data.get("userRequest", {})
        user_info = user_request.get("user", {})
        user_properties = user_info.get("properties", {})

        plus_friend_user_key = (
            user_properties.get("plusfriendUserKey")
            or user_properties.get("plusfriend_user_key")
        )
        bot_user_key = user_properties.get("botUserKey") or user_info.get("id", "")
        utterance = user_request.get("utterance", "").strip()

        logger.info(
            "카카오 메시지 수신",
            extra={
                "plus_friend_user_key": plus_friend_user_key or "(없음)",
                "utterance_preview": utterance[:30]
            }
        )

        if not utterance:
            return _build_kakao_response("메시지를 입력해 주세요. 🌱")

        # plusfriendUserKey 없음 → 채널 메시지가 아닌 환경 (스킬 콘솔 테스트 등)
        if not plus_friend_user_key:
            logger.warning(
                "plusfriendUserKey 없음 (스킬 콘솔 테스트)",
                extra={"bot_user_key": bot_user_key, "utterance": utterance[:30]}
            )
            return _build_kakao_response("안녕하세요! 기억의 정원입니다. 🌱")

        # ── 이미지 URL 감지 ───────────────────────────
        image_url = None
        message_type = "text"
        KAKAO_IMAGE_HOSTS = ("talk.kakaocdn.net", "k.kakaocdn.net")
        if any(host in utterance for host in KAKAO_IMAGE_HOSTS):
            image_url = utterance
            message_type = "image"

        # ── 2. 사용자 조회/생성 ───────────────────────
        user, is_new_user, just_linked = await _get_or_create_user(db, plus_friend_user_key, bot_user_key)
        user_id = str(user.id)

        # 방금 OAuth ↔ 채널 연동 완료 → 환영 메시지 반환
        if just_linked:
            logger.info(f"채널 연동 완료 환영 메시지 전송: {user_id}")
            return _build_kakao_response(
                "채널 연동이 완료됐어요! 🌱\n\n"
                "이제 매일 함께 기억의 정원을 가꿔봐요.\n"
                "잠시 후 첫 대화가 시작됩니다! 😊"
            )

        # 신규 사용자 → 스케줄 자동 등록
        if is_new_user:
            background_tasks.add_task(_register_user_schedule, user_id)

        # ── 2.4. 채널 전용 사용자 → OAuth 로그인 유도 ──────────────────
        # OAuth 토큰이 없는 채널 사용자가 스케줄 메시지를 받으려면 로그인 필요
        if not is_new_user and not user.kakao_access_token and user.kakao_channel_user_key:
            session_data = await redis_client.get_json(f"session:{user_id}")
            if session_data and session_data.get("pending_oauth_prompt"):
                # OAuth 로그인 안내 메시지
                oauth_message = session_data.get("oauth_prompt_message", (
                    "🔔 안녕하세요! 정원지기예요 🌱\n\n"
                    "매일 정해진 시간에 기억의 정원에서 드리는\n"
                    "아침/점심/저녁 인사를 받으시려면 로그인이 필요해요.\n\n"
                    "아래 버튼을 눌러 간편하게 로그인해주세요!"
                ))
                # 프롬프트 표시 후 플래그 제거
                session_data["pending_oauth_prompt"] = False
                await redis_client.set_json(f"session:{user_id}", session_data)
                logger.info(f"OAuth 로그인 유도 메시지 전송: {user_id}")

                # 올바른 Kakao OAuth URL 생성
                import urllib.parse
                oauth_url = (
                    f"https://kauth.kakao.com/oauth/authorize"
                    f"?client_id={settings.KAKAO_REST_API_KEY}"
                    f"&redirect_uri={urllib.parse.quote(settings.KAKAO_REDIRECT_URI, safe='')}"
                    f"&response_type=code"
                )
                return _build_kakao_response_with_button(
                    oauth_message,
                    button_text="로그인 하기 🔐",
                    button_url=oauth_url
                )

        # ── 2.5. 온보딩 플로우 체크 ──────────────────
        # Day 0: 정원 이름 짓기 처리 (2단계: 환영 먼저 → 다음 메시지가 이름)
        if user.onboarding_day == 0 and message_type == "text":
            from core.workflow.onboarding_flow import OnboardingFlow
            ob_flow = OnboardingFlow(db)
            is_onboarding, ob_response = await ob_flow.handle(user, utterance)
            if is_onboarding and ob_response:
                # Day 0 대화는 DB에 저장 후 온보딩 응답 반환
                dialogue_manager = get_dialogue_manager()
                await dialogue_manager.add_turn(
                    user_id=user_id,
                    user_message=utterance,
                    assistant_message=ob_response,
                    metadata={"onboarding_day": user.onboarding_day}
                )
                conversation = Conversation(
                    user_id=user.id,
                    message=utterance,
                    response=ob_response,
                    message_type="text",
                    category="onboarding"
                )
                db.add(conversation)
                await db.commit()
                logger.info(f"온보딩 Day 0 응답 반환: {user_id}")
                return _build_kakao_response(ob_response)

        # ── 3. 저녁 회상 퀴즈 발송 체크 (방안 D) ───────────────────────────
        # 저녁 시간(18~24시) 첫 메시지에 퀴즈만 전송
        # 당일 자정까지 퀴즈 유효, 다음날 넘어가면 무효화
        from zoneinfo import ZoneInfo
        now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
        today_str = now_kst.strftime("%Y-%m-%d")

        # 저녁 시간대(18~24시) 체크
        if 18 <= now_kst.hour < 24 and message_type == "text":
            quiz_sent_key = f"evening_quiz_sent:{user_id}:{today_str}"
            quiz_cache_key = f"evening_quiz_cache:{user_id}:{today_str}"

            # 아직 퀴즈 안 보냈고, 캐시된 퀴즈가 있으면
            if not await redis_client.exists(quiz_sent_key):
                cached_data = await redis_client.get(quiz_cache_key)
                if cached_data:
                    # JSON 파싱
                    import json
                    try:
                        if isinstance(cached_data, str):
                            quiz_context = json.loads(cached_data)
                        else:
                            quiz_context = cached_data
                        quiz_text = quiz_context.get("quiz_text", "")
                    except (json.JSONDecodeError, TypeError):
                        quiz_text = str(cached_data)

                    if quiz_text and quiz_text.strip():
                        # 퀴즈만 단독 전송
                        quiz_response = (
                            f"━━━━━━━━━━━━━━\n"
                            f"📝 오늘의 회상 퀴즈\n"
                            f"━━━━━━━━━━━━━━\n\n"
                            f"{quiz_text.strip()}"
                        )

                        # 대화 저장
                        dialogue_manager = get_dialogue_manager()
                        await dialogue_manager.add_turn(
                            user_id=user_id,
                            user_message=utterance,
                            assistant_message=quiz_response,
                            metadata={"evening_quiz": True}
                        )

                        conversation = Conversation(
                            user_id=user.id,
                            message=utterance,
                            response=quiz_response,
                            message_type="text",
                            category="quiz"
                        )
                        db.add(conversation)
                        await db.commit()

                        # 퀴즈 전송 플래그 설정 (당일 자정까지만 유효)
                        # 자정까지 남은 시간 계산 (초 단위)
                        seconds_until_midnight = (
                            (datetime.now(ZoneInfo("Asia/Seoul")).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
                            - datetime.now(ZoneInfo("Asia/Seoul"))
                        ).total_seconds()
                        await redis_client.set(quiz_sent_key, "1", ttl=int(seconds_until_midnight))

                        logger.info(
                            f"Evening quiz sent for {user_id}: {quiz_text[:30]}",
                            extra={"user_id": user_id, "quiz_text": quiz_text[:50]}
                        )

                        return _build_kakao_response(quiz_response)

        # ── 4. AI 응답 생성 ───────────────────────────
        dialogue_manager = get_dialogue_manager()
        conv_mode = "normal"  # 보완 2: 대화 모드 (SD 편향 플래그용, 기본값)
        selected_category = None  # HIGH-2: 6개 카테고리 라우팅

        if message_type == "image":
            # 이미지는 즉시 응답 후 백그라운드에서 분석
            # 카카오 5초 타임아웃 내에 응답 불가 → 분석은 비동기 처리
            user_message_for_save = "[사진 공유] 사진을 받았어요."
            ai_response = "사진을 받았어요! 🌿 잠깐만 기다려 주세요, 사진을 살펴볼게요..."
            selected_category = "VISUAL"
            background_tasks.add_task(
                _analyze_and_reply_image,
                user_id=user_id,
                image_url=image_url,
                channel_user_key=plus_friend_user_key
            )
        else:
            user_message_for_save = utterance

            # ========== 턴 중복 방지 (카카오 웹훅 재시도 대응) ==========
            msg_hash = hashlib.md5(user_message_for_save.encode()).hexdigest()
            dedup_key = f"msg_dedup:{user_id}:{msg_hash}"
            if await redis_client.exists(dedup_key):
                logger.info(
                    f"Duplicate message detected for {user_id}, skipping",
                    extra={"user_id": user_id, "msg_preview": user_message_for_save[:30]}
                )
                return _build_kakao_response("")  # 빈 응답으로 중복 방지
            # ============================================================

            # ========== 저녁 회상 퀴즈 답변 평가 ==========
            # 퀴즈를 이미 보낸 상태면 답변을 평가
            is_quiz_answer = False
            quiz_feedback = None
            rt_adjustment = None

            quiz_sent_key = f"evening_quiz_sent:{user_id}:{today_str}"
            quiz_cache_key = f"evening_quiz_cache:{user_id}:{today_str}"

            # 퀴즈를 보냈으면 답변 평가 시도 (1회만)
            if await redis_client.exists(quiz_sent_key):
                is_quiz_answer, quiz_feedback, rt_adjustment = await _evaluate_quiz_answer(
                    user_id=user_id,
                    user_answer=user_message_for_save
                )

                # 퀴즈 답변 평가 완료 후 sent 플래그 제거 (재평가 방지)
                if is_quiz_answer or quiz_feedback:
                    await redis_client.delete(quiz_sent_key)
                    logger.info(f"Quiz evaluation completed, sent flag removed for {user_id}")

                if is_quiz_answer and quiz_feedback:
                    # 퀴즈 피드백을 AI 응답 앞에 추가
                    logger.info(
                        f"Quiz answer evaluated for {user_id}: RT={rt_adjustment}",
                        extra={"user_id": user_id, "rt_adjustment": rt_adjustment}
                    )

                    # RT 점수 조정 (백그라운드로 MCDI 재분석)
                    if rt_adjustment is not None:
                        background_tasks.add_task(
                            _adjust_mcdi_rt_score,
                            user_id=user_id,
                            rt_adjustment=rt_adjustment
                        )

                # 퀴즈 캐시는 _evaluate_quiz_answer 내부에서 삭제됨
            # =============================================

            # HIGH-2: 카테고리 선택 (약한 지표 우선, 주간 빈도 제한 적용)
            try:
                from core.dialogue.category_selector import CategorySelector, get_category_prompt_hint
                category_selector = CategorySelector()
                selected_category = await category_selector.select(user_id=user_id)
                category_hint = get_category_prompt_hint(selected_category)
                # 세션 컨텍스트에 카테고리 힌트 저장 → prompt_builder가 활용
                await dialogue_manager.update_context(user_id, {
                    "current_category": selected_category,
                    "category_hint": category_hint,
                })
                logger.info(
                    f"카테고리 선택: {selected_category}",
                    extra={"user_id": user_id, "category": selected_category}
                )
            except Exception as cat_err:
                logger.warning(f"카테고리 선택 실패 (기본값 사용): {cat_err}")
                selected_category = "DAILY_EPISODIC"

            # B3-3: MCDI 컨텍스트 조회 후 응답 생성 (어댑티브 블록 활성화)
            mcdi_context = await _get_mcdi_context(user_id)

            # ========== B3-5: 반복 발화 감지 후 risk_level 승격 (신규) ==========
            # 세션에서 최근 발화 가져오기
            session_data_tmp = await redis_client.get_json(f"session:{user_id}")
            recent_mentions_raw = session_data_tmp.get("conversation_history", []) if session_data_tmp else []
            # conversation_history의 키는 "user" (dialogue_manager.py:271 확인)
            # add_turn()은 응답 생성 후에 호출되므로, 여기서는 현재 턴이 아직 포함되지 않음 (정상 동작)
            recent_mentions = [turn.get("user", "") for turn in recent_mentions_raw if turn.get("user")]

            # 반복 감지 시 risk_level을 임시 ORANGE로 승격
            if _detect_repetition(user_message_for_save, recent_mentions):
                if mcdi_context and mcdi_context.get("has_data"):
                    original_risk = mcdi_context.get("latest_risk_level", "GREEN")
                    mcdi_context["latest_risk_level"] = "ORANGE"
                    logger.info(
                        f"Repetition detected, upgrading risk: {original_risk} → ORANGE",
                        extra={"user_id": user_id}
                    )
            # ============================================================

            ai_response = await dialogue_manager.generate_response(
                user_id=user_id,
                user_message=user_message_for_save,
                mcdi_context=mcdi_context  # 어댑티브 대화 블록 생성용
            )
            conv_mode = await dialogue_manager.get_last_conversation_mode(user_id)

            # ========== B4-1: Gap 메시지 접두사 추가 (2시간 이상 경과 시) ==========
            hours_since_last = await dialogue_manager.get_hours_since_last_interaction(user_id)
            if hours_since_last and hours_since_last >= 2.0:
                time_aware = TimeAwareDialogue()
                gap_message = time_aware.generate_combined_message(hours_since_last)
                # Gap 메시지를 AI 응답 앞에 추가
                ai_response = f"{gap_message}\n\n{ai_response}"
                logger.info(
                    f"Gap message prepended for {user_id}",
                    extra={"user_id": user_id, "hours_since_last": hours_since_last}
                )
            # ====================================================================

        # ── 4. 대화 저장 ──────────────────────────────
        elapsed_ms = int((time.time() - start_time) * 1000)

        # 턴 중복 방지: 처리 완료된 메시지 60초간 마킹
        if message_type == "text":
            await redis_client.set(dedup_key, "1", ttl=60)

        await dialogue_manager.add_turn(
            user_id=user_id,
            user_message=user_message_for_save,
            assistant_message=ai_response,
            metadata={"response_latency_ms": elapsed_ms, "category": selected_category}
        )

        conversation = Conversation(
            user_id=user.id,
            message=user_message_for_save,
            response=ai_response,
            message_type=message_type,
            image_url=image_url,
            response_latency_ms=elapsed_ms,
            category=selected_category,  # HIGH-2: 카테고리 저장
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        # ── 5. MCDI 분석 백그라운드 등록 ──────────────
        # Day 15+ (베이스라인 완성) 이후만 정식 MCDI 분석 실행
        # Day 1-14: 분석은 실행하되 알림은 발송하지 않음 (데이터 축적)
        background_tasks.add_task(
            _run_mcdi_analysis,
            user_id=user_id,
            message=user_message_for_save,
            conversation_id=conversation.id,
            response_latency_sec=elapsed_ms / 1000,
            conversation_mode=conv_mode
        )

        # ========== 저녁 회상 퀴즈 트리거 (18~24시, 1일 1회) ==========
        now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
        if 18 <= now_kst.hour < 24:
            quiz_done_key = f"evening_quiz_done:{user_id}:{now_kst.strftime('%Y-%m-%d')}"
            if not await redis_client.exists(quiz_done_key):
                background_tasks.add_task(
                    _pre_generate_evening_quiz,
                    user_id=user_id
                )
                logger.info(
                    f"Evening quiz pre-generation scheduled for {user_id}",
                    extra={"user_id": user_id, "hour": now_kst.hour}
                )
        # ============================================================

        logger.info(
            "응답 완료 + MCDI 분석 예약됨",
            extra={"user_id": user_id, "elapsed_ms": elapsed_ms}
        )

        # ── 6. 즉시 응답 반환 ─────────────────────────
        return _build_kakao_response(ai_response)

    except Exception as e:
        logger.error(f"웹훅 처리 실패: {e}", exc_info=True)
        return _build_kakao_response(
            "잠시 정원을 가꾸는데 문제가 생겼어요 ㅎㅎ\n조금 후에 다시 말씀해 주세요!"
        )


@router.get("/channel")
async def kakao_channel_redirect():
    """카카오 채널 채팅방으로 리다이렉트

    나에게 보내기 버튼 클릭 시 이 엔드포인트를 통해 채널로 이동.
    우리 서버 도메인(등록 도메인)을 경유해야 카카오 API가 링크를 허용함.
    """
    channel_id = settings.KAKAO_CHANNEL_ID
    if channel_id:
        redirect_url = f"https://pf.kakao.com/{channel_id}/chat"
    else:
        redirect_url = "https://pf.kakao.com"
    logger.info(f"채널 리다이렉트: {redirect_url}")
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/channel-auth/{token}")
async def kakao_channel_auth(token: str):
    """OAuth ↔ 채널 자동 연동 리다이렉트

    플로우:
    1. OAuth 로그인 완료 → send_to_me로 "채널 연동하기" 버튼 포함 메시지 전송
    2. 사용자가 버튼 클릭 → 이 엔드포인트 호출
    3. Redis에서 토큰으로 OAuth user_id 조회
    4. channel_auth_pending:{user_id} 저장 (5분 TTL)
    5. 카카오 채널로 리다이렉트
    6. 사용자가 채널에서 첫 메시지 전송 → 웹훅에서 자동 연동
    """
    channel_id = settings.KAKAO_CHANNEL_ID
    channel_url = f"https://pf.kakao.com/{channel_id}/chat" if channel_id else "https://pf.kakao.com"

    # 토큰으로 OAuth user_id 조회
    user_id = await redis_client.get(f"channel_link_token:{token}")
    if not user_id:
        logger.warning(f"유효하지 않거나 만료된 연동 토큰: {token[:10]}...")
        return RedirectResponse(url=channel_url, status_code=302)

    # pending 상태 저장 (5분 TTL - 채널에서 첫 메시지를 보낼 시간)
    await redis_client.set(f"channel_auth_pending:{user_id}", "1", ttl=300)

    # 링크 토큰 삭제 (일회용)
    await redis_client.delete(f"channel_link_token:{token}")

    logger.info(f"채널 연동 대기 설정 완료: user_id={user_id}")
    return RedirectResponse(url=channel_url, status_code=302)


@router.get("/webhook/test")
async def test_webhook():
    """Webhook 엔드포인트 상태 확인"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is working!",
        "endpoint": "/kakao/webhook"
    }


@router.post("/webhook/simulate")
async def simulate_webhook(
    user_key: str,
    message: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Webhook 시뮬레이션 (개발/테스트용)"""
    fake_payload = {
        "userRequest": {
            "utterance": message,
            "user": {
                "id": f"sim_{user_key}",
                "properties": {
                    "plusfriendUserKey": user_key,
                    "isFriend": True,
                    "botUserKey": f"sim_{user_key}"
                }
            }
        }
    }

    class FakeRequest:
        async def json(self):
            return fake_payload

    return await kakao_webhook(FakeRequest(), background_tasks, db)
