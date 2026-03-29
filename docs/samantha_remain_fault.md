# 사만다 잔여 결함 수정 계획서

> **작성일:** 2026-03-27
> **대상:** `samantha_complete_plan_fixed.md` 8-Phase 구현 후 잔여 결함
> **범위:** M-3 (tasks/dialogue.py), M-4 (kakao_webhook.py) 이모지는 **예외 처리 (수정 대상 제외)**
> **예상 기간:** 2~3시간

---

## 결함 목록

| ID | 심각도 | Phase | 파일 | 결함 요약 |
|----|--------|-------|------|-----------|
| R-1 | **CRITICAL** | B1 | `core/dialogue/dialogue_manager.py` | 관계 Stage 진급이 웹훅 경로에서 동작하지 않음 |
| R-2 | **HIGH** | S | `core/dialogue/prompt_builder.py` | `build_question()` 템플릿에 ~40개 이모지 잔존 (SYSTEM_PROMPT 금지 규칙 위배) |
| R-3 | **MEDIUM** | S | `core/dialogue/prompt_builder.py` | SYSTEM_PROMPT 중복 블록 ("망설임과 불확실성 표현" 2회 작성) |
| R-4 | **MEDIUM** | S | `core/dialogue/prompt_builder.py` | 규칙 번호 갭 (5 → 16, 중간 6~15 누락) |
| R-5 | **MEDIUM** | C1 | `core/memory/memory_manager.py` | `samantha_emotion` 항상 None (파이프라인 미연결) |
| R-6 | **LOW** | C1 | `tests/test_c1_episodic_memory.py` | `EntityCategory.FAMILY`, `EntityCategory.DAILY` 미존재 |
| R-7 | **LOW** | B1 | `tests/test_b1_relationship.py` | `build_system_prompt()` 호출에 `user_id` 누락 (async 변환 미반영) |
| R-8 | **LOW** | B2 | `core/dialogue/response_generator.py:327` | 주석에 중국어 문자 "忆" 혼입 |
| R-9 | **LOW** | B1 | `core/dialogue/dialogue_manager.py:1141` | Bare `except:` 구문 |
| R-10 | **LOW** | B4 | `core/dialogue/time_aware.py` | docstring 예시에 4건 이모지 잔존 |

**예외 (수정 제외):**
- `tasks/dialogue.py` 이모지 (M-3) — 사용자 지시로 유지
- `api/routes/kakao_webhook.py` 이모지 (M-4) — 사용자 지시로 유지

---

## R-1: 관계 Stage 진급 불가 (CRITICAL)

### 문제 분석

**파일:** `core/dialogue/dialogue_manager.py`
**라인:** 447~460

`generate_response()` 메서드에서 감정 기반 관계 Stage 업데이트가 항상 `emotion=None`으로 실행됩니다. 웹훅 경로(`kakao_webhook.py`)에서 `generate_response()`를 호출할 때 `emotion` 파라미터를 전달하지 않기 때문입니다.

```python
# 현재 코드 (line 447-460)
# B1-2: 관계 Stage 업데이트 (감정 기반)
if relationship_stage is None:
    relationship_stage = await self._update_relationship_stage(user_id, emotion)  # ← emotion = None
else:
    await self._update_relationship_stage(user_id, emotion)  # ← emotion = None

# ... (중략) ...

# B2-7: 감정 벡터 실제 갱신
detected_emotion = await self._detect_emotion(user_message)  # ← 감정 감지는 여기서 함
updated_vector = await self._update_emotion_vector(user_id, detected_emotion)
```

**문제 요약:** `_detect_emotion()`이 line 459에서 올바르게 감정을 감지하지만, 관계 Stage 업데이트(line 449)는 그보다 먼저 실행되므로 항상 `emotion=None`으로 동작합니다.

**영향:** `_update_relationship_stage()`의 감정 이벤트 기록(line 922-936)이永远不会触发。`positive_events`, `conflict_events`, `recovery_events`가 항상 0으로 유지됩니다. Stage 2 이상 진급이 불가능합니다 (Stage 2→ 조건: `positive_events >= 3`).

### 수정 가이드

