# 🔄 Workflow Module Guide

> **core/workflow/** 디렉토리 완전 가이드
> 파이프라인 기반 대화 세션 워크플로우 사용법

---

## 📚 목차

1. [개요](#1-개요)
2. [Pipeline Framework](#2-pipeline-framework)
3. [SessionWorkflow](#3-sessionworkflow)
4. [커스텀 워크플로우 만들기](#4-커스텀-워크플로우-만들기)
5. [실전 통합 예시](#5-실전-통합-예시)
6. [API 레퍼런스](#6-api-레퍼런스)

---

## 1. 개요

### 1.1 모듈 구조

```
core/workflow/
├── pipeline.py           # 파이프라인 프레임워크
├── session_workflow.py   # 대화 세션 워크플로우
└── __init__.py          # 모듈 export
```

### 1.2 핵심 개념

**Pipeline**: 여러 Step을 순차적으로 실행하는 프레임워크
- 재시도 (retry)
- 타임아웃 (timeout)
- 에러 핸들링 (skip_on_error)
- 로깅

**Step**: 개별 처리 단계
- `execute()`: 실제 로직 구현
- `validate()`: 실행 전 검증
- `on_success()`, `on_failure()`: 후처리

**PipelineContext**: 단계 간 데이터 공유
- 딕셔너리 기반 상태 관리
- `context.set()`, `context.get()`

### 1.3 SessionWorkflow 플로우

```
1. SessionInitStep        → 세션 초기화 (Redis)
2. ConversationStep       → 대화 처리 (DialogueManager)
3. MemoryExtractionStep   → 기억 추출 (MemoryExtractor)
4. AnalysisStep           → 감정/MCDI 분석
5. GardenUpdateStep       → 정원 업데이트 (GardenMapper)
6. MemoryStorageStep      → 메모리 저장 (MemoryManager)
7. ReportCheckStep        → 주간 리포트 (일요일만)
8. SessionCloseStep       → 세션 종료
```

---

## 2. Pipeline Framework

### 2.1 Step 클래스 만들기

```python
from core.workflow import Step, PipelineContext

class MyCustomStep(Step):
    """커스텀 단계 예시"""

    def __init__(self):
        super().__init__(
            name="my_custom_step",
            retries=3,          # 재시도 3회
            timeout=30.0,       # 30초 타임아웃
            skip_on_error=False # 실패 시 중단
        )

    async def execute(self, context: PipelineContext) -> dict:
        """
        실행 로직 구현

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            실행 결과 딕셔너리
        """
        # 이전 단계 결과 조회
        input_data = context.get("some_input")

        # 처리 로직
        result = self._process(input_data)

        # 다음 단계를 위해 컨텍스트에 저장
        context.set("my_result", result)

        return {"status": "success", "result": result}

    async def validate(self, context: PipelineContext) -> bool:
        """
        실행 전 검증 (선택)

        Returns:
            검증 성공 여부
        """
        return context.has("some_input")

    async def on_success(self, context: PipelineContext, result: dict) -> None:
        """성공 시 후처리 (선택)"""
        logger.info(f"Step succeeded: {result}")

    async def on_failure(self, context: PipelineContext, error: Exception) -> None:
        """실패 시 후처리 (선택)"""
        logger.error(f"Step failed: {error}")
```

### 2.2 Pipeline 클래스 만들기

```python
from core.workflow import Pipeline

class MyPipeline(Pipeline):
    """커스텀 파이프라인 예시"""

    def __init__(self):
        super().__init__("my_pipeline")

        # 단계 추가
        self.add_steps([
            Step1(),
            Step2(),
            Step3()
        ])

# 사용
pipeline = MyPipeline()
```

### 2.3 파이프라인 실행

```python
from core.workflow import create_context

# 1. 컨텍스트 생성
context = create_context(
    pipeline_id="unique_id_123",
    initial_data={
        "user_id": "user123",
        "input": "some data"
    }
)

# 2. 파이프라인 실행
result = await pipeline.run(context)

# 3. 결과 확인
print(f"Status: {result.status.value}")  # completed/failed
print(f"Total time: {result.total_execution_time_ms}ms")

# 각 단계 결과
for step_result in result.step_results:
    print(f"{step_result.step_name}: {step_result.status.value}")
```

### 2.4 에러 핸들링 패턴

```python
# 패턴 1: 실패 시 중단 (기본)
class CriticalStep(Step):
    def __init__(self):
        super().__init__(
            "critical_step",
            skip_on_error=False  # 실패 시 파이프라인 중단
        )

# 패턴 2: 실패 시 건너뛰기
class OptionalStep(Step):
    def __init__(self):
        super().__init__(
            "optional_step",
            skip_on_error=True  # 실패해도 다음 단계 계속
        )

# 패턴 3: 재시도 설정
class RetryableStep(Step):
    def __init__(self):
        super().__init__(
            "retryable_step",
            retries=5,          # 최대 5회 재시도
            timeout=60.0        # 60초 타임아웃
        )
```

---

## 3. SessionWorkflow

### 3.1 기본 사용법

```python
from core.workflow import SessionWorkflow

# 1. 워크플로우 생성
workflow = SessionWorkflow()

# 2. 메시지 처리 (간편 인터페이스)
result = await workflow.process_message(
    user_id="user123",
    message="오늘 점심에 된장찌개 먹었어요"
)

# 3. 결과 확인
if result["success"]:
    print(f"Response: {result['response']}")
    print(f"MCDI Score: {result['mcdi_score']}")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Flowers: {result['garden_status']['flower_count']}")

    # 업적 달성
    if result['achievements']:
        print(f"Achievements: {result['achievements']}")

    # 레벨 업
    if result['level_up']:
        print("🎉 Garden level up!")
else:
    print(f"Error: {result['error']}")
```

### 3.2 이미지 메시지 처리

```python
result = await workflow.process_message(
    user_id="user123",
    message="오늘 점심 사진이에요",
    message_type="image",
    image_url="https://example.com/lunch.jpg"
)
```

### 3.3 연속 대화

```python
workflow = SessionWorkflow()

messages = [
    "오늘 점심에 된장찌개 먹었어요",
    "딸이 전화했어요",
    "고향은 부산이에요"
]

for msg in messages:
    result = await workflow.process_message(
        user_id="user123",
        message=msg
    )

    print(f"User: {msg}")
    print(f"Bot: {result['response']}")
    print(f"Flowers: {result['garden_status']['flower_count']}\n")
```

### 3.4 각 단계 설명

#### 1. SessionInitStep
- Redis에 세션 생성
- 세션 ID 할당
- TTL 24시간

#### 2. ConversationStep
- DialogueManager로 대화 처리
- 이전 대화 히스토리 로드
- 응답 생성

#### 3. MemoryExtractionStep
- MemoryExtractor로 중요 정보 추출
- 일화 기억, 전기적 사실, 감정 기억
- 실패해도 계속 진행 (skip_on_error=True)

#### 4. AnalysisStep
- 감정 감지 (간소화 버전)
- MCDI 점수 계산 (임시값)
- 위험도 평가 (GREEN/YELLOW/ORANGE/RED)

#### 5. GardenUpdateStep
- GardenMapper로 정원 상태 업데이트
- 꽃 심기 (+1)
- 업적 체크
- 레벨 업 체크

#### 6. MemoryStorageStep
- MemoryManager로 4계층에 저장
- Session (Redis)
- Episodic (Qdrant)
- Biographical (PostgreSQL)
- Analytical (TimescaleDB)

#### 7. ReportCheckStep
- 일요일에만 실행 (validate)
- 주간 리포트 생성
- 보호자 알림 (TODO)

#### 8. SessionCloseStep
- 세션 상태 업데이트
- 최종 로깅
- 통계 기록

---

## 4. 커스텀 워크플로우 만들기

### 4.1 간단한 워크플로우

```python
from core.workflow import Pipeline, Step, PipelineContext

# Step 1: 데이터 로드
class LoadDataStep(Step):
    def __init__(self):
        super().__init__("load_data")

    async def execute(self, context: PipelineContext) -> dict:
        user_id = context.get("user_id")
        # DB에서 데이터 로드
        data = await load_from_db(user_id)
        context.set("data", data)
        return {"loaded": True}

# Step 2: 처리
class ProcessStep(Step):
    def __init__(self):
        super().__init__("process")

    async def execute(self, context: PipelineContext) -> dict:
        data = context.get("data")
        result = process_data(data)
        context.set("result", result)
        return {"processed": True}

# Step 3: 저장
class SaveStep(Step):
    def __init__(self):
        super().__init__("save")

    async def execute(self, context: PipelineContext) -> dict:
        result = context.get("result")
        await save_to_db(result)
        return {"saved": True}

# 파이프라인 정의
class DataProcessingPipeline(Pipeline):
    def __init__(self):
        super().__init__("data_processing")
        self.add_steps([
            LoadDataStep(),
            ProcessStep(),
            SaveStep()
        ])

# 사용
pipeline = DataProcessingPipeline()
context = create_context("job_123", {"user_id": "user123"})
result = await pipeline.run(context)
```

### 4.2 조건부 실행

```python
class ConditionalStep(Step):
    """조건부로 실행되는 단계"""

    def __init__(self):
        super().__init__("conditional_step")

    async def validate(self, context: PipelineContext) -> bool:
        """특정 조건에서만 실행"""
        return context.get("should_run", False)

    async def execute(self, context: PipelineContext) -> dict:
        # 조건 만족 시에만 실행됨
        return {"executed": True}
```

### 4.3 병렬 처리 (고급)

```python
import asyncio

class ParallelStep(Step):
    """여러 작업을 병렬로 실행하는 단계"""

    async def execute(self, context: PipelineContext) -> dict:
        # 여러 작업 병렬 실행
        results = await asyncio.gather(
            self._task1(),
            self._task2(),
            self._task3(),
            return_exceptions=True
        )

        return {"results": results}

    async def _task1(self):
        await asyncio.sleep(1)
        return "task1_result"

    async def _task2(self):
        await asyncio.sleep(1)
        return "task2_result"

    async def _task3(self):
        await asyncio.sleep(1)
        return "task3_result"
```

---

## 5. 실전 통합 예시

### 5.1 FastAPI 엔드포인트

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.workflow import SessionWorkflow

router = APIRouter()
workflow = SessionWorkflow()

class MessageRequest(BaseModel):
    user_id: str
    message: str
    message_type: str = "text"
    image_url: Optional[str] = None

class MessageResponse(BaseModel):
    success: bool
    response: str
    garden_status: dict
    mcdi_score: float
    risk_level: str

@router.post("/api/v1/chat", response_model=MessageResponse)
async def chat_endpoint(request: MessageRequest):
    """
    대화 처리 API

    전체 워크플로우를 실행하고 결과 반환.
    """
    try:
        result = await workflow.process_message(
            user_id=request.user_id,
            message=request.message,
            message_type=request.message_type,
            image_url=request.image_url
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error")
            )

        return MessageResponse(**result)

    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

### 5.2 카카오톡 웹훅 핸들러

```python
from fastapi import Request
from core.workflow import SessionWorkflow

workflow = SessionWorkflow()

@router.post("/webhook/kakao")
async def kakao_webhook(request: Request):
    """
    카카오톡 웹훅 핸들러

    카카오톡 메시지를 워크플로우로 처리.
    """
    body = await request.json()

    # 카카오톡 요청 파싱
    user_key = body["userRequest"]["user"]["id"]
    utterance = body["userRequest"]["utterance"]

    # 워크플로우 실행
    result = await workflow.process_message(
        user_id=user_key,
        message=utterance
    )

    # 카카오톡 응답 포맷
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": result["response"]
                    }
                }
            ]
        }
    }
```

### 5.3 배치 작업

```python
from core.workflow import SessionWorkflow
import asyncio

async def daily_report_batch():
    """일일 리포트 배치 작업"""
    workflow = SessionWorkflow()

    # 모든 활성 사용자 조회
    active_users = await get_active_users()

    for user in active_users:
        try:
            # 리포트 생성 (일요일만)
            if datetime.now().weekday() == 6:
                # 리포트는 ReportCheckStep에서 자동 처리
                logger.info(f"Weekly report generated for {user.id}")

        except Exception as e:
            logger.error(f"Batch failed for {user.id}: {e}")

    logger.info(f"Daily batch completed: {len(active_users)} users")
```

---

## 6. API 레퍼런스

### 6.1 Pipeline Framework

```python
# Step 클래스
class Step(ABC):
    def __init__(
        self,
        name: str,
        retries: int = 3,
        timeout: float = 30.0,
        skip_on_error: bool = False
    )

    @abstractmethod
    async def execute(self, context: PipelineContext) -> Dict[str, Any]

    async def validate(self, context: PipelineContext) -> bool
    async def on_success(self, context: PipelineContext, result: Dict) -> None
    async def on_failure(self, context: PipelineContext, error: Exception) -> None

# Pipeline 클래스
class Pipeline(ABC):
    def __init__(self, name: str)

    def add_step(self, step: Step) -> None
    def add_steps(self, steps: List[Step]) -> None
    async def run(self, context: PipelineContext) -> PipelineResult

# PipelineContext 클래스
class PipelineContext:
    def set(self, key: str, value: Any) -> None
    def get(self, key: str, default: Any = None) -> Any
    def has(self, key: str) -> bool
    def set_metadata(self, key: str, value: Any) -> None

# 헬퍼 함수
def create_context(
    pipeline_id: str,
    initial_data: Optional[Dict[str, Any]] = None
) -> PipelineContext
```

### 6.2 SessionWorkflow

```python
class SessionWorkflow(Pipeline):
    def __init__(self)

    async def process_message(
        self,
        user_id: str,
        message: str,
        message_type: str = "text",
        image_url: Optional[str] = None
    ) -> Dict[str, Any]
    # Returns:
    # {
    #     "success": True,
    #     "response": "응답 메시지",
    #     "garden_status": {...},
    #     "session_id": "...",
    #     "mcdi_score": 75.0,
    #     "risk_level": "GREEN",
    #     "achievements": [...],
    #     "level_up": False
    # }
```

---

## 📌 다음 단계

1. ✅ **완료:** Pipeline, SessionWorkflow 구현
2. **TODO:** FastAPI 엔드포인트 통합
3. **TODO:** 카카오톡 웹훅 핸들러
4. **TODO:** 실제 MCDI 계산 (6개 지표)
5. **TODO:** 실제 데이터베이스 연결 (PostgreSQL, TimescaleDB)
6. **TODO:** 보호자 알림 시스템

---

**작성일:** 2025-02-10
**버전:** 1.0.0
**작성자:** Memory Garden Team
