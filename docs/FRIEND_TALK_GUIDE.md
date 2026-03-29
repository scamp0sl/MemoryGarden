# 친구톡 (Friend Talk) 사용 가이드

## 📋 목차

1. [왜 친구톡인가?](#왜-친구톡인가)
2. [친구톡 vs 알림톡 비교](#친구톡-vs-알림톡-비교)
3. [친구톡 설정 방법](#친구톡-설정-방법)
4. [코드 사용 예시](#코드-사용-예시)
5. [Memory Garden 통합](#memory-garden-통합)
6. [시나리오(발화) vs 친구톡 API](#시나리오발화-vs-친구톡-api)
7. [FAQ](#faq)

---

## 🎯 왜 친구톡인가?

### 현재 상황
- ✅ 카카오 채널 등록 완료
- ✅ API 키 발급 완료
- ❌ 알림톡 템플릿 승인 대기 (3-5일 소요)

### 친구톡의 장점
```yaml
즉시 사용 가능: ✅
  - 템플릿 승인 불필요
  - 채널 등록 후 바로 API 호출

자유로운 메시지: ✅
  - 템플릿 제약 없음
  - AI 생성 메시지도 바로 전송
  - 이모지, 줄바꿈 자유

개발/테스트 최적: ✅
  - MVP 단계에 적합
  - 빠른 iteration
  - 실시간 메시지 수정 가능

비용 효율적: ✅
  - 별도 과금 없음
  - 채널 친구에게만 발송
```

### 제약 사항
```yaml
친구 추가 필수: ⚠️
  - 사용자가 채널을 친구로 추가해야 함
  - 친구 추가 유도 필요

광고성 메시지 불가: ⚠️
  - 정보성 메시지만 가능
  - Memory Garden은 정보성이므로 OK ✅
```

---

## 📊 친구톡 vs 알림톡 비교

| 항목 | 친구톡 (Friend Talk) | 알림톡 (Alimtalk) |
|------|---------------------|------------------|
| **템플릿 승인** | 불필요 ✅ | 필수 (3-5일) |
| **친구 추가** | 필수 | 불필요 |
| **메시지 형식** | 자유 형식 ✅ | 고정 템플릿 |
| **발송 대상** | 채널 친구만 | 전화번호만 있으면 |
| **광고성 메시지** | 불가 | 불가 |
| **즉시 사용** | O ✅ | X |
| **MVP/테스트** | 적합 ✅ | 어려움 |
| **정식 서비스** | 제한적 | 적합 ✅ |

### 권장 사용 전략

```mermaid
graph LR
    A[Phase 1: 개발] -->|친구톡| B[Phase 2: 베타]
    B -->|친구톡 + 알림톡| C[Phase 3: 정식]
    C -->|알림톡 중심| D[서비스 운영]
```

**Phase 1 (현재): 친구톡으로 개발/테스트**
- 일일 대화 프롬프트
- 주간 회상 질문
- 감정 체크

**Phase 2 (베타): 친구톡 + 알림톡 병행**
- 일상 대화: 친구톡
- 위험 알림: 알림톡 (보호자)

**Phase 3 (정식): 알림톡 중심**
- 모든 중요 알림: 알림톡
- 보조 메시지: 친구톡

---

## 🔧 친구톡 설정 방법

### 1. 카카오 채널 준비

#### ✅ 이미 완료한 것
- [x] 카카오 채널 생성
- [x] 채널 URL 확인: `http://pf.kakao.com/_tDPzX`
- [x] API 키 발급

#### 📝 추가로 필요한 것

**1) 발신 프로필 키 확인**

카카오 비즈니스 센터에서:
```
카카오 채널 관리 > 관리 > 상세 설정 > 발신 프로필 키
```

예시: `@abcd1234` 또는 `_tDPzX`

**2) 채널 친구 추가**

테스트를 위해 본인이 먼저 채널 친구 추가:
```
http://pf.kakao.com/_tDPzX/chat
```

클릭 후 "친구 추가" 버튼 클릭

**3) 환경 변수 설정**

`.env` 파일에 추가:
```bash
# 카카오 API 설정
KAKAO_API_KEY=your_rest_api_key_here          # REST API 키
KAKAO_ADMIN_KEY=your_admin_key_here           # Admin 키 (선택)
KAKAO_CHANNEL_ID=_tDPzX                       # 채널 ID (발신 프로필 키)
```

### 2. user_key 확인 방법

친구톡은 전화번호가 아닌 **user_key**를 사용합니다.

#### 방법 1: Webhook으로 자동 수집 (권장)

```python
# api/routes/kakao_webhook.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    """카카오 메시지 수신 Webhook"""
    data = await request.json()

    # user_key 추출
    user_key = data.get("user_key")
    message = data.get("content")

    # DB에 저장
    # user_key <-> user_id 매핑

    return {"status": "ok"}
```

#### 방법 2: 수동 확인

카카오 채널 관리자 센터에서:
```
채팅방 > 사용자 클릭 > 프로필 > 사용자 KEY 복사
```

---

## 💻 코드 사용 예시

### 기본 사용법

```python
from services.kakao_client import KakaoClient

# 1. Mock 모드 (개발/테스트)
client = KakaoClient(mock_mode=True)

result = await client.send_friend_talk(
    user_key="test_user_123",
    message="안녕하세요! 오늘의 정원 가꾸기 시간입니다 🌱"
)

print(result)
# {
#     "success": True,
#     "message_id": "mock_ft_a1b2c3d4e5f6",
#     "timestamp": "2025-02-12T10:00:00",
#     "user_key": "test_user_123",
#     "message_length": 24,
#     "mode": "mock"
# }
```

```python
# 2. Real 모드 (실제 전송)
client = KakaoClient(mock_mode=False)

result = await client.send_friend_talk(
    user_key="실제_사용자_KEY",  # Webhook이나 채널 관리자에서 확인
    message="""안녕하세요! Memory Garden 🌱

오늘의 대화 주제입니다.

어제 저녁은 무엇을 드셨나요?
가족이나 친구와 함께 드셨다면 어떤 이야기를 나누셨는지도 말씀해 주세요.

답변을 기다리고 있을게요 😊"""
)
```

### Memory Garden 일일 대화 통합

```python
# core/dialogue/dialogue_manager.py

async def send_daily_prompt(self, user_id: str):
    """일일 대화 프롬프트 전송 (친구톡 사용)"""
    from services.kakao_client import get_kakao_client

    # 1. 사용자의 user_key 조회
    user = await self.db.get_user(user_id)
    kakao_user_key = user.kakao_user_key  # DB에 저장된 user_key

    # 2. 오늘의 질문 생성
    prompt = await self._generate_daily_question(user_id)

    # 3. 친구톡 전송
    kakao_client = get_kakao_client(mock_mode=False)

    result = await kakao_client.send_friend_talk(
        user_key=kakao_user_key,
        message=f"""안녕하세요! Memory Garden 🌱

{prompt}

답변을 기다리고 있을게요 😊"""
    )

    # 4. 전송 로그 저장
    await self._log_message_sent(user_id, result)

    return result
```

### 스케줄링 (Celery Beat)

```python
# tasks/dialogue.py

from celery import Celery
from datetime import datetime

app = Celery('memory_garden')

@app.task
def send_morning_prompts():
    """아침 9시 일일 프롬프트 전송"""
    from core.dialogue.dialogue_manager import DialogueManager

    manager = DialogueManager()

    # 활성 사용자 목록 조회
    active_users = get_active_users()

    for user in active_users:
        try:
            # 비동기 작업을 동기로 변환
            asyncio.run(manager.send_daily_prompt(user.id))

        except Exception as e:
            logger.error(f"Failed to send prompt to {user.id}: {e}")

# Celery Beat 스케줄 설정
app.conf.beat_schedule = {
    'morning-prompts': {
        'task': 'tasks.dialogue.send_morning_prompts',
        'schedule': crontab(hour=9, minute=0),  # 매일 9시
    },
}
```

---

## 🔗 Memory Garden 통합

### 전체 워크플로우

```yaml
1. 사용자 온보딩:
  - 카카오 채널 친구 추가
  - Webhook으로 user_key 자동 수집
  - DB에 user_id <-> user_key 매핑 저장

2. 일일 대화:
  - Celery Beat: 매일 9시 트리거
  - DialogueManager: 맞춤 질문 생성
  - KakaoClient: 친구톡 전송

3. 사용자 응답:
  - Webhook: 메시지 수신
  - MessageProcessor: 분석 실행
  - MemoryManager: 4계층 저장
  - RiskEvaluator: 위험도 평가

4. 위험 알림 (ORANGE/RED):
  - NotificationService: 보호자 알림
  - 친구톡 (사용자) + 알림톡 (보호자)
```

### DB 스키마 추가

```python
# database/models.py

class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid4)
    kakao_user_key = Column(String, unique=True, nullable=True)  # 추가!
    kakao_channel_added_at = Column(DateTime, nullable=True)     # 추가!

    # 기존 필드들...
```

### Webhook 엔드포인트

```python
# api/routes/kakao.py

from fastapi import APIRouter, Request, HTTPException
from core.workflow.message_processor import MessageProcessor

router = APIRouter(prefix="/kakao", tags=["kakao"])

@router.post("/webhook")
async def kakao_webhook(request: Request):
    """
    카카오 채널 메시지 수신 Webhook

    카카오톡에서 사용자 메시지를 받으면 자동으로 호출됨.
    """
    data = await request.json()

    # 1. user_key 추출 및 매핑
    user_key = data.get("user_key")
    message = data.get("content")

    # DB에서 user_id 조회
    user = await db.get_user_by_kakao_key(user_key)

    if not user:
        # 신규 사용자 생성
        user = await db.create_user(kakao_user_key=user_key)

    # 2. 메시지 처리
    processor = MessageProcessor(...)

    response = await processor.process(
        user_id=str(user.id),
        message=message,
        message_type="text"
    )

    # 3. 친구톡으로 응답
    from services.kakao_client import get_kakao_client

    kakao_client = get_kakao_client(mock_mode=False)

    await kakao_client.send_friend_talk(
        user_key=user_key,
        message=response
    )

    return {"status": "ok"}
```

---

## 🤔 시나리오(발화) vs 친구톡 API

### 시나리오 빌더 (발화)

```yaml
장점:
  - 코딩 불필요 (No-Code)
  - 카카오 관리자 UI에서 설정
  - 승인 절차 없음

단점:
  - 정해진 분기만 가능 (단순 챗봇)
  - AI 대화 불가능
  - LLM 연동 어려움
  - MCDI 분석 같은 복잡한 로직 불가능
```

**Memory Garden에 부적합한 이유:**
- ❌ AI 기반 자연어 처리 불가능
- ❌ 개인 맞춤 질문 생성 불가능
- ❌ MCDI 분석 로직 구현 불가능
- ❌ 4계층 메모리 시스템 연동 불가능

### 친구톡 API

```yaml
장점:
  - Python 코드로 완전 제어 ✅
  - LLM 통합 가능 ✅
  - MCDI 분석 가능 ✅
  - 개인화된 대화 ✅
  - 4계층 메모리 연동 ✅

단점:
  - 코딩 필요 (하지만 이미 구현됨 ✅)
  - Webhook 서버 필요 (FastAPI로 구현 가능 ✅)
```

**Memory Garden에 적합한 이유:**
- ✅ AI 기반 맞춤 질문
- ✅ 실시간 인지 기능 분석
- ✅ 복잡한 워크플로우 구현
- ✅ 기존 시스템과 완벽 통합

### 결론

**친구톡 API 사용 권장 ✅**

시나리오 빌더는 단순 FAQ 챗봇에는 적합하지만,
Memory Garden처럼 AI 기반 인지 분석이 필요한 서비스에는 부적합합니다.

---

## 🧪 테스트 방법

### 1. Mock 테스트 (즉시 가능)

```bash
# 친구톡 테스트 스크립트 실행
python scripts/test_friend_talk.py
```

출력 예시:
```
============================================================
Test 1: 친구톡 전송 (Mock 모드)
============================================================

✅ Success: True
📨 Message ID: mock_ft_a1b2c3d4e5f6
📊 Message Length: 54 characters
⏰ Timestamp: 2025-02-12T10:00:00

📝 Message Preview:
------------------------------------------------------------
안녕하세요! Memory Garden 🌱

오늘의 정원 가꾸기 시간입니다.

어제 저녁은 무엇을 드셨나요?
------------------------------------------------------------
```

### 2. Real API 테스트

```python
# scripts/test_friend_talk_real.py

import asyncio
from services.kakao_client import KakaoClient

async def test_real():
    client = KakaoClient(mock_mode=False)

    # 본인의 user_key로 테스트
    result = await client.send_friend_talk(
        user_key="YOUR_USER_KEY_HERE",  # 채널 관리자에서 확인
        message="테스트 메시지입니다 🌱"
    )

    print(result)

asyncio.run(test_real())
```

### 3. Webhook 테스트

```bash
# ngrok으로 로컬 서버 외부 노출
ngrok http 8000

# 카카오 채널 관리자에서 Webhook URL 설정
# https://your-ngrok-url.ngrok.io/api/v1/kakao/webhook

# FastAPI 서버 실행
uvicorn api.main:app --reload

# 카카오 채널에서 메시지 전송 → Webhook 확인
```

---

## ❓ FAQ

### Q1: 친구톡은 무료인가요?

**A:** 네, 무료입니다! 채널 친구에게 발송하는 것은 별도 비용이 없습니다.

### Q2: 친구가 아닌 사용자에게도 보낼 수 있나요?

**A:** 불가능합니다. 반드시 채널 친구 추가가 필요합니다.
→ 온보딩 시 친구 추가 유도 필요

### Q3: 하루에 몇 개까지 보낼 수 있나요?

**A:** 공식 제한은 없지만, 스팸으로 오인될 수 있으니:
- Memory Garden: 하루 2-3회 (아침, 점심, 저녁)

### Q4: 알림톡은 언제 사용해야 하나요?

**A:** 다음 경우에만 알림톡 필요:
- 채널 친구가 아닌 사용자에게 전송
- 보호자에게 위험 알림 전송 (ORANGE/RED)

### Q5: 친구톡으로 이미지도 보낼 수 있나요?

**A:** 네, 가능합니다!

```python
result = await client.send_friend_talk(
    user_key="user_123",
    message="오늘의 정원 🌱",
    image_url="https://your-server.com/images/garden.jpg"  # 추가 예정
)
```

### Q6: Webhook 설정이 복잡하지 않나요?

**A:** FastAPI로 간단히 구현 가능합니다:
```python
@router.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    data = await request.json()
    # 처리 로직
    return {"status": "ok"}
```

### Q7: 알림톡 승인은 얼마나 걸리나요?

**A:** 평균 3-5일 소요:
- 템플릿 등록
- 검수 대기 (2-3일)
- 승인 완료

→ 친구톡으로 먼저 개발 진행 권장 ✅

---

## 📚 다음 단계

1. **즉시 가능:**
   ```bash
   # Mock 테스트
   python scripts/test_friend_talk.py
   ```

2. **오늘 중:**
   - [ ] 본인 채널 친구 추가
   - [ ] .env에 API 키 설정
   - [ ] user_key 확인
   - [ ] Real 모드 테스트

3. **이번 주:**
   - [ ] Webhook 엔드포인트 구현
   - [ ] user_key 자동 수집 로직
   - [ ] DialogueManager에 친구톡 통합

4. **다음 주:**
   - [ ] Celery Beat 스케줄링
   - [ ] 일일 대화 플로우 테스트
   - [ ] 베타 사용자 초대

---

## 🎉 요약

```yaml
지금 바로 사용 가능: ✅
  - 친구톡 API 구현 완료
  - Mock 테스트 스크립트 제공
  - 채널 친구 추가만 하면 끝!

알림톡은 나중에: ⏰
  - 정식 서비스 준비 시
  - 보호자 알림 기능 추가 시
  - 템플릿 승인 받고 사용

Memory Garden은 친구톡으로 충분: ✅
  - 일일 대화 프롬프트
  - 개인 맞춤 질문
  - AI 기반 응답
```

**지금 시작하세요! 🚀**

```bash
python scripts/test_friend_talk.py
```
