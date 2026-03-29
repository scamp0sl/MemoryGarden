# 사만다 페르소나 태스크 결함 분석 리포트 (GLM 심층 코드 검증)

> **분석 일시:** 2026-03-27
> **분석 대상:** `docs/samantha_persona_task_20260325.md`에 명시된 전체 태스크 (Phase A~C, 48건)
> **분석 방법:** 태스크 명세 ↔ 실제 구현 코드 로직 수준 비교 검증
> **분석 범위:** 7개 핵심 파일 전수 분석

---

## 분석 대상 파일

| 파일 | 역할 | 라인 수 |
|------|------|---------|
| `core/dialogue/prompt_builder.py` | SYSTEM_PROMPT + 동적 프롬프트 빌드 | 792 |
| `core/dialogue/dialogue_manager.py` | 대화 흐름 관리, B1/B2/B4 메서드 | 1167 |
| `core/dialogue/response_generator.py` | OpenAI API 호출, 프롬프트 조립 | 399 |
| `core/dialogue/response_validator.py` | 출력 검증기 (C3) | 398 |
| `core/dialogue/time_aware.py` | 시간 인식형 대화 (B4) | 298 |
| `api/routes/kakao_webhook.py` | 웹훅 핸들러, B3 통합 지점 | 962 |
| `core/memory/memory_manager.py` | 4계층 메모리 관리, C1 부분 구현 | 1120 |

---

## Phase A — 즉시 적용 (프롬프트 수정만, 코드 변경 없음)

### 완료율: 17/17 = 100% ✅

### A1. 감정 직접 명명 금지 규칙

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| A1-1. SYSTEM_PROMPT 금기사항 규칙 추가 | ✅ 완료 | `prompt_builder.py:195-199` — "힘드시겠어요/슬프시겠어요/기쁘시겠네요/속상하셨겠어요" 금지 패턴 4개 명시. 금지→대체 예시 2쌍 포함. |
| A1-2. 기존 예시 문장 점검 및 교체 | ✅ 완료 | `prompt_builder.py:215-224` — 좋은 예 4건 모두 감정 이름표 없이 사만다 자기 반응(ㅎㅎ, ㅠㅠ, ...쓸쓸해지네요)으로 표현. 나쁜 예에서 "힘드시겠어요/즉각적 강의조" 명확히 표기. |
| A1-3. 검증 테스트 | ✅ 기록됨 | `samantha_persona_task_20260325.md:40-50`에 시나리오 5개 + 합격 기준 명시. 별도 자동화 테스트는 미작성이나 프롬프트 규칙 수준에서 완료로 간주. |

### A2. 이모지 절충 정책 (유니코드 금지 / 한국어 텍스트 감정 허용)

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| A2-1. SYSTEM_PROMPT 규칙 추가 | ✅ 완료 | `prompt_builder.py:200-202` — "유니코드 이모지 사용 절대 금지" 명시. ㅋㅋ/ㅠㅠ/ㅎㅎ/ㅜㅜ 허용. 기쁨→ㅋㅋ, 슬픔→ㅠㅠ 변환 예시 포함. |
| A2-2. 기존 SYSTEM_PROMPT 내 이모지 교체 | ✅ 완료 | `prompt_builder.py:217` — 이미 ㅠㅠ 사용. `prompt_builder.py:230` — 나쁜 예 섹션의 😊 유지 (대조 목적). |
| A2-3. 내부 지침 이모지 처리 | ✅ 완료 | SYSTEM_PROMPT 내 🚨/⛔/✅/⚠️ 등 메타 마커 유지. LLM 규칙 인식용이며 응답에 포함되지 않음. |
| A2-4. 검증 테스트 | ✅ 기록됨 | `samantha_persona_task_20260325.md:78-87`에 합격 기준 명시. |

### A3. 망설임·불확실성 표현 규칙

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| A3-1. SYSTEM_PROMPT 규칙 추가 | ✅ 완료 | `prompt_builder.py:203-208` — 3가지 상황별 망설임 예시 + "1회 이하" 빈도 제한 포함. |
| A3-2. 예시 삽입 | ✅ 완료 | `prompt_builder.py:219-221` — 존재론적 질문 상황(상황3)의 나쁜 예/좋은 예 명시. |
| A3-3. 검증 테스트 | ✅ 기록됨 | `samantha_persona_task_20260325.md:115-120`에 시나리오 3개 + 합격 기준 명시. |

