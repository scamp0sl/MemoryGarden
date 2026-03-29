# 사만다 페르소나 완성 계획서 (구현 + 테스트)

> **작성일:** 2026-03-27
> **기준 문서:** `docs/samantha_task_fault.md`
> **목표:** 미완료 태스크 구현으로 사만다 페르소나 완성도 100% 달성
> **예상 기간:** 3일 (CRITICAL 1일, HIGH 2일)
> **구성:** 각 Phase별 [구현 가이드] + [테스트 케이스] 포함

---

## 📊 전체 현황

| Phase | 완료도 | 예상 작업량 | 우선순위 |
|-------|--------|-------------|----------|
| **S (질문 패턴)** | 0% (0/3) | **40분** | 🔥 CRITICAL |
| **B1 (관계 모델)** | 93% | 10분 | 🔥 HIGH |
| **B2 (감정 벡터)** | 40% | 30분 | 🔥 HIGH |
| **B3 (MCDI 통합)** | 78% | 20분 | 🔥 HIGH |
| **B4 (시간 인식)** | 75% | 15분 | 🟡 MEDIUM |
| **C1 (에피소드 서사)** | ~70% | 1시간 | 🔥 HIGH |
| **C2 (탐지 분산)** | 0% (0/2) | 45분 | 🟡 MEDIUM |
| **C5 (Proactive)** | 0% (0/6) | 2시간 | 🔥 HIGH |

---

## 🚀 Phase S: 질문 패턴 재설계 [CRITICAL, 40분]

**목표:** 사용자 불만("너무 질문이 많아") 즉시 해결

---

### 📝 구현 가이드

#### S-1. 질문 빈도 제어 규칙 (10분)
**파일:** `core/dialogue/prompt_builder.py`
**위치:** Line 208 (A3 망설임표현 규칙 다음)

**추가할 텍스트:**
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
**위치:** S-1 바로 다음

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
**위치:** Line 185

**기존 코드:**
```python
"2. 이모지 절제적 사용 (1-2개/메시지):\n"
```

**수정:** Line 185 삭제 (Line 200의 "유니코드 이모지 사용 절대 금지"와 충돌)

---

### 🧪 테스트 케이스

**파일:** `tests/test_dialogue/test_s_question_patterns.py`

```python
"""Phase S: 질문 패턴 재설계 테스트"""

import pytest
from core.dialogue.dialogue_manager import DialogueManager


@pytest.mark.asyncio
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
positive_emotions = ["기쁨", "행복", "감동", "설렘", "만족", "즐거움", "joy"]
negative_emotions = ["우울", "슬픔", "불안", "짜증", "스트레스", "분노", "sadness", "anger"]

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

    # Stage 3 도달 조건: 14일 이상 + 긍정 10회 이상
    # ... (테스트 데이터 주입)

    # 갈등 후 회복 이벤트 생성
    await manager.generate_response(user_id=user_id, user_message="너무 속상해요 ㅠㅠ")
    await manager.generate_response(user_id=user_id, user_message="위로해줘서 고마워요 ㅎㅎ")

    # Stage 4 진급 확인
    rel = await manager._get_or_init_relationship(user_id)
    assert rel["stage"] == 4 or rel["recovery_events"] >= 1

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

**Step 1: 감정 인식 헬퍼 추가 (10분)**
```python
async def _detect_emotion(self, text: str) -> str:
    """간단 감정 인식 (B2-7)

    Returns:
        "joy", "sadness", "anger", "fear", "surprise", "neutral" 중 하나
    """
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

    return "neutral"
```

**Step 2: generate_response() 수정 (15분)**
```python
# Line 448-452 근처: 기존 relationship_stage 업데이트 코드 뒤에 추가
if relationship_stage is None:
    relationship_stage = await self._update_relationship_stage(user_id, emotion)

# ========== B2-7: 감정 벡터 실제 갱신 (신규) ==========
detected_emotion = await self._detect_emotion(user_message)
updated_vector = await self._update_emotion_vector(user_id, detected_emotion)
# =====================================================

# Line 455: last_interaction 업데이트
await self.update_last_interaction(user_id)

# response_generator 호출 시 emotion_vector 파라미터 추가
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
            user_message="정말 화가 나요 ㅠㅠ 너무 속상해서..."
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

## 🔧 Phase B3: 반복 발화 감지 연결 [HIGH, 20분]

---

### 📝 구현 가이드

