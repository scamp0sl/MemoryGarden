"""
이름/호칭 등 보호 entity 저장 시 사용자 발화 의도 점수 계산.

biographical_facts 저장 전 LLM이 추출한 fact가 진짜 본인 정보인지
사용자 발화 패턴으로 검증하여 잘못된 덮어쓰기 방지.

Author: Memory Garden Team
Created: 2026-05-06
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import re
from typing import Optional, Dict, Any, Tuple

# ============================================
# 2. Local Imports
# ============================================
from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================
# 3. 상수 정의
# ============================================

# 의도 강도 기반 차등 임계점 (Stage 2)
THRESHOLD_FIRST_STORE = 0.3        # 처음 저장
THRESHOLD_SAME_VALUE = 0.3         # 같은 값 재추출 (refresh)
THRESHOLD_OVERWRITE_TENTATIVE = 0.4  # tentative 위에 다른 값
THRESHOLD_OVERWRITE_CONFIRMED = 0.5  # confirmed 위에 다른 값

# Tentative ↔ Confirmed 분기점 (Stage 3)
CONFIRMED_THRESHOLD = 0.5

# 보호 entity (의도 점수를 적용할 대상)
PROTECTED_ENTITIES = {
    "name", "nickname",
    "daughter_name", "son_name", "spouse_name", "grandchild_name",
    "hometown", "occupation",
}

# ============================================
# 4. 점수 가중치
# ============================================

# 명시적 자기 소개 (+0.3) — value 자리에 추출된 값이 들어감
EXPLICIT_INTRODUCTION_PATTERNS = [
    r"내\s*이름은?\s*{v}",
    r"제\s*이름은?\s*{v}",
    r"나는?\s*{v}\s*(이?야|이?다|입니다)",
    r"저는?\s*{v}\s*(이?에요|예요|입니다|이?야)",
]

# 명시적 변경/호칭 요청 (+0.3)
EXPLICIT_CHANGE_PATTERNS = [
    r"{v}\s*(으)?로\s*(바꿔|불러)",
    r"{v}\s*(이)?라고\s*(불러|기억|불러줘)",
    r"이름을?\s*{v}\s*(으)?로",
]

# 정정 의도 표현 (+0.2)
CORRECTION_PATTERNS = [
    r"잘못\s*(알|기억|불렀|인식)",
    r"틀(렸|려|린|리)",
    r"(가|이)?\s*아니(야|라|에요|예요|고)",
    r"회사\s*(분|동료|사람)",
    r"그건\s*(내|제)?\s*이름이?\s*아니",
]

# 1인칭 주어 (+0.1)
# 한국어는 word boundary가 없으므로 단순 prefix 매칭 사용
FIRST_PERSON_PATTERNS = [
    r"(^|\s)(내|나는|저는|제가)",
    r"(^|\s)(나|저)(\s|이|가)",
]

# 호칭 보조어 (-0.3) — 명백한 제3자 컨텍스트
DISQUALIFIER_PATTERNS = [
    # 직책 (확실한 제3자)
    r"{v}\s*(이사|사장|박사|교수|선생|회장|부장|과장|대리|주임|국장|실장)",
    # 관계어
    r"{v}\s*(동료|친구|이모|삼촌|아저씨|아주머니)",
    r"(우리|내|제)\s*(회사|친구|동료)\s*{v}",
    r"{v}\s*(딸|아들|손녀|손자|며느리|사위|어머니|아버지)",
]

# 거부 패턴 (Stage 3) - 이전 tentative fact를 거부
REJECTION_PATTERNS = [
    r"{v}\s*(가|이)?\s*아니(야|라|에요|예요|고)",
    r"(내|제)\s*이름이?\s*아니",
    r"(잘못|틀렸|틀려|아니야|아니라)\s*",
]

# 확정 강조 패턴 (Stage 3) - 이전 tentative fact를 즉시 확정
CONFIRMATION_PATTERNS = [
    r"잘\s*기억",
    r"꼭\s*기억",
    r"맞(아|어|네)",
    r"다시는?\s*(잘못|틀)",
]


# ============================================
# 5. 점수 계산
# ============================================

def _safe_pattern(template: str, value: str) -> str:
    """
    패턴 템플릿의 {v}를 escape된 value로 치환.
    """
    return template.format(v=re.escape(value))


def _match_any(patterns: list, message: str, value: Optional[str] = None) -> bool:
    """
    패턴 리스트 중 하나라도 매치되면 True.
    """
    for tmpl in patterns:
        try:
            pattern = _safe_pattern(tmpl, value) if value and "{v}" in tmpl else tmpl
            if re.search(pattern, message):
                return True
        except re.error:
            continue
    return False


def calculate_intent_score(
    message: str,
    entity: str,
    value: str
) -> Tuple[float, Dict[str, float]]:
    """
    사용자 발화에서 biographical fact 저장 의도 점수 계산.

    Args:
        message: 사용자 메시지 원문
        entity: fact entity (예: "name", "nickname")
        value: 추출된 값 (예: "이정훈")

    Returns:
        (총점, 세부 신호 dict)

    Example:
        >>> calculate_intent_score("내 이름은 이정훈이야", "name", "이정훈")
        (0.4, {"explicit_intro": 0.3, "first_person": 0.1})
    """
    if not message or not value:
        return 0.0, {}

    signals: Dict[str, float] = {}

    if _match_any(EXPLICIT_INTRODUCTION_PATTERNS, message, value):
        signals["explicit_intro"] = 0.3
    elif _match_any(EXPLICIT_CHANGE_PATTERNS, message, value):
        signals["explicit_change"] = 0.3

    if _match_any(CORRECTION_PATTERNS, message):
        signals["correction"] = 0.2

    if _match_any(FIRST_PERSON_PATTERNS, message):
        signals["first_person"] = 0.1

    if _match_any(DISQUALIFIER_PATTERNS, message, value):
        signals["disqualifier"] = -0.3

    score = sum(signals.values())
    return round(score, 2), signals


def detect_rejection(message: str, tentative_value: str) -> bool:
    """
    현재 메시지가 이전 tentative fact를 거부하는지 감지.
    """
    if not message or not tentative_value:
        return False
    for tmpl in REJECTION_PATTERNS:
        try:
            pattern = _safe_pattern(tmpl, tentative_value) if "{v}" in tmpl else tmpl
            if re.search(pattern, message):
                return True
        except re.error:
            continue
    return False


def detect_confirmation(message: str) -> bool:
    """
    현재 메시지가 이전 tentative fact를 강하게 확정하는지 감지.
    """
    if not message:
        return False
    for pat in CONFIRMATION_PATTERNS:
        try:
            if re.search(pat, message):
                return True
        except re.error:
            continue
    return False


# ============================================
# 6. 저장 결정 로직
# ============================================

def evaluate_storage(
    intent_score: float,
    existing_fact: Optional[Dict[str, Any]],
    new_value: str
) -> Tuple[bool, Optional[str], str]:
    """
    임계점 차등 적용 + tentative/confirmed 상태 결정.

    Args:
        intent_score: 의도 점수
        existing_fact: 기존 Redis에 저장된 fact (없으면 None)
        new_value: 새로 추출된 값

    Returns:
        (should_store, status, reason)
        - should_store: True면 저장, False면 거부
        - status: "confirmed" | "tentative" | None
        - reason: 결정 사유 (로깅용)
    """
    # 임계점 결정 (Stage 2 차등)
    if existing_fact is None:
        threshold = THRESHOLD_FIRST_STORE
        scenario = "first_store"
    elif existing_fact.get("value") == new_value:
        threshold = THRESHOLD_SAME_VALUE
        scenario = "same_value"
    elif existing_fact.get("status") == "tentative":
        threshold = THRESHOLD_OVERWRITE_TENTATIVE
        scenario = "overwrite_tentative"
    else:
        threshold = THRESHOLD_OVERWRITE_CONFIRMED
        scenario = "overwrite_confirmed"

    if intent_score < threshold:
        return False, None, f"score {intent_score} < threshold {threshold} ({scenario})"

    # 상태 결정 (Stage 3)
    if scenario == "same_value":
        # 같은 값 재추출은 기존 상태 유지하되, 약한 신호로도 tentative→confirmed 승격은 허용
        if existing_fact.get("status") == "tentative" and intent_score >= CONFIRMED_THRESHOLD:
            return True, "confirmed", f"promote tentative to confirmed (score {intent_score})"
        # 같은 값이면 기존 상태 유지
        return True, existing_fact.get("status", "confirmed"), f"refresh {scenario}"

    # 새 값 저장
    status = "confirmed" if intent_score >= CONFIRMED_THRESHOLD else "tentative"
    return True, status, f"{scenario} score={intent_score}"


def is_protected_entity(entity: str) -> bool:
    """보호 entity 여부 (의도 점수 적용 대상)"""
    return entity in PROTECTED_ENTITIES


# ============================================
# 7. Export
# ============================================
__all__ = [
    "calculate_intent_score",
    "detect_rejection",
    "detect_confirmation",
    "evaluate_storage",
    "is_protected_entity",
    "PROTECTED_ENTITIES",
    "CONFIRMED_THRESHOLD",
]
