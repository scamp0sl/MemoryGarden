# 대화 모듈 사용 가이드

Memory Garden 프로젝트의 대화(Dialogue) 모듈 사용 가이드입니다.

---

## 📋 목차

1. [개요](#1-개요)
2. [DialogueManager](#2-dialoguemanager)
3. [ResponseGenerator](#3-responsegenerator)
4. [PromptBuilder](#4-promptbuilder)
5. [실전 예제](#5-실전-예제)
6. [성능 최적화](#6-성능-최적화)

---

## 1. 개요

### 모듈 구성

```
core/dialogue/
├── __init__.py              # 모듈 export
├── dialogue_manager.py      # 대화 흐름 관리
├── response_generator.py    # AI 응답 생성
└── prompt_builder.py        # 프롬프트 구성
```

### 주요 기능

| 모듈 | 기능 | 입력 | 출력 |
|------|------|------|------|
| **DialogueManager** | 세션/턴 관리 | user_id, message | session_id, history |
| **ResponseGenerator** | AI 응답 생성 | message, context | response text |
| **PromptBuilder** | 프롬프트 구성 | category, context | formatted prompt |

### 환경 설정

```bash
# .env 파일에 OpenAI API 키 설정
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379/0
```

---

## 2. DialogueManager

### 2.1 기본 사용법

```python
from core.dialogue import DialogueManager

# DialogueManager 생성
manager = DialogueManager()

# 세션 시작
session_id = await manager.start_session(
    user_id="user123",
    initial_context={
        "user_name": "홍길동",
        "garden_name": "행복한 정원"
    }
)

# 대화 턴 추가
await manager.add_turn(
    user_id="user123",
    user_message="오늘 점심 뭐 드셨어요?",
    assistant_message="된장찌개 먹었어요",
    metadata={"emotion": "neutral", "mcdi_score": 78.5}
)

# 대화 히스토리 조회
history = await manager.get_conversation_history("user123")

# 세션 종료
await manager.end_session("user123")
```

### 2.2 세션 관리

```python
# 세션 조회
session = await manager.get_session("user123")
print(session["turn_count"])  # 대화 턴 수
print(session["context"])      # 사용자 컨텍스트

# 세션 통계
stats = await manager.get_session_stats("user123")
print(stats["turn_count"])     # 15
print(stats["history_length"]) # 10 (최근 10턴만 유지)
```

### 2.3 컨텍스트 윈도우

**기본 설정: 최근 10턴 유지 (SPEC.md 기준)**

```python
# 컨텍스트 윈도우 크기 조정
manager = DialogueManager(max_context_turns=20)

# 대화 히스토리 조회 (limit 적용)
history = await manager.get_conversation_history(
    user_id="user123",
    limit=5  # 최근 5턴만 가져오기
)
```

**자동 정리:**
- 대화 턴이 max_context_turns를 초과하면 오래된 턴 자동 제거
- Redis TTL: 24시간 (86400초)

### 2.4 컨텍스트 업데이트

```python
# 사용자 컨텍스트 업데이트
await manager.update_context(
    user_id="user123",
    context_updates={
        "recent_emotion": "기쁨",
        "biographical_facts": {
            "daughter_name": "수진",
            "hometown": "부산"
        }
    }
)
```

### 2.5 통합 응답 생성

```python
# DialogueManager를 통한 응답 생성 (컨텍스트 자동 주입)
response = await manager.generate_response(
    user_id="user123",
    user_message="오늘 기분이 좋아요",
    next_question="무슨 일이 있었나요?",
    emotion="joy",
    emotion_intensity=0.85
)

print(response)
# "기분이 좋으시다니 정말 다행이에요! 🌱
#  무슨 일이 있었나요?"
```

---

## 3. ResponseGenerator

### 3.1 기본 사용법

```python
from core.dialogue import ResponseGenerator

# ResponseGenerator 생성
generator = ResponseGenerator(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=300
)

# 일반 응답 생성
response = await generator.generate(
    user_message="오늘 점심은 된장찌개요",
    conversation_history=[
        {"role": "user", "content": "오늘 점심 뭐 드셨어요?"},
        {"role": "assistant", "content": "말씀해주세요!"}
    ],
    user_context={
        "user_name": "홍길동",
        "garden_name": "행복한 정원"
    },
    next_question="어떤 반찬과 함께 드셨어요?"
)

print(response)
```

### 3.2 공감적 응답 생성

```python
# 감정 기반 공감 응답
response = await generator.generate_empathetic_response(
    user_message="딸이 전화해서 기분 좋아요",
    detected_emotion="joy",          # EmotionDetector 결과
    emotion_intensity=0.85,          # 0.0~1.0
    conversation_history=[],
    user_context={"user_name": "홍길동"}
)

print(response)
# "딸분이 전화하셨군요! 정말 기분 좋으셨겠어요 😊
#  어떤 이야기를 나누셨나요?"
```

### 3.3 감정별 응답 전략

**내부 감정 대응 가이드:**

```python
emotion_guides = {
    "joy": "함께 기뻐하며 긍정적으로 반응",
    "sadness": "공감하되 과도한 동정 피함, 경청",
    "anger": "감정 인정, 차분하게 대응",
    "fear": "안심시키되 걱정 무시하지 않음",
    "surprise": "상황 확인, 긍정적 전환",
    "neutral": "자연스럽게 대화 이어감"
}
```

### 3.4 모델 및 파라미터 조정

```python
# 빠른 응답 (기본)
generator = ResponseGenerator(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=200
)

# 더 창의적인 응답
generator = ResponseGenerator(
    model="gpt-4o",
    temperature=0.9,
    max_tokens=400
)

# 더 일관적인 응답
generator = ResponseGenerator(
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=200
)
```

---

## 4. PromptBuilder

### 4.1 시스템 프롬프트 생성

```python
from core.dialogue import PromptBuilder

# PromptBuilder 생성
builder = PromptBuilder()

# 시스템 프롬프트 생성
system_prompt = builder.build_system_prompt(
    user_name="홍길동",
    recent_emotion="기쁨",
    biographical_facts={
        "daughter_name": "수진",
        "hometown": "부산",
        "favorite_food": "된장찌개"
    },
    garden_name="행복한 정원"
)

print(system_prompt)
# 정원사 페르소나 + 사용자 정보 포함된 시스템 프롬프트
```

### 4.2 질문 프롬프트 생성

```python
# 회상 질문 생성
question_prompt = builder.build_question_prompt(
    category="reminiscence",
    user_context={
        "user_profile": {"name": "홍길동", "age": 75},
        "previous_conversations": "부산에서 오래 사셨다고 하셨죠",
        "current_season": "겨울"
    }
)

# 일화 기억 질문
question_prompt = builder.build_question_prompt(
    category="daily_episodic",
    user_context={
        "today": "2025-02-10 월요일",
        "today_events": "점심에 된장찌개 먹음",
        "last_conversation": "오늘 아침 대화"
    }
)

# 이름대기 질문
question_prompt = builder.build_question_prompt(
    category="naming",
    user_context={
        "difficulty": "medium",
        "category": "음식"
    }
)

# 시간 지남력 질문
question_prompt = builder.build_question_prompt(
    category="temporal",
    user_context={
        "today": "2025-02-10 월요일",
        "season": "겨울",
        "recent_holiday": "설날 (2025-01-29)"
    }
)
```

### 4.3 분석 프롬프트 생성

```python
# 의미적 표류 분석
analysis_prompt = builder.build_analysis_prompt(
    analysis_type="semantic_drift",
    input_data={
        "question": "오늘 점심 뭐 드셨어요?",
        "user_response": "봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요"
    }
)

# 서사 일관성 분석
analysis_prompt = builder.build_analysis_prompt(
    analysis_type="narrative_coherence",
    input_data={
        "user_response": "오늘 딸이 와서 같이 밥 먹었어요. 그래서 기분 좋았어요."
    }
)
```

### 4.4 사실 추출 프롬프트

```python
# 대화에서 사실 추출
fact_prompt = builder.build_fact_extraction_prompt(
    conversation_history=[
        {"role": "user", "content": "딸 이름은 수진이에요"},
        {"role": "assistant", "content": "수진 씨 멋진 이름이네요!"},
        {"role": "user", "content": "고향은 부산이고요"},
        {"role": "assistant", "content": "부산 좋은 곳이죠!"}
    ]
)
```

---

## 5. 실전 예제

### 5.1 MessageProcessor에서 사용

```python
# core/workflow/message_processor.py

from core.dialogue import DialogueManager
from core.nlp import EmotionDetector

class MessageProcessor:
    def __init__(self):
        self.dialogue_manager = DialogueManager()
        self.emotion_detector = EmotionDetector()

    async def process(self, user_id: str, message: str):
        # 1. 감정 분석
        emotion_result = await self.emotion_detector.detect(message)

        # 2. AI 응답 생성 (컨텍스트 자동 주입)
        response = await self.dialogue_manager.generate_response(
            user_id=user_id,
            user_message=message,
            emotion=emotion_result.primary_emotion.value,
            emotion_intensity=emotion_result.intensity
        )

        # 3. 대화 턴 저장
        await self.dialogue_manager.add_turn(
            user_id=user_id,
            user_message=message,
            assistant_message=response,
            metadata={
                "emotion": emotion_result.primary_emotion.value,
                "emotion_intensity": emotion_result.intensity
            }
        )

        return response
```

### 5.2 온보딩 플로우

```python
async def onboarding_flow(user_id: str):
    """첫 사용자 온보딩"""
    manager = DialogueManager()

    # 세션 시작
    session_id = await manager.start_session(user_id)

    # 1단계: 이름 수집
    response1 = await manager.generate_response(
        user_id=user_id,
        user_message="",  # 첫 메시지
        next_question="먼저 어떻게 부르면 좋을까요?"
    )

    # 사용자 응답 대기...
    user_name = "홍길동"  # 예시

    # 컨텍스트 업데이트
    await manager.update_context(
        user_id=user_id,
        context_updates={"user_name": user_name}
    )

    # 2단계: 정원 이름 수집
    response2 = await manager.generate_response(
        user_id=user_id,
        user_message=user_name,
        next_question=f"{user_name}님, 반갑습니다! 정원 이름은 뭐로 하면 좋을까요?"
    )

    # ...
```

### 5.3 다음 질문 생성

```python
async def generate_next_question(
    user_id: str,
    category: str,  # reminiscence/daily_episodic/naming/temporal
    difficulty: str = "medium"
):
    """다음 질문 생성"""
    builder = PromptBuilder()

    # 사용자 컨텍스트 로드
    session = await dialogue_manager.get_session(user_id)
    user_context = session.get("context", {})

    # 카테고리별 컨텍스트 준비
    if category == "reminiscence":
        context = {
            "user_profile": user_context,
            "previous_conversations": "...",
            "current_season": get_current_season()
        }
    elif category == "temporal":
        context = {
            "today": datetime.now().strftime("%Y-%m-%d %A"),
            "season": get_current_season(),
            "recent_holiday": get_recent_holiday()
        }
    # ...

    # 질문 프롬프트 생성
    question_prompt = builder.build_question_prompt(
        category=category,
        user_context=context
    )

    # LLM 호출하여 질문 생성
    # (실제로는 LLMService 사용)
    question = await llm_service.call(question_prompt)

    return question
```

---

## 6. 성능 최적화

### 6.1 모델 선택

```python
# 빠르고 저렴한 모델 (권장)
generator = ResponseGenerator(model="gpt-4o-mini")

# 더 정확한 모델 (특별한 경우)
generator = ResponseGenerator(model="gpt-4o")
```

**비용 비교:**
- gpt-4o-mini: $0.15/1M tokens (input), $0.60/1M tokens (output)
- gpt-4o: $2.50/1M tokens (input), $10.00/1M tokens (output)

### 6.2 토큰 최적화

```python
# max_tokens 조정
generator = ResponseGenerator(
    max_tokens=200  # 짧은 응답 (기본 300)
)

# 컨텍스트 윈도우 크기 제한
manager = DialogueManager(max_context_turns=5)  # 기본 10
```

### 6.3 캐싱 전략

```python
from database.redis_client import redis_client
import hashlib

async def get_cached_response(user_message: str) -> Optional[str]:
    """응답 캐싱 (동일 질문 반복 시)"""

    # 캐시 키 생성
    cache_key = f"response:{hashlib.md5(user_message.encode()).hexdigest()}"

    # 캐시 확인
    cached = await redis_client.get_cache(cache_key)
    if cached:
        return cached

    # 캐시 미스 - 새로 생성
    response = await generator.generate(...)

    # 캐싱 (30분)
    await redis_client.set_cache(cache_key, response, ttl=1800)

    return response
```

### 6.4 배치 처리

```python
# 여러 사용자 동시 처리
user_ids = ["user1", "user2", "user3"]
messages = ["메시지1", "메시지2", "메시지3"]

# 병렬 실행
import asyncio
tasks = [
    manager.generate_response(uid, msg)
    for uid, msg in zip(user_ids, messages)
]
results = await asyncio.gather(*tasks)
```

---

## 📊 테스트

```bash
# Dialogue 모듈 테스트
python scripts/test_dialogue_modules.py

# 예상 출력:
# ============================================================
# 🔍 PromptBuilder Test
# ============================================================
#
# 1️⃣ System Prompt Generation
#   ✅ Generated 523 characters
#
# 2️⃣ Question Prompt Generation (reminiscence)
#   ✅ Generated 312 characters
#
# ...
#
# ✅ All tests passed!
```

---

## ✅ 체크리스트

Dialogue 모듈 설정 완료 후 확인:

- [ ] OPENAI_API_KEY 설정 (.env)
- [ ] REDIS_URL 설정 (.env)
- [ ] `python scripts/test_dialogue_modules.py` 성공
- [ ] 세션 관리 정상 동작 확인
- [ ] 컨텍스트 윈도우 (10턴) 확인
- [ ] 응답 품질 확인
- [ ] MessageProcessor에 통합

---

**작성일:** 2025-02-10
**작성자:** Memory Garden Team
