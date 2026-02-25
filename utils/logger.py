"""
구조화된 로깅 유틸리티

JSON 포맷의 구조화된 로그를 생성하며,
파일 및 콘솔 핸들러를 지원합니다.
요청별 trace_id를 통해 요청 추적이 가능합니다.

Author: Memory Garden Team
Created: 2025-02-10
"""

# ============================================
# 1. Standard Library Imports
# ============================================
import logging
import logging.handlers
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextvars import ContextVar

# ============================================
# 2. Third-Party Imports
# ============================================
# None (순수 표준 라이브러리 사용)

# ============================================
# 3. Local Imports
# ============================================
from config.settings import settings


# ============================================
# 4. 상수 정의
# ============================================

# 로그 디렉토리
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 로그 파일 경로
LOG_FILE = LOG_DIR / "memory_garden.log"
ERROR_LOG_FILE = LOG_DIR / "memory_garden_error.log"

# 로그 포맷
LOG_FORMAT_CONSOLE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 로그 로테이션 설정
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5  # 최대 5개 백업 파일

# 환경별 로그 레벨
DEFAULT_LOG_LEVEL = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)


# ============================================
# 5. ContextVar (요청별 trace_id)
# ============================================

# 요청별 trace_id 저장
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

# 요청별 추가 컨텍스트 저장
log_context_var: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


# ============================================
# 6. JSONFormatter 클래스
# ============================================

class JSONFormatter(logging.Formatter):
    """
    JSON 포맷 로그 포매터

    구조화된 JSON 형태로 로그를 출력합니다.
    trace_id 및 추가 컨텍스트를 자동으로 포함합니다.

    Attributes:
        None

    Example Output:
        {
            "timestamp": "2025-02-10T19:20:30.123456",
            "level": "INFO",
            "logger": "api.main",
            "message": "Request started",
            "trace_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "user123",
            "processing_time_ms": 125.42
        }
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 JSON 문자열로 포맷팅

        Args:
            record: 로깅 레코드

        Returns:
            JSON 형식의 로그 문자열
        """
        # 기본 로그 데이터
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # trace_id 추가 (있는 경우)
        trace_id = trace_id_var.get()
        if trace_id:
            log_data["trace_id"] = trace_id

        # 추가 컨텍스트 병합
        log_context = log_context_var.get()
        if log_context:
            log_data.update(log_context)

        # extra 필드 추가 (logger.info(..., extra={...}) 사용 시)
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # 파일 및 라인 정보 (DEBUG 레벨일 때만)
        if record.levelno <= logging.DEBUG:
            log_data["file"] = record.pathname
            log_data["line"] = record.lineno
            log_data["function"] = record.funcName

        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """
    컬러 콘솔 포매터

    개발 환경에서 가독성을 위해 로그 레벨별 색상을 추가합니다.

    색상:
    - DEBUG: 회색
    - INFO: 파란색
    - WARNING: 노란색
    - ERROR: 빨간색
    - CRITICAL: 빨간색 + 굵게
    """

    # ANSI 색상 코드
    COLORS = {
        "DEBUG": "\033[90m",      # 회색
        "INFO": "\033[94m",       # 파란색
        "WARNING": "\033[93m",    # 노란색
        "ERROR": "\033[91m",      # 빨간색
        "CRITICAL": "\033[91m\033[1m",  # 빨간색 + 굵게
        "RESET": "\033[0m"        # 리셋
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 컬러 포맷팅

        Args:
            record: 로깅 레코드

        Returns:
            색상이 적용된 로그 문자열
        """
        # 레벨별 색상 적용
        level_color = self.COLORS.get(record.levelname, "")
        reset_color = self.COLORS["RESET"]

        # 기본 포맷팅
        formatted = super().format(record)

        # trace_id 추가 (있는 경우)
        trace_id = trace_id_var.get()
        if trace_id:
            formatted += f" [trace_id={trace_id[:8]}...]"

        # 색상 적용
        return f"{level_color}{formatted}{reset_color}"


# ============================================
# 7. Logger 설정 함수
# ============================================

def setup_logger(
    name: str,
    level: Optional[int] = None,
    json_format: bool = True,
    console: bool = True,
    file: bool = True
) -> logging.Logger:
    """
    구조화된 로거 생성 및 설정

    Args:
        name: 로거 이름 (보통 __name__)
        level: 로그 레벨 (None이면 설정 파일 기준)
        json_format: 파일 로그를 JSON 포맷으로 출력할지 여부
        console: 콘솔 핸들러 추가 여부
        file: 파일 핸들러 추가 여부

    Returns:
        설정된 Logger 인스턴스

    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Test message", extra={"user_id": "123"})
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 있으면 반환 (중복 방지)
    if logger.handlers:
        return logger

    # 로그 레벨 설정
    if level is None:
        level = DEFAULT_LOG_LEVEL
    logger.setLevel(level)

    # 전파 방지 (루트 로거로 전파 안 함)
    logger.propagate = False

    # ============================================
    # 콘솔 핸들러 (개발 환경: 컬러, 프로덕션: 일반)
    # ============================================
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # 개발 환경: 컬러 포매터
        if settings.APP_ENV == "development":
            console_formatter = ColoredConsoleFormatter(
                LOG_FORMAT_CONSOLE,
                datefmt=LOG_DATE_FORMAT
            )
        else:
            console_formatter = logging.Formatter(
                LOG_FORMAT_CONSOLE,
                datefmt=LOG_DATE_FORMAT
            )

        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # ============================================
    # 파일 핸들러 (로테이션)
    # ============================================
    if file:
        # 일반 로그 파일 (INFO 이상)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)

        # JSON 포맷 또는 일반 포맷
        if json_format:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                LOG_FORMAT_CONSOLE,
                datefmt=LOG_DATE_FORMAT
            )

        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 에러 로그 파일 (ERROR 이상만)
        error_handler = logging.handlers.RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    로거 인스턴스 가져오기

    setup_logger의 간단한 래퍼 함수입니다.
    기본 설정으로 로거를 생성합니다.

    Args:
        name: 로거 이름 (보통 __name__)

    Returns:
        설정된 Logger 인스턴스

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return setup_logger(name)


