"""
서사 일관성 (NC - Narrative Coherence) 분석기

서사 구조 완결성 분석을 통한 집행기능 및 언어 조직화 능력 평가

Scientific Basis:
    Fraser et al. (2016), Garrard et al. (2005) 연구 기반

    - 5W1H 포함도 저하 = 정보 조직화 능력 저하
    - 시간적 순서 혼란 = 작업 기억 및 계획 능력 저하
    - 과도한 반복 = Perseveration (보속증, 전두엽 기능 저하)
    - 서사 구조 결여 = 담화 구성 능력 저하

Analysis Metrics:
    1. 5W1H Coverage (5W1H 포함도): Who, What, When, Where, Why, How 요소 포함 정도
       Formula: coverage = (present_elements / 6) × 100

    2. Temporal Order (시간 순서): 사건 시간 순서의 논리성
       Formula: order_score = LLM_judge(1-5)

    3. Repetitiveness (반복성): 불필요한 반복 감지
       Formula: repetition_ratio = repeated_phrases / total_phrases

    4. Narrative Structure (서사 구조): 기승전결 구조 평가
       Formula: structure_score = LLM_judge(1-5)

Scoring Formula:
    NC_Score = Coverage × 30 + TemporalOrder × 20 + (1 - Repetitiveness) × 25 + Structure × 5

    Range: 0-100 (높을수록 좋음)

    - Coverage: 0-1 범위 (5W1H 요소 포함 비율)
    - TemporalOrder: 1-5 점수 (시간 순서 논리성)
    - Repetitiveness: 0-1 범위 (반복 비율, 낮을수록 좋음)
    - Structure: 1-5 점수 (서사 구조 완결성)

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2025-02-10
"""

from typing import Dict, Any, List, Optional, Set
import re
from collections import Counter
from kiwipiepy import Kiwi

from services.llm_service import LLMService
from utils.logger import get_logger
from utils.exceptions import AnalysisError

logger = get_logger(__name__)


