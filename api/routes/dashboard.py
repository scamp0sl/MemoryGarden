"""
베타 테스트 대시보드 API

관리자용 사용자별 일별 현황 모니터링 엔드포인트.

Author: Memory Garden Team
Created: 2026-03-05
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date, and_, desc

from database.postgres import get_db
from database.models import User, Conversation, AnalysisResult, GardenStatus
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ============================================
# 대시보드 HTML 서빙
# ============================================

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard():
    """베타 테스트 대시보드 HTML 페이지 서빙"""
    from fastapi.responses import FileResponse
    return FileResponse("static/dashboard.html", media_type="text/html")


# ============================================
# 1. 전체 요약 통계 (상단 4개 카드)
# ============================================

@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    대시보드 상단 요약 카드 데이터

    Returns:
        {
            "total_users": 42,
            "today_active": 38,
            "danger_users": 3,        # ORANGE or RED
            "inactive_24h": 1,        # 24시간 이상 미응답
            "updated_at": "..."
        }
    """
    try:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_24h = now - timedelta(hours=24)

        # 전체 활성 사용자 수 (deleted_at 없는 사람, 온보딩 진행한 사람)
        total_q = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.deleted_at.is_(None),
                    User.onboarding_day >= 1
                )
            )
        )
        total_users = total_q.scalar() or 0

        # 오늘 대화한 사용자 수
        today_active_q = await db.execute(
            select(func.count(func.distinct(Conversation.user_id))).where(
                Conversation.created_at >= today_start
            )
        )
        today_active = today_active_q.scalar() or 0

        # 위험 감지 사용자 (ORANGE or RED 최근 분석 기준)
        # 각 사용자의 최신 분석 결과에서 위험도 확인
        danger_q = await db.execute(
            select(func.count(func.distinct(AnalysisResult.user_id))).where(
                and_(
                    AnalysisResult.risk_level.in_(["ORANGE", "RED"]),
                    AnalysisResult.created_at >= now - timedelta(days=3)
                )
            )
        )
        danger_users = danger_q.scalar() or 0

        # 24시간 이상 미응답 (온보딩 완료된 사용자 기준)
        inactive_q = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.deleted_at.is_(None),
                    User.onboarding_day >= 1,
                    User.last_interaction_at < cutoff_24h
                )
            )
        )
        inactive_24h = inactive_q.scalar() or 0

        return {
            "total_users": total_users,
            "today_active": today_active,
            "danger_users": danger_users,
            "inactive_24h": inactive_24h,
            "updated_at": now.isoformat()
        }

    except Exception as e:
        logger.error(f"Dashboard summary error: {e}", exc_info=True)
        return {
            "total_users": 0,
            "today_active": 0,
            "danger_users": 0,
            "inactive_24h": 0,
            "error": str(e),
            "updated_at": datetime.now().isoformat()
        }


# ============================================
# 2. 사용자별 일별 현황 테이블
# ============================================

