# 카카오 OAuth 구현 계획

> 작성일: 2026-02-12
> 예상 소요 시간: 2-3시간
> 기반: 카카오 디벨로퍼 최신 문서 (2024-2026)

---

## 📋 구현 단계

### Step 1: OAuth 로그인 API (40분)

#### 1.1 라우트 생성: `api/routes/auth.py`

```python
"""
카카오 OAuth 인증 라우트

카카오 로그인 → 권한 동의 → 토큰 저장
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import httpx

from config.settings import settings
from database.postgres import get_db
from database.models import User
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

# ============================================
# 1단계: 카카오 로그인 시작
# ============================================
@router.get("/kakao/login")
async def kakao_login():
    """
    카카오 로그인 페이지로 리다이렉트

    사용자가 이 URL을 방문하면:
    1. 카카오 로그인 페이지로 이동
    2. 사용자가 로그인 + 권한 동의
    3. /auth/kakao/callback으로 리다이렉트됨
    """
    kakao_auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={settings.KAKAO_REST_API_KEY}"
        f"&redirect_uri={settings.KAKAO_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=talk_message,friends"  # 카카오톡 메시지 + 친구목록
    )

    logger.info(f"Redirecting to Kakao OAuth: {kakao_auth_url}")
    return RedirectResponse(url=kakao_auth_url)


# ============================================
# 2단계: 카카오 콜백 처리
# ============================================
@router.get("/kakao/callback")
async def kakao_callback(
    code: str = Query(..., description="인가 코드"),
    db: Session = Depends(get_db)
):
    """
    카카오 OAuth 콜백 처리

    1. 인가 코드 → 액세스 토큰 교환
    2. 사용자 정보 조회
    3. DB에 저장
    4. 성공 페이지로 리다이렉트

    Args:
        code: 카카오가 전달한 인가 코드

    Returns:
        성공 메시지 또는 에러
    """
    logger.info(f"Kakao callback received, code: {code[:10]}...")

    try:
        # 2-1. 토큰 발급
        token_response = await _get_kakao_token(code)
        access_token = token_response["access_token"]
        refresh_token = token_response["refresh_token"]
        expires_in = token_response["expires_in"]  # 43199초 (12시간)
        refresh_token_expires_in = token_response["refresh_token_expires_in"]  # 60일

        # 2-2. 사용자 정보 조회
        user_info = await _get_kakao_user_info(access_token)
        kakao_id = str(user_info["id"])
        nickname = user_info.get("kakao_account", {}).get("profile", {}).get("nickname", "사용자")

        logger.info(f"Kakao user authenticated: {kakao_id} ({nickname})")

        # 2-3. DB에 저장 (없으면 생성, 있으면 업데이트)
        user = db.query(User).filter(User.user_id == kakao_id).first()

        if not user:
            # 신규 사용자 생성
            user = User(
                user_id=kakao_id,
                name=nickname,
                created_at=datetime.now()
            )
            db.add(user)
            logger.info(f"New user created: {kakao_id}")

        # 토큰 업데이트
        user.kakao_access_token = access_token
        user.kakao_refresh_token = refresh_token
        user.kakao_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        user.kakao_refresh_token_expires_at = datetime.now() + timedelta(seconds=refresh_token_expires_in)
        user.updated_at = datetime.now()

        db.commit()
        db.refresh(user)

        logger.info(f"User tokens saved: {kakao_id}")

        # 2-4. 성공 페이지로 리다이렉트
        return {
            "status": "success",
            "message": "카카오 로그인 완료!",
            "user_id": kakao_id,
            "nickname": nickname,
            "expires_at": user.kakao_token_expires_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Kakao OAuth callback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth 처리 실패: {e}")


# ============================================
# 3단계: 토큰 갱신 (자동 실행용)
# ============================================
@router.post("/kakao/refresh/{user_id}")
async def refresh_kakao_token(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    액세스 토큰 갱신

    만료 1시간 전에 자동으로 호출되어야 함 (스케줄러)

    Args:
        user_id: 사용자 ID

    Returns:
        새로운 토큰 정보
    """
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user or not user.kakao_refresh_token:
        raise HTTPException(status_code=404, detail="User or refresh token not found")

    try:
        # 토큰 갱신 요청
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.KAKAO_REST_API_KEY,
                    "client_secret": settings.KAKAO_CLIENT_SECRET,
                    "refresh_token": user.kakao_refresh_token
                }
            )
            response.raise_for_status()
            token_data = response.json()

        # DB 업데이트
        user.kakao_access_token = token_data["access_token"]

        # refresh_token이 갱신되었으면 업데이트 (1개월 미만 남았을 때만)
        if "refresh_token" in token_data:
            user.kakao_refresh_token = token_data["refresh_token"]
            user.kakao_refresh_token_expires_at = datetime.now() + timedelta(
                seconds=token_data.get("refresh_token_expires_in", 5184000)
            )

        user.kakao_token_expires_at = datetime.now() + timedelta(
            seconds=token_data.get("expires_in", 43199)
        )
        user.updated_at = datetime.now()

        db.commit()

        logger.info(f"Token refreshed for user: {user_id}")

        return {
            "status": "success",
            "message": "토큰 갱신 완료",
            "expires_at": user.kakao_token_expires_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Token refresh failed for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"토큰 갱신 실패: {e}")


# ============================================
# Helper Functions
# ============================================
async def _get_kakao_token(code: str) -> dict:
    """
    인가 코드를 액세스 토큰으로 교환

    Args:
        code: 카카오에서 받은 인가 코드

    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "expires_in": 43199,
            "refresh_token_expires_in": 5184000
        }
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_REST_API_KEY,
                "client_secret": settings.KAKAO_CLIENT_SECRET,  # 2024년부터 필수!
                "redirect_uri": settings.KAKAO_REDIRECT_URI,
                "code": code
            }
        )
        response.raise_for_status()
        return response.json()


async def _get_kakao_user_info(access_token: str) -> dict:
    """
    액세스 토큰으로 사용자 정보 조회

    Args:
        access_token: 카카오 액세스 토큰

    Returns:
        {
            "id": 123456789,
            "kakao_account": {
                "profile": {
                    "nickname": "닉네임",
                    "profile_image_url": "..."
                }
            }
        }
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        response.raise_for_status()
        return response.json()
```

