# Claude Code 개발 가이드

> Claude Code (Cursor AI, GitHub Copilot 포함)가 Memory Garden 프로젝트를 개발할 때 참고하는 **코딩 어시스턴트 전용 가이드**입니다.
>
> **상세 명세는 [SPEC.md](SPEC.md)를 참조하세요.**

---

## 목차

1. [프로젝트 요약](#1-프로젝트-요약)
2. [코딩 컨벤션](#2-코딩-컨벤션)
3. [프롬프트 템플릿](#3-프롬프트-템플릿)
4. [디버깅 가이드](#4-디버깅-가이드)
5. [AI 도구 활용 팁](#5-ai-도구-활용-팁)
6. [FAQ](#6-faq)

---

## 1. 프로젝트 요약

Memory Garden = 카카오톡 기반 치매 조기 감지 서비스

- 정원 가꾸기 메타포로 일상 대화 중 인지 기능 분석
- MCDI 분석: LR + SD + NC + TO + ER + RT → 종합 점수
- 위험도 4단계: GREEN → YELLOW → ORANGE → RED
- **순수 Python 기반 (LangGraph 불사용)**

### 상세 참조

| 항목 | SPEC.md 위치 |
|------|-------------|
| 서비스 개요, 비즈니스 목표 | §1 |
| MCDI 가중치, 지표 상세 | §2.1.2 |
| 위험도 분류 기준 | §2.1.3 |
| 메모리 시스템 4계층 | §2.1.4 |
| 워크플로우 pseudo-code | §3.3 |
| 데이터 모델 (ERD, 테이블) | §4 |
| API 명세 | §5 |
| 파일 구조 | §6 |
| 로컬 개발 환경 설정 | §7.1 |
| 환경 변수 | §7.2 |
| 배포 (Docker, K8s) | §8 |
| 테스트 전략 | §9 |
| 보안 및 규제 | §10 |
| 성능 최적화 | §11 |

---

## 2. 코딩 컨벤션

### 파일 구조 템플릿

모든 Python 파일은 이 구조를 따릅니다:

```python
"""모듈 한 줄 설명

상세 설명 (선택사항, 복잡한 로직일 때만)

Author: Dev A/B/C
Created: YYYY-MM-DD
"""

# ============================================
# 1. Standard Library Imports (알파벳 순)
# ============================================
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

# ============================================
# 2. Third-Party Imports (알파벳 순)
# ============================================
from fastapi import HTTPException
from pydantic import BaseModel, Field

# ============================================
# 3. Local Imports (상대 경로 우선)
# ============================================
from config.settings import settings
from utils.logger import get_logger

# ============================================
# 4. Logger 설정
# ============================================
logger = get_logger(__name__)

# ============================================
# 5. 상수 정의 (대문자 + 언더스코어)
# ============================================
MAX_RETRIES = 3
VALID_RISK_LEVELS = ["GREEN", "YELLOW", "ORANGE", "RED"]

# ============================================
# 6. 타입 Alias
# ============================================
UserID = str
AnalysisResult = Dict[str, Any]

# ============================================
# 7. 클래스 정의
# ============================================

# ============================================
# 8. 독립 함수
# ============================================
```

### 네이밍 규칙

```python
# 변수명: snake_case
user_id = "user_123"
mcdi_score = 78.5

# Boolean: is_, has_, should_ 접두사
is_valid = True
should_retry = True

# 함수명: 동사 + 명사 (async 접두사 X)
def calculate_score() -> float: ...
async def fetch_data() -> dict: ...

# 클래스명: PascalCase
class MCDICalculator: ...

# 상수: 대문자 + 언더스코어
MAX_RETRIES = 3

# Private: 언더스코어 접두사
def _internal_helper(): ...
```

### 타입 힌팅 (필수)

```python
# 모든 함수 시그니처에 타입 힌팅
async def process_data(
    input_data: List[str],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, float]:
    ...

# Python 3.10+ 문법도 OK
def get_user(user_id: str) -> User | None: ...
```

### 에러 처리 패턴

```python
# 구체적인 예외 처리
try:
    result = await llm.call(prompt)
except RateLimitError as e:
    logger.warning(f"Rate limited: {e}")
    await asyncio.sleep(60)
    result = await llm.call(prompt)
except APIError as e:
    logger.error(f"API error: {e}", exc_info=True)
    raise AnalysisError(f"Failed to call LLM: {e}") from e

# 너무 광범위한 예외 처리 금지
try:
    ...
except Exception:  # ❌ 피할 것!
    pass

# Custom Exception (utils/exceptions.py)
class AnalysisError(MemoryGardenError): ...
```

### 로깅 규칙

```python
logger.debug(f"State updated: {state}")        # 개발 중 상세 정보
logger.info(f"Processing user: {user_id}")     # 주요 작업 시작/완료
logger.warning(f"Cache miss for {user_id}")    # 예상 가능한 문제
logger.error(f"Parse failed: {e}", exc_info=True)  # 복구 가능한 오류
logger.critical(f"DB connection lost!")        # 시스템 중단 수준

# 구조화된 로그 (권장)
logger.info("MCDI calculated", extra={
    "user_id": user_id,
    "mcdi_score": score,
    "risk_level": risk_level
})
```

### Async/Await 규칙

```python
# IO-bound: async
async def fetch_from_db(user_id: str) -> User: ...

# CPU-bound: executor 사용
async def calculate_heavy(data: List[str]) -> float:
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor() as executor:
        return await loop.run_in_executor(executor, _sync_calc, data)

# 병렬 실행
results = await asyncio.gather(
    task1(), task2(), task3(),
    return_exceptions=True  # 하나 실패해도 계속
)

# 타임아웃
result = await asyncio.wait_for(slow_op(), timeout=10.0)
```

### 테스트 코드

```python
# AAA 패턴 (Arrange-Act-Assert)
@pytest.mark.asyncio
async def test_analyze_normal_response():
    # Arrange
    analyzer = Analyzer()
    message = "봄이면 엄마가 쑥을 뜯으러 뒷산에 가셨어요"
    # Act
    result = await analyzer.analyze(message, {})
    # Assert
    assert result["mcdi_score"] > 70

# Mock 사용
@pytest.mark.asyncio
@patch('services.llm_service.LLMService.call')
async def test_with_llm_failure(mock_llm_call):
    mock_llm_call.side_effect = Exception("API Error")
    with pytest.raises(AnalysisError):
        await analyzer.analyze("test", {})
```

---

## 3. 프롬프트 템플릿

### 기본 파일 생성 프롬프트

```
다음 구조로 {파일 경로} 파일을 생성해주세요:

【Context】
- 프로젝트: Memory Garden (치매 조기 감지 서비스)
- 역할: {파일의 역할 설명}
- 상세 명세: SPEC.md 참조

【Requirements】
1. {기능 요구사항}
2. {기능 요구사항}

【Coding Convention】
- 타입 힌팅, Google Style Docstring, try-except, 로깅
- 본 가이드 §2 코딩 컨벤션 준수

【Reference Files】
- {참고할 기존 파일}
```

### 개별 지표 구현 프롬프트

```
core/analysis/{지표}.py를 생성해주세요:

【Context】
프로젝트: Memory Garden
지표 상세: SPEC.md §2.1.2 참조
공통 인터페이스: analyze(message, context) → {"score": float, "components": dict, "details": dict}

【Requirements】
- async 함수, 상세 Docstring
- 주석으로 수식 명시: # Formula: TTR = unique_tokens / total_tokens
- 에러 처리, 로깅

【Test Requirements】
- 정상 케이스, 비정상 케이스, 빈 입력
```

### API 라우트 생성 프롬프트

```
api/routes/{리소스}.py를 생성해주세요:

【Context】
API 명세: SPEC.md §5 참조
스키마: api/schemas/{리소스}.py

【Requirements】
- OpenAPI tags, summary 추가
- 404/400 에러 처리
- 페이지네이션: skip, limit 파라미터
```

---

## 4. 디버깅 가이드

### 일반적인 문제 해결

```python
# 문제 1: NoneType AttributeError → Optional 값 체크
if ctx.memory and "episodic" in ctx.memory and ctx.memory["episodic"]:
    result = ctx.memory["episodic"][0]["content"]
else:
    result = None

# 문제 2: event loop 이미 실행 중 → await 사용
result = await my_async_function()  # asyncio.run() 금지

# 문제 3: Vector DB 검색 결과 없음 → 임베딩 차원/필터 확인
embedding = await embedder.embed("test")
print(f"Embedding dimension: {len(embedding)}")  # 1536이어야 함
```

### 디버깅 테스트

```bash
pytest tests/test_core/test_analysis.py -v              # 파일 전체
pytest tests/test_core/test_analysis.py::test_name -v   # 특정 테스트
pytest tests/test_core/test_analysis.py -v -s            # 출력 포함
```

---

## 5. AI 도구 활용 팁

### Cursor AI
1. `.cursorrules` 파일 생성 → 본 가이드 §2 코딩 컨벤션 복사
2. `Cmd+K` → 파일 생성/수정
3. `@파일명` → 컨텍스트 참조

### Claude Code
1. 고수준 설계 먼저 pseudo-code로 요청 → 구현은 2단계로
2. 복잡한 로직 (논문 수식 등)은 Claude에게 위임
3. SPEC.md와 CLAUDE.md를 함께 참조

### GitHub Copilot
1. 주석으로 로직 설명 → `Tab`으로 자동완성
2. 함수 시그니처 + Docstring → 구현 제안

---

## 6. FAQ

**Q: LangGraph를 왜 안 쓰나요?**
A: 조건부 분기가 2개뿐 (ORANGE/RED 알림, 점수 하락 시 교란변수 체크). if문으로 충분하며 LangGraph는 오버킬입니다. 상세: SPEC.md §1.3

**Q: ProcessingContext vs LangGraph State?**
A: dataclass로 메서드(to_dict 등) 추가 가능, 타입 체킹 엄격, IDE 자동완성 우수

**Q: 비동기 함수는 언제 쓰나요?**
A: DB 쿼리, API 호출(LLM/Kakao), Redis, 파일 I/O → async. 순수 계산(numpy), 문자열 처리, 형태소 분석(Kiwi 동기) → sync

**Q: 테스트 커버리지 목표?**
A: 핵심 로직 90%+, 워크플로우 85%+, 유틸리티 80%+, API 라우트 75%+. 상세: SPEC.md §9
