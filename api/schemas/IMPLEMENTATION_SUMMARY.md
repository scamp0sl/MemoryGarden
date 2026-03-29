# API Schemas 구현 완료 보고서

**작성일**: 2025-02-10  
**작성자**: Memory Garden Team  
**상태**: ✅ 완료

---

## 📋 구현 개요

api/schemas/ 디렉토리에 6개의 Pydantic v2 스키마 파일을 완성했습니다.  
모든 스키마는 FastAPI의 OpenAPI 문서 자동 생성을 위한 `json_schema_extra` 예시를 포함합니다.

---

## ✅ 완료된 파일 (6개)

### 1. **user.py** (7개 클래스)
```python
# 요청
- UserCreate: 사용자 생성 (kakao_id, name, birth_date, gender, garden_name)
- UserUpdate: 사용자 정보 수정
- GuardianCreate: 보호자 등록 (name, relationship, phone, email)

# 응답
- UserResponse: 사용자 기본 정보 (baseline_mcdi, current_mcdi, risk_level)
- UserProfile: 사용자 상세 프로필 (garden_status 포함)
- GuardianResponse: 보호자 정보
- UserListResponse: 사용자 목록 (페이지네이션)
```

**주요 필드**:
- baseline_mcdi / current_mcdi (인지 기능 점수)
- risk_level (GREEN/YELLOW/ORANGE/RED)
- consecutive_days (연속 참여 일수)
- total_conversations (총 대화 횟수)

---

### 2. **session.py** (4개 클래스)
```python
# 요청
- SessionCreate: 세션 생성 (user_id)

# 응답
- SessionResponse: 세션 정보 (status, started_at, conversation_count)
- SessionStatusResponse: 세션 상태 조회 (elapsed_time_seconds)
- SessionListResponse: 세션 목록 (페이지네이션)
```

**상태 관리**:
- status: active / completed / cancelled
- elapsed_time_seconds: 경과 시간
- conversation_count: 세션 내 대화 횟수

---

### 3. **conversation.py** (6개 클래스)
```python
# 요청
- MessageRequest: 텍스트 메시지 전송 (message, message_type, image_url)
- ImageMessageRequest: 이미지 메시지 전송

# 응답
- MessageResponse: AI 응답 (response, mcdi_score, risk_level, garden_status, achievements, level_up)
- ConversationTurn: 대화 턴 (user_message + assistant_message)
- ConversationHistory: 대화 히스토리 (turns, total_count)
- ConversationListResponse: 대화 목록 (페이지네이션)
```

**핵심 응답 필드 (MessageResponse)**:
- response: AI 응답 메시지
- mcdi_score: MCDI 점수
- risk_level: 위험도
- garden_status: 정원 상태 (flower_count, weather 등)
- achievements: 달성한 업적 목록
- level_up: 레벨 업 여부

---

### 4. **memory.py** (7개 클래스)
```python
# 요청
- MemorySearchRequest: 기억 검색 (query, memory_type, start_date, end_date, limit)
- MemorySearchByEmotionRequest: 감정별 기억 검색

# 응답
- EpisodicMemory: 일화 기억 (content, importance, confidence, emotion)
- BiographicalFact: 전기적 사실 (entity, value, fact_type, confidence)
- EmotionalMemory: 감정 기억 (emotion, intensity, trigger)
- MemorySearchResponse: 검색 결과 (3가지 메모리 통합)
- MemoryStats: 기억 통계 (total counts, retention_rate)
```

**4계층 메모리 시스템**:
1. Session Memory (Redis)
2. Episodic Memory (Qdrant) - 일화 기억
3. Biographical Memory (Qdrant + PostgreSQL) - 전기적 사실
4. Analytical Memory (TimescaleDB) - 분석 기록

---

### 5. **garden.py** (6개 클래스)
```python
# 요청
- GardenUpdateRequest: 정원 상태 업데이트 (테스트/관리자용)

# 응답
- GardenStatusResponse: 정원 상태 조회
- GardenUpdateResponse: 정원 업데이트 결과
- GardenHistoryEntry: 정원 히스토리 항목
- GardenHistoryResponse: 정원 히스토리
- AchievementListResponse: 업적 목록
```

