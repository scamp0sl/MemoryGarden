# 🌐 도메인 설정 가이드 (n8n.softline.co.kr)

## 🎯 현재 상황

```yaml
도메인: n8n.softline.co.kr
상태: ✅ 활성화 (nginx 실행 중)
현재 서비스: n8n (Workflow Automation)
추가 필요: Memory Garden API 경로 설정
```

---

## 📋 2가지 설정 옵션

### **옵션 A: 경로 기반 라우팅** ⭐ 추천 (간단)
```
n8n.softline.co.kr/         → n8n (기존)
n8n.softline.co.kr/api/     → Memory Garden API (추가)
n8n.softline.co.kr/kakao/   → Kakao Webhook (추가)
```

### **옵션 B: 서브도메인 사용** (깔끔)
```
n8n.softline.co.kr          → n8n (기존)
api.softline.co.kr          → Memory Garden API (신규)
또는
memgarden.softline.co.kr    → Memory Garden API (신규)
```

---

## ✅ 옵션 A: 경로 기반 라우팅 설정 (추천)

### 1단계: Nginx 설정 파일 수정

```bash
# Nginx 설정 파일 위치 확인
sudo find /etc/nginx -name "*n8n*" -o -name "*softline*"

# 또는 전체 설정 확인
sudo nginx -T | grep -B 5 "n8n.softline.co.kr"
```

### 2단계: Memory Garden API 경로 추가

```nginx
# /etc/nginx/sites-available/n8n.softline.co.kr
# 또는 /etc/nginx/conf.d/n8n.softline.co.kr.conf

server {
    listen 443 ssl http2;
    server_name n8n.softline.co.kr;

    # SSL 설정 (기존 유지)
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 기존 n8n 설정 (그대로 유지)
    location / {
        proxy_pass http://localhost:5678;  # n8n 포트
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # ============================================
    # Memory Garden API 추가 (여기부터!)
    # ============================================

    # Memory Garden API 전체
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS (필요 시)
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
    }

    # Kakao Webhook (중요!)
    location /kakao/ {
        proxy_pass http://localhost:8000/kakao/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Webhook 타임아웃 설정
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }

    # API Docs (Swagger)
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # ReDoc
    location /redoc {
        proxy_pass http://localhost:8000/redoc;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

### 3단계: Nginx 설정 테스트 및 재시작

```bash
# 1. 설정 파일 문법 확인
sudo nginx -t

# 예상 출력:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# 2. Nginx 재시작
sudo systemctl reload nginx

# 또는
sudo systemctl restart nginx

# 3. Nginx 상태 확인
sudo systemctl status nginx
```

### 4단계: FastAPI 서버 실행 확인

```bash
# 현재 실행 중인지 확인
ps aux | grep "uvicorn api.main:app" | grep -v grep

# 실행 중이 아니면 시작
cd /home/admin/docker/MemoryGardenAI
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# 또는 systemd 서비스로 등록 (권장)
```

### 5단계: 테스트

```bash
# 1. 로컬에서 테스트
curl https://n8n.softline.co.kr/kakao/webhook/test

# 예상 응답:
# {"status":"ok","message":"Webhook endpoint is working!"}

# 2. 외부에서 테스트
curl -X POST "https://n8n.softline.co.kr/kakao/webhook/simulate?user_key=test_001&message=Hello"

# 예상 응답:
# {"status":"ok","user_key":"test_001","message":"Simulation completed"}

# 3. API Docs 확인
https://n8n.softline.co.kr/docs
```

---

## 🔧 옵션 B: 서브도메인 설정

### 1단계: DNS 레코드 추가

```
도메인 관리 콘솔에서:
A 레코드 추가:
  - 호스트: api (또는 memgarden)
  - 값: 서버 IP 주소
  - TTL: 3600

결과:
  - api.softline.co.kr → 서버 IP
  - 또는 memgarden.softline.co.kr → 서버 IP
```

### 2단계: Nginx 새 서버 블록 생성

```nginx
# /etc/nginx/sites-available/api.softline.co.kr

server {
    listen 443 ssl http2;
    server_name api.softline.co.kr;  # 또는 memgarden.softline.co.kr

    # SSL 인증서 (Let's Encrypt 권장)
    ssl_certificate /etc/letsencrypt/live/api.softline.co.kr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.softline.co.kr/privkey.pem;

    # Memory Garden API
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 지원 (필요 시)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;
    }
}

# HTTP → HTTPS 리다이렉트
server {
    listen 80;
    server_name api.softline.co.kr;
    return 301 https://$server_name$request_uri;
}
```

### 3단계: SSL 인증서 발급

```bash
# Certbot 설치 (없는 경우)
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 자동 발급
sudo certbot --nginx -d api.softline.co.kr

# 또는 memgarden.softline.co.kr
sudo certbot --nginx -d memgarden.softline.co.kr

# 자동 갱신 확인
sudo certbot renew --dry-run
```

### 4단계: Nginx 설정 활성화

```bash
# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/api.softline.co.kr /etc/nginx/sites-enabled/

# Nginx 테스트 및 재시작
sudo nginx -t
sudo systemctl reload nginx
```

### 5단계: 테스트

```bash
# API 문서 접속
https://api.softline.co.kr/docs

# Webhook 테스트
curl https://api.softline.co.kr/kakao/webhook/test
```

---

## 🚀 카카오 채널 Webhook URL 설정

### Nginx 설정 완료 후:

```yaml
옵션 A 사용 시:
  Webhook URL: https://n8n.softline.co.kr/kakao/webhook

옵션 B 사용 시:
  Webhook URL: https://api.softline.co.kr/kakao/webhook
  또는
  Webhook URL: https://memgarden.softline.co.kr/kakao/webhook
