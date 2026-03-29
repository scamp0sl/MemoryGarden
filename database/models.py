"""
PostgreSQL 데이터베이스 모델

SQLAlchemy ORM 모델 정의.

Author: Memory Garden Team
Created: 2025-02-11
"""

from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Float, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


# ============================================
# User 모델
# ============================================

class User(Base):
    """사용자 테이블"""
    __tablename__ = "users"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 기본 정보
    kakao_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    birth_date = Column(DateTime, nullable=True)
    gender = Column(String(10), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)

    # Baseline 정보
    baseline_mcdi = Column(Float, nullable=True)
    baseline_established_at = Column(DateTime, nullable=True)

    # 카카오 OAuth 토큰 (2026-02-12 추가)
    kakao_access_token = Column(Text, nullable=True)
    kakao_refresh_token = Column(Text, nullable=True)
    kakao_token_expires_at = Column(DateTime, nullable=True)
    kakao_refresh_token_expires_at = Column(DateTime, nullable=True)

    # 카카오 채널 챗봇 사용자 키 (2026-02-24 추가)
    kakao_channel_user_key = Column(String(255), unique=True, nullable=True, index=True)

    # 온보딩 및 정원 정보 (2026-02-27 추가)
    garden_name = Column(String(100), nullable=True)
    onboarding_day = Column(Integer, default=0, nullable=False)
    last_interaction_at = Column(DateTime, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="user", cascade="all, delete-orphan")
    fcm_tokens = relationship("FCMToken", back_populates="user", cascade="all, delete-orphan")
    garden_status = relationship("GardenStatus", back_populates="user", uselist=False, cascade="all, delete-orphan")


# ============================================
# Conversation 모델
# ============================================

class Conversation(Base):
    """대화 테이블"""
    __tablename__ = "conversations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 메시지 내용
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    message_type = Column(String(20), default="text")  # text/image/selection
    image_url = Column(Text, nullable=True)

    # 분류
    category = Column(String(50), nullable=True)  # reminiscence/daily_episodic/naming/...

    # 성능 메트릭
    response_latency_ms = Column(Integer, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now, index=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    analysis_result = relationship("AnalysisResult", back_populates="conversation", uselist=False)

    # Indexes
    __table_args__ = (
        Index("idx_conversations_user_created", "user_id", "created_at"),
        Index("idx_conversations_category", "category"),
        Index("idx_conversations_created_desc", "created_at"),
    )


# ============================================
# AnalysisResult 모델
# ============================================

class AnalysisResult(Base):
    """분석 결과 테이블"""
    __tablename__ = "analysis_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # 종합 점수
    mcdi_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # GREEN/YELLOW/ORANGE/RED

    # 6개 지표
    lr_score = Column(Float, nullable=True)
    lr_detail = Column(JSONB, nullable=True)

    sd_score = Column(Float, nullable=True)
    sd_detail = Column(JSONB, nullable=True)

    nc_score = Column(Float, nullable=True)
    nc_detail = Column(JSONB, nullable=True)

    to_score = Column(Float, nullable=True)
    to_detail = Column(JSONB, nullable=True)

    er_score = Column(Float, nullable=True)
    er_detail = Column(JSONB, nullable=True)

    rt_score = Column(Float, nullable=True)
    rt_detail = Column(JSONB, nullable=True)

    # 메타데이터
    contradictions = Column(JSONB, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship("User", back_populates="analysis_results")
    conversation = relationship("Conversation", back_populates="analysis_result")

    # Indexes
    __table_args__ = (
        Index("idx_analysis_user_created", "user_id", "created_at"),
        Index("idx_analysis_risk_level", "risk_level"),
    )


# ============================================
# FCMToken 모델 (푸시 알림)
# ============================================

class FCMToken(Base):
    """FCM 푸시 토큰 테이블"""
    __tablename__ = "fcm_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)

    # 기기 정보
    device_type = Column(String(20))  # android, ios, web
    device_id = Column(String(100), nullable=True)
    device_name = Column(String(100), nullable=True)

    # 상태
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, default=datetime.now)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship("User", back_populates="fcm_tokens")

    # Indexes
    __table_args__ = (
        Index("idx_fcm_tokens_user", "user_id"),
        Index("idx_fcm_tokens_active", "is_active"),
    )


# ============================================
# GardenStatus 모델
# ============================================

class GardenStatus(Base):
    """정원 상태 테이블 (게이미피케이션)"""
    __tablename__ = "garden_status"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # 정원 아이템
    flower_count = Column(Integer, default=0, nullable=False)
    butterfly_count = Column(Integer, default=0, nullable=False)

    # 연속 일수
    consecutive_days = Column(Integer, default=0, nullable=False)
    total_conversations = Column(Integer, default=0, nullable=False)

    # 레벨 및 배지
    garden_level = Column(Integer, default=1, nullable=False)
    season_badge = Column(String(50), nullable=True)

    # 타임스탬프
    last_interaction_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship("User", back_populates="garden_status")


# ============================================
# Export
# ============================================
__all__ = [
    "Base",
    "User",
    "Conversation",
    "AnalysisResult",
    "FCMToken",
    "GardenStatus",
]
