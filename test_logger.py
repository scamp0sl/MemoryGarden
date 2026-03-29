"""
Logger 기능 검증 스크립트

utils/logger의 주요 기능을 테스트합니다.
"""

import json
import uuid
from pathlib import Path

from utils.logger import (
    get_logger,
    setup_logger,
    set_trace_id,
    get_trace_id,
    clear_trace_id,
    set_log_context,
    update_log_context,
    get_log_context,
    clear_log_context,
    set_log_level,
    get_log_files,
    LOG_FILE,
    ERROR_LOG_FILE
)


def test_basic_logging():
    """기본 로깅 테스트"""
    print("=" * 60)
    print("기본 로깅 테스트")
    print("=" * 60)

    logger = get_logger(__name__)

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    print("✅ 기본 로깅 테스트 완료")


def test_structured_logging():
    """구조화된 로깅 테스트"""
    print("\n" + "=" * 60)
    print("구조화된 로깅 테스트")
    print("=" * 60)

    logger = get_logger("test.structured")

    # extra 필드로 구조화된 데이터 추가
    logger.info(
        "User login",
        extra={
            "user_id": "user123",
            "ip_address": "192.168.1.1",
            "login_method": "email",
            "processing_time_ms": 125.42
        }
    )

    print("✅ 구조화된 로깅 테스트 완료")


def test_trace_id():
    """Trace ID 테스트"""
    print("\n" + "=" * 60)
    print("Trace ID 테스트")
    print("=" * 60)

    logger = get_logger("test.trace")

    # Trace ID 설정
    trace_id = str(uuid.uuid4())
    set_trace_id(trace_id)

    print(f"설정된 Trace ID: {trace_id}")

    # 로그 출력 (trace_id 자동 포함)
    logger.info("Request started")
    logger.info("Processing request")
    logger.info("Request completed")

    # Trace ID 가져오기
    current_trace_id = get_trace_id()
    print(f"조회된 Trace ID: {current_trace_id}")

    assert current_trace_id == trace_id, "Trace ID 불일치"

    # Trace ID 초기화
    clear_trace_id()
    assert get_trace_id() is None, "Trace ID 초기화 실패"

    print("✅ Trace ID 테스트 완료")


def test_log_context():
    """로그 컨텍스트 테스트"""
    print("\n" + "=" * 60)
    print("로그 컨텍스트 테스트")
    print("=" * 60)

    logger = get_logger("test.context")

    # 컨텍스트 설정
    set_log_context({
        "user_id": "user123",
        "session_id": "session456"
    })

    logger.info("Context test 1")

    # 컨텍스트 업데이트
    update_log_context({
        "request_id": "req789",
        "processing_time_ms": 250.5
    })

    logger.info("Context test 2")

    # 컨텍스트 확인
    context = get_log_context()
    print(f"현재 컨텍스트: {context}")

    assert "user_id" in context, "user_id 없음"
    assert "session_id" in context, "session_id 없음"
    assert "request_id" in context, "request_id 없음"

    # 컨텍스트 초기화
    clear_log_context()
    assert get_log_context() == {}, "컨텍스트 초기화 실패"

    print("✅ 로그 컨텍스트 테스트 완료")


def test_exception_logging():
    """예외 로깅 테스트"""
    print("\n" + "=" * 60)
    print("예외 로깅 테스트")
    print("=" * 60)

    logger = get_logger("test.exception")

    try:
        # 의도적으로 에러 발생
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.error(
            "Division by zero error",
            extra={"numerator": 1, "denominator": 0},
            exc_info=True  # 스택 트레이스 포함
        )

    print("✅ 예외 로깅 테스트 완료")


def test_log_levels():
    """로그 레벨 테스트"""
    print("\n" + "=" * 60)
    print("로그 레벨 테스트")
    print("=" * 60)

    logger = get_logger("test.levels")

    # 초기 레벨로 로그
    logger.debug("Debug level message (might not appear)")
    logger.info("Info level message")

    # 로그 레벨 변경
    print("\n로그 레벨을 DEBUG로 변경...")
    set_log_level("test.levels", "DEBUG")

    logger.debug("Debug level message (should appear now)")
    logger.info("Info level message")

    print("✅ 로그 레벨 테스트 완료")