**게임 메카닉 (SPEC.md 2.2.1 기반)**:
- 🌸 **flower_count**: 1 대화 = 1 꽃
- 🦋 **butterfly_count**: 3일 연속 = 1 나비
- 🌳 **garden_level**: 7일 연속마다 +1 레벨
- 🏅 **season_badge**: 30일 = 계절 뱃지

**날씨 매핑 (위험도 → 날씨)**:
- GREEN → ☀️ sunny
- YELLOW → ☁️ cloudy
- ORANGE → 🌧️ rainy
- RED → ⛈️ stormy

---

### 6. **analysis.py** (10개 클래스) ⭐ 신규 완성
```python
# 요청
- AnalysisRequest: 분석 요청 (message, message_type, include_history)

# 응답
- IndividualMetricDetail: 개별 지표 상세 (score, components, interpretation, confidence)
- MCDIScoreDetail: MCDI 6개 지표 점수 (LR, SD, NC, TO, ER, RT)
- MCDIScoreResponse: MCDI 종합 점수 (mcdi_score, z_score, trend, reliability)
- EmotionAnalysisResponse: 감정 분석 (primary_emotion, emotion_scores, intensity, valence, arousal)
- RiskAssessmentResponse: 위험도 평가 (risk_level, risk_score, factors, recommendation, alert_needed)
- ComprehensiveAnalysisResponse: 종합 분석 결과 (MCDI + Emotion + Risk + 개별 지표 상세)
- AnalysisHistoryEntry: 분석 히스토리 항목
- AnalysisHistoryResponse: 분석 히스토리
- MetricComparisonResponse: 지표 비교 (current vs baseline)
```

**MCDI 6개 지표 (Fraser et al. 2016)**:
1. **LR** (Lexical Richness): 어휘 풍부도
2. **SD** (Semantic Drift): 의미적 표류
3. **NC** (Narrative Coherence): 서사 일관성
4. **TO** (Temporal Orientation): 시간적 지남력
5. **ER** (Episodic Recall): 일화 기억
6. **RT** (Response Time): 반응 시간

**위험도 4단계**:
- GREEN: 정상 (z-score > -1.5)
- YELLOW: 경계 (-2.0 < z-score ≤ -1.5)
- ORANGE: 위험 (-2.5 < z-score ≤ -2.0 또는 하락 추세)
- RED: 고위험 (z-score ≤ -2.5 또는 급격한 하락)

---

## 📊 통계

### 파일 크기
```
user.py         : 245 lines, 10.2KB
session.py      : 118 lines,  4.8KB
conversation.py : 201 lines,  8.3KB
memory.py       : 225 lines,  9.4KB
garden.py       : 230 lines,  9.5KB
analysis.py     : 376 lines, 15.8KB
__init__.py     :  99 lines,  2.8KB
README.md       : 250 lines, 12.0KB
-----------------------------------
Total           : 1744 lines, 72.8KB
```

### 클래스 개수
```
User         : 7 classes
Session      : 4 classes
Conversation : 6 classes
Memory       : 7 classes
Garden       : 6 classes
Analysis     : 10 classes
----------------------------
Total        : 40 classes
```

---

## ✅ 검증 결과

### 테스트 실행
```bash
$ python test_schemas.py
============================================================
🔍 API Schemas Validation Test
============================================================

📝 Testing all imports...
   ✅ All imports successful
📝 Testing User schemas...
   ✅ User schemas OK
📝 Testing Session schemas...
   ✅ Session schemas OK
📝 Testing Conversation schemas...
   ✅ Conversation schemas OK
📝 Testing Memory schemas...
   ✅ Memory schemas OK
📝 Testing Garden schemas...
   ✅ Garden schemas OK
📝 Testing Analysis schemas...
   ✅ Analysis schemas OK

============================================================
✅ All schema tests passed!
============================================================
```

### 검증 항목
- ✅ 모든 스키마 import 성공
- ✅ 타입 힌팅 검증 통과
- ✅ Field validation 규칙 동작 (min_length, ge, le, pattern)
- ✅ json_schema_extra 예시 포함 확인
- ✅ Pydantic ValidationError 정상 발생 (잘못된 입력)

