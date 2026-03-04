#!/bin/bash
pkill -f "uvicorn api.main:app"
sleep 2

# HTTP 모드로 실행 (Nginx가 HTTPS 처리)
nohup .venv/bin/uvicorn api.main:app \
    --reload \
    --host 127.0.0.1 \
    --port 8002 \
    --log-level info \
    >> logs/fastapi.log 2>&1 &

echo "FastAPI 서버 시작 (HTTP 모드, Nginx 프록시용)"
echo "PID: $!"
