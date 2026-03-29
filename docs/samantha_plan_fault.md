# 사만다 페르소나 구현 계획서 결함 분석

> **작성일:** 2026-03-27
> **검증 대상:** `docs/samantha_complete_plan.md`
> **검증 방법:** 실제 코드베이스 라인 단위 크로스체크
> **결과:** 총 11개 결함 (CRITICAL 3, HIGH 4, MEDIUM 4)
> **결론:** 수정 없이 구현 시 **런타임 에러 3건, 테스트 실패 4건, 동작 불량 4건** 발생

---

## 📊 결함 요약

| # | Phase | 심각도 | 결함 유형 | 계획서 위치 | 한 줄 요약 |
|---|-------|--------|-----------|-------------|------------|
| 1 | B2 | **CRITICAL** | 런타임 에러 | Step 1 `_detect_emotion()` | 감정 라벨 EN/KO 미스매치 → 벡터 갱신 안 됨 |
| 2 | C5 | **CRITICAL** | 런타임 에러 | `send_proactive_message()` | `send_to_me()`에 `user_id` 전달 → `access_token` 필요 |
| 3 | C5 | **CRITICAL** | 런타임 에러 | `send_proactive_message()` | `send_bizmessage_friend_talk()` 키워드 인수명 오류 |
| 4 | C1 | **HIGH** | 테스트 실패 | `test_c1_episodic_memory.py` | `MemoryType` import 경로 오류 |
| 5 | C2 | **HIGH** | 테스트 실패 | `test_c2_rotation.py` | DOMAIN_ROTATION에 "RT" 누락 |
| 6 | C2 | **HIGH** | 구현 오류 | `_get_probe_question()` 수정 | 함수가 모듈 레벨인데 `self.`로 표기 |
| 7 | B4+A2 | **HIGH** | 테스트+구현 충돌 | `test_b4_time_aware.py` | gap 템플릿에 이모지 20+개 → "이모지 없음" 테스트 불가 |
| 8 | B3 | **MEDIUM** | 구현 누락 | 전체 계획 | `_check_probe_cooldown()` 데드코드 미해결 |
| 9 | A2 | **MEDIUM** | 구현 가이드 누락 | MEDIUM Priority | 이모지 정리 대상 4개 파일 수정 가이드 없음 |
| 10 | C1-3 | **MEDIUM** | 비용/성능 | `_generate_follow_up_note()` | 에피소드 저장마다 LLM 호출 → 비용/지연 무제한 |
| 11 | B2 | **MEDIUM** | 구현 누락 | `generate_response()` 수정 | `emotion_vector`를 response_generator에 전달하는 코드 누락 |

---

## 🔴 CRITICAL (런타임 에러 — 구현 전 반드시 수정)

---

### 결함 #1: B2 감정 라벨 EN/KO 미스매치

**문제:** 계획서의 `_detect_emotion()`은 영어 라벨(`"joy"`, `"sadness"`, `"anger"`)을 반환하지만, `_update_emotion_vector()` 내부의 `EMOTION_VECTOR_MAP`은 **한국어 키**로 정의됨. 결과적으로 `EMOTION_VECTOR_MAP.get("joy")` → `None` → 벡터가 항상 `(0.0, 0.0, 0.0)`으로 처리됨.

**계획서 코드 (오류):**
```python
# samantha_complete_plan.md B2 Step 1
async def _detect_emotion(self, text: str) -> str:
    emotion_keywords = {
        "joy": ["기쁘", "좋아", "행복", ...],       # ← 영어 키 반환
        "sadness": ["슬프", "우울", "쓸쓸", ...],   # ← 영어 키 반환
        "anger": ["화나", "짜증", "속상", ...],     # ← 영어 키 반환
```

**실제 코드 (`dialogue_manager.py:47-68`):**
```python
EMOTION_VECTOR_MAP = {
    "기쁨": (0.8, 0.6, 0.1),     # ← 한국어 키
    "행복": (0.7, 0.4, 0.1),
    "즐거움": (0.9, 0.7, 0.1),
    "설렘": (0.7, 0.7, 0.1),
    "평온": (0.1, -0.3, 0.0),
    "만족": (0.6, -0.2, 0.1),
    "불안": (-0.5, 0.5, -0.1),
    "짜증": (-0.4, 0.6, -0.1),
    "스트레스": (-0.5, 0.4, 0.0),
    "분노": (-0.7, 0.8, -0.2),
    "우울": (-0.8, -0.6, 0.0),
    "슬픔": (-0.7, -0.4, 0.0),
    "피곤": (-0.3, -0.8, 0.0),
    "무기력": (-0.6, -0.7, 0.0),
    "중립": (0.0, 0.0, 0.0),
}
```

