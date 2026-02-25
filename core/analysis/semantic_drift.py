"""
의미적 표류 (SD - Semantic Drift) 분석기

질문-응답 의미 관련성 분석을 통한 주의력 및 집행기능 평가

Scientific Basis:
    Fraser et al. (2016) "Linguistic Features Identify Alzheimer's Disease
    in Narrative Speech" 논문 기반

    - 질문-응답 관련도 저하 = 주의력 저하
    - 문장 간 응집도 감소 = 집행기능 저하
    - 주제 이탈 빈도 증가 = 작업 기억 손상
    - 논리성 저하 = 추론 능력 저하

Analysis Metrics:
    1. Relevance (관련도): 질문-응답 임베딩 코사인 유사도
       Formula: cosine_sim = (q·a) / (||q|| × ||a||)

    2. Coherence (응집도): 인접 문장 간 의미 유사도 평균
       Formula: coherence = (1/N-1) × Σ sim(s_i, s_{i+1})

    3. Topic Drift (주제 이탈): LLM 기반 이진 분류 (0: 정상, 1: 이탈)

    4. Logical Flow (논리성): LLM 기반 5점 척도 평가

Scoring Formula:
    SD_Score = Relevance × 35 + Coherence × 30 + (1 - TopicDrift) × 15 + LogicalFlow × 4

    Range: 0-100 (높을수록 좋음)

    - Relevance: 0-1 범위 (질문-응답 관련성)
    - Coherence: 0-1 범위 (문장 간 의미 연결성)
    - TopicDrift: 0 or 1 (0: 정상, 1: 이탈)
    - LogicalFlow: 1-5 점수 (논리적 흐름 평가)

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2025-02-10
"""

from typing import Dict, Any, List, Optional
import re
import numpy as np

from services.llm_service import LLMService
from core.nlp.embedder import Embedder
from utils.logger import get_logger
from utils.exceptions import AnalysisError

logger = get_logger(__name__)


