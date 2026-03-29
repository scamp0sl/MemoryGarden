# 사만다 페르소나 미완료 태스크 상세 명세서

> **작성일:** 2026-03-27 (최종 업데이트 - 2차 코드 검증 반영)
> **기준 문서:** `docs/samantha_persona_task_20260325.md`
> **평가 기준:** **보수적 관점** (함수 존재 ≠ 완료, 실제 호출/동작 필요)
> **검증 방법:** 실제 구현 코드 라인 단위 확인 + grep 전체 코드 호출부 검증
> **목적:** 48개 태스크 중 미완료된 태스크의 구체적 구현 가이드 제공

---

## 📋 미완료 태스크 개요 (GLM 코드 검증 반영)

| Phase | 태스크 | 실제 완료도 | 우선순위 | 비고 |
|-------|--------|-------------|----------|------|
| **S** | 질문 패턴 재설계 | 0% (0/3) | **CRITICAL** | **2026-03-27 신규** |
| **B1** | Relationship Stage | **93%** | **HIGH** | recovery_events 증가 로직 누락 |
| **B2** | 감정 벡터 | **40%** | **HIGH** | 실제 호출 연결 전체 누락 |
| **B3** | MCDI 통합 | **78%** | **HIGH** | 반복 감지 연결 누락 + _check_probe_cooldown() 데드코드 |
| **B4** | 시간 인식 | 75% (3/4) | MEDIUM | B4-4 gap prefixing만 필요 |
| **C1** | 에피소드 서사화 | **~70%** | HIGH | C1-2 이미 구현됨, 나머지 비공식 구현 |
| **C2** | 치매 탐지 분산 전략 | 0% (0/2) | MEDIUM | |
| **C5** | Proactive Messaging | 0% (0/6) | HIGH | |
| **A** | 프롬프트 규칙 | 100% | - | A2 이모지 충돌 이슈 있음 |
| **C3** | 출력 검증기 | 100% | - | 완료 |
| **C4** | 기억 감쇠 | 0% (0/1) | LOW | 감쇠 공식만 완료 |

> **완성도 변경 사항 (2026-03-27 GLM 검증):**
> - B1: 100% → **93%** (recovery_events 증가 로직 누락 확인)
> - B2: 67% → **40%** (실제 호출 연결 전체 눝락 확인)
> - B3: 100% → **88%** → **78%** (반복 감지 함수 연결 누락 + _check_probe_cooldown 데드코드 발견)
> - C1: 0% → **~55%** → **~70%** (C1-2 감정 강도 필터 이미 구현됨 확인)

---

## 🔍 GLM 코드 검증 vs 기존 분석 차이점

### GLM이 추가로 발견한 결함:

| 항목 | 기존 분석 | GLM 분석 | 실제 검증 결과 |
|------|-----------|----------|----------------|
| **B1 recovery_events** | 미언급 | **누락 확인** | ✅ GLM 정확 |
| **B2 감정 벡터** | 67% (부분 완료) | **40% (호출 안 됨)** | ✅ GLM 정확 |
| **B3-5 반복 감지** | 미상세 | **연결 누락 확인** | ✅ GLM 정확 |
| **C1 에피소드** | 0% (미구현) | **~55% (비공식 구현)** | ✅ GLM 정확 |
| **A2 이모지 충돌** | 미언급 | **규칙 불일치 확인** | ✅ GLM 정확 |
| **C1-2 감정 필터** | ❌ 미구현 | **✅ 이미 구현됨** | ✅ GLM 정확 (완료도 상향) |
| **B3-4 데드코드** | 미언급 | **_check_probe_cooldown() 호출부 0건** | ✅ GLM 정확 |
| **SYSTEM_PROMPT 모순** | 미언급 | **Line 185 vs 200 내부 충돌** | ✅ GLM 정확 |

---

## 📌 Phase S 제정 배경 (중요)

