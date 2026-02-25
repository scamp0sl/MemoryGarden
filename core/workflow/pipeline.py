"""
처리 파이프라인 기본 클래스

단계별 실행, 에러 핸들링, 로깅을 제공하는 파이프라인 프레임워크.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Type
from datetime import datetime
from enum import Enum
import asyncio
import time

# ============================================
# 2. Third-Party Imports
# ============================================
from pydantic import BaseModel, Field

# ============================================
# 3. Local Imports
# ============================================
from utils.logger import get_logger
from utils.exceptions import MemoryGardenError

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의
# ============================================
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
DEFAULT_TIMEOUT = 30.0  # seconds


# ============================================
# 6. Enum 정의
# ============================================
class StepStatus(str, Enum):
    """단계 실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """파이프라인 실행 상태"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================
# 7. Pydantic 모델
# ============================================
class StepResult(BaseModel):
    """단계 실행 결과"""
    step_name: str
    status: StepStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PipelineResult(BaseModel):
    """파이프라인 실행 결과"""
    pipeline_name: str
    status: PipelineStatus
    step_results: List[StepResult] = Field(default_factory=list)
    total_execution_time_ms: float = 0.0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PipelineContext(BaseModel):
    """파이프라인 실행 컨텍스트

    단계 간 데이터를 공유하는 컨텍스트 객체.
    각 단계는 컨텍스트를 읽고 쓸 수 있음.
    """
    pipeline_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    def set(self, key: str, value: Any) -> None:
        """컨텍스트에 값 저장"""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """컨텍스트에서 값 조회"""
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return key in self.data

    def set_metadata(self, key: str, value: Any) -> None:
        """메타데이터 저장"""
        self.metadata[key] = value

    class Config:
        arbitrary_types_allowed = True


# ============================================
# 8. Step 기본 클래스
# ============================================
class Step(ABC):
    """파이프라인 단계 추상 클래스

    각 처리 단계는 이 클래스를 상속하여 구현.

    Attributes:
        name: 단계 이름
        retries: 재시도 횟수
        timeout: 타임아웃 (초)
        skip_on_error: 에러 시 건너뛸지 여부

    Example:
        >>> class MyStep(Step):
        ...     async def execute(self, context: PipelineContext) -> Dict[str, Any]:
        ...         # 로직 구현
        ...         return {"result": "success"}
    """

    def __init__(
        self,
        name: str,
        retries: int = MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
        skip_on_error: bool = False
    ):
        """
        Step 초기화

        Args:
            name: 단계 이름
            retries: 재시도 횟수 (기본 3회)
            timeout: 타임아웃 (초, 기본 30초)
            skip_on_error: 에러 시 건너뛸지 여부
        """
        self.name = name
        self.retries = retries
        self.timeout = timeout
        self.skip_on_error = skip_on_error

    @abstractmethod
    async def execute(self, context: PipelineContext) -> Dict[str, Any]:
        """
        단계 실행 (하위 클래스에서 구현)

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            실행 결과 딕셔너리

        Raises:
            Exception: 실행 중 에러 발생 시
        """
        pass

    async def validate(self, context: PipelineContext) -> bool:
        """
        실행 전 검증 (선택적 오버라이드)

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            검증 성공 여부
        """
        return True

    async def on_success(self, context: PipelineContext, result: Dict[str, Any]) -> None:
        """
        성공 시 후처리 (선택적 오버라이드)

        Args:
            context: 파이프라인 컨텍스트
            result: 실행 결과
        """
        pass

    async def on_failure(self, context: PipelineContext, error: Exception) -> None:
        """
        실패 시 후처리 (선택적 오버라이드)

        Args:
            context: 파이프라인 컨텍스트
            error: 발생한 에러
        """
        pass


# ============================================
# 9. Pipeline 기본 클래스
# ============================================
class Pipeline(ABC):
    """파이프라인 추상 클래스

    여러 단계를 순차적으로 실행하는 파이프라인.

    Attributes:
        name: 파이프라인 이름
        steps: 실행할 단계 리스트

    Example:
        >>> class MyPipeline(Pipeline):
        ...     def __init__(self):
        ...         super().__init__("my_pipeline")
        ...         self.add_step(Step1())
        ...         self.add_step(Step2())
        ...
        >>> pipeline = MyPipeline()
        >>> result = await pipeline.run(context)
    """

    def __init__(self, name: str):
        """
        Pipeline 초기화

        Args:
            name: 파이프라인 이름
        """
        self.name = name
        self.steps: List[Step] = []

    def add_step(self, step: Step) -> None:
        """
        단계 추가

        Args:
            step: 추가할 단계
        """
        self.steps.append(step)
        logger.debug(f"Step '{step.name}' added to pipeline '{self.name}'")

    def add_steps(self, steps: List[Step]) -> None:
        """
        여러 단계 추가

        Args:
            steps: 추가할 단계 리스트
        """
        for step in steps:
            self.add_step(step)

    async def run(self, context: PipelineContext) -> PipelineResult:
        """
        파이프라인 실행

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            파이프라인 실행 결과

        Example:
            >>> context = PipelineContext(
            ...     pipeline_id="session_123",
            ...     data={"user_id": "user123"}
            ... )
            >>> result = await pipeline.run(context)
        """
        logger.info(f"Starting pipeline '{self.name}'")
        started_at = datetime.now()
        start_time = time.time()

        result = PipelineResult(
            pipeline_name=self.name,
            status=PipelineStatus.RUNNING,
            started_at=started_at
        )

        try:
            # 각 단계 순차 실행
            for step in self.steps:
                step_result = await self._execute_step(step, context)
                result.step_results.append(step_result)

                # 단계 실패 시 처리
                if step_result.status == StepStatus.FAILED:
                    if not step.skip_on_error:
                        logger.error(
                            f"Step '{step.name}' failed, stopping pipeline",
                            extra={"error": step_result.error}
                        )
                        result.status = PipelineStatus.FAILED
                        result.error = f"Step '{step.name}' failed: {step_result.error}"
                        break
                    else:
                        logger.warning(
                            f"Step '{step.name}' failed but skipped",
                            extra={"error": step_result.error}
                        )

            # 모든 단계 완료
            if result.status == PipelineStatus.RUNNING:
                result.status = PipelineStatus.COMPLETED
                logger.info(f"Pipeline '{self.name}' completed successfully")

        except Exception as e:
            logger.error(
                f"Pipeline '{self.name}' failed with unexpected error: {e}",
                exc_info=True
            )
            result.status = PipelineStatus.FAILED
            result.error = str(e)

        finally:
            result.completed_at = datetime.now()
            result.total_execution_time_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Pipeline '{self.name}' finished",
                extra={
                    "status": result.status.value,
                    "total_time_ms": result.total_execution_time_ms,
                    "steps_completed": sum(
                        1 for sr in result.step_results
                        if sr.status == StepStatus.COMPLETED
                    ),
                    "steps_failed": sum(
                        1 for sr in result.step_results
                        if sr.status == StepStatus.FAILED
                    )
                }
            )

        return result

    async def _execute_step(
        self,
        step: Step,
        context: PipelineContext
    ) -> StepResult:
        """
        단계 실행 (내부 메서드)

        재시도, 타임아웃, 에러 핸들링 포함.

        Args:
            step: 실행할 단계
            context: 파이프라인 컨텍스트

        Returns:
            단계 실행 결과
        """
        logger.info(f"Executing step '{step.name}'")
        start_time = time.time()

        step_result = StepResult(
            step_name=step.name,
            status=StepStatus.RUNNING
        )

        # 검증
        try:
            if not await step.validate(context):
                logger.warning(f"Step '{step.name}' validation failed, skipping")
                step_result.status = StepStatus.SKIPPED
                step_result.execution_time_ms = (time.time() - start_time) * 1000
                return step_result
        except Exception as e:
            logger.error(f"Step '{step.name}' validation error: {e}")
            step_result.status = StepStatus.FAILED
            step_result.error = f"Validation error: {str(e)}"
            step_result.execution_time_ms = (time.time() - start_time) * 1000
            return step_result

        # 재시도 루프
        last_error = None
        for attempt in range(step.retries + 1):
            try:
                # 타임아웃과 함께 실행
                output = await asyncio.wait_for(
                    step.execute(context),
                    timeout=step.timeout
                )

                # 성공
                step_result.status = StepStatus.COMPLETED
                step_result.output = output
                step_result.retry_count = attempt
                step_result.execution_time_ms = (time.time() - start_time) * 1000

                # 성공 후처리
                await step.on_success(context, output)

                logger.info(
                    f"Step '{step.name}' completed successfully",
                    extra={
                        "execution_time_ms": step_result.execution_time_ms,
                        "retry_count": attempt
                    }
                )

                return step_result

            except asyncio.TimeoutError:
                last_error = Exception(f"Step timed out after {step.timeout}s")
                logger.warning(
                    f"Step '{step.name}' timed out (attempt {attempt + 1}/{step.retries + 1})"
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Step '{step.name}' failed (attempt {attempt + 1}/{step.retries + 1}): {e}"
                )

            # 재시도 전 대기
            if attempt < step.retries:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))  # 지수 백오프

        # 모든 재시도 실패
        step_result.status = StepStatus.FAILED
        step_result.error = str(last_error)
        step_result.retry_count = step.retries
        step_result.execution_time_ms = (time.time() - start_time) * 1000

        # 실패 후처리
        await step.on_failure(context, last_error)

        logger.error(
            f"Step '{step.name}' failed after {step.retries + 1} attempts",
            extra={"error": str(last_error)}
        )

        return step_result


# ============================================
# 10. 유틸리티 함수
# ============================================
def create_context(pipeline_id: str, initial_data: Optional[Dict[str, Any]] = None) -> PipelineContext:
    """
    파이프라인 컨텍스트 생성 헬퍼

    Args:
        pipeline_id: 파이프라인 ID
        initial_data: 초기 데이터

    Returns:
        생성된 컨텍스트

    Example:
        >>> context = create_context("session_123", {"user_id": "user123"})
    """
    return PipelineContext(
        pipeline_id=pipeline_id,
        data=initial_data or {}
    )


# ============================================
# 11. Export
# ============================================
__all__ = [
    "Step",
    "Pipeline",
    "PipelineContext",
    "PipelineResult",
    "StepResult",
    "StepStatus",
    "PipelineStatus",
    "create_context",
]

logger.info("Pipeline module loaded")