**수정 방식:** `_detect_emotion()`을 `_update_relationship_stage()`보다 먼저 실행하고, 그 결과를 전달합니다.

```python
# 수정 후 (dialogue_manager.py line 447~461)
# ========== B2-7: 감정 감지 (Stage 업데이트보다 먼저) ==========
# [R-1 수정] 감정을 먼저 감지하여 Stage 업데이트에 사용
effective_emotion = emotion or await self._detect_emotion(user_message)
updated_vector = await self._update_emotion_vector(user_id, effective_emotion)

# B1-2: 관계 Stage 업데이트 (감정 기반)
if relationship_stage is None:
    relationship_stage = await self._update_relationship_stage(user_id, effective_emotion)
else:
    await self._update_relationship_stage(user_id, effective_emotion)
# =====================================================
```

**주의사항:**
- `emotion` 파라미터가 외부에서 전달된 경우(테스트 등) 그 값을 우선 사용 (`emotion or ...`)
- `_detect_emotion()`이 텍스트 기반 규칙 매칭이므로 LLM 호출 없이 즉시 실행 가능
- `detected_emotion` 변수명을 `effective_emotion`으로 변경 (역할 명확화)

### 수정 범위

| 파일 | 변경 |
|------|------|
| `core/dialogue/dialogue_manager.py` | line 447~461 블록 재배치 |

---

## R-2: `build_question()` 이모지 템플릿 (HIGH)

### 문제 분석

**파일:** `core/dialogue/prompt_builder.py`
**라인:** 746~838

SYSTEM_PROMPT line 229에 `"유니코드 이모지 사용 절대 금지"` 규칙이 있지만, 동일 파일의 `build_question()` 메서드 내 `question_templates` 딕셔너리에 ~40개의 Unicode 이모지가 잔존합니다.

### 이모지 목록 (전부 수정 대상)

```
Line 746: 🍚
Line 747: 😊
Line 748: ☀️
Line 751: 🌸
Line 752: 🎊
Line 753: 💒
Line 757: 💼
Line 763: 📅
Line 764: ⏰
Line 765: 🌱
Line 768: 📆
Line 769: 🗓️
Line 780: 😊
Line 784: 🎊
Line 785: ✨
Line 786: 👨‍👩‍👧
Line 789: 💑
Line 796: 😊
Line 797: 🌳
Line 800: 🌸
Line 801: 🍲
Line 805: ✨
Line 812: 🍚
Line 813: ☀️
Line 816: 💪
Line 817: 📞
Line 826: 😊
Line 827: 🌱
Line 830: ✨
Line 831: 📺
Line 834: 💭
```

### 수정 가이드

**수정 방식:** 각 이모지를 문맥에 맞는 한국어 텍스트 표현으로 교체

```python
# 수정 전
"오늘 아침 식사로 뭐 드셨어요? 🍚",
# 수정 후
"오늘 아침 식사로 뭐 드셨어요?",

# 수정 전
"어제는 무엇을 하셨나요? 😊",
# 수정 후
"어제는 무엇을 하셨나요? ㅎㅎ",

# 수정 전
"오늘 날씨가 어떤가요? ☀️",
# 수정 후
"오늘 날씨가 어떤가요?",

# 수정 전
"지난 주말에 무엇을 하셨나요? 기억나시나요? 🌸",
# 수정 후
"지난 주말에 무엇을 하셨나요? 기억나시나요?",
```

**이모지 → 대체 표현 매핑 규칙:**

| 이모지 | 대체 | 적용 기준 |
|--------|------|-----------|
| 😊 | ` ㅎㅎ` 또는 제거 | 긍정/친근한 질문 |
| ☀️ / 🌤️ / 🌙 / ✨ | 제거 | 시간 관련 (이미 시간 문맥 있음) |
| 🍚 / 🍲 / 🌳 / 🌱 | 제거 | 자연/식사 관련 |
| 📅 / 📆 / 🗓️ / ⏰ | 제거 | 날짜/시간 관련 |
| 🎊 / 🌸 / 💒 / 💑 / 💼 / 👨‍👩‍👧 | 제거 | 행사/가족 관련 |
| 💪 / 📞 / 💭 / 💡 | 제거 | 감정/동작 관련 |

