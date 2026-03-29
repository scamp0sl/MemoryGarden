# 🚀 카카오 친구톡 빠른 시작 가이드

## ✅ 현재 상태 (모두 완료!)

```yaml
구현 완료:
  - ✅ 친구톡 API (KakaoClient.send_friend_talk)
  - ✅ Webhook 엔드포인트 (/kakao/webhook)
  - ✅ user_key 자동 수집 시스템
  - ✅ 테스트 스크립트 (Mock & Simulation)
  - ✅ FastAPI 서버 실행 중 (Port 8000)

설정 완료:
  - ✅ API 키 (.env 파일)
  - ✅ 카카오 채널 등록 (http://pf.kakao.com/_tDPzX)
```

---

## 🎯 핵심 개념 정리

### API 키 vs user_key

| 항목 | API 키 | user_key |
|------|--------|----------|
| **정의** | 개발자 앱 인증 키 | 각 사용자 고유 ID |
| **개수** | 1개 | 사용자 수만큼 |
| **위치** | .env 파일 | Webhook 수집 |
| **사용** | API 인증 | 메시지 발송 대상 |

**간단 비유:**
- **API 키** = 우체국 직원증 (우편물 보낼 권한)
- **user_key** = 수신자 주소 (누구에게 보낼지)

---

## 🧪 즉시 테스트 (3단계)

### 1단계: Webhook 엔드포인트 확인

```bash
curl -X GET "http://localhost:8000/kakao/webhook/test"

# 예상 응답:
{
  "status": "ok",
  "message": "Webhook endpoint is working!",
  "endpoint": "/api/v1/kakao/webhook"
}
```

✅ **성공!** Webhook 준비 완료

---

### 2단계: user_key 시뮬레이션 (로컬 테스트)

```bash
curl -X POST "http://localhost:8000/kakao/webhook/simulate?user_key=test_user_123&message=Hello"

# 예상 응답:
{
  "status": "ok",
  "user_key": "test_user_123",  # ← 이게 user_key!
  "message": "Simulation completed"
}
```

✅ **성공!** user_key 확인 완료

---

### 3단계: Swagger UI에서 테스트

```bash
# 1. 브라우저 열기
http://localhost:8000/docs

# 2. "kakao" 태그 찾기
# 3. POST /kakao/webhook/simulate 클릭
# 4. Try it out 클릭
# 5. 파라미터 입력:
#    - user_key: my_test_user_001
#    - message: 안녕하세요

# 6. Execute 클릭 → 결과 확인!
```

✅ **성공!** Swagger UI 테스트 완료

---

## 🌱 Memory Garden에서 사용하기

### 친구톡 전송 예시

```python
from services.kakao_client import KakaoClient

# 1. 클라이언트 초기화
client = KakaoClient(mock_mode=False)  # 실제 전송

# 2. user_key로 메시지 전송
result = await client.send_friend_talk(
    user_key="user_abc123",  # Webhook으로 수집한 user_key
    message="""안녕하세요! Memory Garden 🌱

오늘의 정원 가꾸기 시간입니다.

어제 저녁은 무엇을 드셨나요?
가족이나 친구와 함께 드셨다면 어떤 이야기를 나누셨는지도 말씀해 주세요."""
)

print(result)
# {
#     "success": True,
#     "message_id": "ft_xyz789",
#     "user_key": "user_abc123",
#     "message_length": 100
# }
```

---

## 🔄 실제 user_key 수집 방법

### 방법 1: ngrok으로 Webhook 설정 (권장)

```bash
# 1. ngrok 설치 (macOS)
brew install ngrok

# 또는 다운로드: https://ngrok.com/download

# 2. ngrok 실행
ngrok http 8000

# 출력 예시:
# Forwarding   https://abc123.ngrok.io -> http://localhost:8000
#              ^^^^^^^^^^^^^^^^^^^^^^^^
#              이 URL을 복사!

# 3. 카카오 채널 관리자 설정
# - https://business.kakao.com 접속
# - 채널 선택 (Memory Garden)
# - 관리 > 상세 설정 > Webhook URL
# - https://abc123.ngrok.io/kakao/webhook 입력
# - 저장

# 4. 카카오톡에서 채널에 메시지 전송
# "안녕하세요"

# 5. FastAPI 로그 확인 (터미널)
# ============================================================
# 📨 카카오 메시지 수신!
# ============================================================
# 👤 user_key: user_abc123def456  # ← 이것을 복사!
# 💬 메시지: 안녕하세요
# ============================================================
```

### 방법 2: 로컬 테스트 (개발용)

```bash
# 실제 카카오 연동 없이 테스트
curl -X POST "http://localhost:8000/kakao/webhook/simulate?user_key=dev_user_001&message=Test"

# 코드에서 사용
client = KakaoClient(mock_mode=False)
await client.send_friend_talk(
    user_key="dev_user_001",  # 시뮬레이션한 user_key
    message="테스트 메시지입니다"
)
```