#### 1.2 환경 변수 추가: `config/settings.py`

```python
# config/settings.py에 추가

class Settings(BaseSettings):
    # ... 기존 설정 ...

    # ============================================
    # 카카오 OAuth 설정
    # ============================================
    KAKAO_REST_API_KEY: str = ""  # 카카오 디벨로퍼에서 발급
    KAKAO_CLIENT_SECRET: str = ""  # 2024년부터 필수!
    KAKAO_REDIRECT_URI: str = "http://localhost:8001/api/v1/auth/kakao/callback"

    # 프로덕션에서는:
    # KAKAO_REDIRECT_URI: str = "https://n8n.softline.co.kr/api/v1/auth/kakao/callback"
```

#### 1.3 `.env` 파일 업데이트

```bash
# .env에 추가
KAKAO_REST_API_KEY=your_rest_api_key_here
KAKAO_CLIENT_SECRET=your_client_secret_here
KAKAO_REDIRECT_URI=http://localhost:8001/api/v1/auth/kakao/callback
```

---

### Step 2: DB 모델 수정 (20분)

#### 2.1 User 모델에 토큰 필드 추가

```python
# database/models.py 수정

class User(Base):
    __tablename__ = "users"

    # ... 기존 필드 ...

    # ============================================
    # 카카오 OAuth 토큰 (추가)
    # ============================================
    kakao_access_token = Column(String, nullable=True)
    kakao_refresh_token = Column(String, nullable=True)
    kakao_token_expires_at = Column(DateTime, nullable=True)
    kakao_refresh_token_expires_at = Column(DateTime, nullable=True)
```

#### 2.2 Alembic 마이그레이션

```bash
# 1. 마이그레이션 파일 생성
alembic revision --autogenerate -m "Add kakao oauth tokens to users table"

# 2. 마이그레이션 실행
alembic upgrade head
```

---

### Step 3: 메시지 전송 수정 (30분)

#### 3.1 `tasks/dialogue.py` 수정

