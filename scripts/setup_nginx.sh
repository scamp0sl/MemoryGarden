#!/bin/bash
#
# Memory Garden Nginx 설정 스크립트
#
# n8n.softline.co.kr 도메인에 /kakao/ 경로 추가
#

set -e

echo "============================================================"
echo "Memory Garden Nginx 설정"
echo "============================================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 권한 확인
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ 이 스크립트는 root 권한이 필요합니다.${NC}"
    echo ""
    echo "다음 명령어로 실행하세요:"
    echo "sudo bash scripts/setup_nginx.sh"
    exit 1
fi

echo -e "${GREEN}✅ Root 권한 확인 완료${NC}"
echo ""

# 2. Nginx 설치 확인
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}❌ Nginx가 설치되어 있지 않습니다.${NC}"
    echo ""
    echo "Nginx 설치:"
    echo "sudo apt update && sudo apt install nginx -y"
    exit 1
fi

echo -e "${GREEN}✅ Nginx 설치 확인 완료${NC}"
echo ""

# 3. Nginx 설정 파일 찾기
echo "Nginx 설정 파일 검색 중..."

CONFIG_FILE=""

# 가능한 위치들
POSSIBLE_LOCATIONS=(
    "/etc/nginx/sites-available/n8n.softline.co.kr"
    "/etc/nginx/conf.d/n8n.softline.co.kr.conf"
    "/etc/nginx/sites-available/softline.co.kr"
    "/etc/nginx/conf.d/softline.co.kr.conf"
    "/etc/nginx/sites-available/default"
)

for loc in "${POSSIBLE_LOCATIONS[@]}"; do
    if [ -f "$loc" ]; then
        if grep -q "n8n.softline.co.kr" "$loc" 2>/dev/null; then
            CONFIG_FILE="$loc"
            break
        fi
    fi
done

if [ -z "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}⚠️  기존 설정 파일을 찾을 수 없습니다.${NC}"
    echo ""
    echo "수동으로 설정 파일을 지정하세요:"
    read -p "Nginx 설정 파일 경로: " CONFIG_FILE

    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}❌ 파일이 존재하지 않습니다: $CONFIG_FILE${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ 설정 파일 찾음: $CONFIG_FILE${NC}"
echo ""

# 4. 백업 생성
BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "백업 생성 중..."
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✅ 백업 완료: $BACKUP_FILE${NC}"
echo ""

# 5. Memory Garden 설정이 이미 있는지 확인
if grep -q "location /kakao/" "$CONFIG_FILE"; then
    echo -e "${YELLOW}⚠️  /kakao/ 경로가 이미 설정되어 있습니다.${NC}"
    echo ""
    read -p "덮어쓰시겠습니까? (y/N): " OVERWRITE

    if [ "$OVERWRITE" != "y" ] && [ "$OVERWRITE" != "Y" ]; then
        echo "설정을 건너뜁니다."
        exit 0
    fi

    # 기존 설정 제거
    sed -i '/# Memory Garden API/,/^    }/d' "$CONFIG_FILE"
fi

# 6. 새 설정 추가
echo "Memory Garden API 설정 추가 중..."

# 마지막 } 앞에 설정 삽입
TEMP_FILE=$(mktemp)

cat > "$TEMP_FILE" << 'EOF'

    # ============================================
    # Memory Garden API
    # ============================================

    # Memory Garden API 전체
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS
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
EOF

# 마지막 server 블록의 마지막 } 앞에 삽입
awk '/server {/,/^}/ {
    if (/^}/ && !done) {
        while ((getline line < "'$TEMP_FILE'") > 0) {
            print line
        }
        done=1
    }
    print
}
!/server {/,/^}/ {print}' "$CONFIG_FILE" > "${CONFIG_FILE}.new"

mv "${CONFIG_FILE}.new" "$CONFIG_FILE"
rm "$TEMP_FILE"

echo -e "${GREEN}✅ 설정 추가 완료${NC}"
echo ""

# 7. Nginx 설정 테스트
echo "Nginx 설정 테스트 중..."
if nginx -t; then
    echo -e "${GREEN}✅ Nginx 설정 문법 확인 완료${NC}"
else
    echo -e "${RED}❌ Nginx 설정 오류!${NC}"
    echo ""
    echo "백업 복원:"
    echo "sudo cp $BACKUP_FILE $CONFIG_FILE"
    exit 1
fi
echo ""

# 8. Nginx 재시작
echo "Nginx 재시작 중..."
if systemctl reload nginx; then
    echo -e "${GREEN}✅ Nginx 재시작 완료${NC}"
else
    echo -e "${RED}❌ Nginx 재시작 실패!${NC}"
    echo ""
    echo "백업 복원:"
    echo "sudo cp $BACKUP_FILE $CONFIG_FILE"
    echo "sudo systemctl reload nginx"
    exit 1
fi
echo ""

# 9. 테스트
echo "============================================================"
echo "설정 완료!"
echo "============================================================"
echo ""
echo -e "${GREEN}✅ 다음 URL로 접근 가능합니다:${NC}"
echo ""
echo "  • Webhook 테스트:"
echo "    https://n8n.softline.co.kr/kakao/webhook/test"
echo ""
echo "  • API 문서:"
echo "    https://n8n.softline.co.kr/docs"
echo ""
echo "  • Kakao Webhook URL (카카오 채널 설정에 입력):"
echo "    https://n8n.softline.co.kr/kakao/webhook"
echo ""

# 10. 테스트 실행
echo "자동 테스트 실행 중..."
echo ""

sleep 2

if curl -s -f https://n8n.softline.co.kr/kakao/webhook/test > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Webhook 엔드포인트 테스트 성공!${NC}"
else
    echo -e "${YELLOW}⚠️  Webhook 엔드포인트 테스트 실패${NC}"
    echo ""
    echo "FastAPI 서버가 실행 중인지 확인하세요:"
    echo "ps aux | grep 'uvicorn api.main:app'"
    echo ""
    echo "서버가 실행 중이 아니면:"
    echo "cd /home/admin/docker/MemoryGardenAI"
    echo "source .venv/bin/activate"
    echo "uvicorn api.main:app --host 0.0.0.0 --port 8000 &"
fi

echo ""
echo "============================================================"
echo "다음 단계:"
echo "============================================================"
echo ""
echo "1. FastAPI 서버 실행 확인:"
echo "   ps aux | grep uvicorn"
echo ""
echo "2. 카카오 비즈니스 센터에서 Webhook URL 설정:"
echo "   https://business.kakao.com"
echo "   → Memory Garden 채널"
echo "   → 관리 > 상세 설정 > Webhook URL"
echo "   → https://n8n.softline.co.kr/kakao/webhook 입력"
echo ""
echo "3. 카카오톡에서 채널에 메시지 전송:"
echo "   '안녕하세요' → user_key 자동 수집!"
echo ""
echo "4. FastAPI 로그 확인:"
echo "   sudo journalctl -u memgarden.service -f"
echo ""
echo "============================================================"
echo ""
