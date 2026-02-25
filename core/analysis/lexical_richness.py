"""
어휘 풍부도 (LR - Lexical Richness) 분석기

Fraser et al. (2016) "Linguistic Features Identify Alzheimer's Disease" 기반:
- 대명사 대체율 증가 = 인지 저하 신호 (단어 인출 장애)
- Type-Token Ratio (TTR) 감소 = 어휘 빈약
- 구체 명사 감소 = 추상화 능력 저하
- 빈 발화 증가 = 단어 인출 장애

4개 하위 지표:
1. Pronoun Ratio (PR): 대명사 / 명사 비율 (↓ 좋음)
2. Moving Average TTR (MATTR): 어휘 다양성 (↑ 좋음)
3. Concreteness: 구체 명사 비율 (↑ 좋음)
4. Empty Speech Ratio (ESR): 빈 발화 비율 (↓ 좋음)

LR Score = (1 - PR) × 25 + MATTR × 25 + Concreteness × 25 + (1 - ESR) × 25

Author: Memory Garden Team
Created: 2025-02-10
Updated: 2025-02-11
"""

# ============================================
# Standard Library Imports
# ============================================
from typing import Dict, Any, List

# ============================================
# Third-Party Imports
# ============================================
from kiwipiepy import Kiwi
import numpy as np

# ============================================
# Local Imports
# ============================================
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# Logger 설정
# ============================================
logger = get_logger(__name__)


# ============================================
# LexicalRichnessAnalyzer
# ============================================

