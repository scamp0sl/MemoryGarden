"""
FastAPI 애플리케이션 엔트리포인트

Memory Garden API Server
- 치매 조기 감지를 위한 대화 분석 서비스
- 게이미피케이션 기반 참여 유도
- 4계층 메모리 시스템
- MCDI 6개 지표 분석

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2025-02-10
"""

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text

from config.settings import settings
from utils.logger import get_logger

# Import routers
from api.routes import (
    users_router,
    sessions_router,
    conversations_router,
    memories_router,
    garden_router,
    analysis_router,
    kakao_webhook_router,
    kakao_oauth_router,
    auth_router,
)
from api.routes.push import router as push_router

logger = get_logger(__name__)


# ============================================
# Lifespan Events (startup/shutdown)
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리
    
    Startup:
    - DB 연결 풀 생성
    - Redis 연결 테스트
    - Qdrant 연결 테스트
    
    Shutdown:
    - DB 연결 풀 종료
    - Redis 연결 종료
    - 정리 작업
    """
    # ============================================
    # Startup
    # ============================================
    logger.info("=" * 60)
    logger.info("🚀 Memory Garden API Starting...")
    logger.info("=" * 60)
    
    try:
        # PostgreSQL 연결 테스트
        logger.info("📦 Initializing PostgreSQL connection pool...")
        from database.postgres import engine, AsyncSessionLocal

        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL connection pool initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize PostgreSQL: {e}")
        # 계속 진행 (DB 없이도 일부 기능은 작동)
    
    try:
        # Redis 연결 테스트
        logger.info("📦 Initializing Redis connection...")
        from database.redis_client import redis_client
        
        await redis_client.ping()
        logger.info("✅ Redis connection initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Redis: {e}")
        # 계속 진행
    
    try:
        # Qdrant 연결 테스트
        logger.info("📦 Initializing Qdrant connection...")
        try:
            from database.qdrant import qdrant_client
        except ImportError:
            logger.warning("⚠️ Qdrant module not found (database/qdrant.py). Skipping initialization.")
            raise ImportError("Qdrant module not implemented yet")

        collections = await qdrant_client.get_collections()
        logger.info(f"✅ Qdrant connection initialized ({len(collections.collections)} collections)")

    except Exception as e:
        logger.error(f"❌ Failed to initialize Qdrant: {e}")
        # 계속 진행 (Qdrant 없이도 일부 기능 작동)
    
    try:
        # 푸시 알림 스케줄러 시작
        logger.info("📦 Starting push notification scheduler...")
        from services.push_scheduler import get_push_scheduler

        push_scheduler = get_push_scheduler()
        push_scheduler.start()
        logger.info("✅ Push notification scheduler started")

    except Exception as e:
        logger.error(f"❌ Failed to start push scheduler: {e}")
        # 계속 진행 (푸시 알림 없이도 서비스 작동)

    try:
        # 대화 스케줄러 시작
        logger.info("📦 Starting dialogue scheduler...")
        from core.dialogue.scheduler import get_scheduler

        dialogue_scheduler = get_scheduler()
        await dialogue_scheduler.start()
        logger.info("✅ Dialogue scheduler started")

    except Exception as e:
        logger.error(f"❌ Failed to start dialogue scheduler: {e}")
        # 계속 진행 (스케줄러 없이도 수동 대화는 가능)

    logger.info("=" * 60)
    logger.info(f"✅ Memory Garden API Started!")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   Debug Mode: {settings.DEBUG}")
    logger.info(f"   API Docs: http://localhost:8000/docs")
    logger.info("=" * 60)
    
    yield  # 애플리케이션 실행
    
    # ============================================
    # Shutdown
    # ============================================
    logger.info("=" * 60)
    logger.info("🛑 Memory Garden API Shutting down...")
    logger.info("=" * 60)

    try:
        # 푸시 알림 스케줄러 종료
        logger.info("📦 Stopping push notification scheduler...")
        from services.push_scheduler import get_push_scheduler

        push_scheduler = get_push_scheduler()
        push_scheduler.shutdown()
        logger.info("✅ Push notification scheduler stopped")

    except Exception as e:
        logger.error(f"❌ Failed to stop push scheduler: {e}")

    try:
        # 대화 스케줄러 종료
        logger.info("📦 Stopping dialogue scheduler...")
        from core.dialogue.scheduler import get_scheduler

        dialogue_scheduler = get_scheduler()
        await dialogue_scheduler.stop()
        logger.info("✅ Dialogue scheduler stopped")

    except Exception as e:
        logger.error(f"❌ Failed to stop dialogue scheduler: {e}")

    try:
        # PostgreSQL 연결 풀 종료
        logger.info("📦 Closing PostgreSQL connection pool...")
        await engine.dispose()
        logger.info("✅ PostgreSQL connection pool closed")
        
    except Exception as e:
        logger.error(f"❌ Failed to close PostgreSQL: {e}")
    
    try:
        # Redis 연결 종료
        logger.info("📦 Closing Redis connection...")
        await redis_client.close()
        logger.info("✅ Redis connection closed")
        
    except Exception as e:
        logger.error(f"❌ Failed to close Redis: {e}")
    
    logger.info("=" * 60)
    logger.info("✅ Memory Garden API Shutdown complete")
    logger.info("=" * 60)


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="Memory Garden API",
    description="""