> **사용자 불만 사례 (2026-03-26):** aa96e75d-70e2-4546-9001-043cc5db047d 대화에서
> - "너무 질문이 많아" (19:31)
> - "또 질문이야" (19:32)
>
> **원인 분석 결론:**
> - **NOT 코드 부족**: Phase A/B1/B2/B3가 모두 구현된 상태
> - **GPT-4o 패턴 문제**: "공감 후 질문"이 AI의 학습된 기본 패턴
> - **Phase A A1 규칙(감정 직접 명명 금지)의 부작용**:
>   - "힘드시겠어요" → "쓸쓸해지네요" + "어떻게 쉬시나요?"
>   - 감정 라벨을 질문으로 대체하는 현상
>
> **해결 방향:** Phase A 규칙은 유지하되, **질문 빈도 제어** 규칙만 추가

---

## ✅ 완료된 Phase (GLM 코드 검증 반영, 2026-03-27)

| Phase | 상태 | 비고 |
|-------|------|------|
| **A** | ✅ 100% 완료 | A1~A5 모두 prompt_builder.py에 구현. **단, A2 이모지 충돌 이슈 있음** |
| **B1** | ⚠️ **93% 완료** | RELATIONSHIP_STAGE_PROMPTS + Stage 블록 주입 완료. **recovery_events 증가 로직 누락** |
| **B2** | ⚠️ **40% 완료** | 함수는 완벽하나 **실제 호출 연결 전체 누락**. emotion_vector가 항상 None 전달됨 |
| **B3** | ⚠️ **78% 완료** | MCDI 어댑티브 블록 + 캐시 완료. **반복 감지 연결 누락 + probe cooldown 데드코드** |
| **B4** | ⚠️ 75% 완료 | TimeAwareDialogue 완료. **B4-4 gap prefixing 미구현** |
| **C1** | ⚠️ **~70% 완료** | **C1-2 감정 강도 필터 이미 구현됨**. C1-1/C1-3 비공식 구현 상태 |
| **C3** | ✅ 100% 완료 | ResponseValidator 구현 및 DialogueManager 연결 완료 |

### B1-93% 상세: recovery_events 증가 로직 누락

**실제 코드 확인 (`dialogue_manager.py:905-913`):**
```python
# 감정 이벤트 기록 (현재 코드)
if emotion:
    if any(e in emotion for e in positive_emotions):
        rel["positive_events"] += 1
    elif any(e in emotion for e in negative_emotions):
        rel["conflict_events"] += 1
# ← recovery_events 증가 로직 전혀 없음!
```

**결함 영향:**
- Stage 3 → 4 진급 조건: `rel["recovery_events"] >= 1`
- 하지만 이 값을 증가시키는 코드가 없음 → **Stage 4에 도달 불가**

**필요 수정 (약 5줄):**
```python
# dialogue_manager.py _update_relationship_stage() 내부
rel["_was_negative"] = rel.get("_was_negative", False)  # 상태 추적 변수

if emotion:
    if any(e in emotion for e in positive_emotions):
        rel["positive_events"] += 1
        if rel["_was_negative"]:  # 갈등 후 긍정 전환 = 회복
            rel["recovery_events"] += 1
            rel["_was_negative"] = False
    elif any(e in emotion for e in negative_emotions):
        rel["conflict_events"] += 1
        rel["_was_negative"] = True
```

### B2-40% 상세: 호출 연결 전체 누락

**실제 코드 확인 (`dialogue_manager.py:447-528`):**
```python
# Line 448-452: relationship_stage 업데이트 ✅ 호출됨
if relationship_stage is None:
    relationship_stage = await self._update_relationship_stage(user_id, emotion)

# Line 455: last_interaction 업데이트 ✅ 호출됨
await self.update_last_interaction(user_id)

# ← 여기서 _update_emotion_vector(user_id, emotion) 호출이 누락됨!

# Line 510-528: response_generator 호출
if emotion and emotion_intensity is not None:
    response = await self.response_generator.generate_empathetic_response(
        # emotion_vector 파라미터 전달 누락!
    )
```

**결함 영향:**
- 감정 벡터가 항상 초기값 {"v": 0.0, "a": 0.0, "i": 0.5} 유지
- `_vector_to_prompt_description()`이 항상 빈 문자열 반환
- 감정 상태 기반 대화 조절이 작동하지 않음

### B3-78% 상세: 반복 감지 연결 누락 + probe cooldown 데드코드