```python
# tasks/dialogue.py의 send_scheduled_dialogue() 함수 수정

async def send_scheduled_dialogue(user_id: str) -> Dict[str, Any]:
    """스케줄된 자동 대화 시작 (OAuth 버전)"""

    # 1. 사용자 조회 (토큰 포함)
    from database.postgres import AsyncSessionLocal
    from database.models import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"User not found: {user_id}")
            return {"success": False, "error": "User not found"}

        # 2. 토큰 만료 확인 (1시간 전에 갱신)
        if user.kakao_token_expires_at:
            time_until_expiry = user.kakao_token_expires_at - datetime.now()
            if time_until_expiry < timedelta(hours=1):
                logger.info(f"Token expiring soon for {user_id}, refreshing...")
                # 토큰 갱신 API 호출
                async with httpx.AsyncClient() as client:
                    await client.post(f"http://localhost:8001/api/v1/auth/kakao/refresh/{user_id}")

                # 갱신된 사용자 정보 다시 조회
                result = await db.execute(select(User).where(User.user_id == user_id))
                user = result.scalar_one_or_none()

        # 3. 액세스 토큰 확인
        if not user.kakao_access_token:
            logger.error(f"No access token for user {user_id}")
            return {
                "success": False,
                "error": "No Kakao access token. User needs to login via /auth/kakao/login"
            }

        # 4. 최근 대화 컨텍스트 조회
        from core.memory.memory_manager import MemoryManager
        memory_manager = MemoryManager()
        recent_memory = await memory_manager.retrieve_all(user_id=user_id, limit=5)

        # 5. 맞춤형 질문 생성
        from core.dialogue.dialogue_manager import DialogueManager
        dialogue_manager = DialogueManager()

        question_data = await dialogue_manager.plan_next(
            user_id=user_id,
            memory=recent_memory,
            risk_level=recent_memory.get("risk_level", "GREEN")
        )

        # 6. 인사말 + 질문 조합
        greeting = _get_time_based_greeting()
        message = f"{greeting}\n\n{question_data.get('question', '오늘은 어떤 하루를 보내셨나요?')} 😊"

        # 7. 카카오톡 메시지 전송 (OAuth 버전)
        from services.kakao_client import KakaoClient
        kakao_client = KakaoClient()

        try:
            # 나에게 보내기 (테스트용) - user_key 없이 access_token만 사용
            kakao_result = await kakao_client.send_to_me(
                access_token=user.kakao_access_token,
                message=message
            )

            logger.info(f"Kakao message sent to {user_id}: {kakao_result}")

            return {
                "success": True,
                "user_id": user_id,
                "message_sent": message,
                "scheduled_at": datetime.now().isoformat(),
                "kakao_result": kakao_result
            }

        except Exception as e:
            logger.error(f"Failed to send Kakao message to {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
```

#### 3.2 `services/kakao_client.py` 메서드 추가

```python
# services/kakao_client.py에 추가

async def send_to_me(
    self,
    access_token: str,
    message: str
) -> Dict[str, Any]:
    """
    나에게 보내기 (OAuth 버전)

    Args:
        access_token: 사용자의 카카오 액세스 토큰
        message: 전송할 메시지

    Returns:
        전송 결과
    """
    if self.mock_mode:
        logger.info(f"✅ [MOCK] Sending to self: {message[:50]}...")
        return {"success": True, "mock": True}

    # 템플릿 객체 생성
    import json
    template_object = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": "https://n8n.softline.co.kr/static/index.html",
            "mobile_web_url": "https://n8n.softline.co.kr/static/index.html"
        },
        "button_title": "대화하기"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://kapi.kakao.com/v2/api/talk/memo/default/send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
                },
                data={
                    "template_object": json.dumps(template_object, ensure_ascii=False)
                }
            )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        logger.error(f"Send to me failed: {e}", exc_info=True)
        raise


async def send_to_friends(
    self,
    access_token: str,
    receiver_uuids: List[str],
    message: str
) -> Dict[str, Any]:
    """
    친구에게 보내기 (OAuth 버전)

    Args:
        access_token: 사용자의 카카오 액세스 토큰
        receiver_uuids: 친구 UUID 리스트 (최대 5명)
        message: 전송할 메시지

    Returns:
        전송 결과
    """
    if self.mock_mode:
        logger.info(f"✅ [MOCK] Sending to {len(receiver_uuids)} friends: {message[:50]}...")
        return {"success": True, "mock": True}

    # 템플릿 객체 생성
    import json
    template_object = {
        "object_type": "text",
        "text": message,
        "link": {
            "web_url": "https://n8n.softline.co.kr/static/index.html",
            "mobile_web_url": "https://n8n.softline.co.kr/static/index.html"
        },
        "button_title": "대화하기"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://kapi.kakao.com/v1/api/talk/friends/message/default/send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
                },
                data={
                    "receiver_uuids": json.dumps(receiver_uuids),
                    "template_object": json.dumps(template_object, ensure_ascii=False)
                }
            )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        logger.error(f"Send to friends failed: {e}", exc_info=True)
        raise
```

---

### Step 4: 테스트 및 등록 (30-40분)

#### 4.1 카카오 디벨로퍼 앱 설정

1. https://developers.kakao.com/ 접속
2. 내 애플리케이션 > Memory Garden 선택
3. **Redirect URI 등록**:
   - 플랫폼 설정 > Web > Redirect URI 추가
   - `http://localhost:8001/api/v1/auth/kakao/callback`