## 🌸 Memory Garden - 치매 조기 감지 서비스

대화를 통한 인지 기능 분석 및 게이미피케이션 기반 참여 유도 서비스입니다.

### 주요 기능

#### 1. MCDI 분석 (6개 지표)
- **LR** (Lexical Richness): 어휘 풍부도
- **SD** (Semantic Drift): 의미적 표류
- **NC** (Narrative Coherence): 서사 일관성
- **TO** (Temporal Orientation): 시간적 지남력
- **ER** (Episodic Recall): 일화 기억
- **RT** (Response Time): 반응 시간

#### 2. 게이미피케이션
- 🌸 **1 대화 = 1 꽃**
- 🦋 **3일 연속 = 1 나비**
- 🌳 **7일 연속 = 레벨 업**
- 🏅 **30일 = 계절 뱃지**

#### 3. 4계층 메모리 시스템
- Session Memory (Redis)
- Episodic Memory (Qdrant)
- Biographical Memory (Qdrant + PostgreSQL)
- Analytical Memory (TimescaleDB)

#### 4. 위험도 평가
- **GREEN**: 정상
- **YELLOW**: 경계
- **ORANGE**: 위험
- **RED**: 고위험

### 기술 스택
- FastAPI 0.115+
- PostgreSQL 16 (비동기)
- Redis 7 (세션 캐시)
- Qdrant (벡터 DB)
- Claude Sonnet 4.5 (AI)

### 참고 자료
- [SPEC.md](https://github.com/your-org/memory-garden/blob/main/SPEC.md)
- [CLAUDE.md](https://github.com/your-org/memory-garden/blob/main/docs/CLAUDE.md)
""",
    version="1.0.0",
    contact={
        "name": "Memory Garden Team",
        "email": "contact@memorygarden.ai",
    },
    license_info={
        "name": "Proprietary",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.DEBUG,
    lifespan=lifespan,
)


# ============================================
# Middleware
# ============================================

# CORS 설정
if settings.APP_ENV == "production":
    # Production: 허용된 도메인만
    allowed_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else []
    logger.info(f"CORS allowed origins: {allowed_origins}")
else:
    # Development: 모든 도메인 허용
    allowed_origins = ["*"]
    logger.info("CORS: Allowing all origins (development mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    모든 HTTP 요청 로깅
    """
    # 요청 시작
    import time
    start_time = time.time()
    
    # 요청 ID 생성
    import uuid
    request_id = str(uuid.uuid4())
    
    logger.info(
        f"➡️  Request started: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
        }
    )
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = (time.time() - start_time) * 1000  # ms
    
    # 응답 로깅
    logger.info(
        f"⬅️  Request completed: {request.method} {request.url.path} "
        f"[{response.status_code}] {process_time:.2f}ms",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": process_time,
        }
    )
    
    # X-Request-ID 헤더 추가
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    return response


