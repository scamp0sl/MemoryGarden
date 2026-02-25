"""
Memory Garden API Server
메인 진입점 (uvicorn)

Usage:
    # 개발 모드 (Hot Reload)
    python main.py

    # 프로덕션 모드
    python main.py --production

    # 포트 지정
    python main.py --port 8080

Author: Memory Garden Team
Created: 2025-02-10
"""

import sys
import argparse
import uvicorn

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_args():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="Memory Garden API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 개발 모드 (Hot Reload)
  python main.py

  # 프로덕션 모드
  python main.py --production

  # 포트 지정
  python main.py --port 8080

  # 워커 수 지정 (프로덕션)
  python main.py --production --workers 4
        """
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="바인딩할 호스트 (기본: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="바인딩할 포트 (기본: 8000)"
    )
    
    parser.add_argument(
        "--production",
        action="store_true",
        help="프로덕션 모드 실행 (Hot Reload 비활성화)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="워커 프로세스 수 (프로덕션 모드만, 기본: 1)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="로그 레벨 (기본: info)"
    )
    
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_args()
    
    # 프로덕션 모드 체크
    is_production = args.production or settings.APP_ENV == "production"
    
    # 서버 설정
    uvicorn_config = {
        "app": "api.main:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
    }
    
    if is_production:
        # 프로덕션 설정
        logger.info("=" * 60)
        logger.info("🚀 Starting Memory Garden API (Production Mode)")
        logger.info("=" * 60)
        logger.info(f"   Host: {args.host}")
        logger.info(f"   Port: {args.port}")
        logger.info(f"   Workers: {args.workers}")
        logger.info(f"   Log Level: {args.log_level}")
        logger.info("=" * 60)
        
        uvicorn_config.update({
            "workers": args.workers,
            "reload": False,
            "access_log": True,
            "use_colors": True,
        })
    else:
        # 개발 설정
        logger.info("=" * 60)
        logger.info("🔧 Starting Memory Garden API (Development Mode)")
        logger.info("=" * 60)
        logger.info(f"   Host: {args.host}")
        logger.info(f"   Port: {args.port}")
        logger.info(f"   Hot Reload: ✅ Enabled")
        logger.info(f"   Log Level: {args.log_level}")
        logger.info("=" * 60)
        logger.info(f"   API Docs: http://{args.host}:{args.port}/docs")
        logger.info(f"   ReDoc: http://{args.host}:{args.port}/redoc")
        logger.info("=" * 60)
        
        uvicorn_config.update({
            "reload": True,
            "reload_dirs": ["api", "core", "services", "config"],
            "access_log": True,
            "use_colors": True,
        })
    
    try:
        # Uvicorn 서버 실행
        uvicorn.run(**uvicorn_config)
        
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("🛑 Server stopped by user")
        logger.info("=" * 60)
        sys.exit(0)
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Failed to start server: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