**실제 코드 확인:**
- `kakao_webhook.py:574-603` — `_detect_repetition()` 함수 ✅ 완벽히 구현됨
- `kakao_webhook.py:820-825` — 웹훅 핸들러 ❌ 호출 없음

```python
# 현재 코드 (kakao_webhook.py:820-825)
mcdi_context = await _get_mcdi_context(user_id)
# ← _detect_repetition() 호출 누락
# ← mcdi_context["latest_risk_level"] = "ORANGE" 승격 로직 누락
ai_response = await dialogue_manager.generate_response(...)
```

**결함 영향:**
- 반복 발화 사용자의 risk_level을 ORANGE로 승격하는 핵심 보호 로직이 작동하지 않음

**B3-4 추가 결함: `_check_probe_cooldown()` 데드코드**

**실제 코드 확인 (`kakao_webhook.py:542-569`):**
- `_check_probe_cooldown()` 함수가 정의되어 있음 ✅
- **하지만 grep 전체 코드 검증 결과: 호출부 0건** ❌ (데드코드)

**결함 영향:**
- 치매 탐침 질문 쿨다운이 작동하지 않음 → 동일 사용자에게 과도한 탐침 질문 가능
- B3 완료도 88% → 78%로 하향 조정

### C1-55% 상세: 비공식 구현

**실제 코드 확인 (`memory_manager.py:443-447`):**
```python
# Qdrant payload에 비공식적으로 필드 추가
payload = {
    "user_id": user_id,
    "content": memory.content,
    "metadata": {
        "samantha_emotion": analysis.get("samantha_emotion"),  # 비공식
        "follow_up_notes": analysis.get("follow_up_notes")     # 비공식
    }
}
```

하지만 `memory_extractor.py`의 `ExtractedMemory` 모델에는:
```python
class ExtractedMemory(BaseModel):
    # ...
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # samantha_emotion, follow_up_notes 필드 없음!
```

**결함 영향:**
- 타입 안전성 없이 dict로만 접근 가능
- IDE 자동완성 지원 안 됨
- 런타임 에러 위험

---

## ⚠️ SYSTEM_PROMPT 내부 모순 (GLM 추가 발견, 2026-03-27)

**`prompt_builder.py` SYSTEM_PROMPT 내부 충돌:**

| 라인 | 규칙 내용 | 문제 |
|------|-----------|------|
| **Line 185** | `"2. 이모지 절제적 사용 (1-2개/메시지)"` | 이모지 사용 허용 |
| **Line 200** | `"유니코드 이모지 사용 절대 금지"` | 이모지 사용 금지 |

**두 규칙이 상호 모순** → LLM이 어떤 규칙을 따를지 예측 불가

**해결:** Line 185의 `"이모지 절제적 사용"` 규칙을 삭제하거나 `"유니코드 이모지 사용 절대 금지"`와 통합

---

## ⚠️ A2 이모지 금지 규칙 vs 기존 코드 충돌 (GLM 추가 분석)

**SYSTEM_PROMPT (`prompt_builder.py:200-202`):**
```
- **유니코드 이모지 사용 절대 금지**: 😊 🌿 🎉 ❤️ 👍 등 유니코드 그림 이모지를 사용하지 마세요.
```

**하지만 실제 코드에서 다수 사용:**

| 파일 | 라인 | 이모지 사용 내용 | 노출 경로 | 심각도 |
|------|------|----------------|----------|--------|
| `time_aware.py` | 53-81 | 🌅🍁🌙✨ 등 gap 메시지 템플릿 | **사용자에게 직접 전달** | **높음** |
| `response_validator.py` | 304-308 | `variations = [" 🌱", ...]` | **사용자 응답에 결합** | **높음** |
| `response_generator.py` | 662-754 | 질문 템플릿 30개 중 대부분에 이모지 | 사용자에게 노출 가능 | **중간** |
| `dialogue_manager.py` | 747-752 | 교란 변수 질문에 🌙😊 사용 | 사용자에게 전달됨 | **중간** |

**해결 필요 사항:**
- A2 규칙의 적용 범위 명확화: "LLM 생성 응답"만 vs "시스템 전체"
- gap 메시지 템플릿 이모지를 ㅋㅋ/ㅠㅠ/ㅎㅎ 등으로 교체 필요 여부 결정

---