---

## 🎯 주요 특징

### 1. Pydantic v2 완전 활용
```python
from pydantic import BaseModel, Field, ConfigDict

class Example(BaseModel):
    field: str = Field(..., description="설명", min_length=1)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"field": "예시 값"}
        }
    )
```

### 2. OpenAPI 자동 문서화
- FastAPI Swagger UI에서 모든 스키마 자동 표시
- 각 필드의 description이 문서에 표시
- json_schema_extra 예시가 "Example Value"로 표시

### 3. 엄격한 타입 검증
```python
# 범위 검증
mcdi_score: float = Field(..., ge=0, le=100)

# 패턴 검증
risk_level: str = Field(..., pattern="^(GREEN|YELLOW|ORANGE|RED)$")

# 길이 검증
name: str = Field(..., min_length=1, max_length=100)
```

### 4. 풍부한 메타데이터
- description: 모든 필드에 상세 설명
- example: 각 스키마에 실제 사용 예시
- ge/le: 숫자 범위 제한
- pattern: 정규식 검증

---

## 📝 사용 예시

### FastAPI 라우트에서 사용
```python
from fastapi import APIRouter
from api.schemas import MessageRequest, MessageResponse

router = APIRouter(prefix="/api/v1/conversation", tags=["Conversation"])

@router.post("/message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    """메시지 전송 및 AI 응답 생성"""
    # Pydantic이 자동으로 request 검증
    response = await process_message(
        user_id=request.user_id,
        message=request.message,
        message_type=request.message_type
    )
    return response  # MessageResponse로 자동 직렬화
```

### 데이터 검증 예시
```python
from api.schemas import UserCreate
from pydantic import ValidationError

# ✅ 정상 케이스
user = UserCreate(
    kakao_id="1234567890",
    name="홍길동",
    garden_name="수진이네 정원"
)

# ❌ 검증 실패 케이스
try:
    user = UserCreate(
        kakao_id="1234567890",
        name=""  # min_length=1 위반
    )
except ValidationError as e:
    print(e.errors())
    # [{'type': 'string_too_short', 'loc': ('name',), ...}]
```

---

## 🔗 연관 모듈

### 이 스키마를 사용하는 모듈
1. **api/routes/**: FastAPI 라우트에서 요청/응답 검증
2. **core/workflow/**: 워크플로우 처리 결과 직렬화
3. **core/dialogue/**: 대화 생성 결과 응답
4. **core/analysis/**: 분석 결과 응답
5. **core/memory/**: 메모리 검색 결과 응답

### 통합 테스트 필요
```bash
# API 라우트 통합 테스트
pytest tests/test_api/test_routes.py

# 전체 워크플로우 E2E 테스트
pytest tests/test_integration/test_end_to_end.py
```

---

## 📚 참고 문서

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [FastAPI Schema Documentation](https://fastapi.tiangolo.com/tutorial/body/)
- SPEC.md 2.1: MCDI 지표 정의
- SPEC.md 2.2: 게이미피케이션 규칙
- SPEC.md 2.3: 4계층 메모리 시스템

---

## 🎉 완료 상태

| 파일 | 상태 | 클래스 수 | 검증 |
|-----|------|-----------|------|
| user.py | ✅ 완료 | 7 | ✅ Pass |
| session.py | ✅ 완료 | 4 | ✅ Pass |
| conversation.py | ✅ 완료 | 6 | ✅ Pass |
| memory.py | ✅ 완료 | 7 | ✅ Pass |
| garden.py | ✅ 완료 | 6 | ✅ Pass |
| analysis.py | ✅ 완료 | 10 | ✅ Pass |
| __init__.py | ✅ 완료 | - | ✅ Pass |
| README.md | ✅ 완료 | - | - |

**총 40개 클래스, 1744 라인, 모든 테스트 통과** ✅

---

**작성자**: Memory Garden AI Team  
**문의**: CLAUDE.md 참조  
**마지막 업데이트**: 2025-02-10
