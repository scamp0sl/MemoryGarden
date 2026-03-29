# 기억 모듈 사용 가이드

Memory Garden 프로젝트의 Memory (기억) 모듈 사용 가이드입니다.

---

## 📋 목차

1. [개요](#1-개요)
2. [MemoryExtractor](#2-memoryextractor)
3. [MemoryManager](#3-memorymanager)
4. [ContextBuilder](#4-contextbuilder)
5. [4계층 메모리 아키텍처](#5-4계층-메모리-아키텍처)
6. [실전 예제](#6-실전-예제)

---

## 1. 개요

### 모듈 구성

```
core/memory/
├── __init__.py              # 모듈 export
├── memory_extractor.py      # 기억 추출
├── memory_manager.py        # 4계층 메모리 관리
└── context_builder.py       # 컨텍스트 구성
```

### 주요 기능

| 모듈 | 기능 | 입력 | 출력 |
|------|------|------|------|
| **MemoryExtractor** | 대화에서 기억 추출 | 대화 히스토리 | 사실, 일화, 감정 |
| **MemoryManager** | 4계층 CRUD | user_id, 데이터 | 저장/검색 결과 |
| **ContextBuilder** | 관련 기억 검색 | user_id, query | 프롬프트 컨텍스트 |

### 4계층 메모리 시스템

```
Layer 1: Session Memory (Redis, TTL 24h)
 ├─ 현재 대화 세션 컨텍스트 (최근 10턴)
 └─ 오늘의 맥락 참조용

Layer 2: Episodic Memory (Qdrant, 영구)
 ├─ 일화 기억: "2025.02.10 점심에 된장찌개"
 ├─ 감정 기억: "02.09 딸이 전화해서 기분 좋았다"
 └─ 메타데이터: timestamp, category, confidence

Layer 3: Biographical Memory (Qdrant + PostgreSQL)
 ├─ 불변 사실: 이름, 생년월일, 고향, 자녀 이름
 ├─ 반불변 사실: 거주지, 직업, 건강 상태
 ├─ 선호도: 좋아하는 음식, 취미
 └─ 모순 발생 시 버전 관리

Layer 4: Analytical Memory (TimescaleDB)
 ├─ 일별 MCDI 점수 및 하위 지표
 ├─ 주간/월간 트렌드
 └─ 이상 감지 이벤트 로그
```

---

## 2. MemoryExtractor

### 2.1 기본 사용법

```python
from core.memory import MemoryExtractor

# MemoryExtractor 생성
extractor = MemoryExtractor()

# 대화에서 기억 추출
conversation_history = [
    {"role": "user", "content": "오늘 점심에 딸이랑 된장찌개 먹었어요"},
    {"role": "assistant", "content": "딸분과 함께 식사하셨군요!"},
    {"role": "user", "content": "네, 딸 이름은 수진이에요"}
]

result = await extractor.extract(
    conversation_history=conversation_history,
    current_emotion="joy"
)

# 결과 확인
print(result.biographical_facts[0].value)  # "수진"
print(result.episodic_memories[0].content)  # "점심에 된장찌개 먹음"
```

### 2.2 기억 유형

**MemoryType**:
- `EPISODIC`: 일화적 기억 (사건, 경험)
- `BIOGRAPHICAL`: 전기적 사실 (불변/반불변)
- `EMOTIONAL`: 감정 기억
- `PROCEDURAL`: 절차 기억 (습관, 루틴)

**FactType**:
- `IMMUTABLE`: 불변 (이름, 생년월일)
- `SEMI_IMMUTABLE`: 반불변 (거주지, 직업)
- `PREFERENCE`: 선호도 (음식, 취미)
- `TEMPORARY`: 일시적 (오늘 먹은 음식)

**EntityCategory**:
- `PERSON`, `PLACE`, `FOOD`, `EVENT`, `TIME`, `EMOTION`, `ACTIVITY`, `OBJECT`, `HEALTH`

### 2.3 단일 메시지에서 추출

```python
# 한 쌍의 메시지에서 추출
result = await extractor.extract_from_message(
    user_message="고향은 부산이고, 좋아하는 음식은 된장찌개예요",
    assistant_message="부산 출신이시군요! 된장찌개 정말 맛있죠",
    context={"emotion": "neutral"}
)

print(result.biographical_facts)
# [
#   ExtractedFact(entity="hometown", value="부산", ...),
#   ExtractedFact(entity="favorite_food", value="된장찌개", ...)
# ]
```

### 2.4 중요도 점수 계산

```python
# 기억 중요도 계산
memory = result.episodic_memories[0]
importance = extractor.calculate_importance(
    memory=memory,
    recency_weight=0.3,
    emotion_weight=0.3,
    novelty_weight=0.4
)

print(f"Importance: {importance:.3f}")
# Importance: 0.825
```

**중요도 계산 공식**:
```
importance = base * 0.4 + recency * 0.3 + emotion * 0.3 + novelty * 0.4
where:
  base = confidence * importance
  recency = 최신성 (1시간 내: 1.0, 24시간: 0.5, 7일: 0.2)
  emotion = 감정 관련 여부 (1.0 or 0.7)
  novelty = 새로움 (메타데이터에서 추출)
```

### 2.5 응답 구조

```python
class MemoryExtractionResult(BaseModel):
    episodic_memories: List[ExtractedMemory]
    biographical_facts: List[ExtractedFact]
    emotional_memories: List[ExtractedMemory]
    key_entities: List[Dict[str, Any]]
    summary: str

class ExtractedMemory(BaseModel):
    memory_type: MemoryType
    content: str
    category: EntityCategory
    confidence: float  # 0.0~1.0
    importance: float  # 0.0~1.0
    timestamp: str
    metadata: Dict[str, Any]

class ExtractedFact(BaseModel):
    entity: str
    value: str
    category: EntityCategory
    fact_type: FactType
    confidence: float  # 0.0~1.0
    context: str
    timestamp: str
```

---

## 3. MemoryManager

### 3.1 기본 사용법

```python
from core.memory import MemoryManager

# MemoryManager 생성
manager = MemoryManager()

# 4계층에 저장
result = await manager.store_all(
    user_id="user123",
    message="오늘 점심에 딸 수진이랑 된장찌개 먹었어요",
    response="수진 씨와 함께 식사하셨군요!",
    analysis={
        "emotion": "joy",
        "mcdi_score": 78.5
    }
)

print(result)
# {
#     "session_stored": True,
#     "episodic_stored": 2,
#     "biographical_stored": 1,
#     "analytical_stored": True,
#     "extraction_summary": "전기적 사실 1개 추출, 일화 기억 2개 추출"
# }
```

### 3.2 4계층 검색

```python
# 4계층에서 검색 (병렬)
memories = await manager.retrieve_all(
    user_id="user123",
    query="점심",
    limit=10
)

print(memories["session"])        # 세션 데이터
print(memories["episodic"])       # 일화 기억 리스트
print(memories["biographical"])   # 전기적 사실 딕셔너리
print(memories["analytical"])     # 분석 데이터
```

### 3.3 키워드 검색

```python
# 키워드로 검색
results = await manager.search_memories_by_keyword(
    user_id="user123",
    keyword="딸",
    limit=5
)

for memory in results:
    print(f"{memory['timestamp']}: {memory['content']}")
```

### 3.4 시간 범위 검색

```python
from datetime import datetime, timedelta

# 최근 7일 기억
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

results = await manager.search_memories_by_time_range(
    user_id="user123",
    start_date=start_date,
    end_date=end_date
)

print(f"Found {len(results)} memories in last 7 days")
```

### 3.5 감정 기반 검색

```python
# 특정 감정의 기억만 검색
joy_memories = await manager.search_memories_by_emotion(
    user_id="user123",
    emotion="joy",
    limit=10
)

sadness_memories = await manager.search_memories_by_emotion(
    user_id="user123",
    emotion="sadness",
    limit=10
)
```

### 3.6 최근 기억 조회

```python
# 최근 7일 기억 (시간 역순)
recent = await manager.get_recent_memories(
    user_id="user123",
    days=7,
    limit=20
)

for memory in recent:
    print(f"{memory['timestamp']}: {memory['content']}")
```

---

## 4. ContextBuilder

### 4.1 기본 사용법

```python
from core.memory import ContextBuilder

# ContextBuilder 생성
builder = ContextBuilder()

# 컨텍스트 구성
context = await builder.build_context(
    user_id="user123",
    query="딸",
    current_emotion="joy",
    max_memories=5
)

print(context["relevant_memories"])    # 관련 기억 리스트
print(context["biographical_facts"])   # 전기적 사실
print(context["formatted_context"])    # 프롬프트용 문자열
```

### 4.2 프롬프트 컨텍스트 생성

```python
# 프롬프트에 주입할 컨텍스트 문자열
context_str = await builder.build_prompt_context(
    user_id="user123",
    query="점심"
)

print(context_str)
# ## 사용자 정보
# - 딸 이름: 수진
# - 고향: 부산
#
# ## 관련 기억
# - 2025-02-09: 점심에 된장찌개 먹음
# - 2025-02-08: 딸과 함께 저녁 식사
```

### 4.3 대화 히스토리 컨텍스트

```python
# ChatCompletion 형식 대화 히스토리
history = await builder.get_conversation_context(
    user_id="user123",
    last_n_turns=5
)

print(history)
# [
#   {"role": "user", "content": "..."},
#   {"role": "assistant", "content": "..."},
#   ...
# ]
```

### 4.4 강화된 컨텍스트 구성

```python
# 메시지 기반 키워드 추출 + 검색
enriched = await builder.build_enriched_context(
    user_id="user123",
    user_message="오늘 점심에 딸이랑 같이 밥 먹었어요",
    current_emotion="joy"
)

print(enriched["query"])              # 자동 추출된 키워드
print(enriched["relevant_memories"])  # 관련 기억
```

### 4.5 관련성 점수 계산

**내부적으로 사용되는 관련성 점수 공식**:

```
relevance = base * 0.3 + recency * 0.4 + relevance * 0.6 + emotion_bonus

where:
  base = confidence * importance
  recency = 최신성 점수 (지수 감쇠)
  relevance = 키워드 매칭 점수
  emotion_bonus = 감정 일치 시 0.2
```

---

## 5. 4계층 메모리 아키텍처

### 5.1 Layer 1: Session Memory (Redis)

**목적**: 현재 대화 세션 관리

**TTL**: 24시간

**저장 내용**:
- 최근 10턴 대화
- 세션 메타데이터

**사용 예**:
```python
# 자동 관리 (MemoryManager가 처리)
await manager.store_all(...)
```

### 5.2 Layer 2: Episodic Memory (Qdrant)

**목적**: 일화 기억 벡터 저장

**영구 보관**

**저장 내용**:
- 일화적 사건
- 감정 기억
- 임베딩 벡터

**사용 예**:
```python
# 자동 저장 (추출 → 임베딩 → Qdrant)
result = await manager.store_all(...)
```

**검색**:
```python
# 벡터 유사도 검색
memories = await manager.retrieve_all(
    user_id="user123",
    query="점심"  # 벡터 검색
)
```

### 5.3 Layer 3: Biographical Memory (Qdrant + PostgreSQL)

**목적**: 전기적 사실 관리

**영구 보관**

**저장 내용**:
- 불변 사실 (이름, 생년월일)
- 반불변 사실 (거주지, 직업)
- 선호도 (음식, 취미)

**모순 관리**:
```python
# 모순 발생 시 버전 관리 (overwrite X, append O)
# 예: 거주지 변경
# - v1: "서울"
# - v2: "부산" (새로운 버전 추가)
```

### 5.4 Layer 4: Analytical Memory (TimescaleDB)

**목적**: 시계열 분석 데이터

**보관 기간**: 90일 (설정 가능)

**저장 내용**:
- 일별 MCDI 점수
- 6개 하위 지표 (LR, SD, NC, TO, ER, RT)
- 이상 감지 이벤트

**시계열 쿼리**:
```python
# 최근 30일 트렌드
analytical = await manager._retrieve_analytical_data(
    user_id="user123",
    days=30
)
```

---

## 6. 실전 예제

### 6.1 MessageProcessor 통합

```python
# core/workflow/message_processor.py

from core.memory import MemoryManager, ContextBuilder

class MessageProcessor:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.context_builder = ContextBuilder(self.memory_manager)

    async def process(self, user_id: str, message: str):
        # 1. 컨텍스트 검색 (관련 기억)
        context = await self.context_builder.build_enriched_context(
            user_id=user_id,
            user_message=message
        )

        # 2. AI 응답 생성 (컨텍스트 주입)
        response = await self.dialogue_manager.generate_response(
            user_id=user_id,
            user_message=message,
            context=context["formatted_context"]
        )

        # 3. 분석 (감정, MCDI 등)
        analysis = await self.analyzer.analyze(message, context)

        # 4. 메모리 저장 (4계층)
        await self.memory_manager.store_all(
            user_id=user_id,
            message=message,
            response=response,
            analysis=analysis
        )

        return response
```

### 6.2 관련 기억 기반 응답 생성

```python
async def generate_contextual_response(
    user_id: str,
    message: str
):
    """관련 기억을 활용한 응답 생성"""
    builder = ContextBuilder()

    # 관련 기억 검색
    context = await builder.build_context(
        user_id=user_id,
        query=message,
        max_memories=3
    )

    # 프롬프트 구성
    prompt = f"""
{context['formatted_context']}

## 현재 대화
사용자: {message}

위 기억을 참고하여 자연스럽게 응답하세요.
"""

    # LLM 호출
    response = await llm_service.call(prompt)
    return response
```

### 6.3 모순 탐지

```python
async def detect_contradictions(
    user_id: str,
    new_statement: str
):
    """전기적 사실 모순 탐지"""
    manager = MemoryManager()

    # 기존 전기적 사실 조회
    memories = await manager.retrieve_all(user_id)
    biographical = memories["biographical"]

    # 새 진술에서 사실 추출
    extractor = MemoryExtractor()
    result = await extractor.extract_from_message(
        user_message=new_statement,
        assistant_message="",
        context={}
    )

    # 모순 확인
    contradictions = []
    for new_fact in result.biographical_facts:
        entity = new_fact.entity
        if entity in biographical:
            old_value = biographical[entity].get("value")
            new_value = new_fact.value

            if old_value != new_value:
                contradictions.append({
                    "entity": entity,
                    "old_value": old_value,
                    "new_value": new_value,
                    "confidence": new_fact.confidence
                })

    return contradictions
```

### 6.4 감정 기반 기억 회상

```python
async def recall_emotional_memories(
    user_id: str,
    target_emotion: str,
    days: int = 30
):
    """특정 감정의 기억 회상"""
    manager = MemoryManager()

    # 감정 기반 검색
    memories = await manager.search_memories_by_emotion(
        user_id=user_id,
        emotion=target_emotion,
        limit=10
    )

    # 최근 N일 필터링
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    recent_emotional = [
        mem for mem in memories
        if start_date <= datetime.fromisoformat(mem["timestamp"]) <= end_date
    ]

    return recent_emotional
```

---

## 📊 테스트

```bash
# Memory 모듈 테스트
python scripts/test_memory_modules.py

# 예상 출력:
# ============================================================
# 🔍 MemoryExtractor Test
# ============================================================
#
# 1️⃣ Extract from Conversation
#   ✅ Extraction completed
#   - Episodic memories: 2
#   - Biographical facts: 2
#
# ...
#
# ✅ All tests passed!
```

---

## ✅ 체크리스트

Memory 모듈 설정 완료 후 확인:

- [ ] OPENAI_API_KEY 설정 (.env)
- [ ] REDIS_URL 설정 (.env)
- [ ] `python scripts/test_memory_modules.py` 성공
- [ ] 기억 추출 정확도 확인
- [ ] 4계층 저장/검색 동작 확인
- [ ] 컨텍스트 구성 품질 확인
- [ ] MessageProcessor에 통합
- [ ] Qdrant 연동 (TODO)
- [ ] PostgreSQL 연동 (TODO)
- [ ] TimescaleDB 연동 (TODO)

---

**작성일:** 2025-02-10
**작성자:** Memory Garden Team