**실제 `_update_emotion_vector()` 호출부 (`dialogue_manager.py:1009`):**
```python
target = EMOTION_VECTOR_MAP.get(emotion_label, (0.0, 0.0, 0.0))
# emotion_label = "joy" → EMOTION_VECTOR_MAP에 없음 → (0.0, 0.0, 0.0)
```

**영향:** 감정 벡터가 항상 (0.0, 0.0, 0.0) 유지 → B2 전체 태스크 무효화

**해결:**
```python
async def _detect_emotion(self, text: str) -> str:
    """간단 감정 인식 (B2-7)

    Returns:
        EMOTION_VECTOR_MAP의 키와 일치하는 한국어 감정 라벨
    """
    emotion_keywords = {
        "기쁨": ["기쁘", "좋아", "행복", "즐겁", "신나", "ㅋㅋ", "ㅎㅎ", "대박"],
        "우울": ["슬프", "우울", "쓸쓸", "외롭", "ㅠㅠ", "ㅜㅜ"],
        "분노": ["화나", "짜증", "속상", "억울", "미치"],
        "불안": ["무섭", "두렵", "걱정"],
        "피곤": ["피곤", "힘들", "지치"],
    }

    for emotion, keywords in emotion_keywords.items():
        if any(keyword in text for keyword in keywords):
            return emotion

    return "중립"
```

---

### 결함 #2: C5 `send_to_me()` 파라미터 오류

**문제:** 계획서 코드가 `user_id`를 첫 번째 인수로 전달하지만, 실제 함수는 `access_token: str`을 받음.

**계획서 코드 (오류):**
```python
# samantha_complete_plan.md C5 send_proactive_message()
if user.oauth_access_token:
    result = await kakao_client.send_to_me(user_id=str(user.id), message=message)
    #                                      ^^^^^^^^ → access_token이어야 함
```

**실제 시그니처 (`kakao_client.py:636-641`):**
```python
async def send_to_me(
    self,
    access_token: str,       # ← 사용자의 OAuth 액세스 토큰
    message: str,
    link_url: Optional[str] = None,
    button_title: Optional[str] = None
) -> Dict[str, Any]:
```

**영향:** `TypeError` 또는 카카오 API 401 에러

**해결:**
```python
if user.oauth_access_token:
    result = await kakao_client.send_to_me(
        access_token=user.oauth_access_token,  # 수정
        message=message
    )
    method = "oauth"
```

---

### 결함 #3: C5 `send_bizmessage_friend_talk()` 키워드 인수명 오류

**문제:** 계획서가 `user_key=`를 사용하지만, 실제 파라미터명은 `plus_friend_user_key`.

**계획서 코드 (오류):**
```python
result = await kakao_client.send_bizmessage_friend_talk(
    user_key=user.kakao_channel_user_key,  # ← 잘못된 키워드명
    message=message
)
```

**실제 시그니처 (`kakao_client.py:856-860`):**
```python
async def send_bizmessage_friend_talk(
    self,
    plus_friend_user_key: str,    # ← 올바른 파라미터명
    message: str,
    retry_count: int = 3
) -> Dict[str, Any]:
```

**영향:** `TypeError: unexpected keyword argument 'user_key'`

**해결:**
```python
elif user.kakao_channel_user_key:
    result = await kakao_client.send_bizmessage_friend_talk(
        plus_friend_user_key=user.kakao_channel_user_key,  # 수정
        message=message
    )
    method = "channel"
```

---

## 🟠 HIGH (테스트 실패 또는 동작 불량)

---

### 결함 #4: C1 테스트 import 경로 오류

**문제:** 테스트가 `database.models`에서 `MemoryType`을 임포트하려 하지만, 실제 정의 위치는 `core.memory.memory_extractor`에 있음.

