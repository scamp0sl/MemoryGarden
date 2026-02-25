"""
API Schemas Package

All Pydantic models for request/response validation.

Author: Memory Garden Team
Created: 2025-02-10
"""

# User schemas
from .user import (
    UserCreate,
    UserUpdate,
    GuardianCreate,
    UserResponse,
    UserProfile,
    GuardianResponse,
    UserListResponse,
)

# Session schemas
from .session import (
    SessionCreate,
    SessionResponse,
    SessionStatusResponse,
    SessionListResponse,
)

# Conversation schemas
from .conversation import (
    MessageRequest,
    ImageMessageRequest,
    MessageResponse,
    ConversationTurn,
    ConversationHistory,
    ConversationListResponse,
)

# Memory schemas
from .memory import (
    MemorySearchRequest,
    MemorySearchByEmotionRequest,
    EpisodicMemory,
    BiographicalFact,
    EmotionalMemory,
    MemorySearchResponse,
    MemoryStats,
)

# Garden schemas
from .garden import (
    GardenUpdateRequest,
    GardenStatusResponse,
    GardenUpdateResponse,
    GardenHistoryEntry,
    GardenHistoryResponse,
    AchievementListResponse,
)

# Analysis schemas
from .analysis import (
    AnalysisRequest,
    IndividualMetricDetail,
    MCDIScoreDetail,
    MCDIScoreResponse,
    EmotionAnalysisResponse,
    RiskAssessmentResponse,
    ComprehensiveAnalysisResponse,
    AnalysisHistoryEntry,
    AnalysisHistoryResponse,
    MetricComparisonResponse,
)


__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "GuardianCreate",
    "UserResponse",
    "UserProfile",
    "GuardianResponse",
    "UserListResponse",
    # Session
    "SessionCreate",
    "SessionResponse",
    "SessionStatusResponse",
    "SessionListResponse",
    # Conversation
    "MessageRequest",
    "ImageMessageRequest",
    "MessageResponse",
    "ConversationTurn",
    "ConversationHistory",
    "ConversationListResponse",
    # Memory
    "MemorySearchRequest",
    "MemorySearchByEmotionRequest",
    "EpisodicMemory",
    "BiographicalFact",
    "EmotionalMemory",
    "MemorySearchResponse",
    "MemoryStats",
    # Garden
    "GardenUpdateRequest",
    "GardenStatusResponse",
    "GardenUpdateResponse",
    "GardenHistoryEntry",
    "GardenHistoryResponse",
    "AchievementListResponse",
    # Analysis
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
