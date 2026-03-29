# Memory Garden API Server 가이드

FastAPI 기반 REST API 서버 설정 및 실행 가이드.

---

## 📋 목차

1. [서버 구성](#서버-구성)
2. [실행 방법](#실행-방법)
3. [환경 설정](#환경-설정)
4. [API 문서](#api-문서)
5. [모니터링](#모니터링)
6. [트러블슈팅](#트러블슈팅)

---

## 🎯 서버 구성

### 파일 구조
```
.
├── main.py                 # Uvicorn 진입점 (루트)
├── api/
│   ├── main.py            # FastAPI 앱 (startup/shutdown, middleware, exception handlers)
│   ├── routes/            # 6개 라우터 (users, sessions, conversations, memories, garden, analysis)
│   └── schemas/           # Pydantic 모델 (40개 클래스)
├── config/
│   └── settings.py        # 환경 변수 설정
└── .env                   # 환경 변수 파일
```

### 주요 컴포넌트

#### 1. main.py (루트)
```python
# Uvicorn 서버 진입점
python main.py              # 개발 모드 (Hot Reload)
python main.py --production # 프로덕션 모드
python main.py --port 8080  # 포트 지정
```

**기능**:
- 명령줄 인자 파싱
- 개발/프로덕션 모드 전환
- Uvicorn 서버 시작

---

#### 2. api/main.py
```python
# FastAPI 애플리케이션
app = FastAPI(
    title="Memory Garden API",
    version="1.0.0",
    lifespan=lifespan,  # startup/shutdown 이벤트
)
```

**기능**:
- ✅ **Lifespan Events** (startup/shutdown)
  - PostgreSQL 연결 풀 생성/종료
  - Redis 연결 테스트/종료
  - Qdrant 연결 테스트
  
- ✅ **CORS Middleware**
  - 개발: 모든 도메인 허용 (`*`)
  - 프로덕션: 환경 변수 기반 도메인 제한
  
- ✅ **Request Logging Middleware**
  - 모든 요청/응답 로깅
  - 처리 시간 측정
  - X-Request-ID 헤더 추가
  
- ✅ **Exception Handlers**
  - HTTPException
  - ValidationError (Pydantic)
  - General Exception (Fallback)
  
- ✅ **6개 라우터 등록**
  - users, sessions, conversations, memories, garden, analysis
  
- ✅ **Core Routes**
  - `GET /` - 서비스 정보
  - `GET /health` - 헬스 체크 (의존성 포함)
  - `GET /info` - API 통계

---

## 🚀 실행 방법

### 1. 개발 모드 (권장)

**Hot Reload 활성화**:
```bash
# 기본 실행
python main.py

# 또는
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**특징**:
- 코드 변경 시 자동 재시작
- 상세한 로그 출력
- 디버그 모드 활성화

**출력 예시**:
```
============================================================
🔧 Starting Memory Garden API (Development Mode)
============================================================
   Host: 0.0.0.0
   Port: 8000
   Hot Reload: ✅ Enabled
   Log Level: info
============================================================
   API Docs: http://0.0.0.0:8000/docs
   ReDoc: http://0.0.0.0:8000/redoc
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

### 2. 프로덕션 모드

**단일 워커**:
```bash
python main.py --production
```

**다중 워커** (권장):
```bash
python main.py --production --workers 4
```

**워커 수 계산**:
```
워커 수 = (CPU 코어 수 × 2) + 1
예: 4코어 → 9 워커
```

**특징**:
- Hot Reload 비활성화
- 다중 워커 지원
- 최적화된 성능

---

### 3. 포트 지정

```bash
# 포트 8080 사용
python main.py --port 8080

# 프로덕션 + 포트 지정
python main.py --production --port 8080 --workers 4
```

---

### 4. 로그 레벨 지정

```bash
# 디버그 로그
python main.py --log-level debug

# 에러만 표시
python main.py --log-level error
```

**로그 레벨**:
- `critical` - 치명적 오류만
- `error` - 에러 이상
- `warning` - 경고 이상
- `info` - 정보 이상 (기본)
- `debug` - 디버그 정보 포함
- `trace` - 모든 정보

---

### 5. Docker Compose

```bash
# 전체 스택 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f api

# 재시작
docker-compose restart api
```

---

## ⚙️ 환경 설정

### .env 파일 설정

```bash
# 환경 변수 복사
cp .env.example .env

# 필수 변수 설정
nano .env
```

**필수 환경 변수**:
```env
# Application
APP_ENV=development           # development / staging / production
DEBUG=true                    # true / false
LOG_LEVEL=INFO               # DEBUG / INFO / WARNING / ERROR

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/memory_garden
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                # Optional

# AI Services
CLAUDE_API_KEY=sk-ant-...     # Anthropic API Key
OPENAI_API_KEY=sk-...         # OpenAI API Key
CLAUDE_MODEL=claude-4-5-sonnet-20250929
GPT_MODEL=gpt-4o-2024-08-06

# Security
SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS (프로덕션)
CORS_ORIGINS=https://memorygarden.ai,https://app.memorygarden.ai

# Kakao (Optional)
KAKAO_REST_API_KEY=
KAKAO_ADMIN_KEY=
KAKAO_CHANNEL_ID=
```

---

### config/settings.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str
    REDIS_URL: str
    QDRANT_URL: str
    
    # AI Services
    CLAUDE_API_KEY: str
    OPENAI_API_KEY: str
    
    # Security
    SECRET_KEY: str
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

## 📚 API 문서

### Swagger UI (권장)

```
http://localhost:8000/docs
```

**특징**:
- 인터랙티브 API 테스트
- 요청/응답 예시 자동 생성
- Try it out 기능

**사용 방법**:
1. 브라우저에서 `/docs` 접속
2. 원하는 엔드포인트 클릭
3. "Try it out" 버튼 클릭
4. 파라미터 입력 후 "Execute"

---

### ReDoc

```
http://localhost:8000/redoc
```

**특징**:
- 깔끔한 문서 UI
- 3단 레이아웃
- 다운로드 가능

---

### OpenAPI JSON

```
http://localhost:8000/openapi.json
```

**사용처**:
- Postman import
- 코드 생성기 (openapi-generator)
- 자동화 도구

---

## 📊 모니터링

### 1. 헬스 체크

```bash
# 기본 헬스 체크
curl http://localhost:8000/health

# 응답 예시
{
  "status": "ok",
  "environment": "development",
  "version": "1.0.0",
  "dependencies": {
    "postgresql": "ok",
    "redis": "ok",
    "qdrant": "ok (3 collections)"
  }
}
```

**의존성 상태**:
- `ok` - 정상
- `error: ...` - 연결 실패 (상세 오류 포함)

---

### 2. API 정보

```bash
curl http://localhost:8000/info

# 응답 예시
{
  "service": "Memory Garden API",
  "version": "1.0.0",
  "total_routes": 39,
  "api_routes": 32,
  "routes_by_module": {
    "users": 7,
    "sessions": 5,
    "conversations": 4,
    "memories": 5,
    "garden": 4,
    "analysis": 7
  },
  "environment": "development",
  "debug_mode": true
}
```

---

### 3. 로그 모니터링

**개발 모드**:
```bash
# 실시간 로그
tail -f logs/api.log

# 특정 로그 레벨만
tail -f logs/api.log | grep ERROR
```

**Docker**:
```bash
# 실시간 로그
docker-compose logs -f api

# 최근 100줄
docker-compose logs --tail=100 api
```

---

### 4. 요청/응답 헤더

**모든 응답에 포함**:
```http
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Process-Time: 125.42ms
```

**사용 예시**:
```bash
curl -v http://localhost:8000/health

# 응답 헤더 확인
< X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
< X-Process-Time: 2.15ms
```

---

## 🔧 트러블슈팅

### 1. 서버가 시작되지 않음

**증상**:
```
ERROR: Failed to start server: ...
```

**해결**:
```bash
# 1. 포트 충돌 확인
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# 2. 의존성 설치 확인
pip install -r requirements.txt

# 3. 환경 변수 확인
python -c "from config.settings import settings; print(settings.DATABASE_URL)"

# 4. DB 연결 확인
docker-compose ps
docker-compose logs postgres
```

---

### 2. CORS 에러

**증상**:
```
Access to fetch at 'http://localhost:8000/api/v1/users' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**해결**:
```bash
# 개발 모드: 자동으로 "*" 허용
# 프로덕션: .env에 CORS_ORIGINS 추가

# .env
CORS_ORIGINS=http://localhost:3000,https://app.memorygarden.ai
```

---

### 3. Hot Reload가 작동하지 않음

**원인**:
- 프로덕션 모드로 실행됨
- `--production` 플래그 사용

**해결**:
```bash
# --production 플래그 제거
python main.py

# 또는 명시적으로 reload 옵션 사용
uvicorn api.main:app --reload
```

---

### 4. DB 연결 실패

**증상**:
```
❌ Failed to initialize PostgreSQL: ...
```

**해결**:
```bash
# 1. Docker 컨테이너 상태 확인
docker-compose ps

# 2. PostgreSQL 로그 확인
docker-compose logs postgres

# 3. DB 직접 접속 테스트
docker-compose exec postgres psql -U memgarden -d memory_garden

# 4. 연결 문자열 확인
echo $DATABASE_URL
```

---

### 5. Redis 연결 실패

**해결**:
```bash
# 1. Redis 컨테이너 확인
docker-compose ps redis

# 2. Redis 접속 테스트
docker-compose exec redis redis-cli ping
# 응답: PONG

# 3. Redis URL 확인
echo $REDIS_URL
```

---

### 6. 메모리 사용량 증가

**원인**:
- 워커 수가 너무 많음
- 메모리 누수

**해결**:
```bash
# 1. 워커 수 줄이기
python main.py --production --workers 2

# 2. 메모리 사용량 모니터링
docker stats api

# 3. 서버 재시작 (메모리 해제)
docker-compose restart api
```

---

## 📈 성능 최적화

### 1. 워커 수 조정

```bash
# CPU 코어 수 확인
nproc  # Linux
sysctl -n hw.ncpu  # macOS

# 권장 워커 수 = (코어 수 × 2) + 1
python main.py --production --workers 9  # 4코어 기준
```

---

### 2. DB 연결 풀 설정

```python
# database/postgres.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # 기본 연결 수
    max_overflow=10,     # 추가 연결 수
    pool_timeout=30,     # 대기 시간
    pool_recycle=3600,   # 연결 재사용 시간
)
```

---

### 3. Redis 캐싱

```python
# 자주 조회되는 데이터 캐싱
from database.redis_client import redis_client

# 캐시 저장
await redis_client.setex(
    f"user:{user_id}",
    3600,  # 1시간
    user_data
)

# 캐시 조회
cached = await redis_client.get(f"user:{user_id}")
```

---

## 🔒 보안 설정

### 1. SECRET_KEY 생성

```bash
# Python으로 생성
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 또는 OpenSSL
openssl rand -base64 32
```

---

### 2. HTTPS 설정 (프로덕션)

```bash
# Nginx + Let's Encrypt 사용 권장
# nginx.conf
server {
    listen 443 ssl;
    server_name api.memorygarden.ai;
    
    ssl_certificate /etc/letsencrypt/live/api.memorygarden.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.memorygarden.ai/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 3. Rate Limiting

```python
# TODO: slowapi 통합
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/users")
@limiter.limit("100/minute")
async def list_users(request: Request):
    ...
```

---

## 📚 참고 자료

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- api/routes/README.md - 라우터 상세 문서
- api/schemas/README.md - 스키마 문서

---

**작성자**: Memory Garden Team  
**마지막 업데이트**: 2025-02-10