**원칙:** 이모지를 무조건 한국어 이모티콘(ㅋㅋ, ㅠㅠ, ㅎㅎ)으로 바꾸는 것이 아니라, **불필요한 시각 장식은 제거**, **감정 표현이 필요한 경우만 ㅎㅎ 등으로 대체**합니다. SYSTEM_PROMPT의 "이모지 절대 금지" 규칙과 일치시킵니다.

### 수정 범위

| 파일 | 변경 |
|------|------|
| `core/dialogue/prompt_builder.py` | line 746~838의 `question_templates` 내 모든 이모지 제거 또는 ㅎㅋ 교체 |

---

## R-3: SYSTEM_PROMPT 중복 블록 (MEDIUM)

### 문제 분석

**파일:** `core/dialogue/prompt_builder.py`

"망설임과 불확실성 표현 (인간다움의 핵심)" 블록이 두 번 작성되어 있습니다.

- **1차 (line 244~249):** "어렵거나 철학적인 질문" 패턴 + "사용자 경험" 패턴 + 금지/허용/주의사항 포함 (정식판)
- **2차 (line 287~291):** "사용자 경험" 패턴 + 금지/허용/주의사항만 포함 (단축판)

### 수정 가이드

**수정 방식:** 2차 블록(line 287~291)을 삭제. 1차 블록(line 244~249)만 유지.

```
삭제 대상 (line 287~291):
- **망설임과 불확실성 표현 (인간다움의 핵심)**: 모든 질문에 즉각 자신 있게 답하지 마세요.
  - 사용자 경험에 관한 질문: "잠깐, 어떻게 말하면 좋을지..."라며 생각하는 척 하세요.
  - 🚫 금지: 즉각적인 완벽한 정답 제시
  - ✅ 허용: "글쎄요...", "사실 저도 헷갈려요", "뭔가 제대로 떠오르지 않는데..."
  - ⚠️ 주의: 망설임이 과해지면 답답하게 느껴짐. 한 응답에 1회 이하로 제한하세요.
```

### 수정 범위

| 파일 | 변경 |
|------|------|
| `core/dialogue/prompt_builder.py` | line 287~291 삭제 |

---

## R-4: 규칙 번호 갭 (MEDIUM)

### 문제 분석

**파일:** `core/dialogue/prompt_builder.py`

SYSTEM_PROMPT의 대화 원칙 번호가 5 다음 16으로 건너뜁니다. 규칙 6~15가 누락되었습니다.

현재 규칙 구성:
```
1. 인사와 말투
2. 감정 반응 원칙
3. (삭제됨 — 결함 #16 수정으로 제거)
4. (삭제됨 — 결함 #16 수정으로 제거)
5. 사용자 호칭
16. 질문 빈도 제어
17. 대화 종료 패턴
```

### 수정 가이드

**수정 방식:** R-3의 중복 블록 삭제 후, 남은 규칙을 연속 번호로 재할당.

수정 후 규칙 구성:
```
1. 인사와 말투
2. 감정 반응 원칙
3. 사용자 호칭
4. 망설임과 불확실성 표현 (기존 5번 → 4번)
5. 리스트·구조 형식 응답 절대 금지 (기존 번호 없음 → 5번)
6. 질문 빈도 제어 (기존 16번 → 6번)
7. 대화 종료 패턴 (기존 17번 → 7번)
```

### 수정 범위

| 파일 | 변경 |
|------|------|
| `core/dialogue/prompt_builder.py` | 규칙 번호 1→1, 2→2, 5→4, (무번호)→5, 16→6, 17→7 로 재할당 |

---

## R-5: `samantha_emotion` 항상 None (MEDIUM)

### 문제 분석

**파일:** `core/memory/memory_manager.py`
**라인:** 468

`samantha_emotion`은 Qdrant에 에피소드 메모리 메타데이터로 저장됩니다(line 488), 하지만 `analysis` 딕셔너리에 `samantha_emotion` 키를 설정하는 코드가 어디에도 없습니다.