## 🏗️ Phase B1 — recovery_events 증가 로직 추가 (HIGH)

### 수정 위치: `core/dialogue/dialogue_manager.py::_update_relationship_stage()`

```python
# Line 905-913 근처 수정
async def _update_relationship_stage(
    self,
    user_id: str,
    emotion: Optional[str] = None
) -> int:
    """관계 Stage 업데이트 (B1-2: recovery_events 로직 추가)"""
    rel = await self._get_or_init_relationship(user_id)

    # 턴 수 증가
    rel["total_turns"] += 1
    rel["last_interaction"] = datetime.now().isoformat()

    # 대화 일수 계산
    first_dt = datetime.fromisoformat(rel["first_interaction"])
    rel["total_days"] = (datetime.now() - first_dt).days

    # 감정 이벤트 기록 (수정 필요)
    positive_emotions = ["기쁨", "행복", "감동", "설렘", "만족", "즐거움"]
    negative_emotions = ["우울", "슬픔", "불안", "짜증", "스트레스", "분노"]

    # 갈등 상태 추적 변수 초기화
    rel["_was_negative"] = rel.get("_was_negative", False)

    if emotion:
        if any(e in emotion for e in positive_emotions):
            rel["positive_events"] += 1
            # ========== 신규: 갈등 후 긍정 전환 감지 ==========
            if rel["_was_negative"]:
                rel["recovery_events"] += 1
                rel["_was_negative"] = False
                logger.info(
                    f"Recovery event detected for {user_id}",
                    extra={"recovery_count": rel["recovery_events"]}
                )
            # ===============================================
        elif any(e in emotion for e in negative_emotions):
            rel["conflict_events"] += 1
            rel["_was_negative"] = True  # 갈등 상태 표시

    # 저장
    key = f"relationship:{user_id}"
    await redis_client.set_json(key, rel)

    return new_stage
```

---

## 🏗️ Phase B2-7 — 감정 벡터 실제 호출 연결 (HIGH)

### 현황

**구현된 부분:**
- `dialogue_manager.py:45-68` → `EMOTION_VECTOR_MAP` 상수 ✅
- `dialogue_manager.py:986-1037` → `_update_emotion_vector()` 함수 ✅
- `prompt_builder.py:128-159` → `_vector_to_prompt_description()` 함수 ✅

**미구현된 부분:**
- `generate_response()` 메서드 내에서 `_update_emotion_vector()` 호출 ❌
- `response_generator` 호출 시 `emotion_vector` 파라미터 전달 ❌

### 구현 코드

**수정 위치:** `core/dialogue/dialogue_manager.py::generate_response()`

```python
async def generate_response(
    self,
    user_id: str,
    user_message: str,
    mcdi_context: Optional[Dict[str, Any]] = None,
    relationship_stage: Optional[int] = None
) -> str:
    """AI 응답 생성 (B2-7: 감정 벡터 갱신 추가)"""

    # 1. 감정 인식 (기존 NLP 또는 LLM 활용)
    emotion_label = await self._detect_emotion(user_message)

    # ========== B2-7: 감정 벡터 실제 갱신 (신규) ==========
    updated_vector = await self._update_emotion_vector(user_id, emotion_label)
    # =====================================================

    # 2. 관계 Stage 확인 (기존)
    stage = relationship_stage or await self._get_or_init_relationship(user_id)
    stage = stage.get("stage", 0)

    # 3. 사용자 컨텍스트 구성 (기존)
    session_data = await self.get_session(user_id)
    conversation_history = await self.get_conversation_history(user_id)
    user_context = session_data.get("context", {}) if session_data else {}

    # 4. 응답 생성 (emotion_vector 파라미터 추가)
    if emotion and emotion_intensity is not None:
        response = await self.response_generator.generate_empathetic_response(
            user_message=user_message,
            detected_emotion=emotion,
            emotion_intensity=emotion_intensity,
            conversation_history=conversation_history,
            user_context=user_context,
            mcdi_context=mcdi_context,
            relationship_stage=stage,
            emotion_vector=updated_vector  # B2-6: 갱신된 벡터 전달
        )
    else:
        response = await self.response_generator.generate(
            user_message=user_message,
            conversation_history=conversation_history,
            user_context=user_context,
            next_question=next_question,
            mcdi_context=mcdi_context,
            relationship_stage=stage,
            emotion_vector=updated_vector  # B2-6: 갱신된 벡터 전달
        )

    return response


# ========== 신규 헬퍼 함수 ==========
async def _detect_emotion(self, text: str) -> str:
    """간단 감정 인식 (B2-7)

    Returns:
        "joy", "sadness", "anger", "fear", "surprise", "neutral" 중 하나
    """
    # 방법 1: 키워드 기반 (빠름)
    emotion_keywords = {
        "joy": ["기쁘", "좋아", "행복", "즐겁", "신나", "ㅋㅋ", "ㅎㅎ"],
        "sadness": ["슬프", "우울", "쓸쓸", "외롭", "ㅠㅠ", "ㅜㅜ"],
        "anger": ["화나", "짜증", "속상", "억울", "미치"],
        "fear": ["무섭", "두렵", "걱정", "불안"],
        "surprise": ["놀라", "대박", "진짜", "정말"],
    }

    for emotion, keywords in emotion_keywords.items():
        if any(keyword in text for keyword in keywords):
            return emotion

    return "neutral"  # 기본값
```

