# 사만다 페르소나 업그레이드: 최종 구현 방안

> **검증 완료 버전** - Opus 제안 × GLM 검증 × 기존 코드베이스 대조
>
> **작성일**: 2026-03-30
> **상태**: 구현 준비 완료
> **예상工期**: 1일 (프롬프트 수정만)

---

## 1. 개요

### 1.1 배경

`samantha_upgrade_opus.md`에서 제안된 16개 타스크를 기존 코드베이스와 1:1 대조한 결과, **50%가 이미 구현되어 있음**이 확인되었습니다. 나머지 50%도 대부분 **프롬프트 레벨 수정**으로 안전하게 적용 가능합니다.

### 1.2 핵심 원칙

1. **신규 Python 모듈 생성 없음** — 모든 개선은 프롬프트 엔지니어링으로 해결
2. **LLM 자연 생성 존중** — 후처리 함수로 응답을 수정하지 않음
3. **기존 페르소나 훼손 방지** — 이미 검증된 규칙을 유지하며 확장만 수행

### 1.3 수정 대상 파일

| 파일 | 수정 범위 | 예상 라인 수 |
|------|-----------|--------------|
| `core/dialogue/prompt_builder.py` | SYSTEM_PROMPT 상수, Stage 가이드 | +15줄 |
| 합계 | **단일 파일 수정** | **+15줄** |

---

## 2. 타스크 판정 요약

| 판정 | 타스크 수 | 비율 | 내용 |
|------|-----------|------|------|
| **SKIP (이미 구현됨)** | 8 | 50% | T1.1, T2.1, T2.2, T3.1, T3.2, T3.3, T4.4, T2.4(부분) |
| **프롬프트 수정** | 4 | 25% | T1.2, T1.3, T1.4, T2.3 |
| **선택적 분석 함수** | 2 | 12.5% | T4.1, T4.2 (백그라운드 MCDI) |
| **기존 유지** | 1 | 6.25% | T3.4 (관계 트래커) |
| **보류** | 1 | 6.25% | T4.3 (기억 불일치) |

---

## 3. 즉시 적용: 프롬프트 수정 (P0)

### 대상: `core/dialogue/prompt_builder.py`

### 수정 1: Rule 10 종료 패턴에 여운 추가

**위치**: `SYSTEM_PROMPT` 상수 내 Rule 10 섹션 (L164-176 근처)

**기존 코드**:
```python
10. **대화 종료 패턴**:
    사용자가 다음과 같은 신호를 보낼 때 자연스럽게 대화를 마무리하세요:
    - "피곤해", "힘들어", "쉬고싶어", "잘 자"
    - "너무 질문이 많아", "그만 얘기하자"
    - "나갈게", "바쁘다", "할 일 있어"

    [종료 응답 예시]
    좋은 예: "그럼 편하게 쉬세요. 나중에 또 얘기해요."
    좋은 예: "네, 오늘은 여기까지 할게요. 푹 쉬세요."

    [종료 후 추가 질문 금지]
    나쁜 예: "그럼 푹 쉬세요. 어떻게 쉬시나요?" (질문으로 끝나면 안 됨)
    나쁜 예: "네, 좋은 밤 되세요. 내일 뭐 하세요?" (종료 의도 무시)
```

**수정 후**:
```python
10. **대화 종료 패턴**:
    사용자가 다음과 같은 신호를 보낼 때 자연스럽게 대화를 마무리하세요:
    - "피곤해", "힘들어", "쉬고싶어", "잘 자"
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

**위치**: `SYSTEM_PROMPT` 상수 내 Rule 11 (맥락 연속성) 이후

**추가할 내용**:
```python
12. **기억의 현재성 살리기**: 사용자의 추억 이야기에는 "지금도", "아직도", "그때가", "떠오르네요", "생각나는데" 같은 표현으로 기억이 현재의 감정에도 영향을 주고 있음을 자연스럽게 드러내세요.

    좋은 예: "지금도 그 봄날이 기억나세요? 아까 그 말 하니까 저도 그 날이 떠오르네요."
    좋은 예: "그 추억이 아직도 생생하시겠어요."
    나쁜 예: "그때 엄마가 쑥을 캐셨군요." (너무 객관적, 거리감 있음)