@router.get("/users", response_model=Dict[str, Any])
async def get_users_daily_status(
    db: AsyncSession = Depends(get_db),
    days: int = Query(14, ge=1, le=90, description="히스토리 조회 일수")
) -> Dict[str, Any]:
    try:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        since = now - timedelta(days=days)
        cutoff_24h = now - timedelta(hours=24)

        # 전체 사용자 조회 (삭제 안 됨, 온보딩 시작한 사람)
        users_q = await db.execute(
            select(User).where(
                and_(
                    User.deleted_at.is_(None),
                    User.onboarding_day >= 1
                )
            )
        )
        users = users_q.scalars().all()

        # ── 사용자별 최근 대화 시각 일괄 조회 (N+1 방지) ──────────────────
        last_conv_time_q = await db.execute(
            select(
                Conversation.user_id,
                func.max(Conversation.created_at).label("last_at")
            ).group_by(Conversation.user_id)
        )
        last_conv_time_map = {str(row[0]): row[1] for row in last_conv_time_q.fetchall()}
        # ──────────────────────────────────────────────────────────────────

        # 정렬: 실제 최근 대화 기준 내림차순
        users = sorted(
            users,
            key=lambda u: last_conv_time_map.get(str(u.id)) or datetime.min,
            reverse=True
        )

        result = []
        for user in users:
            uid = user.id
            uid_str = str(uid)

            # 오늘 대화 수
            today_conv_q = await db.execute(
                select(func.count(Conversation.id)).where(
                    and_(
                        Conversation.user_id == uid,
                        Conversation.created_at >= today_start
                    )
                )
            )
            today_conversations = today_conv_q.scalar() or 0

            # 최신 분석 결과
            latest_analysis_q = await db.execute(
                select(AnalysisResult)
                .where(AnalysisResult.user_id == uid)
                .order_by(desc(AnalysisResult.created_at))
                .limit(1)
            )
            latest_analysis = latest_analysis_q.scalar_one_or_none()

            # MCDI 트렌드
            trend_q = await db.execute(
                select(AnalysisResult.mcdi_score, AnalysisResult.created_at)
                .where(and_(
                    AnalysisResult.user_id == uid,
                    AnalysisResult.created_at >= since
                ))
                .order_by(AnalysisResult.created_at)
            )
            mcdi_trend = [round(row[0], 1) for row in trend_q.fetchall() if row[0] is not None]

            # 마지막 대화 내용 + 시각 (Conversation 기준 — 정확한 값)
            last_conv_q = await db.execute(
                select(Conversation.message, Conversation.response, Conversation.category, Conversation.created_at)
                .where(Conversation.user_id == uid)
                .order_by(desc(Conversation.created_at))
                .limit(1)
            )
            last_conv = last_conv_q.one_or_none()

            # Conversation 기준 실제 마지막 대화 시각
            real_last_at = last_conv_time_map.get(uid_str)

            result.append({
                "user_id": uid_str,
                "name": user.email or user.name or "이름 없음",
                "garden_name": user.garden_name or "",
                "onboarding_day": user.onboarding_day,
                # ✅ Conversation 테이블 기준 실제 값 사용
                "last_interaction": real_last_at.isoformat() if real_last_at else None,
                "today_conversations": today_conversations,
                "latest_mcdi": round(latest_analysis.mcdi_score, 1) if latest_analysis else None,
                "latest_risk": latest_analysis.risk_level if latest_analysis else "UNKNOWN",
                "mcdi_trend": mcdi_trend[-14:],
                # ✅ 24시간 이상 대화 없으면 inactive
                "is_inactive": (
                    real_last_at < cutoff_24h
                    if real_last_at else True
                ),
                "kakao_channel_user_key": user.kakao_channel_user_key or "",
                "last_message": (last_conv[0][:60] + "…" if last_conv and last_conv[0] and len(last_conv[0]) > 60 else (last_conv[0] if last_conv else None)),
                "last_response": (last_conv[1][:60] + "…" if last_conv and last_conv[1] and len(last_conv[1]) > 60 else (last_conv[1] if last_conv else None)),
                "last_category": last_conv[2] if last_conv else None,
            })

        return {"users": result, "total": len(result)}

    except Exception as e:
        logger.error(f"Dashboard users error: {e}", exc_info=True)
        return {"users": [], "total": 0, "error": str(e)}



# ============================================
# 3. 사용자 MCDI 상세 트렌드 (우측 차트)
# ============================================

