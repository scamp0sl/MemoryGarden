# user_key 확인 가이드

## 🔑 API 키 vs user_key 완벽 정리

### 핵심 차이

| 구분 | API 키 (KAKAO_API_KEY) | user_key |
|------|----------------------|----------|
| **정의** | 개발자 앱의 인증 키 | 각 사용자의 고유 ID |
| **개수** | 1개 (앱 당) | N개 (사용자 수만큼) |
| **역할** | "내가 정식 개발자입니다" | "이 사람에게 보내세요" |
| **위치** | .env 파일 | Webhook으로 수집 |
| **형식** | 길고 복잡 (30-40자) | 상대적으로 짧음 (10-20자) |
| **예시** | `abc123def456...` | `user_abc123` |
| **비유** | 건물 출입증 | 아파트 호수 |

---

## 📍 user_key 확인 방법 (3가지)

### ✅ **방법 1: Webhook으로 자동 수집 (권장)**

사용자가 카카오 채널에 메시지를 보내면 **자동으로** user_key를 받을 수 있습니다.

#### 순서도
```
사용자가 채널에 메시지 전송
      ↓
카카오 서버가 Webhook 호출
      ↓
FastAPI가 user_key 자동 수집
      ↓
DB에 저장 & 로그에 출력
```

#### 실행 방법

**1단계: FastAPI 서버 시작**
```bash
cd /home/admin/docker/MemoryGardenAI
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**2단계: ngrok으로 외부 노출**
```bash
# 새 터미널에서
ngrok http 8000

# 출력 예시:
# Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

**3단계: 카카오 채널 관리자에서 Webhook URL 설정**
```
1. https://business.kakao.com 접속
2. 채널 선택 (Memory Garden)
3. 관리 > 상세 설정 > Webhook URL 설정
4. URL 입력: https://abc123.ngrok.io/api/v1/kakao/webhook
5. 저장
```

**4단계: 카카오 채널에 메시지 전송**
```
1. 카카오톡에서 Memory Garden 채널 찾기
2. 메시지 전송: "안녕하세요"
3. FastAPI 로그 확인 → user_key 출력됨!
```

**5단계: 로그에서 user_key 확인**
```bash
# FastAPI 서버 로그에 출력:
============================================================
📨 카카오 메시지 수신!
============================================================
👤 user_key: user_abc123def456
💬 메시지: 안녕하세요
⏰ 시간: 2026-02-20 14:30:00
============================================================
```

---

### 🧪 **방법 2: Webhook 시뮬레이션 (로컬 테스트)**

실제 카카오 메시지 없이 로컬에서 테스트:

```bash
# 1. FastAPI 서버 실행
uvicorn api.main:app --reload

# 2. 새 터미널에서 시뮬레이션 API 호출
curl -X POST "http://localhost:8000/api/v1/kakao/webhook/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_key": "test_user_12345",
    "message": "안녕하세요"
  }'

# 3. FastAPI 로그 확인:
============================================================
🧪 Webhook 시뮬레이션
============================================================
👤 user_key: test_user_12345
💬 메시지: 안녕하세요
============================================================
```

---

### 🔍 **방법 3: 카카오 채널 관리자에서 수동 확인**

웹 브라우저에서 직접 확인:

```
1. https://business.kakao.com 접속
2. 채널 선택 (Memory Garden)
3. 채팅 탭 클릭
4. 사용자 목록에서 특정 사용자 클릭
5. 우측 프로필 창에서 "사용자 KEY" 복사
```

**장점:** 즉시 확인 가능
**단점:** 수동 작업, 자동화 불가

---

## 💻 코드 예시

### user_key 사용 예시

```python
from services.kakao_client import KakaoClient

# 1. KakaoClient 초기화
client = KakaoClient(mock_mode=False)

# 2. 특정 사용자에게 친구톡 전송
result = await client.send_friend_talk(
    user_key="user_abc123def456",  # Webhook으로 수집한 user_key
    message="안녕하세요! 오늘의 정원 가꾸기 시간입니다 🌱"
)

print(result)
# {
#     "success": True,
#     "message_id": "ft_xyz789",
#     "user_key": "user_abc123def456"
# }
```

### DB에 user_key 저장

```python
# database/models.py

class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid4)
    kakao_user_key = Column(String, unique=True, nullable=True)  # user_key 저장!
    kakao_channel_added_at = Column(DateTime, nullable=True)

    # 기존 필드들...
```

```python
# api/routes/kakao_webhook.py

@router.post("/webhook")
async def kakao_webhook(request: Request):
    data = await request.json()
    user_key = data.get("user_key")

    # DB에 저장
    user = await db.get_user_by_kakao_key(user_key)

    if not user:
        # 신규 사용자 생성
        user = await db.create_user(
            kakao_user_key=user_key,
            kakao_channel_added_at=datetime.now()
        )

    return {"status": "ok"}
```

---

## 🧪 테스트 방법

### 1. Webhook 엔드포인트 확인

```bash
# 서버 실행
uvicorn api.main:app --reload

# 브라우저에서 접속
http://localhost:8000/api/v1/kakao/webhook/test

# 예상 응답:
{
  "status": "ok",
  "message": "Webhook endpoint is working!",
  "endpoint": "/api/v1/kakao/webhook"
}
```

