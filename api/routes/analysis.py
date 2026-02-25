"""
분석 결과 API 라우터

MCDI 점수, 감정 분석, 위험도 평가 조회.

Author: Memory Garden Team
Created: 2025-02-10
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    ComprehensiveAnalysisResponse,
    AnalysisHistoryResponse,
    MCDIScoreResponse,
    RiskAssessmentResponse,
    MetricComparisonResponse,
)
from database.postgres import get_db
from core.memory.analytical_memory import create_analytical_memory
from database.timescale import TimescaleDB
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


# ============================================
# 주간/월간 분석 조회
# ============================================

@router.get("/users/{user_id}/analysis/weekly")
async def get_weekly_analysis(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    주간 분석 리포트 조회
    
    지난 7일간의 데이터를 분석하여 리포트 생성.
    매주 일요일 자동 생성되며, API로 조회 가능.
    
    Returns:
        WeeklyReport with:
        - MCDI 점수 변화 (평균, 추세, 기울기)
        - 감정 분포 (joy/sadness/anger 비율)
        - 위험도 평가
        - 참여 지표 (대화 횟수, 연속 참여 일수)
        - AI 관찰 및 권장 사항
    """
    try:
        logger.info(f"Getting weekly analysis: user_id={user_id}")
        
        # TODO: ReportGenerator 주입
        # from core.analysis.report_generator import ReportGenerator
        # 
        # report_generator = ReportGenerator(db)
        # weekly_report = await report_generator.generate_weekly_report(
        #     user_id=user_id,
        #     user_name="홍길동",  # DB에서 가져오기
        #     report_type=ReportType.GUARDIAN
        # )
        # 
        # return weekly_report
        
        raise HTTPException(
            status_code=501,
            detail="ReportGenerator not fully integrated yet. Please implement services/analysis_service.py"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get weekly analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{user_id}/analysis/monthly")
async def get_monthly_analysis(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    월간 분석 리포트 조회
    
    지난 30일간의 데이터를 분석하여 리포트 생성.
    매월 1일 자동 생성.
    
    Returns:
        MonthlyReport with:
        - 장기 추세 분석
        - 인지 기능 변화 (baseline 대비)
        - 감정 패턴 분석
        - 정원 성장 지표
        - 상세 권장 사항
    """
    try:
        logger.info(f"Getting monthly analysis: user_id={user_id}")
        
        # TODO: ReportGenerator.generate_monthly_report()
        raise HTTPException(
            status_code=501,
            detail="Monthly report generation not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get monthly analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")




# ============================================
# MCDI 점수 조회
# ============================================

@router.get("/users/{user_id}/mcdi", response_model=MCDIScoreResponse)
async def get_mcdi_score(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    현재 MCDI 점수 조회
    
    Returns:
        MCDIScoreResponse with:
        - mcdi_score: 종합 점수
        - scores: 6개 개별 지표 (LR, SD, NC, TO, ER, RT)
        - baseline_score: Baseline 점수
        - z_score: Baseline 대비 Z-score
        - trend: 추세 (improving/stable/declining)
    """
    try:
        logger.info(f"Getting MCDI score: user_id={user_id}")
        
        # TODO: AnalysisService.get_current_mcdi()
        raise HTTPException(
            status_code=501,
            detail="MCDI score retrieval not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MCDI score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{user_id}/risk", response_model=RiskAssessmentResponse)
async def get_risk_assessment(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    현재 위험도 평가 조회
    
    Returns:
        RiskAssessmentResponse with:
        - risk_level: GREEN/YELLOW/ORANGE/RED
        - risk_score: 위험 점수 (0-100)
        - factors: 위험 요인 분석
        - recommendation: 권고 사항
        - alert_needed: 보호자 알림 필요 여부
    """
    try:
        logger.info(f"Getting risk assessment: user_id={user_id}")
        
        # TODO: RiskEvaluator.evaluate()
        raise HTTPException(
            status_code=501,
            detail="Risk assessment not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get risk assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# 지표 비교 (현재 vs Baseline)
# ============================================

@router.get("/users/{user_id}/metrics/{metric_name}/comparison", response_model=MetricComparisonResponse)
async def compare_metric(
    user_id: str,
    metric_name: str = Path(..., pattern="^(LR|SD|NC|TO|ER|RT)$", description="지표 이름"),
    db: AsyncSession = Depends(get_db)
):
    """
    개별 지표 비교 (현재 vs Baseline)
    
    Args:
        user_id: 사용자 UUID
        metric_name: LR/SD/NC/TO/ER/RT
    
    Returns:
        MetricComparisonResponse with:
        - current_score, baseline_score
        - difference, percent_change, z_score
        - interpretation: 변화 해석
        - is_significant: 통계적 유의성
    """
    try:
        logger.info(f"Comparing metric: user_id={user_id}, metric={metric_name}")
        
        # TODO: AnalysisService.compare_metric()
        raise HTTPException(
            status_code=501,
            detail="Metric comparison not implemented yet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare metric: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# Task 5: 분석 결과 조회 엔드포인트
# ============================================

@router.get("/users/{user_id}/analysis/latest")
async def get_latest_analysis(
    user_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    **최근 MCDI 분석 결과 조회**

    사용자의 가장 최근 MCDI 분석 결과를 반환합니다.
    TimescaleDB에서 조회합니다.

    Args:
        user_id: 사용자 ID

    Returns:
        {
            "user_id": "user123",
            "mcdi_score": 78.5,
            "scores": {
                "LR": 78.5,
                "SD": 82.3,
                "NC": 75.0,
                "TO": 80.0,
                "ER": 72.5,
                "RT": 70.0
            },
            "risk_level": "GREEN",
            "timestamp": "2026-02-11T16:00:00Z",
            "baseline": {
                "mean": 80.0,
                "std": 5.0
            },
            "z_score": -0.3
        }

    Example:
        GET /api/v1/analysis/users/user123/analysis/latest
    """
    try:
        logger.info(f"Getting latest analysis for user: {user_id}")

        # AnalyticalMemory를 통해 TimescaleDB 조회
        analytical = await create_analytical_memory()

        # 최근 1개 점수 조회
        recent_scores = await analytical.get_recent_scores(user_id, days=7, limit=1)

        if not recent_scores:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis found for user: {user_id}"
            )

        latest = recent_scores[0]

        # Baseline 조회
        baseline = await analytical.get_baseline(user_id, days=90)

        # z-score 계산
        if baseline["sample_size"] > 0 and baseline["std"] > 0:
            z_score = (latest["mcdi_score"] - baseline["mean"]) / baseline["std"]
        else:
            z_score = 0.0

        response = {
            "user_id": user_id,
            "mcdi_score": latest["mcdi_score"],
            "scores": {
                "LR": latest["lr_score"],
                "SD": latest["sd_score"],
                "NC": latest["nc_score"],
                "TO": latest["to_score"],
                "ER": latest["er_score"],
                "RT": latest["rt_score"]
            },
            "risk_level": latest["risk_level"],
            "timestamp": latest["timestamp"].isoformat() if latest["timestamp"] else None,
            "baseline": {
                "mean": baseline["mean"],
                "std": baseline["std"],
                "sample_size": baseline["sample_size"]
            },
            "z_score": round(z_score, 2)
        }

        logger.info(
            f"Retrieved latest analysis",
            extra={
                "user_id": user_id,
                "mcdi_score": latest["mcdi_score"],
                "risk_level": latest["risk_level"]
            }
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve latest analysis: {str(e)}"
        )


@router.get("/users/{user_id}/analysis/history")
async def get_analysis_history(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="조회 기간 (일)"),
    metric: str = Query("mcdi_score", description="조회 지표 (mcdi_score/lr_score/...)"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    **MCDI 시계열 데이터 조회 (그래프용)**

    사용자의 MCDI 점수 변화 추이를 시계열 데이터로 반환합니다.
    TimescaleDB의 시계열 기능을 활용합니다.

    Args:
        user_id: 사용자 ID
        days: 조회 기간 (일) - 기본 30일, 최대 365일
        metric: 조회 지표 (mcdi_score/lr_score/sd_score/...)

    Returns:
        {
            "user_id": "user123",
            "metric": "mcdi_score",
            "period_days": 30,
            "data": [
                {"time": "2026-02-01T00:00:00Z", "value": 78.5},
                {"time": "2026-02-02T00:00:00Z", "value": 79.2},
                ...
            ],
            "statistics": {
                "mean": 78.5,
                "min": 70.0,
                "max": 85.0,
                "trend": "stable"
            }
        }

    Example:
        GET /api/v1/analysis/users/user123/analysis/history?days=30&metric=mcdi_score
    """
    try:
        logger.info(
            f"Getting analysis history",
            extra={
                "user_id": user_id,
                "days": days,
                "metric": metric
            }
        )

        # TimescaleDB 초기화
        timescale = TimescaleDB()
        await timescale.connect()

        try:
            # 시계열 데이터 조회
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()

            timeseries_data = await timescale.get_timeseries(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                metric=metric
            )

            # 집계 통계 조회
            aggregate_stats = await timescale.get_aggregate_stats(
                user_id=user_id,
                days=days
            )

            # 추세 계산 (기울기)
            slope, direction = await timescale.calculate_slope(
                user_id=user_id,
                weeks=min(4, days // 7)
            )

            response = {
                "user_id": user_id,
                "metric": metric,
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": timeseries_data,
                "data_points": len(timeseries_data),
                "statistics": {
                    "mean": aggregate_stats.get("mcdi", {}).get("mean", 0),
                    "min": aggregate_stats.get("mcdi", {}).get("min", 0),
                    "max": aggregate_stats.get("mcdi", {}).get("max", 0),
                    "median": aggregate_stats.get("mcdi", {}).get("median", 0),
                    "trend": direction,
                    "slope": slope
                }
            }

            logger.info(
                f"Retrieved {len(timeseries_data)} data points",
                extra={
                    "user_id": user_id,
                    "data_points": len(timeseries_data),
                    "trend": direction
                }
            )

            return response

        finally:
            await timescale.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis history: {str(e)}"
        )


@router.get("/users/{user_id}/analysis/report")
async def generate_analysis_report(
    user_id: str,
    report_type: str = Query("weekly", description="리포트 타입 (weekly/monthly)"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    **주간/월간 분석 리포트 생성**

    사용자의 MCDI 분석 결과를 종합하여 리포트를 생성합니다.
    - 주간 리포트: 최근 7일
    - 월간 리포트: 최근 30일

    Args:
        user_id: 사용자 ID
        report_type: 리포트 타입 (weekly/monthly)

    Returns:
        {
            "user_id": "user123",
            "report_type": "weekly",
            "period": {
                "start": "2026-02-04",
                "end": "2026-02-11"
            },
            "summary": {
                "average_mcdi": 78.5,
                "mcdi_change": -2.3,
                "risk_level": "GREEN",
                "total_conversations": 15
            },
            "metrics": {
                "LR": {"average": 78.5, "change": -1.2},
                "SD": {"average": 82.3, "change": +0.5},
                ...
            },
            "insights": [
                "어휘 풍부도가 약간 감소했습니다.",
                "일관된 대화 참여를 보이고 있습니다."
            ],
            "recommendations": [
                "가족과의 대화 시간을 늘려보세요.",
                "새로운 취미 활동을 시도해보세요."
            ]
        }

    Example:
        GET /api/v1/analysis/users/user123/analysis/report?report_type=weekly
    """
    try:
        logger.info(
            f"Generating analysis report",
            extra={
                "user_id": user_id,
                "report_type": report_type
            }
        )

        # 리포트 기간 설정
        if report_type == "weekly":
            days = 7
        elif report_type == "monthly":
            days = 30
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report_type: {report_type}. Use 'weekly' or 'monthly'."
            )

        # TimescaleDB 초기화
        timescale = TimescaleDB()
        await timescale.connect()

        try:
            # 기간 설정
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 최근 점수 조회
            recent_scores = await timescale.get_recent_scores(
                user_id=user_id,
                days=days,
                limit=1000
            )

            if not recent_scores:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data found for user: {user_id} in the last {days} days"
                )

            # 집계 통계
            aggregate_stats = await timescale.get_aggregate_stats(
                user_id=user_id,
                days=days
            )

            # 추세 계산
            slope, direction = await timescale.calculate_slope(
                user_id=user_id,
                weeks=min(4, days // 7)
            )

            # Baseline 대비 변화
            baseline = await timescale.get_baseline(
                user_id=user_id,
                days=90
            )

            current_avg = aggregate_stats.get("mcdi", {}).get("mean", 0)
            mcdi_change = current_avg - baseline["mean"]

            # 인사이트 생성 (간단한 규칙 기반)
            insights = []
            if slope < -0.5:
                insights.append(f"{days}일간 MCDI 점수가 주당 {abs(slope):.1f}점씩 감소하고 있습니다.")
            elif slope > 0.5:
                insights.append(f"{days}일간 MCDI 점수가 주당 {slope:.1f}점씩 증가하고 있습니다.")
            else:
                insights.append("MCDI 점수가 안정적으로 유지되고 있습니다.")

            if len(recent_scores) >= days:
                insights.append(f"일관된 대화 참여를 보이고 있습니다 ({len(recent_scores)}회 대화).")
            else:
                insights.append(f"대화 참여가 {len(recent_scores)}회로 다소 적습니다. 더 자주 대화해보세요.")

            # 권장 사항
            recommendations = []
            if current_avg < baseline["mean"] - baseline["std"]:
                recommendations.append("최근 점수가 평소보다 낮습니다. 충분한 휴식을 취하세요.")
            if aggregate_stats.get("lr", {}).get("mean", 0) < 70:
                recommendations.append("어휘 다양성을 높이기 위해 독서나 새로운 활동을 해보세요.")

            # 응답 구성
            response = {
                "user_id": user_id,
                "report_type": report_type,
                "period": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d"),
                    "days": days
                },
                "summary": {
                    "average_mcdi": round(current_avg, 2),
                    "mcdi_change": round(mcdi_change, 2),
                    "baseline_mean": round(baseline["mean"], 2),
                    "risk_level": recent_scores[-1]["risk_level"] if recent_scores else "UNKNOWN",
                    "total_conversations": len(recent_scores),
                    "trend": direction
                },
                "metrics": {
                    "LR": {
                        "average": round(aggregate_stats.get("lr", {}).get("mean", 0), 2)
                    },
                    "SD": {
                        "average": round(aggregate_stats.get("sd", {}).get("mean", 0), 2)
                    },
                    "NC": {
                        "average": round(aggregate_stats.get("nc", {}).get("mean", 0), 2)
                    },
                    "TO": {
                        "average": round(aggregate_stats.get("to", {}).get("mean", 0), 2)
                    },
                    "ER": {
                        "average": round(aggregate_stats.get("er", {}).get("mean", 0), 2)
                    },
                    "RT": {
                        "average": round(aggregate_stats.get("rt", {}).get("mean", 0), 2)
                    }
                },
                "insights": insights,
                "recommendations": recommendations if recommendations else ["현재 상태가 양호합니다. 계속 유지하세요!"],
                "generated_at": datetime.now().isoformat()
            }

            logger.info(
                f"Generated {report_type} report",
                extra={
                    "user_id": user_id,
                    "conversations": len(recent_scores),
                    "average_mcdi": current_avg
                }
            )

            return response

        finally:
            await timescale.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate analysis report: {str(e)}"
        )
