# API Routes

FastAPI 기반 REST API 라우터 구현.

## 📋 완성된 라우터 (6개)

### 1. users.py - 사용자 관리
```python
POST   /api/v1/users                      # 사용자 생성
GET    /api/v1/users                      # 사용자 목록 (페이지네이션)
GET    /api/v1/users/{user_id}            # 사용자 조회
PUT    /api/v1/users/{user_id}            # 사용자 정보 수정
GET    /api/v1/users/{user_id}/profile    # 상세 프로필 (정원 상태 포함)
POST   /api/v1/users/{user_id}/guardians  # 보호자 등록
GET    /api/v1/users/{user_id}/guardians  # 보호자 목록
```

**주요 기능**:
- 카카오톡 ID 기반 사용자 등록
- MCDI 점수 및 위험도 조회
- 정원 이름 설정
- 보호자 관리 (가족 구성원)

---

### 2. sessions.py - 세션 관리
```python
POST   /api/v1/sessions                       # 세션 생성
GET    /api/v1/sessions/{session_id}          # 세션 조회
GET    /api/v1/sessions/{session_id}/status   # 세션 상태 (간소화)
PUT    /api/v1/sessions/{session_id}/end      # 세션 종료
GET    /api/v1/sessions/users/{user_id}/sessions  # 사용자 세션 목록
```

**주요 기능**:
- Redis 기반 세션 상태 관리
- 대화 횟수 추적
- 자동 종료 (타임아웃)
- 세션 히스토리

---

### 3. conversations.py - 대화 처리 ⭐ 핵심
```python
POST   /api/v1/conversations/sessions/{session_id}/messages  # 메시지 전송 (핵심)
POST   /api/v1/conversations/messages/image                  # 이미지 메시지
GET    /api/v1/conversations/sessions/{session_id}/history   # 세션 히스토리
GET    /api/v1/conversations/users/{user_id}/conversations   # 전체 대화 목록
```

**핵심 워크플로우** (`POST /sessions/{session_id}/messages`):
```
1. SessionInit        # 세션 검증 및 컨텍스트 로드
2. Conversation       # DialogueManager - AI 응답 생성
3. MemoryExtraction   # MemoryExtractor - 사실 추출
4. Analysis           # Analyzer - MCDI 분석 + 감정 분석
5. GardenUpdate       # GardenMapper - 정원 상태 업데이트
6. MemoryStorage      # MemoryManager - 4계층 메모리 저장
7. ReportCheck        # ReportGenerator - 주간 리포트 (일요일)
8. SessionClose       # 세션 정리
```

**응답 구조** (`MessageResponse`):
```json
{
  "success": true,
  "response": "AI 응답 메시지",
  "session_id": "...",
  "mcdi_score": 81.58,
  "risk_level": "GREEN",
  "detected_emotion": "joy",
  "garden_status": {
    "flower_count": 42,
    "butterfly_count": 5,
    "garden_level": 3,
    "weather": "sunny",
    "status_message": "정원이 건강하게 자라고 있어요! ☀️"
  },
  "achievements": ["flowers_42"],
  "level_up": false,
  "execution_time_ms": 1250.5
}
```

---

### 4. memories.py - 기억 조회
```python
GET    /api/v1/memories/users/{user_id}/memories           # 통합 검색
GET    /api/v1/memories/users/{user_id}/memories/by-emotion  # 감정별 검색
GET    /api/v1/memories/users/{user_id}/memories/stats    # 기억 통계
GET    /api/v1/memories/episodic/{memory_id}               # 일화 기억 조회
GET    /api/v1/memories/biographical/{fact_id}             # 전기적 사실 조회
```

**4계층 메모리 시스템**:
1. **Session Memory** (Redis) - 현재 세션 컨텍스트
2. **Episodic Memory** (Qdrant) - 일화 기억 (시간, 장소, 사건)
3. **Biographical Memory** (Qdrant + PostgreSQL) - 전기적 사실 (이름, 관계, 선호도)
4. **Analytical Memory** (TimescaleDB) - 분석 기록 (MCDI 점수 시계열)

---

### 5. garden.py - 정원 상태
```python
GET    /api/v1/garden/users/{user_id}/garden          # 정원 상태 조회
GET    /api/v1/garden/users/{user_id}/garden/history  # 정원 히스토리
GET    /api/v1/garden/users/{user_id}/achievements    # 업적 목록
POST   /api/v1/garden/admin/users/{user_id}/garden/reset  # [관리자] 초기화
```

**게임 메카닉** (SPEC.md 2.2.1):
- 🌸 **flower_count**: 1 대화 = 1 꽃
- 🦋 **butterfly_count**: 3일 연속 = 1 나비
- 🌳 **garden_level**: 7일 연속마다 +1 레벨 (최대 10)
- 🏅 **season_badge**: 30일 = 계절 뱃지

**날씨 매핑** (위험도 → 날씨):
- GREEN → ☀️ sunny
- YELLOW → ☁️ cloudy
- ORANGE → 🌧️ rainy
- RED → ⛈️ stormy

**업적 종류**:
- first_flower, butterfly_visit, garden_expansion
- flowers_10, flowers_42, flowers_100
- streak_7days, streak_14days, streak_30days
- season_badge_spring/summer/autumn/winter

---