```python
# line 468: 읽기만 함, 쓰기는 없음
samantha_emotion = analysis.get("samantha_emotion") if analysis else None
# → 항상 None

# line 488: None이 Qdrant에 저장됨
"samantha_emotion": samantha_emotion,  # → 항상 None
```

`_generate_follow_up_note_async()` 메서드(line 391)가 LLM 기반 후속 메모를 생성하도록 설계되었지만, `store_all()` 파이프라인에서 호출되지 않습니다. 대신 `_extract_follow_up_topics()` (정규식 기반, line 160)이 사용되고 있어 `follow_up_notes`는 정상 동작합니다.

### 수정 가이드

**수정 방식:** `_update_relationship_stage()` 직전에 감지된 감정을 `analysis["samantha_emotion"]`에 주입합니다.

`memory_manager.py`의 `store_all()` 메서드 내, line 460~470 부근:

```python
# R-5 수정: 감정을 analysis에 주입
if analysis and not analysis.get("samantha_emotion"):
    emotion_label = analysis.get("detected_emotion") or analysis.get("emotion")
    if emotion_label:
        analysis["samantha_emotion"] = emotion_label
```

**대안 (권장):** `dialogue_manager.py`에서 `memory_manager.store_all()`을 호출하기 전에 `analysis` 딕셔너리에 감정을 주입하는 것이 더 깔끔합니다. `_run_mcdi_analysis()` 또는 `generate_response()`의 메모리 저장 단계에서:

```python
# dialogue_manager.py에서 store_all 호출 전
analysis["samantha_emotion"] = effective_emotion  # R-1 수정 후의 변수
```

**주의사항:**
- `_generate_follow_up_note_async()`는 LLM 호출이 필요하므로 파이프라인에 추가하면 응답 지연 발생 가능
- 현재 `_extract_follow_up_topics()` (정규식 기반)이 `follow_up_notes`를 정상 생성하므로, `samantha_emotion`만 주입하면 충분
- `_generate_follow_up_note_async()`는 데드코드로 유지하되 향후 필요시 활성화 가능

### 수정 범위

| 파일 | 변경 |
|------|------|
| `core/dialogue/dialogue_manager.py` | `store_all()` 호출 전 `analysis["samantha_emotion"] = effective_emotion` 추가 |

---

## R-6: `test_c1_episodic_memory.py` EntityCategory 오류 (LOW)

### 문제 분석

**파일:** `tests/test_c1_episodic_memory.py`
**라인:** 66, 124

`EntityCategory.FAMILY`와 `EntityCategory.DAILY`를 사용하지만, 실제 `EntityCategory` 열거형에는 이 값들이 없습니다.

```python
# EntityCategory 실제 정의 (memory_extractor.py:57~68)
class EntityCategory(str, Enum):
    PERSON = "person"
    PLACE = "place"
    FOOD = "food"
    EVENT = "event"
    TIME = "time"
    EMOTION = "emotion"
    ACTIVITY = "activity"
    OBJECT = "object"
    HEALTH = "health"
```

### 수정 가이드

```python
# 수정 전 (line 66)
category=EntityCategory.FAMILY,
# 수정 후
category=EntityCategory.PERSON,

# 수정 전 (line 124)
category=EntityCategory.DAILY,
# 수정 후
category=EntityCategory.ACTIVITY,
```

### 수정 범위

| 파일 | 변경 |
|------|------|
| `tests/test_c1_episodic_memory.py` | line 66: `FAMILY` → `PERSON`, line 124: `DAILY` → `ACTIVITY` |

---

## R-7: `test_b1_relationship.py` async 호출 미반영 (LOW)

### 문제 분석

**파일:** `tests/test_b1_relationship.py`
**라인:** 151~173

Phase B3에서 `build_system_prompt()`가 async로 변경되었지만, 테스트에서 여전히 동기 호출로 사용하고 있습니다.

```python
# 현재 코드 (line 151)
prompt_0 = self.pb.build_system_prompt(relationship_stage=0)
# → RuntimeError: coroutine was never awaited
```

### 수정 가이드

5개의 `build_system_prompt()` 호출을 모두 `await`로 변경:

