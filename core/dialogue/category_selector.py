"""
대화 카테고리 선택기

SPEC §2.1.1 기반: 6개 카테고리를 약한 지표 우선으로 선택.

카테고리 정의:
    - REMINISCENCE    (회상의 꽃밭): LR + ER 연결 → 주 2회
    - DAILY_EPISODIC  (오늘의 한 접시): ER 중심 → 주 3회
    - NAMING          (이름 꽃밭): NC → 주 1회
    - TEMPORAL        (시간의 나침반): TO → 주 2회
    - VISUAL          (그림 읽기 놀이): LR + SD → 주 1회 (이미지 업로드)
    - CHOICE          (선택의 정원): NC + SD → 주 1회 (버튼 선택)

선택 알고리즘:
    1. 최근 14일 MCDI 지표별 평균 산출
    2. 지표 점수 낮은 순으로 카테고리 후보 정렬
    3. 이번 주 카테고리 사용 횟수(Redis) 조회
    4. 주 제한 초과 카테고리 제외 후 최우선 선택
    5. 모든 카테고리 제한 초과 시 → DAILY_EPISODIC (가장 빈도 높음)

Author: Memory Garden Team
Created: 2026-02-27
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ============================================
# 2. Third-Party Imports
# ============================================
from sqlalchemy import select, and_

# ============================================
# 3. Local Imports
# ============================================
from database.postgres import AsyncSessionLocal
from database.models import AnalysisResult
from database.redis_client import redis_client
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 카테고리 상수 정의
# ============================================

# 카테고리 ID 상수
CATEGORY_REMINISCENCE = "REMINISCENCE"     # 회상의 꽃밭
CATEGORY_DAILY_EPISODIC = "DAILY_EPISODIC"  # 오늘의 한 접시
CATEGORY_NAMING = "NAMING"                  # 이름 꽃밭
CATEGORY_TEMPORAL = "TEMPORAL"              # 시간의 나침반
CATEGORY_VISUAL = "VISUAL"                  # 그림 읽기 놀이
CATEGORY_CHOICE = "CHOICE"                  # 선택의 정원

# 카테고리 → 측정 지표 매핑 (주요 지표가 낮을수록 해당 카테고리 우선)
CATEGORY_INDICATOR_MAP: Dict[str, List[str]] = {
    CATEGORY_REMINISCENCE:   ["ER", "LR"],   # 일화 기억 + 어휘 풍부도
    CATEGORY_DAILY_EPISODIC: ["ER"],          # 일화 기억 중심
    CATEGORY_NAMING:         ["NC"],          # 서사 일관성 (이름 명명)
    CATEGORY_TEMPORAL:       ["TO"],          # 시간 지남력
    CATEGORY_VISUAL:         ["LR", "SD"],    # 어휘 풍부도 + 의미적 표류
    CATEGORY_CHOICE:         ["NC", "SD"],    # 서사 일관성 + 의미적 표류
}

# 카테고리 주간 최대 사용 횟수 (SPEC §2.1.1 완화 - 무제한 라우팅)
CATEGORY_WEEKLY_LIMIT: Dict[str, int] = {
    CATEGORY_REMINISCENCE:   9999,
    CATEGORY_DAILY_EPISODIC: 9999,
    CATEGORY_NAMING:         9999,
    CATEGORY_TEMPORAL:       9999,
    CATEGORY_VISUAL:         9999,
    CATEGORY_CHOICE:         9999,
}

# 카테고리 한국어 표시명
CATEGORY_DISPLAY_NAMES: Dict[str, str] = {
    CATEGORY_REMINISCENCE:   "회상의 꽃밭",
    CATEGORY_DAILY_EPISODIC: "오늘의 한 접시",
    CATEGORY_NAMING:         "이름 꽃밭",
    CATEGORY_TEMPORAL:       "시간의 나침반",
    CATEGORY_VISUAL:         "그림 읽기 놀이",
    CATEGORY_CHOICE:         "선택의 정원",
}

# Redis 키 접두사
CATEGORY_USAGE_KEY_PREFIX = "category_usage:"  # category_usage:{user_id}:{week_key}
CATEGORY_USAGE_DAILY_KEY_PREFIX = "category_usage_daily:"  # category_usage_daily:{user_id}:{day_key}

# 분석 조회 기간
ANALYSIS_LOOKBACK_DAYS = 14


# ============================================
# 6. CategorySelector 클래스
# ============================================

class CategorySelector:
    """
    대화 카테고리 선택기

    약한 MCDI 지표를 집중 훈련할 수 있는 카테고리를 우선 선택.
    주간 빈도 제한을 적용하여 균형 잡힌 대화를 유지.

    Example:
        >>> selector = CategorySelector()
        >>> category = await selector.select(user_id="user_123")
        >>> print(category)  # "TEMPORAL"
    """

    async def select(
        self,
        user_id: str,
        force_category: Optional[str] = None
    ) -> str:
        """
        다음 대화 카테고리 선택.

        Args:
            user_id: 사용자 ID
            force_category: 강제 카테고리 지정 (테스트/관리자용)

        Returns:
            카테고리 ID 문자열 (예: "TEMPORAL")
        """
        if force_category and force_category in CATEGORY_WEEKLY_LIMIT:
            logger.info(
                f"Category forced: {force_category}",
                extra={"user_id": user_id}
            )
            return force_category

        # 1. 최근 14일 지표별 평균 조회
        indicator_scores = await self._fetch_indicator_averages(user_id)

        # 2. 주간 및 일간 카테고리 사용 횟수 조회
        weekly_usage = await self._fetch_weekly_usage(user_id)
        daily_usage = await self._fetch_daily_usage(user_id)

        # 3. 카테고리 우선순위 결정
        category = self._select_category(indicator_scores, weekly_usage, daily_usage)

        # 4. 사용 횟수 증가 (Redis)
        await self._increment_usage(user_id, category)

        logger.info(
            f"Category selected: {category} ({CATEGORY_DISPLAY_NAMES[category]})",
            extra={
                "user_id": user_id,
                "category": category,
                "indicator_scores": indicator_scores,
                "weekly_usage": weekly_usage,
            }
        )

        return category

    async def _fetch_indicator_averages(
        self, user_id: str
    ) -> Dict[str, float]:
        """
        최근 14일 MCDI 지표별 평균 점수 조회.

        Args:
            user_id: 사용자 ID

        Returns:
            {"LR": 78.5, "SD": 72.0, "NC": 85.0, "TO": 68.0, "ER": 71.0, "RT": 90.0}
            조회 실패 또는 데이터 없으면 중립값(75.0)으로 채움
        """
        default_scores = {k: 75.0 for k in ["LR", "SD", "NC", "TO", "ER", "RT"]}

        try:
            cutoff = datetime.now() - timedelta(days=ANALYSIS_LOOKBACK_DAYS)

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(AnalysisResult).where(
                        and_(
                            AnalysisResult.user_id == user_id,
                            AnalysisResult.created_at >= cutoff,
                        )
                    ).order_by(AnalysisResult.created_at.desc()).limit(50)
                )
                analyses = result.scalars().all()

            if not analyses:
                logger.debug(
                    f"No analysis data found for user {user_id}, using defaults",
                    extra={"user_id": user_id}
                )
                return default_scores

            # 지표별 합산 (AnalysisResult 개별 컬럼 사용)
            sums: Dict[str, float] = {k: 0.0 for k in ["LR", "SD", "NC", "TO", "ER", "RT"]}
            counts: Dict[str, int] = {k: 0 for k in sums}
            _col_map = {
                "LR": "lr_score", "SD": "sd_score", "NC": "nc_score",
                "TO": "to_score", "ER": "er_score", "RT": "rt_score",
            }

            for analysis in analyses:
                for indicator, col_name in _col_map.items():
                    score = getattr(analysis, col_name, None)
                    if score is not None:
                        sums[indicator] += float(score)
                        counts[indicator] += 1

            # 평균 계산 (데이터 없는 지표는 중립값 75.0)
            averages = {}
            for indicator in sums:
                if counts[indicator] > 0:
                    averages[indicator] = round(sums[indicator] / counts[indicator], 2)
                else:
                    averages[indicator] = 75.0

            logger.debug(
                f"Indicator averages for {user_id}: {averages}",
                extra={"user_id": user_id, "analysis_count": len(analyses)}
            )

            return averages

        except Exception as e:
            logger.error(
                f"Failed to fetch indicator averages for {user_id}: {e}",
                exc_info=True
            )
            return default_scores

    async def _fetch_weekly_usage(self, user_id: str) -> Dict[str, int]:
        """
        이번 주 카테고리 사용 횟수 조회 (Redis).

        Returns:
            {"REMINISCENCE": 1, "DAILY_EPISODIC": 2, ...}
        """
        week_key = self._get_week_key()
        redis_key = f"{CATEGORY_USAGE_KEY_PREFIX}{user_id}:{week_key}"

        try:
            redis_conn = await redis_client.get_client()
            if redis_conn is None:
                return {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}

            raw = await redis_conn.get(redis_key)
            if not raw:
                return {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}

            usage = json.loads(raw)
            # 존재하지 않는 카테고리는 0으로 채움
            return {cat: usage.get(cat, 0) for cat in CATEGORY_WEEKLY_LIMIT}

        except Exception as e:
            logger.error(f"Failed to fetch weekly usage for {user_id}: {e}")
            return {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}

    async def _fetch_daily_usage(self, user_id: str) -> Dict[str, int]:
        """일간 카테고리 사용 횟수 조회 (Redis)"""
        day_key = self._get_day_key()
        redis_key = f"{CATEGORY_USAGE_DAILY_KEY_PREFIX}{user_id}:{day_key}"
        try:
            redis_conn = await redis_client.get_client()
            if redis_conn is None:
                return {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}
            raw = await redis_conn.get(redis_key)
            if not raw:
                return {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}
            usage = json.loads(raw)
            return {cat: usage.get(cat, 0) for cat in CATEGORY_WEEKLY_LIMIT}
        except Exception as e:
            logger.error(f"Failed to fetch daily usage for {user_id}: {e}")
            return {cat: 0 for cat in CATEGORY_WEEKLY_LIMIT}

    def _select_category(
        self,
        indicator_scores: Dict[str, float],
        weekly_usage: Dict[str, int],
        daily_usage: Dict[str, int],
    ) -> str:
        """
        지표 점수와 사용량 기반으로 카테고리 선택.

        알고리즘:
            1. 주간 제한 초과 카테고리 제외
            2. 저녁(18:00~23:59)이고 당일 사용 안 한 카테고리가 있다면 0순위
            3. 사용량(적은 순) 1순위 -> 약점 점수(낮은 순) 2순위
        """
        now_hour = datetime.now().hour
        is_evening = 18 <= now_hour <= 23

        # (저녁 미사용 우선플래그, 주간 사용량, 약점 점수, 카테고리ID)
        category_weakness: List[Tuple[int, int, float, str]] = []

        for category, indicators in CATEGORY_INDICATOR_MAP.items():
            if weekly_usage.get(category, 0) >= CATEGORY_WEEKLY_LIMIT[category]:
                continue

            scores = [indicator_scores.get(ind, 75.0) for ind in indicators]
            avg_score = sum(scores) / len(scores)

            w_usage = weekly_usage.get(category, 0)
            d_usage = daily_usage.get(category, 0)

            # 저녁 18시~24시 && 오늘 0번 라우팅되었으면 최우선 0, 아니면 1
            missing_in_evening = 0 if (is_evening and d_usage == 0) else 1

            category_weakness.append((missing_in_evening, w_usage, avg_score, category))

        if not category_weakness:
            logger.warning("All categories at weekly limit, defaulting to DAILY_EPISODIC")
            return CATEGORY_DAILY_EPISODIC

        # 0순위: 저녁미사용(0우선), 1순위: 주간사용량(적은순), 2순위: 약점점수(낮은순)
        category_weakness.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

        selected = category_weakness[0][3]
        return selected

    async def _increment_usage(self, user_id: str, category: str) -> None:
        """
        Redis에 카테고리 사용 횟수 1 증가. TTL은 이번 주 남은 초로 설정.

        Args:
            user_id: 사용자 ID
            category: 선택된 카테고리 ID
        """
        week_key = self._get_week_key()
        redis_key = f"{CATEGORY_USAGE_KEY_PREFIX}{user_id}:{week_key}"

        try:
            redis_conn = await redis_client.get_client()
            if redis_conn is None:
                return

            # 현재 값 조회
            raw = await redis_conn.get(redis_key)
            usage = json.loads(raw) if raw else {}

            # 주간 카운트 증가
            usage[category] = usage.get(category, 0) + 1
            ttl_seconds = self._seconds_until_next_monday()
            await redis_conn.setex(redis_key, ttl_seconds, json.dumps(usage))

            # 일간 카운트 증가
            day_key = self._get_day_key()
            daily_redis_key = f"{CATEGORY_USAGE_DAILY_KEY_PREFIX}{user_id}:{day_key}"
            raw_daily = await redis_conn.get(daily_redis_key)
            daily_usage = json.loads(raw_daily) if raw_daily else {}
            daily_usage[category] = daily_usage.get(category, 0) + 1
            ttl_daily = self._seconds_until_midnight()
            await redis_conn.setex(daily_redis_key, ttl_daily, json.dumps(daily_usage))

        except Exception as e:
            logger.error(f"Failed to increment category usage for {user_id}: {e}")

    def _get_week_key(self) -> str:
        """이번 주 식별자 반환 (월요일 기준 주차)"""
        return datetime.now().strftime("%Y-W%W")

    def _get_day_key(self) -> str:
        """오늘 식별자 반환"""
        return datetime.now().strftime("%Y-%m-%d")

    def _seconds_until_next_monday(self) -> int:
        """
        다음 주 월요일 자정까지 남은 초.
        Redis TTL에 사용.
        """
        now = datetime.now()
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # 오늘이 월요일이면 다음 월요일

        next_monday = (now + timedelta(days=days_until_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return max(1, int((next_monday - now).total_seconds()))

    def _seconds_until_midnight(self) -> int:
        """오늘 자정까지 남은 초"""
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return max(1, int((tomorrow - now).total_seconds()))

    def get_category_info(self, category: str) -> Dict:
        """
        카테고리 메타정보 반환.

        Args:
            category: 카테고리 ID

        Returns:
            {
                "id": "TEMPORAL",
                "name": "시간의 나침반",
                "indicators": ["TO"],
                "weekly_limit": 2,
                "is_image": False,
                "is_button": False,
            }
        """
        return {
            "id": category,
            "name": CATEGORY_DISPLAY_NAMES.get(category, category),
            "indicators": CATEGORY_INDICATOR_MAP.get(category, []),
            "weekly_limit": CATEGORY_WEEKLY_LIMIT.get(category, 1),
            "is_image": category == CATEGORY_VISUAL,
            "is_button": category == CATEGORY_CHOICE,
        }


# ============================================
# 7. 편의 함수
# ============================================

def get_category_display_name(category: str) -> str:
    """카테고리 한국어 표시명 반환."""
    return CATEGORY_DISPLAY_NAMES.get(category, category)


def get_category_prompt_hint(category: str) -> str:
    """
    카테고리별 프롬프트 힌트 반환.
    prompt_builder.py에서 활용.

    Returns:
        프롬프트에 삽입할 카테고리 안내 문구
    """
    hints = {
        CATEGORY_REMINISCENCE: (
            "사용자의 오래된 추억(어린 시절, 가족, 고향, 직업)을 회상하도록 유도하세요. "
            "구체적인 인물·장소·사건을 이끌어내는 열린 질문을 하세요."
        ),
        CATEGORY_DAILY_EPISODIC: (
            "오늘 하루의 일상(식사, 날씨, 기분, 만난 사람)에 대해 대화하세요. "
            "최근 경험을 생생하게 묘사하도록 유도하세요."
        ),
        CATEGORY_NAMING: (
            "가족, 지인, 유명인, 식물, 동물의 이름을 자연스럽게 떠올릴 수 있도록 대화하세요. "
            "이름이 기억나지 않을 때 힌트를 주되, 정답을 먼저 말하지 마세요."
        ),
        CATEGORY_TEMPORAL: (
            "오늘 날짜·요일·계절·시간대에 대해 자연스럽게 확인하세요. "
            "틀려도 부드럽게 정정하고, 정원 메타포로 계절 연결하세요."
        ),
        CATEGORY_VISUAL: (
            "사용자가 사진이나 이미지를 보고 내용을 설명하도록 유도하세요. "
            "다음 대화에서 이미지 속 사물·인물·상황을 자세히 묻고 기억을 활성화하세요."
        ),
        CATEGORY_CHOICE: (
            "두 가지 선택지를 제시하고 사용자가 고르도록 하세요. "
            "선택 이유도 간단히 물어보세요. 카카오 버튼 카드 형식으로 구성하세요."
        ),
    }
    return hints.get(category, "사용자와 자연스럽게 대화하세요.")
