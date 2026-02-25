"""
일화 기억 (ER - Episodic Recall) 분석기

과거 사건 회상 능력 평가를 통한 기억 기능 측정

Scientific Basis:
    Tulving (1972) Episodic Memory Theory
    Hodges & Patterson (1995) Semantic Dementia Research

    - 자유 회상 정확도 = 장기 기억 인출 능력
    - 단서 재인 정확도 = 기억 흔적 잔존 여부
    - 모순 탐지 = 기억 일관성 및 혼란 정도
    - 세부 사항 풍부도 = 기억 선명도 및 생생함

Analysis Metrics:
    1. Free Recall Accuracy (자유 회상 정확도): 이전 대화 내용 회상 정확도
       Formula: accuracy = verified_facts / total_facts

    2. Detail Richness (세부 사항 풍부도): 구체적 세부 사항 포함 정도
       Formula: richness = specific_details / total_elements

    3. Contradiction Rate (모순 비율): 이전 기억과의 모순 발생률
       Formula: contradiction_rate = contradictions / total_statements

    4. Consistency Score (일관성 점수): 기억 일관성 LLM 평가
       Formula: LLM_judge(1-5)

Scoring Formula:
    ER_Score = RecallAccuracy × 35 + DetailRichness × 30 + (1 - ContradictionRate) × 15 + Consistency × 4

    Range: 0-100 (높을수록 좋음)

    - RecallAccuracy: 0-1 범위 (자유 회상 정확도)
    - DetailRichness: 0-1 범위 (세부 사항 풍부도)
    - ContradictionRate: 0-1 범위 (모순 비율, 낮을수록 좋음)
    - Consistency: 1-5 점수 (일관성 평가)

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2025-02-10
"""

from typing import Dict, Any, List, Optional, Set
import re
from kiwipiepy import Kiwi

from services.llm_service import LLMService
from utils.logger import get_logger
from utils.exceptions import AnalysisError

logger = get_logger(__name__)


