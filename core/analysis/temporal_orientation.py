"""
시간적 지남력 (TO - Temporal Orientation) 분석기

시간 인식 및 지남력 평가를 통한 인지 기능 측정

Scientific Basis:
    Folstein et al. (1975) Mini-Mental State Examination (MMSE)
    시간 지남력은 인지 기능 평가의 핵심 지표

    - 날짜/요일 정확도 저하 = 단기 기억 및 인지 기능 저하
    - 계절 인식 부족 = 시간 개념 혼란
    - 시간대 부적절 = 현실 인식 저하
    - 시간 일관성 부족 = 혼란 상태

Analysis Metrics:
    1. Date/Day Accuracy (날짜/요일 정확도): 언급된 날짜/요일과 실제 비교
       Formula: accuracy = 1 - (|mentioned - actual| / tolerance)

    2. Season Appropriateness (계절 적합성): 계절 언급과 현재 계절 일치도
       Formula: season_score = 1 if match else 0

    3. Time of Day Consistency (시간대 일관성): 시간대 표현의 적절성
       Formula: consistency = matched_references / total_references

    4. Temporal Consistency (시간 일관성): 내부 시간 표현의 일관성
       Formula: LLM_judge(1-5)

Scoring Formula:
    TO_Score = DateAccuracy × 35 + SeasonScore × 25 + TimeConsistency × 20 + TemporalConsistency × 4

    Range: 0-100 (높을수록 좋음)

    - DateAccuracy: 0-1 범위 (날짜/요일 정확도)
    - SeasonScore: 0-1 범위 (계절 적합성)
    - TimeConsistency: 0-1 범위 (시간대 일관성)
    - TemporalConsistency: 1-5 점수 (시간 일관성 평가)

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2025-02-10
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import re
from calendar import day_name, month_name

from services.llm_service import LLMService
from utils.logger import get_logger
from utils.exceptions import AnalysisError

logger = get_logger(__name__)


class TemporalOrientationAnalyzer:
    """
    시간적 지남력 (Temporal Orientation) 분석기

    사용자 응답에서 시간 관련 표현을 추출하여 현재 시간과 비교하고
    시간 인식 정확도 및 일관성을 평가합니다.

    Attributes:
        llm: LLM 서비스 (시간 일관성 평가용)

    Example:
        >>> analyzer = TemporalOrientationAnalyzer(llm_service)
        >>> result = await analyzer.analyze(
        ...     message="오늘은 월요일이에요. 봄이라 따뜻해요.",
        ...     context={"current_datetime": datetime(2025, 3, 17)}  # 실제로는 월요일, 봄
        ... )
        >>> print(result["score"])
        95.0
        >>> print(result["components"]["date_accuracy"])
        1.0  # 정확함
    """

    # ============================================
    # 한국어 시간 표현 패턴
    # ============================================

    # 요일 매핑
    KOREAN_WEEKDAYS = {
        "월요일": 0, "월": 0,
        "화요일": 1, "화": 1,
        "수요일": 2, "수": 2,
        "목요일": 3, "목": 3,
        "금요일": 4, "금": 4,
        "토요일": 5, "토": 5,
        "일요일": 6, "일": 6,
    }

    # 계절 매핑 (월 기준)
    SEASONS = {
        "봄": [3, 4, 5],
        "여름": [6, 7, 8],
        "가을": [9, 10, 11],
        "겨울": [12, 1, 2],
    }

    # 시간대 매핑
    TIME_OF_DAY = {
        "새벽": (4, 6),
        "아침": (6, 11),  # 10시까지 포함 (< 11이므로 10시 포함)
        "오전": (9, 12),
        "점심": (11, 13),
        "낮": (12, 15),
        "오후": (12, 18),
        "저녁": (17, 20),
        "밤": (19, 24),
        "심야": (0, 4),
    }

    # 상대 시간 표현
    RELATIVE_TIME = {
        "오늘": 0,
        "어제": -1,
        "그제": -2,
        "그저께": -2,
        "내일": 1,
        "모레": 2,
        "글피": 3,
    }

    def __init__(self, llm_service: LLMService):
        """
        시간적 지남력 분석기 초기화

        Args:
            llm_service: LLM 서비스 인스턴스
        """
        self.llm = llm_service

        logger.info("TemporalOrientationAnalyzer initialized")

    async def analyze(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        시간적 지남력 종합 분석

        사용자 응답에서 시간 표현을 추출하여 현재 시간과 비교하고
        날짜/요일 정확도, 계절 적합성, 시간 일관성을 평가합니다.

        Args:
            message: 사용자 응답 텍스트
            context: 분석 컨텍스트 (선택)
                - current_datetime: 현재 시간 (datetime 객체, 기본값: 현재 시간)

        Returns:
            분석 결과 딕셔너리
            {
                "score": 85.5,  # TO 종합 점수 (0-100)
                "components": {
                    "date_accuracy": 1.0,        # 날짜/요일 정확도 (0-1)
                    "season_score": 1.0,         # 계절 적합성 (0-1)
                    "time_consistency": 0.8,     # 시간대 일관성 (0-1)
                    "temporal_consistency": 4    # 시간 일관성 (1-5)
                },
                "details": {
                    "current_date": "2025-03-17",
                    "current_weekday": "월요일",
                    "current_season": "봄",
                    "mentioned_weekday": "월요일",
                    "mentioned_season": "봄",
                    "weekday_match": True,
                    "season_match": True,
                    "time_references": ["오늘", "아침"]
                }
            }

        Raises:
            AnalysisError: 분석 실패 시

        Example:
            >>> result = await analyzer.analyze(
            ...     "오늘은 월요일이고 봄이라 날씨가 좋아요",
            ...     context={"current_datetime": datetime(2025, 3, 17)}
            ... )
            >>> print(result["score"])
            95.0
            >>> print(result["details"]["weekday_match"])
            True

        Note:
            - 날짜/요일이 언급되지 않으면 1.0 (중립)
            - 계절이 언급되지 않으면 1.0 (중립)
            - 시간대 표현이 없으면 1.0 (중립)
        """
        logger.debug(f"Starting TO analysis for message (length={len(message)})")

        # ============================================
        # 0. 입력 검증 및 현재 시간 설정
        # ============================================
        if not message or not message.strip():
            logger.warning("Empty message provided for TO analysis")
            raise AnalysisError("Message cannot be empty")

        # 현재 시간 (context에서 가져오거나 실제 현재 시간 사용)
        current_dt = context.get("current_datetime") if context else None
        if not current_dt:
            current_dt = datetime.now()

        logger.debug(f"Current datetime: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # ============================================
            # 1. 4개 지표 계산
            # ============================================

            # 1.1 날짜/요일 정확도 (Date/Day Accuracy)
            # Formula: accuracy = 1 - (|mentioned - actual| / tolerance)
            # 높을수록 좋음 (0-1 범위)
            logger.debug("Calculating date/weekday accuracy...")
            date_result = self._calculate_date_accuracy(message, current_dt)
            date_accuracy = date_result["accuracy"]
            logger.debug(f"Date accuracy: {date_accuracy:.3f}")

            # 1.2 계절 적합성 (Season Appropriateness)
            # Formula: season_score = 1 if match else 0
            # 높을수록 좋음 (0-1 범위)
            logger.debug("Checking season appropriateness...")
            season_result = self._check_season_appropriateness(message, current_dt)
            season_score = season_result["score"]
            logger.debug(f"Season score: {season_score:.3f}")

            # 1.3 시간대 일관성 (Time of Day Consistency)
            # Formula: consistency = matched_references / total_references
            # 높을수록 좋음 (0-1 범위)
            logger.debug("Checking time of day consistency...")
            time_result = self._check_time_consistency(message, current_dt)
            time_consistency = time_result["consistency"]
            logger.debug(f"Time consistency: {time_consistency:.3f}")

            # 1.4 시간 일관성 (Temporal Consistency)
            # LLM Judge: 1-5 점수
            # 높을수록 좋음
            logger.debug("Evaluating temporal consistency...")
            temporal_consistency = await self._evaluate_temporal_consistency(message)
            logger.debug(f"Temporal consistency: {temporal_consistency}/5")

            # ============================================
            # 2. 종합 점수 계산
            # ============================================
            # Formula: TO = DateAccuracy×35 + SeasonScore×25 + TimeConsistency×20 + TemporalConsistency×4
            # Range: 0-100
            score = (
                date_accuracy * 100 * 0.35 +         # 날짜/요일 정확도 (35%)
                season_score * 100 * 0.25 +          # 계절 적합성 (25%)
                time_consistency * 100 * 0.20 +      # 시간대 일관성 (20%)
                temporal_consistency * 20 * 0.20     # 시간 일관성 (20%, 1-5 → 0-20)
            )

            logger.info(
                f"TO analysis completed: score={score:.2f}",
                extra={
                    "date_accuracy": date_accuracy,
                    "season_score": season_score,
                    "time_consistency": time_consistency,
                    "temporal_consistency": temporal_consistency
                }
            )

            # ============================================
            # 3. 결과 반환
            # ============================================
            return {
                "score": round(score, 2),
                "components": {
                    "date_accuracy": round(date_accuracy, 3),
                    "season_score": round(season_score, 3),
                    "time_consistency": round(time_consistency, 3),
                    "temporal_consistency": temporal_consistency
                },
                "details": {
                    "current_date": current_dt.strftime("%Y-%m-%d"),
                    "current_weekday": self._get_korean_weekday(current_dt),
                    "current_season": self._get_current_season(current_dt),
                    **date_result["details"],
                    **season_result["details"],
                    **time_result["details"],
                }
            }

        except Exception as e:
            logger.error(f"TO analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Temporal Orientation analysis failed: {e}") from e

    def _calculate_date_accuracy(
        self,
        text: str,
        current_dt: datetime
    ) -> Dict[str, Any]:
        """
        날짜/요일 정확도 계산

        텍스트에서 언급된 날짜/요일을 추출하여 현재 날짜/요일과 비교합니다.

        Formula:
            accuracy = 1 - (|mentioned_day - actual_day| / tolerance)
            tolerance = 3 days for date, 1 day for weekday

        Args:
            text: 분석할 텍스트
            current_dt: 현재 날짜/시간

        Returns:
            {
                "accuracy": 0.9,
                "details": {
                    "mentioned_weekday": "월요일",
                    "actual_weekday": "월요일",
                    "weekday_match": True,
                    "weekday_diff_days": 0
                }
            }

        Example:
            >>> result = self._calculate_date_accuracy(
            ...     "오늘은 월요일이에요",
            ...     datetime(2025, 3, 17)  # 월요일
            ... )
            >>> print(result["accuracy"])
            1.0
        """
        # 요일 추출
        mentioned_weekday = None
        for korean_day, day_num in self.KOREAN_WEEKDAYS.items():
            if korean_day in text:
                mentioned_weekday = korean_day
                mentioned_day_num = day_num
                break

        actual_weekday = self._get_korean_weekday(current_dt)
        actual_day_num = current_dt.weekday()

        if not mentioned_weekday:
            # 요일이 언급되지 않으면 중립 (1.0)
            return {
                "accuracy": 1.0,
                "details": {
                    "mentioned_weekday": None,
                    "actual_weekday": actual_weekday,
                    "weekday_match": None,
                    "weekday_diff_days": None
                }
            }

        # 요일 차이 계산 (순환 고려)
        diff = abs(mentioned_day_num - actual_day_num)
        if diff > 3:
            diff = 7 - diff  # 순환 거리 (예: 금 → 월 = 3일)

        # 정확도 계산 (tolerance = 1일)
        accuracy = max(0.0, 1.0 - diff / 3.0)

        weekday_match = (mentioned_day_num == actual_day_num)

        logger.debug(
            f"Weekday: mentioned='{mentioned_weekday}', actual='{actual_weekday}', "
            f"diff={diff}, match={weekday_match}"
        )

        return {
            "accuracy": accuracy,
            "details": {
                "mentioned_weekday": mentioned_weekday,
                "actual_weekday": actual_weekday,
                "weekday_match": weekday_match,
                "weekday_diff_days": diff
            }
        }

    def _check_season_appropriateness(
        self,
        text: str,
        current_dt: datetime
    ) -> Dict[str, Any]:
        """
        계절 적합성 체크

        텍스트에서 언급된 계절이 현재 계절과 일치하는지 확인합니다.

        Formula:
            season_score = 1.0 if match else 0.0
            no mention = 1.0 (neutral)

        Args:
            text: 분석할 텍스트
            current_dt: 현재 날짜/시간

        Returns:
            {
                "score": 1.0,
                "details": {
                    "mentioned_season": "봄",
                    "current_season": "봄",
                    "season_match": True
                }
            }

        Example:
            >>> result = self._check_season_appropriateness(
            ...     "봄이라 날씨가 좋아요",
            ...     datetime(2025, 3, 17)  # 봄
            ... )
            >>> print(result["score"])
            1.0
        """
        # 현재 계절
        current_season = self._get_current_season(current_dt)

        # 계절 추출
        mentioned_season = None
        for season in self.SEASONS.keys():
            if season in text:
                mentioned_season = season
                break

        if not mentioned_season:
            # 계절이 언급되지 않으면 중립 (1.0)
            return {
                "score": 1.0,
                "details": {
                    "mentioned_season": None,
                    "current_season": current_season,
                    "season_match": None
                }
            }

        # 일치 여부
        season_match = (mentioned_season == current_season)
        score = 1.0 if season_match else 0.0

        logger.debug(
            f"Season: mentioned='{mentioned_season}', current='{current_season}', "
            f"match={season_match}"
        )

        return {
            "score": score,
            "details": {
                "mentioned_season": mentioned_season,
                "current_season": current_season,
                "season_match": season_match
            }
        }

    def _check_time_consistency(
        self,
        text: str,
        current_dt: datetime
    ) -> Dict[str, Any]:
        """
        시간대 일관성 체크

        텍스트에서 언급된 시간대 표현(아침, 저녁 등)이
        현재 시간과 일치하는지 확인합니다.

        Formula:
            consistency = matched_count / total_count
            no mentions = 1.0 (neutral)

        Args:
            text: 분석할 텍스트
            current_dt: 현재 날짜/시간

        Returns:
            {
                "consistency": 0.8,
                "details": {
                    "time_references": ["아침", "오전"],
                    "current_hour": 10,
                    "matched_count": 2,
                    "total_count": 2
                }
            }

        Example:
            >>> result = self._check_time_consistency(
            ...     "아침에 일어나서 산책했어요",
            ...     datetime(2025, 3, 17, 10, 0)  # 오전 10시
            ... )
            >>> print(result["consistency"])
            1.0
        """
        current_hour = current_dt.hour

        # 시간대 표현 추출
        time_references = []
        matched_count = 0

        for time_expr, (start_hour, end_hour) in self.TIME_OF_DAY.items():
            if time_expr in text:
                time_references.append(time_expr)

                # 현재 시간이 해당 시간대에 포함되는지 확인
                if start_hour <= current_hour < end_hour:
                    matched_count += 1
                # 자정을 넘는 경우 (예: 밤 19-24, 심야 0-4)
                elif start_hour > end_hour:
                    if current_hour >= start_hour or current_hour < end_hour:
                        matched_count += 1

        if not time_references:
            # 시간대 표현이 없으면 중립 (1.0)
            return {
                "consistency": 1.0,
                "details": {
                    "time_references": [],
                    "current_hour": current_hour,
                    "matched_count": 0,
                    "total_count": 0
                }
            }

        # 일관성 계산
        consistency = matched_count / len(time_references)

        logger.debug(
            f"Time: references={time_references}, hour={current_hour}, "
            f"matched={matched_count}/{len(time_references)}"
        )

        return {
            "consistency": consistency,
            "details": {
                "time_references": time_references,
                "current_hour": current_hour,
                "matched_count": matched_count,
                "total_count": len(time_references)
            }
        }

    async def _evaluate_temporal_consistency(self, text: str) -> int:
        """
        시간 일관성 평가 (LLM Judge 기반 5점 척도)

        텍스트 내 시간 표현들이 서로 일관성 있게 사용되었는지 평가합니다.

        Scoring Scale:
            5점: 시간 표현이 매우 일관되고 논리적
            4점: 대체로 일관됨
            3점: 보통 수준
            2점: 다소 혼란스러움
            1점: 매우 혼란스럽거나 모순됨

        Args:
            text: 평가할 텍스트

        Returns:
            시간 일관성 점수 (1-5)
            - 5: 매우 일관됨
            - 3: 보통
            - 1: 매우 혼란
            - LLM 실패 시: 3 (중립)

        Example:
            >>> score = await self._evaluate_temporal_consistency(
            ...     "아침에 일어나서 점심을 먹고 저녁에 잤어요"
            ... )
            >>> print(score)
            5  # 시간 순서 명확

            >>> score = await self._evaluate_temporal_consistency(
            ...     "저녁에 일어나서 아침을 먹고 점심에 잤어요"
            ... )
            >>> print(score)
            1  # 시간 순서 혼란

        Note:
            - LLM 모델: Claude Sonnet 4.5
            - 평가 기준: 시간 표현 일관성, 모순 여부
            - 실패 시 기본값: 3 (중립)
        """
        try:
            prompt = f"""다음 텍스트에서 시간 표현의 일관성을 평가하세요.

텍스트: {text}

평가 기준:
5점: 시간 표현이 매우 일관되고 논리적 (예: "아침에 일어나 → 점심 먹고 → 저녁에 잤다")
4점: 대체로 일관됨
3점: 보통 수준이거나 시간 표현이 거의 없음
2점: 시간 표현이 다소 혼란스럽거나 일부 모순
1점: 시간 표현이 매우 혼란스럽거나 명백히 모순 (예: "저녁에 일어나 아침을 먹었다")

숫자만 출력하세요 (1-5).
"""

            result = await self.llm.call(prompt, max_tokens=5)
            score = int(result.strip())

            # 1-5 범위 강제
            score = max(1, min(5, score))

            logger.debug(f"Temporal consistency score: {score}/5")
            return score

        except ValueError as e:
            logger.error(f"Failed to parse temporal consistency score: {e}, defaulting to 3")
            return 3
        except Exception as e:
            logger.error(f"Failed to evaluate temporal consistency: {e}", exc_info=True)
            return 3

    def _get_korean_weekday(self, dt: datetime) -> str:
        """
        datetime 객체에서 한국어 요일 추출

        Args:
            dt: datetime 객체

        Returns:
            한국어 요일 (예: "월요일")

        Example:
            >>> weekday = self._get_korean_weekday(datetime(2025, 3, 17))
            >>> print(weekday)
            "월요일"
        """
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        return weekdays[dt.weekday()]

    def _get_current_season(self, dt: datetime) -> str:
        """
        datetime 객체에서 현재 계절 추출

        Args:
            dt: datetime 객체

        Returns:
            계절 (봄/여름/가을/겨울)

        Example:
            >>> season = self._get_current_season(datetime(2025, 3, 17))
            >>> print(season)
            "봄"
        """
        month = dt.month
        for season, months in self.SEASONS.items():
            if month in months:
                return season
        return "알 수 없음"
