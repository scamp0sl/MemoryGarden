#!/usr/bin/env python3
"""
APScheduler Redis 좀비 잡 정리 스크립트

APScheduler가 사용하는 Redis DB 1에서 value가 null인 좀비 잡 키와
test_user_*, user_001, user_002 형태의 레거시 잡 ID를 정리합니다.

Usage:
    python scripts/cleanup_zombie_jobs.py
"""

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis
from urllib.parse import urlparse


def cleanup_zombie_jobs():
    """Redis DB 1에서 좀비 APScheduler 잡 키 정리"""
    try:
        from config.settings import settings
        redis_url = settings.REDIS_URL
    except Exception:
        redis_url = "redis://localhost:6379"

    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    password = parsed.password or None

    # APScheduler는 DB 1 사용
    r = redis.Redis(host=host, port=port, db=1, password=password, decode_responses=False)

    print(f"Redis 연결: {host}:{port} db=1")
    print("=" * 60)

    # 1. 전체 키 목록 조회
    all_keys = r.keys("*")
    print(f"전체 잡 키 수: {len(all_keys)}")

    zombie_keys = []    # value가 None인 키
    legacy_keys = []    # test_user_*, user_001, user_002 형태 레거시 잡
    removed_count = 0

    for key in all_keys:
        key_str = key.decode("utf-8") if isinstance(key, bytes) else key
        val = r.get(key)

        # value가 None인 좀비 잡
        if val is None:
            zombie_keys.append(key_str)
        else:
            # 레거시 테스트 잡 패턴 체크
            is_legacy = any([
                key_str.startswith("test_user_"),
                key_str.startswith("user_001"),
                key_str.startswith("user_002"),
                key_str.startswith("user_003"),
            ])
            if is_legacy:
                legacy_keys.append(key_str)

    # 2. 좀비 잡 삭제 (value가 None)
    print(f"\n[1] Value-null 좀비 잡: {len(zombie_keys)}개")
    for key in zombie_keys:
        r.delete(key)
        print(f"  🗑️  삭제: {key}")
        removed_count += 1

    # 3. 레거시 테스트 잡 삭제
    print(f"\n[2] 레거시 테스트 잡: {len(legacy_keys)}개")
    for key in legacy_keys:
        r.delete(key)
        print(f"  🗑️  삭제: {key}")
        removed_count += 1

    # 4. 잔여 키 확인
    remaining_keys = r.keys("*")
    print(f"\n{'=' * 60}")
    print(f"✅ 총 {removed_count}개 좀비/레거시 잡 삭제 완료")
    print(f"📋 잔여 잡 수: {len(remaining_keys)}")

    if remaining_keys:
        print("\n[잔여 잡 목록]")
        for key in remaining_keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            print(f"  - {key_str}")

    return removed_count


if __name__ == "__main__":
    removed = cleanup_zombie_jobs()
    print(f"\n완료. 총 {removed}개 제거됨.")