### 검증 테스트

```python
# tests/test_dialogue/test_b2_7_emotion_vector_update.py
import pytest
from core.dialogue.dialogue_manager import DialogueManager

@pytest.mark.asyncio
async def test_b2_7_emotion_vector_called():
    """B2-7: generate_response()에서 감정 벡터가 갱신되어야 함"""
    manager = DialogueManager()

    # 기쁜 메시지 전송
    response = await manager.generate_response(
        user_id="test_user",
        user_message="딸이 방문해서 정말 기뻐요 ㅋㅋ"
    )

    # Redis에서 갱신된 벡터 확인
    vector = await manager.get_emotion_vector("test_user")

    assert vector is not None
    assert vector["v"] > 0.5  # 기쁨 → 긍정 valence
    assert vector["a"] > 0.5  # 기쁨 → 높은 arousal
```

---

## 🏗️ Phase B3-5 — 반복 발화 감지 연결 (HIGH)

### 현황

**구현된 부분:**
- `kakao_webhook.py:574-603` → `_detect_repetition()` 함수 ✅ 완벽히 구현됨

**미구현된 부분:**
- 웹훅 핸들러에서 함수 호출 ❌
- 반복 감지 시 mcdi_context["latest_risk_level"]을 ORANGE로 승격 ❌

### 구현 코드

**수정 위치:** `api/routes/kakao_webhook.py::post()` (메인 핸들러)

```python
# Line 820 직후에 추가
# B3-3: MCDI 컨텍스트 조회 후 응답 생성 (어댑티브 블록 활성화)
mcdi_context = await _get_mcdi_context(user_id)

# ========== B3-5: 반복 발화 감지 후 risk_level 승격 (신규) ==========
# 세션에서 최근 발화 가져오기
from collections import deque
session_data_tmp = await redis_client.get_json(f"session:{user_id}")
recent_mentions_raw = session_data_tmp.get("conversation_history", []) if session_data_tmp else []
recent_mentions = [turn.get("user", "") for turn in recent_mentions_raw if turn.get("user")]

# 반복 감지 시 risk_level을 임시 ORANGE로 승격
if _detect_repetition(user_message_for_save, recent_mentions):
    if mcdi_context and mcdi_context.get("has_data"):
        original_risk = mcdi_context.get("latest_risk_level", "GREEN")
        mcdi_context["latest_risk_level"] = "ORANGE"
        logger.info(
            f"Repetition detected, upgrading risk: {original_risk} → ORANGE",
            extra={"user_id": user_id}
        )
# ============================================================

ai_response = await dialogue_manager.generate_response(
    user_id=user_id,
    user_message=user_message_for_save,
    mcdi_context=mcdi_context
)
```

---

## 🏗️ Phase B4-4 — Gap 메시지 Prefixing (MEDIUM)

### 현황

**구현된 부분:**
- `time_aware.py:112-297` → `TimeAwareDialogue` 클래스 ✅
- `dialogue_manager.py:1062-1156` → 시간 인식 메서드들 ✅