# ============================================
# Exception Handlers
# ============================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    HTTP 예외 핸들러
    """
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": request.url.path,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic 검증 실패 핸들러
    """
    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Request validation failed",
                "details": exc.errors(),
                "path": request.url.path,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    모든 예외 핸들러 (Fallback)
    """
    logger.error(
        f"Unhandled Exception: {exc}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "path": request.url.path,
                "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            }
        },
    )


# ============================================
# Register Routers
# ============================================

app.include_router(users_router)
app.include_router(sessions_router)
app.include_router(conversations_router)
app.include_router(memories_router)
app.include_router(garden_router)
app.include_router(analysis_router)
app.include_router(kakao_webhook_router)  # 카카오 Webhook
app.include_router(kakao_oauth_router)  # 카카오 OAuth (기존)
app.include_router(auth_router)  # 카카오 OAuth (신규, DB 저장)
app.include_router(push_router)  # 푸시 알림


# ============================================
# Static Files (Web App)
# ============================================

# Service Worker는 루트 경로에서 서빙 (HTTPS 호환성)
from fastapi.responses import FileResponse

@app.get("/firebase-messaging-sw.js")
async def serve_service_worker():
    """
    Firebase Service Worker 파일 제공

    Service Worker는 보안상 루트 경로에서 제공되어야 하며,
    올바른 Content-Type과 Cache-Control 헤더가 필요합니다.
    """
    return FileResponse(
        path="firebase-messaging-sw.js",
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/"
        }
    )

# 정적 파일 서빙 (Landing Page, PWA)
app.mount("/static", StaticFiles(directory="static"), name="static")

logger.info("✅ Static files mounted at /static")
logger.info("✅ Service Worker available at /firebase-messaging-sw.js")


# ============================================
# Core Routes
# ============================================

@app.get(
    "/",
    tags=["Core"],
    summary="Root Endpoint",
    description="웹 앱 또는 API 정보",
    response_class=HTMLResponse,
)
async def root(request: Request):
    """
    루트 엔드포인트

    브라우저 접속 시: Landing Page (HTML)
    API 호출 시: JSON 정보

    Returns:
        웹 앱 또는 서비스 정보
    """
    # Accept 헤더 확인
    accept = request.headers.get("accept", "")

    # 브라우저 요청이면 Landing Page로 리다이렉트
    if "text/html" in accept:
        return RedirectResponse(url="/static/index.html")

    # API 요청이면 JSON 반환
    return JSONResponse({
        "service": "Memory Garden API",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.APP_ENV,
        "web_app": "/static/index.html",
        "docs": "/docs",
        "redoc": "/redoc",
    })


@app.get(
    "/health",
    tags=["Core"],
    summary="Health Check",
    description="서비스 상태 및 의존성 확인",
)
async def health_check() -> Dict[str, Any]:
    """
    헬스 체크 엔드포인트
    
    의존성 상태:
    - PostgreSQL
    - Redis
    - Qdrant
    
    Returns:
        서비스 상태 및 의존성 체크 결과
    """
    health_status = {
        "status": "ok",
        "environment": settings.APP_ENV,
        "version": "1.0.0",
        "dependencies": {},
    }
    
    # PostgreSQL 체크
    try:
        from database.postgres import engine
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["dependencies"]["postgresql"] = "ok"
    except Exception as e:
        health_status["dependencies"]["postgresql"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Redis 체크
    try:
        from database.redis_client import redis_client
        await redis_client.ping()
        health_status["dependencies"]["redis"] = "ok"
    except Exception as e:
        health_status["dependencies"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Qdrant 체크 (푸시 알림에 불필요, 선택적)
    try:
        try:
            from database.qdrant import qdrant_client
        except ImportError:
            health_status["dependencies"]["qdrant"] = "not required (push notifications work without it)"
            # 푸시 알림 테스트에는 영향 없으므로 degraded 상태로 만들지 않음
            raise ImportError("Qdrant module not found")

        collections = await qdrant_client.get_collections()
        health_status["dependencies"]["qdrant"] = f"ok ({len(collections.collections)} collections)"
    except Exception as e:
        health_status["dependencies"]["qdrant"] = f"skipped: {str(e)}"
        # status는 "ok" 유지 (Qdrant는 선택적)
    
    return health_status


@app.get(
    "/config/firebase",
    tags=["Core"],
    summary="Firebase Config",
    description="웹 앱용 Firebase 설정 정보",
)
async def get_firebase_config() -> Dict[str, Any]:
    """
    Firebase Web 설정 정보

    웹 앱에서 FCM 토큰 생성에 필요한 Firebase 설정을 반환합니다.

    Returns:
        Firebase 설정 정보
    """
    # Settings 객체에서 Firebase 설정 읽기
    firebase_config = {
        "apiKey": settings.FIREBASE_API_KEY or "",
        "authDomain": settings.FIREBASE_AUTH_DOMAIN or "",
        "projectId": settings.FIREBASE_PROJECT_ID or "",
        "storageBucket": f"{settings.FIREBASE_PROJECT_ID}.appspot.com" if settings.FIREBASE_PROJECT_ID else "",
        "messagingSenderId": settings.FIREBASE_MESSAGING_SENDER_ID or "",
        "appId": settings.FIREBASE_APP_ID or "",
    }

    vapid_key = settings.FIREBASE_VAPID_KEY or ""

    return {
        "firebaseConfig": firebase_config,
        "vapidKey": vapid_key,
        "configured": bool(firebase_config["apiKey"] and vapid_key)
    }


@app.get(
    "/info",
    tags=["Core"],
    summary="API Information",
    description="API 엔드포인트 및 통계 정보",
)
async def api_info() -> Dict[str, Any]:
    """
    API 정보 엔드포인트
    
    Returns:
        API 통계 및 엔드포인트 정보
    """
    # 라우트 통계
    api_routes = [route for route in app.routes if hasattr(route, 'path') and route.path.startswith('/api/v1')]
    
    route_counts = {}
    for route in api_routes:
        if hasattr(route, 'path'):
            prefix = route.path.split('/')[3] if len(route.path.split('/')) > 3 else 'root'
            route_counts[prefix] = route_counts.get(prefix, 0) + 1
    
    return {
        "service": "Memory Garden API",
        "version": "1.0.0",
        "total_routes": len(app.routes),
        "api_routes": len(api_routes),
        "routes_by_module": route_counts,
        "environment": settings.APP_ENV,
        "debug_mode": settings.DEBUG,
    }
