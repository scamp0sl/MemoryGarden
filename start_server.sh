#!/bin/bash
# Claude Code 환경 변수 상속 방지
unset ANTHROPIC_BASE_URL
export ANTHROPIC_BASE_URL="https://api.anthropic.com"

# 포트 8002 사용 중인 프로세스 종료 (더 안정적인 방법)
PID=$(lsof -ti:8002 2>/dev/null)
if [ -n "$PID" ]; then
    echo "기존 프로세스 종료 (PID: $PID)"
    kill -9 $PID 2>/dev/null
    sleep 1
fi

# HTTP 모드로 실행 (Nginx가 HTTPS 처리)
#    --reload \
nohup .venv/bin/uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8002 \
    --log-level info \
    >> logs/fastapi.log 2>&1 &

echo "FastAPI 서버 시작 (HTTP 모드, Nginx 프록시용)"
echo "PID: $!"