**미구현된 부분:**
- 웹훅 핸들러에서 AI 응답 앞에 gap 메시지 붙이기 ❌

### 구현 코드

**수정 위치:** `api/routes/kakao_webhook.py::post()` (메인 핸들러)

```python
# AI 응답 생성 직후에 추가
ai_response = await dialogue_manager.generate_response(
    user_id=user_id,
    user_message=user_message_for_save,
    mcdi_context=mcdi_context
)

# ========== B4-4: Gap 메시지 Prefixing (신규) ==========
# 경과 시간 확인
gap_hours = await dialogue_manager.get_hours_since_last_interaction(user_id)

# 4시간 이상 경과 시 gap 메시지 추가
if gap_hours and gap_hours >= 4:
    gap_message = await dialogue_manager.generate_gap_message(user_id)

    if gap_message:
        # gap 메시지 + AI 응답 결합
        ai_response = f"{gap_message}\n\n{ai_response}"
        logger.info(
            f"Gap message prefixed: {gap_hours:.1f}h gap",
            extra={"user_id": user_id, "gap_hours": gap_hours}
        )
# =====================================================
```

---

## 🏗️ Phase C1 — 에피소드 기억 서사화 (~70% 부분 구현)

### C1-1. 데이터 클래스 확장 ⚠️

**현재 상태 (비공식 구현):**
```python
# core/memory/memory_manager.py:443-447 — 실제 저장 코드
payload = {
    "user_id": user_id,
    "content": memory.content,
    "metadata": {
        "samantha_emotion": analysis.get("samantha_emotion"),  # 비공식
        "follow_up_notes": analysis.get("follow_up_notes")     # 비공식
    }
}
```

**하지만 모델 정의에는 누락:**
```python
# core/memory/memory_extractor.py:85-93 — 현재 ExtractedMemory
class ExtractedMemory(BaseModel):
    memory_type: MemoryType
    content: str
    category: EntityCategory
    confidence: float
    importance: float
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # samantha_emotion, follow_up_notes 필드 없음!
```

**구현 필요 (정식 모델 확장):**
```python
class ExtractedMemory(BaseModel):
    memory_type: MemoryType
    content: str
    category: EntityCategory
    confidence: float
    importance: float
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # ========== 신규 필드 (C1-1) ==========
    samantha_emotion: Optional[str] = Field(None, description="사만다의 당시 감정")
    follow_up_notes: Optional[str] = Field(None, description="후속 화제")
    relationship_impact: float = Field(0.0, description="관계 영향도")
```

### C1-2. 저장 조건: 감정 강도 임계값 필터 ✅ 이미 구현됨

**상태:** `memory_manager.py:430-436` 및 `478-480` (Redis fallback)에 이미 구현됨

```python
# memory_manager.py:430-436 (실제 구현 코드)
if valence_intensity < 0.4 and memory.importance < 0.6:
    logger.debug(f"Skipped ordinary conversation: valence={valence:.2f}, importance={memory.importance:.2f}")
    continue
```

**검증:** valence_intensity < 0.4 이고 importance < 0.6 인 경우 저장 스킵 — 태스크 명세와 일치

### C1-3. follow_up_notes 백그라운드 생성 ⚠️

**목적:** 에피소드 저장 후 자연스럽게 꺼낼 수 있는 후속 화제 자동 생성

**현재 상태:**
- `memory_manager.py:332-389`에 `_extract_follow_up_topics()` 함수가 존재
- **하지만 LLM 미사용**: regex 패턴 매칭 기반 (태스크 명세와 차이)

**구현 필요 (LLM 사용):**
```python
async def _generate_follow_up_note(episode_content: str, user_id: str) -> str:
    """에피소드 저장 후 follow_up_notes 비동기 생성 (C1-3)"""
    from services.llm_service import LLMService

    prompt = f"""
다음 대화에서 사만다가 자연스럽게 꺼낼 수 있는 후속 화제를 1개 문장으로 생성하세요.

대화 내용: {episode_content}

후속 화제는 다음 조건을 만족해야 합니다:
1. 사용자가 기억에 남길 만한 중요한 요소
2. 나중에 "그때 말씀하신 ~ 기억나세요?"로 자연스럽게 꺼낼 수 있는 것
3. 구체적이고 개인적인 맥락

후속 화제:"""

    llm = LLMService()
    response = await llm.call(
        prompt=prompt,
        temperature=0.7,
        max_tokens=100
    )

    return response.strip()
```