**계획서 코드 (오류):**
```python
# samantha_complete_plan.md C1 테스트
from database.models import MemoryType  # ← 잘못된 경로
```

**실제 정의 위치 (`memory_extractor.py:41-47`):**
```python
class MemoryType(str, Enum):
    """기억 유형"""
    EPISODIC = "episodic"
    BIOGRAPHICAL = "biographical"
    EMOTIONAL = "emotional"
    PROCEDURAL = "procedural"
```

**해결:**
```python
from core.memory.memory_extractor import MemoryType, EntityCategory, ExtractedMemory
```

---

### 결함 #5: C2 DOMAIN_ROTATION에 "RT" 도메인 누락

**문제:** 테스트가 6개 MCDI 도메인(LR, SD, NC, TO, ER, RT) 전체 포함을 검증하지만, 계획서의 `DOMAIN_ROTATION`에 `"RT"`가 없음.

**계획서 DOMAIN_ROTATION:**
```python
DOMAIN_ROTATION = {
    0: ["LR", "ER"],  # 월요일
    1: ["TO", "NC"],  # 화요일
    2: ["SD"],        # 수요일
    3: ["LR", "TO"],  # 목요일
    4: ["ER", "NC"],  # 금요일
    5: ["SD", "LR"],  # 토요일
    6: ["TO", "ER"],  # 일요일
}
# "RT" (Reaction Time) 누락!
```

**계획서 자체 테스트 (`test_c2_rotation.py`)가 실패함:**
```python
def test_all_domains_covered(self):
    expected = {"LR", "SD", "NC", "TO", "ER", "RT"}
    assert all_domains.issuperset(expected)  # ← "RT" 없어서 FAIL
```

**해결:** 하루에 "RT" 추가:
```python
DOMAIN_ROTATION = {
    0: ["LR", "ER"],    # 월요일
    1: ["TO", "NC"],    # 화요일
    2: ["SD", "RT"],    # 수요일 ← RT 추가
    3: ["LR", "TO"],    # 목요일
    4: ["ER", "NC"],    # 금요일
    5: ["SD", "LR"],    # 토요일
    6: ["TO", "ER", "RT"],  # 일요일 ← RT 추가
}
```

---

### 결함 #6: C2 `_get_probe_question()` 함수 시그니처 불일치

**문제:** 계획서가 `self._get_probe_question(domain, user_context, mcdi_context)`로 메서드 호출을 표기하지만, 실제 함수는 **모듈 레벨 함수**이며 파라미터 1개만 받음.

**계획서 코드 (오류):**
```python
def _get_probe_question(
    self,                          # ← self 없음 (모듈 레벨 함수)
    domain: str,
    user_context: dict,            # ← 존재하지 않는 파라미터
    mcdi_context: dict             # ← 존재하지 않는 파라미터
) -> str:
```

**실제 코드 (`prompt_builder.py:73-91`):**
```python
def _get_probe_question(domain: str) -> str:
    """도메인에 맞는 자연어 질문 랜덤 반환 (B3-3)"""
    import random
    questions = DEMENTIA_PROBE_QUESTIONS.get(domain)
    if not questions:
        return ""
    return random.choice(questions)
```

**해결:** 모듈 레벨에서 로테이션 체크:
```python
# 인지 도메인 주간 로테이션 스케줄 (C2-1)
DOMAIN_ROTATION = {
    0: ["LR", "ER"],
    1: ["TO", "NC"],
    2: ["SD", "RT"],
    3: ["LR", "TO"],
    4: ["ER", "NC"],
    5: ["SD", "LR"],
    6: ["TO", "ER", "RT"],
}

def _get_probe_question(domain: str) -> str:
    """도메인에 맞는 자연어 질문 랜덤 반환 (B3-3, C2-1 로테이션 추가)"""
    import random
    from datetime import datetime

    # C2-1: 요일별 로테이션 체크
    today_weekday = datetime.now().weekday()
    rotation_domains = DOMAIN_ROTATION.get(today_weekday, ["LR", "SD"])
    if domain not in rotation_domains:
        logger.debug(f"Domain {domain} not in today's rotation {rotation_domains}")
        return ""

    questions = DEMENTIA_PROBE_QUESTIONS.get(domain)
    if not questions:
        return ""
    return random.choice(questions)
```