# ============================================
# 8. Trace ID 관리 함수
# ============================================

def set_trace_id(trace_id: str) -> None:
    """
    현재 요청의 trace_id 설정

    FastAPI 미들웨어나 의존성에서 호출하여
    요청별 고유 ID를 설정합니다.

    Args:
        trace_id: 요청 고유 ID (UUID 등)

    Example:
        >>> import uuid
        >>> set_trace_id(str(uuid.uuid4()))
    """
    trace_id_var.set(trace_id)


def get_trace_id() -> Optional[str]:
    """
    현재 요청의 trace_id 가져오기

    Returns:
        trace_id 문자열 또는 None
    """
    return trace_id_var.get()


def clear_trace_id() -> None:
    """
    trace_id 초기화

    요청 처리 완료 후 호출하여 초기화합니다.
    """
    trace_id_var.set(None)


# ============================================
# 9. 로그 컨텍스트 관리 함수
# ============================================

def set_log_context(context: Dict[str, Any]) -> None:
    """
    로그 컨텍스트 설정

    현재 요청의 추가 컨텍스트 정보를 설정합니다.
    모든 로그에 자동으로 포함됩니다.

    Args:
        context: 컨텍스트 딕셔너리

    Example:
        >>> set_log_context({"user_id": "user123", "session_id": "session456"})
    """
    log_context_var.set(context)


def update_log_context(context: Dict[str, Any]) -> None:
    """
    로그 컨텍스트 업데이트

    기존 컨텍스트에 새로운 값을 병합합니다.

    Args:
        context: 추가할 컨텍스트

    Example:
        >>> update_log_context({"processing_time_ms": 125.42})
    """
    current_context = log_context_var.get()
    current_context.update(context)
    log_context_var.set(current_context)


def get_log_context() -> Dict[str, Any]:
    """
    현재 로그 컨텍스트 가져오기

    Returns:
        로그 컨텍스트 딕셔너리
    """
    return log_context_var.get()


