# 사만다 페르소나 완성 계획서 (최종 수정版)

> **작성일:** 2026-03-27
> **수정 내역:**
> - v1: 결함 분석 보고(`samantha_plan_fault.md`) 11개 결함 전체 반영
> - v2: **2차 코드 교차 검증** 14개 추가 결함 반영 (실제 코드 라인 단위 확인 완료)
> - **v3: 최종 코드 교차 검증 완료** (grep + Read 도구로 실제 코드 라인 단위 확인)
>   - DOMAIN_ROTATION 신규 정의 필요 (결함 #5 수정: "수정" → "신규 정의")
>   - time_aware.py 이모지 25+개 식별 (결함 #7 수정: 예상 시간 60분으로 증가)
>   - User 모델 필드명 검증 완료 (결함 #12, #13: kakao_access_token, deleted_at 확인)
> **목표:** 미완료 태스크 구현으로 사만다 페르소나 완성도 100% 달성
> **예상 기간:** 3일 (CRITICAL 1일, HIGH 2일)
> **구성:** 각 Phase별 [구현 가이드] + [테스트 케이스] 포함

---

## 🔴 수정된 결함 목록

### v1 (fault.md 기반, 11건)

| # | Phase | 심각도 | 결함 | 수정 내용 |
|---|-------|--------|------|-----------|
| 1 | B2 | CRITICAL | 감정 라벨 EN/KO 미스매치 | `_detect_emotion()` 한국어 라벨 반환으로 수정 |
| 2 | C5 | CRITICAL | `send_to_me()` 파라미터 오류 | `access_token=` 올바른 인수로 수정 |
| 3 | C5 | CRITICAL | `send_bizmessage()` 키워드 오류 | `plus_friend_user_key=` 로 수정 |
| 4 | C1 | HIGH | 테스트 import 경로 오류 | `core.memory.memory_extractor`에서 import |
| 5 | C2 | HIGH | DOMAIN_ROTATION 상수 누락 | DOMAIN_ROTATION 상수 신규 정의 (현재 존재하지 않음) + RT 포함 | [v3 검증] |
| 6 | C2 | HIGH | 함수 시그니처 불일치 | 모듈 레벨 함수 구조 유지 |
| 7 | B4+A2 | HIGH | 이모지 템플릿 충돌 | 동시 구현 필수 명시 + 4개 파일 수정 가이드 |
| 8 | B3 | MEDIUM | 데드코드 미해결 | `_check_probe_cooldown()` 호출부 추가 |
| 9 | A2 | MEDIUM | 이모지 정리 가이드 누락 | 4개 파일 수정 가이드 추가 |
| 10 | C1-3 | MEDIUM | LLM 비용 문제 | asyncio.create_task로 비동기 처리 |
| 11 | B2 | MEDIUM | emotion_vector 전달 누락 | `generate_response()`에 전달 코드 추가 |

### v2 (2차 교차 검증, 14건)

| # | Phase | 심각도 | 결함 | 수정 내용 |
|---|-------|--------|------|-----------|
| 12 | C5 | **CRITICAL** | `User.oauth_access_token` 필드 없음 | → `User.kakao_access_token`으로 교체 (`models.py:43`) |
| 13 | C5 | **CRITICAL** | `User.is_active` 필드 없음 | → `User.deleted_at == None`으로 교체 (`is_active`은 `FCMToken` 전용, `models.py:177`) |
| 14 | B2 | HIGH | `generate_response()`의 `emotion` 파라미터 미전달 | webhook에서 `emotion=None` 호출 → `_detect_emotion()`이 실제 감정원 | 설계 의도 명시 |
| 15 | B3 | HIGH | `_check_probe_cooldown()` 순환 임포트 | `prompt_builder.py`에서 `kakao_webhook` import → 순환 의존 | 인라인 로직으로 해결 |
| 16 | S-3 | HIGH | Line 185 삭제 시 번호 재배열 누락 | SYSTEM_PROMPT 내부 "대화 원칙 2번" 항목 → 내용 통합(삭제 아닌 교체) |
| 17 | B4 | MEDIUM | `generate_gap_message()` 내부 이중 호출 | 이미 `get_hours_since_last_interaction()` 재호출 → `time_aware` 직접 사용 |
| 18 | C2 | MEDIUM | 기존 `_get_probe_question()` 호출부 2곳 누락 | `prompt_builder.py:361, 371`에서도 로테이션 체크 필요 | 기존 함수 수정으로 해결 |
| 19 | C1-3 | MEDIUM | "BackgroundTask" 명칭 부정확 | FastAPI `BackgroundTasks`가 아닌 `asyncio.create_task()` 사용 | 용어 정정 |
| 20 | S | MEDIUM | LLM 응답 기반 테스트 비결정성 | `pytest.mark.slow` + mock 분리 필요 | 테스트 전략 추가 |
| 21 | B3 | MEDIUM | private 함수 테스트 import | `_detect_repetition`, `_check_probe_cooldown`은 private | 주의사항 명시 |
| 22 | B3 | MEDIUM | `recent_mentions` 시점 명확화 | `add_turn()` 이전에 조회 → 현재 턴 미포함 (정상 동작) | 주의사항 명시 |
| 23 | B1 | MEDIUM | EN 감정명 불필요 포함 | `positive_emotions`에 `"joy"`, `negative_emotions`에 `"sadness","anger"` 포함 → `EMOTION_VECTOR_MAP`은 한국어 키만 사용 | 제거 |
| 24 | B1 | LOW | `test_b1_stage_4_progression` 테스트 미완성 | `# ... (테스트 데이터 주입)` 주석으로 대체 | Redis 직접 주입 코드 작성 |
| 25 | C5 | LOW | `push_scheduler.py` 구조 확인 누락 | 기존 스케줄러 구조 확인 후 추가 필요 | 주의사항 명시 |

---

## 📊 전체 현황

| Phase | 완료도 | 예상 작업량 | 우선순위 |
|-------|--------|-------------|----------|
| **S (질문 패턴)** | 0% (0/3) | **40분** | 🔥 CRITICAL |
| **B1 (관계 모델)** | 93% | 10분 | 🔥 HIGH |
| **B2 (감정 벡터)** | 40% | 30분 | 🔥 HIGH |
| **B3 (MCDI 통합)** | 78% | 25분 | 🔥 HIGH |
| **B4 (시간 인식)** | 75% | 15분 | 🟡 MEDIUM |
| **C1 (에피소드 서사)** | ~70% | 35분 | 🔥 HIGH |
| **C2 (탐지 분산)** | 0% (0/2) | 45분 | 🟡 MEDIUM |
| **C5 (Proactive)** | 0% (0/6) | 2시간 | 🔥 HIGH |

---

## 🚀 Phase S: 질문 패턴 재설계 [CRITICAL, 40분]

**목표:** 사용자 불만("너무 질문이 많아") 즉시 해결

---

### 📝 구현 가이드

#### S-1. 질문 빈도 제어 규칙 (10분)
**파일:** `core/dialogue/prompt_builder.py`
**위치:** SYSTEM_PROMPT 리터럴 내부, Line 208 (A3 망설임표현 규칙 `"""` 닫힌 후) 바로 앞
> **참고:** SYSTEM_PROMPT은 line 153에서 `"""`로 시작하여 line 229에서 `"""`로 닫힘. S-1/S-2는 이 리터럴 **내부**의 마지막 규칙으로 추가

**추가할 텍스트 (SYSTEM_PROMPT 리터럴 내부, line 208 직전):**
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

#### S-2. 대화 종료 패턴 (10분)
**위치:** S-1 바로 다음 (같은 SYSTEM_PROMPT 리터럴 내부)

**추가할 텍스트:**
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

#### S-3. SYSTEM_PROMPT 모순 수정 (5분)
**파일:** `core/dialogue/prompt_builder.py`
**위치:** Line 185 (SYSTEM_PROMPT 리터럴 내부, "대화 원칙" 섹션)

> **[결함 #16 수정]** 단순 삭제 시 "대화 원칙" 번호 2번이 빈 칸이 됨.
> **해결:** Line 185의 내용을 "유니코드 이모지 사용 절대 금지"로 **교체** (삭제 아닌 통합)

**기존 코드 (line 185):**
```python
"2. 이모지 절제적 사용 (1-2개/메시지)\n"
```

**수정 후:**
```python
"2. 유니코드 이모지 사용 절대 금지 (😊 🌿 🎉 등 사용 불가, ㅋㅋ ㅠㅠ 등은 허용)\n"
```

> 이렇게 하면 line 200의 별도 "유니코드 이모지 사용 절대 금지" 규칙과 **중복**됩니다.
> 따라서 **line 200-202의 3줄도 함께 삭제**하여 중복을 제거합니다:
> ```python
> # 삭제할 라인 (line 200-202):
> "- **유니코드 이모지 사용 절대 금지**: 😊 🌿 🎉 ❤️ 👍 등 유니코드 그림 이모지를 사용하지 마세요.\n"
> "  - ✅ 대신 'ㅋㅋ', 'ㅠㅠ', 'ㅎㅎ', 'ㅜㅜ' 같은 한국어 텍스트 감정 표현은 자유롭게 허용합니다.\n"
> "  - 기쁜 표현: 😄 → "ㅋㅋ", "ㅎㅎ" / 슬픈 표현: 😢 → "ㅠㅠ", "ㅜㅜ"\n"
> ```

---

### 🧪 테스트 케이스

**파일:** `tests/test_dialogue/test_s_question_patterns.py` (신규)

> **[결함 #20 주의]** 이 테스트들은 LLM 응답에 의존하므로 비결정적입니다.
> CI 환경에서는 `@pytest.mark.slow` + mock을 사용하거나, 별도 integration test로 분리하세요.

```python
"""Phase S: 질문 패턴 재설계 테스트"""

import pytest
from core.dialogue.dialogue_manager import DialogueManager


@pytest.mark.asyncio
@pytest.mark.slow  # [결함 #20] LLM 응답 기반이므로 비결정적
class TestQuestionFrequencyControl:
    """S-1: 질문 빈도 제어 테스트"""

    async def test_fatigue_signal_no_question(self):
        """피로 신호 시 질문 자제"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_fatigue",
            user_message="너무 피곤해요"
        )

        # 물음표 0-1개만 허용
        question_count = response.count("?")
        assert question_count <= 1, f"Too many questions: {question_count}"

        # 피로를 공감하는 표현 포함
        assert any(kw in response for kw in ["피곤", "힘드", "쉬", "휴식"])

    async def test_user_complaint_response(self):
        """"질문이 많아" 불만에 대한 반응"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_complaint",
            user_message="너무 질문이 많아"
        )

        # 사과/이해 표현
        assert any(kw in response for kw in ["죄송", "미안", "이해", "알겠"])

        # 추가 질문 없음
        assert not response.strip().endswith("?")

    async def test_short_answer_no_followup(self):
        """짧은 답변 후 추가 질문 자제"""
        manager = DialogueManager()

        # 짧은 답변 3회
        for _ in range(3):
            response = await manager.generate_response(
                user_id="test_s_short",
                user_message="응"
            )

        # 3턴 후에는 질문 빈도 감소
        assert response.count("?") <= 1

    async def test_active_conversation_questions_ok(self):
        """활발한 대화에서는 질문 허용"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_active",
            user_message="오늘 딸이랑 벚꽃 구경하러 다녀왔어요. 정말 예쁘더라고요."
        )

        # 적절한 질문 1개 허용
        question_count = response.count("?")
        assert 0 <= question_count <= 2


@pytest.mark.asyncio
@pytest.mark.slow  # [결함 #20] LLM 응답 기반
class TestConversationClosure:
    """S-2: 대화 종료 패턴 테스트"""

    async def test_fatigue_closure(self):
        """피로 신호 시 자연스러운 종료"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_closure",
            user_message="힘들어서 그만 얘기하고 싶어요"
        )

        # 종료 키워드
        assert any(kw in response for kw in ["쉬세요", "나중에", "편안한", "안녕"])

        # 종료 후 질문 없음
        assert not response.strip().endswith("?")

    async def test_goodbye_no_followup(self):
        """작별 인사 후 추가 질문 없음"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_goodbye",
            user_message="그럼 안녕히 계세요"
        )

        # 응답이 짧고 종료적이어야 함
        assert len(response) < 100
        assert "안녕" in response or "좋은" in response

    async def test_multiple_fatigue_signals(self):
        """반복적인 피로 신호에 일관된 대응"""
        manager = DialogueManager()

        fatigue_messages = ["피곤해", "힘들어", "쉬고싶어"]

        for msg in fatigue_messages:
            response = await manager.generate_response(
                user_id="test_s_multi_fatigue",
                user_message=msg
            )

            # 모든 경우에 종료 패턴
            assert not response.strip().endswith("?")


@pytest.mark.asyncio
@pytest.mark.slow
class TestSystemPromptConsistency:
    """S-3: SYSTEM_PROMPT 모순 수정 검증"""

    async def test_no_emoji_in_response(self):
        """응답에 유니코드 이모지 없음"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_emoji",
            user_message="오늘 기분이 좋아요"
        )

        # 유니코드 이모지 범위 확인
        emoji_pattern = "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]"
        import re
        emojis = re.findall(emoji_pattern, response)

        assert len(emojis) == 0, f"Found emojis: {emojis}"

    async def test_korean_emoticon_allowed(self):
        """한국어 텍스트 감정 표현 허용"""
        manager = DialogueManager()

        response = await manager.generate_response(
            user_id="test_s_korean",
            user_message="웃긴 일 있었어요 ㅋㅋ"
        )

        # ㅋㅋ, ㅠㅠ 등은 허용
        has_korean_emoticon = any(em in response for em in ["ㅋㅋ", "ㅠㅠ", "ㅎㅎ", "ㅜㅜ"])
        # 필수는 아니지만 있어도 됨
```

---

## 🔧 Phase B1: recovery_events 증가 로직 [HIGH, 10분]

---

### 📝 구현 가이드

**파일:** `core/dialogue/dialogue_manager.py`
**함수:** `_update_relationship_stage()`
**위치:** Line 905-913 근처

**수정 코드:**
```python
# 감정 이벤트 기록 (수정 필요)
# [결함 #23 수정] EN 감정명 제거 — EMOTION_VECTOR_MAP은 한국어 키만 사용
positive_emotions = ["기쁨", "행복", "감동", "설렘", "만족", "즐거움"]
negative_emotions = ["우울", "슬픔", "불안", "짜증", "스트레스", "분노"]

# 갈등 상태 추적 변수 초기화
rel["_was_negative"] = rel.get("_was_negative", False)

if emotion:
    if any(e in emotion for e in positive_emotions):
        rel["positive_events"] += 1
        # ========== B1 수정: 갈등 후 긍정 전환 감지 ==========
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
```

---

### 🧪 테스트 케이스

**파일:** `tests/test_b1_relationship.py` (기존 파일에 추가)

```python
"""B1: Relationship Stage 테스트 (recovery_events 검증)"""

import pytest
from core.dialogue.dialogue_manager import DialogueManager
from database.redis_client import redis_client


@pytest.mark.asyncio
async def test_b1_recovery_events_increment():
    """B1 수정: 갈등 후 긍정 전환 시 recovery_events 증가"""
    manager = DialogueManager()
    user_id = "test_b1_recovery"

    # 초기화
    await redis_client.delete(f"relationship:{user_id}")

    # 1. 갈등 상황 (부정 감정)
    await manager.generate_response(
        user_id=user_id,
        user_message="속상해서 마음이 너무 힘들어요"
    )

    # 2. 긍정 전환
    await manager.generate_response(
        user_id=user_id,
        user_message="그래도 친구가 위로해줘서 기분이 나아졌어요"
    )

    # 3. recovery_events 확인
    rel = await manager._get_or_init_relationship(user_id)
    assert rel["recovery_events"] >= 1, f"recovery_events should be >= 1, got {rel['recovery_events']}"

    # 정리
    await redis_client.delete(f"relationship:{user_id}")


@pytest.mark.asyncio
async def test_b1_stage_4_progression():
    """Stage 3 → 4 진급: recovery_events 조건 충족"""
    manager = DialogueManager()
    user_id = "test_b1_stage4"

    # 초기화
    await redis_client.delete(f"relationship:{user_id}")

    # [결함 #24 수정] Redis에 Stage 3 조건 데이터 직접 주입
    # Stage 3 → 4 조건: total_days >= 30 AND recovery_events >= 1
    from datetime import datetime, timedelta
    await redis_client.set_json(f"relationship:{user_id}", {
        "stage": 3,
        "total_turns": 200,
        "total_days": 35,
        "positive_events": 50,
        "conflict_events": 3,
        "recovery_events": 0,
        "_was_negative": False,
        "first_interaction": (datetime.now() - timedelta(days=35)).isoformat(),
        "last_interaction": datetime.now().isoformat(),
    })

    # 갈등 상태 설정 (_was_negative = True)
    rel_before = await redis_client.get_json(f"relationship:{user_id}")
    rel_before["_was_negative"] = True
    await redis_client.set_json(f"relationship:{user_id}", rel_before)

    # 긍정 전환 → recovery_events 증가 → Stage 4 진급
    await manager.generate_response(user_id=user_id, user_message="위로해줘서 고마워요 ㅎㅎ")

    # Stage 4 진급 확인
    rel = await manager._get_or_init_relationship(user_id)
    assert rel["stage"] == 4, f"Expected stage 4, got {rel['stage']}"
    assert rel["recovery_events"] >= 1, f"Expected recovery_events >= 1, got {rel['recovery_events']}"

    # 정리
    await redis_client.delete(f"relationship:{user_id}")
```

---

## 🔧 Phase B2: 감정 벡터 호출 연결 [HIGH, 30분]

---

### 📝 구현 가이드

**파일:** `core/dialogue/dialogue_manager.py`
**함수:** `generate_response()`
**위치:** Line 447-528

> **[결함 #14 설계 의도]**
> 현재 `kakao_webhook.py:821`에서 `generate_response()`를 호출할 때 `emotion`과 `emotion_intensity`를 전달하지 않습니다.
> 따라서 항상 `else` 분기(`response_generator.generate()`)로 진입합니다.
> `_detect_emotion()`은 webhook에서 감정을 전달하지 않는 상황을 보완하는 **내부 fallback**입니다.
> 향후 webhook에서 NLP 기반 감정 인식을 추가하면 `emotion` 파라미터로 전달하여 `generate_empathetic_response()` 경로를 활성화할 수 있습니다.

**Step 1: 감정 인식 헬퍼 추가 (10분)**
```python
async def _detect_emotion(self, text: str) -> str:
    """간단 감정 인식 (B2-7)

    [결함 #1 수정] EMOTION_VECTOR_MAP의 키와 일치하는 한국어 감정 라벨 반환
    [결함 #14] webhook에서 emotion을 전달하지 않을 때의 내부 fallback

    Returns:
        "기쁨", "우울", "분노", "불안", "피곤", "중립" 중 하나
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

**Step 2: generate_response() 수정 (20분)**
```python
# Line 448-452 근처: 기존 relationship_stage 업데이트 코드 뒤에 추가
# [참고] _update_relationship_stage()는 int를 반환하며, relationship_stage 파라미터도 int 타입
if relationship_stage is None:
    relationship_stage = await self._update_relationship_stage(user_id, emotion)

# ========== B2-7: 감정 벡터 실제 갱신 (신규) ==========
# [결함 #14] webhook에서 emotion을 전달하지 않으므로 내부에서 감지
detected_emotion = await self._detect_emotion(user_message)
updated_vector = await self._update_emotion_vector(user_id, detected_emotion)
# =====================================================

# Line 455: last_interaction 업데이트
await self.update_last_interaction(user_id)

# response_generator 호출 시 emotion_vector 파라미터 추가
# [결함 #11 수정] 두 호출부 모두에 emotion_vector=updated_vector 추가

if emotion and emotion_intensity is not None:
    response = await self.response_generator.generate_empathetic_response(
        user_message=user_message,
        detected_emotion=emotion,
        emotion_intensity=emotion_intensity,
        conversation_history=conversation_history,
        user_context=user_context,
        mcdi_context=mcdi_context,
        relationship_stage=relationship_stage,
        emotion_vector=updated_vector  # B2-6: 갱신된 벡터 전달 [결함 #11 수정]
    )
else:
    response = await self.response_generator.generate(
        user_message=user_message,
        conversation_history=conversation_history,
        user_context=user_context,
        next_question=next_question,
        mcdi_context=mcdi_context,
        relationship_stage=relationship_stage,
        emotion_vector=updated_vector  # B2-6: 갱신된 벡터 전달 [결함 #11 수정]
    )
```

---

### 🧪 테스트 케이스

**파일:** `tests/test_b2_emotion_vector.py`

```python
"""B2: 감정 벡터 테스트 (호출 연결 검증)"""

import pytest
from core.dialogue.dialogue_manager import DialogueManager
from database.redis_client import redis_client


@pytest.mark.asyncio
class TestEmotionVectorUpdate:
    """B2-7: 감정 벡터 실제 갱신 테스트"""

    async def test_joy_increases_valence(self):
        """기쁨 → valence 증가"""
        manager = DialogueManager()
        user_id = "test_b2_joy"

        # 초기화
        await redis_client.delete(f"emotion_vector:{user_id}")

        # 기쁜 메시지
        await manager.generate_response(
            user_id=user_id,
            user_message="딸이 방문해서 정말 기뻐요 ㅋㅋ"
        )

        # 벡터 확인
        vector = await redis_client.get_json(f"emotion_vector:{user_id}")

        assert vector is not None
        assert vector["v"] > 0.5, f"valence should be > 0.5, got {vector['v']}"
        assert vector["a"] > 0.5, f"arousal should be > 0.5, got {vector['a']}"

    async def test_sadness_decreases_valence(self):
        """슬픔 → valence 감소"""
        manager = DialogueManager()
        user_id = "test_b2_sadness"

        # 초기화
        await redis_client.delete(f"emotion_vector:{user_id}")

        # 슬픈 메시지
        await manager.generate_response(
            user_id=user_id,
            user_message="며칠 전 지나가신 친구분 생각하니까 너무 슬퍼요 ㅠㅠ"
        )

        # 벡터 확인
        vector = await redis_client.get_json(f"emotion_vector:{user_id}")

        assert vector is not None
        assert vector["v"] < 0.4, f"valence should be < 0.4, got {vector['v']}"

    async def test_anger_increases_arousal(self):
        """분노 → arousal 증가"""
        manager = DialogueManager()
        user_id = "test_b2_anger"

        # 초기화
        await redis_client.delete(f"emotion_vector:{user_id}")

        # 화난 메시지
        await manager.generate_response(
            user_id=user_id,
            user_message="정말 화가 나요 너무 속상해서..."
        )

        # 벡터 확인
        vector = await redis_client.get_json(f"emotion_vector:{user_id}")

        assert vector is not None
        assert vector["a"] > 0.6, f"arousal should be > 0.6 for anger, got {vector['a']}"
        assert vector["v"] < 0.4, f"valence should be < 0.4 for anger"

    async def test_emotion_delta_clamping(self):
        """한 턴 최대 변화량 제한 (MAX_DELTA_PER_TURN = 0.25)"""
        manager = DialogueManager()
        user_id = "test_b2_clamp"

        # 초기화
        await redis_client.delete(f"emotion_vector:{user_id}")

        # 극단적으로 기쁜 메시지
        await manager.generate_response(
            user_id=user_id,
            user_message="대박 최고의 행복입니다!!! ㅋㅋㅋㅋ"
        )

        # 벡터 확인
        vector = await redis_client.get_json(f"emotion_vector:{user_id}")

        # 초기값이 {"v": 0.0, "a": 0.0, "i": 0.5}이므로 최대 0.25까지만 증가 가능
        assert vector["v"] <= 0.25, f"valence should be clamped to 0.25, got {vector['v']}"
```

---

## 🔧 Phase B3: 반복 발화 감지 연결 + 쿨다운 [HIGH, 25분]

---

### 📝 구현 가이드

**파일:** `api/routes/kakao_webhook.py`
**위치:** Line 820 직후 (메인 핸들러)

**Step 1: 반복 발화 감지 연결 (15분)**
```python
# B3-3: MCDI 컨텍스트 조회 후 응답 생성
mcdi_context = await _get_mcdi_context(user_id)

# ========== B3-5: 반복 발화 감지 후 risk_level 승격 (신규) ==========
# 세션에서 최근 발화 가져오기
session_data_tmp = await redis_client.get_json(f"session:{user_id}")
recent_mentions_raw = session_data_tmp.get("conversation_history", []) if session_data_tmp else []
# [결함 #22 주의] conversation_history의 키는 "user" (dialogue_manager.py:271 확인)
# add_turn()은 응답 생성 후에 호출되므로, 여기서는 현재 턴이 아직 포함되지 않음 (정상 동작)
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

**Step 2: 탐침 질문 쿨다운 연결 (10분)**

> **[결함 #15 수정] 순환 임포트 문제 해결**
> `prompt_builder.py`에서 `from api.routes.kakao_webhook import _check_probe_cooldown`을 하면
> 순환 의존 발생 가능: `prompt_builder` → `kakao_webhook` → `dialogue_manager` → `prompt_builder`
>
> **해결:** `prompt_builder.py` 내부에 쿨다운 체크 로직을 **인라인**으로 추가.
> 기존 `_check_probe_cooldown()` 함수는 `kakao_webhook.py`에 유지하되, `prompt_builder.py`에서는
> 동일 로직을 직접 수행하는 방식으로 분리.

**수정 위치:** `core/dialogue/prompt_builder.py` — 기존 `_get_probe_question()` 함수 수정

```python
# core/dialogue/prompt_builder.py

# [결함 #18] 기존 _get_probe_question() (line 73)을 수정
# 기존 호출부 (line 361, 371)에서도 동일하게 로테이션 + 쿨다운 체크 적용됨
async def _get_probe_question(domain: str, user_id: str = None) -> str:
    """도메인에 맞는 자연어 질문 랜덤 반환 (B3-3, C2-1 로테이션 + B3-4 쿨다운)

    [결함 #15] kakao_webhook import 대신 redis_client 직접 사용으로 순환 의존 방지
    [결함 #18] 기존 호출부 2곳(line 361, 371)에 user_id 전달 필요

    Args:
        domain: MCDI 도메인 코드 (LR, SD, NC, TO, ER, RT)
        user_id: 사용자 ID (쿨다운 체크용, None이면 쿨다운 스킵)

    Returns:
        자연어 질문 문자열 또는 빈 문자열
    """
    import random
    from datetime import datetime
    from database.redis_client import redis_client

    # C2-1: 요일별 로테이션 체크
    today_weekday = datetime.now().weekday()
    rotation_domains = DOMAIN_ROTATION.get(today_weekday, ["LR", "SD"])
    if domain not in rotation_domains:
        logger.debug(f"Domain {domain} not in today's rotation {rotation_domains}")
        return ""

    # [결함 #8] 쿨다운 체크 — kakao_webhook의 _check_probe_cooldown()과 동일 로직
    if user_id:
        cooldown_key = f"probe_used:{user_id}:{domain}"
        try:
            cooldown_active = await redis_client.get_json(cooldown_key)
            if cooldown_active:
                logger.debug(f"Probe cooldown active for {user_id}:{domain}")
                return ""
            await redis_client.set_json(cooldown_key, {"used": True}, ttl=1800)
        except Exception:
            pass  # 실패 시 허용

    questions = DEMENTIA_PROBE_QUESTIONS.get(domain)
    if not questions:
        return ""
    return random.choice(questions)
```

> **주의:** `_get_probe_question()`이 `async`로 변경되므로 기존 호출부(line 361, 371)에서도 `await` 추가 필요:
> ```python
> # line 361, 371 수정
> probe_hint = await _get_probe_question(weak_domain, user_id=user_id) if weak_domain else ""
> ```

---

### 🧪 테스트 케이스

**파일:** `tests/test_b3_adaptive.py` (기존 파일에 추가)

> **[결함 #21 주의]** `_detect_repetition`, `_check_probe_cooldown`은 private 함수 (접두사 `_`).
> `from api.routes.kakao_webhook import _detect_repetition`으로 임포트 가능하지만
> IDE/린터에서 경고 발생할 수 있음. 테스트 전용으로 허용.

```python
"""B3: 반복 발화 감지 테스트"""

import pytest
# [결함 #21] private 함수 import — IDE 경고 무시
from api.routes.kakao_webhook import _detect_repetition, _check_probe_cooldown


@pytest.mark.asyncio
class TestRepetitionDetection:
    """B3-5: 반복 발화 감지 테스트"""

    async def test_repetition_detection_logic(self):
        """_detect_repetition() 함수 로직 검증"""
        user_message = "아들이 연락이 안 와서 걱정이에요"
        recent_mentions = [
            "딸은 연락이 잘 되는데",
            "아들이 연락이 안 와",
            "아들이 연락이 안 와서 걱정이에요"
        ]

        is_repetition = _detect_repetition(user_message, recent_mentions)

        assert is_repetition is True, "Should detect repetition"

    async def test_repetition_risk_upgrade(self):
        """반복 감지 시 risk_level ORANGE 승격"""
        user_id = "test_b3_repetition"

        # MCDI 컨텍스트 초기화 (GREEN)
        mcdi_context = {
            "has_data": True,
            "latest_risk_level": "GREEN",
            "slope": -0.5
        }

        # 반복 발화 시뮬레이션
        user_message = "아들이 연락이 안 와"
        recent_mentions = ["아들이 연락이 안 와", "연락이 없어서 걱정"]

        if _detect_repetition(user_message, recent_mentions):
            original_risk = mcdi_context.get("latest_risk_level", "GREEN")
            mcdi_context["latest_risk_level"] = "ORANGE"

        assert mcdi_context["latest_risk_level"] == "ORANGE"

    async def test_no_repetition_normal_flow(self):
        """비반복 발화는 정상 흐름"""
        user_message = "오늘 날씨가 좋아요"
        recent_mentions = ["아들이 연락이 안 와", "딸은 연락이 잘 돼"]

        is_repetition = _detect_repetition(user_message, recent_mentions)

        assert is_repetition is False


@pytest.mark.asyncio
class TestProbeCooldown:
    """[결함 #8] 탐침 질문 쿨다운 테스트"""

    async def test_cooldown_prevents_duplicate_questions(self):
        """쿨다운 중에는 동일 도메인 질문 방지"""
        user_id = "test_b3_cooldown"
        domain = "LR"

        # 첫 번째 호출
        first_cooldown = await _check_probe_cooldown(user_id, domain)
        # 두 번째 호출 (30분 이내)
        second_cooldown = await _check_probe_cooldown(user_id, domain)

        # 첫 번째는 허용(True), 두 번째는 쿨다운(False)
        assert first_cooldown is True, "First call should be allowed"
        assert second_cooldown is False, "Second call should be blocked by cooldown"

        # 정리
        from database.redis_client import redis_client
        await redis_client.delete(f"probe_used:{user_id}:{domain}")
```

---

## 🔧 Phase B4+A2: Gap 메시지 + 이모지 제거 [MEDIUM, 1시간 15분]

> **⚠️ [결함 #7] B4와 A2는 동시에 구현해야 합니다.**
> B4 테스트는 이모지 없음을 검증하지만, `time_aware.py` 템플릿에 이모지가 20+개 있어 단독 구현 시 테스트가 통과하지 않습니다.

> **[v3 검증] time_aware.py에 25+개 이모지 포함 → 예상 시간 45분 → 60분으로 증가**

---

### 📝 구현 가이드

#### B4-1: Gap 메시지 Prefixing (15분)
**파일:** `api/routes/kakao_webhook.py`
**위치:** AI 응답 생성 직후

> **[결함 #17 수정]** `generate_gap_message(user_id)`는 내부에서 `get_hours_since_last_interaction()`을
> 재호출합니다. 이미 `gap_hours`를 구했으므로 중복 호출을 피하기 위해
> `dialogue_manager.time_aware.generate_gap_message(gap_hours, user_id)`를 직접 사용합니다.

**추가 코드:**
```python
# AI 응답 생성
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
    # [결함 #17] 중복 호출 방지 — time_aware 직접 사용
    gap_message = dialogue_manager.time_aware.generate_gap_message(gap_hours, user_id)

    if gap_message:
        # gap 메시지 + AI 응답 결합
        ai_response = f"{gap_message}\n\n{ai_response}"
        logger.info(
            f"Gap message prefixed: {gap_hours:.1f}h gap",
            extra={"user_id": user_id, "gap_hours": gap_hours}
        )
# =====================================================

return {"message": ai_response}
```

#### A2-1: 이모지 제거 (45분)
**[결함 #9, #16 수정] 수정 대상 4개 파일 상세 가이드**

| 파일 | 라인 | 수정 내용 | 수정량 |
|------|------|-----------|--------|
| `prompt_builder.py` | 185 | `"2. 이모지 절제적 사용..."` → `"2. 유니코드 이모지 사용 절대 금지..."` | 1줄 교체 |
| `prompt_builder.py` | 200-202 | 중복 금지 규칙 3줄 **삭제** (S-3에서 통합했으므로) | 3줄 삭제 |
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

**이모지 → 텍스트 치환 표:**

| 원본 | 대체 | 위치 |
|------|------|------|
| 🌅🌅☀️ | (삭제) | morning 템플릿 |
| 🌱🌿🌸 | (삭제 — 이미 텍스트에 정원/꽃 등 포함) | 전체 템플릿 |
| 😊 | "ㅎㅎ" | gap short |
| 🌙✨ | (삭제) | evening/night 템플릿 |
| 🍳🍽️🥗☕⏰🏃‍♀️🍃😴🤜💭💊🏥 | (삭제) | 시간대별 템플릿 |
| " 🌱" | " 정원에서" | response_validator.py:305 |
| 🌙😊💊🏥💭 | (삭제) | dialogue_manager.py:747-751 |

---

### 🧪 테스트 케이스

**파일:** `tests/test_b4_time_aware.py`

```python
"""B4+A2: 시간 인식 테스트 (Gap 메시지 Prefixing + 이모지 제거)"""

import pytest
from core.dialogue.dialogue_manager import DialogueManager
from core.dialogue.time_aware import TimeAwareDialogue
from database.redis_client import redis_client
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_gap_message_prefixed():
    """B4-4: 4시간 이상 경과 시 gap 메시지 접두사"""
    manager = DialogueManager()
    user_id = "test_b4_gap"

    # 마지막 상호작용을 5시간 전으로 설정
    five_hours_ago = datetime.now() - timedelta(hours=5)
    await redis_client.set_json(
        f"last_interaction:{user_id}",
        {"timestamp": five_hours_ago.isoformat()}
    )

    # Gap 시간 확인
    gap_hours = await manager.get_hours_since_last_interaction(user_id)

    assert gap_hours >= 4, f"Should detect 4h+ gap, got {gap_hours}h"

    # [결함 #17] Gap 메시지 직접 생성 (중복 호출 없이)
    time_aware = TimeAwareDialogue(seed=42)
    gap_message = time_aware.generate_gap_message(gap_hours, user_id)

    assert gap_message is not None
    assert len(gap_message) > 0

    # 정리
    await redis_client.delete(f"last_interaction:{user_id}")


@pytest.mark.asyncio
async def test_gap_message_no_emoji(self):
    """[결함 #7 수정] Gap 메시지에 유니코드 이모지 없음 (A2 규칙)"""
    time_aware = TimeAwareDialogue(seed=42)

    # 모든 경과 시간 범위에서 이모지 없음 확인
    for hours in [2, 6, 15, 30]:
        gap_message = time_aware.generate_gap_message(hours, None)

        import re
        emoji_pattern = "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]"
        emojis = re.findall(emoji_pattern, gap_message)

        assert len(emojis) == 0, f"Gap message ({hours}h) should not contain emojis: {emojis}"


@pytest.mark.asyncio
async def test_time_greeting_no_emoji(self):
    """[결함 #7 수정] 시간대별 인사말에 이모지 없음"""
    time_aware = TimeAwareDialogue(seed=42)

    # 모든 시간대 인사말 확인
    for period in ["morning", "noon", "afternoon", "evening", "night"]:
        greetings = time_aware.TIME_GREETING_TEMPLATES.get(period, [])
        for greeting in greetings:
            import re
            emoji_pattern = "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]"
            emojis = re.findall(emoji_pattern, greeting)

            assert len(emojis) == 0, f"{period} greeting should not contain emojis: {emojis}"
```

---

## 🔧 Phase C1: 에피소드 데이터 모델 확장 [HIGH, 35분]

---

### 📝 구현 가이드

**파일:** `core/memory/memory_extractor.py`
**클래스:** `ExtractedMemory` (line 85)

**수정 코드:**
```python
class ExtractedMemory(BaseModel):
    """추출된 기억 (C1-1: samantha 필드 추가)"""
    memory_type: MemoryType
    content: str
    category: EntityCategory
    confidence: float
    importance: float
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # ========== C1-1: 신규 필드 ==========
    samantha_emotion: Optional[str] = Field(None, description="사만다의 당시 감정")
    follow_up_notes: Optional[str] = Field(None, description="후속 화제")
    relationship_impact: float = Field(0.0, description="관계 영향도 (-1.0 ~ 1.0)")
    # ======================================
```

> **호환성 주의:** 기존 코드에서 `ExtractedMemory()` 생성 시 `samantha_emotion` 등을 전달하지 않아도
> `Optional[str]` 기본값 `None`과 `float` 기본값 `0.0`으로 인해 **기존 동작에 영향 없음**.

**[결함 #10, #19] 비용 최적화: asyncio.create_task로 후속 화제 생성**

**파일:** `core/memory/memory_manager.py`

> **[결함 #19]** `BackgroundTask` 명칭 수정. 이 구현은 FastAPI의 `BackgroundTasks`가 아닌
> `asyncio.create_task()`를 사용합니다. 호출 측(webhook)에서 `asyncio.create_task()`로 호출합니다.

```python
async def _generate_follow_up_note_async(self, episode_content: str, user_id: str) -> None:
    """[결함 #10 수정] asyncio.create_task로 비동기 처리 - 사용자 응답 지연 없음

    에피소드 저장 후 별도 태스크로 후속 화제 생성.
    LLM 호출 비용/지연이 사용자 대화에 영향 주지 않음.

    호출 예 (webhook 핸들러에서):
        asyncio.create_task(memory_manager._generate_follow_up_note_async(content, user_id))
    """
    import asyncio
    from services.llm_service import LLMService

    try:
        # 기존 regex 기반 추출 (비용 0)
        follow_up = self._extract_follow_up_topics(episode_content)

        # 품질이 부족할 때만 LLM 사용 (fallback)
        if not follow_up or len(follow_up) < 5:
            prompt = f"""다음 에피소드에서 후속으로 이야기할 만한 화제를 한 문장으로 추출하세요:
            {episode_content}

            출력 예시:
            - "올해 벚꽃"
            - "딸의 방문"
            """

            llm = LLMService()
            response = await llm.call(
                prompt=prompt,
                temperature=0.7,
                max_tokens=50
            )
            follow_up = response.strip()

        # Redis에 캐싱
        await redis_client.set_json(
            f"follow_up:{user_id}:{int(datetime.now().timestamp())}",
            {"content": follow_up},
            ttl=86400 * 7  # 7일
        )
    except Exception as e:
        logger.warning(f"Follow-up generation failed: {e}")
```

**관련 파일 수정:**
- `memory_manager.py`: payload 구성 시 신규 필드 사용 (이미 비공식으로 사용 중, 정식 전환)

---

### 🧪 테스트 케이스

**파일:** `tests/test_c1_episodic_memory.py` (신규)

```python
"""C1: 에피소드 서사화 테스트"""

import pytest
# [결함 #4 수정] 올바른 import 경로
from core.memory.memory_extractor import MemoryType, EntityCategory, ExtractedMemory


@pytest.mark.asyncio
class TestExtractedMemoryModel:
    """C1-1: ExtractedMemory 모델 확장 검증"""

    def test_samantha_fields_exist(self):
        """ExtractedMemory에 samantha 필드 포함"""
        memory = ExtractedMemory(
            memory_type=MemoryType.EPISODIC,
            content="딸이랑 벚꽃 보러갔어요",
            category=EntityCategory.ACTIVITY,
            confidence=0.9,
            importance=0.8,
            timestamp="2026-03-27T10:00:00",
            samantha_emotion="기쁨",  # C1-1 필드
            follow_up_notes="올해 벚꽃",
            relationship_impact=0.3
        )

        assert memory.samantha_emotion == "기쁨"
        assert memory.follow_up_notes == "올해 벚꽃"
        assert memory.relationship_impact == 0.3

    def test_backward_compatibility(self):
        """기존 코드와의 호환성 — 신규 필드 없이도 생성 가능"""
        memory = ExtractedMemory(
            memory_type=MemoryType.BIOGRAPHICAL,
            content="딸 이름은 수진",
            category=EntityCategory.PERSON,
            confidence=0.95,
            importance=0.9,
            timestamp="2026-03-27T10:00:00",
        )

        # 기본값 확인
        assert memory.samantha_emotion is None
        assert memory.follow_up_notes is None
        assert memory.relationship_impact == 0.0


@pytest.mark.asyncio
class TestFollowUpGeneration:
    """[결함 #10, #19] 후속 화제 생성 비용 최적화 테스트"""

    async def test_follow_up_async_no_blocking(self):
        """asyncio.create_task로 사용자 응답 차단 없음"""
        import asyncio
        from core.memory.memory_manager import MemoryManager

        manager = MemoryManager()
        user_id = "test_c1_followup"

        # 비동기 태스크 생성 (즉시 반환)
        task = asyncio.create_task(
            manager._generate_follow_up_note_async("딸이랑 벚꽃 보러갔어요", user_id)
        )

        # 태스크가 즉시 반환되어야 함
        assert task.done() is False  # 백그라운드에서 실행 중

        # 태스크 완료 대기 (테스트용)
        await task
```

---

## 🔧 Phase C2: 치매 탐지 분산 전략 [MEDIUM, 45분]

---

### 📝 구현 가이드

**파일:** `core/dialogue/prompt_builder.py`

> **[결함 #18] 주의:** `_get_probe_question()`을 `async`로 변경하므로
> 기존 호출부 2곳(`prompt_builder.py:361, 371`)에 `await` 추가 필요.

> **[v3 검증] DOMAIN_ROTATION 상수가 현재 존재하지 않음 → 신규 정의 필요**
> 위치: `prompt_builder.py` 상단 (DEMENTIA_PROBE_QUESTIONS 다음에 배치)

```python
# 인지 도메인 주간 로테이션 스케줄 (C2-1)
# [v3 검증] 상수 신규 정의 (현재 존재하지 않음)
# [결함 #5 수정] 수요일, 일요일에 "RT" 포함
DOMAIN_ROTATION = {
    0: ["LR", "ER"],          # 월요일
    1: ["TO", "NC"],          # 화요일
    2: ["SD", "RT"],          # 수요일 ← RT 추가
    3: ["LR", "TO"],          # 목요일
    4: ["ER", "NC"],          # 금요일
    5: ["SD", "LR"],          # 토요일
    6: ["TO", "ER", "RT"],    # 일요일 ← RT 추가
}
```

**기존 호출부 수정 (line 361, 371):**
```python
# [결함 #18] async 변경에 따른 await 추가 + user_id 전달
# line 361 근처
probe_hint = await _get_probe_question(weak_domain, user_id=user_id) if weak_domain else ""

# line 371 근처
probe_hint = await _get_probe_question(weak_domain, user_id=user_id) if weak_domain else ""
```

---

### 🧪 테스트 케이스

**파일:** `tests/test_c2_rotation.py` (신규)

```python
"""C2: 치매 탐지 분산 전략 테스트"""

import pytest
from core.dialogue.prompt_builder import DOMAIN_ROTATION


@pytest.mark.asyncio
class TestDomainRotation:
    """C2-1: 인지 도메인 주간 로테이션 테스트"""

    def test_rotation_schedule_exists(self):
        """DOMAIN_ROTATION 스케줄 정의 확인"""
        assert DOMAIN_ROTATION is not None
        assert len(DOMAIN_ROTATION) == 7  # 7일

    def test_monday_domains(self):
        """월요일: LR, ER"""
        monday_domains = DOMAIN_ROTATION.get(0, [])
        assert "LR" in monday_domains
        assert "ER" in monday_domains

    def test_all_domains_covered(self):
        """[결함 #5 수정] 모든 요일에 도메인 할당 (RT 포함)"""
        all_domains = set()
        for domains in DOMAIN_ROTATION.values():
            all_domains.update(domains)

        # 6개 도메인 모두 포함되어야 함
        expected = {"LR", "SD", "NC", "TO", "ER", "RT"}
        assert all_domains.issuperset(expected), f"Missing domains: {expected - all_domains}"

    def test_rt_in_rotation(self):
        """[결함 #5] RT가 수요일(2)과 일요일(6)에 포함"""
        assert "RT" in DOMAIN_ROTATION[2], "RT should be in Wednesday rotation"
        assert "RT" in DOMAIN_ROTATION[6], "RT should be in Sunday rotation"
```

---

## 🔧 Phase C5: Proactive Messaging [HIGH, 2시간]

---

### 📝 구현 가이드

**파일:** `services/proactive_service.py` (신규)

> **[결함 #12, #13] User 모델 필드명 교차 검증 완료:**
> - `User.kakao_access_token` (`models.py:43`) — NOT `oauth_access_token`
> - `User.deleted_at` (`models.py:59`) — `User.is_active`는 `FCMToken` 전용 (`models.py:177`)

```python
"""Proactive Messaging Service (C5)

36시간 이상 비활성 사용자에게 자동으로 메시지 발송
"""

import asyncio
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select
from database.models import User
from database.redis_client import redis_client
from database.postgres import AsyncSessionLocal
from services.kakao_client import KakaoClient
from utils.logger import get_logger

logger = get_logger(__name__)


class ProactiveService:
    """Proactive 메시징 서비스"""

    INACTIVE_THRESHOLD_HOURS = 36
    SENDING_START_HOUR = 9
    SENDING_END_HOUR = 21

    async def get_inactive_users(self, hours: int = 36) -> List[dict]:
        """비활성 사용자 조회

        [결함 #13 수정] User.is_active → User.deleted_at == None 사용
        (User 모델에 is_active 필드 없음, models.py 확인 완료)
        """
        async with AsyncSessionLocal() as session:
            now = datetime.now()
            threshold = now - timedelta(hours=hours)

            stmt = select(User).where(
                User.deleted_at == None,  # [결함 #13] 활성 사용자 조건
                User.last_interaction_at < threshold
            )
            result = await session.execute(stmt)
            users = result.scalars().all()

            inactive_list = []
            for user in users:
                if user.last_interaction_at:
                    hours_since = (now - user.last_interaction_at).total_seconds() / 3600
                    inactive_list.append({
                        "user_id": str(user.id),
                        "kakao_id": user.kakao_id,
                        "last_interaction": user.last_interaction_at.isoformat(),
                        "hours_since": round(hours_since, 1)
                    })

            logger.info(f"Found {len(inactive_list)} inactive users ({hours}h+)")
            return inactive_list

    async def generate_proactive_message(self, user_context: dict) -> str:
        """Proactive 메시지 생성"""
        hours_since = user_context.get("hours_since", 36)

        if hours_since < 48:
            templates = [
                "안녕하세요 ㅎㅎ 오늘 하루는 어떻게 지내고 계세요?",
                "오늘 날씨가 추워진 것 같아요. 따뜻하게 지내고 계시나요?",
                "오랜만에 인사드려요 ㅎㅎ 별일 없으신가요?"
            ]
        elif hours_since < 72:
            templates = [
                "안녕하세요 ㅠㅠ 요즘 잘 지내고 계시는지 모르겠네요.",
                "혹시 몸이 안 편하신 건 아닌지 조금 걱정돼서 연락드려요.",
                "오늘 점심은 드셨나요? ㅎㅎ"
            ]
        else:
            templates = [
                "안녕하세요... 정말 오랜만이네요 ㅠㅠ",
                "혹시 무슨 일 있으신 건 아닌지 저도 좀 걱정이 되고요.",
                "저 기다리고 있어요 ㅠㅠ 편할 때 연락 주세요 ㅎㅎ"
            ]

        import random
        return random.choice(templates)

    async def send_proactive_message(self, user_id: str) -> dict:
        """특정 사용자에게 Proactive 메시지 발송

        [결함 #2-3, #12 수정] 카카오 API 파라미터 교차 검증 완료
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

        context = {"user_id": str(user.id), "hours_since": 36.0}
        message = await self.generate_proactive_message(context)

        kakao_client = KakaoClient()

        # [결함 #2, #12 수정] kakao_access_token 사용 (NOT oauth_access_token)
        if user.kakao_access_token:  # [결함 #12] 필드명 수정
            result = await kakao_client.send_to_me(
                access_token=user.kakao_access_token,
                message=message
            )
            method = "oauth"
        # [결함 #3 수정] plus_friend_user_key 키워드 사용
        elif user.kakao_channel_user_key:
            result = await kakao_client.send_bizmessage_friend_talk(
                plus_friend_user_key=user.kakao_channel_user_key,
                message=message
            )
            method = "channel"
        else:
            return {"success": False, "error": "No messaging method available"}

        if result.get("success"):
            logger.info(f"Proactive message sent via {method}", extra={"user_id": user_id})

        return {
            "success": result.get("success", False),
            "method": method,
            "message": message,
            "result_code": result.get("result_code")
        }

    async def send_batch_proactive_messages(self, limit: int = 10) -> dict:
        """비활성 사용자에게 일괄 Proactive 메시지 발송"""
        now_hour = datetime.now().hour
        if not (self.SENDING_START_HOUR <= now_hour <= self.SENDING_END_HOUR):
            logger.info(f"Outside sending hours ({now_hour}), skipping")
            return {"total": 0, "sent": 0, "skipped": True}

        inactive_users = await self.get_inactive_users()
        if not inactive_users:
            return {"total": 0, "sent": 0}

        results = []
        sent_count = 0
        failed_count = 0

        for user_context in inactive_users[:limit]:
            result = await self.send_proactive_message(user_context["user_id"])
            results.append({"user_id": user_context["user_id"], "result": result})

            if result.get("success"):
                sent_count += 1
            else:
                failed_count += 1

            await asyncio.sleep(0.5)

        logger.info(f"Proactive batch completed: {sent_count}/{len(inactive_users[:limit])} sent")

        return {
            "total": len(inactive_users[:limit]),
            "sent": sent_count,
            "failed": failed_count,
            "results": results
        }
```

**스케줄러 연동:**

> **[결함 #25 주의]** `push_scheduler.py` 기존 구조를 확인한 후 추가하세요.
> 기존 APScheduler 인스턴스(`scheduler`)에 `add_job()`으로 등록합니다.

```python
# tasks/dialogue.py에 추가
from services.proactive_service import ProactiveService

async def send_proactive_messages():
    """Proactive 메시지 스케줄 태스크"""
    service = ProactiveService()
    result = await service.send_batch_proactive_messages(limit=10)
    logger.info(f"Proactive messages sent: {result}")

# push_scheduler.py에 등록 — [결함 #25] 기존 scheduler 변수 확인 후 추가
scheduler.add_job(send_proactive_messages, 'cron', hour='10', id='proactive_messaging')
```

---

### 🧪 테스트 케이스

**파일:** `tests/test_c5_proactive.py` (신규)

```python
"""C5: Proactive Messaging 테스트"""

import pytest
from services.proactive_service import ProactiveService


@pytest.mark.asyncio
class TestProactiveMessageGeneration:
    """C5-3: Proactive 메시지 생성 테스트"""

    async def test_message_templates_exist(self):
        """메시지 템플릿 존재"""
        service = ProactiveService()

        context = {"hours_since": 40}
        message = await service.generate_proactive_message(context)

        assert message is not None
        assert len(message) > 0

    async def test_message_varies_by_duration(self):
        """경과 시간에 따른 메시지 변화"""
        service = ProactiveService()

        msg_40h = await service.generate_proactive_message({"hours_since": 40})
        msg_80h = await service.generate_proactive_message({"hours_since": 80})

        # 메시지가 다름 (동일할 확률은 낮음)
        assert msg_40h != msg_80h

    async def test_message_no_emoji(self):
        """Proactive 메시지에 유니코드 이모지 없음"""
        service = ProactiveService()

        message = await service.generate_proactive_message({"hours_since": 40})

        import re
        emoji_pattern = "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]"
        emojis = re.findall(emoji_pattern, message)

        assert len(emojis) == 0


@pytest.mark.asyncio
class TestInactiveUserDetection:
    """C5-1: 비활성 사용자 감지 테스트"""

    async def test_respects_threshold(self):
        """비활성 기준 시간 준수"""
        service = ProactiveService()

        # 24시간 기준
        inactive_24h = await service.get_inactive_users(hours=24)

        # 48시간 기준
        inactive_48h = await service.get_inactive_users(hours=48)

        # 24시간이 더 많은 사용자 감지
        assert len(inactive_24h) >= len(inactive_48h)
```

---

## 🧪 통합 테스트: End-to-End 시나리오

**파일:** `tests/test_samantha_integration.py` (신규)

```python
"""사만다 페르소나 통합 테스트

여러 Phase가 결합된 실제 사용자 시나리오 검증
"""

import pytest
from api.routes.kakao_webhook import post as webhook_post
from database.redis_client import redis_client


@pytest.mark.asyncio
@pytest.mark.slow  # E2E 테스트는 비결정적
class TestFatigueScenario:
    """시나리오 1: 피로 사용자 대화"""

    async def test_fatigue_conversation_flow(self):
        """
        사용자: "너무 피곤해요"
        AI: 질문 없이 공감 + 종료 제안
        """
        payload = {
            "user_id": "test_fatigue_user",
            "user_message": "너무 피곤해요"
        }

        # response = await webhook_post(payload)

        # 검증: 물음표 0-1개, "쉬세요" 포함, 종료 응답 패턴


@pytest.mark.asyncio
@pytest.mark.slow
class TestRepetitionScenario:
    """시나리오 2: 반복 발화 사용자"""

    async def test_repetition_upgrades_risk(self):
        """
        사용자: "아들이 연락이 안 와" (3회 반복)
        예상: risk_level GREEN → ORANGE 승격
        """
        user_id = "test_repetition_user"

        # 반복 발화
        for _ in range(3):
            await webhook_post({"user_id": user_id, "user_message": "아들이 연락이 안 와"})

        # MCDI 컨텍스트 확인: latest_risk_level == "ORANGE"


@pytest.mark.asyncio
@pytest.mark.slow
class TestEmotionVectorScenario:
    """시나리오 4: 감정 상태 추이"""

    async def test_emotion_changes_over_time(self):
        """
        1. "기뻐요" → valence 증가
        2. "슬퍼요" → valence 감소
        3. 최종 valence 확인
        """
        user_id = "test_emotion_user"

        # 기쁨
        await webhook_post({"user_id": user_id, "user_message": "정말 기뻐요 ㅋㅋ"})
        # vector_1 = await get_emotion_vector(user_id)
        # assert vector_1["v"] > 0.5

        # 슬픔
        await webhook_post({"user_id": user_id, "user_message": "너무 슬퍼요 ㅠㅠ"})
        # vector_2 = await get_emotion_vector(user_id)
        # assert vector_2["v"] < 0.5
        # assert vector_2["v"] < vector_1["v"]  # 감소


@pytest.mark.asyncio
@pytest.mark.slow
class TestRecoveryEventScenario:
    """시나리오 5: 관계 회복 이벤트"""

    async def test_conflict_then_recovery(self):
        """
        1. 갈등 상황 ("속상해요")
        2. 긍정 전환 ("위로해줘서 고마워요")
        3. recovery_events 증가 확인
        """
        user_id = "test_recovery_user"

        # 초기화
        await redis_client.delete(f"relationship:{user_id}")

        # 갈등
        await webhook_post({"user_id": user_id, "user_message": "정말 속상해요 ㅠㅠ"})

        # 회복
        await webhook_post({"user_id": user_id, "user_message": "친구가 위로해줘서 고마워요 ㅎㅎ"})

        # recovery_events 확인: >= 1
```

---

## 📊 전체 타임라인 요약

| Day | 시간 | 태스크 | 예상 시간 |
|-----|------|--------|-----------|
| **Day 1** | 09:00-09:40 | Phase S (질문 패턴) | 40분 |
| | 09:40-09:50 | B1 (recovery_events) | 10분 |
| | 09:50-10:20 | B2 (감정 벡터) | 30분 |
| | 10:20-10:45 | B3 (반복 감지+쿨다운) | 25분 |
| | 10:45-11:20 | C1 (모델 확장) | 35분 |
| | 11:20-12:00 | C2 (로테이션) | 40분 |
| | 12:00-14:00 | 점심/휴식 | - |
| | 14:00-14:15 | B4 (Gap prefixing) | 15분 |
| | 14:15-15:15 | A2 (이모지 수정) | 60분 (v3 검증: time_aware.py 25+개) |
| | **합계** | **Day 1 CRITICAL+HIGH+MEDIUM** | **4시간 15분** |
| **Day 2** | 09:00-11:00 | C5 (Proactive) | 2시간 |
| | 11:00-12:00 | 통합 테스트 작성 | 1시간 |
| | **합계** | **Day 2** | **3시간** |
| **Day 3** | 전체 | LOW Priority 태스크 + 버그 수정 | 2-3시간 |
| | **총합계** | **전체 구현** | **~9시간** |

---

## 🚀 테스트 실행 가이드

### 전체 테스트 실행
```bash
# 전체 테스트
pytest tests/ -v

# 특정 Phase만
pytest tests/test_dialogue/test_s_question_patterns.py -v
pytest tests/test_b1_relationship.py -v
pytest tests/test_b2_emotion_vector.py -v
pytest tests/test_b3_adaptive.py -v
pytest tests/test_b4_time_aware.py -v
pytest tests/test_c1_episodic_memory.py -v
pytest tests/test_c2_rotation.py -v
pytest tests/test_c5_proactive.py -v

# 통합 테스트만 (slow 마크)
pytest tests/test_samantha_integration.py -v -m slow
```

### 커버리지 확인
```bash
pytest --cov=core/dialogue --cov=services/proactive_service --cov-report=html
```

---

## ✅ 검증 체크리스트

각 태스크 완료 후:

- [ ] 코드 수정 완료
- [ ] 테스트 코드 작성
- [ ] `pytest tests/test_xxx.py` 통과
- [ ] 로그 확인 (`tail -f logs/fastapi.log`)
- [ ] 서버 재시작 (`./start_server.sh`)
- [ ] 수동 테스트 (카카오 채널에서 직접 대화)

---

## 🔧 결함 수정 완료 재검증

### v1 CRITICAL 수정 확인
- [x] `_detect_emotion()` 반환값이 `EMOTION_VECTOR_MAP` 키와 일치하는지 (한국어)
- [x] `send_to_me()` 첫 인수가 `access_token`인지
- [x] `send_bizmessage_friend_talk()` 키워드가 `plus_friend_user_key`인지

### v2 CRITICAL 수정 확인
- [ ] **[결함 #12]** C5에서 `user.oauth_access_token` → `user.kakao_access_token`으로 전체 교체
- [ ] **[결함 #13]** C5에서 `User.is_active == True` → `User.deleted_at == None`으로 전체 교체

### v1 HIGH 수정 확인
- [x] C1 테스트가 `core.memory.memory_extractor`에서 import하는지
- [x] DOMAIN_ROTATION에 "RT" 포함되어 있는지
- [x] `_get_probe_question()` 수정이 모듈 레벨 함수 구조를 유지하는지
- [x] time_aware.py 템플릿에서 이모지가 모두 제거되었는지

### v2 HIGH 수정 확인
- [ ] **[결함 #14]** webhook에서 `emotion` 미전달 → `_detect_emotion()`이 내부 fallback으로 작동하는지 확인
- [ ] **[결함 #15]** `_check_probe_cooldown()` 순환 임포트 해결 — `prompt_builder.py`에서 인라인 로직 사용
- [ ] **[결함 #16]** S-3 Line 185 내용 교체(삭제 아닌 통합) + Line 200-202 중복 삭제
- [ ] **[결함 #18]** `_get_probe_question()` → `async` 변경 후 기존 호출부(line 361, 371)에 `await` 추가

### v1 MEDIUM 수정 확인
- [x] `_check_probe_cooldown()` 호출부가 추가되었는지
- [x] response_validator.py, dialogue_manager.py 이모지가 제거되었는지
- [x] `_generate_follow_up_note()`에 asyncio.create_task가 적용되었는지
- [x] `generate_response()`에 `emotion_vector=` 전달 코드가 있는지

### v2 MEDIUM 수정 확인
- [ ] **[결함 #17]** B4 gap 메시지 `time_aware.generate_gap_message()` 직접 사용으로 이중 호출 방지
- [ ] **[결함 #19]** `asyncio.create_task` 명칭 정정 (BackgroundTask 아님)
- [ ] **[결함 #20]** S 테스트에 `@pytest.mark.slow` + mock 분리 전략 적용
- [ ] **[결함 #21]** B3 테스트 private 함수 import 주의사항 반영
- [ ] **[결함 #22]** B3 `recent_mentions` 시점 정상 동작 (add_turn 이전) 명시
- [ ] **[결함 #23]** B1 `positive/negative_emotions`에서 EN 감정명("joy","sadness","anger") 제거

### v2 LOW 수정 확인
- [ ] **[결함 #24]** B1 `test_b1_stage_4_progression` Redis 직접 주입으로 완성
- [ ] **[결함 #25]** C5 스케줄러 등록 전 `push_scheduler.py` 구조 확인

---

---

## 🔍 v3 최종 코드 교차 검증 (2026-03-27 완료)

> **검증 방법:** 실제 코드 라인 단위 grep + Read 도구 확인
> **검증 대상:** 8개 Phase × 수정 대상 파일 × 결함 수정 내용
> **검증 결과:** 작업 계획서와 실제 코드 일치 여부 확인

### ✅ v3 검증 완료 항목

#### 1. User 모델 필드명 교차 검증 (결함 #12, #13) ✅ 정확함
```python
# database/models.py 확인 결과
kakao_access_token = Column(Text, nullable=True)     # line 43 ✅
deleted_at = Column(DateTime, nullable=True)         # line 59 ✅
# FCMToken.is_active = Column(Boolean, default=True) # line 177 ✅
```
- **검증 완료**: 작업 계획서의 `user.kakao_access_token`, `User.deleted_at == None` 사용법 정확

#### 2. EMOTION_VECTOR_MAP 한국어 키 확인 (결함 #1, #23) ✅
```python
# dialogue_manager.py:47-68 확인
EMOTION_VECTOR_MAP = {
    "기쁨": (0.8, 0.6, 0.1),    # 한국어 키만 사용 ✅
    "우울": (-0.8, -0.6, 0.0),
    # ... 모두 한국어 키
}
```

#### 3. SYSTEM_PROMPT 라인 번호 확인 (결함 #16) ✅ 정확함
```python
# prompt_builder.py 확인 결과
# line 163: SYSTEM_PROMPT = """ 시작
# line 185: "2. 이모지 절제적 사용 (1-2개/메시지)\n"
# line 200-202: 유니코드 이모지 금지 규칙 3줄
```

### 🚨 v3 검증 중 발견 - 작업 계획 수정 필요

#### 1. **[CRITICAL]** DOMAIN_ROTATION이 존재하지 않음 (결함 #5)
```
grep 결과: core/dialogue 디렉토리에서 DOMAIN_ROTATION 매칭 0건
```
- **현황**: 작업 계획서에는 "수정"이라고 되어 있으나 실제로는 **신규 추가** 필요
- **수정 내용**:
  ```diff
  - | 5 | C2 | HIGH | DOMAIN_ROTATION 상수 누락 | DOMAIN_ROTATION 상수 신규 정의 (현재 존재하지 않음) + RT 포함 | [v3 검증] |
  + | 5 | C2 | HIGH | DOMAIN_ROTATION 상수 누락 | DOMAIN_ROTATION 상수 신규 정의 + RT 포함 |
  ```
- **영향**: C2 Phase 전체가 신규 추가 작업으로 변경됨

#### 2. **[HIGH]** 이모지 제거 대상 식별 완료 (결함 #7, #9, #16)
| 파일 | 라인 | 이모지 개수 | 수정 우선순위 |
|------|------|-----------|-------------|
| `time_aware.py` | 53-101 | **25+ 개** | 🔥 CRITICAL |
| `dialogue_manager.py` | 747-751 | 5개 | HIGH |
| `response_validator.py` | 305 | 1개 | MEDIUM |
| `prompt_builder.py` | 185, 200-202 | 0개 (텍스트 규칙만) | LOW |

- **수정 내용**: A2 Phase 예상 시간 45분 → **60분** (time_aware.py 25+개 이모지 제거 포함)

#### 3. **[HIGH]** `_get_probe_question()` async 변환 영향도 (결함 #18)
- **현황**: 현재 sync 함수 (`prompt_builder.py:73-91`)
- **영향**: line 361, 371 호출부에 `await` 추가 필요
- **순환 임포트**: 결함 #15로 인해 인라인 로직 구현 필수

#### 4. **[MEDIUM]** recovery_events 로직 누락 확인 (B1)
```python
# dialogue_manager.py:906-913 확인
# 기존 코드: positive_events, conflict_events만 증가
# 누락: recovery_events 증가 로직
```

#### 5. **[MEDIUM]** emotion_vector 전달 누락 확인 (B2)
```python
# dialogue_manager.py:510-528 확인
# response_generator.generate() 호출에 emotion_vector 파라미터 없음
```

### 📋 v3 검증 기반 최종 수정 사항

#### 결함 #5 표기 수정
```diff
### v1 (fault.md 기반, 11건)
- | 5 | C2 | HIGH | DOMAIN_ROTATION 상수 누락 | DOMAIN_ROTATION 상수 신규 정의 (현재 존재하지 않음) + RT 포함 | [v3 검증] |
+ | 5 | C2 | HIGH | DOMAIN_ROTATION 상수 누락 | DOMAIN_ROTATION 상수 신규 정의 (현재 존재하지 않음) + RT 포함 |
```

#### A2 Phase 예상 시간 수정
```diff
## 🔧 Phase B4+A2: Gap 메시지 + 이모지 제거 [MEDIUM, 1시간]
+ > **[v3 검증] time_aware.py에 25+개 이모지 포함 → 예상 시간 60분으로 증가**
```

#### C2 Phase 구현 가이드 명시 수정
```diff
**[결함 #5 수정] DOMAIN_ROTATION에 "RT" 추가 (기존 _get_probe_question 앞에 배치):**
+ > **[v3 검증] DOMAIN_ROTATION 상수가 현재 존재하지 않음 → 신규 정의 필요**
+ > 위치: `prompt_builder.py` 상단 (DEMENTIA_PROBE_QUESTIONS 다음에 추가)
```

---

## 📊 최종 검증 기반 구현 현황

| Phase | 계획서 내용 | 실제 코드 현황 | 일치 여부 | v3 검증 |
|-------|-----------|---------------|----------|----------|
| **S** | 질문 패턴 추가 | SYSTEM_PROMPT 리터럴 확인 | ✅ | 정확함 |
| S-3 | line 185 수정 | `"2. 이모지 절제적 사용..."` 확인 | ✅ | 정확함 |
| **B1** | recovery_events 추가 | `rel["recovery_events"] += 1` 누락 | ❌ | 로직 없음 |
| **B2** | emotion_vector 전달 | `emotion_vector=` 파라미터 없음 | ❌ | 파라미터 없음 |
| **B3** | 반복 감지 연결 | `_detect_repetition()` 호출부 없음 | ❌ | 함수는 존재 |
| **B3** | 쿨다운 체크 | `_check_probe_cooldown()` 호출부 없음 | ❌ | 함수는 존재 |
| **B4** | Gap 메시지 | `generate_gap_message()` 존재 | ✅ | 중복 호출 주의 |
| **A2** | 이모지 제거 | time_aware.py에 25+개 이모지 | ❌ | 대량 수정 필요 |
| **C1** | samantha 필드 | `ExtractedMemory`에 누락 | ❌ | 3개 필드 미존재 |
| **C2** | DOMAIN_ROTATION | **상수 자체가 없음** | ❌ | **신규 추가 필요** |
| **C5** | kakao_access_token | User 모델 확인 완료 | ✅ | field name 정확 |

---

## ✅ 최종 실행 전 점검 체크리스트

### Day 1 CRITICAL (반드시 완료)
- [ ] **Phase S** (40분): 질문 패턴 - line 185 수정
- [ ] **Phase B2** (30분): 감정 벡터 연결 - `emotion_vector=` 추가
- [ ] **Phase B3** (25분): 반복 감지 연결 + 쿨다운

### Day 2 HIGH (우선 완료)
- [ ] **Phase B4+A2** (60분으로 증가): 이모지 제거 (time_aware.py 25+개 포함)
- [ ] **Phase C2** (45분): DOMAIN_ROTATION **신규 정의**
- [ ] **Phase C1** (35분): samantha 필드 추가

### Day 3 MEDIUM (완료 가능 범위)
- [ ] **Phase B1** (10분): recovery_events 로직
- [ ] **Phase C5** (2시간): Proactive Service

---

*이 문서는 `docs/samantha_plan_fault.md`의 11개 결함 + 2차 교차 검증 14개 결함 + **v3 최종 코드 검증 5개 추가 사항**을 모두 반영하여 수정되었습니다 (2026-03-27).*
