"""
대화 처리 API 라우터

핵심 대화 엔드포인트 - SessionWorkflow 통합.

Author: Memory Garden Team
Created: 2025-02-10
"""

from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import base64
import uuid

from api.schemas import (
    MessageRequest,
    ImageMessageRequest,
    MessageResponse,
    ConversationHistory,
    ConversationListResponse,
)
from database.postgres import get_db
from database.redis_client import redis_client
from core.memory.session_memory import SessionMemory
from core.workflow.session_workflow import SessionWorkflow
from api.dependencies import get_session_workflow
from services.image_analysis_service import get_image_analysis_service
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


# ============================================
# 핵심 대화 엔드포인트
# ============================================

@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    message_request: MessageRequest,
    db: AsyncSession = Depends(get_db),
    workflow: SessionWorkflow = Depends(get_session_workflow)
):
    """
    **핵심 대화 엔드포인트**

    메시지를 전송하고 AI 응답을 받습니다.
    전체 SessionWorkflow를 실행합니다.

    Workflow Steps:
    1. 컨텍스트 생성
    2. 메모리 검색 (4계층 병렬)
    3. 응답 분석 (6개 지표 병렬)
    4. 위험도 평가 (4단계)
    5. 조건부 알림 (ORANGE/RED)
    6. 교란 변수 처리
    7. 다음 상호작용 계획
    8. 응답 생성 및 메모리 저장

    Args:
        session_id: 세션 UUID
        message_request: 사용자 메시지 및 메타데이터
        db: 데이터베이스 세션 (자동 주입)
        workflow: SessionWorkflow 인스턴스 (자동 주입)

    Returns:
        MessageResponse with:
        - response: AI 응답 메시지
        - mcdi_score: MCDI 종합 점수
        - risk_level: 위험도 (GREEN/YELLOW/ORANGE/RED)
        - garden_status: 정원 상태 (향후 구현)
        - achievements: 달성한 업적 목록 (향후 구현)
        - level_up: 레벨 업 여부 (향후 구현)
    """
    try:
        logger.info(
            f"Processing message for session: session_id={session_id}, "
            f"user_id={message_request.user_id}, "
            f"message_type={message_request.message_type}"
        )

        # ============================================
        # SessionWorkflow 실행
        # ============================================
        ctx = await workflow.process_message(
            user_id=message_request.user_id,
            message=message_request.message,
            message_type=message_request.message_type,
            image_url=message_request.image_url,
            metadata={
                "session_id": session_id,
                # TODO: 카카오톡에서 response_latency 받아오면 여기 추가
                "response_latency": 0.0  # 기본값
            }
        )

        # ============================================
        # MessageResponse 생성
        # ============================================
        response = MessageResponse(
            success=True,
            response=ctx.response,
            session_id=session_id,
            mcdi_score=ctx.mcdi_score,
            risk_level=ctx.risk_level,
            detected_emotion=None,  # TODO: 감정 분석 추가 시 구현
            garden_status=None,     # TODO: 정원 시스템 구현 시 추가
            achievements=None,      # TODO: 업적 시스템 구현 시 추가
            level_up=False,         # TODO: 레벨 시스템 구현 시 추가
            execution_time_ms=ctx.processing_time_ms,
            timestamp=ctx.timestamp
        )

        logger.info(
            f"✅ Message processed successfully",
            extra={
                "session_id": session_id,
                "user_id": message_request.user_id,
                "mcdi_score": ctx.mcdi_score,
                "risk_level": ctx.risk_level,
                "processing_time_ms": ctx.processing_time_ms
            }
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"❌ Failed to process message: {e}",
            extra={
                "session_id": session_id,
                "user_id": message_request.user_id
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )


@router.post("/messages/image", response_model=MessageResponse)
async def send_image_message(
    image_request: ImageMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    이미지 메시지 전송

    - Vision API를 사용하여 이미지 분석
    - 텍스트 메시지와 동일한 워크플로우 실행

    Args:
        image_request: 이미지 URL 및 설명

    Returns:
        MessageResponse
    """
    try:
        logger.info(f"Processing image message: user_id={image_request.user_id}")

        # TODO: VisionService + SessionWorkflow
        # vision_service = VisionService()
        # image_description = await vision_service.analyze_image(image_request.image_url)
        #
        # workflow = SessionWorkflow()
        # result = await workflow.process_message(
        #     user_id=image_request.user_id,
        #     message=f"{image_request.message}\n[이미지 분석: {image_description}]",
        #     message_type="image",
        #     image_url=image_request.image_url
        # )

        raise HTTPException(
            status_code=501,
            detail="VisionService and SessionWorkflow not fully integrated yet"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process image message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# 이미지 업로드 및 분석
# ============================================

@router.post("/sessions/{session_id}/images")
async def upload_and_analyze_image(
    session_id: str,
    file: UploadFile = File(..., description="이미지 파일 (JPEG, PNG)"),
    message: Optional[str] = Form(None, description="사용자 메시지 (선택)"),
    analysis_type: str = Form("memory", description="분석 타입 (meal/place/memory)"),
    db: AsyncSession = Depends(get_db)
):
    """
    **이미지 업로드 및 분석**

    사용자가 업로드한 이미지를 분석하고 결과를 반환합니다.

    지원 형식:
    - JPEG, PNG
    - 최대 크기: 10MB

    분석 타입:
    - meal: 음식 사진 분석
    - place: 장소 사진 분석
    - memory: 일반 기억 단서 추출

    Args:
        session_id: 세션 ID
        file: 업로드 파일
        message: 사용자 메시지 (선택)
        analysis_type: 분석 타입

    Returns:
        {
            "success": true,
            "image_id": "uuid",
            "analysis": {...분석 결과...},
            "message": "분석 완료",
            "timestamp": "2026-02-11T16:00:00Z"
        }

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/conversations/sessions/{session_id}/images \
          -F "file=@meal.jpg" \
          -F "analysis_type=meal" \
          -F "message=오늘 점심 먹었어요"
        ```
    """
    try:
        # 파일 타입 검증
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Only JPEG/PNG allowed."
            )

        # 파일 크기 검증 (10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()

        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {len(file_content)} bytes. Max: {MAX_FILE_SIZE} bytes."
            )

        logger.info(
            f"Uploading image for session: {session_id}",
            extra={
                "session_id": session_id,
                "image_filename": file.filename,
                "size_bytes": len(file_content),
                "content_type": file.content_type,
                "analysis_type": analysis_type
            }
        )

        # Base64 인코딩
        image_base64 = base64.b64encode(file_content).decode('utf-8')

        # 이미지 분석 (ImageAnalysisService)
        image_service = get_image_analysis_service()

        analysis_result = await image_service.analyze_image(
            image_base64=image_base64,
            analysis_type=analysis_type,
            context=message
        )

        # 이미지 ID 생성
        image_id = str(uuid.uuid4())

        # Redis에 저장 (24시간 TTL)
        # TODO: S3 또는 로컬 스토리지에 저장하는 것이 더 적절
        # 현재는 Redis에 메타데이터만 저장
        image_metadata = {
            "image_id": image_id,
            "session_id": session_id,
            "image_filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(file_content),
            "analysis": analysis_result,
            "message": message,
            "uploaded_at": datetime.now().isoformat()
        }

        await redis_client.setex(
            f"image:{image_id}",
            86400,  # 24시간
            str(image_metadata)  # JSON serialize 필요 시 json.dumps() 사용
        )

        logger.info(
            f"Image uploaded and analyzed successfully",
            extra={
                "image_id": image_id,
                "session_id": session_id,
                "analysis_type": analysis_type,
                "tokens_used": analysis_result.get("usage", {}).get("total_tokens", 0)
            }
        )

        return {
            "success": True,
            "image_id": image_id,
            "session_id": session_id,
            "image_filename": file.filename,
            "analysis": analysis_result["analysis"],
            "raw_response": analysis_result["raw_response"],
            "analysis_type": analysis_type,
            "message": message,
            "timestamp": analysis_result["timestamp"],
            "model": analysis_result["model"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to upload and analyze image: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}"
        )


# ============================================
# 대화 히스토리 조회
# ============================================

@router.get("/sessions/{session_id}/history", response_model=ConversationHistory)
async def get_session_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=200, description="최대 조회 개수"),
    db: AsyncSession = Depends(get_db)
):
    """
    **세션의 대화 히스토리 조회**

    SessionMemory (Redis)에서 현재 세션의 모든 대화 턴을 조회합니다.

    Args:
        session_id: 세션 ID
        limit: 최대 조회 개수 (기본 50, 최대 200)

    Returns:
        ConversationHistory with:
        - session_id: 세션 ID
        - turns: 대화 턴 리스트
        - total_turns: 총 대화 수
        - created_at: 세션 생성 시간
        - updated_at: 마지막 업데이트 시간

    Example:
        GET /api/v1/conversations/sessions/abc123/history?limit=10
    """
    try:
        logger.info(f"Getting conversation history: session_id={session_id}, limit={limit}")

        # SessionMemory 사용하여 대화 히스토리 조회
        session_memory = SessionMemory(user_id=0)  # user_id는 실제로는 session에서 가져와야 함

        # 세션 존재 확인
        if not await session_memory.exists(session_id):
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )

        # 대화 턴 조회
        turns = await session_memory.get_all_turns(session_id, limit=limit)

        # 메타데이터 조회
        metadata = await session_memory.get_metadata(session_id)
        if not metadata:
            metadata = {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

        # 응답 구성
        response = ConversationHistory(
            session_id=session_id,
            turns=turns,
            total_turns=len(turns),
            created_at=metadata.get("created_at") if metadata else None,
            updated_at=metadata.get("updated_at") if metadata else None
        )

        logger.info(
            f"Retrieved conversation history",
            extra={
                "session_id": session_id,
                "total_turns": len(turns)
            }
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


@router.get("/users/{user_id}/conversations", response_model=ConversationListResponse)
async def list_user_conversations(
    user_id: str,
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(20, ge=1, le=100, description="조회 개수"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    **사용자의 전체 대화 목록 조회 (페이지네이션)**

    사용자의 모든 세션과 대화를 조회합니다.
    Redis (SessionMemory)에서 세션 목록을 가져옵니다.

    Args:
        user_id: 사용자 ID
        skip: 건너뛸 개수 (페이지네이션)
        limit: 조회 개수 (기본 20, 최대 100)
        start_date: 시작 날짜 필터 (YYYY-MM-DD)
        end_date: 종료 날짜 필터 (YYYY-MM-DD)

    Returns:
        ConversationListResponse with:
        - conversations: 대화 목록
        - total: 총 대화 수
        - skip: 현재 오프셋
        - limit: 현재 limit

    Example:
        GET /api/v1/conversations/users/user123/conversations?skip=0&limit=20
    """
    try:
        logger.info(
            f"Listing conversations",
            extra={
                "user_id": user_id,
                "skip": skip,
                "limit": limit,
                "start_date": start_date,
                "end_date": end_date
            }
        )

        # PostgreSQL에서 대화 조회 (analysis_result와 join)
        from sqlalchemy import select, func
        from sqlalchemy.orm import joinedload
        from database.models import Conversation, AnalysisResult
        from api.schemas import ConversationHistory, ConversationTurn
        from uuid import UUID

        # user_id를 UUID로 변환
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid user_id format: {user_id}"
            )

        # 기본 쿼리 (analysis_result eager loading)
        query = (
            select(Conversation)
            .where(Conversation.user_id == user_uuid)
            .options(joinedload(Conversation.analysis_result))
        )

        # 날짜 필터링
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(Conversation.created_at >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # 종료일 23:59:59까지 포함
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.where(Conversation.created_at <= end_dt)

        # 총 개수 조회
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar() or 0

        # 정렬 (최신순) 및 페이지네이션
        query = query.order_by(Conversation.created_at.desc())
        query = query.offset(skip).limit(limit)

        # 실행
        result = await db.execute(query)
        conversations = result.scalars().all()

        # ConversationHistory 형식으로 변환
        conversation_histories = []
        for conv in conversations:
            # analysis_result에서 emotion과 mcdi_score 가져오기
            emotion = None
            mcdi_score = None

            if conv.analysis_result:
                # emotion은 lr_detail 또는 sd_detail의 JSONB에서 추출 (간단히 None으로)
                # 실제로는 감정 분석 결과를 별도로 저장해야 함
                emotion = None
                mcdi_score = conv.analysis_result.mcdi_score

            # 각 대화를 개별 ConversationHistory로 변환
            turn = ConversationTurn(
                user_message=conv.message,
                assistant_message=conv.response or "",
                emotion=emotion,
                mcdi_score=mcdi_score,
                timestamp=conv.created_at
            )

            history = ConversationHistory(
                user_id=user_id,
                session_id=None,  # PostgreSQL에는 session_id 없음
                turns=[turn],
                total_count=1,
                start_date=conv.created_at,
                end_date=conv.created_at
            )

            conversation_histories.append(history)

        response = ConversationListResponse(
            conversations=conversation_histories,
            total=total,
            skip=skip,
            limit=limit
        )

        logger.info(
            f"Retrieved {len(conversation_histories)} conversations (total: {total})",
            extra={
                "user_id": user_id,
                "total": total,
                "returned": len(conversation_histories)
            }
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list conversations: {str(e)}"
        )