---

### 결함 #7: B4+A2 이모지 템플릿 충돌 — 테스트 통과 불가

**문제:** B4 테스트는 gap 메시지에 유니코드 이모지 없음을 검증하지만, `time_aware.py` 템플릿에 이모지가 **20개 이상** 하드코딩되어 있음. B4 단독 구현으로는 이 테스트를 절대 통과할 수 없음.

**이모지가 포함된 실제 템플릿 (`time_aware.py:50-106`):**

| 라인 | 파일 | 이모지 | 출처 |
|------|------|--------|------|
| 53-56 | `time_aware.py` | 🌅🍳☀️🌱 | TIME_GREETING "morning" |
| 59-62 | `time_aware.py` | 🍽️🌤️🥗☕ | TIME_GREETING "noon" |
| 65-68 | `time_aware.py` | 🌿🌤️⏰🏃‍♀️ | TIME_GREETING "afternoon" |
| 71-74 | `time_aware.py` | 🌙🌅🍃🌸 | TIME_GREETING "evening" |
| 77-80 | `time_aware.py` | 🌙😴!🌙✨ | TIME_GREETING "night" |
| 87-89 | `time_aware.py` | 😊🌱🌿 | GAP "short" |
| 92-94 | `time_aware.py` | 🌸🌿🌱 | GAP "medium" |
| 97-99 | `time_aware.py` | 🌸🌿🌱 | GAP "long" |
| 102-104 | `time_aware.py` | 🌸🌿🌱 | GAP "extended" |
| 305 | `response_validator.py` | 🌱 | `_add_variation()` |
| 747-751 | `dialogue_manager.py` | 🌙😊💊🏥💭 | 교란 변수 질문 |

**계획서 B4 테스트 (실패 확정):**
```python
async def test_gap_message_no_emoji(self):
    gap_message = await manager.generate_gap_message(user_id)
    emojis = re.findall(emoji_pattern, gap_message)
    assert len(emojis) == 0  # ← 항상 FAIL (템플릿에 이모지 있음)
```

**해결:** B4와 A2를 **동시에** 구현해야 함. 이모지 → 한국어 텍스트 치환 가이드 추가 필요:

| 원본 | 대체 | 위치 |
|------|------|------|
| 🌅🌅☀️ | (삭제 또는 텍스트 설명) | morning 템플릿 |
| 🌱🌿🌸 | "정원", "꽃", "나뭇잎" (이미 텍스트에 포함) | 전체 템플릿 |
| 😊 | "ㅎㅎ" | gap short |
| 🌙✨ | (삭제) | evening/night 템플릿 |
| 🍳🍽️🥗☕⏰🏃‍♀️🍃😴🤜💭💊🏥 | (삭제) | 시간대별 템플릿 |
| " 🌱" | " 정원에서" | response_validator.py:305 |
| 🌙😊💊🏥💭 | (삭제) | dialogue_manager.py:747-751 |

---

## 🟡 MEDIUM (구현 누락 또는 가이드 불충분)

---

### 결함 #8: B3 `_check_probe_cooldown()` 데드코드 미해결

**문제:** `samantha_task_fault.md`에서 `_check_probe_cooldown()` 호출부 0건을 지적했지만, `samantha_complete_plan.md`에는 이에 대한 해결 방안이 전혀 없음.

**실제 코드 (`kakao_webhook.py:542-569`):**
```python
async def _check_probe_cooldown(user_id: str, domain: str) -> bool:
    """탐침 질문 쿨다운 체크

    동일 도메인의 탐침 질문이 2턴 이내에 사용되었는지 확인.
    30분 TTL로 Redis에 기록.
    """
    # ... 구현됨 ...
```

**grep 결과:** 전체 코드베이스에서 `_check_probe_cooldown` 호출부 0건

**영향:** 치매 탐침 질문이 쿨다운 없이 연속 발생 가능 → 사용자 불편

**해결 옵션:**
- **옵션 A (권장):** `_get_probe_question()` 호출 전에 쿨다운 체크 추가
  ```python
  # category_selector.py 또는 prompt_builder.py에서
  from api.routes.kakao_webhook import _check_probe_cooldown
  if await _check_probe_cooldown(user_id, domain):
      return ""  # 쿨다운 중이면 빈 문자열 반환
  ```
