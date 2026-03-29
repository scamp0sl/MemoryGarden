"""
API Schemas 검증 스크립트

모든 스키마 파일을 import하고 기본 검증 수행.

Usage:
    python test_schemas.py
"""

import sys
from datetime import datetime
from pydantic import ValidationError


def test_user_schemas():
    """User 스키마 테스트"""
    print("📝 Testing User schemas...")
    
    from api.schemas import (
        UserCreate, UserUpdate, GuardianCreate,
        UserResponse, UserProfile, GuardianResponse
    )
    
    # UserCreate 정상 케이스
    user = UserCreate(
        kakao_id="1234567890",
        name="홍길동",
        birth_date="1953-05-15",
        gender="male",
        garden_name="수진이네 정원"
    )
    assert user.kakao_id == "1234567890"
    
    # UserCreate 검증 실패 케이스
    try:
        UserCreate(kakao_id="123", name="")  # name 빈 문자열
        assert False, "Should fail validation"
    except ValidationError:
        pass  # 예상된 에러
    
    print("   ✅ User schemas OK")


def test_session_schemas():
    """Session 스키마 테스트"""
    print("📝 Testing Session schemas...")
    
    from api.schemas import (
        SessionCreate, SessionResponse,
        SessionStatusResponse, SessionListResponse
    )
    
    session = SessionCreate(user_id="550e8400-e29b-41d4-a716-446655440000")
    assert session.user_id is not None
    
    print("   ✅ Session schemas OK")


def test_conversation_schemas():
    """Conversation 스키마 테스트"""
    print("📝 Testing Conversation schemas...")
    
    from api.schemas import (
        MessageRequest, ImageMessageRequest, MessageResponse,
        ConversationTurn, ConversationHistory
    )
    
    # MessageRequest 정상 케이스
    msg = MessageRequest(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        message="안녕하세요",
        message_type="text"
    )
    assert msg.message == "안녕하세요"
    
    # MessageRequest 검증 실패
    try:
        MessageRequest(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            message="",  # 빈 메시지
            message_type="text"
        )
        assert False, "Should fail validation"
    except ValidationError:
        pass
    
    print("   ✅ Conversation schemas OK")


def test_memory_schemas():
    """Memory 스키마 테스트"""
    print("📝 Testing Memory schemas...")
    
    from api.schemas import (
        MemorySearchRequest, EpisodicMemory,
        BiographicalFact, EmotionalMemory, MemoryStats
    )
    
    # MemorySearchRequest
    search = MemorySearchRequest(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        query="딸",
        memory_type="episodic",
        limit=10
    )
    assert search.limit == 10
    
    # limit 범위 검증
    try:
        MemorySearchRequest(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            limit=200  # 최대 100
        )
        assert False, "Should fail validation"
    except ValidationError:
        pass
    
    print("   ✅ Memory schemas OK")


def test_garden_schemas():
    """Garden 스키마 테스트"""
    print("📝 Testing Garden schemas...")
    
    from api.schemas import (
        GardenUpdateRequest, GardenStatusResponse,
        GardenUpdateResponse, AchievementListResponse
    )
    
    # GardenStatusResponse
    garden = GardenStatusResponse(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        flower_count=42,
        butterfly_count=5,
        garden_level=3,
        consecutive_days=15,
        total_conversations=42,
        weather="sunny",
        status_message="정원이 건강하게 자라고 있어요!",
        updated_at=datetime.now()
    )
    assert garden.flower_count == 42
    assert garden.weather == "sunny"
    
    # flower_count 음수 검증
    try:
        GardenStatusResponse(
            user_id="550e8400-e29b-41d4-a716-446655440000",
            flower_count=-5,  # 음수 불가
            butterfly_count=0,
            garden_level=1,
            consecutive_days=0,
            total_conversations=0,
            weather="sunny",
            status_message="test",
            updated_at=datetime.now()
        )
        assert False, "Should fail validation"
    except ValidationError:
        pass
    
    print("   ✅ Garden schemas OK")


def test_analysis_schemas():
    """Analysis 스키마 테스트"""
    print("📝 Testing Analysis schemas...")
    
    from api.schemas import (
        AnalysisRequest, MCDIScoreResponse,
        EmotionAnalysisResponse, RiskAssessmentResponse,
        ComprehensiveAnalysisResponse
    )
    
    # AnalysisRequest
    analysis_req = AnalysisRequest(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        message="봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요",
        message_type="text"
    )
    assert analysis_req.message is not None
    
    # EmotionAnalysisResponse
    emotion = EmotionAnalysisResponse(
        primary_emotion="joy",
        emotion_scores={"joy": 0.75, "sadness": 0.05},
        intensity=0.75,
        valence=0.8,
        arousal=0.6,
        confidence=0.92
    )
    assert emotion.primary_emotion == "joy"
    
    # intensity 범위 검증
    try:
        EmotionAnalysisResponse(
            primary_emotion="joy",
            emotion_scores={"joy": 0.75},
            intensity=1.5,  # 최대 1.0
            valence=0.8,
            arousal=0.6,
            confidence=0.92
        )
        assert False, "Should fail validation"
    except ValidationError:
        pass
    
    print("   ✅ Analysis schemas OK")


def test_all_imports():
    """모든 스키마 import 테스트"""
    print("📝 Testing all imports...")
    
    from api.schemas import (
        # User
        UserCreate, UserUpdate, GuardianCreate,
        UserResponse, UserProfile, GuardianResponse, UserListResponse,
        # Session
        SessionCreate, SessionResponse,
        SessionStatusResponse, SessionListResponse,
        # Conversation
        MessageRequest, ImageMessageRequest, MessageResponse,
        ConversationTurn, ConversationHistory, ConversationListResponse,
        # Memory
        MemorySearchRequest, MemorySearchByEmotionRequest,
        EpisodicMemory, BiographicalFact, EmotionalMemory,
        MemorySearchResponse, MemoryStats,
        # Garden
        GardenUpdateRequest, GardenStatusResponse,
        GardenUpdateResponse, GardenHistoryEntry,
        GardenHistoryResponse, AchievementListResponse,
        # Analysis
        AnalysisRequest, IndividualMetricDetail,
        MCDIScoreDetail, MCDIScoreResponse,
        EmotionAnalysisResponse, RiskAssessmentResponse,
        ComprehensiveAnalysisResponse, AnalysisHistoryEntry,
        AnalysisHistoryResponse, MetricComparisonResponse,
    )
    
    print("   ✅ All imports successful")


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🔍 API Schemas Validation Test")
    print("=" * 60)
    print()
    
    try:
        test_all_imports()
        test_user_schemas()
        test_session_schemas()
        test_conversation_schemas()
        test_memory_schemas()
        test_garden_schemas()
        test_analysis_schemas()
        
        print()
        print("=" * 60)
        print("✅ All schema tests passed!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
