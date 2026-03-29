"""
기억 감쇠 (Memory Decay) 곡선 모듈

Ebbinghaus 망각 곡선 기반 기억 감쇠 가중치 계산.
오래된 기억일수록 점수 가중치를 감소시켜 최신성을 반영.

SPEC §2.5.2 기반:
- 1일: 100%, 3일: 80%, 7일: 60%, 14일: 40%, 30일: 20%
- 지수 감쇠 함수: weight = e^(-λt)

Author: Memory Garden Team
Created: 2026-03-26
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

# ============================================
# 2. Third-Party Imports
# ============================================
import math

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

# 감쇠 파라미터 (λ)
# weight = e^(-λ * days_ago)
# λ = 0.05 → 1일: 95%, 3일: 86%, 7일: 70%, 14일: 49%, 30일: 22%
DECAY_LAMBDA = 0.05

# 경과 일수별 목표 감쇠 가중치 (SPEC 기준)
TARGET_WEIGHTS = {
    1: 1.00,   # 1일: 100%
    3: 0.80,   # 3일: 80%
    7: 0.60,   # 7일: 60%
    14: 0.40,  # 14일: 40%
    30: 0.20,  # 30일: 20%
}

# 최소 가중치 (너무 오래된 기억도 최소한 반영)
MIN_WEIGHT = 0.1

# 최대 가중치 적용 기간 (일)
MAX_DECAY_DAYS = 90


# ============================================
# 6. MemoryDecay 클래스
# ============================================

class MemoryDecay:
    """
    기억 감쇠 계산기

    Ebbinghaus 망각 곡선을 기반으로 기억의 감쇠 가중치를 계산.

    Example:
        >>> decay = MemoryDecay()
        >>> weight = decay.get_decay_weight(days_ago=7)
        >>> print(weight)  # 0.70 (지수 감쇠)
    """

    def __init__(self, lambda_param: float = DECAY_LAMBDA):
        """
        MemoryDecay 초기화

        Args:
            lambda_param: 감쇠 파라미터 (기본값 0.05)
        """
        self.lambda_param = lambda_param

    def get_decay_weight(
        self,
        days_ago: float,
        method: str = "exponential"
    ) -> float:
        """
        경과 일수에 따른 감쇠 가중치 계산

        Args:
            days_ago: 경과 일수 (소수점 가능, 예: 0.5일 = 12시간)
            method: 계산 방식 ("exponential", "linear", "step")

        Returns:
            0.0 ~ 1.0 사이의 감쇠 가중치

        Example:
            >>> decay = MemoryDecay()
            >>> decay.get_decay_weight(1)  # 0.95
            >>> decay.get_decay_weight(7)  # 0.70
            >>> decay.get_decay_weight(30)  # 0.22
        """
        if days_ago < 0:
            days_ago = 0
        elif days_ago > MAX_DECAY_DAYS:
            days_ago = MAX_DECAY_DAYS

        if method == "exponential":
            # 지수 감쇠: weight = e^(-λt)
            weight = math.exp(-self.lambda_param * days_ago)
        elif method == "linear":
            # 선형 감쇠: weight = 1 - (t / MAX)
            weight = 1.0 - (days_ago / MAX_DECAY_DAYS)
        elif method == "step":
            # 계단형 감쇠 (SPEC 기준)
            weight = self._step_decay(days_ago)
        else:
            weight = 1.0

        # 최소 가중치 보장
        return max(MIN_WEIGHT, weight)

    def _step_decay(self, days_ago: float) -> float:
        """계단형 감쇠 (SPEC 목표값 기준)"""
        if days_ago <= 1:
            return TARGET_WEIGHTS[1]
        elif days_ago <= 3:
            return TARGET_WEIGHTS[3]
        elif days_ago <= 7:
            return TARGET_WEIGHTS[7]
        elif days_ago <= 14:
            return TARGET_WEIGHTS[14]
        elif days_ago <= 30:
            return TARGET_WEIGHTS[30]
        else:
            return MIN_WEIGHT

    def apply_decay_to_score(
        self,
        score: float,
        days_ago: float,
        method: str = "exponential"
    ) -> float:
        """
        점수에 감쇠 가중치 적용

        Args:
            score: 원래 점수 (0-100)
            days_ago: 경과 일수
            method: 감쇠 계산 방식

        Returns:
            감쇠 적용后的 점수

        Example:
            >>> decay = MemoryDecay()
            >>> decay.apply_decay_to_score(85.0, 7)  # 59.5 (70% 적용)
        """
        weight = self.get_decay_weight(days_ago, method)
        return score * weight

    def get_weighted_average(
        self,
        score_days_pairs: List[tuple[float, int]],
        method: str = "exponential"
    ) -> float:
        """
        감쇠 가중 평균 계산

        여러 점수와 경과 일수 쌍에서 가중 평균을 계산.

        Args:
            score_days_pairs: [(score1, days_ago1), (score2, days_ago2), ...]
            method: 감쇠 계산 방식

        Returns:
            가중 평균 점수

        Example:
            >>> decay = MemoryDecay()
            >>> pairs = [(80, 1), (75, 7), (70, 30)]
            >>> avg = decay.get_weighted_average(pairs)  # 최근 점수에 더 높은 가중치
        """
        if not score_days_pairs:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for score, days_ago in score_days_pairs:
            weight = self.get_decay_weight(days_ago, method)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0:
            return sum(score for score, _ in score_days_pairs) / len(score_days_pairs)

        return weighted_sum / total_weight

    def get_memory_freshness_score(
        self,
        memories: List[Dict],
        timestamp_key: str = "timestamp",
        method: str = "exponential"
    ) -> float:
        """
        기억 집합의 신선도 점수 계산

        여러 기억의 timestamp을 분석하여 전체적인 신선도를 계산.

        Args:
            memories: 기억 리스트
            timestamp_key: timestamp 키 이름
            method: 감쇠 계산 방식

        Returns:
            0.0 ~ 1.0 사이의 신선도 점수 (1.0 = 최신)

        Example:
            >>> decay = MemoryDecay()
            >>> memories = [
            ...     {"timestamp": "2026-03-26T10:00:00"},
            ...     {"timestamp": "2026-03-20T10:00:00"},
            ... ]
            >>> freshness = decay.get_memory_freshness_score(memories)
        """
        if not memories:
            return 0.0

        now = datetime.now()
        weights = []

        for memory in memories:
            try:
                timestamp_str = memory.get(timestamp_key, "")
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    timestamp = timestamp_str

                delta = now - timestamp
                days_ago = delta.total_seconds() / 86400

                weight = self.get_decay_weight(days_ago, method)
                weights.append(weight)
            except Exception as e:
                logger.warning(f"Failed to parse timestamp: {e}")
                weights.append(MIN_WEIGHT)

        # 평균 가중치 = 신선도
        return sum(weights) / len(weights) if weights else 0.0

    def filter_fresh_memories(
        self,
        memories: List[Dict],
        min_freshness: float = 0.5,
        timestamp_key: str = "timestamp",
        method: str = "exponential"
    ) -> List[Dict]:
        """
        신선도 기준으로 기억 필터링

        Args:
            memories: 기억 리스트
            min_freshness: 최소 신선도 (기본값 0.5 = 최소 50%)
            timestamp_key: timestamp 키 이름
            method: 감쇠 계산 방식

        Returns:
            신선도 기준을 통과한 기억 리스트

        Example:
            >>> decay = MemoryDecay()
            >>> fresh_memories = decay.filter_fresh_memories(all_memories, min_freshness=0.6)
        """
        now = datetime.now()
        filtered = []

        for memory in memories:
            try:
                timestamp_str = memory.get(timestamp_key, "")
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    timestamp = timestamp_str

                delta = now - timestamp
                days_ago = delta.total_seconds() / 86400

                weight = self.get_decay_weight(days_ago, method)

                if weight >= min_freshness:
                    # 가중치 메타데이터 추가
                    memory_copy = memory.copy()
                    memory_copy["_decay_weight"] = weight
                    memory_copy["_days_ago"] = days_ago
                    filtered.append(memory_copy)
            except Exception as e:
                logger.warning(f"Failed to filter memory: {e}")

        return filtered


# ============================================
# 7. 편의 함수
# ============================================

def calculate_decay_weight(days_ago: float, lambda_param: float = DECAY_LAMBDA) -> float:
    """
    간편한 감쇠 가중치 계산 함수

    Example:
        >>> calculate_decay_weight(7)  # 0.70
    """
    decay = MemoryDecay(lambda_param=lambda_param)
    return decay.get_decay_weight(days_ago)


def apply_decay_to_mcdi_score(
    score: float,
    days_ago: float,
    lambda_param: float = DECAY_LAMBDA
) -> float:
    """
    MCDI 점수에 감쇠 적용

    Example:
        >>> apply_decay_to_mcdi_score(85.0, 7)  # 59.5
    """
    decay = MemoryDecay(lambda_param=lambda_param)
    return decay.apply_decay_to_score(score, days_ago)


# ============================================
# 8. Export
# ============================================
__all__ = [
    "MemoryDecay",
    "calculate_decay_weight",
    "apply_decay_to_mcdi_score",
    "DECAY_LAMBDA",
    "TARGET_WEIGHTS",
    "MIN_WEIGHT",
]

logger.info("Memory decay module loaded")