**파일:** `api/routes/kakao_webhook.py`
**위치:** Line 820 직후 (메인 핸들러)

**추가 코드:**
```python
# B3-3: MCDI 컨텍스트 조회 후 응답 생성
mcdi_context = await _get_mcdi_context(user_id)

# ========== B3-5: 반복 발화 감지 후 risk_level 승격 (신규) ==========
# 세션에서 최근 발화 가져오기
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

### 🧪 테스트 케이스

**파일:** `tests/test_b3_adaptive.py` (기존 파일에 추가)

```python
"""B3: 반복 발화 감지 테스트"""

import pytest
from api.routes.kakao_webhook import _detect_repetition


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
```

---

## 🔧 Phase B4: Gap 메시지 Prefixing [MEDIUM, 15분]

---

### 📝 구현 가이드

**파일:** `api/routes/kakao_webhook.py`
**위치:** AI 응답 생성 직후

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
    gap_message = await dialogue_manager.generate_gap_message(user_id)

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

---

### 🧪 테스트 케이스

**파일:** `tests/test_b4_time_aware.py`

```python
"""B4: 시간 인식 테스트 (Gap 메시지 Prefixing)"""

import pytest
from core.dialogue.dialogue_manager import DialogueManager
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

    # Gap 메시지 생성
    gap_message = await manager.generate_gap_message(user_id)

    assert gap_message is not None
    assert len(gap_message) > 0

    # 정리
    await redis_client.delete(f"last_interaction:{user_id}")


@pytest.mark.asyncio
async def test_gap_message_no_emoji(self):
    """Gap 메시지에 유니코드 이모지 없음 (A2 규칙)"""
    manager = DialogueManager()
    user_id = "test_b4_gap_emoji"

    # 마지막 상호작용을 10시간 전으로 설정
    ten_hours_ago = datetime.now() - timedelta(hours=10)
    await redis_client.set_json(
        f"last_interaction:{user_id}",
        {"timestamp": ten_hours_ago.isoformat()}
    )

    # Gap 메시지 생성
    gap_message = await manager.generate_gap_message(user_id)

    # 유니코드 이모지 확인
    import re
    emoji_pattern = "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]"
    emojis = re.findall(emoji_pattern, gap_message)

    assert len(emojis) == 0, f"Gap message should not contain emojis: {emojis}"

    # 한국어 감정 표현은 허용
    assert any(em in gap_message for em in ["ㅎㅎ", "ㅠㅠ"]) or len(emojis) == 0

    # 정리
    await redis_client.delete(f"last_interaction:{user_id}")
```

---

## 🔧 Phase C1: 에피소드 데이터 모델 확장 [HIGH, 20분]

---

### 📝 구현 가이드

**파일:** `core/memory/memory_extractor.py`
**클래스:** `ExtractedMemory`

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

**관련 파일 수정:**
- `memory_manager.py`: payload 구성 시 신규 필드 사용 (이미 비공식으로 사용 중, 정식 전환)

---

### 🧪 테스트 케이스

**파일:** `tests/test_c1_episodic_memory.py`

```python
"""C1: 에피소드 서사화 테스트"""

import pytest
from core.memory.memory_extractor import ExtractedMemory
from database.models import MemoryType


