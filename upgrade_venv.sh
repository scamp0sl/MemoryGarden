#!/bin/bash
# ============================================
# Memory Garden - 가상환경 재생성 스크립트
#
# 최신 버전으로 업그레이드 + 호환성 테스트
# ============================================

set -e  # 에러 발생 시 중단

PROJECT_DIR="/home/admin/docker/MemoryGardenAI"
BACKUP_DIR="$PROJECT_DIR/.backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "============================================"
echo "🚀 Memory Garden 가상환경 업그레이드"
echo "============================================"
echo ""

# ============================================
# Step 1: 백업
# ============================================
echo "📦 Step 1: 기존 환경 백업..."
mkdir -p "$BACKUP_DIR"

if [ -d "$PROJECT_DIR/.venv" ]; then
    echo "  - .venv 백업 중..."
    pip freeze > "$BACKUP_DIR/requirements_old_$TIMESTAMP.txt"
    mv "$PROJECT_DIR/.venv" "$BACKUP_DIR/.venv_$TIMESTAMP"
    echo "  ✅ 백업 완료: $BACKUP_DIR/.venv_$TIMESTAMP"
fi

if [ -d "$PROJECT_DIR/venv" ]; then
    echo "  - venv 제거 중... (미사용)"
    rm -rf "$PROJECT_DIR/venv"
    echo "  ✅ venv 제거 완료"
fi

echo ""

# ============================================
# Step 2: 새 가상환경 생성
# ============================================
echo "🔧 Step 2: 새 가상환경 생성..."
cd "$PROJECT_DIR"
python3.11 -m venv .venv
echo "  ✅ .venv 생성 완료"
echo ""

# ============================================
# Step 3: pip 업그레이드
# ============================================
echo "⬆️  Step 3: pip 업그레이드..."
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
echo "  ✅ pip 업그레이드 완료: $(pip --version)"
echo ""

# ============================================
# Step 4: 의존성 설치
# ============================================
echo "📥 Step 4: 최신 의존성 설치 중..."
echo "  (약 3-5분 소요, 네트워크 속도에 따라 다름)"
pip install -r requirements.txt

# 설치된 버전 저장
pip freeze > "$BACKUP_DIR/requirements_new_$TIMESTAMP.txt"
echo ""

# ============================================
# Step 5: 주요 패키지 버전 확인
# ============================================
echo "📊 Step 5: 설치된 주요 패키지 버전..."
echo ""
echo "  Web Framework:"
python -c "import fastapi; print(f'    - FastAPI: {fastapi.__version__}')"
python -c "import pydantic; print(f'    - Pydantic: {pydantic.__version__}')"
python -c "import uvicorn; print(f'    - Uvicorn: {uvicorn.__version__}')"

echo ""
echo "  Database:"
python -c "import sqlalchemy; print(f'    - SQLAlchemy: {sqlalchemy.__version__}')"
python -c "import asyncpg; print(f'    - asyncpg: {asyncpg.__version__}')"
python -c "import redis; print(f'    - Redis: {redis.__version__}')"

echo ""
echo "  AI/ML:"
python -c "import anthropic; print(f'    - Anthropic: {anthropic.__version__}')"
python -c "import openai; print(f'    - OpenAI: {openai.__version__}')"
python -c "import numpy; print(f'    - NumPy: {numpy.__version__}')"
python -c "import pandas; print(f'    - Pandas: {pandas.__version__}')"

echo ""

# ============================================
# Step 6: Import 테스트
# ============================================
echo "🧪 Step 6: Import 호환성 테스트..."
python -c "
import sys
try:
    # Core imports
    import fastapi
    import pydantic
    import sqlalchemy
    import redis
    import qdrant_client
    import anthropic
    import openai
    import numpy
    import pandas
    import kiwipiepy

    print('  ✅ 모든 핵심 패키지 import 성공!')
except ImportError as e:
    print(f'  ❌ Import 실패: {e}')
    sys.exit(1)
"

echo ""

# ============================================
# Step 7: 호환성 경고
# ============================================
echo "⚠️  Step 7: 호환성 체크 필요 항목..."
echo ""
echo "  다음 파일들을 확인하세요:"
echo "    1. config/settings.py - Pydantic v2 호환성"
echo "    2. database/models.py - SQLAlchemy 2.0 호환성"
echo "    3. api/schemas/*.py - Pydantic v2 BaseModel"
echo ""
echo "  테스트 실행:"
echo "    pytest tests/ -v"
echo ""

# ============================================
# Step 8: 비교 리포트 생성
# ============================================
echo "📄 Step 8: 업그레이드 리포트 생성..."
REPORT_FILE="$BACKUP_DIR/upgrade_report_$TIMESTAMP.txt"

cat > "$REPORT_FILE" << EOF
============================================
Memory Garden 가상환경 업그레이드 리포트
============================================

업그레이드 일시: $TIMESTAMP

[이전 버전]
$(cat "$BACKUP_DIR/requirements_old_$TIMESTAMP.txt" | grep -E "^(fastapi|pydantic|sqlalchemy|numpy|pandas)" || echo "N/A")

[새 버전]
$(cat "$BACKUP_DIR/requirements_new_$TIMESTAMP.txt" | grep -E "^(fastapi|pydantic|sqlalchemy|numpy|pandas)")

[전체 패키지 수]
이전: $(cat "$BACKUP_DIR/requirements_old_$TIMESTAMP.txt" | wc -l)
현재: $(cat "$BACKUP_DIR/requirements_new_$TIMESTAMP.txt" | wc -l)

[백업 위치]
$BACKUP_DIR/.venv_$TIMESTAMP

[복원 방법]
cd $PROJECT_DIR
rm -rf .venv
mv $BACKUP_DIR/.venv_$TIMESTAMP .venv
source .venv/bin/activate

============================================
EOF

echo "  ✅ 리포트 저장: $REPORT_FILE"
echo ""

# ============================================
# 완료
# ============================================
echo "============================================"
echo "✅ 가상환경 업그레이드 완료!"
echo "============================================"
echo ""
echo "📌 다음 단계:"
echo "  1. 코드 호환성 확인:"
echo "     pytest tests/ -v"
echo ""
echo "  2. 개발 서버 실행:"
echo "     uvicorn api.main:app --reload"
echo ""
echo "  3. 문제 발생 시 복원:"
echo "     cat $REPORT_FILE"
echo ""
echo "🎉 Happy Coding!"
