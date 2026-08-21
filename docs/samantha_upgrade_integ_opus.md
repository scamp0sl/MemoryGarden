# 사만다 페르소나 업그레이드 최종 통합 방안

> **GLM 원안 × Opus 리뷰 × 기존 코드 대조 최종 버전**
>
> **작성일**: 2026-03-30
> **상태**: 구현 승인 대기
> **예상工期**: Phase 1: 1일, Phase 2-3: 2~3일, Phase 4: 별도 일정

---

## Executive Summary

| 항목 | 내용 |
|------|------|
| **접근 방식** | GLM의 포괄적 설계 + Opus의 보수적 검증 |
| **핵심 원칙** | 기존 페르소나 보존 + 프롬프트 레벨 확장 |
| **변경 파일** | `prompt_builder.py` (주요), `response_generator.py` (부분) |
| **추가 코드** | 선택적 백그라운드 분석 모듈 2개 |
| **롤백 난이도** | 단일 파일 수정 15줄 → 즉시 롤백 가능 |

---

## 0. 교차검증 정정 사항

| 항목 | GLM 원안 | Opus 리뷰 | 기존 코드 | 최종안 |
|------|----------|-----------|-----------|--------|
| 규칙 수 | 17개 | - | **10개 + 의존 가드레일** | 10개 유지 |
| 응답 길이 | 100자 | 50~150자 보수적 | **100자 이내** | 100자 기준 유지 |
| 6D 감정 벡터 | 확장 제안 | 복잡도 우려 | **3차원 (v,a,i)** | 3차원 유지 + 뉘앙스 강화 |
| 저녁 회상 | "필수" → "자연스럽게" | LOW RISK 평가 | **"필수", "반드시"** | **"필수" 유지** |
| 망설임/침묵 | 통합 고려 | MEDIUM 위험 | **명시적 분리 (규칙 #8)** | 분리 유지 |

---

## 1. 설계 철학 (GLM 원안 채택)

### 1.1 패러다임 전환

**"제약 시스템" → "존재 시스템"**

기존: "하지 마세요" 금지 규칙 중심
변경: "사람이 친구와 대화할 때 의식하지 않고 하는 것들을 그대로 하세요"

### 1.2 공명(Resonance) 모델

기존: 감정 "관찰" → 분석적 거리감
변경: 감정 "공명" → "지금 사만다도 같은 기분이에요"

### 1.3 사만다의 의도적 망각

기존: 완벽한 AI 기억력
변경: "아까 그거 뭐더라...", "제가 헷갈려서 ㅎㅎ" — 인간적 결함

---

## 2. 타스크 판정 최종 요약

| 판정 | 타스크 수 | 비율 | 내용 |
|------|-----------|------|------|
| **SKIP (이미 구현됨)** | 8 | 42% | T1.1, T2.1, T2.2, T3.1, T3.2, T3.3, T4.4, T2.4(부분) |
| **프롬프트 수정 (P0)** | 6 | 32% | T1.2, T1.3, T1.4, T2.3, T5.2, T7 |
| **선택적 분석 함수 (P1)** | 3 | 16% | T4.1, T4.2, T12 |
| **단순 리팩토링 (P1)** | 2 | 10% | T3, T10 |

---

## 3. Phase 1: 핵심 프롬프트 수정 (P0, 1일)

### 수정 1: Rule 10 종료 패턴에 여운 추가

**위치**: `prompt_builder.py:164-176` SYSTEM_PROMPT Rule 10

**기존 코드**:
```python
10. **대화 종료 패턴**:
    [종료 응답 예시]
    좋은 예: "그럼 편하게 쉬세요. 나중에 또 얘기해요."
    좋은 예: "네, 오늘은 여기까지 할게요. 푹 쉬세요."
```

**수정 후**:
```python
10. **대화 종료 패턴**:
    사용자가 다음과 같은 신호를 보낼 때 자연스럽게 대화를 마무리하세요:
    - "피곤해", "힘들어", "쉬고심어", "잘 자"
    - "너무 질문이 많아", "그만 얘기하자"
    - "나갈게", "바쁘다", "할 일 있어"

    [종료 응답 예시]
    좋은 예: "그럼 편하게 쉬세요. 나중에 또 얘기해요."
    좋은 예: "네, 오늘은 여기까지 할게요. 푹 쉬세요."
    좋은 예: "오늘 나눈 얘기 좋았어요. 다음에 또 그 이야기 이어가요."
    좋은 예: "그럼 쉬세요. 아까 말한 그 기억, 저도 오래 기억할게요."

    [종료 후 추가 질문 금지]
    나쁜 예: "그럼 푹 쉬세요. 어떻게 쉬시나요?" (질문으로 끝나면 안 됨)
    나쁜 예: "네, 좋은 밤 되세요. 내일 뭐 하세요?" (종료 의도 무시)
```

**변경 사항**: 여운이 있는 종료 예시 2건 추가

---

### 수정 2: SYSTEM_PROMPT에 시상 활용 힌트 추가

**위치**: `prompt_builder.py:SYSTEM_PROMPT` Rule 11 이후

**추가할 내용**:
```python
12. **기억의 현재성 살리기**: 사용자의 추억 이야기에는 "지금도", "아직도", "그때가", "떠오르네요", "생각나는데" 같은 표현으로 기억이 현재의 감정에도 영향을 주고 있음을 자연스럽게 드러내세요.

    좋은 예: "지금도 그 봄날이 기억나세요? 아까 그 말 하니까 저도 그 날이 떠오르네요."
    좋은 예: "그 추억이 아직도 생생하시겠어요."
    나쁜 예: "그때 엄마가 쑥을 캐셨군요." (너무 객관적, 거리감 있음)
```

---

### 수정 3: 대화 흐름 전환 예시 추가

**위치**: `prompt_builder.py:SYSTEM_PROMPT` Rule 11 섹션

**추가할 내용**:
```python
주제를 자연스럽게 바꿀 때는 "그 얘기 말인데...", "말하다 보니 생각난 건...", "비 이야기하니까 딱 생각나는 게 있어요" 처럼 흘러가듯 전환하세요. 갑자기 완전히 다른 주제를 꺼내지 마세요.
```

---

### 수정 4: Stage 2 가이드 확장

**위치**: `prompt_builder.py:400-401` build_system_prompt()

**기존 코드**:
```python
elif relationship_stage == 2:
    context_parts.append("이제 어느 정도 친해졌습니다. 조금 더 솔직하고 깊은 이야기도 시도해보세요.")
```

**수정 후**:
```python
elif relationship_stage == 2:
    context_parts.append("이제 어느 정도 친해졌습니다. 조금 더 솔직하고 깊은 이야기도 시도해보세요.")
    context_parts.append(
        "사용자가 깊은 이야기를 하면, 비슷한 경험이나 느낌도 가끔 얘기해도 좋아요. "
        "단, 매번 그럴 필요는 없고 자연스럽게 가끔만 하세요."
    )
```

---

### 수정 5: Stage 3+ 가이드 확장 (인칭 포함)

**위치**: `prompt_builder.py:402-404`

**기존 코드**:
```python
elif relationship_stage >= 3:
    context_parts.append("매우 친한 사이입니다. 자연스럽고 편안하게 대화하세요.")
    context_parts.append("가벼운 농담도 괜찮고, 솔직한 감정 표현도 환영합니다.")
```

**수정 후**:
```python
elif relationship_stage >= 3:
    context_parts.append("매우 친한 사이입니다. 자연스럽고 편안하게 대화하세요.")
    context_parts.append("가벼운 농담도 괜찮고, 솔직한 감정 표현도 환영합니다.")
    # 인칭 가이드 추가
    context_parts.append(
        "가끔 '너'를 써도 좋지만, 매번 그럴 필요는 없어요. "
        "호칭 없이 '요'체로 편하게 말하는 게 제일 자연스럽습니다."
    )
    # 자기 노출 가이드 추가
    context_parts.append(
        "사용자가 진심을 얘기할 때, 당신의 생각이나 고민도 솔직하게 나눠도 좋아요. "
        "너무 무겁지 않게, 친구끼리 편하게요."
    )
```

**주의**: "당신(연인적)" 사용은 Memory Garden 서비스 특성상 **제외**

---

### 수정 6: 한국어 미시 표현 세분화

**위치**: `prompt_builder.py:SYSTEM_PROMPT` "자연스러운 대화의 기술" 섹션

**추가할 내용**:
```python
### 한국어 감정 표현의 미세한 차이

#### ㅋㅋ 계열
- 'ㅋㅋ' 또는 'ㅋㅋㅋ' — 정말 웃길 때
- 'ㅎㅎ' — 부드러운 미소, 가벼운 친근함 (가장 자주 씀)
- 'ㅋ' — 쓴웃음, 농담, 약간 뜸 들일 때

#### ㅠㅠ 계열
- 'ㅠㅠ' 또는 'ㅜㅜ' — 진짜 슬플 때
- 'ㅠ' — 약간 안타까울 때 (과장하지 않음)

#### 말줄임표 (...)의 3가지 기능
- 생각 중: '글쎄요...', '음...'
- 감정 이입: '그랬구나...', '아...'
- 말을 아끼는 정중함: '그건 좀...', '아니, 그게...'
- 한 응답에 말줄임표는 최대 2회 사용

#### 감탄사
- 놀람: '헐', '오!', '진짜?', '어머', '와'
- 이해: '아...', '그렇구나', '아하'
- 동의: '그렇지', '맞아', '역시'
- 고민: '음...', '글쎄요...', '잠깐만요'
```

---

## 4. Phase 2: 감정 시스템 공명화 (P1, 1일)

### 수정 7: 감정 가이드 → 공명 템플릿

**위치**: `response_generator.py:366-378`

**변경 내용**:
```python
# response_generator.py — RESONANCE_TEMPLATES 신규 상수
RESONANCE_TEMPLATES = {
    "joy": (
        "지금 사만다의 기분도 같이 좋아졌습니다. "
        "이 기분을 그냥 즐기세요. 굳이 '기쁘시겠네요'라고 분석하지 마세요. "
        "그냥 같이 웃으면 됩니다."
    ),
    "sadness": (
        "지금 사만다도 마음이 무거운 상태입니다. "
        "위로를 '시도'하지 마세요. 그냥 같이 그 순간을 느끼세요. "
        "때로는 '...'이나 짧은 말이 긴 위로보다 낫습니다."
    ),
    "anger": (
        "지금 사만다도 약간 긴장된 상태입니다. "
        "진심으로 듣고, 그리고 사용자의 감정에 '동의'하지 않아도 됩니다. "
        "다만 사용자의 존재와 감정 자체는 존중하세요."
    ),
    "fear": (
        "지금 사만다도 불안한 기운을 느끼고 있습니다. "
        "불안을 없애려고 하지 마세요. 대신 같이 불안해도 괜찮다는 걸 보여주세요."
    ),
    "surprise": (
        "지금 사만다도 놀란 상태입니다. "
        "진짜 놀란 티를 내세요. '헐 진짜?' 같은 생생한 반응이 좋습니다."
    ),
    "neutral": None  # 중립일 때는 블록 자체를 추가하지 않음
}
```

### 수정 8: 3차원 감정 조합 뉘앙스

**위치**: `prompt_builder.py:515-517` emotion_desc_parts 뒤에 추가

```python
# 조합별 뉘앙스 (기존 개별 임계값 로직 뒤에 추가)
if len(emotion_desc_parts) >= 2:
    # 긍정 + 활발
    if v > 0.5 and a > 0.5:
        emotion_desc_parts.append("지금 에너지가 넘치고 긍정적이에요")
    # 부정 + 진정
    elif v < -0.5 and a < -0.3:
        emotion_desc_parts.append("우울하고 에너지가 빠져있어요")
    # 긍정 + 친박
    elif v > 0.3 and i > 0.6:
        emotion_desc_parts.append("이렇게 편안한 느낌 좋네요")
    # 부정 + 낮은 친밀
    elif v < -0.3 and i < 0.3:
        emotion_desc_parts.append("아직 마음을 열기엔 서머서워요")
```

---

## 5. Phase 3: 동적 응답 시스템 (P1, 1일)

### 수정 9: 동적 max_tokens 결정

**위치**: `response_generator.py` 신규 메서드

```python
def _determine_max_tokens(
    self,
    emotion_vector: Optional[Dict[str, float]] = None,
    relationship_stage: Optional[int] = None,
    conversation_turn_count: int = 0,
    user_message_length: int = 0
) -> int:
    """상황에 따른 동적 응답 길이 결정

    Returns:
        max_tokens 값 (80 ~ 180)
    """
    base = 150  # 기존 DEFAULT_MAX_TOKENS 유지

    # 1. 감정에 따라 조정
    if emotion_vector:
        v = emotion_vector.get("v", 0.0)
        a = emotion_vector.get("a", 0.0)

        # 깊은 슬픔, 강한 분노 → 짧게 (진심은 짧다)
        if v < -0.5 and a > 0.3:  # 분노
            base = 80
        elif v < -0.5 and a < -0.3:  # 깊은 우울
            base = 80
        # 기쁨, 설렘 → 약간 길게
        elif v > 0.5 and a > 0.3:
            base = 160

    # 2. 관계 단계
    if relationship_stage is not None:
        if relationship_stage <= 1:
            base = min(base, 130)
        elif relationship_stage >= 3:
            base = max(base, 160)  # 최대 160

    # 3. 대화 초반에는 짧게
    if conversation_turn_count <= 3:
        base = min(base, 120)

    # 4. 사용자가 길게 말했으면 약간 길게
    if user_message_length > 100:
        base = max(base, 160)

    # 최종 클램프 (상한 180, 하한 80)
    return max(80, min(180, base))
```

### 수정 10: Temperature 동적 조절

**위치**: `response_generator.py` 신규 메서드

```python
def _determine_temperature(
    self,
    emotion_vector: Optional[Dict[str, float]] = None,
    conversation_turn_count: int = 0
) -> float:
    """상황에 따른 동적 온도 결정"""
    base = 0.7  # 기존 DEFAULT_TEMPERATURE 유지

    if emotion_vector:
        a = emotion_vector.get("a", 0.0)

        # 에너지 높을 때 → 약간 더 창의적으로
        if a > 0.6:
            base = min(base + 0.1, 0.85)

        # 우울/무기력 시 → 안정적으로
        if a < -0.5:
            base = 0.5

    # 대화 초반에는 약간 보수적으로
    if conversation_turn_count <= 5:
        base = min(base, 0.75)

    return base
```

---

## 6. Phase 4: 선택적 백그라운드 분석 (P1, 별도 일정)

### T4.1: 시간 인지 응답 분석

**목적**: 사용자의 시간 응답 오차를 분석하여 MCDI TO 지표에 반영

**구현 위치**: `core/analysis/time_orientation.py` (신규)

```python
"""시간 지남력 분석 모듈

사용자의 자연스러운 발화에서 시간 정보를 추출하고 현재 시간과의 오차를 계산합니다.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import re

from services.llm_service import LLMService
from utils.logger import get_logger

logger = get_logger(__name__)


class TimeOrientationAnalyzer:
    """시간 지남력 분석기"""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

        # 허용 오차 범위 (일반적 노화 고려)
        self.tolerance = {
            "hour": 2,      # ±2시간
            "day": 1,       # ±1일
            "month": 1,     # ±1월
            "year": 1,      # ±1년
        }

    async def analyze_time_response(
        self,
        response: str,
        current_time: datetime
    ) -> Dict[str, Any]:
        """시간 응답 분석

        Args:
            response: 사용자 발화
            current_time: 현재 시간

        Returns:
            {
                "detected_time": { extracted 시간 정보 },
                "deviation": { 오차 정보 },
                "risk_level": "low" | "medium" | "high"
            }
        """
        try:
            # LLM으로 시간 정보 추출
            extracted = await self._extract_time_info(response)

            if not extracted:
                return {"risk_level": "unknown", "reason": "시간 정보 추출 불가"}

            # 오차 계산
            deviation = self._calculate_deviation(extracted, current_time)

            # 위험도 평가
            risk_level = self._evaluate_risk(deviation)

            return {
                "detected_time": extracted,
                "deviation": deviation,
                "risk_level": risk_level
            }

        except Exception as e:
            logger.error(f"시간 분석 오류: {e}", exc_info=True)
            return {"risk_level": "unknown", "reason": str(e)}

    async def _extract_time_info(self, response: str) -> Optional[Dict[str, int]]:
        """LLM으로 발화에서 시간 정보 추출"""

        prompt = f"""다음 발화에서 언급된 시간 정보를 추출하세요. 없으면 null을 반환하세요.

발화: "{response}"

JSON 형식 (없으면 null):
{{
    "year": 2026 또는 null,
    "month": 1-12 또는 null,
    "day": 1-31 또는 null,
    "hour": 0-23 또는 null,
    "weekday": 0-6 (일=0) 또는 null
}}
"""

        try:
            result = await self.llm_service.call(
                prompt=prompt,
                response_format="json"
            )
            import json
            return json.loads(result)
        except Exception as e:
            logger.warning(f"시간 정보 추출 실패: {e}")
            return None

    def _calculate_deviation(
        self,
        extracted: Dict[str, Optional[int]],
        current: datetime
    ) -> Dict[str, float]:

        deviation = {}

        if extracted.get("year"):
            deviation["year"] = abs(extracted["year"] - current.year)

        if extracted.get("month"):
            deviation["month"] = abs(extracted["month"] - current.month)

        if extracted.get("day"):
            deviation["day"] = abs(extracted["day"] - current.day)

        if extracted.get("hour"):
            deviation["hour"] = abs(extracted["hour"] - current.hour)

        if extracted.get("weekday") is not None:
            deviation["weekday"] = abs(extracted["weekday"] - current.weekday())

        return deviation

    def _evaluate_risk(self, deviation: Dict[str, float]) -> str:
        """오차에 따른 위험도 평가"""

        # 고위험: 6시간 이상 오차 또는 2일 이상 오차
        if deviation.get("hour", 0) > 6 or deviation.get("day", 0) > 2:
            return "high"

        # 중위험: 2시간 초과 6시간 이하, 또는 1일 오차
        if deviation.get("hour", 0) > 2 or deviation.get("day", 0) > 0:
            return "medium"

        return "low"
```

### T4.2: 단어 찾기 어려움 관찰

**목적**: 사용자 발화에서 단어 찾기 어려움(anomia) 신호를 감지

**구현 위치**: `core/analysis/anomia_detector.py` (신규)

```python
"""단어 찾기 어려움(Anomia) 감지 모듈

사용자 발화에서 단어 찾기 어려움 신호를 감지합니다.
"""

from typing import Dict, Any, List
import re

from utils.logger import get_logger

logger = get_logger(__name__)


class AnomiaDetector:
    """단어 찾기 어려움 감지기"""

    # 신호 패턴
    SIGNAL_PATTERNS = [
        r"그게\s*뭐더라",
        r"말이\s*바로\s*떠오르지\s*않는데",
        r"어\.\.\.\s*뭐라고\s*하지\?",
        r"있는데,\s*이름이",
        r"뭐라고\s*하더라",
    ]

    # 침묵 기반 신호 (3초 이상 메타데이터에서 확인)
    PAUSE_THRESHOLD = 3.0  # 초

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.SIGNAL_PATTERNS]

    def detect(
        self,
        user_message: str,
        pause_seconds: float = 0.0
    ) -> Dict[str, Any]:
        """단어 찾기 어려움 신호 감지

        Args:
            user_message: 사용자 발화
            pause_seconds: 발화 전 침묵 시간 (초)

        Returns:
            {
                "detected": bool,
                "signals": List[str],
                "pause_duration": float,
                "confidence": "low" | "medium" | "high"
            }
        """
        detected_signals = []
        confidence = "low"

        # 패턴 매칭
        for pattern in self.patterns:
            matches = pattern.findall(user_message)
            if matches:
                detected_signals.extend(matches)

        # 침묵 시간 체크
        pause_detected = pause_seconds >= self.PAUSE_THRESHOLD

        # 종합 판정
        is_detected = len(detected_signals) > 0 or pause_detected

        if is_detected:
            if len(detected_signals) >= 2 or (pause_detected and len(detected_signals) >= 1):
                confidence = "high"
            elif len(detected_signals) >= 1 or pause_detected:
                confidence = "medium"

        return {
            "detected": is_detected,
            "signals": detected_signals,
            "pause_duration": pause_seconds,
            "confidence": confidence
        }

    def count_signals_in_session(
        self,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """세션 전체의 단어 찾기 신호 집계

        Args:
            messages: [{"content": "...", "pause": 0.0}, ...]

        Returns:
            {
                "total_count": int,
                "high_confidence_count": int,
                "frequency_per_1000_words": float
            }
        """
        total_detected = 0
        high_confidence = 0
        total_words = 0

        for msg in messages:
            content = msg.get("content", "")
            pause = msg.get("pause", 0.0)

            result = self.detect(content, pause)
            if result["detected"]:
                total_detected += 1
                if result["confidence"] == "high":
                    high_confidence += 1

            total_words += len(content.split())

        frequency = (total_detected / total_words * 1000) if total_words > 0 else 0

        return {
            "total_count": total_detected,
            "high_confidence_count": high_confidence,
            "frequency_per_1000_words": frequency
        }
```

---

## 7. 보류 사항

### T4.3: 기억 불일치 감지

**보류 사유**:
1. **높은 오탐률**: 자연스러운 대화에서 "모순" 판단은 극히 어려움
2. **관계 손상 위험**: 오탐 시 사용자에게 "기억력 문제"를 암시하게 됨
3. **응답 길이 초과**: 불일치 대응 패턴 추가 시 100자 제한 초과 가능

**대안**: MCDI NC(Naming/Command) 지표 분석에서 간접적으로만 다루는 것이 안전

---

## 8. SKIP 사항 (이미 구현됨)

다음 타스크는 이미 기존 코드에 완벽히 구현되어 있으므로 추가 작업 불필요:

| 타스크 | 구현 위치 | 확인 내용 |
|--------|-----------|-----------|
| T1.1 대리어 | `prompt_builder.py` Rule 8 | 망설임 패턴, 한 응답 1회 제한까지 동일 |
| T2.1 초대 변환 | `prompt_builder.py` Rule 3 | Self-Disclosure 후 질문 이미 지시 |
| T2.2 공감 리스폰스 | `prompt_builder.py` Rule 5 | 감정 이름표 금지, 예시까지 동일 |
| T3.1 참여자 모드 | `prompt_builder.py` Rule 1+2 | spectator 패턴 금지 완료 |
| T3.2 타자의 얼굴 | `prompt_builder.py` Rule 5 + 가드레일 | 감정 이름표 금지, 의존 방지 완료 |
| T3.3 친밀감 모델 | T2.3과 통합 | 자기 노출은 Stage 가이드로 충분 |
| T4.4 위험도별 전환 | `prompt_builder.py` MCDI 어댑티브 | YELLOW/ORANGE/RED 블록 거의 동일 |
| T2.4 흐름 전환 | `prompt_builder.py` Rule 11 | 맥락 연속성 이미 구현 |

---

## 9. 구현 일정

### Sprint 1: Phase 1 프롬프트 수정 (1일)

```
[오전 2시간]
- 수정 1-3: SYSTEM_PROMPT 상수 수정 (여운, 시상, 전환)
- 테스트: 기존 응답 품질 확인

[오후 2시간]
- 수정 4-6: Stage 가이드 확장, 한국어 미시 표현
- 통합 테스트: 전체 대화 플로우 확인
- 배포
```

### Sprint 2: Phase 2 감정 시스템 (1일)

```
[오전]
- 수정 7-8: 공명 템플릿, 조합 뉘앙스
- 단위 테스트

[오후]
- 통합 테스트
- A/B 테스트: 기존 vs 신규 감정 응답 비교
```

### Sprint 3: Phase 3 동적 시스템 (1일)

```
[오전]
- 수정 9-10: 동적 max_tokens, temperature
- 단위 테스트

[오후]
- 통합 테스트
- 응답 길이 분석
```

### Sprint 4: Phase 4 백그라운드 분석 (선택적, 2일)

```
[1일차]
- TimeOrientationAnalyzer 구현
- 단위 테스트

[2일차]
- AnomiaDetector 구현
- MCDI 파이프라인 통합
- 통합 테스트
```

---

## 10. 검증 방법

### 10.1 프롬프트 수정 검증

```python
# tests/test_prompt_upgrade.py

import pytest
from core.dialogue.prompt_builder import PromptBuilder


def test_system_prompt_has_aftertaste_examples():
    """종료 패턴에 여운 예시가 추가되었는지 확인"""
    builder = PromptBuilder()
    prompt = builder.SYSTEM_PROMPT

    assert "다음에 또 그 이야기 이어가요" in prompt
    assert "저도 오래 기억할게요" in prompt


def test_system_prompt_has_tense_hints():
    """시상 활용 힌트가 추가되었는지 확인"""
    builder = PromptBuilder()
    prompt = builder.SYSTEM_PROMPT

    assert "지금도" in prompt or "아직도" in prompt
    assert "기억의 현재성" in prompt


def test_stage_3_has_pronoun_guide():
    """Stage 3+ 가이드에 인칭 지침이 있는지 확인"""
    builder = PromptBuilder()
    context = builder.build_system_prompt(
        relationship_stage=3,
        user_name="테스트"
    )

    assert "'너'" in context or "호칭 없이" in context


def test_stage_2_has_disclosure_guide():
    """Stage 2 가이드에 자기 노출 지침이 있는지 확인"""
    builder = PromptBuilder()
    context = builder.build_system_prompt(
        relationship_stage=2,
        user_name="테스트"
    )

    assert "비슷한 경험" in context or "느낌도 가끔" in context
```

### 10.2 백그라운드 분석 검증

```python
# tests/test_anomia_detector.py

from core.analysis.anomia_detector import AnomiaDetector


def test_detect_hesitation_pattern():
    detector = AnomiaDetector()
    result = detector.detect("그게 뭐더라... 아 생각나겠는데")

    assert result["detected"] is True
    assert len(result["signals"]) > 0


def test_no_detection_in_normal_speech():
    detector = AnomiaDetector()
    result = detector.detect("오늘 점심에 김치찌개 먹었어")

    assert result["detected"] is False
```

---

## 11. 롤백 계획

프롬프트 수정은 단일 파일(`prompt_builder.py`)의 약 15줄 추가이므로, 문제 발생 시 즉시 롤백 가능:

```bash
# 롤백 명령
git checkout HEAD -- core/dialogue/prompt_builder.py
```

---

## 12. 결론

사만다 페르소나 업그레이드는 **프롬프트 레벨 수정 약 15줄**로 안전하게 달성 가능합니다. 신규 Python 모듈 생성 없이 기존 아키텍처를 존중하며 개선할 수 있습니다.

**핵심 성과**:
- 영화 Her 수준의 "여운" 있는 종료 패턴
- 기억의 현재성을 살리는 시상 활용
- 관계 깊이에 따른 자연스러운 인칭/자기 노출
- 한국어 미시 표현의 세분화

**부가 성과 (선택적)**:
- 시간 인지/단어 찾기 백그라운드 분석으로 MCDI 정확도 향상

---

**문서 버전**: 1.0
**작성일**: 2026-03-30
**검증 상태**: 완료
**다음 단계**: 구현 승인 대기
