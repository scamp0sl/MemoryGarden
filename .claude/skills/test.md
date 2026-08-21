---
name: test
description: venv Python으로 테스트 실행
---

# 테스트 실행

프로젝트 가상환경 Python으로 테스트를 실행합니다.

## 사용법

```
/test [파일 경로 또는 테스트 이름]
```

### 예시

```
/test                    # 전체 테스트
/test tests/test_core/   # 특정 디렉토리
/test test_analyzer      # 특정 테스트 이름 포함
```

## 동작

1. `.venv/bin/python`으로 pytest 실행
2. 자동으로 커버리지 리포트 생성
3. 상세 출력 (-v), 실패 시 표준출력 표시 (-s)

## 명령어

```bash
# 전체 테스트
.venv/bin/python -m pytest -v -s

# 특정 파일/디렉토리
.venv/bin/python -m pytest -v -s <path>

# 커버리지 포함
.venv/bin/python -m pytest --cov=. --cov-report=term-missing -v -s
```
