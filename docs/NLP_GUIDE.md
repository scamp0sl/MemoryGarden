# NLP 모듈 사용 가이드

Memory Garden 프로젝트의 자연어 처리(NLP) 모듈 사용 가이드입니다.

---

## 📋 목차

1. [개요](#1-개요)
2. [감정 분석기](#2-감정-분석기-emotiondetector)
3. [키워드 추출기](#3-키워드-추출기-keywordextractor)
4. [실전 예제](#4-실전-예제)
5. [프롬프트 커스터마이징](#5-프롬프트-커스터마이징)
6. [성능 최적화](#6-성능-최적화)

---

## 1. 개요

### 모듈 구성

```
core/nlp/
├── __init__.py              # 모듈 export
├── emotion_detector.py      # 감정 분석기
└── keyword_extractor.py     # 키워드 추출기

services/
└── llm_service.py           # OpenAI API 래퍼

config/
└── prompts.py               # 프롬프트 정의
```

### 주요 기능

| 모듈 | 기능 | 입력 | 출력 |
|------|------|------|------|
| **EmotionDetector** | 감정 분석 | 텍스트 | 감정 라벨 + 강도 (0.0~1.0) |
| **KeywordExtractor** | 키워드 추출 | 텍스트 | 키워드 리스트 + 중요도 |

### 환경 설정

```bash
# .env 파일에 OpenAI API 키 설정
OPENAI_API_KEY=sk-...
```

---

## 2. 감정 분석기 (EmotionDetector)

### 2.1 기본 사용법

```python
from core.nlp import EmotionDetector, EmotionCategory

# 감정 분석기 생성
detector = EmotionDetector()

# 감정 분석
text = "오늘 딸이 전화해서 정말 기분 좋았어요!"
result = await detector.detect(text)

# 결과 출력
print(result.primary_emotion)  # EmotionCategory.JOY
print(result.intensity)         # 0.85
print(result.keywords)          # ['기분', '좋았어요']
```

### 2.2 감정 카테고리

```python
class EmotionCategory(str, Enum):
    JOY = "joy"           # 기쁨
    SADNESS = "sadness"   # 슬픔
    ANGER = "anger"       # 분노
    FEAR = "fear"         # 두려움
    SURPRISE = "surprise" # 놀람
    NEUTRAL = "neutral"   # 중립
```

### 2.3 응답 구조

```python
class EmotionResult(BaseModel):
    primary_emotion: EmotionCategory  # 주요 감정
    intensity: float                  # 강도 (0.0~1.0)
    secondary_emotions: List[...]     # 부차적 감정들
    keywords: List[str]               # 감정 키워드
    rationale: str                    # 분석 근거
```

**예시 출력:**
```python
EmotionResult(
    primary_emotion=EmotionCategory.JOY,
    intensity=0.85,
    secondary_emotions=[
        SecondaryEmotion(emotion=EmotionCategory.SURPRISE, intensity=0.3)
    ],
    keywords=["기분", "좋았어요", "전화"],
    rationale="텍스트에서 긍정적인 감정 표현이 명확함"
)
```

### 2.4 배치 처리

```python
# 여러 텍스트를 동시에 분석
texts = [
    "오늘 기분이 좋아요!",
    "슬프고 외로워요",
    "화가 나네요"
]

results = await detector.detect_batch(texts)

for text, result in zip(texts, results):
    emotion_kr = detector.get_emotion_label_kr(result.primary_emotion)
    print(f"{text} → {emotion_kr} ({result.intensity:.2f})")
```

### 2.5 한국어 레이블

```python
# 감정 카테고리의 한국어 레이블
emotion_kr = detector.get_emotion_label_kr(EmotionCategory.JOY)
print(emotion_kr)  # "기쁨"
```

---

## 3. 키워드 추출기 (KeywordExtractor)

### 3.1 기본 사용법

```python
from core.nlp import KeywordExtractor, KeywordCategory

# 키워드 추출기 생성 (최대 10개 키워드)
extractor = KeywordExtractor(max_keywords=10)

# 키워드 추출
text = "오늘 점심에 된장찌개를 먹었어요. 딸이 끓여줬어요."
result = await extractor.extract(text)

# 결과 출력
print(result.main_topic)        # "식사 및 가족"
print(result.sub_topics)        # ["음식", "일상"]
print(result.keywords[0].word)  # "된장찌개"
```

### 3.2 키워드 카테고리

```python
class KeywordCategory(str, Enum):
    PERSON = "person"       # 인물
    PLACE = "place"         # 장소
    FOOD = "food"           # 음식
    EVENT = "event"         # 사건
    TIME = "time"           # 시간
    EMOTION = "emotion"     # 감정
    ACTIVITY = "activity"   # 활동
    OBJECT = "object"       # 사물
    CONCEPT = "concept"     # 개념
    OTHER = "other"         # 기타
```

### 3.3 키워드 구조

```python
class Keyword(BaseModel):
    word: str               # 키워드
    importance: float       # 중요도 (0.0~1.0)
    category: KeywordCategory  # 카테고리
    context: str            # 문맥/설명
```

**예시 출력:**
```python
Keyword(
    word="된장찌개",
    importance=0.9,
    category=KeywordCategory.FOOD,
    context="점심 메뉴"
)
```

### 3.4 카테고리별 필터링

```python
# 특정 카테고리의 키워드만 추출
people = extractor.get_keywords_by_category(result, KeywordCategory.PERSON)
places = extractor.get_keywords_by_category(result, KeywordCategory.PLACE)
foods = extractor.get_keywords_by_category(result, KeywordCategory.FOOD)

print([kw.word for kw in people])  # ["딸", "손녀"]
print([kw.word for kw in places])  # ["뒷산"]
print([kw.word for kw in foods])   # ["된장찌개", "김치"]
```

### 3.5 상위 N개 키워드

```python
# 중요도 순으로 상위 5개
top_5 = extractor.get_top_keywords(result, n=5)

for kw in top_5:
    category_kr = extractor.get_category_label_kr(kw.category)
    print(f"{kw.word} ({category_kr}) - {kw.importance:.2f}")
```

---

## 4. 실전 예제

### 4.1 MessageProcessor에서 사용

```python
# core/workflow/message_processor.py

from core.nlp import EmotionDetector, KeywordExtractor

class MessageProcessor:
    def __init__(self):
        self.emotion_detector = EmotionDetector()
        self.keyword_extractor = KeywordExtractor()

    async def process(self, user_id: str, message: str):
        # 1. 감정 분석
        emotion = await self.emotion_detector.detect(message)
        logger.info(f"Emotion: {emotion.primary_emotion} (intensity: {emotion.intensity})")

        # 2. 키워드 추출
        keywords = await self.keyword_extractor.extract(message)
        logger.info(f"Keywords: {[kw.word for kw in keywords.keywords[:5]]}")

        # 3. 메모리 저장 (Episodic Memory)
        await self._store_episodic_memory(
            user_id=user_id,
            message=message,
            emotion=emotion,
            keywords=keywords
        )

        # 4. 응답 생성
        response = await self.generate_response(user_id, message, emotion)

        return response
```

### 4.2 Episodic Memory 저장

```python
# core/memory/episodic_memory.py

async def store_conversation(
    user_id: str,
    message: str,
    emotion: EmotionResult,
    keywords: KeywordExtractionResult
):
    """대화를 episodic memory에 저장"""

    # Qdrant payload
    payload = {
        "user_id": user_id,
        "content": message,
        "category": "conversation",
        "timestamp": datetime.now().isoformat(),
        "confidence": 0.9,
        "metadata": {
            "emotion": emotion.primary_emotion.value,
            "emotion_intensity": emotion.intensity,
            "keywords": [kw.word for kw in keywords.keywords[:10]],
            "main_topic": keywords.main_topic
        }
    }

    # 임베딩 생성
    embedding = await embedder.embed(message)

    # Qdrant에 저장
    await qdrant_client.upsert(
        collection_name="episodic_memory",
        points=[
            {
                "id": generate_id(),
                "vector": embedding,
                "payload": payload
            }
        ]
    )
```

### 4.3 감정 기반 응답 생성

```python
async def generate_empathetic_response(
    message: str,
    emotion: EmotionResult
) -> str:
    """감정에 맞는 공감 응답 생성"""

    emotion_templates = {
        EmotionCategory.JOY: [
            "정말 기쁘셨겠어요! 😊",
            "좋은 일이 있으셨나 봐요!",
            "기분이 좋으시니 저도 행복하네요!"
        ],
        EmotionCategory.SADNESS: [
            "마음이 많이 아프셨겠어요.",
            "힘든 시간이셨겠네요.",
            "곁에서 함께하고 싶네요."
        ],
        EmotionCategory.ANGER: [
            "많이 화가 나셨나 봐요.",
            "속상하셨겠어요.",
            "그럴 수 있어요. 괜찮아요."
        ]
    }

    # 감정에 맞는 템플릿 선택
    templates = emotion_templates.get(
        emotion.primary_emotion,
        ["말씀 감사합니다."]
    )

    import random
    empathy = random.choice(templates)

    return empathy
```

### 4.4 키워드 기반 Fact 추출

```python
async def extract_facts_from_keywords(
    keywords: KeywordExtractionResult,
    message: str
) -> List[Dict]:
    """키워드에서 저장할 사실 추출"""

    facts = []

    # 인물 정보
    people = [kw for kw in keywords.keywords if kw.category == KeywordCategory.PERSON]
    for person in people:
        facts.append({
            "entity": "family_member",
            "value": person.word,
            "context": person.context,
            "confidence": person.importance
        })

    # 음식 선호도
    foods = [kw for kw in keywords.keywords if kw.category == KeywordCategory.FOOD]
    for food in foods:
        facts.append({
            "entity": "food_preference",
            "value": food.word,
            "context": food.context,
            "confidence": food.importance
        })

    return facts
```

---

## 5. 프롬프트 커스터마이징

### 5.1 감정 분석 프롬프트 수정

```python
# config/prompts.py

EMOTION_DETECTION_PROMPT = """
다음 텍스트에서 화자의 감정을 분석하세요.

## 입력
{text}

## 감정 카테고리
... (원하는 대로 수정)
"""
```

### 5.2 키워드 추출 프롬프트 수정

```python
# config/prompts.py

KEYWORD_EXTRACTION_PROMPT = """
다음 텍스트에서 핵심 키워드와 주제를 추출하세요.

## 입력
{text}

## 추출 기준
... (원하는 대로 수정)
"""
```

---

## 6. 성능 최적화

### 6.1 모델 선택

```python
# 빠르고 저렴한 모델 (기본)
llm_service = LLMService(model="gpt-4o-mini")

# 더 정확한 모델
llm_service = LLMService(model="gpt-4o")

# 감정 분석기에 적용
detector = EmotionDetector(llm_service=llm_service)
```

### 6.2 배치 처리

```python
# 여러 텍스트를 동시에 처리 (속도 향상)
texts = ["텍스트1", "텍스트2", "텍스트3"]

# 순차 처리 (느림)
results = [await detector.detect(text) for text in texts]

# 배치 처리 (빠름)
results = await detector.detect_batch(texts)
```

### 6.3 캐싱

```python
from database.redis_client import redis_client
import hashlib

async def detect_emotion_with_cache(text: str):
    """감정 분석 결과 캐싱"""

    # 캐시 키 생성
    text_hash = hashlib.md5(text.encode()).hexdigest()
    cache_key = f"emotion:{text_hash}"

    # 캐시 확인
    cached = await redis_client.get_cache(cache_key)
    if cached:
        return cached

    # 캐시 미스 - 실제 분석
    result = await detector.detect(text)

    # 결과 캐싱 (30분)
    await redis_client.set_cache(cache_key, result.dict(), ttl=1800)

    return result
```

### 6.4 토큰 최적화

```python
# 짧은 텍스트는 max_tokens 줄이기
detector = EmotionDetector()

result = await detector.llm_service.call_json(
    prompt=prompt,
    max_tokens=300,  # 기본 1000에서 300으로 줄임
    temperature=0.3
)
```

---

## 📊 테스트

```bash
# NLP 모듈 테스트
python scripts/test_nlp_modules.py

# 예상 출력:
# ============================================================
# 🔍 Emotion Detection Test
# ============================================================
#
# Test 1: 오늘 딸이 전화해서 정말 기분 좋았어요! 😊
#   ✅ Result: 기쁨 (joy)
#   📊 Intensity: 0.85
#   🔑 Keywords: 기분, 좋았어요
#   💭 Rationale: 텍스트에서 긍정적인 감정 표현이 명확함
#   ✓ Expected: 기쁨 - MATCH!
#
# ...
#
# ✅ All tests passed!
```

---

## ✅ 체크리스트

NLP 모듈 설정 완료 후 확인:

- [ ] OPENAI_API_KEY 설정 (.env)
- [ ] `python scripts/test_nlp_modules.py` 성공
- [ ] 감정 분석 정확도 확인
- [ ] 키워드 추출 정확도 확인
- [ ] MessageProcessor에 통합
- [ ] Episodic Memory 저장 연동

---

**작성일:** 2025-01-15
**작성자:** Memory Garden Team