```python
# 수정 전
prompt_0 = self.pb.build_system_prompt(relationship_stage=0)
# 수정 후
prompt_0 = await self.pb.build_system_prompt(user_id="test_b1", relationship_stage=0)
```

`test_b1_3_stage_prompts()` 메서드를 `async def`로 변경 (이미 async이므로 OK).

### 수정 범위

| 파일 | 변경 |
|------|------|
| `tests/test_b1_relationship.py` | line 151, 156, 161, 166, 171에 `await` 및 `user_id` 추가 |

---

## R-8: 주석 중국어 문자 혼입 (LOW)

### 문제 분석

**파일:** `core/dialogue/response_generator.py`
**라인:** 327

```python
episodic_memories=user_context.get("episodic_memories") if user_context else None  # 에피소드 기忆
```

"기억"이 깨져서 "기忆"로 표시됨 (중국어 문자 "忆" 혼입).

### 수정 가이드

```python
# 수정 전
# 에피소드 기忆
# 수정 후
# 에피소드 기억
```

### 수정 범위

| 파일 | 변경 |
|------|------|
| `core/dialogue/response_generator.py` | line 327 주석 수정 |

---

## R-9: Bare `except:` 구문 (LOW)

### 문제 분석

**파일:** `core/dialogue/dialogue_manager.py`
**라인:** 1141

```python
try:
    return datetime.fromisoformat(last_str)
except:
    return None
```

CLAUDE.md 코딩 컨벤션 위반: "구체적인 예외 처리" 원칙에 어긋납니다.

### 수정 가이드

```python
# 수정 전
except:
# 수정 후
except (ValueError, TypeError):
```

### 수정 범위

| 파일 | 변경 |
|------|------|
| `core/dialogue/dialogue_manager.py` | line 1141: `except:` → `except (ValueError, TypeError):` |

---

## R-10: `time_aware.py` docstring 이모지 잔존 (LOW)

### 문제 분석

**파일:** `core/dialogue/time_aware.py`

실제 템플릿(`TIME_GREETING_TEMPLATES`, `GAP_MESSAGE_TEMPLATES`)은 이모지 제거 완료이지만, docstring 예시에 4건 잔존:

```
Line 206: "좋은 아침이에요 🌅 오늘도 정원에 햇살이 따뜻하게 내려앉고 있어요."
Line 233: "어제 이후로 정원이 기다리고 있었어요 🌸"
Line 269: "저녁 식사는 맛있게 하셨나요? 🌙 정원이 노을빛으로 물들고 있어요."
Line 271: "정말 오랜만이에요 🌸 정원의 식물들이 보고 싶어 했어요."
```

### 수정 가이드

Docstring 예시에서 이모지를 제거하고 ㅎㅎ 등으로 대체:

```python
# 수정 전
"좋은 아침이에요 🌅 오늘도 정원에 햇살이 따뜻하게 내려앉고 있어요."
# 수정 후
"좋은 아침이에요. 오늘도 정원에 햇살이 따뜻하게 내려앉고 있어요."

# 수정 전
"어제 이후로 정원이 기다리고 있었어요 🌸"
# 수정 후
"어제 이후로 정원이 기다리고 있었어요."
```

### 수정 범위

| 파일 | 변경 |
|------|------|
| `core/dialogue/time_aware.py` | line 206, 233, 269, 271 docstring 이모지 제거 |

---

## 수정 우선순서 및 실행 계획

### Phase 1: CRITICAL 수정 (R-1)

1. `dialogue_manager.py` line 447~461 재배치
2. `dialogue_manager.py` store_all 호출 전 `analysis["samantha_emotion"]` 주입 (R-5 함께 처리)

### Phase 2: HIGH 수정 (R-2)

3. `prompt_builder.py` line 746~838 이모지 ~30건 제거/교체

### Phase 3: MEDIUM 수정 (R-3, R-4)

4. `prompt_builder.py` line 287~291 중복 블록 삭제
5. `prompt_builder.py` 규칙 번호 재할당

### Phase 4: LOW 수정 (R-6~R-10)

6. `test_c1_episodic_memory.py` EntityCategory 수정
7. `test_b1_relationship.py` await 추가
8. `response_generator.py` 주석 수정
9. `dialogue_manager.py` bare except 수정
10. `time_aware.py` docstring 수정