4. **동의항목 설정**:
   - 제품 설정 > 카카오 로그인 > 동의항목
   - "카카오톡 메시지 전송" 필수 동의
   - "카카오 서비스 내 친구목록" 선택 동의
5. **Client Secret 활성화**:
   - 제품 설정 > 카카오 로그인 > 보안
   - Client Secret 코드 생성 및 복사

#### 4.2 실제 사용자 로그인 테스트

```bash
# 1. FastAPI 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8001

# 2. 브라우저에서 카카오 로그인 페이지 열기
open http://localhost:8001/api/v1/auth/kakao/login

# 3. 카카오 로그인 + 권한 동의
# → 자동으로 /auth/kakao/callback으로 리다이렉트됨

# 4. DB 확인
psql -U memgarden -d memory_garden -c "SELECT user_id, name, kakao_access_token IS NOT NULL as has_token FROM users;"

# 예상 출력:
#   user_id   |  name  | has_token
# ------------+--------+-----------
#  1234567890 | 홍길동 | t
```

#### 4.3 메시지 전송 테스트

```bash
# 1. 즉시 메시지 전송 테스트
curl -X POST http://localhost:8001/api/v1/sessions/test-scheduled-dialogue \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1234567890"}'

# 2. 카카오톡 앱 확인
# → "나에게 보내기" 메시지 수신 확인

# 3. 스케줄 등록 (10:00, 15:00, 20:00)
curl -X POST http://localhost:8001/api/v1/sessions/users/1234567890/schedule \
  -H "Content-Type: application/json" \
  -d '{"schedule_times": ["10:00", "15:00", "20:00"]}'
```

---

## 🎯 완료 기준

✅ 사용자가 카카오 로그인 완료
✅ DB에 access_token, refresh_token 저장됨
✅ 나에게 보내기 메시지 수신 확인
✅ 자동 스케줄 등록 완료
✅ 다음날 10:00에 첫 메시지 수신 예정

---

## 🔧 트러블슈팅

### 문제 1: "Redirect URI mismatch"
**원인**: 카카오 디벨로퍼에 등록한 URI와 요청 URI 불일치
**해결**:
1. 카카오 디벨로퍼 > 플랫폼 설정 > Web > Redirect URI 확인
2. 정확히 `http://localhost:8001/api/v1/auth/kakao/callback` 등록

### 문제 2: "Client authentication failed"
**원인**: CLIENT_SECRET 누락 또는 잘못됨
**해결**:
1. 카카오 디벨로퍼 > 제품 설정 > 카카오 로그인 > 보안
2. Client Secret 코드 재생성
3. `.env`에 정확히 복사

### 문제 3: "Insufficient scope"
**원인**: 동의항목 설정 안 됨
**해결**:
1. 카카오 디벨로퍼 > 동의항목
2. "카카오톡 메시지 전송" 필수 동의로 설정
3. 사용자 재로그인 필요

### 문제 4: "Token expired"
**원인**: access_token 만료 (12시간 후)
**해결**: 자동 갱신 로직이 작동하지 않음
```python
# 수동 갱신 테스트
curl -X POST http://localhost:8001/api/v1/auth/kakao/refresh/1234567890
```

---

## 📊 구현 후 비교

| 항목 | Before (Mock) | After (OAuth) |
|------|---------------|---------------|
| 메시지 전송 | ❌ 로그만 출력 | ✅ 실제 카카오톡 수신 |
| 사용자 경험 | - | 🌟 카카오톡 대화창에서 바로 확인 |
| 설정 시간 | 0분 (즉시) | 1회 로그인 (2분) |
| 유지 보수 | - | 토큰 자동 갱신 (12시간마다) |

---

## 🚀 다음 단계 (추가 개선)

구현 완료 후 선택적으로 추가 가능:

1. **친구에게 보내기**: 보호자에게도 리포트 전송
2. **친구 목록 조회**: UUID 자동 수집
3. **토큰 갱신 스케줄러**: APScheduler로 자동 갱신 (11시간마다)
4. **웹 대시보드**: 로그인 상태 확인 UI

---

## 📝 참고 문서

- 카카오 로그인 REST API: https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api
- 카카오톡 메시지 REST API: https://developers.kakao.com/docs/latest/ko/kakaotalk-message/rest-api
- 에러 코드: https://developers.kakao.com/docs/latest/ko/rest-api/error-code
- 쿼터 정보: https://developers.kakao.com/docs/latest/ko/getting-started/quota
