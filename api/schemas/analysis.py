"""
분석 결과 관련 Pydantic 스키마

Author: Memory Garden Team
Created: 2025-02-10
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# 요청 스키마
# ============================================

class AnalysisRequest(BaseModel):
    """분석 요청"""
    user_id: str = Field(..., description="사용자 UUID")
    message: str = Field(..., min_length=1, description="분석할 메시지")
    message_type: str = Field("text", pattern="^(text|image|selection)$", description="메시지 유형")
    image_url: Optional[str] = Field(None, description="이미지 URL (선택)")
    include_history: bool = Field(False, description="과거 분석 히스토리 포함 여부")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요",
                "message_type": "text",
                "image_url": None,
                "include_history": False
            }
        }
    )


# ============================================
# 응답 스키마
# ============================================

class IndividualMetricDetail(BaseModel):
    """개별 지표 상세"""
    score: float = Field(..., ge=0, le=100, description="지표 점수 (0-100)")
    components: Dict[str, Any] = Field(..., description="지표 하위 구성요소")
    interpretation: str = Field(..., description="결과 해석")
    confidence: float = Field(..., ge=0, le=1, description="신뢰도 (0-1)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "score": 78.5,
                "components": {
                    "pronoun_ratio": 0.15,
                    "mattr": 0.72,
                    "concreteness": 0.85,
                    "empty_speech_ratio": 0.05
                },
                "interpretation": "어휘 다양성이 양호하며, 구체적인 명사 사용이 우수합니다.",
                "confidence": 0.92
            }
        }
    )


class MCDIScoreDetail(BaseModel):
    """MCDI 점수 상세"""
    lr_score: Optional[float] = Field(None, ge=0, le=100, description="어휘 풍부도 (Lexical Richness)")
    sd_score: Optional[float] = Field(None, ge=0, le=100, description="의미적 표류 (Semantic Drift)")
    nc_score: Optional[float] = Field(None, ge=0, le=100, description="서사 일관성 (Narrative Coherence)")
    to_score: Optional[float] = Field(None, ge=0, le=100, description="시간적 지남력 (Temporal Orientation)")
    er_score: Optional[float] = Field(None, ge=0, le=100, description="일화 기억 (Episodic Recall)")
    rt_score: Optional[float] = Field(None, ge=0, le=100, description="반응 시간 (Response Time)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "lr_score": 78.5,
                "sd_score": 82.3,
                "nc_score": 75.0,
                "to_score": 88.2,
                "er_score": 80.5,
                "rt_score": 85.0
            }
        }
    )


class MCDIScoreResponse(BaseModel):
    """MCDI 종합 점수 응답"""
    mcdi_score: float = Field(..., ge=0, le=100, description="MCDI 종합 점수 (0-100)")
    scores: MCDIScoreDetail = Field(..., description="개별 지표 점수")
    baseline_score: Optional[float] = Field(None, description="Baseline 점수")
    z_score: Optional[float] = Field(None, description="Z-score (baseline 대비)")
    trend: Optional[str] = Field(None, description="추세 (improving/stable/declining)")
    reliability: float = Field(..., ge=0, le=1, description="신뢰도 (사용된 지표 비율)")
    failed_metrics: list[str] = Field(default_factory=list, description="실패한 지표 목록")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mcdi_score": 81.58,
                "scores": {
                    "lr_score": 78.5,
                    "sd_score": 82.3,
                    "nc_score": 75.0,
                    "to_score": 88.2,
                    "er_score": 80.5,
                    "rt_score": 85.0
                },
                "baseline_score": 83.2,
                "z_score": -0.32,
                "trend": "stable",
                "reliability": 1.0,
                "failed_metrics": []
            }
        }
    )


class EmotionAnalysisResponse(BaseModel):
    """감정 분석 응답"""
    primary_emotion: str = Field(..., description="주 감정 (joy/sadness/anger/fear/surprise/neutral)")
    emotion_scores: Dict[str, float] = Field(..., description="각 감정별 점수 (0-1)")
    intensity: float = Field(..., ge=0, le=1, description="감정 강도")
    valence: float = Field(..., ge=-1, le=1, description="감정 극성 (-1: 부정, 0: 중립, 1: 긍정)")
    arousal: float = Field(..., ge=0, le=1, description="각성 수준")
    confidence: float = Field(..., ge=0, le=1, description="감정 분석 신뢰도")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "primary_emotion": "joy",
                "emotion_scores": {
                    "joy": 0.75,
                    "sadness": 0.05,
                    "anger": 0.02,
                    "fear": 0.03,
                    "surprise": 0.10,
                    "neutral": 0.05
                },
                "intensity": 0.75,
                "valence": 0.8,
                "arousal": 0.6,
                "confidence": 0.92
            }
        }
    )


class RiskAssessmentResponse(BaseModel):
    """위험도 평가 응답"""
    risk_level: str = Field(..., pattern="^(GREEN|YELLOW|ORANGE|RED)$", description="위험도 등급")
    risk_score: float = Field(..., ge=0, le=100, description="위험 점수 (0-100)")
    factors: Dict[str, Any] = Field(..., description="위험 요인 분석")
    recommendation: str = Field(..., description="권고 사항")
    alert_needed: bool = Field(..., description="보호자 알림 필요 여부")
    next_check_date: Optional[datetime] = Field(None, description="다음 검사 권장 일자")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "risk_level": "GREEN",
                "risk_score": 18.5,
                "factors": {
                    "z_score": -0.32,
                    "trend_slope": -0.05,
                    "consecutive_declines": 0,
                    "baseline_deviation": "normal"
                },
                "recommendation": "현재 인지 기능이 정상 범위입니다. 꾸준한 대화 참여를 유지하세요.",
                "alert_needed": False,
                "next_check_date": "2025-02-17T10:00:00Z"
            }
        }
    )


class ComprehensiveAnalysisResponse(BaseModel):
    """종합 분석 결과 응답"""
    user_id: str
    message: str
    
    # MCDI 분석
    mcdi: MCDIScoreResponse
    
    # 감정 분석
    emotion: EmotionAnalysisResponse
    
    # 위험도 평가
    risk: RiskAssessmentResponse
    
    # 개별 지표 상세 (선택)
    lr_detail: Optional[IndividualMetricDetail] = None
    sd_detail: Optional[IndividualMetricDetail] = None
    nc_detail: Optional[IndividualMetricDetail] = None
    to_detail: Optional[IndividualMetricDetail] = None
    er_detail: Optional[IndividualMetricDetail] = None
    rt_detail: Optional[IndividualMetricDetail] = None
    
    # 모순 탐지
    contradictions: list[str] = Field(default_factory=list, description="감지된 모순 목록")
    
    # 메타데이터
    analyzed_at: datetime
    processing_time_ms: float = Field(..., description="처리 시간 (밀리초)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요",
                "mcdi": {
                    "mcdi_score": 81.58,
                    "scores": {
                        "lr_score": 78.5,
                        "sd_score": 82.3,
                        "nc_score": 75.0,
                        "to_score": 88.2,
                        "er_score": 80.5,
                        "rt_score": 85.0
                    },
                    "baseline_score": 83.2,
                    "z_score": -0.32,
                    "trend": "stable",
                    "reliability": 1.0,
                    "failed_metrics": []
                },
                "emotion": {
                    "primary_emotion": "joy",
                    "emotion_scores": {
                        "joy": 0.75,
                        "sadness": 0.05,
                        "anger": 0.02,
                        "fear": 0.03,
                        "surprise": 0.10,
                        "neutral": 0.05
                    },
                    "intensity": 0.75,
                    "valence": 0.8,
                    "arousal": 0.6,
                    "confidence": 0.92
                },
                "risk": {
                    "risk_level": "GREEN",
                    "risk_score": 18.5,
                    "factors": {
                        "z_score": -0.32,
                        "trend_slope": -0.05,
                        "consecutive_declines": 0,
                        "baseline_deviation": "normal"
                    },
                    "recommendation": "현재 인지 기능이 정상 범위입니다. 꾸준한 대화 참여를 유지하세요.",
                    "alert_needed": False,
                    "next_check_date": "2025-02-17T10:00:00Z"
                },
                "contradictions": [],
                "analyzed_at": "2025-02-10T14:30:00Z",
                "processing_time_ms": 1250.5
            }
        }
    )


class AnalysisHistoryEntry(BaseModel):
    """분석 히스토리 항목"""
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    mcdi_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., pattern="^(GREEN|YELLOW|ORANGE|RED)$")
    primary_emotion: str
    emotion_valence: float = Field(..., ge=-1, le=1)
    message_count: int = Field(..., ge=1, description="해당 날짜의 대화 횟수")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2025-02-10",
                "mcdi_score": 81.58,
                "risk_level": "GREEN",
                "primary_emotion": "joy",
                "emotion_valence": 0.8,
                "message_count": 3
            }
        }
    )


class AnalysisHistoryResponse(BaseModel):
    """분석 히스토리 응답"""
    user_id: str
    history: list[AnalysisHistoryEntry]
    start_date: str = Field(..., description="조회 시작 날짜 (YYYY-MM-DD)")
    end_date: str = Field(..., description="조회 종료 날짜 (YYYY-MM-DD)")
    total_entries: int
    
    # 통계
    average_mcdi: float = Field(..., description="평균 MCDI 점수")
    mcdi_trend: str = Field(..., description="MCDI 추세 (improving/stable/declining)")
    dominant_emotion: str = Field(..., description="주요 감정")
    risk_distribution: Dict[str, int] = Field(..., description="위험도별 분포")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "history": [
                    {
                        "date": "2025-02-10",
                        "mcdi_score": 81.58,
                        "risk_level": "GREEN",
                        "primary_emotion": "joy",
                        "emotion_valence": 0.8,
                        "message_count": 3
                    },
                    {
                        "date": "2025-02-09",
                        "mcdi_score": 82.15,
                        "risk_level": "GREEN",
                        "primary_emotion": "neutral",
                        "emotion_valence": 0.2,
                        "message_count": 2
                    }
                ],
                "start_date": "2025-02-01",
                "end_date": "2025-02-10",
                "total_entries": 10,
                "average_mcdi": 81.85,
                "mcdi_trend": "stable",
                "dominant_emotion": "joy",
                "risk_distribution": {
                    "GREEN": 10,
                    "YELLOW": 0,
                    "ORANGE": 0,
                    "RED": 0
                }
            }
        }
    )


class MetricComparisonResponse(BaseModel):
    """지표 비교 응답 (현재 vs Baseline)"""
    user_id: str
    metric_name: str = Field(..., description="지표 이름 (LR/SD/NC/TO/ER/RT)")
    
    current_score: float = Field(..., ge=0, le=100)
    baseline_score: float = Field(..., ge=0, le=100)
    
    difference: float = Field(..., description="차이 (current - baseline)")
    percent_change: float = Field(..., description="변화율 (%)")
    z_score: float = Field(..., description="Z-score")
    
    interpretation: str = Field(..., description="변화 해석")
    is_significant: bool = Field(..., description="통계적 유의성 (|z|>2)")
    
    timestamp: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "metric_name": "LR",
                "current_score": 78.5,
                "baseline_score": 80.2,
                "difference": -1.7,
                "percent_change": -2.12,
                "z_score": -0.42,
                "interpretation": "어휘 풍부도가 baseline 대비 소폭 감소했으나, 정상 범위 내입니다.",
                "is_significant": False,
                "timestamp": "2025-02-10T14:30:00Z"
            }
        }
    )


# ============================================
# Export
# ============================================
__all__ = [
    "AnalysisRequest",
    "IndividualMetricDetail",
    "MCDIScoreDetail",
    "MCDIScoreResponse",
    "EmotionAnalysisResponse",
    "RiskAssessmentResponse",
    "ComprehensiveAnalysisResponse",
    "AnalysisHistoryEntry",
    "AnalysisHistoryResponse",
    "MetricComparisonResponse",
]