@router.get("/users/{user_id}/trend", response_model=Dict[str, Any])
async def get_user_mcdi_trend(
    user_id: str,
    days: int = Query(14, ge=7, le=90),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    선택된 사용자의 MCDI 상세 트렌드 (우측 차트용)

    Returns:
        {
            "user_id": "...",
            "user_name": "홍길동",
            "dates": ["2026-02-20", ...],
            "mcdi": [78.5, 79.2, ...],
            "risk_levels": ["GREEN", ...],
            "metrics": {
                "LR": [75, 80, ...],
                "SD": [...], ...
            }
        }
    """
    try:
        since = datetime.now() - timedelta(days=days)

        # 사용자 확인
        user_q = await db.execute(select(User).where(User.id == user_id))
        user = user_q.scalar_one_or_none()
        if not user:
            return {"error": "User not found"}

        # MCDI 시계열 데이터
        analysis_q = await db.execute(
            select(AnalysisResult)
            .where(and_(
                AnalysisResult.user_id == user_id,
                AnalysisResult.created_at >= since
            ))
            .order_by(AnalysisResult.created_at)
        )
        analyses = analysis_q.scalars().all()

        dates = [a.created_at.strftime("%m/%d") for a in analyses]
        mcdi = [round(a.mcdi_score, 1) if a.mcdi_score else None for a in analyses]
        risk_levels = [a.risk_level for a in analyses]

        metrics = {
            "LR": [round(a.lr_score, 1) if a.lr_score else None for a in analyses],
            "SD": [round(a.sd_score, 1) if a.sd_score else None for a in analyses],
            "NC": [round(a.nc_score, 1) if a.nc_score else None for a in analyses],
            "TO": [round(a.to_score, 1) if a.to_score else None for a in analyses],
            "ER": [round(a.er_score, 1) if a.er_score else None for a in analyses],
            "RT": [round(a.rt_score, 1) if a.rt_score else None for a in analyses],
        }

        # Baseline
        baseline = user.baseline_mcdi

        return {
            "user_id": user_id,
            "user_name": user.email or user.name,
            "garden_name": user.garden_name,
            "dates": dates,
            "mcdi": mcdi,
            "risk_levels": risk_levels,
            "metrics": metrics,
            "baseline": baseline,
            "onboarding_day": user.onboarding_day,
        }

    except Exception as e:
        logger.error(f"User trend error: {e}", exc_info=True)
        return {"error": str(e)}


# ============================================
# 4. 히트맵 데이터 (하단 - 참여 현황)
# ============================================

@router.get("/heatmap", response_model=Dict[str, Any])
async def get_heatmap_data(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    사용자별 · 날짜별 대화 참여 히트맵 데이터

    Returns:
        {
            "dates": ["2026-02-04", "2026-02-05", ...],
            "users": [
                {
                    "user_id": "...",
                    "name": "홍길동",
                    "counts": [2, 0, 3, 1, ...]   # 날짜 순서에 맞게
                },
                ...
            ]
        }
    """
    try:
        now = datetime.now()
        since = now - timedelta(days=days)

        # 날짜 목록 생성
        date_list = [
            (since + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days + 1)
        ]

        # 사용자 전체 조회
        users_q = await db.execute(
            select(User).where(
                and_(User.deleted_at.is_(None), User.onboarding_day >= 1)
            ).order_by(User.name)
        )
        users = users_q.scalars().all()

        # 날짜별·사용자별 대화 수 집계
        conv_q = await db.execute(
            select(
                Conversation.user_id,
                cast(Conversation.created_at, Date).label("conv_date"),
                func.count(Conversation.id).label("cnt")
            )
            .where(Conversation.created_at >= since)
            .group_by(Conversation.user_id, cast(Conversation.created_at, Date))
        )
        conv_rows = conv_q.fetchall()

        # user_id → date → count 매핑
        conv_map: Dict[str, Dict[str, int]] = defaultdict(dict)
        for row in conv_rows:
            uid = str(row[0])
            d = row[1].strftime("%Y-%m-%d") if hasattr(row[1], "strftime") else str(row[1])
            cnt = row[2]
            conv_map[uid][d] = cnt

        heatmap_users = []
        for user in users:
            uid = str(user.id)
            counts = [conv_map.get(uid, {}).get(d, 0) for d in date_list]
            heatmap_users.append({
                "user_id": uid,
                "name": user.email or user.name or "이름 없음",
                "counts": counts,
            })

        return {
            "dates": date_list,
            "users": heatmap_users,
        }

    except Exception as e:
        logger.error(f"Heatmap error: {e}", exc_info=True)
        return {"dates": [], "users": [], "error": str(e)}
