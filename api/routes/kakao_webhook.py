"""
카카오 채널 Webhook 엔드포인트

사용자가 카카오 채널에 메시지를 보내면 자동으로 호출됨.
AI 응답 생성 + 대화 DB 저장 + MCDI 분석 (백그라운드).
"""

import time
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.postgres import get_db, AsyncSessionLocal
from database.models import User, Conversation, AnalysisResult
from core.dialogue.dialogue_manager import DialogueManager
from core.analysis.analyzer import Analyzer
from services.llm_service import LLMService
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
    """plusfriendUserKey로 사용자 조회, 없으면 신규 생성

    Returns:
        (user, is_new): 사용자 객체와 신규 여부
    """
    result = await db.execute(
        select(User).where(User.kakao_channel_user_key == plus_friend_user_key)
    )
    user = result.scalar_one_or_none()

    if user:
        return user, False

    user = User(
        kakao_id=f"ch_{plus_friend_user_key}",
        name="정원 친구",
        kakao_channel_user_key=plus_friend_user_key
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"신규 채널 사용자 생성: {plus_friend_user_key}")
    return user, True


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

async def _run_mcdi_analysis(
    user_id: str,
    message: str,
    conversation_id: int,
    response_latency_sec: float
) -> None:
    """
    MCDI 분석 백그라운드 태스크

    웹훅 응답 후 비동기로 실행 (카카오 5초 타임아웃 영향 없음).
    6개 지표 분석 → MCDI 점수 → DB 저장.
    """
    try:
        logger.info(f"MCDI 분석 시작 - user: {user_id}, conv: {conversation_id}")

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
                sd_detail=result.get("sd_detail"),
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

    except Exception as e:
        logger.error(f"MCDI 분석 실패 - user: {user_id}: {e}", exc_info=True)


# ── 카카오 응답 형식 ──────────────────────────────────

def _build_kakao_response(text: str) -> Dict[str, Any]:
    """카카오 i 오픈빌더 응답 형식 생성"""
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": text}}]
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
            or user_properties.get("plusfriend_user_key", "unknown")
        )
        bot_user_key = (
            user_properties.get("botUserKey")
            or user_info.get("id", "unknown")
        )
        utterance = user_request.get("utterance", "").strip()

        logger.info(
            "카카오 메시지 수신",
            extra={
                "plus_friend_user_key": plus_friend_user_key,
                "utterance_preview": utterance[:30]
            }
        )

        if not utterance:
            return _build_kakao_response("메시지를 입력해 주세요. 🌱")

        # ── 2. 사용자 조회/생성 ───────────────────────
        user, is_new_user = await _get_or_create_user(db, plus_friend_user_key, bot_user_key)
        user_id = str(user.id)

        # 신규 사용자 → 스케줄 자동 등록
        if is_new_user:
            background_tasks.add_task(_register_user_schedule, user_id)

        # ── 3. AI 응답 생성 ───────────────────────────
        dialogue_manager = get_dialogue_manager()
        ai_response = await dialogue_manager.generate_response(
            user_id=user_id,
            user_message=utterance
        )

        # ── 4. 대화 저장 ──────────────────────────────
        elapsed_ms = int((time.time() - start_time) * 1000)

        await dialogue_manager.add_turn(
            user_id=user_id,
            user_message=utterance,
            assistant_message=ai_response,
            metadata={"response_latency_ms": elapsed_ms}
        )

        conversation = Conversation(
            user_id=user.id,
            message=utterance,
            response=ai_response,
            message_type="text",
            response_latency_ms=elapsed_ms
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        # ── 5. MCDI 분석 백그라운드 등록 ──────────────
        background_tasks.add_task(
            _run_mcdi_analysis,
            user_id=user_id,
            message=utterance,
            conversation_id=conversation.id,
            response_latency_sec=elapsed_ms / 1000
        )

        logger.info(
            "응답 완료 + MCDI 분석 예약됨",
            extra={"user_id": user_id, "elapsed_ms": elapsed_ms}
        )

        # ── 6. 즉시 응답 반환 ─────────────────────────
        return _build_kakao_response(ai_response)

    except Exception as e:
        logger.error(f"웹훅 처리 실패: {e}", exc_info=True)
        return _build_kakao_response(
            "잠시 정원을 가꾸는데 문제가 생겼어요 🌱\n조금 후에 다시 말씀해 주세요!"
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
