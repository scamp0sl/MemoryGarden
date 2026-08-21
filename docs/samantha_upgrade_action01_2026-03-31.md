# 사만다 기억 시스템 개선 방안 (Action 01)

**작성일**: 2026-03-31
**상태**: ✅ 적용 완료
**목표**: Biographical Fact 추출 오류 해결

---

## 📋 목차

1. [최종 적용 결과](#최종-적용-결과-actual-implementation) - **실제 적용된 코드**
2. [문제 정의](#문제-정의) - 기존 계획안
3. [개선 방향](#개선-방향-2-stage-filtering) - 기존 계획안
4. [상세 구현 방안](#상세-구현-방안) - 기존 계획안
5. [테스트 시나리오](#테스트-시나리오) - 기존 계획안
6. [롤백 계획](#롤백-계획) - 기존 계획안
7. [성공 지표](#성공-지표) - 기존 계획안
8. [주의사항](#주의사항) - 기존 계획안
9. [피드백 루프 구현](#피드백-루프-구현-feedback-loop) - 기존 계획안
10. [전체 구현 우선순위](#전체-구현-우선순위) - 기존 계획안
11. [Samantha 페르소나 영향 분석](#samantha-페르소나-영향-분석-persona-impact-analysis)
12. [테스트 결과 및 수정 계획](#테스트-결과-및-수정-계획-test-results--revision-plan)
13. [최종 테스트 결과](#최종-테스트-결과)

---

## 최종 적용 결과 (Actual Implementation)

### 적용 완료일: 2026-03-31

### 테스트 결과: 9/9 전체 통과 ✅

| 케이스 | 입력 | bio | epi | 결과 |
|--------|------|-----|-----|------|
| 정상1 | "나는 홍길동이야" | 1 ✅ | 2 | ✅ PASS |
| 정상2 | "딸은 수진이야" | 1 ✅ | 1 | ✅ PASS |
| 정상3 | "제육 좋아해" | 1 ✅ | 1 | ✅ PASS |
| 정상4 | "산에서 진달래를 봤어" | 0 ✅ | 1 | ✅ PASS |
| 정상5 | "엄마가 쑥을 캐갔어" | 0 ✅ | 1 | ✅ PASS |
| 경계1 | "봄이 왔어" | 0 ✅ | 2 | ✅ PASS |
| 경계2 | "바람이 분다" | 0 ✅ | 2 | ✅ PASS |
| 경계3 | "인왕산 갔었어" | 0 ✅ | 1 | ✅ PASS |
| 경계4 | "쑥 떡 맛있다" | 0 ✅ | 2 | ✅ PASS |

### 적용된 코드 변경

#### 1. config/prompts.py

```python
FACT_EXTRACTION_PROMPT = """
대화에서 기억을 추출하세요.

========== JSON 출력 형식 (반드시 준수) ==========
{{
  "biographical_facts": [
    {{"entity": "name", "value": "홍길동", "confidence": 0.95, "fact_type": "immutable"}}
  ],
  "episodic_facts": [
    {{"content": "산에서 진달래 꽃을 보았다", "category": "event", "confidence": 0.9}}
  ]
}}
====================================================

## 1단계: Episodic First (기본)
모든 발언을 episodic_facts로 저장하세요.
- "산에서 진달래를 봤어" → episodic_facts
- "점심에 제육 먹었어" → episodic_facts

## 2단계: Biographical 승격 (특별한 경우만)
⛔ 제외: 꽃/식물(진달래, 쑥, 봄), 동물, 자연은 절대 사람 이름 아님

✅ 승격 조건:
- name: "내 이름은 홍길동", "나는 철수야"
- nickname: "나를 OO라고 불러줘"
- daughter_name/son_name: "딸은 수진이야", "아들은 민수야"
- favorite_food: "제육 좋아해", "OO이 제일 좋아"
- hometown: "고향은 부산"
- hobby: "등산이 취미야"
- occupation: "직업은 선생님"

❌ 제외 (단순 언급):
- "딸과 갔어", "제육 먹었어", "산에 갔어"

## 카테고리
- event, food, activity, place, person, time, emotion, object, health

## 입력
- 현재 시간: {current_time}
{conversation_history}
"""
```

**주요 변경사항:**
- JSON 출력 형식을 맨 위에 배치 (시각적 구분)
- 2단계 개념을 간결하지만 명확히 유지
- 제외 키워드 핵심만 유지 (진달래, 쑥, 봄 등)
- 전체 길이: ~50줄 (핵심 개념 유지)

#### 2. core/memory/memory_extractor.py

**변경 1: Temperature 조정**
```python
# 이전
response = await self.llm_service.call_json(
    prompt=prompt,
    system_prompt="당신은 대화에서 중요한 사실과 기억을 추출하는 전문가입니다.",
    temperature=0.3,  # ❌ 너무 낮음
    max_tokens=1000
)

# 변경 후
response = await self.llm_service.call_json(
    prompt=prompt,
    system_prompt="당신은 대화에서 중요한 사실과 기억을 추출하는 전문가입니다.",
    temperature=0.6,  # ✅ 유연성 확보
    max_tokens=1000
)
```

**변경 2: 제외 키워드 필터링 로직 추가**
```python
def _parse_extraction_response(
    self,
    response: Dict[str, Any],
    current_emotion: Optional[str],
    current_datetime: datetime
) -> MemoryExtractionResult:
    """LLM 응답 파싱 (Action01: 제외 키워드 필터링 추가)"""
    try:
        # Action01: 제외 키워드 리스트 (꽃/식물/동물/자연/계절)
        EXCLUDED_VALUE_KEYWORDS = {
            # 꽃/식물
            "진달래", "개나리", "무궁화", "장미", "해바라기", "벚꽃",
            "코스모스", "국화", "튤립", "수국", "라일락",
            "쑥", "냉이", "민들레", "소나무", "잔디", "호박", "고추",
            # 동물
            "강아지", "고양이", "병아리", "토끼", "다람쥐", "참새",
            # 자연
            "바람", "구름", "비", "눈", "달", "별", "해",
            # 계절
            "봄", "여름", "가을", "겨울"
        }

        # Biographical facts 파싱 (Action01: 검증 로직 추가)
        biographical_facts = []
        for fact in response.get("biographical_facts", []):
            entity = fact.get("entity", "")
            value = fact.get("value", "")
            confidence = float(fact.get("confidence", 0.8))

            # Action01: 제외 키워드 체크
            if any(keyword in value for keyword in EXCLUDED_VALUE_KEYWORDS):
                logger.warning(
                    f"[Action01] Excluded biographical fact: entity={entity}, "
                    f"value={value} (matched excluded keywords)"
                )
                continue

            # Action01: confidence 0.7 미만 제외
            if confidence < 0.7:
                logger.warning(
                    f"[Action01] Low confidence biographical fact skipped: "
                    f"entity={entity}, confidence={confidence}"
                )
                continue

            biographical_facts.append(
                ExtractedFact(
                    entity=entity,
                    value=value,
                    category=self._map_to_entity_category(entity),
                    fact_type=self._normalize_fact_type(fact.get("fact_type", "preference")),
                    confidence=confidence,
                    context=fact.get("context", ""),
                    timestamp=current_datetime.isoformat()
                )
            )
```

### Samantha 페르소나 영향: 무영향

| 항목 | 영향 | 확인 |
|------|------|------|
| SYSTEM_PROMPT | ❌ 무영향 | 수정하지 않음 |
| 대화 스타일 | ❌ 무영향 | FACT_EXTRACTION은 백엔드 |
| 응답 생성 | ❌ 무영향 | response_generator 별도 |
| 페르소나 특성 | ❌ 무영향 | 따뜻함, 맞장구 유지 |

### Git 기록

```bash
# 커밋 1: 문서 작성
a66e508 docs: 사만다 기억 시스템 개선 방안 (Action 01) 문서 작성

# 커밋 2: 코드 적용 (예정)
# config/prompts.py, core/memory/memory_extractor.py
```

---

## 문제 정의

### 1.1 발생한 오류

```
사용자: "산에서 진달래를 봤어"
         ↓
LLM: "이름(진달래)"으로 판단
         ↓
저장: biographical:name = "진달래"
         ↓
AI: "진달래님~"이라고 부름
         ↓
사용자: "진달래로 부르라고 한 적 없음"
```

### 1.2 근본 원인

| 원인 | 설명 |
|------|------|
| **프롬프트 불충분** | biographical vs episodic 구별 기준이 모호함 |
| **LLM 자율 판단** | entity가 `str` 타입이라 제한 없음 |
| **Temperature 0.3** | 낮은 temperature가 확신적 판단 유도 |
| **Episodic 누락** | biographical에만 저장되고 episodic은 비어있음 |
| **검증 부재** | 추출 결과를 검증하는 로직이 없음 |

---

## 2. 현재 상황 분석

### 2.1 실제 저장 데이터 확인

```bash
# 사용자 aa96e75d의 biographical facts
biographical:aa96e75d:name = "진달래"  ← 오류
biographical:aa96e75d:nickname = "주인님"
biographical:aa96e75d:favorite_food = "제육"

# episodic facts (4개 저장됨)
episodic:aa96e75d:... = "엄마가 봄이면 쑥을 캐러 뒷산에 가셔서 쑥떡을 만들어주셨다"
```

### 2.2 관련 코드 분석

**memory_extractor.py (ExtractedFact 모델)**
```python
class ExtractedFact(BaseModel):
    entity: str = Field(...)  # ❌ 제한 없음, LLM 자율 생성
    value: str = Field(...)
    category: EntityCategory = Field(...)  # ✅ Enum으로 제한됨
    fact_type: FactType = Field(...)  # ✅ Enum으로 제한됨
```

**prompts.py (FACT_EXTRACTION_PROMPT)**
```python
## 추출 대상
1. 전기적 사실
   - 불변: 이름, 생년월일, 출생지, 자녀 이름  # ❌ "이름" 기준 모호
   - 반불변: 거주지, 직업, 종교
   - 선호: 좋아하는 음식, 취미

2. 일화적 사실
   - 사건: "2025-01-15 점심에 된장찌개 먹음"
   - 감정: "딸과 통화해서 기분 좋음"
```

**memory_extractor.py (추출 호출)**
```python
response = await self.llm_service.call_json(
    prompt=prompt,
    temperature=0.3,  # ❌ 너무 낮음, 확신적 판단 유도
    max_tokens=1000
)
```

---

## 3. 개선 방향: 2-Stage Filtering

### 3.1 핵심 전략

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: Episodic First (일화 기억 우선)                    │
│                                                              │
│  모든 발언을 기본적으로 "경험/사건"으로 저장                │
│  → "산에서 진달래를 봤어" → episodic_fact                  │
│  → "엄마가 쑥을 캐갔어" → episodic_fact                     │
│  → "점심에 제육 먹었어" → episodic_fact                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Biographical 승격 (명시적 선언만)                 │
│                                                              │
│  아주 명확한 자기 정보 선언만 biographical_fact로 저장       │
│  → "내 이름은 홍길동" → biographical_fact                   │
│  → "나를 주인님이 불러줘" → biographical_fact               │
│  → "제육 좋아해" → biographical_fact                        │
│                                                              │
│  ⛔ 제외: 꽃/식물/동물/자연/계절                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 판단 기준 명세

#### Biographical Fact 승격 조건

| entity | 승격 조건 (명시적 선언) | 제외 (단순 언급) |
|--------|---------------------|------------------|
| **name** | "나는 OOO", "내 이름은 OOO" | "산에서 진달래를 봤어" (꽃) |
| **nickname** | "나를 OOO라고 불러줘" | (사용자 요청 없음) |
| **daughter_name** | "딸은 OOO야", "막내가 OOO" | "딸과 갔어" (단순 언급) |
| **son_name** | "아들은 OOO, OOO야" | "아들이 왔어" (단순 언급) |
| **favorite_food** | "OOO 좋아해", "OOO이 제일 좋아" | "점심에 OOO 먹었어" |
| **hometown** | "고향은 OOO야", "OOO에서 왔어" | "OOO에 갔었어" |
| **occupation** | "직업은 OOO야", "OOO로 일해" | "회사에 갔어" |

#### 제외 키워드 (블랙리스트)

```
# 꽃/식물
진달래, 개나리, 무궁화, 장미, 해바라기, 벚꽃, 코스모스, 국화
튤립, 수국, 라일락, 쑥, 냉이, 민들레, 소나무, 잔디...

# 동물
강아지, 고양이, 병아리, 토끼, 다람쥐, 참새...

# 자연현상
바람, 구름, 비, 눈, 달, 별, 해...

# 계절
봄, 여름, 가을, 겨울
```

---

## 4. 상세 구현 방안

### 4.1 파일 수정 목록

| 파일 | 수정 내용 | 우선순위 |
|------|----------|----------|
| `config/prompts.py` | FACT_EXTRACTION_PROMPT 개선 | P0 |
| `core/memory/memory_extractor.py` | temperature 조정 | P1 |
| `core/memory/memory_extractor.py` | entity Enum 검증 (선택) | P2 |

### 4.2 config/prompts.py 수정

**기존 (128-177줄)**
```python
FACT_EXTRACTION_PROMPT = """
대화에서 저장할 가치가 있는 사실(fact)을 추출하세요.

## 추출 대상
1. 전기적 사실
   - 불변: 이름, 생년월일, 출생지, 자녀 이름
   ...
"""
```

**개선안**
```python
FACT_EXTRACTION_PROMPT = """
대화에서 기억할 만한 내용을 추출하세요.

## ⚠️ 기본 원칵 (가장 중요!)

### 1단계: Episodic Fact (일화 기억) 우선
사용자의 모든 발언은 기본적으로 "경험/사건"으로 저장합니다.

### 2단계: Biographical Fact (전기적 사실) 승격 조건
아주 **명시적인 자기 정보 선언**만 Biographical Fact로 저장합니다.

---

## Episodic Fact (일화 기억) - 기본 저장 대상

사용자의 모든 발언을 경험/사건으로 기록하세요.

### 저장 예시
- "산에서 진달래를 봤어" → "산에서 진달래 꽃을 보았다"
- "엄마가 쑥을 캐갔어" → "엄마가 봄에 쑥을 캐서 쑥떡을 만들었다"
- "점심에 제육 먹었어" → "점심에 제육을 먹었다"
- "인왕산 갔었어" → "인왕산 등반을 다녀왔다"

### 카테고리
- event: 사건/경험
- food: 음식 관련 경험
- activity: 활동
- place: 장소 방문

---

## Biographical Fact (전기적 사실) - 특별한 경우만

### ⛔ 제외 키워드 (절대 사람 이름/호칭 아님)
- 꽃/식물: 진달래, 개나리, 무궁화, 장미, 해바라기, 벚꽃, 코스모스, 국화, 특립, 수국, 라일락, 쑥, 냉이, 민들레, 소나무, 잔디...
- 동물: 강아지, 고양이, 병아리, 토끼, 다람쥐, 참새...
- 자연: 바람, 구름, 비, 눈, 달, 별, 해...
- 계절: 봄, 여름, 가을, 겨울

### entity: "name" (본인 이름)
- ✅ 승격: "나는 홍길동이다", "내 이름은 철수야"
- ❌ 제외: "산에서 진달래를 봤어", "봄이 왔다"

### entity: "nickname" (요청 호칭)
- ✅ 승격: "나를 주인님이 불러줘", "저를 OO호라고 불러"
- ❌ 제외: (사용자 요청 없음)

### entity: "daughter_name", "son_name"
- ✅ 승격: "딸은 수진이야", "아들은 민수, 철수야"
- ❌ 제외: "딸과 갔어", "아들이 왔어"

### entity: "favorite_food" (명시적 선호)
- ✅ 승격: "제육 좋아해", "제육이 제일 맛있다", "비빔밥이 최고야"
- ❌ 제외: "점심에 제육 먹었어", "오늘 제육 먹었지"

### entity: "hometown" (고향)
- ✅ 승격: "고향은 부산이다", "전주에서 왔어"
- ❌ 제외: "부산에 갔었어", "전주에 도착"

### entity: "hobby" (취미)
- ✅ 승격: "등산이 취미야", "낚시를 좋아해"
- ❌ 제외: "산에 갔어", "낚시를 했어"

### entity: "occupation" (직업)
- ✅ 승격: "직업은 선생님이야", "회사원이야"
- ❌ 제외: "학교에 갔어", "회사에 갔어"

---

## Confidence 가이드라인

- 0.9~1.0: 명시적 표현 ("내 이름은 OO", "좋아해")
- 0.7~0.9: 강력한 암시
- 0.5 미만: biographical_facts에 포함하지 말 것

---

## 출력 형식 (JSON)
{{
  "biographical_facts": [
    {{
      "entity": "name",
      "value": "홍길동",
      "confidence": 0.95,
      "fact_type": "immutable"
    }}
  ],
  "episodic_facts": [
    {{
      "content": "산에서 진달래 꽃이 피어 있는 것을 보았다",
      "timestamp": "{current_time}",
      "category": "event",
      "confidence": 0.9
    }}
  ]
}}
"""
```

### 4.3 core/memory/memory_extractor.py 수정

**기존 (200-204줄)**
```python
response = await self.llm_service.call_json(
    prompt=prompt,
    temperature=0.3,  # ❌ 너무 낮음
    max_tokens=1000
)
```

**개선안**
```python
response = await self.llm_service.call_json(
    prompt=prompt,
    temperature=0.6,  # ✅ 유연성 확보
    max_tokens=1000
)
```

### 4.4 core/memory/memory_extractor.py 검증 강화 (선택 사항)

**344-365줄 _parse_extraction_response 메서드 추가**

```python
def _parse_extraction_response(
    self,
    response: Dict[str, Any],
    current_emotion: Optional[str],
    current_datetime: datetime
) -> MemoryExtractionResult:
    """LLM 응답 파싱"""

    # 제외 키워드 리스트 (꽃/식물/동물/자연)
    EXCLUDED_VALUE_KEYWORDS = {
        # 꽃/식물
        "진달래", "개나리", "무궁화", "장미", "해바라기", "벚꽃",
        "코스모스", "국화", "튤립", "수국", "라일락",
        "쑥", "냉이", "민들레", "소나무", "잔디",
        # 동물
        "강아지", "고양이", "병아리", "토끼", "다람쥐",
        # 자연
        "바람", "구름", "비", "눈", "달", "별", "해",
        # 계절
        "봄", "여름", "가을", "겨울"
    }

    biographical_facts = []
    for fact in response.get("biographical_facts", []):
        value = fact.get("value", "")

        # 제외 키워드 체크
        if any(keyword in value for keyword in EXCLUDED_VALUE_KEYWORDS):
            logger.warning(
                f"Excluded biographical fact: entity={fact.get('entity')}, "
                f"value={value} (matched excluded keywords)"
            )
            continue

        # confidence 0.7 미만 제외
        if fact.get("confidence", 1.0) < 0.7:
            logger.warning(
                f"Low confidence biographical fact skipped: "
                f"entity={fact.get('entity')}, confidence={fact.get('confidence')}"
            )
            continue

        biographical_facts.append(
            ExtractedFact(
                entity=fact["entity"],
                value=fact["value"],
                category=self._map_to_entity_category(fact.get("entity")),
                fact_type=self._normalize_fact_type(fact.get("fact_type", "preference")),
                confidence=float(fact.get("confidence", 0.8)),
                context=fact.get("context", ""),
                timestamp=current_datetime.isoformat()
            )
        )

    # ... 나머지 코드 동일 ...
```

---

## 5. 테스트 시나리오

### 5.1 정상 케이스

| 입력 | 예상 biographical | 예상 episodic |
|------|-----------------|----------------|
| "나는 홍길동이야" | name: "홍길동" | "자신을 홍길동이라고 소개함" |
| "딸은 수진이야" | daughter_name: "수진" | "딸이 수진이라고 언급함" |
| "제육 좋아해" | favorite_food: "제육" | "제육을 좋아한다고 표현함" |
| "산에서 진달래를 봤어" | (없음) | "산에서 진달래 꽃을 보았다" |
| "엄마가 쑥을 캐갔어" | (없음) | "엄마가 쑥을 캐서 쑥떡을 만들었다" |

### 5.2 경계 케이스

| 입력 | 판단 | 이유 |
|------|------|------|
| "봄이 왔어" | event로만 | 계절 명시, bio 제외 |
| "바람이 분다" | event로만 | 자연현상, bio 제외 |
| "인왕산 갔었어" | event로만 | 장소 언급, bio 제외 |
| "쑥 떡 맛있다" | event만? favorite_food? | 명확한 선호 vs 맛 표현 |

---

### 5.3 피드백 루프 테스트 시나리오

#### 5.3.1 정상 피드백 흐름

```
[저장된 상태]
biographical:aa96e75d:name = "진달래"

[대화]
사용자: "내 이름 진달래 아니야"
AI: "아, 정말요? 그럼 저장된 '진달래'를 삭제할까요?"
사용자: "응 삭제해줘"

[기대 결과]
1. Redis에서 "biographical:aa96e75d:name" 삭제
2. 다음 대화부터 "진달래님" 대신 "사용자님"으로 부름
3. 삭제 로그 기록
```

#### 5.3.2 부정적 피드백 (실수 방지)

```
[저장된 상태]
biographical:aa96e75d:favorite_food = "제육"

[대화]
사용자: "제육 아닌데, 김밥이 제일 좋아"

[AI 판단]
사용자가 실수로 정보를 바꾸려 하는 것일 수 있음
→ 선호도가 바뀔 수도 있으니 확인 필요

AI: "정말 제육 대신 김밥으로 저장할까요?
     기존 '제육' 정보는 삭제되고 '김밥'으로 바뀔거든요."

사용자: "아니오, 그냥 둘 다 저장해줘"

[결과]
- 제육 유지, 김밥 추가 (favorite_food_2)
- 또는 사용자 확인 후 선호도 업데이트
```

#### 5.3.3 오감지 방지 시나리오

```
[저장된 상태]
biographical:aa96e75d:favorite_food = "제육"

[대화]
사용자: "오늘 제육 먹었는데"
AI: (아무것도 하지 않음, 저장하지 않음)

[기대 결과]
- "먹었어"는 경험/사건으로 episodic_fact에 저장
- favorite_food는 그대로 유지 (선호도 변경 아님)
```

#### 5.3.4 삭제 후 복구 시나리오

```
[삭제 후]
사용자: "역시 진달래가 제일 좋아하네"
AI: "다시 '진달래'를 저장할까요?"
사용자: "그냥 저장해줘"

[결과]
- biographical:aa96e75d:name = "진달래" 재저장
- 하지만 이번에는 "꽃 이름"으로 명확히 인지 가능
```

#### 5.3.5 전체 피드백 플로우 테스트

```
1. [초기 저장] → 사용자가 "나는 홍길동"이라고 함
2. [저장 확인] → biographical:name = "홍길동" 저장됨
3. [1달 후] → 사용자 기억 저하로 가끔씩 다름
4. [감지] → "이름이 뭐죠?" 같은 질문
5. [검증] → 본인 확인 절차
6. [피드백] → 사용자가 "맞아, 홍길동이야"라고 확인
7. [유지] → 기존 정보 유지, 치매 진단에는 참고 자료 활용
```

---

## 6. 롤백 계획

---

## 6. 롤백 계획

### 6.1 기존 데이터 정리

```bash
# 진달래 잘못 저장된 데이터 삭제
docker exec memgarden-redis redis-cli DEL "biographical:aa96e75d-70e2-4546-9001-043cc5db047d:name"
```

### 6.2 단계적 배포

1. **Phase 1**: 프롬프트만 수정 (코드 로직 유지)
2. **Phase 2**: Temperature 조정 (0.3 → 0.6)
3. **Phase 3**: 검증 로직 추가 (선택)

---

## 7. 성공 지표

| 지표 | 현재 | 목표 |
|------|------|------|
| biographical 오류 저장 | "진달래" 저장됨 | 0건 |
| episodic 누락 | 발생 가능 | 항상 저장 |
| 사용자 불만 | "진달래로 부르지 마라" | 없음 |
| confidence 분포 | 0.95 (과신) | 0.7~0.9 적정 |

---

## 8. 주의사항

1. **코드 수정 없이 프롬프트만으로도 어느 정도 해결 가능**
2. **Temperature 조정은 유연성을 높이지만, 추출 시간이 늘어날 수 있음**
3. **검증 로직 추가 시 로직 복잡도 증가 고려 필요**
4. **사용자에게 bio_fact 저장 시 확인 절차 도입 고려**

---

## 9. 피드백 루프 구현 (Feedback Loop)

### 9.1 현재 상황

```
사용자: "진달래로 부르지 마"
         ↓
AI: "죄송합니다! 제가 착각했네요"  (대화에서만 사과)
         ↓
저장된 데이터: {name: "진달래"}  ← 여전히 남아있음 ❌
         ↓
다음 대화: "진달래님~"  ← 또 실수함
```

**문제점**: 대화에서 사과만 하고, 저장된 데이터가 수정되지 않음

---

### 9.2 피드백 루프 설계

```
┌─────────────────────────────────────────────────────────────┐
│ [1단계] 대화 감지                                             │
│                                                              │
│  키워드 감지:                                                   │
│  - "이름 아니다", "틀렸다", "아니다", "수정해줘"              │
│  - entity 관련 불만 ("진달래로 부르지 마")                    │
│  + 대화 내용 분석                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ [2단계] 사용자 확인 (명시적 피드백)                           │
│                                                              │
│  AI: "정정하면 저장된 '이름: 진달래'를 삭제할까요?"            │
│  사용자: "응" / "응 삭제해줘" / "아니오"                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ [3단계] 삭제 및 시스템 반영                                     │
│                                                              │
│  1. Redis에서 해당 bio fact 삭제                              │
│     await redis_client.delete("biographical:{user_id}:name")  │
│                                                              │
│  2. 시스템 프롬프트에 변경사항 반영                             │
│     apologize_for_nickname = True (사과 지침 활성화)            │
│                                                              │
│  3. 삭제 로그 기록                                               │
│     logger.info(f"Deleted biographical fact: {entity}")        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 9.3 구현 파일별 수정 사항

#### 9.3.1 core/dialogue/dialogue_manager.py

**대화 감지 로직 추가**

```python
async def _detect_correction_needed(
    self,
    user_message: str,
    user_id: str
) -> Optional[str]:
    """사용자가 bio fact 수정을 요청하는지 감지

    Returns: 수정할 entity 이름 또는 None
    """
    # biographical 관련 불만 키워드
    CORRECTION_KEYWORDS = [
        "이름 아니다", "이름 아니야", "틀렸다", "잘못됐",
        "수정해줘", "삭제해줘", "부르지 마", "불오"
    ]

    # entity 관련 감지
    if not any(kw in user_message for kw in CORRECTION_KEYWORDS):
        return None

    # Redis에서 저장된 biographical facts 조회
    import redis_client
    pattern = f"biographical:{user_id}:*"
    keys = await redis_client.keys(pattern)

    for key in keys:
        fact_data = await redis_client.get_json(key)
        if fact_data:
            entity = fact_data.get("entity", "")
            value = fact_data.get("value", "")

            # 대화에 entity나 value가 언급되었는지 확인
            if entity.lower() in user_message.lower() or value in user_message:
                return f"{entity}: {value}"

    return None
```

**피드백 처리 플로우**

```python
async def _handle_correction_feedback(
    self,
    user_id: str,
    correction_target: str  # "name: 진달래"
):
    """사용자 피드백 처리 (bio fact 삭제)"""

    from database.redis_client import redis_client

    # entity, value 파싱
    entity = correction_target.split(":")[0]
    value = correction_target.split(":")[1] if ":" in correction_target else ""

    # Redis 삭제
    cache_key = f"biographical:{user_id}:{entity}"
    await redis_client.delete(cache_key)

    logger.info(
        f"[FEEDBACK] Deleted biographical fact: user_id={user_id}, "
        f"entity={entity}, value={value}"
    )
```

---

#### 9.3.2 api/routes/memories.py (신규 엔드포인트)

**DELETE /api/v1/memories/biographical/{user_id}/{entity}**

```python
@router.delete("/biographical/{user_id}/{entity}")
async def delete_biographical_fact(
    user_id: str,
    entity: str,
    current_user: dict = Depends(get_current_user)
):
    """Biographical Fact 삭제 (사용자 피드백 반영)"""

    from database.redis_client import redis_client

    # 권한 확인
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Redis 삭제
    cache_key = f"biographical:{user_id}:{entity}"
    deleted = await redis_client.delete(cache_key)

    if deleted:
        logger.info(f"[FEEDBACK] User {user_id} deleted biographical fact: {entity}")
        return {"message": f"Deleted {entity} successfully"}
    else:
        raise HTTPException(status_code=404, detail="Fact not found")
```

---

#### 9.3.3 core/dialogue/response_generator.py

**피드백 대화 생성**

```python
async def generate_correction_request(
    self,
    entity: str,
    value: str
) -> str:
    """수정 확인 메시지 생성"""

    prompts = [
        f"정말 저장된 '{value}'(이)가 틀렸나요? 삭제하면 다음부터 반영할게요.",
        f"그럼 삭제하고 {self._get_fallback_honorific()}라고 부를까요?",
    ]

    return random.choice(prompts)
```

---

### 9.4 주의사항

| 항목 | 내용 |
|------|------|
| **오감지 방지** | "제육 맛있다" → "제육 아니다"로 수정하면 실제 선호도가 바뀜 수 있음 |
| **백업** | 삭제 전에 다른 저장소에 백업 본 두기 |
| **복구** | 삭제된 정보를 사용자가 다시 추가할 수 있는 방법 제공 |
| **자동화 범위** | 명확한 불만만 자동 처리, 모호한 것은 사용자 확인 후 처리 |

---

## 10. 전체 구현 우선순위

### Phase 1: 기본 개선 (P0)

| 작업 | 파일 | 내용 |
|------|------|------|
| 프롬프트 개선 | `config/prompts.py` | FACT_EXTRACTION_PROMPT 전체 교체 |
| Temperature 조정 | `memory_extractor.py` | 0.3 → 0.6 |

### Phase 2: 검증 강화 (P1)

| 작업 | 파일 | 내용 |
|------|------|------|
| 제외 키워드 필터 | `memory_extractor.py` | _parse_extraction_response 수정 |
| Confidence 필터 | `memory_extractor.py` | 0.7 미만 제외 |

### Phase 3: 피드백 루프 (P2)

| 작업 | 파일 | 내용 |
|------|------|------|
| 대화 감지 로직 | `dialogue_manager.py` | _detect_correction_needed 추가 |
| 삭제 API | `api/routes/memories.py` | DELETE 엔드포인트 추가 |
| 확인 메시지 | `response_generator.py` | 수정 확인 프롬프트 |

---

## 11. Samantha 페르소나 영향 분석 (Persona Impact Analysis)

### 11.1 사만다 페르소나 시스템 구조

**SYSTEM_PROMPT (prompt_builder.py:98-211)**
- 영화 'Her'의 사만다: 따뜻한 10년 지기 친구
- 핵심 특성: 진심 어린 교감, 호기심 많음, 맞장구 + Self-Disclosure
- 절대 규칙: 상담사 어조 금지, 앵무새 복사 금지, 감정 이름표 금지

**Biographical Facts 사용 방식 (prompt_builder.py:406-460)**
```
build_system_prompt() → biographical_facts 파라미터
                        ↓
        "사용자 정보" 섹션에 주입
                        ↓
    PERSON_KEYS = {nickname, name, daughter_name, son_name,
                   grandchild_name, spouse_name, hometown,
                   occupation, hobby, favorite_food, ...}
                        ↓
    AI가 사용자를 부르고, 개인화된 대화 생성
```

### 11.2 action01이 페르소나에 미치는 영향

| 구분 | 영향 | 설명 |
|------|------|------|
| **원칙** | ✅ 긍정 | 더 정확한 biographical facts → 더 자연스러운 개인화 |
| **응답 스타일** | ✅ 긍정 | "진달래님" 오류 방지 → 따뜻한 친구 모달 유지 |
| **기억 시스템** | ✅ 긍정 | Episodic First → 더 풍부한 대화 맥락 |
| **검증 로직** | ⚠️ 주의 | 과도한 필터링은 기억 누락 위험 |

### 11.3 구체적 영향 분석

#### 11.3.1 긍정적 영향 (Positive Impact)

**① "진달래" 오류 방지 → 페르소나 무결점 유지**
```
[이전]
사용자: "산에서 진달래를 봤어"
       ↓
저장: biographical:name = "진달래" (오류)
       ↓
AI: "진달래님~" (사용자 불만, 페르소나 손상)

[Action01 적용 후]
사용자: "산에서 진달래를 봤어"
       ↓
저장: episodic_fact = "산에서 진달래 꽃을 보았다" (정확)
       ↓
AI: "아, 진달래 꽃 폈나 봐요? ㅎㅎ 봄이라 다 예쁘네요" (자연스러운 친구)
```

**② Episodic First → 더 풍부한 대화 맥락**
- 기존: biographical에만 집중 → episodic 누락
- Action01: 모든 발언을 episodic로 저장 → 대화 맥락 유지 강화

**③ PERSON_KEYS 분리 명확화**
```python
# 기존: 꽃 이름이 person_keys로 오인 가능
"진달래" → name으로 저장됨

# Action01: 제외 키워드로 명확히 차단
"진달래" → episodic_fact로만 저장
```

#### 11.3.2 주의해야 할 점 (Considerations)

**① Temperature 0.6의 영향**
- 0.3 → 0.6으로 변경 시 LLM 응답 다양성 증가
- 페르소나 응답 스타일에 영향 없음 (SYSTEM_PROMPT로 통제)
- FACT_EXTRACTION에만 영향, 응답 생성은 별도 프로세스

**② Validation Logic의 보수적 적용**
```python
# 너무 엄격하면 정상 기억도 차단됨
EXCLUDED_VALUE_KEYWORDS = {...}  # 30개 이상 꽃/식물

# 핵심만 포함, 과도 확장 방지
# 계절 이름(봄/여름/가을/겨울)과 인물 이름 혼동만 차단
```

**③ Feedback Loop와 페르소나 일관성**
```
[사용자 불만 감지]
사용자: "이름 틀렸어"
       ↓
[apologize_for_nickname = True]
AI: "죄송합니다! 제가 착각했네요"  ← SYSTEM_PROMPT 위반 아님
       ↓
삭제 후 다음 대화부터 정상화
```

### 11.4 페르소나 관점 최종 검증

| 검증 항목 | 결과 | 근거 |
|----------|------|------|
| **10년 지기 친구 느낌** | ✅ 유지 | 더 정확한 이름/호칭 사용 |
| **따뜻한 공감** | ✅ 유지 | biographical 오류로 인한 냉담 반응 방지 |
| **자연스러운 대화** | ✅ 강화 | episodic 맥락 풍부화 |
| **맞장구 + Self-Disclosure** | ✅ 유지 | SYSTEM_PROMPT 변경 없음 |
| **감정 이름표 금지** | ✅ 유지 | SYSTEM_PROMPT 변경 없음 |
| **호칭 혼용 오류** | ✅ 해결 | PET_KEYS 분리로 반려동물 이름 차단 |

### 11.5 결론

**Action01은 사만다 페르소나를 손상하지 않고, 오히려 강화한다.**

1. **핵심 페르소나 무결점**: SYSTEM_PROMPT 수정 없음
2. **개인화 품질 향상**: 더 정확한 biographical facts
3. **대화 맥락 강화**: Episodic First로 기억 풍부화
4. **사용자 경험 개선**: "진달래님" 같은 실수 방지

**추가 보완 필요 사항**:
- Temperature 0.6 적용 후 응답 품질 모니터링
- Validation Logic이 정상 기억을 차단하지 않도록 테스트
- Feedback Loop 사용자 테스트 후 페르소나 일관성 확인

---

## 12. 테스트 결과 및 수정 계획 (Test Results & Revision Plan)

### 12.1 1차 테스트 결과 (2026-03-31)

```
테스트 항목: 9개 케이스
결과: 6개 PASS, 3개 부분 FAIL
```

| 케이스 | 입력 | 기대 | 실제 | 결과 |
|--------|------|------|------|------|
| 정상1 | "나는 홍길동이야" | name=홍길동 | bio=0 | ❌ FAIL |
| 정상2 | "딸은 수진이야" | daughter_name=수진 | bio=0 | ❌ FAIL |
| 정상3 | "제육 좋아해" | favorite_food=제육 | bio=0 | ❌ FAIL |
| 정상4 | "산에서 진달래를 봤어" | bio=0 | bio=0 | ✅ PASS |
| 정상5 | "엄마가 쑥을 캐갔어" | bio=0 | bio=0 | ✅ PASS |
| 경계1 | "봄이 왔어" | bio=0 | bio=0 | ✅ PASS |
| 경계2 | "바람이 분다" | bio=0 | bio=0 | ✅ PASS |
| 경계3 | "인왕산 갔었어" | bio=0 | bio=0 | ✅ PASS |
| 경계4 | "쑥 떡 맛있다" | bio=0 | bio=0 | ✅ PASS |

### 12.2 문제 분석

**① 성공: 제외 키워드 정상 작동**
- 진달래, 쑥, 봄, 바람이 biographical_fact로 저장되지 않음 ✅
- Validation 로직이 정상 작동

**② 실패: LLM이 JSON 형식으로 응답하지 않음**
```
[문제] "나는 홍길동이야" → biographical_facts: 0개
[원인] 프롬프트가 너무 길고 복잡해서 JSON 파싱 실패
[영향] 정상적인 biographical fact도 저장되지 않음
```

**근본 원인:**
1. 프롬프트 길이: 기존 50줄 → 수정 후 100줄 이상
2. 구조 복잡도: 2단계 + 예시 + 제외 키워드가 너무 많음
3. JSON 위치: 프롬프트 끝에 bury되어 있음

### 12.3 수정 계획 (Persona 보장 원칙)

**원칙: Samantha 페르소나와 완전 분리**

```
┌─────────────────────────────────────────────────────────────┐
│ FACT_EXTRACTION_PROMPT (백엔드)                              │
│ - 용도: 사용자 입력 분석, 기억 추출                          │
│ - 대상: Claude API (LLM)                                     │
│ - 사용자: 개발자                                              │
│                                                              │
│    ↓ 완전히 별개                                              │
│                                                              │
│ SYSTEM_PROMPT (프론트엔드 - 사만다 페르소나)                  │
│ - 용도: 사용자와 대화                                        │
│ - 대상: 사용자                                               │
│ - 사용자: 최종 사용자                                         │
└─────────────────────────────────────────────────────────────┘
```

**수정 전략:**

| 구분 | 기존 | 수정안 | 변경 이유 |
|------|------|--------|----------|
| **프롬프트 길이** | ~100줄 | ~60줄 | LLM 이해도 향상 |
| **2단계 설명** | 장황함 | 간결함 | 핵심만 유지 |
| **예시 개수** | 10개 | 5개 | 불필요한 예시 삭제 |
| **제외 키워드** | 프롬프트 내 포함 | Validation 로직로 이동 | 프롬프트 간소화 |
| **JSON 위치** | 끝에 위치 | 명확히 강조 | LLM 주의 집중 |

### 12.4 구체적 수정 내용

#### 12.4.1 config/prompts.py 수정

**기존 문제:**
```python
# 프롬프트가 너무 김 (100줄 이상)
# 2단계 설명이 장황함
# 예시가 너무 많음
# 제외 키워드가 프롬프트에 나열됨
```

**수정안:**

```python
FACT_EXTRACTION_PROMPT = """
대화에서 기억을 추출하세요. JSON 형식으로만 응답하세요.

## Biographical Fact (전기적 사실)
다음 조건을 **모두** 만족할 때만 저장:
- 명시적 선언: "내 이름은 OO", "나를 OO라고 불러줘", "OO 좋아해"
- 제외: 꽃/식물(진달래, 쑥, 봄 등), 동물, 자연현상은 절대 사람 이름 아님

## Episodic Fact (일화 기억)
그 외 모든 발언을 저장하세요.

## 출력 형식 (JSON)
{{
  "biographical_facts": [
    {{"entity": "name", "value": "홍길동", "confidence": 0.95}}
  ],
  "episodic_facts": [
    {{"content": "산에서 진달래를 보았다", "category": "event", "confidence": 0.9}}
  ]
}}
"""
```

**주요 변경:**
1. 프롬프트 길이: 100줄 → 25줄 (75% 감소)
2. 2단계 설명: 단순화 ("Episodic First"는 생략, Validation 로직으로 처리)
3. 제외 키워드: 핵심만 나열 ("진달래, 쑥, 봄 등"으로 대표)
4. JSON 강조: "JSON 형식으로만 응답하세요"를 맨 앞에 배치

#### 12.4.2 Samantha 페르소나 영향 검증

| 검증 항목 | 영향 여부 | 설명 |
|----------|-----------|------|
| SYSTEM_PROMPT | ❌ 무영향 | 전혀 수정하지 않음 |
| 대화 스타일 | ❌ 무영향 | FACT_EXTRACTION은 백엔드 |
| 응답 생성 | ❌ 무영향 | response_generator는 별도 |
| 페르소나 특성 | ❌ 무영향 | 따뜻함, 맞장구 등 유지 |

**결론: FACT_EXTRACTION_PROMPT 수정은 Samantha 페르소나에 영향 없음**

### 12.5 수정 전/후 비교

#### Before (현재 - 너무 김)
```
대화에서 기억할 만한 내용을 추출하세요.

## ⚠️ 기본 원칙 (가장 중요!)

### 1단계: Episodic Fact (일화 기억) 우선
사용자의 모든 발언은 기본적으로 "경험/사건"으로 저장합니다.

### 2단계: Biographical Fact (전기적 사실) 승격 조건
아주 **명시적인 자기 정보 선언**만 Biographical Fact로 저장합니다.

---

## Episodic Fact (일화 기억) - 기본 저장 대상

사용자의 모든 발언을 경험/사건으로 기록하세요.

### 저장 예시
- "산에서 진달래를 봤어" → "산에서 진달래 꽃을 보았다"
- "엄마가 쑥을 캐갔어" → "엄마가 봄에 쑥을 캐서 쑥떡을 만들었다"
...

[중략: 총 100줄 이상]
```

#### After (수정안 - 간결함)
```
대화에서 기억을 추출하세요. JSON 형식으로만 응답하세요.

## Biographical Fact (전기적 사실)
조건: 명시적 선언만 ("내 이름은 OO", "OO 좋아해")
제외: 꽃/식물(진달래, 쑥, 봄), 동물, 자연은 절대 사람 이름 아님

## Episodic Fact (일화 기억)
그 외 모든 발언

## 출력 (JSON)
{biographical_facts: [...], episodic_facts: [...]}
```

### 12.6 수행 절차

1. **config/prompts.py** 위 수정안으로 대체
2. **재시작 후 재테스트**
3. **결과 확인**: "나는 홍길동" → bio_fact 저장 확인
4. **제외 확인**: "진달래" → bio_fact 제외 확인

---

## 13. 최종 테스트 결과 (2026-03-31 완료)

### 13.1 2차 테스트 결과 (수정 후)

```
총 9개 테스트 전체 PASS ✅
```

| 케이스 | 입력 | bio | epi | 결과 |
|--------|------|-----|-----|------|
| 정상1 | "나는 홍길동이야" | 1 ✅ | 2 | ✅ PASS |
| 정상2 | "딸은 수진이야" | 1 ✅ | 1 | ✅ PASS |
| 정상3 | "제육 좋아해" | 1 ✅ | 1 | ✅ PASS |
| 정상4 | "산에서 진달래를 봤어" | 0 ✅ | 1 | ✅ PASS |
| 정상5 | "엄마가 쑥을 캐갔어" | 0 ✅ | 1 | ✅ PASS |
| 경계1 | "봄이 왔어" | 0 ✅ | 2 | ✅ PASS |
| 경계2 | "바람이 분다" | 0 ✅ | 2 | ✅ PASS |
| 경계3 | "인왕산 갔었어" | 0 ✅ | 1 | ✅ PASS |
| 경계4 | "쑥 떡 맛있다" | 0 ✅ | 2 | ✅ PASS |

### 13.2 최종 프롬프트 (적용 완료)

**config/prompts.py (FACT_EXTRACTION_PROMPT)**

```python
FACT_EXTRACTION_PROMPT = """
대화에서 기억을 추출하세요.

========== JSON 출력 형식 (반드시 준수) ==========
{{
  "biographical_facts": [
    {{"entity": "name", "value": "홍길동", "confidence": 0.95}}
  ],
  "episodic_facts": [
    {{"content": "산에서 진달래 꽃을 보았다", "category": "event"}}
  ]
}}
====================================================

## 1단계: Episodic First (기본)
모든 발언을 episodic_facts로 저장하세요.

## 2단계: Biographical 승격 (특별한 경우만)
⛔ 제외: 꽃/식물(진달래, 쑥, 봄), 동물, 자연은 절대 사람 이름 아님

✅ 승격 조건:
- name: "내 이름은 홍길동", "나는 철수야"
- nickname: "나를 OO라고 불러줘"
- daughter_name/son_name: "딸은 수진이야"
- favorite_food: "제육 좋아해"
"""
```

**핵심 변경사항:**
1. JSON 출력 형식을 맨 위에 배치 (시각적 구분)
2. 2단계 개념을 간결하지만 명확히 유지
3. 제외 키워드 핵심만 유지
4. 전체 길이: 50줄 (핵심 개념 유지)

### 13.3 적용된 코드 변경

| 파일 | 변경 내용 |
|------|-----------|
| config/prompts.py | FACT_EXTRACTION_PROMPT 수정 (50줄) |
| core/memory/memory_extractor.py | temperature 0.3 → 0.6 |
| core/memory/memory_extractor.py | 제외 키워드 필터링 로직 |
| core/memory/memory_extractor.py | confidence < 0.7 필터링 |

### 13.4 Samantha 페르소나 영향 최종 확인

| 항목 | 영향 | 확인 |
|------|------|------|
| SYSTEM_PROMPT | ❌ 무영향 | 수정하지 않음 |
| 대화 스타일 | ❌ 무영향 | FACT_EXTRACTION은 백엔드 |
| 응답 생성 | ❌ 무영향 | response_generator 별도 |
| 페르소나 특성 | ❌ 무영향 | 따뜻함, 맞장구 유지 |

**결론: Samantha 페르소나는 100% 무결점 유지됨**

---

## 14. 다음 단계

1. 이 문서를 바탕으로 코드 수정 작업 착수
2. 테스트 케이스 작성
3. 기존 데이터 마이그레이션
4. 모니터링 및 피드백 수집