### 2. Swagger UI에서 테스트

```bash
# 1. 서버 실행
uvicorn api.main:app --reload

# 2. 브라우저에서 Swagger 접속
http://localhost:8000/docs

# 3. POST /api/v1/kakao/webhook/simulate 찾기
# 4. Try it out 클릭
# 5. 파라미터 입력:
#    - user_key: test_user_123
#    - message: 테스트 메시지
# 6. Execute 클릭

# 7. FastAPI 로그 확인 (터미널)
```

### 3. 실제 카카오 메시지로 테스트

```bash
# 1. ngrok 실행
ngrok http 8000

# 2. Webhook URL 설정 (카카오 채널 관리자)
# https://abc123.ngrok.io/api/v1/kakao/webhook

# 3. 카카오톡에서 채널에 메시지 전송
# "안녕하세요"

# 4. FastAPI 로그에서 user_key 확인!
```

---

## 🔐 보안 주의사항

### API 키 보안

```bash
# ✅ 올바른 방법: .env 파일에 저장
KAKAO_API_KEY=your_api_key_here

# ❌ 잘못된 방법: 코드에 하드코딩
client = KakaoClient(api_key="abc123...")  # 절대 금지!
```

### user_key 보안

```yaml
보안 등급: 중간
  - user_key는 민감 정보 (개인 식별 가능)
  - DB에 저장 시 암호화 권장
  - 로그에 전체 출력 지양 (마스킹 권장)

로그 마스킹 예시:
  - user_abc123def456 → user_abc***def456
```

---

## ❓ FAQ

### Q1: user_key는 바뀌나요?

**A:** 아니오, 고정입니다.
- 사용자가 채널 친구를 삭제해도 user_key는 동일
- 재친구 추가 시에도 같은 user_key 사용

### Q2: user_key 없이 전화번호만으로 보낼 수 있나요?

**A:** 친구톡은 불가능, 알림톡만 가능합니다.
- **친구톡**: user_key 필수
- **알림톡**: 전화번호만 있으면 가능

### Q3: 여러 명에게 한 번에 보낼 수 있나요?

**A:** 네, 가능합니다.

```python
# 여러 사용자에게 일괄 전송
user_keys = ["user_123", "user_456", "user_789"]

for user_key in user_keys:
    await client.send_friend_talk(
        user_key=user_key,
        message="오늘의 정원 가꾸기 🌱"
    )
```

### Q4: Webhook 설정이 복잡하지 않나요?

**A:** 3단계면 끝입니다!
1. FastAPI 서버 실행
2. ngrok으로 외부 노출
3. 카카오 채널 관리자에서 URL 설정

개발 중에는 **Webhook 시뮬레이션**을 사용하면 더 간단합니다.

### Q5: ngrok 없이 Webhook을 테스트할 수 있나요?

**A:** 네, 2가지 방법이 있습니다:

**방법 1: Webhook 시뮬레이션 (권장)**
```bash
curl -X POST http://localhost:8000/api/v1/kakao/webhook/simulate \
  -H "Content-Type: application/json" \
  -d '{"user_key": "test_123", "message": "안녕"}'
```

**방법 2: 실제 서버 배포**
- AWS EC2, Google Cloud Run 등에 배포
- 고정 도메인 사용

---

## 📚 다음 단계

### 1. 즉시 가능 (로컬 테스트)

```bash
# 1. FastAPI 서버 실행
uvicorn api.main:app --reload

# 2. Webhook 시뮬레이션
curl -X POST http://localhost:8000/api/v1/kakao/webhook/simulate \
  -d '{"user_key": "test_user_123", "message": "안녕하세요"}'

# 3. 로그 확인
```

### 2. 오늘 중 (실제 카카오 연동)

```bash
# 1. ngrok 설치
brew install ngrok  # macOS
# 또는 https://ngrok.com/download

# 2. ngrok 실행
ngrok http 8000

# 3. 카카오 채널 Webhook URL 설정
# 4. 카카오톡에서 메시지 전송
# 5. user_key 확인!
```

### 3. 이번 주 (DB 저장 & 자동화)

- [ ] User 모델에 kakao_user_key 필드 추가
- [ ] Webhook에서 DB 저장 로직 구현
- [ ] 일일 대화 플로우에 친구톡 통합

---

## 🎯 요약

```yaml
API 키:
  - 개발자 앱 인증 키
  - .env 파일에 저장
  - 1개만 존재
  - 카카오 개발자 콘솔에서 발급

user_key:
  - 각 사용자의 고유 ID
  - Webhook으로 자동 수집
  - 사용자 수만큼 존재
  - 친구톡 발송 시 필수
  - DB에 저장 권장

확인 방법:
  1. Webhook 자동 수집 (권장) ✅
  2. Webhook 시뮬레이션 (로컬 테스트)
  3. 채널 관리자에서 수동 확인
```

---

## 🚀 바로 시작하기

```bash
# 1. FastAPI 서버 실행
uvicorn api.main:app --reload

# 2. Swagger UI 접속
# http://localhost:8000/docs

# 3. POST /api/v1/kakao/webhook/simulate 테스트
# user_key: test_user_123
# message: 안녕하세요

# 4. 로그에서 user_key 확인!
```

**지금 바로 테스트해보세요!** 🎉
