"""
베타 테스트 사용자 초기화 스크립트

실제 카카오 채널/OAuth 사용자의 모든 데이터를 삭제합니다.
테스트용 더미 사용자(test_kakao_123, web_*)는 유지합니다.

사용법:
    python scripts/reset_beta_users.py [--dry-run] [--keep-user USER_ID]

옵션:
    --dry-run        실제 삭제 없이 대상만 출력
    --keep-user ID   특정 UUID의 사용자는 유지 (반복 가능)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select, delete
from database.postgres import AsyncSessionLocal
from database.models import User

# ============================================
# 유지할 더미/테스트 사용자 kakao_id 패턴
# ============================================
KEEP_KAKAO_IDS = {
    "test_kakao_123",  # 고정 테스트 사용자
}
KEEP_KAKAO_ID_PREFIXES = [
    "web_",             # 웹 테스트 사용자
    "ch_test_",         # 채널 테스트 사용자
]


async def reset_beta_users(dry_run: bool = False, keep_uuids: list = None):
    """
    실제 베타 사용자 데이터 삭제

    Args:
        dry_run: True이면 삭제 없이 대상만 출력
        keep_uuids: 유지할 사용자 UUID 목록
    """
    keep_uuids = keep_uuids or []

    async with AsyncSessionLocal() as db:
        # 전체 사용자 조회
        result = await db.execute(
            select(User).order_by(User.created_at)
        )
        all_users = result.scalars().all()

        to_delete = []
        to_keep = []

        for user in all_users:
            kakao_id = user.kakao_id or ""
            uuid_str = str(user.id)

            # 유지 조건 확인
            if kakao_id in KEEP_KAKAO_IDS:
                to_keep.append(user)
                continue
            if any(kakao_id.startswith(p) for p in KEEP_KAKAO_ID_PREFIXES):
                to_keep.append(user)
                continue
            if uuid_str in keep_uuids:
                to_keep.append(user)
                continue

            to_delete.append(user)

        # 결과 출력
        print(f"\n{'='*60}")
        print(f"  베타 사용자 초기화 {'[DRY RUN]' if dry_run else ''}")
        print(f"{'='*60}")
        print(f"\n✅ 유지 대상: {len(to_keep)}명")
        for u in to_keep:
            print(f"   - {u.kakao_id[:30]:<35} day={u.onboarding_day} name={u.garden_name or '-'}")

        print(f"\n❌ 삭제 대상: {len(to_delete)}명")
        for u in to_delete:
            print(f"   - [{str(u.id)[:8]}] {u.kakao_id[:30]:<35} day={u.onboarding_day} name={u.garden_name or '-'}")

        if dry_run:
            print(f"\n⚠️  DRY RUN - 실제 삭제는 수행되지 않습니다.")
            print("   실제 실행: python scripts/reset_beta_users.py")
            return

        if not to_delete:
            print("\n삭제 대상이 없습니다.")
            return

        # 삭제 확인
        print(f"\n⚠️  {len(to_delete)}명의 사용자와 관련 모든 데이터를 삭제합니다.")
        print("   (conversations, analysis_results, garden_status 등 CASCADE 삭제)")
        confirm = input("\n계속하려면 'yes'를 입력하세요: ").strip().lower()
        if confirm != "yes":
            print("취소됨.")
            return

        # UUID 목록 추출
        delete_ids = [u.id for u in to_delete]
        delete_id_strs = [str(uid) for uid in delete_ids]

        # CASCADE DELETE (외래키 CASCADE 설정으로 관련 데이터 자동 삭제)
        await db.execute(
            text("DELETE FROM users WHERE id = ANY(:ids::uuid[])"),
            {"ids": delete_id_strs}
        )
        await db.commit()

        print(f"\n✅ {len(to_delete)}명 삭제 완료")

        # Redis 캐시 정리
        try:
            from database.redis_client import RedisClient
            redis = RedisClient.get_instance()
            deleted_keys = 0
            for uid_str in delete_id_strs:
                keys_to_delete = [
                    f"garden:{uid_str}",
                    f"session:{uid_str}",
                    f"onboarding_day0_waiting:{uid_str}",
                    f"visual_context:{uid_str}",
                    f"category_usage:{uid_str}",
                    f"mcdi_history:{uid_str}",
                ]
                for key in keys_to_delete:
                    n = await redis.delete(key)
                    deleted_keys += n

            print(f"✅ Redis 캐시 정리 완료 ({deleted_keys}개 키 삭제)")
        except Exception as e:
            print(f"⚠️  Redis 정리 실패 (무시): {e}")

        print(f"\n완료! 이제 베타 참여자들에게 채널 URL을 재발송하세요.")
        print(f"채널 URL: https://pf.kakao.com/{os.getenv('KAKAO_CHANNEL_ID', '_tDPzX')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="베타 사용자 초기화")
    parser.add_argument("--dry-run", action="store_true", help="삭제 없이 대상만 출력")
    parser.add_argument("--keep-user", action="append", default=[], metavar="UUID",
                        help="유지할 사용자 UUID (반복 가능)")
    args = parser.parse_args()

    asyncio.run(reset_beta_users(dry_run=args.dry_run, keep_uuids=args.keep_user))