def test_json_log_file():
    """JSON 로그 파일 테스트"""
    print("\n" + "=" * 60)
    print("JSON 로그 파일 테스트")
    print("=" * 60)

    logger = get_logger("test.json")

    # Trace ID와 컨텍스트 설정
    set_trace_id(str(uuid.uuid4()))
    set_log_context({
        "user_id": "user123",
        "session_id": "session456"
    })

    # 구조화된 로그 생성
    logger.info(
        "JSON log test message",
        extra={
            "test_field": "test_value",
            "numeric_field": 42,
            "nested_field": {"key": "value"}
        }
    )

    # 로그 파일 정보 조회
    log_files = get_log_files()
    print("\n로그 파일 정보:")
    for name, info in log_files.items():
        print(f"  {name}:")
        print(f"    경로: {info['path']}")
        print(f"    크기: {info['size_mb']} MB")
        print(f"    존재: {info['exists']}")

    # JSON 로그 파일 읽기 (마지막 줄)
    if LOG_FILE.exists():
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                try:
                    log_entry = json.loads(last_line)
                    print("\n마지막 로그 엔트리 (JSON):")
                    print(json.dumps(log_entry, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print("\n❌ JSON 파싱 실패")

    # 정리
    clear_trace_id()
    clear_log_context()

    print("✅ JSON 로그 파일 테스트 완료")


def test_file_rotation():
    """로그 파일 로테이션 테스트"""
    print("\n" + "=" * 60)
    print("로그 파일 로테이션 테스트")
    print("=" * 60)

    logger = get_logger("test.rotation")

    # 대량 로그 생성 (로테이션 확인)
    print("대량 로그 생성 중 (100개)...")
    for i in range(100):
        logger.info(
            f"Rotation test message {i}",
            extra={
                "iteration": i,
                "data": "x" * 100  # 더미 데이터
            }
        )

    # 로그 파일 정보 확인
    log_files = get_log_files()
    print("\n로그 파일 정보 (로테이션 후):")
    for name, info in log_files.items():
        print(f"  {name}: {info['size_mb']} MB")

    print("✅ 로그 파일 로테이션 테스트 완료")


def test_multiple_loggers():
    """다중 로거 테스트"""
    print("\n" + "=" * 60)
    print("다중 로거 테스트")
    print("=" * 60)

    # 여러 로거 생성
    logger1 = get_logger("module.api")
    logger2 = get_logger("module.database")
    logger3 = get_logger("module.service")

    logger1.info("API module log")
    logger2.info("Database module log")
    logger3.info("Service module log")

    print("✅ 다중 로거 테스트 완료")


def test_combined_features():
    """복합 기능 테스트 (실제 사용 시나리오)"""
    print("\n" + "=" * 60)
    print("복합 기능 테스트 (실제 시나리오)")
    print("=" * 60)

    logger = get_logger("test.combined")

    # 요청 시작 - Trace ID 설정
    trace_id = str(uuid.uuid4())
    set_trace_id(trace_id)

    # 컨텍스트 설정
    set_log_context({
        "user_id": "user123",
        "session_id": "session456"
    })

    logger.info("Request started")

    # 처리 단계 1
    update_log_context({"step": "authentication"})
    logger.info("Authenticating user")

    # 처리 단계 2
    update_log_context({"step": "data_processing"})
    logger.info("Processing data", extra={"data_size": 1024})

    # 처리 단계 3
    update_log_context({"step": "response_generation"})
    logger.info("Generating response")

    # 요청 완료
    logger.info(
        "Request completed",
        extra={"total_processing_time_ms": 345.67}
    )

    # 정리
    clear_trace_id()
    clear_log_context()

    print("✅ 복합 기능 테스트 완료")


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("Logger 기능 테스트 시작")
    print("=" * 60)

    # 모든 테스트 실행
    test_basic_logging()
    test_structured_logging()
    test_trace_id()
    test_log_context()
    test_exception_logging()
    test_log_levels()
    test_json_log_file()
    test_file_rotation()
    test_multiple_loggers()
    test_combined_features()

    # 결과 요약
    print("\n" + "=" * 60)
    print("🎉 모든 테스트 성공!")
    print("=" * 60)

    # 로그 파일 위치 안내
    print("\n로그 파일 위치:")
    print(f"  일반 로그: {LOG_FILE}")
    print(f"  에러 로그: {ERROR_LOG_FILE}")
    print("\nJSON 로그를 확인하려면:")
    print(f"  cat {LOG_FILE} | jq")
    print("=" * 60)


if __name__ == "__main__":
    main()
