---
name: restart-service
description: 안전하게 FastAPI 서비스 재시작 (다른 서비스 영향 없이)
---

# 서비스 안전 재시작

Memory Garden FastAPI 서비스를 안전하게 재시작합니다.

## 사용법

```
/restart-service
```

## 동작

1. 기존 uvicorn 프로세스 종료 (`pkill -f "uvicorn.*api\.main:app"`)
2. 포트 8002 정리
3. start_server.sh로 서비스 재시작

## 주의사항

- Nginx가 HTTPS를 처리하므로 다른 서비스에 영향 없음
- --reload 모드로 코드 변경 즉시 반영
- 로그는 logs/fastapi.log에 기록