### 6. analysis.py - 분석 결과
```python
GET    /api/v1/analysis/users/{user_id}/analysis/weekly   # 주간 리포트
GET    /api/v1/analysis/users/{user_id}/analysis/monthly  # 월간 리포트
GET    /api/v1/analysis/users/{user_id}/analysis/history  # 분석 히스토리
GET    /api/v1/analysis/users/{user_id}/analysis/latest   # 최신 분석
GET    /api/v1/analysis/users/{user_id}/mcdi               # MCDI 점수
GET    /api/v1/analysis/users/{user_id}/risk               # 위험도 평가
GET    /api/v1/analysis/users/{user_id}/metrics/{metric_name}/comparison  # 지표 비교
```

**MCDI 6개 지표**:
1. **LR** (Lexical Richness) - 어휘 풍부도
2. **SD** (Semantic Drift) - 의미적 표류
3. **NC** (Narrative Coherence) - 서사 일관성
4. **TO** (Temporal Orientation) - 시간적 지남력
5. **ER** (Episodic Recall) - 일화 기억
6. **RT** (Response Time) - 반응 시간

**위험도 4단계**:
- **GREEN**: 정상 (z-score > -1.5)
- **YELLOW**: 경계 (-2.0 < z ≤ -1.5)
- **ORANGE**: 위험 (-2.5 < z ≤ -2.0 또는 하락 추세)
- **RED**: 고위험 (z ≤ -2.5 또는 급격한 하락)

---

## 📊 통계

### 전체 엔드포인트
```
Total: 32 API endpoints + 6 core routes = 38 routes

By module:
- users:          7 endpoints
- sessions:       5 endpoints
- conversations:  4 endpoints (핵심 대화 포함)
- memories:       5 endpoints
- garden:         4 endpoints
- analysis:       7 endpoints
```

### 파일 크기
```
users.py         : 205 lines,  8.5KB
sessions.py      : 165 lines,  6.8KB
conversations.py : 195 lines,  8.0KB (핵심)
memories.py      : 235 lines,  9.7KB
garden.py        : 180 lines,  7.4KB
analysis.py      : 295 lines, 12.2KB
__init__.py      :  15 lines,  0.5KB
README.md        : 350 lines, 14.5KB
-----------------------------------------
Total            : 1640 lines, 67.6KB
```

---

## 🔗 의존성 주입 (Dependency Injection)

### 1. DB 세션 주입
```python
from sqlalchemy.ext.asyncio import AsyncSession
from database.postgres import get_db

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)  # ← DB 세션 자동 주입
):
    # db 사용 가능
    pass
```

### 2. 서비스 클래스 주입 (TODO)
```python
# 예시: UserService 주입
from services.user_service import UserService

async def get_user_service(
    db: AsyncSession = Depends(get_db)
) -> UserService:
    return UserService(db)

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_user(user_id)
```

---

## 🚀 서버 실행

### 개발 서버
```bash
# Hot reload 활성화
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 로그 레벨 지정
uvicorn api.main:app --reload --log-level debug
```

### API 문서 접속
```bash
# Swagger UI (권장)
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc

# OpenAPI JSON
http://localhost:8000/openapi.json
```

---

## ✅ 검증

### 라우터 테스트
```bash
$ python test_routes.py
============================================================
✅ All route tests passed!
============================================================

📊 Routes by module:
   - users: 7 endpoints
   - sessions: 5 endpoints
   - conversations: 4 endpoints
   - memories: 5 endpoints
   - garden: 4 endpoints
   - analysis: 7 endpoints

✅ Total API endpoints: 32
```

### 수동 테스트 (cURL)
```bash
# 헬스 체크
curl http://localhost:8000/health

# 사용자 생성
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "kakao_id": "1234567890",
    "name": "홍길동",
    "garden_name": "수진이네 정원"
  }'

# 세션 생성
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000"
  }'

# 메시지 전송 (핵심)
curl -X POST http://localhost:8000/api/v1/conversations/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "오늘 점심에 된장찌개 먹었어요",
    "message_type": "text"
  }'
```

---

## 🔧 다음 단계 (구현 필요)

### 1. Service 클래스 구현
```bash
services/
├── user_service.py         # UserService
├── session_service.py      # SessionService
├── conversation_service.py # ConversationService (SessionWorkflow 통합)
├── memory_service.py       # MemoryService
├── garden_service.py       # GardenService
├── analysis_service.py     # AnalysisService
└── __init__.py
```

### 2. Service 주입 설정
```python
# api/dependencies.py 생성
from services.user_service import UserService
from database.postgres import get_db

async def get_user_service(db = Depends(get_db)) -> UserService:
    return UserService(db)
```

### 3. 라우터에서 Service 사용
```python
# api/routes/users.py
from api.dependencies import get_user_service

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### 4. 핵심 워크플로우 통합
```python
# services/conversation_service.py
from core.workflow.session_workflow import SessionWorkflow

class ConversationService:
    def __init__(self, db):
        self.workflow = SessionWorkflow()
    
    async def process_message(self, session_id, message_request):
        result = await self.workflow.process_message(
            user_id=message_request.user_id,
            message=message_request.message,
            message_type=message_request.message_type
        )
        return result
```

---

## 📚 참고 자료

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- SPEC.md 2.1: MCDI 지표 정의
- SPEC.md 2.2: 게이미피케이션 규칙
- CLAUDE.md 3장: 파일별 개발 가이드

---

**작성자**: Memory Garden Team  
**마지막 업데이트**: 2025-02-10  
**상태**: ✅ 라우터 완성, Service 클래스 구현 필요