### C1-5. Qdrant 스키마 마이그레이션 ❌

**목적:** 기존 에피소드 포인트에 신규 필드 추가

**구현 단계:**

1. **`database/qdrant_client.py`에 메서드 추가**
2. **마이그레이션 스크립트 생성** — `scripts/migrate_c1_episodic_fields.py`

---

## 🏗️ Phase C2 — 치매 탐지 신호 분산 삽입 전략

### C2-1. 주간 로테이션 스케줄 ❌

**목적:** 요일별로 다른 인지 도메인 질문을 삽입하여 편향 방지

**구현 위치:** `core/dialogue/prompt_builder.py` 또는 `core/dialogue/category_selector.py`

**구현 코드:**
```python
# 인지 도메인 주간 로테이션 스케줄 (C2-1)
DOMAIN_ROTATION = {
    0: ["LR", "ER"],  # 월요일
    1: ["TO", "NC"],  # 화요일
    2: ["SD"],        # 수요일
    3: ["LR", "TO"],  # 목요일
    4: ["ER", "NC"],  # 금요일
    5: ["SD", "LR"],  # 토요일
    6: ["TO", "ER"],  # 일요일
}

def _get_rotation_domains(today_weekday: int) -> List[str]:
    """요일별 로테이션 도메인 반환"""
    return DOMAIN_ROTATION.get(today_weekday, ["LR", "SD"])
```

### C2-2. 삽입 성공률 추적 ❌

**목적:** 인지 도메인 질문 삽입 후 사용자가 제대로 응답했는지 추적

**구현 위치:** `api/routes/kakao_webhook.py`

---

## 🏗️ Phase C5 — Proactive Messaging (먼저 말 걸기)

### C5-1. 카카오 Push API 조사 ❌

**목적:** 카카오워크 API vs 카카오 채널 알림톡 API 차이 확인 및 발신 방법 결정

### C5-2. 발송 조건 로직 ❌

**목적:** 36시간 이상 비활성 사용자에게 자동으로 메시지 발송

**구현 위치:** `services/proactive_service.py` (신규 파일)

### C5-3. 메시지 생성 함수 ❌

### C5-4. 검증 테스트 ❌

### C5-5. 스케줄러 등록 ❌

---

## 🚨 Phase S — 질문 패턴 재설계 (CRITICAL)

> **핵심 원칙:** Phase A/B1/B2/B3는 이미 완료된 상태. 추가 구현 없이
> **SYSTEM_PROMPT에 질문 빈도 제어 규칙 2개만 추가**하면 됨.

---

### S-1. 질문 빈도 제어 규칙 ⚠️ CRITICAL (5분)

**목적:** GPT-4o의 "공감 후 질문" 패턴을 제어

**구현 위치:** `core/dialogue/prompt_builder.py` - SYSTEM_PROMPT에 규칙 추가

**추가할 텍스트 (A3 망설임표현 규칙 다음에 추가):**
```python
"""
16. **질문 빈도 제어**:

   ⚠️ **질문은 선택 사항이며, 무조건 덧붙여서는 안 됩니다.**

   [질문을 피해야 하는 상황]
   - 사용자가 "피곤해", "힘들어", "쉬고싶어" 등 피로를 표현할 때
   - 사용자가 "질문이 많아", "또 질문이야" 등 불만을 표현할 때
   - 사용자가 짧게 대답할 때 ("응", "글쎄", "별로" 등 10자 이하)
   - 최근 3턴 연속으로 질문을 했을 때

   [질문을 해도 괜찮은 상황]
   - 사용자가 자발적으로 정보를 제공하며 대화가 활발할 때
   - 사용자의 반응이 긍정적이고 흥미로워 보일 때
   - 3턴 이상 질문을 하지 않았을 때

   [예시]
   ✅ 좋은 예: "쑥떡 기억이 나신다니 반가워요. 그때의 따뜻했던 기분이 떠오르네요." (질문 없이 멈춤)
   🚫 나쁜 예: "쑥떡 기억이 나시네요! 어떤 종류 쑥떡이셨나요?" (자동 질문)
   🚫 나쁜 예: "고기는 정말이지 그렇죠. 어떤 고기를 좋아하세요? 자주 드시나요?" (연속 질문)
"""
```

