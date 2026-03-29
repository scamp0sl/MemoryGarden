"""
출력 검증기 (Response Validator)

사만다의 응답이 사용자에게 상처를 주지 않도록 검증.

SPEC §2.3.3 기반:
- 부정적 표현 완화
- 응답 길이 제한 (3문장 이하 권장)
- 연속 중복 멘트 방지
- 자연스러운 대화 흐름 유지

Author: Memory Garden Team
Created: 2026-03-26
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# ============================================
# 2. Third-Party Imports
# ============================================

# ============================================
# 3. Local Imports
# ============================================
from database.redis_client import redis_client
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================

# 부정적 단어 목록 (완화 필요)
NEGATIVE_WORDS = [
    "바보", "멍청이", " idiot", "stupid",
    "못해", "不能", "できません",
    "잊어버린", "치매", "dementia",
    "이상한", "이상해", "weird", "strange",
    "문제있", "problem", "issue",
    "틀렸", "wrong", "incorrect"
]

# 문장 길이 제한 (글자 수)
MAX_RESPONSE_LENGTH = 200
PREFERRED_RESPONSE_LENGTH = 100

# 중복 응답 확인 기간 (최근 N개 응답)
DUPLICATE_CHECK_COUNT = 10
DUPLICATE_SIMILARITY_THRESHOLD = 0.8

# Redis 키
LAST_RESPONSES_KEY_PREFIX = "last_responses:"  # last_responses:{user_id}

# 자연스러움 검증 패턴
UNNATURAL_PATTERNS = [
    r"^(네|예|아니오)[\s,.]*$",  # 단답형
    r"^(알겠습니다|그렇군요|그렇습니다)[\s,.]*$",  # 기계식 응답
    r"^.{300,}$",  # 너무 긴 응답
]


# ============================================
# 6. ResponseValidator 클래스
# ============================================

class ResponseValidator:
    """
    출력 검증기

    사만다의 응답을 검증하고 필요시 수정.

    Example:
        >>> validator = ResponseValidator()
        >>> result = await validator.validate(
        ...     user_id="user123",
        ...     response="좋은 아침이에요! 오늘도 함께할 수 있어서 기뻐요."
        ... )
        >>> print(result["is_valid"])  # True
    """

    def __init__(self):
        self.negative_words = NEGATIVE_WORDS
        self.max_length = MAX_RESPONSE_LENGTH
        self.preferred_length = PREFERRED_RESPONSE_LENGTH

    async def validate(
        self,
        user_id: str,
        response: str,
        user_message: Optional[str] = None
    ) -> Dict[str, any]:
        """
        응답 검증 실행

        Args:
            user_id: 사용자 ID
            response: 검증할 응답
            user_message: 사용자 메시지 (선택, 관련성 검증용)

        Returns:
            {
                "is_valid": bool,
                "original": str,
                "modified": str,
                "issues": List[str],
                "warnings": List[str]
            }
        """
        issues = []
        warnings = []
        modified_response = response

        # 1. 부정적 단어 검증
        negative_check = self._check_negative_words(response)
        if negative_check["found"]:
            issues.append(f"부정적 단어 포함: {negative_check['words']}")
            modified_response = self._soften_negative_response(modified_response, negative_check["words"])

        # 2. 길이 검증
        length_check = self._check_length(response)
        if not length_check["is_valid"]:
            issues.append(f"응답 길이 초과: {len(response)}자 (최대 {self.max_length}자)")
            modified_response = self._shorten_response(modified_response)
        elif length_check["is_long"]:
            warnings.append(f"응답이 다소 김: {len(response)}자 (권장 {self.preferred_length}자)")

        # 3. 중복 응답 검증
        duplicate_check = await self._check_duplicate(user_id, response)
        if duplicate_check["is_duplicate"]:
            issues.append(f"최근 응답과 유사함 (유사도: {duplicate_check['similarity']:.2f})")
            modified_response = self._add_variation(modified_response)

        # 4. 자연스러움 검증
        naturalness_check = self._check_naturalness(response)
        if not naturalness_check["is_natural"]:
            issues.append(f"자연스럽지 않은 응답 패턴: {naturalness_check['pattern']}")
            modified_response = self._make_more_natural(modified_response, user_message)

        # 5. 이모지 과다 사용 확인
        emoji_count = self._count_emojis(response)
        if emoji_count > 3:
            warnings.append(f"이모지 과다 사용: {emoji_count}개")

        # 6. 응답 기록 (중복 검증용)
        await self._record_response(user_id, modified_response)

        is_valid = len(issues) == 0

        if not is_valid:
            logger.warning(
                f"Response validation failed for {user_id}",
                extra={
                    "user_id": user_id,
                    "issues": issues,
                    "original": response[:100],
                    "modified": modified_response[:100]
                }
            )
        else:
            logger.debug(f"Response validated successfully for {user_id}")

        return {
            "is_valid": is_valid,
            "original": response,
            "modified": modified_response,
            "issues": issues,
            "warnings": warnings
        }

    def _check_negative_words(self, response: str) -> Dict[str, any]:
        """부정적 단어 검출"""
        found_words = []
        lower_response = response.lower()

        for word in self.negative_words:
            if word.lower() in lower_response:
                found_words.append(word)

        return {
            "found": len(found_words) > 0,
            "words": found_words
        }

    def _soften_negative_response(self, response: str, negative_words: List[str]) -> str:
        """부정적 표현 완화"""
        softened = response

        # 부정적 단어 완화 매핑
        softenings = {
            "바보": "그르신",
            "멍청이": "잠시 잊으신",
            " idiot": " 실수한",
            "stupid": "잠시 혼란스러운",
            "못해": "아직 어려운",
            "不能": "아직 어려운",
            "できません": "아직 어려운",
            "잊어버린": "잠시 기억나지 않는",
            "치매": "기억력",
            "dementia": "기억력",
            "이상한": "달라진",
            "이상해": "달라진",
            "weird": "달라진",
            "strange": "달라진",
            "문제있": "주의가 필요한",
            "problem": "주의가 필요한",
            "issue": "주의가 필요한",
            "틀렸": "다른",
            "wrong": "다른",
            "incorrect": "다른"
        }

        for word in negative_words:
            replacement = softenings.get(word, word)
            softened = softened.replace(word, replacement)

        return softened

    def _check_length(self, response: str) -> Dict[str, any]:
        """응답 길이 검증"""
        length = len(response)
        is_valid = length <= self.max_length
        is_long = length > self.preferred_length

        return {
            "is_valid": is_valid,
            "is_long": is_long,
            "length": length
        }

    def _shorten_response(self, response: str) -> str:
        """응답 길이 단축"""
        # 문장 단위로 분리하여 앞부분만 유지
        sentences = re.split(r'(?<=[.!?])\s+', response)

        # 최대 3문장 또는 preferred_length 문자
        shortened = []
        total_length = 0

        for sentence in sentences:
            if total_length + len(sentence) > self.preferred_length and len(shortened) >= 2:
                break
            shortened.append(sentence)
            total_length += len(sentence)

        result = ' '.join(shortened)

        # 여전히 길면 강제 자름
        if len(result) > self.max_length:
            result = result[:self.max_length - 3] + "..."

        return result

    async def _check_duplicate(self, user_id: str, response: str) -> Dict[str, any]:
        """중복 응답 검증 (Redis)"""
        try:
            redis_key = f"{LAST_RESPONSES_KEY_PREFIX}{user_id}"
            last_responses = await redis_client.get_json(redis_key) or []

            for past_response_obj in last_responses[:DUPLICATE_CHECK_COUNT]:
                # past_response_obj is a dict with 'response' key
                if isinstance(past_response_obj, dict):
                    past_response = past_response_obj.get('response', '')
                else:
                    past_response = str(past_response_obj)

                similarity = self._calculate_similarity(response, past_response)
                if similarity >= DUPLICATE_SIMILARITY_THRESHOLD:
                    return {
                        "is_duplicate": True,
                        "similarity": similarity,
                        "matched_response": past_response
                    }

            return {"is_duplicate": False, "similarity": 0.0}

        except Exception as e:
            logger.error(f"Failed to check duplicate for {user_id}: {e}")
            return {"is_duplicate": False, "similarity": 0.0}

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """두 문자열 간 유사도 계산 (단순 Jaccard)"""
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _add_variation(self, response: str) -> str:
        """중복 응답에 변화 추가"""
        variations = [
            " ㅎㅎ",
            " 정원에서 생각나네요.",
            " 그런데 어떠세요?",
            " 다시 생각해보니"
        ]

        import random
        variation = random.choice(variations)

        # 응답 끝에 변화 추가
        return response.rstrip(".!?") + variation

    def _check_naturalness(self, response: str) -> Dict[str, any]:
        """자연스러움 검증"""
        for pattern in UNNATURAL_PATTERNS:
            if re.match(pattern, response.strip()):
                return {
                    "is_natural": False,
                    "pattern": pattern
                }

        return {"is_natural": True, "pattern": None}

    def _make_more_natural(self, response: str, user_message: Optional[str]) -> str:
        """자연스럽지 않은 응답 개선"""
        # 단답형 응답 확장
        if re.match(r"^(네|예|아니오)[\s,.]*$", response.strip()):
            extensions = [
                " 그렇죠! 더 이야기해 주세요.",
                " 어떻게 생각하시나요?",
                " 자세히 말씀해 주시겠어요?"
            ]
            import random
            return response.strip() + random.choice(extensions)

        # 기계식 응답 완화
        if re.match(r"^(알겠습니다|그렇군요|그렇습니다)[\s,.]*$", response.strip()):
            softeners = [
                " 그렇군요! 정원에서도 비슷한 일이 있었어요.",
                " 알겠어요! 같이 생각해볼까요?",
                " 그렇죠! 더 말씀해 주세요."
            ]
            import random
            return response.strip() + random.choice(softeners)

        return response

    def _count_emojis(self, text: str) -> int:
        """이모지 개수 카운트"""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002600-\U000027BF"  # misc symbols + dingbats (FIXED)
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended
            "]+",
            flags=re.UNICODE
        )
        return len(emoji_pattern.findall(text))

    async def _record_response(self, user_id: str, response: str) -> None:
        """응답 기록 (중복 검증용)"""
        try:
            redis_key = f"{LAST_RESPONSES_KEY_PREFIX}{user_id}"
            last_responses = await redis_client.get_json(redis_key) or []

            # 새 응답 추가
            last_responses.insert(0, {
                "response": response[:100],  # 앞부분 100자만 저장
                "timestamp": datetime.now().isoformat()
            })

            # 최근 N개만 유지
            if len(last_responses) > DUPLICATE_CHECK_COUNT:
                last_responses = last_responses[:DUPLICATE_CHECK_COUNT]

            # Redis에 저장 (24시간 TTL)
            await redis_client.set_json(redis_key, last_responses, ttl=86400)

        except Exception as e:
            logger.error(f"Failed to record response for {user_id}: {e}")


# ============================================
# 7. Export
# ============================================
__all__ = [
    "ResponseValidator",
]

logger.info("Response validator module loaded")
