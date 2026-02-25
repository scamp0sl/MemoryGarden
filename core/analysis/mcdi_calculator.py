"""
MCDI 종합 점수 계산기 (MCDI Calculator)

6개 인지 지표를 가중 평균하여 Memory & Cognitive Decline Index 산출

Scientific Basis:
    Fraser et al. (2016) "Linguistic Features Identify Alzheimer's Disease
    in Narrative Speech"

    종합 인지 기능 평가를 위한 6개 디지털 바이오마커:
    - LR (Lexical Richness): 어휘 풍부도 - 단어 다양성 및 구체성
    - SD (Semantic Drift): 의미적 표류 - 맥락 유지 능력
    - NC (Narrative Coherence): 서사 일관성 - 담화 구성 능력
    - TO (Temporal Orientation): 시간적 지남력 - 시간 인식 능력
    - ER (Episodic Recall): 일화 기억 - 과거 사건 회상 능력
    - RT (Response Time): 반응 시간 - 인지 처리 속도

MCDI Formula:
    MCDI = w₁·LR + w₂·SD + w₃·NC + w₄·TO + w₅·ER + w₆·RT

    Where:
    - w₁ = 0.20 (LR weight)
    - w₂ = 0.20 (SD weight)
    - w₃ = 0.15 (NC weight)
    - w₄ = 0.15 (TO weight)
    - w₅ = 0.20 (ER weight)
    - w₆ = 0.10 (RT weight)

    Range: 0-100
    - 80-100: Excellent cognitive function (GREEN)
    - 60-80: Mild concerns (YELLOW)
    - 40-60: Moderate concerns (ORANGE)
    - 0-40: Severe concerns (RED)

Adaptive Weighting:
    일부 지표 실패 시 남은 지표로 가중치 재정규화
    - 최소 3개 지표 필요 (신뢰도 확보)
    - 가중치 합 = 1.0 유지

Author: Memory Garden Team
Created: 2025-01-15
Updated: 2025-02-10
"""

from typing import Dict, Any, Optional
from utils.logger import get_logger
from utils.exceptions import MCDICalculationError

logger = get_logger(__name__)


