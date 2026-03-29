# API Schemas

Pydantic 모델 기반 API 요청/응답 스키마 정의.

## 📋 파일 구조

```
api/schemas/
├── __init__.py           # 모든 스키마 export
├── user.py              # 사용자 관련 스키마
├── session.py           # 세션 관련 스키마
├── conversation.py      # 대화 관련 스키마
├── memory.py            # 기억 관련 스키마
├── garden.py            # 정원 상태 스키마
└── analysis.py          # 분석 결과 스키마
```

## 🎯 스키마 카테고리

### 1. User (사용자)

**사용자 및 보호자 관련 스키마**

#### 요청 스키마
- `UserCreate`: 사용자 생성 (kakao_id, name, birth_date, gender, garden_name)
- `UserUpdate`: 사용자 정보 수정
- `GuardianCreate`: 보호자 등록 (name, relationship, phone, email)

#### 응답 스키마
- `UserResponse`: 사용자 기본 정보 (baseline_mcdi, current_mcdi, risk_level 포함)
- `UserProfile`: 사용자 상세 프로필 (garden_status 포함)
- `GuardianResponse`: 보호자 정보
- `UserListResponse`: 사용자 목록 (페이지네이션)

```python
# Example: 사용자 생성
user_data = UserCreate(
    kakao_id="1234567890",
    name="홍길동",
    birth_date="1953-05-15",
    gender="male",
    garden_name="수진이네 정원"
)
```

---

### 2. Session (세션)

**대화 세션 관리 스키마**

#### 요청 스키마
- `SessionCreate`: 세션 생성 (user_id)

#### 응답 스키마
- `SessionResponse`: 세션 정보 (status, started_at, conversation_count)
- `SessionStatusResponse`: 세션 상태 조회 (elapsed_time_seconds)
- `SessionListResponse`: 세션 목록 (페이지네이션)

```python
# Example: 세션 생성
session = SessionCreate(user_id="550e8400-e29b-41d4-a716-446655440000")
```

---

### 3. Conversation (대화)

**메시지 송수신 및 대화 히스토리 스키마**

#### 요청 스키마
- `MessageRequest`: 텍스트 메시지 전송 (message, message_type, image_url)
- `ImageMessageRequest`: 이미지 메시지 전송

#### 응답 스키마
- `MessageResponse`: AI 응답 (response, mcdi_score, risk_level, garden_status, achievements, level_up)
- `ConversationTurn`: 대화 턴 (user_message + assistant_message)
- `ConversationHistory`: 대화 히스토리 (turns, total_count)
- `ConversationListResponse`: 대화 목록 (페이지네이션)

```python
# Example: 메시지 전송
message = MessageRequest(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    message="오늘 점심에 된장찌개 먹었어요",
    message_type="text"
)
```

---

### 4. Memory (기억)

**4계층 메모리 시스템 스키마**

#### 요청 스키마
- `MemorySearchRequest`: 기억 검색 (query, memory_type, start_date, end_date, limit)
- `MemorySearchByEmotionRequest`: 감정별 기억 검색

#### 응답 스키마
- `EpisodicMemory`: 일화 기억 (content, importance, confidence, emotion)
- `BiographicalFact`: 전기적 사실 (entity, value, fact_type, confidence)
- `EmotionalMemory`: 감정 기억 (emotion, intensity, trigger)
- `MemorySearchResponse`: 검색 결과 (3가지 메모리 통합)
- `MemoryStats`: 기억 통계 (total counts, retention_rate)

```python
# Example: 기억 검색
search = MemorySearchRequest(
    user_id="550e8400-e29b-41d4-a716-446655440000",
    query="딸",
    memory_type="episodic",
    limit=10
)
```

---

### 5. Garden (정원)

**게이미피케이션 정원 상태 스키마**

#### 요청 스키마
- `GardenUpdateRequest`: 정원 상태 업데이트 (테스트/관리자용)

#### 응답 스키마
- `GardenStatusResponse`: 정원 상태 조회
  - **게임 메카닉**: flower_count, butterfly_count, garden_level, consecutive_days
  - **정원 상태**: weather (sunny/cloudy/rainy/stormy), season_badge
  - **메시지**: status_message, achievement_message, next_milestone
- `GardenUpdateResponse`: 정원 업데이트 결과 (previous_status, current_status, achievements_unlocked, level_up, new_badge)
- `GardenHistoryEntry`: 정원 히스토리 항목
- `GardenHistoryResponse`: 정원 히스토리 (history, start_date, end_date)
- `AchievementListResponse`: 업적 목록 (achievements, total_count, latest_achievement)

```python
# Example: 정원 상태 조회 응답
{
    "flower_count": 42,
    "butterfly_count": 5,
    "garden_level": 3,
    "consecutive_days": 15,
    "weather": "sunny",
    "season_badge": "winter",
    "status_message": "정원이 건강하게 자라고 있어요! ☀️",
    "next_milestone": "🦋 1일 더 참여하면 나비가 날아와요!"
}
```

