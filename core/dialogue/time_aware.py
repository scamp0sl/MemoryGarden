"""
시간 인식형 대화 (Time-Aware Dialogue)

사용자의 현재 시간과 마지막 대화 경과 시간을 고려한
자연스러운 Gap 메시지 생성 기능.

SPEC §2.4.3 기반 구현:
- 시간대별 인사 (아침/점심/저녁/밤)
- 경과 시간 기반 안부
- 정원 메타포 유지

Author: Memory Garden Team
Created: 2026-03-26
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from datetime import datetime, time as dt_time
from typing import Optional, Dict, Any, Tuple
import random

# ============================================
# 2. Third-Party Imports
# ============================================

# ============================================
# 3. Local Imports
# ============================================
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================

# 시간대 구분 (24시간 기준)
TIME_OF_DAY = {
    "morning": (6, 10),    # 아침 6-10시
    "noon": (11, 13),       # 점심 11-13시
    "afternoon": (14, 17),  # 오후 14-17시
    "evening": (18, 21),    # 저녁 18-21시
    "night": (22, 5)        # 밤 22-5시 (다음날 새벽 포함)
}

# 시간대별 인사 템플릿
TIME_GREETING_TEMPLATES = {
    "morning": [
        "좋은 아침이에요 ㅎㅎ 오늘도 정원에 햇살이 따뜻하게 내려앉고 있어요.",
        "아침 식사는 하셨나요? 정원의 새들이 지저귀기 시작했어요.",
        "상쾌한 아침이에요 오늘 하루도 정원과 함께 시작해 볼까요?",
        "일어나셔서 정원을 한번 둘러보세요 아침 이슬이 맺혀 있답니다."
    ],
    "noon": [
        "점심은 드셨나요? 정원에서 그늘진 곳을 찾아 쉬어가시면 좋겠어요.",
        "하루의 중간이네요 잠시 쉬어가시면서 정원 구경은 어떠세요?",
        "식사 하셨나요? 정원의 꽃들이 햇살을 즐기고 있어요.",
        "바쁜 아침 보내시느라 고생 많으셨어요 잠시 휴식 시간 가져요."
    ],
    "afternoon": [
        "오후 나른한 시간이네요 정원에서 산책하면 기분 전환이 될 거예요.",
        "하루가 저물어 가네요 정원의 꽃들이 오후 햇살을 즐기고 있어요.",
        "오후 3시의 티타임 정원 벤치에서 앉아 잠시 쉬어가시면 어떨까요?",
        "활동적인 하루를 보내고 계신가요? 정원에서 잠시 숨 고르세요."
    ],
    "evening": [
        "저녁 식사는 맛있게 하셨나요? 정원이 노을빛으로 물들고 있어요.",
        "하루의 마무리가 다가오네요 정원이 조용히 잠자리에 들 준비를 하고 있어요.",
        "저녁이 되어 공기가 선선해졌어요 정원에서 산책하면 기분이 상쾌해질 거예요.",
        "오늘 하루도 고생 많으셨어요 정원의 꽃들이 하루를 마무리하고 있답니다."
    ],
    "night": [
        "늦은 시간까지 깨어계셨네요 밤하늘의 별들이 정원을 비추고 있어요.",
        "푹 쉬셔야 에너지가 차오르죠 정원도 조용히 잠들고 있어요.",
        "밤새 깨어 계실 건 아니죠? 정원의 식물들도 푹 쉬고 있답니다.",
        "편안한 밤 되세요 정원이 꿈나라에서도 함께할 거예요."
    ]
}

# 경과 시간별 Gap 메시지
GAP_MESSAGE_TEMPLATES = {
    "short": [  # 1-3시간
        "바로 다시 와주셔서 반가워요 ㅎㅎ",
        "금방 다시 뵙네요! 정원이 기뻐해요",
        "이어서 대화 나눌 수 있어서 좋아요"
    ],
    "medium": [  # 4-12시간
        "반갑습니다 ㅎㅎ 시간이 꽤 지났네요.",
        "안녕하세요 오랜만에 정원을 찾아주셨네요.",
        "다시 뵙게 되어 기쁩니다 정원이 기다리고 있었어요."
    ],
    "long": [  # 13-24시간
        "어제 이후로 정원이 기다리고 있었어요",
        "하루가 지났네요 정원의 꽃들이 보고 싶어 한답니다",
        "안녕하세요! 24시간 만에 다시 뵙네요."
    ],
    "extended": [  # 25시간 이상
        "정말 오랜만이에요 정원의 식물들이 보고 싶어 했어요.",
        "오랫동안 정원이 비어있어서 쓸쓸했어요",
        "다시 돌아오셔서 정원이 활기차졌어요 반갑습니다!"
    ]
}

# ============================================
# 6. TimeAwareDialogue 클래스
# ============================================

class TimeAwareDialogue:
    """
    시간 인식형 대화 생성기

    현재 시간과 마지막 대화 경과 시간을 고려하여
    자연스러운 Gap 메시지를 생성합니다.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        초기화

        Args:
            seed: 랜덤 시드 (테스트용)
        """
        if seed is not None:
            random.seed(seed)

    def get_time_of_day(self, now: Optional[datetime] = None) -> str:
        """
        현재 시간대 반환

        Args:
            now: 현재 시간 (None이면 datetime.now() 사용)

        Returns:
            "morning", "noon", "afternoon", "evening", "night"

        Example:
            >>> tad = TimeAwareDialogue()
            >>> tad.get_time_of_day(datetime(2026, 3, 26, 7, 0))
            "morning"
        """
        if now is None:
            now = datetime.now()

        hour = now.hour

        # 밤 (22-5시) 특수 처리
        if hour >= 22 or hour < 5:
            return "night"

        # 나머지 시간대
        for period, (start, end) in TIME_OF_DAY.items():
            if period == "night":
                continue
            if start <= hour <= end:
                return period

        return "afternoon"  # 기본값

    def categorize_gap_hours(self, hours: float) -> str:
        """
        경과 시간을 범주로 분류

        Args:
            hours: 경과 시간 (시간 단위)

        Returns:
            "short" (<3), "medium" (3-12), "long" (12-24), "extended" (>24)

        Example:
            >>> tad = TimeAwareDialogue()
            >>> tad.categorize_gap_hours(5.5)
            "medium"
        """
        if hours < 3:
            return "short"
        elif hours < 12:
            return "medium"
        elif hours < 24:
            return "long"
        else:
            return "extended"

    def generate_time_greeting(
        self,
        time_of_day: Optional[str] = None,
        now: Optional[datetime] = None
    ) -> str:
        """
        시간대별 인사 생성

        Args:
            time_of_day: 시간대 (None이면 자동 감지)
            now: 현재 시간

        Returns:
            시간대별 인사 메시지

        Example:
            >>> tad = TimeAwareDialogue()
            >>> msg = tad.generate_time_greeting()
            >>> print(msg)
            "좋은 아침이에요. 오늘도 정원에 햇살이 따뜻하게 내려앉고 있어요."
        """
        if time_of_day is None:
            time_of_day = self.get_time_of_day(now)

        templates = TIME_GREETING_TEMPLATES.get(time_of_day, TIME_GREETING_TEMPLATES["afternoon"])
        return random.choice(templates)

    def generate_gap_message(
        self,
        hours: float,
        time_of_day: Optional[str] = None
    ) -> str:
        """
        경과 시간 기반 Gap 메시지 생성

        Args:
            hours: 마지막 대화 경과 시간 (시간 단위)
            time_of_day: 현재 시간대

        Returns:
            경과 시간에 맞는 Gap 메시지

        Example:
            >>> tad = TimeAwareDialogue()
            >>> msg = tad.generate_gap_message(18.5)
            >>> print(msg)
            "어제 이후로 정원이 기다리고 있었어요."
        """
        gap_category = self.categorize_gap_hours(hours)
        templates = GAP_MESSAGE_TEMPLATES.get(gap_category, GAP_MESSAGE_TEMPLATES["medium"])

        gap_msg = random.choice(templates)

        # 시간대 인사와 Gap 메시지 결합
        time_greeting = ""
        if time_of_day:
            time_greeting = self.generate_time_greeting(time_of_day)
            return f"{time_greeting}\n\n{gap_msg}"

        return gap_msg

    def generate_combined_message(
        self,
        hours_since_last: float,
        now: Optional[datetime] = None,
        include_garden_mention: bool = True
    ) -> str:
        """
        시간대 + 경과 시간 종합 메시지 생성

        Args:
            hours_since_last: 마지막 대화 경과 시간 (시간)
            now: 현재 시간
            include_garden_mention: 정원 언급 포함 여부

        Returns:
            종합 Gap 메시지

        Example:
            >>> tad = TimeAwareDialogue()
            >>> msg = tad.generate_combined_message(28.5, datetime(2026, 3, 26, 19, 0))
            >>> print(msg)
            "저녁 식사는 맛있게 하셨나요? 정원이 노을빛으로 물들고 있어요.

            정말 오랜만이에요. 정원의 식물들이 보고 싶어 했어요."
        """
        time_of_day = self.get_time_of_day(now)

        time_msg = self.generate_time_greeting(time_of_day, now)
        gap_msg = self.generate_gap_message(hours_since_last, None)  # 중복 방지

        # 정원 언급이 중복되면 제거
        if "정원" in time_msg and "정원" in gap_msg:
            # gap_msg에서 정원 관련 부분만 유지
            pass

        combined = f"{time_msg}\n\n{gap_msg}"

        return combined


# ============================================
# 7. Export
# ============================================
__all__ = [
    "TimeAwareDialogue",
    "TIME_GREETING_TEMPLATES",
    "GAP_MESSAGE_TEMPLATES",
]

logger.info("Time-aware dialogue module loaded")