class NarrativeCoherenceAnalyzer:
    """
    서사 일관성 (Narrative Coherence) 분석기

    텍스트의 5W1H 포함도, 시간적 순서, 반복성, 서사 구조를 분석하여
    사용자의 언어 조직화 능력 및 집행기능을 평가합니다.

    Attributes:
        llm: LLM 서비스 (시간 순서 및 구조 평가용)
        kiwi: Kiwi 형태소 분석기 (반복 탐지용)

    Example:
        >>> analyzer = NarrativeCoherenceAnalyzer(llm_service)
        >>> result = await analyzer.analyze(
        ...     message="지난 봄에 엄마와 함께 뒷산에 쑥을 뜯으러 갔어요. "
        ...            "쑥이 많이 나 있었어요. 집에 돌아와서 쑥떡을 만들었어요."
        ... )
        >>> print(result["score"])
        87.5
        >>> print(result["components"]["coverage_5w1h"])
        0.833  # 6개 중 5개 요소 포함
    """

    # ============================================
    # 5W1H 키워드 패턴
    # ============================================
    W5H1_PATTERNS = {
        "who": [
            # 인칭 대명사
            r'\b(나|저|우리|내가|제가)\b',
            r'\b(엄마|아빠|할머니|할아버지|어머니|아버지)\b',
            r'\b(친구|동료|선생님|의사|간호사)\b',
            r'\b(아들|딸|손자|손녀|형제|자매)\b',
            # 직함
            r'\b(선생님|의사|간호사|사장님)\b',
        ],
        "what": [
            # 동작 동사
            r'\b\w+(했|갔|왔|봤|먹|마시|만들|놀|일)\w*\b',
            # 명사 + 하다
            r'\b\w+하(다|고|여|였)\b',
        ],
        "when": [
            # 시간 표현
            r'\b(오늘|어제|그제|내일|모레|지난|다음)\b',
            r'\b(아침|점심|저녁|밤|새벽)\b',
            r'\b(봄|여름|가을|겨울)\b',
            r'\b(월요일|화요일|수요일|목요일|금요일|토요일|일요일)\b',
            r'\b\d{1,2}월\b',
            r'\b\d{1,2}일\b',
            r'\b\d{4}년\b',
            r'\b(전에|후에|때|무렵)\b',
        ],
        "where": [
            # 장소 표현
            r'\b(집|학교|병원|회사|시장|공원)\b',
            r'\b(산|바다|강|호수|들판)\b',
            r'\b(서울|부산|대구|인천|광주|대전|울산)\b',
            r'\b\w+(에서|에|로)\b',
        ],
        "why": [
            # 이유 표현
            r'\b(때문에|덕분에|이유|까닭)\b',
            r'\b(그래서|따라서|그러므로)\b',
            r'\b(위해|위하여)\b',
        ],
        "how": [
            # 방법 표현
            r'\b(방법|방식|수단)\b',
            r'\b(\w+게|게)\b',  # 부사형 어미
            r'\b(어떻게|어떤)\b',
        ],
    }

    def __init__(self, llm_service: LLMService):
        """
        서사 일관성 분석기 초기화

        Args:
            llm_service: LLM 서비스 인스턴스
        """
        self.llm = llm_service
        self.kiwi = Kiwi()

        logger.info("NarrativeCoherenceAnalyzer initialized")

    async def analyze(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        서사 일관성 종합 분석

        텍스트의 5W1H 포함도, 시간적 순서, 반복성, 서사 구조를 평가하여
        언어 조직화 능력 및 집행기능을 측정합니다.

        Args:
            message: 사용자 응답 텍스트
            context: 분석 컨텍스트 (선택)
                - question_type: 질문 유형 (미사용, 향후 확장용)

        Returns:
            분석 결과 딕셔너리
            {
                "score": 87.5,  # NC 종합 점수 (0-100)
                "components": {
                    "coverage_5w1h": 0.833,     # 5W1H 포함도 (0-1)
                    "temporal_order": 4,        # 시간 순서 (1-5)
                    "repetitiveness": 0.05,     # 반복 비율 (0-1)
                    "narrative_structure": 4    # 서사 구조 (1-5)
                },
                "details": {
                    "w5h1_present": ["who", "what", "when", "where", "how"],
                    "w5h1_missing": ["why"],
                    "repeated_phrases": ["그거", "그거"],
                    "sentence_count": 3
                }
            }

        Raises:
            AnalysisError: 분석 실패 시

        Example:
            >>> result = await analyzer.analyze(
            ...     "지난 봄에 엄마와 뒷산에서 쑥을 뜯었어요. "
            ...     "쑥떡을 만들어서 먹었어요."
            ... )
            >>> print(result["score"])
            85.2
            >>> print(result["components"]["coverage_5w1h"])
            0.833

        Note:
            - 5W1H: 6개 요소 중 포함된 개수 계산
            - 시간 순서 및 구조: LLM 기반 평가 (1-5점)
            - 반복성: 형태소 분석 기반 n-gram 중복 탐지
        """
        logger.debug(f"Starting NC analysis for message (length={len(message)})")

        # ============================================
        # 0. 입력 검증
        # ============================================
        if not message or not message.strip():
            logger.warning("Empty message provided for NC analysis")
            raise AnalysisError("Message cannot be empty")

        try:
            # ============================================
            # 1. 4개 지표 계산
            # ============================================

            # 1.1 5W1H 포함도 (Coverage)
            # Formula: coverage = present_elements / 6
            # 높을수록 좋음 (0-1 범위)
            logger.debug("Calculating 5W1H coverage...")
            coverage_result = self._calculate_5w1h_coverage(message)
            coverage = coverage_result["coverage"]
            logger.debug(f"5W1H coverage: {coverage:.3f} ({coverage_result['present']})")

            # 1.2 시간 순서 (Temporal Order)
            # LLM Judge: 1-5 점수
            # 높을수록 좋음
            logger.debug("Evaluating temporal order...")
            temporal_order = await self._evaluate_temporal_order(message)
            logger.debug(f"Temporal order: {temporal_order}/5")

            # 1.3 반복성 (Repetitiveness)
            # Formula: repetition_ratio = repeated_phrases / total_phrases
            # 낮을수록 좋음 (0-1 범위)
            logger.debug("Detecting repetitiveness...")
            repetitiveness_result = self._detect_repetitiveness(message)
            repetitiveness = repetitiveness_result["ratio"]
            logger.debug(f"Repetitiveness: {repetitiveness:.3f}")

            # 1.4 서사 구조 (Narrative Structure)
            # LLM Judge: 1-5 점수
            # 높을수록 좋음
            logger.debug("Evaluating narrative structure...")
            structure_score = await self._evaluate_narrative_structure(message)
            logger.debug(f"Narrative structure: {structure_score}/5")

            # ============================================
            # 2. 종합 점수 계산
            # ============================================
            # Formula: NC = Coverage×30 + TemporalOrder×20 + (1-Repetitiveness)×25 + Structure×5
            # Range: 0-100
            score = (
                coverage * 100 * 0.30 +              # 5W1H 포함도 (30%)
                temporal_order * 20 * 0.20 +         # 시간 순서 (20%, 1-5 → 0-20)
                (1 - repetitiveness) * 100 * 0.25 +  # 반복성 반전 (25%)
                structure_score * 20 * 0.25          # 서사 구조 (25%, 1-5 → 0-20)
            )

            logger.info(
                f"NC analysis completed: score={score:.2f}",
                extra={
                    "coverage": coverage,
                    "temporal_order": temporal_order,
                    "repetitiveness": repetitiveness,
                    "structure": structure_score
                }
            )

            # ============================================
            # 3. 결과 반환
            # ============================================
            return {
                "score": round(score, 2),
                "components": {
                    "coverage_5w1h": round(coverage, 3),
                    "temporal_order": temporal_order,
                    "repetitiveness": round(repetitiveness, 3),
                    "narrative_structure": structure_score
                },
                "details": {
                    "w5h1_present": coverage_result["present"],
                    "w5h1_missing": coverage_result["missing"],
                    "repeated_phrases": repetitiveness_result["repeated_phrases"],
                    "repetition_count": repetitiveness_result["count"],
                    "sentence_count": len([s for s in message.split('.') if s.strip()])
                }
            }

        except Exception as e:
            logger.error(f"NC analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Narrative Coherence analysis failed: {e}") from e

    def _calculate_5w1h_coverage(self, text: str) -> Dict[str, Any]:
        """
        5W1H 포함도 계산

        텍스트에서 Who, What, When, Where, Why, How 요소가
        얼마나 포함되어 있는지 패턴 매칭으로 계산합니다.

        Formula:
            coverage = (present_elements / 6)

        Args:
            text: 분석할 텍스트

        Returns:
            {
                "coverage": 0.833,  # 6개 중 5개
                "present": ["who", "what", "when", "where", "how"],
                "missing": ["why"],
                "details": {
                    "who": ["엄마", "나"],
                    "what": ["뜯었어요", "만들었어요"],
                    ...
                }
            }

        Example:
            >>> result = self._calculate_5w1h_coverage(
            ...     "지난 봄에 엄마와 뒷산에서 쑥을 뜯었어요"
            ... )
            >>> print(result["coverage"])
            0.833
            >>> print(result["present"])
            ["who", "what", "when", "where", "how"]

        Note:
            - 패턴 매칭 기반 (정규표현식)
            - 각 요소는 하나라도 매칭되면 포함으로 간주
            - 일부 요소는 문맥에 따라 false positive 가능
        """
        present_elements = []
        missing_elements = []
        details = {}

        # 각 5W1H 요소별로 패턴 매칭
        for element, patterns in self.W5H1_PATTERNS.items():
            matches = []

            for pattern in patterns:
                found = re.findall(pattern, text, re.IGNORECASE)
                if found:
                    matches.extend(found)

            # 중복 제거
            unique_matches = list(set(matches))

            if unique_matches:
                present_elements.append(element)
                details[element] = unique_matches[:3]  # 최대 3개만 저장
            else:
                missing_elements.append(element)
                details[element] = []

        # 포함도 계산 (0-1 범위)
        coverage = len(present_elements) / 6

        logger.debug(f"5W1H: {len(present_elements)}/6 present - {present_elements}")

        return {
            "coverage": coverage,
            "present": present_elements,
            "missing": missing_elements,
            "details": details
        }

    async def _evaluate_temporal_order(self, text: str) -> int:
        """
        시간 순서 평가 (LLM Judge 기반 5점 척도)

        텍스트 내 사건들이 시간적으로 논리적인 순서로 배열되어 있는지
        LLM을 활용하여 평가합니다.

        Scoring Scale:
            5점: 시간 순서가 매우 명확하고 논리적
            4점: 대체로 시간 순서가 명확
            3점: 시간 순서가 보통 수준
            2점: 시간 순서가 다소 혼란스러움
            1점: 시간 순서가 매우 혼란스럽거나 없음

        Args:
            text: 평가할 텍스트

        Returns:
            시간 순서 점수 (1-5)
            - 5: 매우 논리적
            - 3: 보통
            - 1: 매우 혼란
            - LLM 실패 시: 3 (중립)

        Example:
            >>> score = await self._evaluate_temporal_order(
            ...     "아침에 일어나서 밥을 먹었어요. 그 다음 산책을 나갔어요."
            ... )
            >>> print(score)
            5  # 명확한 시간 순서

            >>> score = await self._evaluate_temporal_order(
            ...     "저녁을 먹었어요. 아침에 일어났어요."
            ... )
            >>> print(score)
            2  # 시간 순서 혼란

        Note:
            - LLM 모델: Claude Sonnet 4.5
            - 평가 기준: 시간 표현의 논리성, 사건 순서
            - 실패 시 기본값: 3 (중립)
        """
        try:
            prompt = f"""다음 텍스트에서 사건의 시간적 순서가 논리적인지 평가하세요.

텍스트: {text}

평가 기준:
5점: 시간 순서가 매우 명확하고 논리적 (예: "아침에 일어나서 → 밥을 먹고 → 회사에 갔다")
4점: 대체로 시간 순서가 명확
3점: 시간 순서가 보통 수준이거나 시간 표현이 없음
2점: 시간 순서가 다소 혼란스러움 (예: "저녁에 밥을 먹고 → 아침에 일어났다")
1점: 시간 순서가 매우 혼란스럽거나 완전히 뒤섞임

숫자만 출력하세요 (1-5).
"""

            result = await self.llm.call(prompt, max_tokens=5)
            score = int(result.strip())

            # 1-5 범위 강제
            score = max(1, min(5, score))

            logger.debug(f"Temporal order score: {score}/5")
            return score

        except ValueError as e:
            logger.error(f"Failed to parse temporal order score: {e}, defaulting to 3")
            return 3
        except Exception as e:
            logger.error(f"Failed to evaluate temporal order: {e}", exc_info=True)
            return 3

    def _detect_repetitiveness(self, text: str) -> Dict[str, Any]:
        """
        반복성 탐지 (형태소 기반 n-gram 분석)

        텍스트에서 불필요하게 반복되는 구나 단어를 탐지합니다.
        과도한 반복은 Perseveration(보속증)의 지표입니다.

        Formula:
            repetition_ratio = repeated_phrases / total_phrases

        Args:
            text: 분석할 텍스트

        Returns:
            {
                "ratio": 0.15,  # 반복 비율 (0-1)
                "count": 3,
                "repeated_phrases": ["그거", "그거", "뭐더라"],
                "unique_repeated": ["그거", "뭐더라"]
            }

        Example:
            >>> result = self._detect_repetitiveness(
            ...     "그거 있잖아요. 그거 말이에요. 그거요."
            ... )
            >>> print(result["ratio"])
            0.60
            >>> print(result["repeated_phrases"])
            ["그거", "그거", "그거"]

        Note:
            - Bigram (2-gram) 기반 분석
            - 2회 이상 등장하는 구만 반복으로 간주
            - 형태소 단위로 분석 (조사 제외)
        """
        # 형태소 분석
        result = self.kiwi.analyze(text)
        tokens = []
        for token, pos, _, _ in result[0][0]:
            # 조사(J) 및 기호(S) 제외
            if not pos.startswith('J') and not pos.startswith('S'):
                tokens.append(token)

        if len(tokens) < 2:
            return {
                "ratio": 0.0,
                "count": 0,
                "repeated_phrases": [],
                "unique_repeated": []
            }

        # Bigram 생성
        bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]

        # 단일 토큰도 포함
        all_phrases = tokens + bigrams

        # 빈도 계산
        phrase_counts = Counter(all_phrases)

        # 2회 이상 등장하는 것만 필터링
        repeated_phrases = [
            phrase for phrase, count in phrase_counts.items()
            if count >= 2
        ]

        # 반복된 구들을 모두 나열 (["그거", "그거", "그거"])
        all_repeated = []
        for phrase, count in phrase_counts.items():
            if count >= 2:
                all_repeated.extend([phrase] * count)

        # 반복 비율 계산
        total_phrases = len(all_phrases)
        repetition_ratio = len(all_repeated) / total_phrases if total_phrases > 0 else 0.0

        logger.debug(f"Repetitiveness: {len(all_repeated)}/{total_phrases} = {repetition_ratio:.3f}")

        return {
            "ratio": repetition_ratio,
            "count": len(all_repeated),
            "repeated_phrases": all_repeated[:10],  # 최대 10개
            "unique_repeated": list(set(repeated_phrases))[:5]  # 최대 5개
        }

    async def _evaluate_narrative_structure(self, text: str) -> int:
        """
        서사 구조 평가 (LLM Judge 기반 5점 척도)

        텍스트가 기승전결의 서사 구조를 갖추고 있는지 평가합니다.
        완결된 이야기 구조는 언어 조직화 능력의 지표입니다.

        Scoring Scale:
            5점: 명확한 기승전결 구조 (시작-전개-결말)
            4점: 대체로 구조가 있음
            3점: 단순 나열이지만 이해 가능
            2점: 구조가 불명확
            1점: 구조 없음, 단편적

        Args:
            text: 평가할 텍스트

        Returns:
            서사 구조 점수 (1-5)
            - 5: 명확한 구조
            - 3: 보통
            - 1: 구조 없음
            - LLM 실패 시: 3 (중립)

        Example:
            >>> score = await self._evaluate_narrative_structure(
            ...     "옛날에 할머니와 산에 갔어요. 쑥을 많이 뜯었어요. "
            ...     "집에 와서 쑥떡을 만들어 먹었어요."
            ... )
            >>> print(score)
            5  # 시작-전개-결말

            >>> score = await self._evaluate_narrative_structure(
            ...     "쑥. 산. 할머니."
            ... )
            >>> print(score)
            1  # 단편적

        Note:
            - LLM 모델: Claude Sonnet 4.5
            - 평가 기준: 기승전결, 도입-전개-결말
            - 실패 시 기본값: 3 (중립)
        """
        try:
            prompt = f"""다음 텍스트의 서사 구조를 평가하세요.

텍스트: {text}

평가 기준:
5점: 명확한 기승전결 구조 (시작-전개-결말이 있는 완결된 이야기)
4점: 대체로 구조가 있음 (일부 요소 부족하지만 흐름 있음)
3점: 단순 나열이지만 이해 가능 (사건 나열, 구조는 불명확)
2점: 구조가 불명확 (연결성 부족, 파편적)
1점: 구조 없음 (단어 나열, 완전 단편적)

숫자만 출력하세요 (1-5).
"""

            result = await self.llm.call(prompt, max_tokens=5)
            score = int(result.strip())

            # 1-5 범위 강제
            score = max(1, min(5, score))

            logger.debug(f"Narrative structure score: {score}/5")
            return score

        except ValueError as e:
            logger.error(f"Failed to parse structure score: {e}, defaulting to 3")
            return 3
        except Exception as e:
            logger.error(f"Failed to evaluate narrative structure: {e}", exc_info=True)
            return 3