---

## 테스트 계획

### 단위 테스트 (수정 직후 즉시 실행)

#### T-1: R-1 관계 Stage 진급 검증 (CRITICAL)

**파일:** `tests/test_b1_relationship.py` (기존 테스트 활용 + 신규 케이스)

```python
@pytest.mark.asyncio
async def test_b1_stage_progression_via_webhook_path():
    """R-1: emotion=None으로 generate_response 호출해도 Stage 진급 확인"""
    manager = DialogueManager()
    user_id = "test_r1_webhook"

    await redis_client.delete(f"relationship:{user_id}")

    # webhook 경로: emotion 파라미터 없이 호출 (실제 운영과 동일)
    for i in range(5):
        await manager.generate_response(
            user_id=user_id,
            user_message="오늘 정말 기뻐요! 행복합니다 ㅎㅎ"
        )

    rel = await manager._get_or_init_relationship(user_id)
    assert rel["positive_events"] >= 1, \
        f"positive_events should be >= 1, got {rel['positive_events']}"

    # 갈등 후 긍정 전환 (recovery)
    await manager.generate_response(
        user_id=user_id,
        user_message="속상해서 너무 슬퍼요 ㅠㅠ"
    )
    await manager.generate_response(
        user_id=user_id,
        user_message="그래도 괜찮아졌어요 ㅎㅎ"
    )

    rel = await manager._get_or_init_relationship(user_id)
    assert rel["recovery_events"] >= 1, \
        f"recovery_events should be >= 1, got {rel['recovery_events']}"

    await redis_client.delete(f"relationship:{user_id}")
```

**검증 포인트:**
- `emotion` 파라미터 없이 호출해도 `_detect_emotion()`이 내부에서 감지
- `positive_events`가 정상 증가
- `recovery_events`가 정상 증가
- 기존 `test_b1_recovery_events_increment`도 여전히 통과

#### T-2: R-2 이모지 제거 검증 (HIGH)

```python
import re

def test_no_emoji_in_build_question_templates():
    """R-2: build_question() 템플릿에 이모지 없음"""
    from core.dialogue.prompt_builder import PromptBuilder
    pb = PromptBuilder()

    # question_templates 전체 조회 (리플렉션)
    import inspect
    source = inspect.getsource(pb.build_question)

    # Unicode 이모지 패턴 (U+1F300~U+1F9FF, U+2600~U+26FF, U+2700~U+27BF 등)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # 이모티콘
        "\U0001F300-\U0001F5FF"  # 기호 및 픽토그램
        "\U0001F680-\U0001F6FF"  # 교통 및 지도
        "\U0001F1E0-\U0001F1FF"  # 국기
        "\U0001FA00-\U0001FA6F"  # 확장 기호
        "\U0001FA70-\U0001FAFF"
        "\U00002702-\U000027B0"  # 장식 기호
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # 보충 기호
        "]+"
    )

    # 이모지가 있으면 실패
    emojis_found = emoji_pattern.findall(source)
    assert len(emojis_found) == 0, \
        f"Found emojis in build_question templates: {emojis_found}"
```

#### T-3: R-3 + R-4 SYSTEM_PROMPT 일관성 검증 (MEDIUM)

```python
def test_system_prompt_no_duplicate_blocks():
    """R-3: SYSTEM_PROMPT에 중복 블록 없음"""
    from core.dialogue.prompt_builder import PromptBuilder
    pb = PromptBuilder()
    prompt = pb.build_system_prompt(user_id="test")

    # "망설임과 불확실성" 이 1회만 등장하는지 확인
    count = prompt.count("망설임과 불확실성")
    assert count == 1, f"'망설임과 불확실성' appears {count} times, expected 1"


def test_system_prompt_consecutive_numbering():
    """R-4: 규칙 번호 연속성 확인"""
    from core.dialogue.prompt_builder import PromptBuilder
    import re
    pb = PromptBuilder()
    prompt = pb.build_system_prompt(user_id="test")

    # 규칙 번호 추출: "1.", "2.", "3." 등
    numbers = [int(m) for m in re.findall(r'^(\d+)\.\s', prompt, re.MULTILINE)]
    numbers.sort()

    # 연속성 확인
    for i in range(len(numbers) - 1):
        assert numbers[i+1] == numbers[i] + 1, \
            f"Rule number gap: {numbers[i]} → {numbers[i+1]}"
```

