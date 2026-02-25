class MemoryGardenError(Exception):
    """Memory Garden 베이스 예외 클래스"""
    pass


class AnalysisError(MemoryGardenError):
    """대화 분석 또는 처리 중 발생하는 에러"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class MCDICalculationError(AnalysisError):
    """MCDI 점수 계산 중 발생하는 에러"""
    pass


class WorkflowError(Exception):
    """대화 워크플로우 제어 중 발생하는 에러"""
    def __init__(self, message: str, workflow_step: str = None):
        self.message = message
        self.workflow_step = workflow_step
        super().__init__(self.message)

class DatabaseError(Exception):
    """데이터베이스 작업 중 발생하는 에러"""
    pass

class MemoryError(MemoryGardenError):
    """메모리 레이어 작업 중 발생하는 에러"""
    pass

class AIServiceError(Exception):
    """LLM 또는 외부 AI 서비스 호출 중 발생하는 에러"""
    pass

class ExternalServiceError(MemoryGardenError):
    """외부 서비스 (Kakao, etc.) 호출 중 발생하는 에러"""
    pass