@pytest.mark.asyncio
class TestExtractedMemoryModel:
    """C1-1: ExtractedMemory 모델 확장 검증"""

    def test_samantha_fields_exist(self):
        """ExtractedMemory에 samantha 필드 포함"""
        memory = ExtractedMemory(
            memory_type=MemoryType.EPISODIC,
            content="딸이랑 벚꽃 보러갔어요",
            category="activity",
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
```

---

## 🔧 Phase C2: 치매 탐지 분산 전략 [MEDIUM, 45분]

---

### 📝 구현 가이드

**파일:** `core/dialogue/prompt_builder.py`
**위치:** `_get_probe_question()` 함수 내부

**수정 코드:**
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

def _get_probe_question(
    self,
    domain: str,
    user_context: dict,
    mcdi_context: dict
) -> str:
    """인지 도메인별 탐침 질문 생성 (C2-1 로테이션 추가)"""
    # 요일별 로테이션 확인
    from datetime import datetime
    today_weekday = datetime.now().weekday()

    rotation_domains = DOMAIN_ROTATION.get(today_weekday, ["LR", "SD"])

    # 요일별 허용 도메인이 아니면 빈 문자열 반환
    if domain not in rotation_domains:
        logger.debug(f"Domain {domain} not in today's rotation {rotation_domains}")
        return ""

    # 기존 질문 생성 로직...
```

---

### 🧪 테스트 케이스

**파일:** `tests/test_c2_rotation.py`

```python
"""C2: 치매 탐지 분산 전략 테스트"""

import pytest
from core.dialogue.prompt_builder import PromptBuilder


@pytest.mark.asyncio
class TestDomainRotation:
    """C2-1: 인지 도메인 주간 로테이션 테스트"""

    def test_rotation_schedule_exists(self):
        """DOMAIN_ROTATION 스케줄 정의 확인"""
        from core.dialogue.prompt_builder import DOMAIN_ROTATION

        assert DOMAIN_ROTATION is not None
        assert len(DOMAIN_ROTATION) == 7  # 7일

    def test_monday_domains(self):
        """월요일: LR, ER"""
        from core.dialogue.prompt_builder import DOMAIN_ROTATION

        monday_domains = DOMAIN_ROTATION.get(0, [])
        assert "LR" in monday_domains
        assert "ER" in monday_domains

    def test_all_domains_covered(self):
        """모든 요일에 도메인 할당"""
        from core.dialogue.prompt_builder import DOMAIN_ROTATION

        all_domains = set()
        for domains in DOMAIN_ROTATION.values():
            all_domains.update(domains)

        # 6개 도메인 모두 포함되어야 함
        expected = {"LR", "SD", "NC", "TO", "ER", "RT"}
        assert all_domains.issuperset(expected), f"Missing domains: {expected - all_domains}"
```

---

## 🔧 Phase C5: Proactive Messaging [HIGH, 2시간]

---

### 📝 구현 가이드

**파일:** `services/proactive_service.py` (신규)

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
        """비활성 사용자 조회"""
        async with AsyncSessionLocal() as session:
            now = datetime.now()
            threshold = now - timedelta(hours=hours)

            stmt = select(User).where(
                User.is_active == True,
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
        """특정 사용자에게 Proactive 메시지 발송"""
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

        context = {"user_id": str(user.id), "hours_since": 36.0}
        message = await self.generate_proactive_message(context)

        kakao_client = KakaoClient()

        if user.oauth_access_token:
            result = await kakao_client.send_to_me(user_id=str(user.id), message=message)
            method = "oauth"
        elif user.kakao_channel_user_key:
            result = await kakao_client.send_bizmessage_friend_talk(
                user_key=user.kakao_channel_user_key, message=message
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
```python
# tasks/dialogue.py에 추가
from services.proactive_service import ProactiveService

async def send_proactive_messages():
    """Proactive 메시지 스케줄 태스크"""
    service = ProactiveService()
    result = await service.send_batch_proactive_messages(limit=10)
    logger.info(f"Proactive messages sent: {result}")

# push_scheduler.py에 등록
scheduler.add_job(send_proactive_messages, 'cron', hour='10', id='proactive_messaging')
```

---

### 🧪 테스트 케이스

**파일:** `tests/test_c5_proactive.py`

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

**파일:** `tests/test_samantha_integration.py`

```python
"""사만다 페르소나 통합 테스트

여러 Phase가 결합된 실제 사용자 시나리오 검증
"""

import pytest
from api.routes.kakao_webhook import post as webhook_post
from database.redis_client import redis_client


@pytest.mark.asyncio
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
| | 10:20-10:40 | B3 (반복 감지) | 20분 |
| | 10:40-11:00 | C1 (모델 확장) | 20분 |
| | 11:00-12:00 | C5 (Proactive) | 1시간 |
| | **합계** | **Day 1 CRITICAL+HIGH** | **3시간** |
| **Day 1-2** | 14:00-14:15 | B4 (Gap prefixing) | 15분 |
| | 14:15-15:00 | A2 (이모지 수정) | 45분 |
| | 15:00-15:45 | C2 (로테이션) | 45분 |
| | **합계** | **Day 1-2 MEDIUM** | **1.75시간** |
| **Day 2-3** | 전체 | LOW Priority 태스크 | 2-3시간 |
| | **총합계** | **전체 구현** | **~7시간** |

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

# 통합 테스트만
pytest tests/test_samantha_integration.py -v
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

*이 문서는 `docs/samantha_task_fault.md`를 기반으로 구현과 테스트를 통합하여 작성되었습니다.*