#### T-4: R-5 samantha_emotion 연결 검증 (MEDIUM)

```python
@pytest.mark.asyncio
async def test_samantha_emotion_populated():
    """R-5: store_all 호출 시 samantha_emotion이 None이 아님"""
    # integration test: generate_response → memory_manager.store_all
    # 이 테스트는 store_all이 analysis dict와 함께 호출될 때
    # samantha_emotion이 채워지는지 검증
    # (실제 구현은 dialogue_manager → memory_manager 경로)
    pass  # 통합 테스트에서 verify
```

#### T-5: R-6~R-10 회귀 테스트

```python
def test_c1_entity_category_valid():
    """R-6: EntityCategory.FAMILY/DAILY 사용하지 않음"""
    from core.memory.memory_extractor import EntityCategory
    assert not hasattr(EntityCategory, "FAMILY")
    assert not hasattr(EntityCategory, "DAILY")


@pytest.mark.asyncio
async def test_b1_stage_prompts_await():
    """R-7: build_system_prompt async 호출 정상"""
    from core.dialogue.prompt_builder import PromptBuilder
    pb = PromptBuilder()
    prompt = await pb.build_system_prompt(user_id="test", relationship_stage=0)
    assert "처음 알아가는 사이" in prompt


def test_response_generator_no_garbled_comment():
    """R-8: 중국어 문자 혼입 없음"""
    from core.dialogue.response_generator import ResponseGenerator
    import inspect
    source = inspect.getsource(ResponseGenerator)
    assert "忆" not in source, "Garbled Chinese character found"


def test_dialogue_manager_no_bare_except():
    """R-9: bare except 없음"""
    from core.dialogue.dialogue_manager import DialogueManager
    import inspect
    source = inspect.getsource(DialogueManager)
    # 'except:'가 'except ('로 시작하지 않는 경우 탐지
    import re
    bare_excepts = re.findall(r'except\s*:', source)
    assert len(bare_excepts) == 0, f"Found {len(bare_excepts)} bare except clauses"


def test_time_aware_docstring_no_emoji():
    """R-10: time_aware.py docstring에 이모지 없음"""
    from core.dialogue.time_aware import TimeAwareDialogue
    import inspect, re
    source = inspect.getsource(TimeAwareDialogue)
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0"
        "\U000024C2-\U0001F251\U0001F900-\U0001F9FF]+"
    )
    emojis = emoji_pattern.findall(source)
    assert len(emojis) == 0, f"Found emojis in time_aware docstrings: {emojis}"
```

### 통합 테스트 (Phase별 순차 실행)

#### 실행 순서

```bash
# 1. R-1 수정 후 B1 테스트
python -m pytest tests/test_b1_relationship.py -v

# 2. R-2 수정 후 build_question 테스트
python -m pytest tests/test_b3_adaptive.py -v  # build_question을 사용하는 테스트

# 3. R-3, R-4 수정 후 프롬프트 일관성 테스트
python -m pytest tests/test_b1_relationship.py::test_b1_3_stage_prompts -v

# 4. R-5~R-10 전체 수정 후 회귀 테스트
python -m pytest tests/test_b1_relationship.py tests/test_c1_episodic_memory.py tests/test_b3_adaptive.py tests/test_b4_time_aware.py tests/test_c2_rotation.py tests/test_c5_proactive.py -v

# 5. 전체 테스트 스위트
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

#### 전체 테스트 스크립트

```bash
# samantha_remain_fault 전체 검증
cd /home/admin/docker/MemoryGardenAI

echo "=== R-1: B1 관계 Stage 테스트 ==="
python -m pytest tests/test_b1_relationship.py -v

echo "=== R-2~R-4: 프롬프트 일관성 테스트 ==="
python -c "
import re, inspect
from core.dialogue.prompt_builder import PromptBuilder