class LexicalRichnessAnalyzer:
    """
    어휘 풍부도 (Lexical Richness) 분석기

    Fraser et al. (2016) 논문 기반으로 한국어 대화에서
    어휘 다양성과 풍부도를 측정하여 인지 저하를 감지합니다.

    Attributes:
        kiwi: Kiwi 한국어 형태소 분석기
        empty_speech_patterns: 빈 발화 패턴 리스트

    Example:
        >>> analyzer = LexicalRichnessAnalyzer()
        >>> result = await analyzer.analyze("오늘 날씨가 좋아서 산책했어요")
        >>> print(result["score"])
        78.5
    """

    def __init__(self):
        """
        LexicalRichnessAnalyzer 초기화

        Kiwi 형태소 분석기를 초기화하고 빈 발화 패턴을 설정합니다.
        """
        # Kiwi 형태소 분석기 초기화
        self.kiwi = Kiwi()

        # 빈 발화 패턴 (Empty Speech Patterns)
        # 치매 환자에게서 자주 나타나는 무의미한 대명사/지시어
        self.empty_speech_patterns = [
            "그거", "저거", "뭐더라", "있잖아", "그게",
            "어", "음", "그", "저", "이거",
            "아니", "그냥", "뭐", "그런", "저런"
        ]

    async def analyze(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        텍스트의 어휘 풍부도를 분석합니다.

        Args:
            message: 분석할 텍스트
            context: 추가 컨텍스트 (현재 미사용, 향후 확장용)

        Returns:
            {
                "score": 78.5,  # 0-100 점수
                "components": {
                    "pronoun_ratio": 0.15,      # 대명사 비율 (낮을수록 좋음)
                    "mattr": 0.72,              # Moving Average TTR (높을수록 좋음)
                    "concreteness": 0.85,       # 구체성 (높을수록 좋음)
                    "empty_speech_ratio": 0.05  # 빈 발화 비율 (낮을수록 좋음)
                },
                "details": {
                    "total_tokens": 42,
                    "unique_tokens": 30,
                    "pronouns": ["그거", "저거"],
                    "concrete_nouns": ["날씨", "산책", "공원", "나무", "꽃"]
                }
            }

        Raises:
            AnalysisError: 분석 실패 시

        Example:
            >>> result = await analyzer.analyze("봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요")
            >>> print(f"LR Score: {result['score']}")
            LR Score: 85.3
        """
        # 입력 검증
        if not message or not message.strip():
            logger.error("Empty message provided to LexicalRichnessAnalyzer")
            raise AnalysisError("Message cannot be empty for lexical richness analysis")

        try:
            # ============================================
            # 1. 형태소 분석
            # ============================================
            tokens = self._tokenize(message)

            if not tokens:
                logger.warning(f"No tokens extracted from message: {message[:50]}")
                return self._empty_result()

            # ============================================
            # 2. 4개 하위 지표 계산
            # ============================================

            # 2.1 대명사 비율 (Pronoun Ratio)
            # Formula: PR = N_pronouns / N_nouns
            # 낮을수록 좋음 (대명사 대신 구체적인 명사 사용)
            pronoun_ratio = self._calculate_pronoun_ratio(tokens)

            # 2.2 Moving Average TTR (어휘 다양성)
            # Formula: MATTR = (1/N) × Σ TTR_i (window=20)
            # 높을수록 좋음 (다양한 어휘 사용)
            mattr = self._calculate_mattr(tokens)

            # 2.3 구체성 (Concreteness)
            # Formula: Concreteness = N_concrete_nouns / N_nouns
            # 높을수록 좋음 (구체적 명사 사용)
            concreteness = self._calculate_concreteness(tokens)

            # 2.4 빈 발화 비율 (Empty Speech Ratio)
            # Formula: ESR = N_empty_words / N_total_words
            # 낮을수록 좋음 ("그거", "뭐더라" 등 무의미한 단어)
            empty_speech_ratio = self._calculate_empty_speech(message)

            # ============================================
            # 3. 종합 점수 계산
            # ============================================
            # LR Score = (1 - PR) × 25 + MATTR × 25 + Concreteness × 25 + (1 - ESR) × 25
            # 역방향 지표(PR, ESR)는 (1 - 값)으로 반전
            # 각 지표는 0~1 범위이므로 × 25로 정규화 (4개 합=100)
            score = (
                (1 - pronoun_ratio) * 25 +      # 대명사 적을수록 +
                mattr * 100 * 0.25 +            # 어휘 다양할수록 +
                concreteness * 100 * 0.25 +     # 구체적일수록 +
                (1 - empty_speech_ratio) * 25   # 빈 발화 적을수록 +
            )

            # ============================================
            # 4. 결과 반환
            # ============================================
            result = {
                "score": round(score, 2),
                "components": {
                    "pronoun_ratio": round(pronoun_ratio, 3),
                    "mattr": round(mattr, 3),
                    "concreteness": round(concreteness, 3),
                    "empty_speech_ratio": round(empty_speech_ratio, 3)
                },
                "details": {
                    "total_tokens": len(tokens),
                    "unique_tokens": len(set(t['form'] for t in tokens)),
                    "pronouns": self._extract_pronouns(tokens),
                    "concrete_nouns": self._extract_concrete_nouns(tokens)
                }
            }

            logger.debug(
                f"LR analysis complete: score={score:.2f}",
                extra={
                    "pronoun_ratio": pronoun_ratio,
                    "mattr": mattr,
                    "concreteness": concreteness,
                    "empty_speech_ratio": empty_speech_ratio
                }
            )

            return result

        except Exception as e:
            logger.error(f"Lexical Richness analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"LR analysis failed: {e}") from e

    def _tokenize(self, text: str) -> List[Dict]:
        """
        Kiwi 형태소 분석

        Args:
            text: 분석할 텍스트

        Returns:
            [{"form": "엄마", "pos": "NNG"}, {"form": "가", "pos": "JKS"}, ...]

        Note:
            Kiwi 품사 태그:
            - NNG: 일반 명사 (구체 명사)
            - NNP: 고유 명사
            - NP: 대명사 (이것, 그것, 저것 등)
            - VV: 동사
            - VA: 형용사
        """
        try:
            result = self.kiwi.analyze(text)
            tokens = []

            # Kiwi 결과: [(token, pos, start, end), ...]
            for token, pos, _, _ in result[0][0]:
                tokens.append({"form": token, "pos": pos})

            return tokens

        except Exception as e:
            logger.error(f"Tokenization failed: {e}", exc_info=True)
            return []

    def _calculate_pronoun_ratio(self, tokens: List[Dict]) -> float:
        """
        대명사 비율 계산

        Formula:
            PR = N_pronouns / N_nouns

        Args:
            tokens: 형태소 분석 결과

        Returns:
            0.0 ~ 1.0 (낮을수록 좋음)

        Example:
            >>> tokens = [
            ...     {"form": "그거", "pos": "NP"},   # 대명사
            ...     {"form": "먹었어", "pos": "VV"},
            ...     {"form": "밥", "pos": "NNG"}     # 명사
            ... ]
            >>> ratio = _calculate_pronoun_ratio(tokens)
            >>> print(ratio)
            0.5  # 1개 대명사 / 2개 명사
        """
        # NP: 대명사 (이것, 그것, 저것, 여기, 거기 등)
        pronouns = [t for t in tokens if t['pos'] == 'NP']

        # N으로 시작: 명사류 (NNG, NNP, NP 등)
        nouns = [t for t in tokens if t['pos'].startswith('N')]

        if not nouns:
            return 0.0  # 명사가 없으면 0

        ratio = len(pronouns) / len(nouns)

        logger.debug(
            f"Pronoun ratio: {ratio:.3f} ({len(pronouns)} pronouns / {len(nouns)} nouns)"
        )

        return ratio

    def _calculate_mattr(self, tokens: List[Dict], window: int = 20) -> float:
        """
        Moving Average Type-Token Ratio 계산

        Formula:
            MATTR = (1 / (N - W + 1)) × Σ TTR_i
            where TTR_i = unique_tokens_i / W

        Args:
            tokens: 형태소 분석 결과
            window: 윈도우 크기 (기본 20)

        Returns:
            0.0 ~ 1.0 (높을수록 좋음)

        Note:
            짧은 텍스트 (<20 토큰)는 일반 TTR 사용
            긴 텍스트는 20토큰 윈도우를 슬라이딩하며 평균 계산

        Example:
            >>> # 20토큰 미만: TTR = unique / total
            >>> tokens = [{"form": "나", "pos": "NP"}, {"form": "는", "pos": "JX"}, ...]
            >>> mattr = _calculate_mattr(tokens)

            >>> # 20토큰 이상: Moving Average
            >>> long_tokens = [...]  # 50개 토큰
            >>> mattr = _calculate_mattr(long_tokens)  # 31개 윈도우의 평균
        """
        if len(tokens) < window:
            # 짧은 문장: 일반 TTR = unique / total
            forms = [t['form'] for t in tokens]
            if not forms:
                return 0.0

            ttr = len(set(forms)) / len(forms)
            logger.debug(f"Short text TTR: {ttr:.3f} ({len(set(forms))} / {len(forms)})")
            return ttr

        # 긴 문장: Moving Average TTR
        ttrs = []
        for i in range(len(tokens) - window + 1):
            window_tokens = [tokens[j]['form'] for j in range(i, i + window)]
            window_unique = len(set(window_tokens))
            ttr = window_unique / window
            ttrs.append(ttr)

        mattr = np.mean(ttrs)
        logger.debug(
            f"MATTR: {mattr:.3f} (averaged over {len(ttrs)} windows)"
        )

        return float(mattr)

    def _calculate_concreteness(self, tokens: List[Dict]) -> float:
        """
        구체 명사 비율 계산

        Formula:
            Concreteness = N_concrete_nouns / N_nouns

        Args:
            tokens: 형태소 분석 결과

        Returns:
            0.0 ~ 1.0 (높을수록 좋음)

        Note:
            - NNG (일반명사): 구체 명사로 간주 (예: 나무, 집, 밥)
            - NNP (고유명사): 추상 명사로 간주 (예: 서울, 한국)
            - 실제로는 더 정교한 구체성 사전이 필요하지만,
              초기 구현에서는 NNG/NNP 비율로 근사

        Example:
            >>> tokens = [
            ...     {"form": "나무", "pos": "NNG"},   # 구체 명사
            ...     {"form": "집", "pos": "NNG"},     # 구체 명사
            ...     {"form": "서울", "pos": "NNP"}    # 고유 명사
            ... ]
            >>> concreteness = _calculate_concreteness(tokens)
            >>> print(concreteness)
            0.667  # 2개 NNG / 3개 명사
        """
        # NN으로 시작: 명사 (NNG, NNP)
        nouns = [t for t in tokens if t['pos'].startswith('NN')]

        # NNG: 일반명사 (구체 명사로 간주)
        concrete = [t for t in nouns if t['pos'] == 'NNG']

        if not nouns:
            return 0.5  # 명사가 없으면 중립값

        ratio = len(concrete) / len(nouns)

        logger.debug(
            f"Concreteness: {ratio:.3f} ({len(concrete)} concrete / {len(nouns)} nouns)"
        )

        return ratio

    def _calculate_empty_speech(self, text: str) -> float:
        """
        빈 발화 비율 계산

        Formula:
            ESR = N_empty_words / N_total_words

        Args:
            text: 원본 텍스트

        Returns:
            0.0 ~ 1.0 (낮을수록 좋음)

        Note:
            치매 환자에게서 자주 나타나는 패턴:
            - "그거 있잖아 그거 뭐더라"
            - "저기 그 뭐 있잖아요"
            - "음... 어... 그..."

        Example:
            >>> text = "그거 있잖아 그거 먹었어요"
            >>> esr = _calculate_empty_speech(text)
            >>> print(esr)
            0.5  # 2개 빈 발화 / 4개 단어
        """
        words = text.split()
        if not words:
            return 0.0

        # 빈 발화 패턴에 매칭되는 단어 수
        empty_count = sum(
            1 for word in words
            if any(pattern in word for pattern in self.empty_speech_patterns)
        )

        ratio = empty_count / len(words)

        logger.debug(
            f"Empty speech ratio: {ratio:.3f} ({empty_count} empty / {len(words)} words)"
        )

        return ratio

    def _extract_pronouns(self, tokens: List[Dict]) -> List[str]:
        """
        대명사 추출

        Args:
            tokens: 형태소 분석 결과

        Returns:
            ["그거", "저거", "이것"] 형태의 대명사 리스트
        """
        pronouns = [t['form'] for t in tokens if t['pos'] == 'NP']
        return pronouns

    def _extract_concrete_nouns(self, tokens: List[Dict]) -> List[str]:
        """
        구체 명사 추출 (최대 5개)

        Args:
            tokens: 형태소 분석 결과

        Returns:
            ["나무", "집", "밥", "공원", "꽃"] 형태의 구체 명사 리스트
        """
        concrete_nouns = [t['form'] for t in tokens if t['pos'] == 'NNG']
        return concrete_nouns[:5]  # 최대 5개만 반환

    def _empty_result(self) -> Dict[str, Any]:
        """
        빈 결과 반환 (분석 실패 시)

        Returns:
            모든 값이 0인 결과 딕셔너리
        """
        return {
            "score": 0.0,
            "components": {
                "pronoun_ratio": 0.0,
                "mattr": 0.0,
                "concreteness": 0.0,
                "empty_speech_ratio": 0.0
            },
            "details": {
                "total_tokens": 0,
                "unique_tokens": 0,
                "pronouns": [],
                "concrete_nouns": []
            }
        }