---

### S-2. 대화 종료 패턴 ⚠️ CRITICAL (5분)

**목적:** 피로 신호 시 자연스러운 대화 종료

**구현 위치:** `core/dialogue/prompt_builder.py` - SYSTEM_PROMPT에 종료 패턴 추가

**추가할 텍스트 (S-1 바로 다음):**
```python
"""
17. **대화 종료 패턴**:

   사용자가 다음과 같은 신호를 보낼 때 자연스럽게 대화를 마무리하세요:
   - "피곤해", "힘들어", "쉬고싶어", "잘 자"
   - "너무 질문이 많아", "그만 얘기하자"
   - "나갈게", "바쁘다", "할 일 있어"

   [종료 응답 예시]
   ✅ "그럼 편하게 쉬세요. 나중에 또 얘기해요."
   ✅ "네, 오늘은 여기까지 할게요. 푹 쉬세요."
   ✅ "알겠어요. 편안한 시간 보내세요."

   [종료 후 추가 질문 금지]
   🚫 "그럼 푹 쉬세요. 어떻게 쉬시나요?" (질문으로 끝나면 안 됨)
   🚫 "네, 좋은 밤 되세요. 내일 뭐 하세요?" (종료 의도 무시)
"""
```

---

### S-3. 검증 테스트 ❌ (30분)

**테스트 파일:** `tests/test_dialogue/test_s_question_patterns.py`

---

## 📋 구현 우선순위 (GLM 검증 반영, 최종)

### 🔥 CRITICAL (즉시 구현) - 2026-03-27 목표
1. **S-1**: 질문 빈도 제어 규칙 추가 (prompt_builder.py만, 5분)
2. **S-2**: 대화 종료 패턴 추가 (prompt_builder.py만, 5분)
3. **S-3**: 검증 테스트 작성 (30분)

**합계 예상 시간:** 약 40분

### 🔥 HIGH Priority (당일 구현 권장)
1. **B1 recovery_events**: 증가 로직 추가 (dialogue_manager.py, 5줄, 5분)
2. **B2-7**: 감정 벡터 호출 연결 (dialogue_manager.py, 15줄, 15분)
3. **B3-5**: 반복 감지 연결 (kakao_webhook.py, 8줄, 10분)
4. **C1-1**: 데이터 모델 정식 확장 (memory_extractor.py, 10분)
5. **C5-2, C5-3**: Proactive Messaging 핵심 (1-2시간)

### 🟡 MEDIUM Priority (조만간 구현)
1. **B4-4**: Gap 메시지 prefixing (kakao_webhook.py, 6줄, 10분)
2. **A2 이모지**: SYSTEM_PROMPT 모순 수정 (line 185 삭제) + time_aware.py 템플릿 수정 (30분)
3. **B3-4**: `_check_probe_cooldown()` 데드코드 정리 — 호출부 추가 또는 함수 삭제 (10분)
4. **C2-1**: 로테이션 스케줄 (prompt_builder.py, 30분)
5. **C1-3**: follow_up_notes LLM 기반 생성으로 교체 (1시간)

### 🔵 LOW Priority (이후 구현)
1. C1-4, C2-2, C5-4: 테스트
2. C4-2: 스케줄러 연동

---

## 🔧 구현 시 참고사항

### 공통 라이브러리
```python
# AsyncIO
import asyncio
from datetime import datetime, timedelta

# Database
from database.postgres import AsyncSessionLocal
from database.models import User
from sqlalchemy import select

# Redis
from database.redis_client import redis_client

# Qdrant
from database.qdrant_client import QdrantManager
```

### 에러 처리 패턴
```python
try:
    # 구현 로직
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    return {"success": False, "error": str(e)}
```

### 로깅 패턴
```python
logger.info(
    "Operation completed",
    extra={
        "user_id": user_id,
        "result": result
    }
)
```

---

*이 문서는 GLM 심층 코드 검증 결과를 반영하여 작성되었습니다 (2026-03-27 최종)*