---

### 6. Analysis (분석)

**MCDI 점수, 감정 분석, 위험도 평가 스키마**

#### 요청 스키마
- `AnalysisRequest`: 분석 요청 (message, message_type, include_history)

#### 응답 스키마
- `IndividualMetricDetail`: 개별 지표 상세 (score, components, interpretation, confidence)
- `MCDIScoreDetail`: MCDI 6개 지표 점수 (LR, SD, NC, TO, ER, RT)
- `MCDIScoreResponse`: MCDI 종합 점수 (mcdi_score, z_score, trend, reliability)
- `EmotionAnalysisResponse`: 감정 분석 (primary_emotion, emotion_scores, intensity, valence, arousal)
- `RiskAssessmentResponse`: 위험도 평가 (risk_level, risk_score, factors, recommendation, alert_needed)
- `ComprehensiveAnalysisResponse`: 종합 분석 결과 (MCDI + Emotion + Risk + 개별 지표 상세)
- `AnalysisHistoryEntry`: 분석 히스토리 항목
- `AnalysisHistoryResponse`: 분석 히스토리 (average_mcdi, mcdi_trend, dominant_emotion, risk_distribution)
- `MetricComparisonResponse`: 지표 비교 (current vs baseline)

```python
# Example: 종합 분석 결과
{
    "mcdi": {
        "mcdi_score": 81.58,
        "scores": {"lr_score": 78.5, "sd_score": 82.3, ...},
        "z_score": -0.32,
        "trend": "stable",
        "reliability": 1.0
    },
    "emotion": {
        "primary_emotion": "joy",
        "intensity": 0.75,
        "valence": 0.8,
        "confidence": 0.92
    },
    "risk": {
        "risk_level": "GREEN",
        "risk_score": 18.5,
        "alert_needed": false
    }
}
```

---

## 🔍 주요 특징

### 1. Pydantic v2 사용
- `ConfigDict`로 설정 관리
- `json_schema_extra`로 OpenAPI 예시 자동 생성
- 강력한 타입 검증 및 직렬화

### 2. OpenAPI 통합
모든 스키마에 `json_schema_extra` 포함:
```python
model_config = ConfigDict(
    json_schema_extra={
        "example": {
            # 실제 사용 예시
        }
    }
)
```

FastAPI에서 자동으로 Swagger UI에 예시가 표시됩니다.

### 3. 상세한 Field 설명
```python
class UserCreate(BaseModel):
    kakao_id: str = Field(..., description="카카오톡 사용자 ID")
    name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")
    birth_date: Optional[str] = Field(None, description="생년월일 (YYYY-MM-DD)")
```

### 4. 검증 규칙
- 문자열 길이 제한 (`min_length`, `max_length`)
- 숫자 범위 제한 (`ge`, `le`)
- 정규식 패턴 (`pattern`)
- 이메일 형식 (`EmailStr`)

---

## 📝 사용 예시

### API 라우트에서 사용

```python
from fastapi import APIRouter
from api.schemas import MessageRequest, MessageResponse

router = APIRouter(prefix="/api/v1/conversation", tags=["Conversation"])

@router.post("/message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    """메시지 전송 및 AI 응답 생성"""
    # request.user_id, request.message 자동 검증
    response = await process_message(request)
    return response  # MessageResponse로 자동 직렬화
```

### 응답 생성

```python
from api.schemas import GardenStatusResponse

garden_status = GardenStatusResponse(
    user_id=user_id,
    flower_count=42,
    butterfly_count=5,
    garden_level=3,
    consecutive_days=15,
    total_conversations=42,
    weather="sunny",
    season_badge="winter",
    status_message="정원이 건강하게 자라고 있어요! ☀️",
    next_milestone="🦋 1일 더 참여하면 나비가 날아와요!",
    updated_at=datetime.now()
)
```

---

## ✅ 검증

### Import 테스트
```bash
python test_schemas.py
```

### Pydantic 검증 예시
```python
from api.schemas import UserCreate
from pydantic import ValidationError

# ✅ 정상 케이스
user = UserCreate(kakao_id="123", name="홍길동")

# ❌ 검증 실패
try:
    user = UserCreate(kakao_id="123", name="")  # name 길이 1 미만
except ValidationError as e:
    print(e.errors())
```

---

## 📚 참고 자료

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [FastAPI Schema Documentation](https://fastapi.tiangolo.com/tutorial/body/)
- SPEC.md 2.1 (MCDI 지표)
- SPEC.md 2.2 (게이미피케이션)
- SPEC.md 2.3 (4계층 메모리)

---

**Author**: Memory Garden Team  
**Created**: 2025-02-10  
**Last Updated**: 2025-02-10