class EpisodicRecallAnalyzer:
    """
    일화 기억 (Episodic Recall) 분석기

    사용자의 과거 사건 회상 능력을 평가하고 이전 대화 기록과 비교하여
    기억 정확도, 세부 사항 풍부도, 모순 여부, 일관성을 측정합니다.

    Attributes:
        llm: LLM 서비스 (일관성 평가용)
        kiwi: Kiwi 형태소 분석기 (세부 사항 추출용)

    Example:
        >>> analyzer = EpisodicRecallAnalyzer(llm_service)
        >>> result = await analyzer.analyze(
        ...     message="지난 봄에 엄마와 뒷산에서 쑥을 뜯었어요. "
        ...            "쑥이 많이 나 있었고 햇살이 따뜻했어요.",
        ...     context={
        ...         "episodic": [
        ...             {"fact": "봄에 쑥을 뜯었다", "verified": True},
        ...             {"fact": "엄마와 함께였다", "verified": True}
        ...         ],
        ...         "biographical": {
        ...             "mother_name": "이순자",
        ...             "hometown": "부산"
        ...         }
        ...     }
        ... )
        >>> print(result["score"])
        88.5
        >>> print(result["components"]["detail_richness"])
        0.85
    """

    # ============================================
    # 세부 사항 추출 패턴
    # ============================================

    # 구체적 세부 사항 지표
    SPECIFIC_DETAIL_PATTERNS = {
        "numbers": r'\b\d+\b',  # 숫자
        "names": r'\b[가-힣]{2,4}\b(?=님|씨|이|가|은|는)',  # 인명
        "places": r'\b(집|학교|병원|회사|시장|공원|산|강|바다)\b',  # 장소
        "colors": r'\b(빨간|파란|노란|하얀|검은|초록)\b',  # 색상
        "sizes": r'\b(큰|작은|높은|낮은|넓은|좁은)\b',  # 크기
        "emotions": r'\b(기쁜|슬픈|화난|행복한|즐거운|아픈)\b',  # 감정
    }

    # 모호한 표현 (세부 사항 부족 지표)
    VAGUE_EXPRESSIONS = [
        "그거", "저거", "이거", "뭐", "그것", "저것", "이것",
        "뭔가", "어떤", "무슨", "어디", "언제", "누구",
        "그런", "저런", "이런", "그냥", "막", "좀",
    ]

    def __init__(self, llm_service: LLMService):
        """
        일화 기억 분석기 초기화

        Args:
            llm_service: LLM 서비스 인스턴스
        """
        self.llm = llm_service
        self.kiwi = Kiwi()

        logger.info("EpisodicRecallAnalyzer initialized")

    async def analyze(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        일화 기억 종합 분석

        사용자 응답의 기억 회상 정확도, 세부 사항 풍부도, 모순 여부를 평가하여
        일화 기억 능력을 측정합니다.

        Args:
            message: 사용자 응답 텍스트
            context: 분석 컨텍스트 (선택)
                - episodic: 검증 가능한 과거 사실 목록 (선택)
                  [{"fact": "봄에 쑥을 뜯었다", "verified": True}, ...]
                - biographical: 사용자 생애 정보 (선택)
                  {"mother_name": "이순자", "hometown": "부산", ...}
                - previous_statements: 이전 진술 목록 (모순 탐지용, 선택)
                  ["엄마는 선생님이셨어요", "아버지는 의사였어요", ...]

        Returns:
            분석 결과 딕셔너리
            {
                "score": 88.5,  # ER 종합 점수 (0-100)
                "components": {
                    "recall_accuracy": 0.95,       # 회상 정확도 (0-1)
                    "detail_richness": 0.85,       # 세부 사항 풍부도 (0-1)
                    "contradiction_rate": 0.0,     # 모순 비율 (0-1)
                    "consistency_score": 5         # 일관성 점수 (1-5)
                },
                "details": {
                    "verified_facts": ["봄에 쑥을 뜯었다", "엄마와 함께였다"],
                    "unverified_facts": [],
                    "specific_details": ["쑥", "뒷산", "햇살"],
                    "vague_expressions": [],
                    "contradictions": [],
                    "total_facts": 2
                }
            }

        Raises:
            AnalysisError: 분석 실패 시

        Example:
            >>> result = await analyzer.analyze(
            ...     "지난 봄에 엄마와 뒷산에서 쑥을 뜯었어요",
            ...     context={"episodic": [{"fact": "봄에 쑥을 뜯었다", "verified": True}]}
            ... )
            >>> print(result["score"])
            88.5
            >>> print(result["components"]["recall_accuracy"])
            0.95

        Note:
            - episodic 없으면 recall_accuracy는 1.0 (중립)
            - biographical 없으면 contradiction 체크 불가
            - 모든 context가 없어도 detail_richness는 계산 가능
        """
        logger.debug(f"Starting ER analysis for message (length={len(message)})")

        # ============================================
        # 0. 입력 검증
        # ============================================
        if not message or not message.strip():
            logger.warning("Empty message provided for ER analysis")
            raise AnalysisError("Message cannot be empty")

        try:
            # ============================================
            # 1. 컨텍스트 추출
            # ============================================
            episodic_facts = context.get("episodic", []) if context else []
            biographical_info = context.get("biographical", {}) if context else {}
            previous_statements = context.get("previous_statements", []) if context else []

            logger.debug(
                f"Context: {len(episodic_facts)} episodic facts, "
                f"{len(biographical_info)} biographical items, "
                f"{len(previous_statements)} previous statements"
            )

            # ============================================
            # 2. 4개 지표 계산
            # ============================================

            # 2.1 자유 회상 정확도 (Free Recall Accuracy)
            # Formula: accuracy = verified_facts / total_facts
            # 높을수록 좋음 (0-1 범위)
            logger.debug("Calculating recall accuracy...")
            recall_result = self._calculate_recall_accuracy(message, episodic_facts)
            recall_accuracy = recall_result["accuracy"]
            logger.debug(f"Recall accuracy: {recall_accuracy:.3f}")

            # 2.2 세부 사항 풍부도 (Detail Richness)
            # Formula: richness = specific_details / total_elements
            # 높을수록 좋음 (0-1 범위)
            logger.debug("Calculating detail richness...")
            detail_result = self._calculate_detail_richness(message)
            detail_richness = detail_result["richness"]
            logger.debug(f"Detail richness: {detail_richness:.3f}")

            # 2.3 모순 비율 (Contradiction Rate)
            # Formula: contradiction_rate = contradictions / total_statements
            # 낮을수록 좋음 (0-1 범위)
            logger.debug("Detecting contradictions...")
            contradiction_result = await self._detect_contradictions(
                message, biographical_info, previous_statements
            )
            contradiction_rate = contradiction_result["rate"]
            logger.debug(f"Contradiction rate: {contradiction_rate:.3f}")

            # 2.4 일관성 점수 (Consistency Score)
            # LLM Judge: 1-5 점수
            # 높을수록 좋음
            logger.debug("Evaluating consistency...")
            consistency_score = await self._evaluate_consistency(
                message, previous_statements
            )
            logger.debug(f"Consistency score: {consistency_score}/5")

            # ============================================
            # 3. 종합 점수 계산
            # ============================================
            # Formula: ER = RecallAccuracy×35 + DetailRichness×30 + (1-ContradictionRate)×15 + Consistency×4
            # Range: 0-100
            score = (
                recall_accuracy * 100 * 0.35 +              # 회상 정확도 (35%)
                detail_richness * 100 * 0.30 +              # 세부 사항 풍부도 (30%)
                (1 - contradiction_rate) * 100 * 0.15 +     # 모순 반전 (15%)
                consistency_score * 20 * 0.20               # 일관성 (20%, 1-5 → 0-20)
            )

            logger.info(
                f"ER analysis completed: score={score:.2f}",
                extra={
                    "recall_accuracy": recall_accuracy,
                    "detail_richness": detail_richness,
                    "contradiction_rate": contradiction_rate,
                    "consistency_score": consistency_score
                }
            )

            # ============================================
            # 4. 결과 반환
            # ============================================
            return {
                "score": round(score, 2),
                "components": {
                    "recall_accuracy": round(recall_accuracy, 3),
                    "detail_richness": round(detail_richness, 3),
                    "contradiction_rate": round(contradiction_rate, 3),
                    "consistency_score": consistency_score
                },
                "details": {
                    **recall_result["details"],
                    **detail_result["details"],
                    **contradiction_result["details"],
                }
            }

        except Exception as e:
            logger.error(f"ER analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Episodic Recall analysis failed: {e}") from e

    def _calculate_recall_accuracy(
        self,
        text: str,
        episodic_facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        자유 회상 정확도 계산

        사용자가 언급한 내용이 이전에 검증된 사실과 얼마나 일치하는지 계산합니다.

        Formula:
            accuracy = verified_facts / total_facts
            no episodic facts = 1.0 (neutral)

        Args:
            text: 분석할 텍스트
            episodic_facts: 검증 가능한 과거 사실 목록
                [{"fact": "봄에 쑥을 뜯었다", "verified": True}, ...]

        Returns:
            {
                "accuracy": 0.95,
                "details": {
                    "verified_facts": ["봄에 쑥을 뜯었다", "엄마와 함께였다"],
                    "unverified_facts": [],
                    "total_facts": 2,
                    "verified_count": 2
                }
            }

        Example:
            >>> result = self._calculate_recall_accuracy(
            ...     "봄에 엄마와 쑥을 뜯었어요",
            ...     [{"fact": "봄에 쑥을 뜯었다", "verified": True}]
            ... )
            >>> print(result["accuracy"])
            1.0

        Note:
            - episodic_facts가 없으면 1.0 (중립) 반환
            - 부분 일치도 인정 (키워드 기반)
        """
        if not episodic_facts:
            return {
                "accuracy": 1.0,
                "details": {
                    "verified_facts": [],
                    "unverified_facts": [],
                    "total_facts": 0,
                    "verified_count": 0
                }
            }

        verified_facts = []
        unverified_facts = []

        # 각 사실을 텍스트에서 확인
        for fact_obj in episodic_facts:
            fact = fact_obj.get("fact", "")
            is_verified = fact_obj.get("verified", False)

            if not fact:
                continue

            # 키워드 기반 매칭 (간단한 구현)
            # 실제로는 임베딩 유사도 사용 가능
            keywords = [w for w in fact.split() if len(w) > 1]
            matched = any(keyword in text for keyword in keywords)

            if matched:
                if is_verified:
                    verified_facts.append(fact)
                else:
                    unverified_facts.append(fact)

        total_facts = len(verified_facts) + len(unverified_facts)
        accuracy = len(verified_facts) / total_facts if total_facts > 0 else 1.0

        logger.debug(
            f"Recall: {len(verified_facts)}/{total_facts} verified - {verified_facts[:3]}"
        )

        return {
            "accuracy": accuracy,
            "details": {
                "verified_facts": verified_facts,
                "unverified_facts": unverified_facts,
                "total_facts": total_facts,
                "verified_count": len(verified_facts)
            }
        }

    def _calculate_detail_richness(self, text: str) -> Dict[str, Any]:
        """
        세부 사항 풍부도 계산

        텍스트에 포함된 구체적 세부 사항(숫자, 이름, 장소, 색상 등)의
        비율을 계산하여 기억의 선명도를 평가합니다.

        Formula:
            richness = specific_details / (specific_details + vague_expressions)

        Args:
            text: 분석할 텍스트

        Returns:
            {
                "richness": 0.85,
                "details": {
                    "specific_details": ["쑥", "뒷산", "햇살", "따뜻"],
                    "vague_expressions": ["그거"],
                    "specific_count": 4,
                    "vague_count": 1,
                    "detail_types": {
                        "places": ["뒷산"],
                        "colors": [],
                        "numbers": [],
                        ...
                    }
                }
            }

        Example:
            >>> result = self._calculate_detail_richness(
            ...     "지난 봄에 엄마와 뒷산에서 쑥을 뜯었어요"
            ... )
            >>> print(result["richness"])
            0.88

        Note:
            - 구체적 세부 사항: 숫자, 이름, 장소, 색상, 크기, 감정
            - 모호한 표현: 그거, 저거, 뭔가, 그냥 등
        """
        # 형태소 분석
        result = self.kiwi.analyze(text)
        tokens = [token for token, pos, _, _ in result[0][0]]

        # 구체적 세부 사항 추출
        specific_details = []
        detail_types = {key: [] for key in self.SPECIFIC_DETAIL_PATTERNS.keys()}

        for pattern_type, pattern in self.SPECIFIC_DETAIL_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                specific_details.extend(matches)
                detail_types[pattern_type] = list(set(matches))[:5]  # 최대 5개

        # 일반 명사도 구체적 세부 사항으로 간주
        for token, pos, _, _ in result[0][0]:
            if pos == 'NNG':  # 일반명사
                if token not in specific_details and len(token) > 1:
                    specific_details.append(token)

        # 모호한 표현 추출
        vague_expressions = [
            expr for expr in self.VAGUE_EXPRESSIONS
            if expr in text
        ]

        # 풍부도 계산
        total_elements = len(specific_details) + len(vague_expressions)
        richness = len(specific_details) / total_elements if total_elements > 0 else 0.5

        # 중복 제거
        unique_specific = list(set(specific_details))
        unique_vague = list(set(vague_expressions))

        logger.debug(
            f"Details: {len(unique_specific)} specific, {len(unique_vague)} vague"
        )

        return {
            "richness": richness,
            "details": {
                "specific_details": unique_specific[:10],  # 최대 10개
                "vague_expressions": unique_vague,
                "specific_count": len(unique_specific),
                "vague_count": len(unique_vague),
                "detail_types": detail_types
            }
        }

    async def _detect_contradictions(
        self,
        text: str,
        biographical_info: Dict[str, Any],
        previous_statements: List[str]
    ) -> Dict[str, Any]:
        """
        모순 탐지

        현재 진술이 이전 기억(biographical, previous statements)과
        모순되는지 LLM을 활용하여 탐지합니다.

        Formula:
            contradiction_rate = contradictions / total_statements
            no previous data = 0.0 (neutral)

        Args:
            text: 현재 진술
            biographical_info: 사용자 생애 정보
                {"mother_name": "이순자", "hometown": "부산", ...}
            previous_statements: 이전 진술 목록
                ["엄마는 선생님이셨어요", "아버지는 의사였어요", ...]

        Returns:
            {
                "rate": 0.0,
                "details": {
                    "contradictions": [],
                    "consistent_statements": ["엄마와 함께였다"],
                    "total_checked": 1
                }
            }

        Example:
            >>> result = await self._detect_contradictions(
            ...     "엄마는 간호사였어요",
            ...     {},
            ...     ["엄마는 선생님이셨어요"]
            ... )
            >>> print(result["rate"])
            1.0  # 모순 발견
            >>> print(result["details"]["contradictions"])
            ["엄마는 간호사였어요 vs 엄마는 선생님이셨어요"]

        Note:
            - biographical_info와 previous_statements 모두 없으면 0.0 반환
            - LLM 실패 시 0.0 (보수적 기본값)
        """
        if not biographical_info and not previous_statements:
            return {
                "rate": 0.0,
                "details": {
                    "contradictions": [],
                    "consistent_statements": [],
                    "total_checked": 0
                }
            }

        contradictions = []
        consistent_statements = []

        # 이전 진술과 비교
        if previous_statements:
            for prev_statement in previous_statements[-5:]:  # 최근 5개만 체크
                try:
                    is_contradiction = await self._check_contradiction_llm(
                        text, prev_statement
                    )

                    if is_contradiction:
                        contradictions.append(f"{text[:50]} ⟷ {prev_statement[:50]}")
                    else:
                        consistent_statements.append(prev_statement[:50])

                except Exception as e:
                    logger.error(f"Failed to check contradiction: {e}")
                    # 실패 시 일관성 있다고 간주 (false negative 최소화)
                    consistent_statements.append(prev_statement[:50])

        total_checked = len(contradictions) + len(consistent_statements)
        contradiction_rate = len(contradictions) / total_checked if total_checked > 0 else 0.0

        logger.debug(
            f"Contradictions: {len(contradictions)}/{total_checked} detected"
        )

        return {
            "rate": contradiction_rate,
            "details": {
                "contradictions": contradictions,
                "consistent_statements": consistent_statements[:5],
                "total_checked": total_checked
            }
        }

    async def _check_contradiction_llm(
        self,
        statement1: str,
        statement2: str
    ) -> bool:
        """
        두 진술 간 모순 여부를 LLM으로 판단

        Args:
            statement1: 첫 번째 진술
            statement2: 두 번째 진술

        Returns:
            True if contradiction detected, False otherwise

        Example:
            >>> is_contradiction = await self._check_contradiction_llm(
            ...     "엄마는 간호사였어요",
            ...     "엄마는 선생님이셨어요"
            ... )
            >>> print(is_contradiction)
            True
        """
        try:
            prompt = f"""다음 두 진술이 서로 모순되는지 판단하세요.

진술 1: {statement1}
진술 2: {statement2}

모순이면 1, 모순이 아니면 0을 출력하세요.
숫자만 출력하세요 (0 또는 1).
"""

            result = await self.llm.call(prompt, max_tokens=5)
            contradiction = int(result.strip())

            return contradiction == 1

        except Exception as e:
            logger.error(f"Failed to check contradiction: {e}")
            return False  # 실패 시 보수적 기본값

    async def _evaluate_consistency(
        self,
        text: str,
        previous_statements: List[str]
    ) -> int:
        """
        일관성 점수 평가 (LLM Judge 기반 5점 척도)

        현재 진술이 이전 진술들과 전반적으로 일관되는지 평가합니다.

        Scoring Scale:
            5점: 매우 일관됨 (완전히 일치하거나 보완적)
            4점: 대체로 일관됨
            3점: 보통 수준
            2점: 다소 불일치
            1점: 매우 불일치하거나 명백히 모순

        Args:
            text: 현재 진술
            previous_statements: 이전 진술 목록

        Returns:
            일관성 점수 (1-5)
            - 5: 매우 일관됨
            - 3: 보통
            - 1: 매우 불일치
            - 이전 진술 없음: 3 (중립)
            - LLM 실패 시: 3 (중립)

        Example:
            >>> score = await self._evaluate_consistency(
            ...     "엄마와 쑥을 뜯었어요",
            ...     ["엄마는 선생님이셨어요", "쑥떡을 좋아해요"]
            ... )
            >>> print(score)
            5  # 일관됨
        """
        if not previous_statements:
            return 3  # 비교 대상 없음, 중립

        try:
            # 최근 5개만 사용
            recent_statements = previous_statements[-5:]
            statements_text = "\n".join([f"- {s}" for s in recent_statements])

            prompt = f"""다음 진술들의 전반적인 일관성을 평가하세요.

이전 진술들:
{statements_text}

현재 진술:
- {text}

평가 기준:
5점: 매우 일관됨 (완전히 일치하거나 자연스럽게 연결됨)
4점: 대체로 일관됨 (일부 차이는 있지만 큰 문제 없음)
3점: 보통 수준 (특별히 일관되거나 불일치하지 않음)
2점: 다소 불일치 (일부 모순이나 혼란 있음)
1점: 매우 불일치 (명백한 모순이나 완전히 다른 내용)

숫자만 출력하세요 (1-5).
"""

            result = await self.llm.call(prompt, max_tokens=5)
            score = int(result.strip())

            # 1-5 범위 강제
            score = max(1, min(5, score))

            logger.debug(f"Consistency score: {score}/5")
            return score

        except ValueError as e:
            logger.error(f"Failed to parse consistency score: {e}, defaulting to 3")
            return 3
        except Exception as e:
            logger.error(f"Failed to evaluate consistency: {e}", exc_info=True)
            return 3