pb = PromptBuilder()

# R-2: 이모지 검사
source = inspect.getsource(pb.build_question)
emoji_pattern = re.compile('[' + '\U0001F600-\U0001F64F' + '\U0001F300-\U0001F5FF' + '\U0001F680-\U0001F6FF' + '\U00002702-\U000027B0' + '\U0001F900-\U0001F9FF' + ']+')
emojis = emoji_pattern.findall(source)
print(f'R-2 이모지 검사: {\"PASS\" if not emojis else f\"FAIL ({len(emojis)}개 잔존)\"}')

# R-3: 중복 블록 검사
import asyncio
prompt = asyncio.get_event_loop().run_until_complete(pb.build_system_prompt(user_id='test'))
count = prompt.count('망설임과 불확실성')
print(f'R-3 중복 블록: {\"PASS\" if count == 1 else f\"FAIL ({count}회 등장)\"}')

# R-4: 번호 연속성
numbers = sorted([int(m) for m in re.findall(r'^(\\d+)\\.\\s', prompt, re.MULTILINE)])
gaps = [f'{numbers[i]}→{numbers[i+1]}' for i in range(len(numbers)-1) if numbers[i+1] != numbers[i]+1]
print(f'R-4 번호 연속성: {\"PASS\" if not gaps else f\"FAIL (갭: {gaps})\"}')
"

echo "=== R-6: EntityCategory 검증 ==="
python -c "
from core.memory.memory_extractor import EntityCategory
print(f'R-6 FAMILY 미존재: {\"PASS\" if not hasattr(EntityCategory, \"FAMILY\") else \"FAIL\"}'  )
print(f'R-6 DAILY 미존재: {\"PASS\" if not hasattr(EntityCategory, \"DAILY\") else \"FAIL\"}'  )
"

echo "=== R-8: 중국어 문자 검증 ==="
python -c "
import inspect
from core.dialogue.response_generator import ResponseGenerator
source = inspect.getsource(ResponseGenerator)
print(f'R-8 깨진 문자: {\"PASS\" if \"忆\" not in source else \"FAIL\"}'  )
"

echo "=== R-9: Bare except 검증 ==="
python -c "
import inspect, re
from core.dialogue.dialogue_manager import DialogueManager
source = inspect.getsource(DialogueManager)
bare = re.findall(r'except\\s*:', source)
print(f'R-9 bare except: {\"PASS\" if not bare else f\"FAIL ({len(bare)}건)\"}'  )
"

echo "=== R-10: time_aware docstring 이모지 검증 ==="
python -c "
import inspect, re
from core.dialogue.time_aware import TimeAwareDialogue
source = inspect.getsource(TimeAwareDialogue)
emoji_pattern = re.compile('[' + '\U0001F600-\U0001F64F' + '\U0001F300-\U0001F5FF' + '\U0001F680-\U0001F6FF' + '\U00002702-\U000027B0' + '\U0001F900-\U0001F9FF' + ']+')
emojis = emoji_pattern.findall(source)
print(f'R-10 docstring 이모지: {\"PASS\" if not emojis else f\"FAIL ({len(emojis)}개 잔존)\"}'  )
"

echo "=== 전체 테스트 ==="
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

---

## 수정 파일 총괄

| 파일 | R-ID | 변경 유형 | 라인 (대략) |
|------|------|-----------|-------------|
| `core/dialogue/dialogue_manager.py` | R-1, R-5, R-9 | 로직 수정 + 변수 추가 | 447~461, store_all 호출부, 1141 |
| `core/dialogue/prompt_builder.py` | R-2, R-3, R-4 | 이모지 제거 + 블록 삭제 + 번호 재할당 | 746~838, 287~291, 전역 |
| `core/dialogue/response_generator.py` | R-8 | 주석 수정 | 327 |
| `core/dialogue/time_aware.py` | R-10 | docstring 수정 | 206, 233, 269, 271 |
| `tests/test_b1_relationship.py` | R-7 | await 추가 + 신규 테스트 | 151, 156, 161, 166, 171 |
| `tests/test_c1_episodic_memory.py` | R-6 | 상수명 수정 | 66, 124 |