---

## 📊 DB에 user_key 저장

### User 모델 업데이트

```python
# database/models.py

class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid4)
    kakao_user_key = Column(String, unique=True, nullable=True)  # 추가!
    kakao_channel_added_at = Column(DateTime, nullable=True)     # 추가!

    # 기존 필드들...
```

### Webhook에서 자동 저장

```python
# api/routes/kakao_webhook.py

@router.post("/webhook")
async def kakao_webhook(request: Request):
    data = await request.json()
    user_key = data.get("user_key")

    # DB에서 user_key로 사용자 찾기
    user = await db.get_user_by_kakao_key(user_key)

    if not user:
        # 신규 사용자 생성
        user = await db.create_user(
            kakao_user_key=user_key,
            kakao_channel_added_at=datetime.now()
        )

    # 메시지 처리...
    return {"status": "ok"}
```

---

## 🎯 다음 단계 체크리스트

### 오늘 (완료 ✅)
- [x] 친구톡 API 구현
- [x] Webhook 엔드포인트 생성
- [x] user_key 수집 시스템
- [x] 테스트 스크립트 작성
- [x] FastAPI 서버 실행

### 내일
- [ ] 본인 카카오 채널 친구 추가
- [ ] ngrok 설치 및 실행
- [ ] Webhook URL 설정 (카카오 채널 관리자)
- [ ] 실제 메시지로 user_key 수집

### 이번 주
- [ ] User 모델에 kakao_user_key 필드 추가
- [ ] Alembic 마이그레이션 생성
- [ ] DB 저장 로직 구현
- [ ] DialogueManager에 친구톡 통합

### 다음 주
- [ ] Celery Beat 스케줄링 (매일 9시)
- [ ] 일일 대화 플로우 테스트
- [ ] 베타 사용자 초대

---

## 📚 참고 문서

### 주요 가이드
1. **`docs/FRIEND_TALK_GUIDE.md`** - 친구톡 완벽 가이드
2. **`docs/USER_KEY_GUIDE.md`** - user_key 확인 방법
3. **`docs/KAKAO_TESTING_GUIDE.md`** - 카카오 테스팅 가이드

### 테스트 스크립트
```bash
# 친구톡 테스트
python scripts/test_friend_talk.py

# E2E 테스트 (실제 API)
python scripts/test_kakao_e2e.py
```

### API 문서
```bash
# Swagger UI
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc
```

---

## ❓ 자주 묻는 질문

### Q: API 키는 어디서 확인하나요?

**A:** 카카오 개발자 콘솔에서 확인
```
1. https://developers.kakao.com 접속
2. 내 애플리케이션 선택
3. 앱 설정 > 앱 키
4. REST API 키 복사
```

### Q: user_key는 어떻게 확인하나요?

**A:** 3가지 방법
1. **Webhook 자동 수집** (권장) - 위 "방법 1" 참조
2. **시뮬레이션** - 개발/테스트용
3. **채널 관리자** - 수동 확인

### Q: 친구톡과 알림톡의 차이는?

**A:**

| 항목 | 친구톡 | 알림톡 |
|------|--------|--------|
| 템플릿 승인 | 불필요 ✅ | 필수 (3-5일) |
| 친구 추가 | 필수 | 불필요 |
| 메시지 형식 | 자유 ✅ | 고정 템플릿 |
| 즉시 사용 | 가능 ✅ | 불가능 |

**Memory Garden 전략:**
- **개발/베타**: 친구톡 사용
- **정식 서비스**: 알림톡 (보호자 알림)

### Q: 여러 명에게 한 번에 보낼 수 있나요?

**A:** 네, 가능합니다.
```python
user_keys = ["user_001", "user_002", "user_003"]

for user_key in user_keys:
    await client.send_friend_talk(
        user_key=user_key,
        message="오늘의 정원 가꾸기 🌱"
    )
```

---

## 🎉 요약

```yaml
✅ 구현 완료:
  - 친구톡 API (KakaoClient)
  - Webhook 엔드포인트
  - user_key 자동 수집
  - 테스트 환경 완비

✅ 즉시 사용 가능:
  - Mock 모드 테스트
  - Webhook 시뮬레이션
  - Swagger UI 테스트

🎯 다음 단계:
  - ngrok으로 Webhook 연동
  - 실제 user_key 수집
  - DB 저장 로직 구현
  - 일일 대화 플로우 통합
```

---

## 🚀 지금 바로 테스트!

```bash
# 1. Webhook 확인
curl -X GET "http://localhost:8000/kakao/webhook/test"

# 2. user_key 시뮬레이션
curl -X POST "http://localhost:8000/kakao/webhook/simulate?user_key=my_user_001&message=Hello"

# 3. Swagger UI
http://localhost:8000/docs
```

**성공했습니다!** 🎉

이제 Memory Garden에서 카카오 친구톡을 사용할 준비가 완료되었습니다!