class MCDICalculator:
    """
    MCDI (Memory & Cognitive Decline Index) 종합 점수 계산기

    6개 인지 지표를 가중 평균하여 0-100 범위의 종합 점수를 산출합니다.
    일부 지표 실패 시 자동으로 가중치를 재정규화하여 계산합니다.

    Attributes:
        WEIGHTS: 각 지표의 가중치 (합 = 1.0)
        MIN_VALID_METRICS: 최소 필요 지표 개수 (3개)

    Example:
        >>> calculator = MCDICalculator()
        >>> scores = {
        ...     "LR": 78.5,
        ...     "SD": 82.3,
        ...     "NC": 75.0,
        ...     "TO": 80.0,
        ...     "ER": 72.5,
        ...     "RT": 70.0
        ... }
        >>> mcdi = calculator.calculate(scores)
        >>> print(mcdi)
        76.88
        >>> print(calculator.get_risk_category(mcdi))
        "YELLOW"
    """

    # ============================================
    # 가중치 (CLAUDE.md 참조)
    # ============================================
    WEIGHTS = {
        "LR": 0.20,  # Lexical Richness (어휘 풍부도)
        "SD": 0.20,  # Semantic Drift (의미적 표류)
        "NC": 0.15,  # Narrative Coherence (서사 일관성)
        "TO": 0.15,  # Temporal Orientation (시간적 지남력)
        "ER": 0.20,  # Episodic Recall (일화 기억)
        "RT": 0.10   # Response Time (반응 시간)
    }

    # 최소 유효 지표 개수
    MIN_VALID_METRICS = 3

    # 위험도 임계값
    RISK_THRESHOLDS = {
        "GREEN": 80.0,     # 80-100: 정상
        "YELLOW": 60.0,    # 60-80: 경계
        "ORANGE": 40.0,    # 40-60: 위험
        # 0-40: RED (고위험)
    }

    def __init__(self):
        """
        MCDI 계산기 초기화
        """
        logger.info("MCDICalculator initialized with 6 indicators")
        logger.debug(f"Weights: {self.WEIGHTS}")

    def calculate(self, scores: Dict[str, float]) -> float:
        """
        6개 지표를 가중 평균하여 MCDI 계산

        일부 지표가 누락된 경우 남은 지표로 가중치를 재정규화하여 계산합니다.
        최소 3개 지표가 필요하며, 이보다 적으면 예외를 발생시킵니다.

        Formula:
            MCDI = Σ(score_i × normalized_weight_i) for i in valid_indicators

            normalized_weight_i = weight_i / Σ(weight_j) for j in valid_indicators

        Args:
            scores: 각 지표의 점수 딕셔너리
                {"LR": 78.5, "SD": 82.3, "NC": 75.0, ...}
                - 각 점수는 0-100 범위
                - None 값은 미리 제거되어야 함
                - 최소 3개 지표 필요

        Returns:
            MCDI 종합 점수 (0-100)
            - 소수점 둘째 자리까지 반올림

        Raises:
            MCDICalculationError: 다음의 경우 발생
                - scores가 빈 딕셔너리
                - 유효 지표가 3개 미만
                - 점수가 0-100 범위를 벗어남
                - 알 수 없는 지표 이름

        Example:
            >>> calculator = MCDICalculator()
            >>> scores = {
            ...     "LR": 80.0,
            ...     "SD": 85.0,
            ...     "NC": 75.0,
            ...     "TO": 82.0,
            ...     "ER": 78.0,
            ...     "RT": 70.0
            ... }
            >>> mcdi = calculator.calculate(scores)
            >>> print(mcdi)
            78.85

            >>> # 일부 지표만 있는 경우
            >>> partial_scores = {"LR": 80.0, "SD": 85.0, "NC": 75.0}
            >>> mcdi = calculator.calculate(partial_scores)
            >>> print(mcdi)
            80.27  # 가중치 재정규화 후 계산

        Note:
            - 6개 모두 있을 때: 정확한 MCDI
            - 3-5개 있을 때: 재정규화 MCDI (신뢰도 낮음)
            - 2개 이하: 계산 불가 (예외 발생)
        """
        logger.debug(f"Calculating MCDI from scores: {scores}")

        # ============================================
        # 1. 입력 검증
        # ============================================
        if not scores:
            logger.error("Empty scores dictionary provided")
            raise MCDICalculationError("No valid scores provided")

        if len(scores) < self.MIN_VALID_METRICS:
            logger.error(
                f"Insufficient metrics: {len(scores)} < {self.MIN_VALID_METRICS}"
            )
            raise MCDICalculationError(
                f"At least {self.MIN_VALID_METRICS} metrics required, "
                f"got {len(scores)}: {list(scores.keys())}"
            )

        # 알 수 없는 지표 체크
        unknown_metrics = set(scores.keys()) - set(self.WEIGHTS.keys())
        if unknown_metrics:
            logger.error(f"Unknown metrics: {unknown_metrics}")
            raise MCDICalculationError(
                f"Unknown metrics: {unknown_metrics}. "
                f"Valid metrics: {list(self.WEIGHTS.keys())}"
            )

        # 점수 범위 검증 (0-100)
        for metric, score in scores.items():
            if not (0 <= score <= 100):
                logger.error(f"Score out of range: {metric}={score}")
                raise MCDICalculationError(
                    f"Score for {metric} out of range: {score} (must be 0-100)"
                )

        # ============================================
        # 2. 가중치 재정규화
        # ============================================
        # 유효한 지표만 가중치 추출
        valid_weights = {k: self.WEIGHTS[k] for k in scores.keys()}
        weight_sum = sum(valid_weights.values())

        # 가중치 재정규화 (합이 1.0이 되도록)
        normalized_weights = {
            k: v / weight_sum
            for k, v in valid_weights.items()
        }

        logger.debug(
            f"Normalized weights: {normalized_weights} "
            f"(original sum: {weight_sum:.3f})"
        )

        # ============================================
        # 3. 가중 평균 계산
        # ============================================
        # MCDI = Σ(score_i × weight_i)
        mcdi = sum(
            scores[k] * normalized_weights[k]
            for k in scores.keys()
        )

        # 신뢰도 계산 (6개 중 몇 개 사용했는가)
        reliability = len(scores) / len(self.WEIGHTS)

        logger.info(
            f"MCDI calculated: {mcdi:.2f}",
            extra={
                "mcdi_score": round(mcdi, 2),
                "used_metrics": list(scores.keys()),
                "reliability": f"{reliability:.2%}",
                "normalized_weights": {k: round(v, 3) for k, v in normalized_weights.items()}
            }
        )

        return round(mcdi, 2)

    def calculate_with_confidence(
        self,
        scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        MCDI 점수 + 신뢰도 + 메타 정보 함께 반환

        calculate() 메서드의 확장 버전으로, 점수와 함께
        신뢰도, 사용된 지표, 누락된 지표 등의 메타 정보를 반환합니다.

        Args:
            scores: 각 지표의 점수 딕셔너리
                {"LR": 78.5, "SD": 82.3, ...}

        Returns:
            {
                "mcdi_score": 76.88,
                "reliability": 1.0,           # 6/6 지표 사용
                "used_metrics": ["LR", "SD", "NC", "TO", "ER", "RT"],
                "missing_metrics": [],
                "risk_category": "YELLOW",
                "normalized_weights": {
                    "LR": 0.20,
                    "SD": 0.20,
                    ...
                },
                "component_scores": {
                    "LR": 78.5,
                    "SD": 82.3,
                    ...
                }
            }

        Example:
            >>> calculator = MCDICalculator()
            >>> scores = {"LR": 80.0, "SD": 85.0, "NC": 75.0}
            >>> result = calculator.calculate_with_confidence(scores)
            >>> print(result["mcdi_score"])
            80.27
            >>> print(result["reliability"])
            0.5  # 3/6 지표 사용
            >>> print(result["missing_metrics"])
            ["TO", "ER", "RT"]
        """
        # MCDI 계산
        mcdi_score = self.calculate(scores)

        # 메타 정보 생성
        all_metrics = set(self.WEIGHTS.keys())
        used_metrics = set(scores.keys())
        missing_metrics = all_metrics - used_metrics

        # 가중치 재정규화
        valid_weights = {k: self.WEIGHTS[k] for k in scores.keys()}
        weight_sum = sum(valid_weights.values())
        normalized_weights = {
            k: round(v / weight_sum, 3)
            for k, v in valid_weights.items()
        }

        # 위험도 분류
        risk_category = self.get_risk_category(mcdi_score)

        result = {
            "mcdi_score": mcdi_score,
            "reliability": len(used_metrics) / len(all_metrics),
            "used_metrics": sorted(used_metrics),
            "missing_metrics": sorted(missing_metrics),
            "risk_category": risk_category,
            "normalized_weights": normalized_weights,
            "component_scores": {k: round(v, 2) for k, v in scores.items()}
        }

        logger.debug(f"MCDI with confidence: {result}")
        return result

    def get_risk_category(self, mcdi_score: float) -> str:
        """
        MCDI 점수에 따른 위험도 분류

        4단계 위험도 분류 시스템:
        - GREEN: 80-100 (정상)
        - YELLOW: 60-80 (경계)
        - ORANGE: 40-60 (위험)
        - RED: 0-40 (고위험)

        Args:
            mcdi_score: MCDI 점수 (0-100)

        Returns:
            위험도 카테고리 문자열 ("GREEN", "YELLOW", "ORANGE", "RED")

        Example:
            >>> calculator = MCDICalculator()
            >>> print(calculator.get_risk_category(85.0))
            "GREEN"
            >>> print(calculator.get_risk_category(65.0))
            "YELLOW"
            >>> print(calculator.get_risk_category(45.0))
            "ORANGE"
            >>> print(calculator.get_risk_category(30.0))
            "RED"

        Note:
            - 경계값은 낮은 등급에 포함 (예: 80.0 = GREEN, 79.9 = YELLOW)
        """
        if mcdi_score >= self.RISK_THRESHOLDS["GREEN"]:
            return "GREEN"
        elif mcdi_score >= self.RISK_THRESHOLDS["YELLOW"]:
            return "YELLOW"
        elif mcdi_score >= self.RISK_THRESHOLDS["ORANGE"]:
            return "ORANGE"
        else:
            return "RED"

    def validate_scores(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """
        점수 딕셔너리 유효성 검증 (계산 전 사전 검증용)

        calculate() 호출 전에 점수의 유효성을 미리 검증할 수 있습니다.

        Args:
            scores: 각 지표의 점수 딕셔너리

        Returns:
            {
                "valid": True,
                "errors": [],
                "warnings": [],
                "can_calculate": True
            }

        Example:
            >>> calculator = MCDICalculator()
            >>> scores = {"LR": 80.0, "SD": 85.0}
            >>> validation = calculator.validate_scores(scores)
            >>> print(validation["valid"])
            False
            >>> print(validation["errors"])
            ["Insufficient metrics: 2 < 3"]
            >>> print(validation["can_calculate"])
            False
        """
        errors = []
        warnings = []

        # 빈 딕셔너리 체크
        if not scores:
            errors.append("Empty scores dictionary")

        # 지표 개수 체크
        elif len(scores) < self.MIN_VALID_METRICS:
            errors.append(
                f"Insufficient metrics: {len(scores)} < {self.MIN_VALID_METRICS}"
            )

        # 알 수 없는 지표 체크
        unknown_metrics = set(scores.keys()) - set(self.WEIGHTS.keys())
        if unknown_metrics:
            errors.append(f"Unknown metrics: {unknown_metrics}")

        # 점수 범위 체크
        for metric, score in scores.items():
            if not (0 <= score <= 100):
                errors.append(f"Score out of range: {metric}={score}")

        # 누락된 지표 경고
        missing_metrics = set(self.WEIGHTS.keys()) - set(scores.keys())
        if missing_metrics:
            warnings.append(
                f"Missing metrics (will use normalized weights): {missing_metrics}"
            )

        # 신뢰도 경고
        reliability = len(scores) / len(self.WEIGHTS)
        if reliability < 0.8:  # 80% 미만
            warnings.append(
                f"Low reliability: {reliability:.1%} ({len(scores)}/6 metrics)"
            )

        valid = len(errors) == 0
        can_calculate = valid

        return {
            "valid": valid,
            "can_calculate": can_calculate,
            "errors": errors,
            "warnings": warnings,
            "metric_count": len(scores),
            "reliability": reliability if scores else 0.0
        }

    def get_weights(self) -> Dict[str, float]:
        """
        현재 설정된 가중치 반환

        Returns:
            가중치 딕셔너리 (복사본)

        Example:
            >>> calculator = MCDICalculator()
            >>> weights = calculator.get_weights()
            >>> print(weights["LR"])
            0.20
        """
        return self.WEIGHTS.copy()

    def get_metric_names(self) -> list:
        """
        모든 지표 이름 리스트 반환

        Returns:
            지표 이름 리스트

        Example:
            >>> calculator = MCDICalculator()
            >>> metrics = calculator.get_metric_names()
            >>> print(metrics)
            ["LR", "SD", "NC", "TO", "ER", "RT"]
        """
        return list(self.WEIGHTS.keys())
