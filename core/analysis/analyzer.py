"""
분석 총괄 클래스 (Analyzer)

6개 인지 지표를 통합 관리하고 MCDI 종합 점수를 계산

6개 지표를 병렬 실행하여 성능을 최적화하고, 개별 지표 실패 시에도
나머지 지표로 MCDI를 계산할 수 있도록 설계되었습니다.

Analysis Pipeline:
    1. 6개 지표 병렬 실행 (asyncio.gather)
    2. 실패한 지표 처리 (로깅 및 None 처리)
    3. 유효 지표만으로 MCDI 계산
    4. 모순 탐지 (선택적)
    5. 종합 결과 반환

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2025-02-10
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from core.analysis.lexical_richness import LexicalRichnessAnalyzer
from core.analysis.semantic_drift import SemanticDriftAnalyzer
from core.analysis.narrative_coherence import NarrativeCoherenceAnalyzer
from core.analysis.temporal_orientation import TemporalOrientationAnalyzer
from core.analysis.episodic_recall import EpisodicRecallAnalyzer
from core.analysis.response_time import ResponseTimeAnalyzer
from core.analysis.mcdi_calculator import MCDICalculator
from core.analysis.contradiction_detector import ContradictionDetector
from services.llm_service import LLMService
from core.nlp.embedder import Embedder
from utils.logger import get_logger
from utils.exceptions import AnalysisError

logger = get_logger(__name__)


class Analyzer:
    """
    분석 총괄 클래스

    6개 인지 지표를 병렬로 실행하고 MCDI 종합 점수를 계산합니다.
    개별 지표 실패 시에도 나머지 지표로 계속 진행합니다.

    Attributes:
        lr: Lexical Richness Analyzer (어휘 풍부도)
        sd: Semantic Drift Analyzer (의미적 표류)
        nc: Narrative Coherence Analyzer (서사 일관성)
        to: Temporal Orientation Analyzer (시간적 지남력)
        er: Episodic Recall Analyzer (일화 기억)
        rt: Response Time Analyzer (반응 시간)
        mcdi: MCDI Calculator (종합 점수 계산기)
        contradiction: Contradiction Detector (모순 탐지기)

    Example:
        >>> analyzer = Analyzer(llm_service, embedder)
        >>> result = await analyzer.analyze(
        ...     message="봄에는 엄마와 뒷산에서 쑥을 뜯었어요",
        ...     memory={
        ...         "question": "어머니와 함께 했던 봄철 추억이 있나요?",
        ...         "current_datetime": datetime.now(),
        ...         "response_latency": 3.5
        ...     }
        ... )
        >>> print(result["mcdi_score"])
        78.85
        >>> print(result["scores"])
        {"LR": 78.5, "SD": 82.3, "NC": 75.0, ...}
    """

    def __init__(
        self,
        llm_service: LLMService,
        embedder: Embedder
    ):
        """
        분석 총괄 클래스 초기화

        Args:
            llm_service: LLM 서비스 인스턴스
            embedder: 임베딩 서비스 인스턴스
        """
        # ============================================
        # 6개 분석기 초기화
        # ============================================
        self.lr = LexicalRichnessAnalyzer()
        self.sd = SemanticDriftAnalyzer(llm_service, embedder)
        self.nc = NarrativeCoherenceAnalyzer(llm_service)
        self.to = TemporalOrientationAnalyzer(llm_service)
        self.er = EpisodicRecallAnalyzer(llm_service)
        self.rt = ResponseTimeAnalyzer()

        # ============================================
        # 계산기 및 탐지기 초기화
        # ============================================
        self.mcdi = MCDICalculator()
        self.contradiction = ContradictionDetector(llm_service, embedder)

        logger.info("Analyzer initialized with 6 indicators + MCDI calculator")

    async def analyze(
        self,
        message: str,
        memory: Optional[Dict[str, Any]] = None,
        message_type: str = "text",
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        전체 분석 실행

        6개 지표를 병렬로 실행하고 MCDI 종합 점수를 계산합니다.
        개별 지표가 실패해도 나머지로 계속 진행합니다.

        Args:
            message: 사용자 메시지
            memory: 검색된 메모리 데이터 (선택)
                - question: 질문 텍스트 (SD용)
                - current_datetime: 현재 시간 (TO용)
                - episodic: 과거 사실 목록 (ER용)
                - biographical: 생애 정보 (ER용)
                - previous_statements: 이전 진술 (ER용)
                - response_latency: 응답 시간 (RT용, 필수!)
                - typing_pauses: 타이핑 중단 (RT용)
                - historical_latencies: 과거 응답 시간 (RT용)
            message_type: 메시지 유형 ("text", "image", "selection")
            image_url: 이미지 URL (선택)

        Returns:
            {
                "scores": {"LR": 78.5, "SD": 82.3, ...},
                "mcdi_score": 76.88,
                "mcdi_details": {
                    "reliability": 1.0,
                    "risk_category": "YELLOW",
                    ...
                },
                "lr_detail": {...},
                "sd_detail": {...},
                "nc_detail": {...},
                "to_detail": {...},
                "er_detail": {...},
                "rt_detail": {...},
                "contradictions": [...],
                "failed_metrics": [],
                "timestamp": "2025-02-10T10:30:00Z"
            }

        Raises:
            AnalysisError: 모든 지표 실패 또는 MCDI 계산 실패 시

        Example:
            >>> result = await analyzer.analyze(
            ...     message="봄에는 엄마와 쑥을 뜯었어요",
            ...     memory={
            ...         "question": "어머니와 함께 했던 봄철 추억이 있나요?",
            ...         "response_latency": 3.5
            ...     }
            ... )
            >>> print(result["mcdi_score"])
            78.85

        Note:
            - RT 분석은 response_latency가 필수
            - 다른 지표는 관련 컨텍스트가 없어도 동작
            - 최소 3개 지표 성공 필요 (MCDI 계산용)
        """
        logger.info(
            f"Starting comprehensive analysis",
            extra={
                "message_length": len(message),
                "message_type": message_type,
                "has_memory": bool(memory)
            }
        )

        if not message or not message.strip():
            raise AnalysisError("Message cannot be empty")

        # 메모리가 없으면 빈 딕셔너리
        memory = memory or {}

        try:
            # ============================================
            # 1. 6개 지표 병렬 실행
            # ============================================
            logger.debug("Running 6 indicators in parallel...")

            results = await asyncio.gather(
                # LR: Lexical Richness
                self._run_lr(message),

                # SD: Semantic Drift
                self._run_sd(message, memory),

                # NC: Narrative Coherence
                self._run_nc(message, memory),

                # TO: Temporal Orientation
                self._run_to(message, memory),

                # ER: Episodic Recall
                self._run_er(message, memory),

                # RT: Response Time
                self._run_rt(message, memory),

                return_exceptions=True  # 일부 실패해도 계속 진행
            )

            # 결과 언팩
            lr_result, sd_result, nc_result, to_result, er_result, rt_result = results

            # ============================================
            # 2. 에러 핸들링 & 점수 집계
            # ============================================
            scores = {}
            details = {}
            failed_metrics = []

            # 각 지표 처리
            indicators = [
                ("LR", lr_result),
                ("SD", sd_result),
                ("NC", nc_result),
                ("TO", to_result),
                ("ER", er_result),
                ("RT", rt_result)
            ]

            for name, result in indicators:
                if isinstance(result, Exception):
                    logger.error(f"{name} analysis failed: {result}")
                    scores[name] = None
                    details[f"{name.lower()}_detail"] = {
                        "error": str(result),
                        "score": None
                    }
                    failed_metrics.append(name)
                else:
                    scores[name] = result["score"]
                    details[f"{name.lower()}_detail"] = result

            # ============================================
            # 3. 유효 지표 확인
            # ============================================
            valid_scores = {k: v for k, v in scores.items() if v is not None}

            if len(valid_scores) == 0:
                logger.error("All analysis metrics failed")
                raise AnalysisError("All 6 analysis metrics failed")

            logger.info(
                f"Analysis metrics completed: {len(valid_scores)}/6 successful",
                extra={"valid_metrics": list(valid_scores.keys())}
            )

            # ============================================
            # 4. MCDI 계산
            # ============================================
            try:
                mcdi_details = self.mcdi.calculate_with_confidence(valid_scores)
                mcdi_score = mcdi_details["mcdi_score"]

                logger.info(
                    f"MCDI calculated: {mcdi_score}",
                    extra={
                        "mcdi_score": mcdi_score,
                        "reliability": mcdi_details["reliability"],
                        "risk_category": mcdi_details["risk_category"]
                    }
                )

            except Exception as e:
                logger.error(f"MCDI calculation failed: {e}", exc_info=True)
                raise AnalysisError(f"MCDI calculation failed: {e}") from e

            # ============================================
            # 5. 모순 탐지 (선택적)
            # ============================================
            contradictions = []
            if memory.get("biographical") or memory.get("previous_statements"):
                try:
                    contradictions = await self.contradiction.detect(
                        user_id=memory.get("user_id"),
                        new_statement=message,
                        biographical_memory=memory.get("biographical"),
                        previous_statements=memory.get("previous_statements")
                    )
                except Exception as e:
                    logger.warning(f"Contradiction detection failed: {e}")
                    # 실패해도 계속 진행

            # ============================================
            # 6. 종합 결과 반환
            # ============================================
            return {
                # 점수
                "scores": scores,
                "mcdi_score": mcdi_score,
                "mcdi_details": mcdi_details,

                # 세부 정보
                **details,

                # 모순 탐지
                "contradictions": contradictions,

                # 메타데이터
                "failed_metrics": failed_metrics,
                "message_type": message_type,
                "timestamp": datetime.now().isoformat()
            }

        except AnalysisError:
            # 이미 처리된 에러는 그대로 전달
            raise

        except Exception as e:
            logger.error(f"Comprehensive analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Analysis failed: {e}") from e

    # ============================================
    # 개별 지표 실행 메서드 (에러 격리)
    # ============================================

    async def _run_lr(self, message: str) -> Dict[str, Any]:
        """
        LR (Lexical Richness) 분석 실행

        Args:
            message: 사용자 메시지

        Returns:
            LR 분석 결과

        Raises:
            Exception: 분석 실패 시
        """
        try:
            logger.debug("Running LR analysis...")
            result = await self.lr.analyze(message)
            logger.debug(f"LR analysis completed: {result['score']:.2f}")
            return result
        except Exception as e:
            logger.error(f"LR analysis failed: {e}", exc_info=True)
            raise

    async def _run_sd(
        self,
        message: str,
        memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        SD (Semantic Drift) 분석 실행

        Args:
            message: 사용자 메시지
            memory: 메모리 데이터 (question 포함)

        Returns:
            SD 분석 결과

        Raises:
            Exception: 분석 실패 시
        """
        try:
            logger.debug("Running SD analysis...")

            # 컨텍스트 준비
            context = {
                "question": memory.get("question", ""),
                "previous_messages": memory.get("previous_messages", [])
            }

            result = await self.sd.analyze(message, context)
            logger.debug(f"SD analysis completed: {result['score']:.2f}")
            return result

        except Exception as e:
            logger.error(f"SD analysis failed: {e}", exc_info=True)
            raise

    async def _run_nc(
        self,
        message: str,
        memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        NC (Narrative Coherence) 분석 실행

        Args:
            message: 사용자 메시지
            memory: 메모리 데이터

        Returns:
            NC 분석 결과

        Raises:
            Exception: 분석 실패 시
        """
        try:
            logger.debug("Running NC analysis...")

            # 컨텍스트 준비 (선택적)
            context = {
                "question_type": memory.get("question_type")
            }

            result = await self.nc.analyze(message, context)
            logger.debug(f"NC analysis completed: {result['score']:.2f}")
            return result

        except Exception as e:
            logger.error(f"NC analysis failed: {e}", exc_info=True)
            raise

    async def _run_to(
        self,
        message: str,
        memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        TO (Temporal Orientation) 분석 실행

        Args:
            message: 사용자 메시지
            memory: 메모리 데이터 (current_datetime 포함)

        Returns:
            TO 분석 결과

        Raises:
            Exception: 분석 실패 시
        """
        try:
            logger.debug("Running TO analysis...")

            # 컨텍스트 준비
            context = {
                "current_datetime": memory.get("current_datetime")
            }

            result = await self.to.analyze(message, context)
            logger.debug(f"TO analysis completed: {result['score']:.2f}")
            return result

        except Exception as e:
            logger.error(f"TO analysis failed: {e}", exc_info=True)
            raise

    async def _run_er(
        self,
        message: str,
        memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ER (Episodic Recall) 분석 실행

        Args:
            message: 사용자 메시지
            memory: 메모리 데이터 (episodic, biographical 포함)

        Returns:
            ER 분석 결과

        Raises:
            Exception: 분석 실패 시
        """
        try:
            logger.debug("Running ER analysis...")

            # 컨텍스트 준비
            context = {
                "episodic": memory.get("episodic", []),
                "biographical": memory.get("biographical", {}),
                "previous_statements": memory.get("previous_statements", [])
            }

            result = await self.er.analyze(message, context)
            logger.debug(f"ER analysis completed: {result['score']:.2f}")
            return result

        except Exception as e:
            logger.error(f"ER analysis failed: {e}", exc_info=True)
            raise

    async def _run_rt(
        self,
        message: str,
        memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        RT (Response Time) 분석 실행

        Args:
            message: 사용자 메시지
            memory: 메모리 데이터 (response_latency 필수)

        Returns:
            RT 분석 결과

        Raises:
            Exception: 분석 실패 시 (response_latency 없으면 실패)
        """
        try:
            logger.debug("Running RT analysis...")

            # 컨텍스트 준비 (response_latency 필수)
            if "response_latency" not in memory:
                raise ValueError("response_latency is required for RT analysis")

            context = {
                "response_latency": memory["response_latency"],
                "typing_pauses": memory.get("typing_pauses", []),
                "historical_latencies": memory.get("historical_latencies", [])
            }

            result = await self.rt.analyze(message, context)
            logger.debug(f"RT analysis completed: {result['score']:.2f}")
            return result

        except Exception as e:
            logger.error(f"RT analysis failed: {e}", exc_info=True)
            raise

    # ============================================
    # 유틸리티 메서드
    # ============================================

    def get_indicator_names(self) -> list:
        """
        모든 지표 이름 리스트 반환

        Returns:
            지표 이름 리스트 ["LR", "SD", "NC", "TO", "ER", "RT"]
        """
        return self.mcdi.get_metric_names()

    def get_weights(self) -> Dict[str, float]:
        """
        각 지표의 가중치 반환

        Returns:
            가중치 딕셔너리
        """
        return self.mcdi.get_weights()