def clear_log_context() -> None:
    """
    로그 컨텍스트 초기화

    요청 처리 완료 후 호출하여 초기화합니다.
    """
    log_context_var.set({})


# ============================================
# 10. 로그 레벨 동적 변경
# ============================================

def set_log_level(logger_name: str, level: str) -> None:
    """
    특정 로거의 로그 레벨 동적 변경

    Args:
        logger_name: 로거 이름
        level: 로그 레벨 문자열 (DEBUG/INFO/WARNING/ERROR/CRITICAL)

    Example:
        >>> set_log_level("api.main", "DEBUG")
    """
    logger = logging.getLogger(logger_name)
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 모든 핸들러의 레벨도 변경
    for handler in logger.handlers:
        handler.setLevel(log_level)


def set_all_log_levels(level: str) -> None:
    """
    모든 로거의 로그 레벨 변경

    Args:
        level: 로그 레벨 문자열

    Example:
        >>> set_all_log_levels("DEBUG")
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.root.setLevel(log_level)

    # 모든 로거 순회
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)

        for handler in logger.handlers:
            handler.setLevel(log_level)


# ============================================
# 11. 로그 파일 관리
# ============================================

def rotate_logs() -> None:
    """
    로그 파일 수동 로테이션

    즉시 로그 파일을 로테이션합니다.
    """
    for handler in logging.root.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            handler.doRollover()


def get_log_files() -> Dict[str, Dict[str, Any]]:
    """
    현재 로그 파일 정보 조회

    Returns:
        {
            "main_log": {
                "path": "logs/memory_garden.log",
                "size_mb": 2.5,
                "exists": True
            },
            "error_log": {...}
        }
    """
    def get_file_info(path: Path) -> Dict[str, Any]:
        if path.exists():
            size_bytes = path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            return {
                "path": str(path),
                "size_mb": round(size_mb, 2),
                "exists": True
            }
        return {
            "path": str(path),
            "size_mb": 0,
            "exists": False
        }

    return {
        "main_log": get_file_info(LOG_FILE),
        "error_log": get_file_info(ERROR_LOG_FILE)
    }


# ============================================
# 12. 초기화
# ============================================

# 루트 로거 설정 (다른 라이브러리 로그 캐치)
logging.basicConfig(
    level=DEFAULT_LOG_LEVEL,
    format=LOG_FORMAT_CONSOLE,
    datefmt=LOG_DATE_FORMAT
)

# 외부 라이브러리 로그 레벨 조정
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("redis").setLevel(logging.WARNING)


# ============================================
# 13. 사용 예시 (문서화)
# ============================================

"""
사용 예시:

# 1. 기본 사용
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Application started")

# 2. 구조화된 로깅
logger.info(
    "User login",
    extra={
        "user_id": "user123",
        "ip_address": "192.168.1.1",
        "login_method": "email"
    }
)

# 3. Trace ID 사용 (FastAPI 미들웨어)
from utils.logger import set_trace_id, clear_trace_id
import uuid

@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    set_trace_id(trace_id)

    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id

    clear_trace_id()
    return response

# 4. 로그 컨텍스트 사용
from utils.logger import set_log_context

set_log_context({
    "user_id": "user123",
    "session_id": "session456"
})

logger.info("Processing request")  # user_id와 session_id가 자동으로 포함됨

# 5. 로그 레벨 동적 변경
from utils.logger import set_log_level

set_log_level("api.main", "DEBUG")

# 6. 에러 로깅
try:
    result = process_data()
except Exception as e:
    logger.error(
        "Data processing failed",
        extra={"input_size": len(data)},
        exc_info=True  # 스택 트레이스 포함
    )

# 7. JSON 로그 파일 확인
# logs/memory_garden.log 파일을 확인하면 JSON 형태로 저장됨
{
    "timestamp": "2025-02-10T19:20:30.123456",
    "level": "INFO",
    "logger": "api.main",
    "message": "User login",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user123",
    "ip_address": "192.168.1.1"
}
"""