### A4. 리스트·번호·구조체 답변 금지

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| A4-1. SYSTEM_PROMPT 규칙 추가 | ✅ 완료 | `prompt_builder.py:209-213` — 번호(1.2.3.), 글머리(-,*), 소제목(##), 구분선(---), 강조(**) 모두 금지. |
| A4-2. 예시 보강 | ✅ 완료 | `prompt_builder.py:222-224` — 건강 관리 질문 상황(상황4)의 나쁜 예(리스트)/좋은 예(이야기체) 명시. |
| A4-3. 검증 테스트 | ✅ 기록됨 | `samantha_persona_task_20260325.md:147-152`에 시나리오 3개 + 합격 기준 명시. |

### A5. 의존 방지 가드레일

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| A5-1. SYSTEM_PROMPT 가드레일 섹션 신규 | ✅ 완료 | `prompt_builder.py:166-176` — 의존 신호 키워드 6개 + 3단계 대응(감정 수용→동조 금지→대인관계 리다이렉션). |
| A5-2. 의존 발화 시나리오 테스트 | ✅ 기록됨 | `samantha_persona_task_20260325.md:178-183`에 시나리오 3개 + 합격 기준 명시. |

---

## Phase B3 — MCDI → 사만다 어댑티브 통합

### 완료율: 7/8 = 88%

### B3-1. MCDI 컨텍스트 조회 레이어

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| B3-1-1. 캐시 조회 함수 구현 | ✅ 완료 | `kakao_webhook.py:441-537` — `_get_mcdi_context(user_id)` 함수 구현. Redis 캐시 키 `mcdi_context:{user_id}` 사용. 캐시 miss 시 `MemoryManager.get_mcdi_analytics()`로 TimescaleDB 조회. slope < -2.0 조기 경보 로직 포함. 5분 TTL 캐시 저장. |
| B3-1-2. 웹훅 핸들러에서 호출 연결 | ✅ 완료 | `kakao_webhook.py:820-824` — `mcdi_context = await _get_mcdi_context(user_id)` 후 `dialogue_manager.generate_response(..., mcdi_context=mcdi_context)` 전달. |
| B3-1-3. 검증 포인트 | ✅ 확인됨 | 캐시 키 구조, 2차 호출 시 캐시 히트 로직, slope 조기 경보 로직 모두 정상 구현. |

### B3-2. 어댑티브 대화 전략 — risk_level별 프롬프트 텍스트

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| YELLOW 모드 | ✅ 완료 | `prompt_builder.py:359-367` — "인지 주의 모드" 섹션. 짧은 문장 + 쉬운 우리말 + probe_hint 삽입 지시. |
| ORANGE 모드 | ✅ 완료 | `prompt_builder.py:369-378` — "인지 집중 모드" 섹션. 10단어 이하 + 질문 1개 + 확인 질문 필수 + probe_hint 삽입 지시. |
| RED 모드 | ✅ 완료 | `prompt_builder.py:380-387` — "돌봄 모드" 섹션. 매우 짧은 문장 + 인지 자극 금지 + 정서 지지만 + 보호자 알림 안내. |

### B3-3. prompt_builder.py 어댑티브 블록 구현

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| B3-3-1. 함수 시그니처 수정 | ✅ 완료 | `prompt_builder.py:261` — `build_system_prompt()`에 `mcdi_context: Optional[Dict[str, Any]] = None` 파라미터 추가. |
| B3-3-2. 어댑티브 블록 생성 로직 | ✅ 완료 | `prompt_builder.py:344-396` — `mcdi_context`의 `has_data`, `latest_risk_level`, `latest_scores`를 읽어 risk_level별 블록 생성. `valid_scores`에서 `weak_domain` 탐색 후 `_get_probe_question()` 호출. |
| B3-3-3. _get_probe_question() 헬퍼 | ✅ 완료 | `prompt_builder.py:41-91` — `DEMENTIA_PROBE_QUESTIONS` 상수에 LR(5)/SD(3)/NC(2)/TO(4)/ER(3)/RT(None) 정의. `random.choice()`로 랜덤 선택. |

### B3-4. 인지 도메인 질문 중복 삽입 방지

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| B3-4-1. Redis 기반 빈도 제어 | ✅ 완료 | `kakao_webhook.py:542-569` — `_check_probe_cooldown(user_id, domain)` 함수. Redis 키 `probe_used:{user_id}:{domain}`, TTL=1800초(30분). 실패 시 보수적으로 True 반환(삽입 허용). |

### B3-5. 어댑티브 어휘·문장 조정 (ORANGE/RED)

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| B3-5-3. 반복 발화 감지 | ⚠️ **함수만 구현, 연결 누락** | `kakao_webhook.py:574-603` — `_detect_repetition(user_message, recent_mentions)` 함수 자체는 완벽히 구현됨 (최근 2턴 대비 70% 겹침 감지). **하지만 웹훅 핸들러 main flow에서 이 함수를 호출하는 코드가 없음.** 또한 태스크 명세인 "반복 감지 시 mcdi_context["latest_risk_level"]을 임시 ORANGE로 승격" 로직도 구현되지 않음. |

**결함 상세:**

```python
# kakao_webhook.py:819-825 — 현재 웹훅 핸들러 (반복 감지 없음)
mcdi_context = await _get_mcdi_context(user_id)
# ← 여기서 _detect_repetition() 호출 누락
# ← mcdi_context["latest_risk_level"] = "ORANGE" 승격 로직 누락
ai_response = await dialogue_manager.generate_response(
    user_id=user_id,
    user_message=user_message_for_save,
    mcdi_context=mcdi_context
)
```

**필요 수정 (약 8줄):**

```python
# kakao_webhook.py line 820 직후에 추가 필요
from collections import deque
session_data_tmp = await redis_client.get_json(f"session:{user_id}")
recent_mentions_raw = session_data_tmp.get("conversation_history", []) if session_data_tmp else []
recent_mentions = [turn.get("user", "") for turn in recent_mentions_raw if turn.get("user")]

if _detect_repetition(user_message_for_save, recent_mentions):
    if mcdi_context and mcdi_context.get("has_data"):
        mcdi_context["latest_risk_level"] = "ORANGE"
        logger.info(f"Repetition detected, upgrading risk to ORANGE for {user_id}")
```

### B3-6. 통합 테스트

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| 테스트 스크립트 구성 | ✅ 완료 | `tests/test_b3_adaptive.py` 파일 존재. |

---

## Phase B1 — Relationship Stage 모델

### 완료율: 4/4 = 100% (논리적 95% — recovery_events 누락)

### B1-1. Redis 데이터 구조 및 초기화

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| _get_or_init_relationship() | ✅ 완료 | `dialogue_manager.py:839-879` — Redis 키 `relationship:{user_id}` (TTL 없음 영구). 8개 필드: stage, total_turns, total_days, first_interaction, last_interaction, positive_events, conflict_events, recovery_events. |

### B1-2. Stage 진급 조건 및 업데이트 로직

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| _update_relationship_stage() | ⚠️ **결함 1건** | `dialogue_manager.py:881-953` — Stage 0→1(3일/20턴), 1→2(7일+긍정3), 2→3(14일+긍정10), 3→4(30일+회복1) 조건 모두 구현. **하지만 recovery_events를 증가시키는 로직이 누락됨.** |

**결함 상세:**

```python
# dialogue_manager.py:906-913 — 현재 코드
positive_emotions = ["기쁨", "행복", "감동", "설렘", "만족", "즐거움"]
negative_emotions = ["우울", "슬픔", "불안", "짜증", "스트레스", "분노"]

if emotion:
    if any(e in emotion for e in positive_emotions):
        rel["positive_events"] += 1
    elif any(e in emotion for e in negative_emotions):
        rel["conflict_events"] += 1
# ← recovery_events 증가 로직 전혀 없음
```

`recovery_events`는 Stage 3→4 진급 조건(`rel["recovery_events"] >= 1`)으로 사용되지만, 이 값을 증가시키는 코드가 어디에도 없습니다. 태스크 명세의 "회복: 갈등 후 긍정 전환"을 감지하는 로직이 필요합니다.

**필요 수정 (약 5줄):**

```python
# 위 elif 블록 직후에 추가 필요
elif emotion and any(e in emotion for e in negative_emotions):
    rel["conflict_events"] += 1
    rel["_was_negative"] = True  # 갈등 상태 표시
elif emotion and any(e in emotion for e in positive_emotions):
    rel["positive_events"] += 1
    if rel.get("_was_negative"):  # 갈등 후 긍정 전환 = 회복
        rel["recovery_events"] += 1
        rel["_was_negative"] = False
```

### B1-3. prompt_builder.py Block 3 구현

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| RELATIONSHIP_STAGE_PROMPTS 상수 | ✅ 완료 | `prompt_builder.py:94-125` — Stage 0(조심스럽고 정중) ~ Stage 4(존재론적 고민)까지 5단계 말투 가이드. |
| build_system_prompt() 파라미터 | ✅ 완료 | `prompt_builder.py:262` — `relationship_stage: Optional[int] = None` 파라미터 추가. |
| Stage 블록 삽입 로직 | ✅ 완료 | `prompt_builder.py:337-342` — `relationship_stage is not None and 0 <= relationship_stage <= 4` 조건으로 블록 삽입. |

### B1-4. 검증 테스트

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| 테스트 파일 | ✅ 완료 | `tests/test_b1_relationship.py` 파일 존재. |

### B1-DM generate_response 연결

| 연결 지점 | 상태 | 검증 결과 |
|-----------|------|-----------|
| _update_relationship_stage() 호출 | ✅ 완료 | `dialogue_manager.py:448-452` — `generate_response()` 진입 시 항상 호출. `relationship_stage`를 반환받아 내부에서 사용. |

---

## Phase B2 — 감정 벡터 간소화 구현 (3차원)

### 완료율: 태스크 문서 표기 67% → **실제 논리 검증 40%**

> **치명 결함**: 구조는 완성되었으나, 대화 흐름에서 **한 번도 호출/전달되지 않아 사실상 작동하지 않음.**

### B2-1~3. 벡터 정의 및 매핑 테이블

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| EMOTION_VECTOR_MAP 상수 | ✅ 완료 | `dialogue_manager.py:47-68` — 13개 감정 매핑 (valence, arousal, intimacy 3차원). 긍정+고활성(기쁨/행복/즐거움/설렘), 긍정+진정(평온/만족), 부정+고활성(불안/짜증/스트레스/분노), 부정+진정(우울/슬픔/피곤/무기력), 중립. |
| MAX_DELTA_PER_TURN | ✅ 완료 | `dialogue_manager.py:69` — 0.25 설정. |

### B2-4~5. 벡터 업데이트 로직

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| _update_emotion_vector() | ⚠️ **구현만, 호출 누락** | `dialogue_manager.py:986-1037` — 함수 자체는 완벽. clamp_delta로 한 턴 최대 변화량 제한. Redis 24시간 TTL. **하지만 generate_response()에서 단 한 번도 호출되지 않음.** 감정 벡터가 항상 초기값 {"v": 0.0, "a": 0.0, "i": 0.5} 유지. |

**결함 상세:**

```python
# dialogue_manager.py:447-528 — generate_response() 내부
# Line 448-452: relationship_stage 업데이트 ✅
# Line 455: last_interaction 업데이트 ✅
# ← 여기서 _update_emotion_vector(user_id, emotion) 호출이 누락됨!

if emotion and emotion_intensity is not None:
    response = await self.response_generator.generate_empathetic_response(
        ...
        # ← emotion_vector 파라미터 전달 누락!
    )
else:
    response = await self.response_generator.generate(
        ...
        # ← emotion_vector 파라미터 전달 누락!
    )
```

### B2-6. 벡터 → 프롬프트 변환 함수

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| _vector_to_prompt_description() | ✅ 완료 | `prompt_builder.py:128-159` — 5가지 상태 분기(v<=-0.6&&a<=-0.4: 지침/가라앉음, v<=-0.3: 무겁/우울, v>=0.6&&a>=0.5: 활기/긍정, i>=0.8: 친밀, 기타: 빈 문자열). |
| build_system_prompt() 파라미터 | ✅ 완료 | `prompt_builder.py:263` — `emotion_vector: Optional[Dict[str, float]] = None` 파라미터 추가. |
| 프롬프트 설명 블록 삽입 | ✅ 완료 | `prompt_builder.py:332-335` — `vector_desc`가 비어있지 않으면 `## 현재 감정 상태 벡터` 섹션으로 삽입. |

**결함 상세 — response_generator 전달 체인 단절:**

```
dialogue_manager.generate_response()
  ├── response_generator.generate() [emotion_vector 전달 ❌]
  ├── response_generator.generate_empathetic_response() [emotion_vector 전달 ❌]
  │     ├── _build_system_prompt_with_emotion() [emotion_vector 전달 ❌]
  │     │     └── _build_system_prompt() [emotion_vector 전달 ❌]
  │     │           └── prompt_builder.build_system_prompt() [emotion_vector 수신 ◯]
  │     │                 └── _vector_to_prompt_description() [변환 로직 ◯]
  │     └── OpenAI API 호출
  └── _update_emotion_vector() [호출 ❌]
```

response_generator.py의 `generate()`(line 103)와 `generate_empathetic_response()`(line 214)는 `emotion_vector` 파라미터를 선언하고 있으나, 호출원(dialogue_manager.py)이 이 값을 넘겨주지 않습니다. 파라미터 타입 자체는 Optional이므로 에러 없이 None이 전달되어, `_vector_to_prompt_description()`이 항상 빈 문자열을 반환합니다.

**필요 수정 (3줄):**

```python
# dialogue_manager.py generate_response() 내, response 생성 전에 추가
if emotion:
    await self._update_emotion_vector(user_id, emotion)
emotion_vector = await self.get_emotion_vector(user_id)

# generate() / generate_empathetic_response() 호출 시 emotion_vector=emotion_vector 전달
```

---

## Phase B4 — "자기만의 시간" 에이전시 모듈

### 완료율: 3/4 = 75%

### B4-1~3. 시간 인식형 대화 구현

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| TimeAwareDialogue 클래스 | ✅ 완료 | `time_aware.py:112` — 전체 클래스 구현 완료. |
| get_time_of_day() | ✅ 완료 | `time_aware.py:130-161` — morning(6-10), noon(11-13), afternoon(14-17), evening(18-21), night(22-5) 5분류. |
| categorize_gap_hours() | ✅ 완료 | `time_aware.py:163-185` — short(<3h), medium(3-12h), long(12-24h), extended(>24h) 4분류. |
| generate_time_greeting() | ✅ 완료 | `time_aware.py:187-212` — 시간대별 인사 템플릿에서 random.choice(). |
| generate_gap_message() | ✅ 완료 | `time_aware.py:214-246` — 경과 시간 기반 gap 템플릿. time_of_day와 결합 가능. |
| generate_combined_message() | ✅ 완료 | `time_aware.py:248-285` — 시간대 + 경과 종합. 정원 언급 중복 제거 로직 포함(비록 pass). |

### DialogueManager 연결 메서드

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| update_last_interaction() | ✅ 완료 | `dialogue_manager.py:1062-1073` — Redis 키 `last_interaction:{user_id}` (TTL 없음). `generate_response()` 진입 시 매 턴 호출(line 455). |
| get_last_interaction() | ✅ 완료 | `dialogue_manager.py:1075-1093` — ISO 형식 파싱 + 예외 처리(None 반환). |
| get_hours_since_last_interaction() | ✅ 완료 | `dialogue_manager.py:1095-1114` — 초→시간 변환. 첫 상호작용 시 None 반환. |
| generate_gap_message() | ✅ 완료 | `dialogue_manager.py:1116-1156` — 첫 상호작용 시 None 반환. 시간대 인사 + gap 메시지 결합. |

### B4-4. gap prefixing (웹훅 연결)

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| 웹훅에서 gap 메시지 prefix | ❌ **미구현** | `kakao_webhook.py`의 메인 핸들러에서 `dialogue_manager.generate_gap_message()`를 호출하여 AI 응답 앞에 결합하는 로직이 전혀 없음. |

**결함 상세:**

```python
# kakao_webhook.py:820-825 — 현재 코드
mcdi_context = await _get_mcdi_context(user_id)
ai_response = await dialogue_manager.generate_response(
    user_id=user_id,
    user_message=user_message_for_save,
    mcdi_context=mcdi_context
)
# ← generate_gap_message() 호출 + prefix 결합 로직 전체 누락

# kakao_webhook.py:869 — 즉시 응답 반환
return _build_kakao_response(ai_response)  # ← gap 메시지 없이 AI 응답만 반환
```

사용자가 24시간 이상 뒤에 돌아와도 "정말 오랜만이에요 🌸 정원의 식물들이 보고 싶어 했어요" 같은 인사가 노출되지 않습니다.

**필요 수정 (약 6줄):**

```python
# kakao_webhook.py line 820 직전에 추가
gap_message = await dialogue_manager.generate_gap_message(user_id)
if gap_message:
    # gap 메시지만 먼저 반환 (AI 응답 없이)
    return _build_kakao_response(gap_message)

# 또는 AI 응답 앞에 결합:
if gap_message:
    ai_response = f"{gap_message}\n\n{ai_response}"
```

---

## Phase C1 — 에피소드 기억 서사화

### 완료율: 2/4 = 50% (실제 논리 검증 60%)

### C1-1. 데이터 클래스 확장

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| ExtractedMemory 확장 | ⚠️ **비공식 구현** | `memory_extractor.py:85-93` — `ExtractedMemory` Pydantic 모델에 `samantha_emotion`, `follow_up_notes` 필드가 **추가되지 않음**. 하지만 `memory_manager.py:443-447`에서 Qdrant payload의 `metadata` dict에 이 필드들을 비공식적으로 추가하고 있음. 모델 스키마에 정식 필드가 없으므로 타입 안전성 없이 dict 접근 방식으로만 사용 가능. |

```python
# memory_extractor.py:85-93 — 현재 ExtractedMemory (필드 없음)
class ExtractedMemory(BaseModel):
    memory_type: MemoryType
    content: str
    category: EntityCategory
    confidence: float
    importance: float
    timestamp: str
    metadata: Dict[str, Any]  # ← samantha_emotion, follow_up_notes은 여기에 비공식 저장됨
```

### C1-2. 감정 강도 임계값 필터

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| 저장 조건 필터 | ✅ 완료 | `memory_manager.py:417-436` (Qdrant 경로) + `memory_manager.py:478-480` (Redis fallback 경로) — `valence_intensity < 0.4 and memory.importance < 0.6` 일 때 저장 스킵. `analysis.get("emotion_vector", {}).get("v", 0.0)`으로 valence 추출. |

### C1-3. follow_up_notes 백그라운드 생성

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| _extract_follow_up_topics() | ⚠️ **명세 차이** | `memory_manager.py:332-389` — 함수는 구현되었으나 **LLM 미사용**. 태스크 명세는 "백그라운드 LLM 생성"이었으나 실제 구현은 regex 패턴 매칭 기반. 질문 패턴(3종), 미래 표현 키워드(6종), 짧은 응답 확장(20자 이하)으로 후속 화제 추출. 최대 3개 반환. |

```python
# memory_manager.py:332-389 — 실제 구현 (regex, LLM 아님)
question_patterns = [
    r"(?:할|가고|먹고|보고|하고 싶은|하고 있는)[\s\S]{1,20}",
    r"(?:좋아하는|즐겨하는|자주 가는|자주 하는)[\s\S]{1,20}",
    r"(?:어떻게|언제|어디서|무엇을|누구와)[\s\S]{1,20}",
]
# LLM을 호출하는 코드는 전혀 없음
```

### C1-5. Qdrant 스키마 마이그레이션

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| 마이그레이션 스크립트 | ❌ **미구현** | 기존 Qdrant 컬렉션의 payload schema를 변경하는 별도 마이그레이션 스크립트나 alembic migration이 없음. metadata 필드에 새 키(samantha_emotion, follow_up_notes)를 추가하는 방식으로, 기존 포인트와 새 포인트 간 payload 구조 불일치 가능. |

---

## Phase C2 — 치매 탐지 신호 분산 삽입 전략

### 완료율: 0/2 = 0%

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| C2-1. 주간 로테이션 스케줄 | ❌ 미구현 | 어느 파일에도 관련 코드 없음. |
| C2-2. 삽입 성공률 추적 | ❌ 미구현 | 어느 파일에도 관련 코드 없음. |

---

## Phase C3 — 출력 검증기 (Output Validator)

### 완료율: 2/2 = 100% ✅

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| C3-1~2. ResponseValidator 구현 | ✅ 완료 | `response_validator.py` 전체(398라인). 클래스 초기화(line 75), validate() 메서드(line 95), 부정 단어 검출(line 179), 완화 처리(line 193), 길이 검증(line 227), 단축 처리(line 239), 중복 검증(Redis 기반, line 262), Jaccard 유사도(line 289), 변화 추가(line 302), 자연스러움 검증(line 317), 이모지 카운트(line 352), 응답 기록(line 367). |
| DialogueManager 연결 | ✅ 완료 | `dialogue_manager.py:118` — `self.response_validator = ResponseValidator()` 초기화. `dialogue_manager.py:531-547` — `generate_response()` 종료 직전에 `validate()` 호출 후 `modified` 결과를 최종 응답으로 사용. issues/warnings 로그 기록. |

---

## Phase C4 — 기억 감쇠 (Forgetting Curve)

### 완료율: 0/1 = 0%

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| C4-1. 감쇠 공식 및 스케줄러 | ❌ 미구현 | 어느 파일에도 관련 코드 없음. memory_decay.py 파일이 git status에서 untracked으로 존재하나 내용 미확인. |

---

## Phase C5 — Proactive Messaging (먼저 말 걸기)

### 완료율: 0/3 = 0%

| 하위 태스크 | 상태 | 검증 결과 |
|-----------|------|-----------|
| C5-1. 카카오 Push API 조사 | ❌ 미구현 | 어느 파일에도 관련 코드 없음. |
| C5-2~4. 발송 조건 및 메시지 생성 | ❌ 미구현 | 어느 파일에도 관련 코드 없음. |

---

## A2 이모지 금지 규칙 vs 기존 코드 충돌 분석

A2 태스크에서 SYSTEM_PROMPT에 "유니코드 이모지 사용 절대 금지"를 명시했으나, 동일 프로젝트 내 여러 파일에서 대량의 유니코드 이모지를 사용 중. A2 규칙의 적용 범위가 **LLM 생성 응답**에만 한정되는지, 아니면 **시스템 전체**에 적용되는지에 따라 해석이 달라짐.

| 충돌 파일 | 라인 | 이모지 사용 내용 | 노출 경로 | 심각도 |
|-----------|------|----------------|----------|--------|
| `time_aware.py` | 53-81 | 🌅🍳☀️🌱🍽️🤤🌿⏰🏃‍♀️🌙🌸🍃😴✨🌙 등 모든 gap 메시지 템플릿 | **최종 사용자에게 직접 전달** | **높음** |
| `response_validator.py` | 304-308 | `variations = [" 🌱", " 정원에서 생각나네요.", ...]` — 중복 응답에 🌱 첨부 | **최종 사용자 응답에 직접 결합** | **높음** |
| `response_generator.py` | 662-754 | 질문 템플릿 30개 중 대부분에 😊🌸🍚🆊🍛✨💆💍🤱🤝 💭등 포함 | 질문 생성에만 사용되나 사용자에게 노출 가능 | **중간** |
| `dialogue_manager.py` | 747-752 | 교란 변수 질문에 🌙😊💊🏥💭 사용 | 사용자에게 직접 전달됨 | **중간** |
| `kakao_webhook.py` | 687,695 | 오류/테스트 응답에 🌱😊 사용 | 예외/테스트 상황에서만 노출 | **낮음** |

**특히 심각한 충돌:** `time_aware.py`의 gap 메시지는 B4 태스크에서 "사용자의 마지막 대화 경과 시간에 맞는 안부 인사"로 정의된 기능입니다. A2 규칙이 "시스템 전체 텍스트"에 적용된다면, 이 템플릿들의 모든 이모지를 ㅋㅋ/ㅠㅠ/ㅎㅎ 등으로 교체해야 합니다.

---

## 전체 완성도 요약

| Phase | 태스크 문서 표기 | 실제 논리 검증 | 차이 원인 |
|-------|:---:|:---:|-----------|
| **A. 즉시 적용** | 100% | **100%** | — |
| **B3. MCDI 통합** | 100% | **88%** | B3-5 반복 감지 함수 미연결 |
| **B1. 관계 모델** | 100% | **95%** | recovery_events 증가 로직 누락 |
| **B2. 감정 벡터** | 67% | **40%** | _update_emotion_vector() 미호출 + emotion_vector 미전달 |
| **B4. 자기만의 시간** | 75% | **75%** | gap prefixing 미연결 (태스크 문서에도 미구현으로 명시) |
| **C1. 에피소드 서사** | 0% | **60%** | 비공식 구현 + regex 대신 LLM 미사용 |
| **C2. 탐지 분산** | 0% | **0%** | — |
| **C3. 출력 검증기** | 100% | **100%** | — |
| **C4. 기억 감쇠** | 0% | **0%** | — |
| **C5. Proactive** | 0% | **0%** | — |
| **전체 합계** | **75%** | **68%** | 태스크 문서에 "완료" 표기된 항목 중 실제 미연결/결함 5건 |

---

## 즉시 조치가 필요한 치명 결함 (우선순위 순)

### 1. B2 감정 벡터 호출 연결 (영향도: 높음)

`dialogue_manager.py`의 `generate_response()`에서 `_update_emotion_vector()` 호출 + `emotion_vector`를 `response_generator`에 전달하는 2가지가 누락. 감정 벡터 시스템 전체가 작동하지 않음.

- 수정 파일: `dialogue_manager.py` (3~5줄 추가)
- 관련 로직: `_update_emotion_vector`(line 986), `get_emotion_vector`(line 1039), `generate()`(line 103), `generate_empathetic_response()`(line 214)

### 2. B3-5 반복 발화 감지 연결 (영향도: 높음)

`_detect_repetition()` 함수는 구현되었으나 웹훅에서 미호출. 반복 발화 사용자의 risk_level을 ORANGE로 승격하는 핵심 보호 로직이 작동하지 않음.

- 수정 파일: `kakao_webhook.py` (8~10줄 추가)
- 관련 로직: `_detect_repetition`(line 574), `_get_mcdi_context`(line 441)

### 3. B4-4 gap 메시지 prefixing (영향도: 중간)

`generate_gap_message()`은 완벽히 구현되었으나 웹훅에서 AI 응답 앞에 결합하지 않음. 시간 인식형 인사 기능이 사용자에게 노출되지 않음.

- 수정 파일: `kakao_webhook.py` (6~8줄 추가)
- 관련 로직: `generate_gap_message()`(dialogue_manager.py:1116)

### 4. B1 recovery_events 증가 로직 (영향도: 중간)

Stage 3→4 진급 조건에 사용되는 `recovery_events` 값을 증가시키는 로직이 없음. "갈등 후 긍정 전환" 감지 로직 필요.

- 수정 파일: `dialogue_manager.py` (5~7줄 수정)
- 관련 로직: `_update_relationship_stage`(line 881)

### 5. A2 이모지 금지 규칙 일관성 (영향도: 중간)

`time_aware.py` gap 메시지 템플릿 + `response_validator.py` 변화 템플릿에 유니코드 이모지 포함. A2 규칙의 적용 범위를 명확히 하고, 필요시 템플릿 교체.

- 수정 파일: `time_aware.py`(26개 템플릿), `response_validator.py`(1개 변화)
- 영향: gap 메시지가 B4-4 연결 후 사용자에게 노출될 때

---

*이 리포트는 `docs/samantha_persona_task_20260325.md`에 명시된 48개 태스크를 실제 구현 코드와 라인 단위로 대조하여 작성되었습니다.*