```

### 카카오 비즈니스 센터 설정:

```
1. https://business.kakao.com 접속
2. Memory Garden 채널 선택
3. 관리 > 상세 설정 > Webhook URL
4. URL 입력:
   - https://n8n.softline.co.kr/kakao/webhook (옵션 A)
   - 또는 https://api.softline.co.kr/kakao/webhook (옵션 B)
5. 저장
6. 테스트 메시지 전송 → FastAPI 로그 확인!
```

---

## 🔐 SystemD 서비스 등록 (권장)

FastAPI 서버를 자동 시작되도록 설정:

```bash
# 1. 서비스 파일 생성
sudo nano /etc/systemd/system/memgarden.service
```

```ini
[Unit]
Description=Memory Garden API Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/docker/MemoryGardenAI
Environment="PATH=/home/admin/docker/MemoryGardenAI/.venv/bin"
ExecStart=/home/admin/docker/MemoryGardenAI/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# 로그
StandardOutput=append:/var/log/memgarden/access.log
StandardError=append:/var/log/memgarden/error.log

[Install]
WantedBy=multi-user.target
```

```bash
# 2. 로그 디렉토리 생성
sudo mkdir -p /var/log/memgarden
sudo chown admin:admin /var/log/memgarden

# 3. 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable memgarden.service
sudo systemctl start memgarden.service

# 4. 상태 확인
sudo systemctl status memgarden.service

# 5. 로그 확인
sudo journalctl -u memgarden.service -f
```

---

## 🧪 전체 테스트 체크리스트

### 로컬 테스트

```bash
# 1. FastAPI 서버 직접 접속
curl http://localhost:8000/kakao/webhook/test

# 2. Nginx를 통한 접속 (옵션 A)
curl https://n8n.softline.co.kr/kakao/webhook/test

# 3. Webhook 시뮬레이션
curl -X POST "https://n8n.softline.co.kr/kakao/webhook/simulate?user_key=test&message=OK"

# 4. API 문서 접속
https://n8n.softline.co.kr/docs
```

### 외부 테스트

```bash
# 다른 컴퓨터에서:
curl https://n8n.softline.co.kr/kakao/webhook/test

# 또는 브라우저에서:
https://n8n.softline.co.kr/docs
```

### 카카오 연동 테스트

```
1. 카카오 채널 Webhook URL 설정
2. 카카오톡에서 채널에 메시지 전송: "안녕하세요"
3. FastAPI 로그 확인:
   - sudo journalctl -u memgarden.service -f
   또는
   - tail -f /var/log/memgarden/access.log

4. 로그에서 user_key 확인:
   ============================================================
   📨 카카오 메시지 수신!
   ============================================================
   👤 user_key: user_abc123def456
   💬 메시지: 안녕하세요
   ============================================================
```

---

## 🎯 권장 설정 순서

### 빠른 시작 (옵션 A - 15분)

```bash
# 1. Nginx 설정 백업
sudo cp /etc/nginx/sites-available/n8n.softline.co.kr /etc/nginx/sites-available/n8n.softline.co.kr.backup

# 2. Nginx 설정 편집
sudo nano /etc/nginx/sites-available/n8n.softline.co.kr
# 위의 "옵션 A" 설정 추가

# 3. Nginx 테스트 및 재시작
sudo nginx -t && sudo systemctl reload nginx

# 4. FastAPI 서버 확인
ps aux | grep uvicorn

# 5. 테스트
curl https://n8n.softline.co.kr/kakao/webhook/test

# 6. 카카오 Webhook URL 설정
# https://n8n.softline.co.kr/kakao/webhook

# 7. 카카오톡에서 메시지 전송 → user_key 수집!
```

---

## 🔧 문제 해결

### 502 Bad Gateway

```bash
# FastAPI 서버 실행 확인
ps aux | grep uvicorn

# 실행 중이 아니면:
cd /home/admin/docker/MemoryGardenAI
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 또는 systemd 서비스 재시작
sudo systemctl restart memgarden.service
```

### 404 Not Found

```bash
# Nginx 설정 확인
sudo nginx -T | grep -A 20 "location /kakao"

# FastAPI 라우터 확인
curl http://localhost:8000/kakao/webhook/test
```

### SSL 인증서 오류

```bash
# 인증서 확인
sudo certbot certificates

# 인증서 갱신
sudo certbot renew

# Nginx 재시작
sudo systemctl reload nginx
```

### 로그 확인

```bash
# Nginx 에러 로그
sudo tail -f /var/log/nginx/error.log

# FastAPI 로그
sudo journalctl -u memgarden.service -f

# 또는
tail -f /var/log/memgarden/error.log
```

---

## 📚 다음 단계

1. ✅ Nginx 설정 완료
2. ✅ FastAPI 서버 실행
3. ✅ 도메인 테스트
4. ✅ 카카오 Webhook URL 설정
5. ✅ 실제 user_key 수집
6. 🔄 DB에 user_key 저장
7. 🔄 일일 대화 플로우 통합

---

## 🎉 요약

```yaml
기존 상태:
  - 도메인: n8n.softline.co.kr ✅
  - 서비스: n8n (기존)
  - FastAPI: localhost:8000 실행 중

설정 필요:
  - Nginx 경로 추가 (/kakao/)
  - 또는 서브도메인 생성

완료 후:
  - Webhook URL: https://n8n.softline.co.kr/kakao/webhook
  - ngrok 불필요! ✅
  - 즉시 실제 user_key 수집 가능! ✅
```

**ngrok 대신 실제 도메인 사용 - 훨씬 안정적이고 전문적입니다!** 🚀
