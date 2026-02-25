"""
모순 탐지기 (Contradiction Detector)

사용자의 현재 발언과 과거 기록을 비교하여 모순을 탐지합니다.
일화 기억(ER) 지표의 일부로 사용됩니다.

Scientific Basis:
    - Taler & Phillips (2008): 치매 환자의 일관성 없는 진술 증가
    - 의미적 모순: 임베딩 유사도 + LLM 판단
    - 시간적 모순: 날짜/시간 순서 불일치
    - 논리적 모순: 인과관계 오류

Detection Methods:
    1. Semantic Contradiction (의미적 모순):
       - 임베딩 코사인 유사도로 유사한 진술 검색
       - LLM으로 모순 여부 판단

    2. Temporal Contradiction (시간적 모순):
       - 과거 사건의 날짜/시간 불일치
       - 인생 사건의 순서 오류

    3. Factual Contradiction (사실적 모순):
       - 이름, 장소, 수치 등 사실 정보 불일치

Output Format:
    [
        {
            "type": "semantic" | "temporal" | "factual",
            "severity": "high" | "medium" | "low",
            "current_statement": "현재 발언",
            "contradicting_statement": "모순되는 과거 발언",
            "explanation": "모순 설명"
        }
    ]

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

# ============================================
# 2. Third-Party Imports
# ============================================
import numpy as np

# ============================================
# 3. Local Imports
# ============================================
from services.llm_service import LLMService
from core.nlp.embedder import Embedder
from utils.logger import get_logger
from utils.exceptions import AnalysisError

# ============================================
# 4. Logger Setup
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. Constants
# ============================================
SIMILARITY_THRESHOLD = 0.75  # 유사도 임계값 (0-1)
MIN_CONTRADICTION_CONFIDENCE = 0.6  # 최소 신뢰도


# ============================================
# 6. ContradictionDetector Class
# ============================================
class ContradictionDetector:
    """
    모순 탐지기

    현재 발언과 과거 기록을 비교하여 의미적, 시간적, 사실적 모순 탐지.

    Attributes:
        llm: LLM 서비스 (모순 판단)
        embedder: 임베딩 생성기 (유사 진술 검색)

    Example:
        >>> detector = ContradictionDetector(llm_service, embedder)
        >>> contradictions = await detector.detect(
        ...     user_id="user_123",
        ...     new_statement="아버지는 의사셨어요",
        ...     biographical_memory=[
        ...         {"content": "아버지는 선생님이셨어요", "timestamp": "2025-01-01"}
        ...     ]
        ... )
        >>> print(len(contradictions))
        1
    """

    def __init__(self, llm_service: LLMService, embedder: Embedder):
        """
        초기화

        Args:
            llm_service: LLM 서비스
            embedder: 임베딩 생성기
        """
        self.llm = llm_service
        self.embedder = embedder

        logger.info("ContradictionDetector initialized")

    async def detect(
        self,
        user_id: str,
        new_statement: str,
        biographical_memory: Optional[List[Dict[str, Any]]] = None,
        previous_statements: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        모순 탐지

        Args:
            user_id: 사용자 ID
            new_statement: 현재 발언
            biographical_memory: 전기적 메모리 (장기 사실)
            previous_statements: 최근 발언 기록

        Returns:
            모순 리스트 [{"type": "semantic", "severity": "high", ...}]

        Example:
            >>> contradictions = await detector.detect(
            ...     user_id="user_123",
            ...     new_statement="저는 서울에서 태어났어요",
            ...     biographical_memory=[
            ...         {"content": "부산에서 태어났어요", "timestamp": "2025-01-01"}
            ...     ]
            ... )
        """
        if not new_statement or not new_statement.strip():
            logger.warning("Empty statement, skipping contradiction detection")
            return []

        logger.info(
            f"Detecting contradictions",
            extra={"user_id": user_id, "statement_length": len(new_statement)}
        )

        contradictions = []

        try:
            # 1. 전기적 메모리와 비교
            if biographical_memory:
                bio_contradictions = await self._check_biographical_contradictions(
                    new_statement, biographical_memory
                )
                contradictions.extend(bio_contradictions)

            # 2. 최근 발언과 비교
            if previous_statements:
                recent_contradictions = await self._check_recent_contradictions(
                    new_statement, previous_statements
                )
                contradictions.extend(recent_contradictions)

            # 중복 제거 (같은 과거 발언과의 모순은 1번만)
            contradictions = self._deduplicate_contradictions(contradictions)

            logger.info(
                f"Contradiction detection completed",
                extra={
                    "user_id": user_id,
                    "contradictions_found": len(contradictions)
                }
            )

            return contradictions

        except Exception as e:
            logger.error(
                f"Contradiction detection failed: {e}",
                exc_info=True
            )
            # 실패해도 빈 리스트 반환 (다른 분석은 계속 진행)
            return []

    async def _check_biographical_contradictions(
        self,
        new_statement: str,
        biographical_memory: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        전기적 메모리와의 모순 체크

        Args:
            new_statement: 현재 발언
            biographical_memory: 전기적 메모리 리스트

        Returns:
            모순 리스트
        """
        contradictions = []

        # 현재 발언 임베딩
        new_embedding = await self.embedder.embed(new_statement)

        # 유사한 과거 진술 찾기
        for memory in biographical_memory[:20]:  # 최대 20개만 체크
            past_statement = memory.get("content", "")
            if not past_statement:
                continue

            # 임베딩 유사도 계산
            past_embedding = await self.embedder.embed(past_statement)
            similarity = self.embedder.calculate_similarity(
                new_embedding, past_embedding
            )

            # 유사도가 높으면 (같은 주제에 대한 발언) 모순 여부 확인
            if similarity >= SIMILARITY_THRESHOLD:
                contradiction = await self._detect_semantic_contradiction(
                    new_statement=new_statement,
                    past_statement=past_statement,
                    similarity=similarity,
                    timestamp=memory.get("timestamp")
                )

                if contradiction:
                    contradictions.append(contradiction)

        return contradictions

    async def _check_recent_contradictions(
        self,
        new_statement: str,
        previous_statements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        최근 발언과의 모순 체크

        Args:
            new_statement: 현재 발언
            previous_statements: 최근 발언 리스트

        Returns:
            모순 리스트
        """
        contradictions = []

        # 현재 발언 임베딩
        new_embedding = await self.embedder.embed(new_statement)

        # 최근 10개 발언과 비교
        for statement in previous_statements[:10]:
            past_text = statement.get("content", "")
            if not past_text:
                continue

            # 임베딩 유사도
            past_embedding = await self.embedder.embed(past_text)
            similarity = self.embedder.calculate_similarity(
                new_embedding, past_embedding
            )

            # 유사도가 높으면 모순 체크
            if similarity >= SIMILARITY_THRESHOLD:
                contradiction = await self._detect_semantic_contradiction(
                    new_statement=new_statement,
                    past_statement=past_text,
                    similarity=similarity,
                    timestamp=statement.get("timestamp")
                )

                if contradiction:
                    contradictions.append(contradiction)

        return contradictions

    async def _detect_semantic_contradiction(
        self,
        new_statement: str,
        past_statement: str,
        similarity: float,
        timestamp: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        LLM을 사용한 의미적 모순 탐지

        Args:
            new_statement: 현재 발언
            past_statement: 과거 발언
            similarity: 임베딩 유사도
            timestamp: 과거 발언 시간

        Returns:
            모순 정보 또는 None (모순 없음)
        """
        prompt = f"""
다음 두 발언이 서로 모순되는지 판단하세요.

현재 발언: {new_statement}
과거 발언: {past_statement}

모순 판단 기준:
- 같은 주제에 대해 정반대 내용이면 모순
- 사실 정보(이름, 장소, 직업 등)가 다르면 모순
- 단순히 다른 이야기를 하는 것은 모순 아님

다음 형식으로 JSON 응답하세요:
{{
    "is_contradiction": true/false,
    "confidence": 0.0-1.0,
    "type": "semantic" | "factual" | "temporal",
    "severity": "high" | "medium" | "low",
    "explanation": "모순 설명"
}}
"""

        try:
            response = await self.llm.call(prompt, max_tokens=300)

            # JSON 파싱
            import json
            result = json.loads(response.strip())

            # 모순이 아니거나 신뢰도가 낮으면 None 반환
            if not result.get("is_contradiction"):
                return None

            confidence = result.get("confidence", 0.0)
            if confidence < MIN_CONTRADICTION_CONFIDENCE:
                return None

            # 모순 정보 반환
            return {
                "type": result.get("type", "semantic"),
                "severity": result.get("severity", "medium"),
                "confidence": confidence,
                "similarity": similarity,
                "current_statement": new_statement,
                "contradicting_statement": past_statement,
                "past_timestamp": timestamp,
                "explanation": result.get("explanation", "내용이 모순됩니다")
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return None
        except Exception as e:
            logger.error(f"Semantic contradiction detection failed: {e}")
            return None

    def _deduplicate_contradictions(
        self,
        contradictions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        중복 모순 제거

        같은 과거 발언과의 모순은 1개만 유지 (신뢰도 높은 것)

        Args:
            contradictions: 모순 리스트

        Returns:
            중복 제거된 리스트
        """
        if not contradictions:
            return []

        # 과거 발언 기준으로 그룹화
        grouped = {}
        for contradiction in contradictions:
            past_stmt = contradiction.get("contradicting_statement")
            confidence = contradiction.get("confidence", 0.0)

            if past_stmt not in grouped:
                grouped[past_stmt] = contradiction
            else:
                # 신뢰도 높은 것으로 교체
                if confidence > grouped[past_stmt].get("confidence", 0.0):
                    grouped[past_stmt] = contradiction

        # 신뢰도 순으로 정렬
        deduplicated = sorted(
            grouped.values(),
            key=lambda x: x.get("confidence", 0.0),
            reverse=True
        )

        return deduplicated