- **옵션 B:** 함수를 `prompt_builder.py`로 이동하고 거기서 연결
- **옵션 C:** 데드코드로 판단하여 삭제 (쿨다운이 불필요하다고 결정한 경우)

---

### 결함 #9: A2 이모지 정리 대상 4개 파일 수정 가이드 누락

**문제:** 계획서 MEDIUM Priority에 "A2 이모지: SYSTEM_PROMPT 모순 수정 (line 185 삭제) + time_aware.py 템플릿 수정 (30분)"라고만 언급하지만, 수정 대상이 4개 파일이며 구체적인 수정 가이드가 없음.

**수정 대상 파일 정리:**

| 파일 | 라인 | 수정 내용 | 수정량 |
|------|------|-----------|--------|
| `prompt_builder.py` | 185 | `"2. 이모지 절제적 사용 (1-2개/메시지)\n"` 라인 삭제 | 1줄 |
| `time_aware.py` | 50-106 | `TIME_GREETING_TEMPLATES` + `GAP_MESSAGE_TEMPLATES`에서 모든 유니코드 이모지 제거 | ~25줄 |
| `response_validator.py` | 305 | `" 🌱"` → `" 정원에서"` | 1줄 |
| `dialogue_manager.py` | 747-751 | 교란 변수 질문에서 🌙😊💊🏥💭 제거 | 5줄 |

**time_aware.py 수정 예시:**
```python
# 수정 전 (Line 53)
"좋은 아침이에요 🌅 오늘도 정원에 햇살이 따뜻하게 내려앉고 있어요.",
# 수정 후
"좋은 아침이에요. 오늘도 정원에 햇살이 따뜻하게 내려앉고 있어요.",

# 수정 전 (Line 87)
"바로 다시 와주셔서 반가워요 😊",
# 수정 후
"바로 다시 와주셔서 반가워요 ㅎㅎ",
```

---

### 결함 #10: C1-3 `follow_up_notes` LLM 호출 비용 문제

**문제:** 계획서의 `_generate_follow_up_note()`은 에피소드 저장 시마다 별도 LLM API 호출을 수행함. 사용자 1명이 하루 10개 에피소드를 저장하면 10회 LLM 호출 추가. 비용/지연에 대한 고려가 전혀 없음.

**계획서 코드:**
```python
async def _generate_follow_up_note(episode_content: str, user_id: str) -> str:
    llm = LLMService()
    response = await llm.call(          # ← 에피소드마다 LLM 호출
        prompt=prompt,
        temperature=0.7,
        max_tokens=100
    )
    return response.strip()
```

**기존 구현 (`memory_manager.py:332-390`):**
- 이미 `_extract_follow_up_topics()` 존재 (regex 기반, LLM 없음)
- 비용 0, 지연 ~1ms

**해결 옵션:**
- **옵션 A (권장):** 기존 regex 기반 유지, 품질이 부족할 때만 LLM 사용 (fallback)
- **옵션 B:** BackgroundTask로 비동기 처리 (사용자 응답 지연 없음)
- **옵션 C:** 배치 처리 (하루 1회, 자정에 일괄 생성)

---

### 결함 #11: B2 `generate_response()`에서 `emotion_vector`를 response_generator에 전달하는 코드 누락

**문제:** 계획서 B2 Step 2에서 `_detect_emotion()`과 `_update_emotion_vector()` 호출 코드는 제시하지만, **갱신된 벡터를 `response_generator`에 전달하는 코드를 누락**. 실제 `generate_response()`의 현재 코드(Lines 510-528)를 보면 `emotion_vector` 파라미터가 전혀 전달되지 않음.

**현재 코드 (`dialogue_manager.py:510-528`):**
```python
if emotion and emotion_intensity is not None:
    response = await self.response_generator.generate_empathetic_response(
        user_message=user_message,
        detected_emotion=emotion,
        emotion_intensity=emotion_intensity,
        conversation_history=conversation_history,
        user_context=user_context,
        mcdi_context=mcdi_context,
        relationship_stage=relationship_stage
        # ← emotion_vector 파라미터 없음!
    )
else:
    response = await self.response_generator.generate(
        user_message=user_message,
        conversation_history=conversation_history,
        user_context=user_context,
        next_question=next_question,
        mcdi_context=mcdi_context,
        relationship_stage=relationship_stage
        # ← emotion_vector 파라미터 없음!
    )
```