class SemanticDriftAnalyzer:
    """
    의미적 표류 (Semantic Drift) 분석기

    질문-응답 관련성, 문장 간 응집도, 주제 이탈, 논리성을 종합 평가하여
    사용자의 주의력 및 집행기능 상태를 분석합니다.

    Attributes:
        llm: LLM 서비스 (주제 이탈 및 논리성 평가용)
        embedder: 임베딩 서비스 (관련도 및 응집도 계산용)

    Example:
        >>> analyzer = SemanticDriftAnalyzer(llm_service, embedder)
        >>> result = await analyzer.analyze(
        ...     message="봄에는 쑥을 뜯으러 뒷산에 갔어요",
        ...     context={"question": "어머니와 함께 했던 봄철 추억이 있나요?"}
        ... )
        >>> print(result["score"])
        85.2
        >>> print(result["components"]["relevance"])
        0.892
    """

    def __init__(self, llm_service: LLMService, embedder: Embedder):
        """
        의미적 표류 분석기 초기화

        Args:
            llm_service: LLM 서비스 인스턴스
            embedder: 임베딩 서비스 인스턴스
        """
        self.llm = llm_service
        self.embedder = embedder

        logger.info("SemanticDriftAnalyzer initialized")
    
    async def analyze(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        의미적 표류 종합 분석

        사용자 응답의 의미적 관련성, 문장 응집도, 주제 이탈, 논리성을 평가하여
        주의력 및 집행기능 상태를 측정합니다.

        Args:
            message: 사용자 응답 텍스트
            context: 분석 컨텍스트 (선택)
                - question: 원래 질문 (질문-응답 관련도 계산에 사용)
                - previous_messages: 이전 대화 내용 (미사용, 향후 확장용)

        Returns:
            분석 결과 딕셔너리
            {
                "score": 82.3,  # SD 종합 점수 (0-100)
                "components": {
                    "relevance": 0.75,      # 질문-응답 관련도 (0-1)
                    "coherence": 0.82,      # 문장 간 응집도 (0-1)
                    "topic_drift": 0,       # 주제 이탈 여부 (0 or 1)
                    "logical_flow": 4       # 논리성 평가 (1-5)
                },
                "details": {
                    "question": "...",
                    "answer_length": 42,
                    "sentence_count": 3,
                    "drift_detected": False
                }
            }

        Raises:
            AnalysisError: 분석 실패 시

        Example:
            >>> analyzer = SemanticDriftAnalyzer(llm, embedder)
            >>> result = await analyzer.analyze(
            ...     message="봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요",
            ...     context={"question": "어머니와 함께 했던 봄철 추억이 있나요?"}
            ... )
            >>> print(f"SD Score: {result['score']}")
            SD Score: 85.2
            >>> print(f"Relevance: {result['components']['relevance']}")
            Relevance: 0.892

        Note:
            - 질문이 없는 경우 relevance는 1.0 (중립)으로 설정
            - 단일 문장인 경우 coherence는 1.0으로 설정
            - LLM 호출 실패 시 기본값 사용 (topic_drift=0, logical_flow=3)
        """
        logger.debug(f"Starting SD analysis for message (length={len(message)})")

        # ============================================
        # 0. 입력 검증
        # ============================================
        if not message or not message.strip():
            logger.warning("Empty message provided for SD analysis")
            raise AnalysisError("Message cannot be empty")

        try:
            # ============================================
            # 1. 컨텍스트 추출
            # ============================================
            question = context.get("question", "") if context else ""
            logger.debug(f"Question: '{question[:50]}...' (length={len(question)})")

            # ============================================
            # 2. 4개 지표 계산
            # ============================================

            # 2.1 질문-응답 관련도 (Embedding Cosine Similarity)
            # Formula: cosine_sim = (q·a) / (||q|| × ||a||)
            # 높을수록 좋음 (0-1 범위)
            logger.debug("Calculating relevance...")
            relevance = await self._calculate_relevance(question, message)
            logger.debug(f"Relevance: {relevance:.3f}")

            # 2.2 문장 간 응집도 (Sentence-level Coherence)
            # Formula: coherence = (1/N-1) × Σ sim(s_i, s_{i+1})
            # 높을수록 좋음 (0-1 범위)
            logger.debug("Calculating coherence...")
            coherence = await self._calculate_coherence(message)
            logger.debug(f"Coherence: {coherence:.3f}")

            # 2.3 주제 이탈 탐지 (LLM Judge)
            # 0: 정상, 1: 이탈
            # 낮을수록 좋음
            logger.debug("Detecting topic drift...")
            topic_drift = await self._detect_topic_drift(question, message)
            logger.debug(f"Topic drift: {topic_drift}")

            # 2.4 논리성 평가 (LLM Judge)
            # 1-5점 척도
            # 높을수록 좋음
            logger.debug("Evaluating logical flow...")
            logical_flow = await self._evaluate_logic(message)
            logger.debug(f"Logical flow: {logical_flow}/5")

            # ============================================
            # 3. 종합 점수 계산
            # ============================================
            # Formula: SD = relevance×35 + coherence×30 + (1-drift)×15 + logic×4
            # Range: 0-100
            score = (
                relevance * 100 * 0.35 +           # 질문-응답 관련도 (35%)
                coherence * 100 * 0.30 +           # 문장 간 응집도 (30%)
                (1 - topic_drift) * 100 * 0.15 +   # 주제 이탈 반전 (15%)
                logical_flow * 20 * 0.20           # 논리성 평가 (20%, 1-5 → 0-20)
            )

            logger.info(
                f"SD analysis completed: score={score:.2f}",
                extra={
                    "relevance": relevance,
                    "coherence": coherence,
                    "topic_drift": topic_drift,
                    "logical_flow": logical_flow
                }
            )

            # ============================================
            # 4. 결과 반환
            # ============================================
            return {
                "score": round(score, 2),
                "components": {
                    "relevance": round(relevance, 3),
                    "coherence": round(coherence, 3),
                    "topic_drift": int(topic_drift),
                    "logical_flow": logical_flow
                },
                "details": {
                    "question": question[:100] if question else None,
                    "answer_length": len(message),
                    "sentence_count": len([s for s in message.split('.') if s.strip()]),
                    "drift_detected": bool(topic_drift),
                    "has_question": bool(question)
                }
            }

        except Exception as e:
            logger.error(f"SD analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Semantic Drift analysis failed: {e}") from e
    
    async def _calculate_relevance(self, question: str, answer: str) -> float:
        """
        질문-응답 관련도 계산 (임베딩 코사인 유사도)

        질문과 응답의 의미 벡터 간 코사인 유사도를 계산하여
        응답이 질문과 얼마나 관련이 있는지 평가합니다.

        Formula:
            cosine_similarity = (q · a) / (||q|| × ||a||)
            normalized = (similarity + 1) / 2  # -1~1 → 0~1 변환

        Args:
            question: 원래 질문 텍스트
            answer: 사용자 응답 텍스트

        Returns:
            관련도 점수 (0.0-1.0)
            - 1.0: 매우 관련 있음
            - 0.5: 중립
            - 0.0: 전혀 관련 없음
            - 질문이 없는 경우: 1.0 (중립값)

        Example:
            >>> rel = await self._calculate_relevance(
            ...     "어머니와 함께 했던 봄철 추억이 있나요?",
            ...     "봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요"
            ... )
            >>> print(rel)
            0.892

        Note:
            - 임베딩 차원: 1536 (OpenAI text-embedding-ada-002)
            - 코사인 유사도 범위: -1 ~ 1
            - 정규화 후 범위: 0 ~ 1
        """
        if not question or not question.strip():
            logger.debug("No question provided, returning neutral relevance")
            return 1.0  # 질문이 없으면 중립

        try:
            # 질문과 응답 임베딩
            q_vec = await self.embedder.embed(question)
            a_vec = await self.embedder.embed(answer)

            # 코사인 유사도 계산
            # Formula: cos(θ) = (A·B) / (||A|| × ||B||)
            similarity = np.dot(q_vec, a_vec) / (
                np.linalg.norm(q_vec) * np.linalg.norm(a_vec)
            )

            # -1~1 범위를 0~1로 정규화
            # -1 (반대 방향) → 0, 0 (직교) → 0.5, 1 (같은 방향) → 1
            normalized = max(0.0, min(1.0, (similarity + 1) / 2))

            logger.debug(f"Relevance: raw={similarity:.3f}, normalized={normalized:.3f}")
            return normalized

        except Exception as e:
            logger.error(f"Failed to calculate relevance: {e}", exc_info=True)
            return 0.5  # 실패 시 중립값 반환
    
    async def _calculate_coherence(self, text: str) -> float:
        """
        문장 간 응집도 계산 (인접 문장 유사도 평균)

        텍스트를 문장 단위로 분할한 후, 인접한 문장 간 의미 유사도를
        계산하여 문장 간 응집력을 평가합니다.

        Formula:
            coherence = (1 / N-1) × Σ_{i=1}^{N-1} cosine_sim(s_i, s_{i+1})

            where:
            - N: 문장 개수
            - s_i: i번째 문장의 임베딩 벡터
            - cosine_sim: 코사인 유사도

        Args:
            text: 분석할 텍스트 (여러 문장)

        Returns:
            응집도 점수 (0.0-1.0)
            - 1.0: 매우 응집적 (문장 간 의미 연결성 높음)
            - 0.5: 보통
            - 0.0: 비응집적 (문장 간 의미 연결성 낮음)
            - 단일 문장: 1.0 (응집도 평가 불가)

        Example:
            >>> coherence = await self._calculate_coherence(
            ...     "봄에는 쑥을 뜯었어요. 쑥떡을 만들어 먹었어요. 정말 맛있었어요."
            ... )
            >>> print(coherence)
            0.872

        Note:
            - 문장 구분자: 마침표 (.)
            - 빈 문장은 자동으로 제외
            - 2개 미만 문장: 1.0 반환
        """
        # 문장 분할 (마침표 기준)
        sentences = [s.strip() for s in text.split('.') if s.strip()]

        if len(sentences) < 2:
            logger.debug("Single sentence, returning max coherence")
            return 1.0

        logger.debug(f"Calculating coherence for {len(sentences)} sentences")

        try:
            # 각 문장 임베딩
            embeddings = []
            for i, sentence in enumerate(sentences):
                emb = await self.embedder.embed(sentence)
                embeddings.append(emb)
                logger.debug(f"Sentence {i+1} embedded (dim={len(emb)})")

            # 인접 문장 간 코사인 유사도 계산
            similarities = []
            for i in range(len(embeddings) - 1):
                # cos(θ) = (A·B) / (||A|| × ||B||)
                sim = np.dot(embeddings[i], embeddings[i+1]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i+1])
                )
                similarities.append(sim)
                logger.debug(f"Similarity s{i+1}-s{i+2}: {sim:.3f}")

            # 평균 응집도
            coherence = float(np.mean(similarities)) if similarities else 1.0

            # -1~1 범위를 0~1로 정규화
            normalized = max(0.0, min(1.0, (coherence + 1) / 2))

            logger.debug(f"Coherence: raw={coherence:.3f}, normalized={normalized:.3f}")
            return normalized

        except Exception as e:
            logger.error(f"Failed to calculate coherence: {e}", exc_info=True)
            return 0.5  # 실패 시 중립값 반환
    
    async def _detect_topic_drift(self, question: str, answer: str) -> int:
        """
        주제 이탈 탐지 (LLM Judge 기반 이진 분류)

        LLM을 활용하여 응답이 질문의 주제에서 벗어났는지 판단합니다.
        주제 이탈은 주의력 저하 및 작업 기억 손상의 지표입니다.

        Classification:
            0: 정상 (질문과 관련 있는 응답)
            1: 이탈 (질문과 무관한 응답)

        Args:
            question: 원래 질문
            answer: 사용자 응답

        Returns:
            이탈 여부 (0 or 1)
            - 0: 주제 정상 유지
            - 1: 주제 이탈 감지
            - 질문이 없는 경우: 0 (평가 불가)
            - LLM 실패 시: 0 (보수적 기본값)

        Example:
            >>> drift = await self._detect_topic_drift(
            ...     question="어머니와 함께 했던 봄철 추억이 있나요?",
            ...     answer="봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요"
            ... )
            >>> print(drift)
            0  # 정상

            >>> drift = await self._detect_topic_drift(
            ...     question="어머니와 함께 했던 봄철 추억이 있나요?",
            ...     answer="요즘 날씨가 너무 덥네요"
            ... )
            >>> print(drift)
            1  # 이탈

        Note:
            - LLM 모델: Claude Sonnet 4.5 (config/settings.py)
            - 평가 기준: 의미적 관련성 (키워드 매칭이 아님)
            - 실패 시 기본값: 0 (false negative 최소화)
        """
        if not question or not question.strip():
            logger.debug("No question provided, assuming no drift")
            return 0

        try:
            # LLM 프롬프트: 이진 분류 (0 or 1)
            prompt = f"""다음 질문과 답변의 관련성을 평가하세요.

질문: {question}
답변: {answer}

답변이 질문과 관련이 있으면 0, 주제를 완전히 벗어났으면 1을 출력하세요.
반드시 숫자 0 또는 1만 단독으로 출력하세요. 다른 텍스트는 절대 출력하지 마세요.
"""

            result = await self.llm.call(prompt, max_tokens=10)
            result = result.strip()

            # 정규식으로 첫 번째 숫자 추출 (LLM이 추가 텍스트를 반환하는 경우 대비)
            match = re.search(r'[01]', result)
            if match:
                drift = int(match.group())
            else:
                logger.warning(f"No valid drift value found in: '{result}', defaulting to 0")
                drift = 0

            logger.debug(f"Topic drift detected: {drift}")
            return drift

        except Exception as e:
            logger.error(f"Failed to detect topic drift: {e}", exc_info=True)
            return 0  # 실패 시 보수적 기본값 (false negative 최소화)
    
    async def _evaluate_logic(self, text: str) -> int:
        """
        논리성 평가 (LLM Judge 기반 5점 척도)

        LLM을 활용하여 텍스트의 논리적 흐름, 인과관계, 추론 능력을 평가합니다.
        논리성 저하는 집행기능 및 추론 능력 저하의 지표입니다.

        Scoring Scale:
            5점: 논리적 흐름이 명확, 인과관계 뚜렷
            4점: 대체로 논리적, 일부 비약 있음
            3점: 보통 수준의 논리성
            2점: 다소 비논리적, 비약이 많음
            1점: 논리 없음, 횡설수설

        Args:
            text: 평가할 텍스트

        Returns:
            논리성 점수 (1-5)
            - 5: 매우 논리적
            - 4: 논리적
            - 3: 보통 (중립)
            - 2: 비논리적
            - 1: 매우 비논리적
            - LLM 실패 시: 3 (보수적 중립값)

        Example:
            >>> logic = await self._evaluate_logic(
            ...     "봄에는 쑥이 많이 나요. 그래서 엄마가 쑥을 뜯으러 가셨어요. "
            ...     "쑥떡을 만들어서 가족들과 함께 먹었어요."
            ... )
            >>> print(logic)
            5  # 명확한 인과관계

            >>> logic = await self._evaluate_logic(
            ...     "봄이에요. 날씨가 좋아요. 그거 있잖아요. 뭐더라..."
            ... )
            >>> print(logic)
            2  # 비논리적, 비약 많음

        Note:
            - LLM 모델: Claude Sonnet 4.5
            - 평가 기준: 논리적 흐름, 인과관계, 추론 일관성
            - 범위 강제: 1-5 (범위 밖 값은 자동 보정)
            - 실패 시 기본값: 3 (중립)
        """
        try:
            # LLM 프롬프트: 5점 척도 평가
            prompt = f"""다음 텍스트의 논리성을 1-5점으로 평가하세요.

텍스트: {text}

평가 기준:
5점: 논리적 흐름이 명확, 인과관계 뚜렷
4점: 대체로 논리적, 일부 비약 있음
3점: 보통 수준의 논리성
2점: 다소 비논리적, 비약이 많음
1점: 논리 없음, 횡설수설

반드시 1부터 5 사이의 숫자 하나만 단독으로 출력하세요. 다른 텍스트는 절대 출력하지 마세요.
"""

            result = await self.llm.call(prompt, max_tokens=10)
            result = result.strip()

            # 정규식으로 첫 번째 1-5 숫자 추출 (LLM이 추가 텍스트를 반환하는 경우 대비)
            match = re.search(r'[1-5]', result)
            if match:
                score = int(match.group())
            else:
                logger.warning(f"No valid logic score found in: '{result}', defaulting to 3")
                score = 3

            # 1-5 범위 강제
            score = max(1, min(5, score))

            logger.debug(f"Logical flow score: {score}/5")
            return score

        except Exception as e:
            logger.error(f"Failed to evaluate logic: {e}", exc_info=True)
            return 3  # 실패 시 중립값