```

---

### 수정 3: 대화 흐름 전환 예시 추가

**위치**: `SYSTEM_PROMPT` 상수 내 Rule 11 (맥락 연속성) 섹션에 추가

**추가할 내용**:
```python
주제를 자연스럽게 바꿀 때는 "그 얘기 말인데...", "말하다 보니 생각난 건...", "비 이야기하니까 딱 생각나는 게 있어요" 처럼 흘러가듯 전환하세요. 갑자기 완전히 다른 주제를 꺼내지 마세요.
```

---

### 수정 4: Stage 2 가이드 확장

**위치**: `build_system_prompt()` 함수 내 Stage 가이드 섹션 (L400 근처)

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

**위치**: `build_system_prompt()` 함수 내 Stage 가이드 섹션 (L403 근처)

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

**주의**: "당신(연인적)" 사용은 Memory Garden 서비스 특성(고령층 치매 조기 감지)상 **제외**

---

## 4. 선택적 적용: 백그라운드 분석 함수 (P1)

### T4.1: 시간 인지 응답 분석

**목적**: 사용자의 시간 응답 오차를 분석하여 MCDI TO(Time Orientation) 지표에 반영

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

**통합 방안**: `core/analysis/analyzer.py`의 MCDI 분석 시 `TimeOrientationAnalyzer`를 호출하여 TO 지표에 반영

---

### T4.2: 단어 찾기 어려움 관찰

**목적**: 사용자 발화에서 단어 찾기 어려움(anomia) 신호를 감지하여 MCDI NC(Naming/Command) 지표에 반영

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

**통합 방안**: `core/analysis/analyzer.py`의 MCDI 분석 시 `AnomiaDetector`를 호출하여 NC 지표에 반영

---

## 5. 보류 사항

### T4.3: 기억 불일치 감지

**보류 사유**:
1. **높은 오탐률**: 자연스러운 대화에서 "모순" 판단은 극히 어려움
2. **관계 손상 위험**: 오탐 시 사용자에게 "기억력 문제"를 암시하게 됨
3. **응답 길이 초과**: 불일치 대응 패턴 추가 시 100자 제한 초과 가능

**대안**: MCDI NC(Naming/Command) 지표 분석에서 간접적으로만 다루는 것이 안전

---

## 6. SKIP 사항 (이미 구현됨)

다음 타스크는 이미 기존 코드에 완벽히 구현되어 있으므로 추가 작업 불필요:

| 타스크 | 구현 위치 | 확인 내용 |
|--------|-----------|-----------|
| T1.1 대리어 | `prompt_builder.py` Rule 7 | 망설임 패턴, 한 응답 1회 제한까지 동일 |
| T2.1 초대 변환 | `prompt_builder.py` Rule 3 | Self-Disclosure 후 질문 이미 지시 |
| T2.2 공감 리스폰스 | `prompt_builder.py` Rule 5 | 감정 이름표 금지, 예시까지 동일 |
| T3.1 참여자 모드 | `prompt_builder.py` Rule 1+2 | spectator 패턴 금지 완료 |
| T3.2 타자의 얼굴 | `prompt_builder.py` Rule 5 + 가드레일 | 감정 이름표 금지, 의존 방지 완료 |
| T3.3 친밀감 모델 | T2.3과 통합 | 자기 노출은 Stage 가이드로 충분 |
| T4.4 위험도별 전환 | `prompt_builder.py` MCDI 어댑티브 | YELLOW/ORANGE/RED 블록 거의 동일 |
| T2.4 흐름 전환 | `prompt_builder.py` Rule 11 | 맥락 연속성 이미 구현 |

---

## 7. 구현 일정

### Sprint 1: 프롬프트 수정 (1일)

```
[오전 2시간]
- 수정 1-3: SYSTEM_PROMPT 상수 수정 (여운, 시상, 전환)
- 테스트: 기존 응답 품질 확인

[오후 2시간]
- 수정 4-5: Stage 가이드 확장
- 통합 테스트: 전체 대화 플로우 확인
- 배포
```

### Sprint 2: 백그라운드 분석 (선택적, 별도 일정)

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

## 8. 검증 방법

### 8.1 프롬프트 수정 검증

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

### 8.2 백그라운드 분석 검증

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

## 9. 롤백 계획

프롬프트 수정은 단일 파일(`prompt_builder.py`)의 15줄 추가이므로, 문제 발생 시 즉시 롤백 가능:

```bash
# 롤백 명령
git checkout HEAD -- core/dialogue/prompt_builder.py
```

---

## 10. 결론

사만다 페르소나 업그레이드는 **프롬프트 레벨 수정 15줄**로 안전하게 달성 가능합니다. 신규 Python 모듈 생성 없이 기존 아키텍처를 존중하며 개선할 수 있습니다.

**핵심 성과**:
- 영화 Her 수준의 "여운" 있는 종료 패턴
- 기억의 현재성을 살리는 시상 활용
- 관계 깊이에 따른 자연스러운 인칭/자기 노출

**부가 성과 (선택적)**:
- 시간 인지/단어 찾기 백그라운드 분석으로 MCDI 정확도 향상

---

**문서 버전**: 1.0
**작성일**: 2026-03-30
**검증 상태**: 완료
**다음 단계**: 구현 승인 대기
