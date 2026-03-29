# Domain 서버 Nginx 설정 가이드

## 🎯 목적
n8n.softline.co.kr 도메인을 N8N 서버의 8888 포트로 연결

## 📝 설정 파일

### `/etc/nginx/sites-available/n8n.softline.co.kr.conf`
또는
### `/etc/nginx/conf.d/n8n.softline.co.kr.conf`

```nginx
# HTTPS 서버 블록
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name n8n.softline.co.kr;

    # SSL 인증서 (기존 설정 유지)
    ssl_certificate /etc/letsencrypt/live/n8n.softline.co.kr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/n8n.softline.co.kr/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 모든 경로를 N8N 서버 8888 포트로 포워딩
    location / {
        # ============================================
        # 중요: N8N 서버 IP와 포트
        # ============================================
        proxy_pass http://N8N서버IP:8888;

        proxy_http_version 1.1;

        # 필수 헤더
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # WebSocket 지원 (n8n용)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;

        # 타임아웃 설정
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 버퍼 설정
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # 로그 설정
    access_log /var/log/nginx/n8n.softline.co.kr-access.log;
    error_log /var/log/nginx/n8n.softline.co.kr-error.log;
}

# HTTP → HTTPS 리다이렉트
server {
    listen 80;
    listen [::]:80;
    server_name n8n.softline.co.kr;

    return 301 https://$server_name$request_uri;
}
```

## ⚙️ 적용 방법

```bash
# 1. 설정 파일 생성/수정
sudo nano /etc/nginx/sites-available/n8n.softline.co.kr.conf

# 2. 심볼릭 링크 생성 (sites-enabled 사용 시)
sudo ln -s /etc/nginx/sites-available/n8n.softline.co.kr.conf /etc/nginx/sites-enabled/

# 3. 설정 테스트
sudo nginx -t

# 4. Nginx 재시작
sudo systemctl reload nginx
```

## ✅ 테스트

```bash
# 1. Domain 서버에서 로컬 테스트
curl -I http://localhost/

# 2. 외부에서 HTTPS 테스트
curl https://n8n.softline.co.kr/

# 3. Memory Garden Webhook 테스트
curl https://n8n.softline.co.kr/kakao/webhook/test

# 예상 응답:
# {"status":"ok","message":"Webhook endpoint is working!"}

# 4. API 문서 접근
curl -I https://n8n.softline.co.kr/docs

# 5. n8n 접근 (기존 기능 확인)
curl -I https://n8n.softline.co.kr/
```

## 🔍 문제 해결

### 502 Bad Gateway
```bash
# N8N 서버 8888 포트 확인
telnet N8N서버IP 8888

# N8N 서버에서 nginx 상태 확인
ssh N8N서버
sudo systemctl status nginx
sudo netstat -tuln | grep 8888
```

### 504 Gateway Timeout
```nginx
# 타임아웃 증가 (location 블록 내)
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

### SSL 인증서 갱신
```bash
# Let's Encrypt 인증서 갱신
sudo certbot renew --nginx
sudo systemctl reload nginx
```

## 📊 Architecture

```
Internet
  ↓ HTTPS (443)
Domain 서버 (softline.co.kr)
  ├─ SSL 종료
  └─ HTTP (8888) → N8N 서버
                    ↓
                    N8N 서버 (nginx:8888)
                    ├─ / → n8n (5678)
                    ├─ /kakao/ → FastAPI (8000)
                    ├─ /api/ → FastAPI (8000)
                    └─ /docs → FastAPI (8000)
```

## 🔐 보안 체크리스트

- [x] SSL/TLS 활성화 (TLS 1.2+)
- [x] HTTPS 리다이렉트 설정
- [x] 적절한 헤더 전달 (X-Forwarded-*)
- [x] 타임아웃 설정
- [ ] Rate limiting (선택사항)
- [ ] IP 화이트리스트 (선택사항)

## 📞 문의

설정 중 문제가 있으면 N8N 서버 관리자에게 문의하세요.

---

생성일: 2026-02-20
작성자: Memory Garden DevOps Team