**response_generator는 이미 파라미터를 수용함** (`response_generator.py:103-112, 214-224`):
```python
async def generate(self, ..., emotion_vector: Optional[Dict[str, float]] = None) -> str:
async def generate_empathetic_response(self, ..., emotion_vector: Optional[Dict[str, float]] = None) -> str:
```

**해결:** 두 호출부 모두에 `emotion_vector=updated_vector` 추가:
```python
# Line 510-519 수정
response = await self.response_generator.generate_empathetic_response(
    ...
    relationship_stage=relationship_stage,
    emotion_vector=updated_vector  # ← 추가
)

# Line 520-528 수정
response = await self.response_generator.generate(
    ...
    relationship_stage=relationship_stage,
    emotion_vector=updated_vector  # ← 추가
)
```

---

## 📋 수정 우선순위 매트릭스

### 구현 전 반드시 수정 (Phase S + B1 + B2 + B3 + C5)

| 순서 | 결함 # | Phase | 수정 내용 | 소요시간 |
|------|--------|-------|-----------|----------|
| 1 | #11 | B2 | `generate_response()`에 `emotion_vector=` 전달 추가 | 2분 |
| 2 | #1 | B2 | `_detect_emotion()` 한국어 라벨 반환으로 수정 | 5분 |
| 3 | #2 | C5 | `send_to_me(access_token=...)` 수정 | 2분 |
| 4 | #3 | C5 | `send_bizmessage_friend_talk(plus_friend_user_key=...)` 수정 | 2분 |

### 구현 중 동시 수정 (Phase B4 + A2)

| 순서 | 결함 # | Phase | 수정 내용 | 소요시간 |
|------|--------|-------|-----------|----------|
| 5 | #7 | B4+A2 | time_aware.py 이모지 20+개 제거 + 테스트 수정 | 30분 |
| 6 | #9 | A2 | response_validator.py, dialogue_manager.py 이모지 제거 | 10분 |

### 구현 후 보완 (Phase C1 + C2 + B3)

| 순서 | 결함 # | Phase | 수정 내용 | 소요시간 |
|------|--------|-------|-----------|----------|
| 7 | #4 | C1 | 테스트 import 경로 수정 | 1분 |
| 8 | #5 | C2 | DOMAIN_ROTATION에 "RT" 추가 | 2분 |
| 9 | #6 | C2 | `_get_probe_question()` 모듈 레벨 함수로 수정 | 5분 |
| 10 | #8 | B3 | `_check_probe_cooldown()` 호출부 추가 또는 삭제 결정 | 10분 |
| 11 | #10 | C1-3 | `_generate_follow_up_note()` 비용 최적화 (BackgroundTask) | 15분 |

---

## ✅ 수정 완료 후 재검증 체크리스트

### CRITICAL 수정 확인
- [ ] `_detect_emotion()` 반환값이 `EMOTION_VECTOR_MAP` 키와 일치하는지 (한국어)
- [ ] `send_to_me()` 첫 인수가 `access_token`인지
- [ ] `send_bizmessage_friend_talk()` 키워드가 `plus_friend_user_key`인지

### HIGH 수정 확인
- [ ] C1 테스트가 `core.memory.memory_extractor`에서 import하는지
- [ ] DOMAIN_ROTATION에 "RT" 포함되어 있는지
- [ ] `_get_probe_question()` 수정이 모듈 레벨 함수 구조를 유지하는지
- [ ] time_aware.py 템플릿에서 이모지가 모두 제거되었는지

### MEDIUM 수정 확인
- [ ] `_check_probe_cooldown()` 호출부가 추가되었거나 삭제 사유가 문서화되었는지
- [ ] response_validator.py, dialogue_manager.py 이모지가 제거되었는지
- [ ] `_generate_follow_up_note()`에 비용 제어가 있는지

---

*이 문서는 `docs/samantha_complete_plan.md`의 실제 코드베이스 크로스체크 결과를 기반으로 작성되었습니다 (2026-03-27).*
