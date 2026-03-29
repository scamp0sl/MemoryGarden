#!/usr/bin/env python3
"""대화 내역 조회 스크립트

사용자별 대화 내역을 보기 좋게 출력합니다.
"""

import sys
import asyncio
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.append('/home/admin/docker/MemoryGardenAI')

from database.models import User, Conversation, AnalysisResult
from config.settings import settings


async def show_conversations(user_identifier: str = None, limit: int = 50):
    """대화 내역 조회

    Args:
        user_identifier: 사용자 식별자 (이름, kakao_id, 없으면 전체)
        limit: 최대 출력 건수
    """
    # DB 연결
    engine = create_async_session(
        settings.DATABASE_URL.replace("+asyncpg", ""),
        class_=AsyncSession
    )

    async with engine as session:
        if user_identifier:
            # 특정 사용자 검색
            query = select(User).where(
                (User.name.ilike(f"%{user_identifier}%")) |
                (User.kakao_id.ilike(f"%{user_identifier}%"))
            )
            result = await session.execute(query)
            users = result.scalars().all()

            if not users:
                print(f"❌ '{user_identifier}' 사용자를 찾을 수 없습니다.")
                return

            for user in users:
                await print_user_conversations(session, user, limit)
        else:
            # 전체 사용자 목록
            query = select(User).order_by(desc(User.created_at)).limit(10)
            result = await session.execute(query)
            users = result.scalars().all()

            print(f"📋 전체 사용자 ({len(users)}명)\n")
            for user in users:
                await print_user_conversations(session, user, limit)
                print("\n" + "="*80 + "\n")


async def print_user_conversations(session: AsyncSession, user: User, limit: int):
    """사용자별 대화 출력"""
    # 대화 조회
    query = select(Conversation).where(
        Conversation.user_id == user.id
    ).order_by(desc(Conversation.created_at)).limit(limit)

    result = await session.execute(query)
    conversations = result.scalars().all()

    # 분석 결과 조회 (최근)
    analysis_query = select(AnalysisResult).where(
        AnalysisResult.user_id == user.id
    ).order_by(desc(AnalysisResult.created_at)).limit(3)

    analysis_result = await session.execute(analysis_query)
    analyses = analysis_result.scalars().all()

    # 헤더 출력
    print(f"{'='*80}")
    print(f"👤 사용자: {user.name} ({user.kakao_id})")
    print(f"   정원이름: {user.garden_name or '미설정'} | 온보딩: {user.onboarding_day}일차")
    print(f"   마지막 활동: {user.last_interaction_at or '없음'}")
    print(f"{'='*80}")

    if not conversations:
        print("   (대화 내역 없음)")
        return

    print(f"\n💬 최근 대화 {len(conversations)}건\n")

    for i, conv in enumerate(conversations, 1):
        timestamp = conv.created_at.strftime("%Y-%m-%d %H:%M:%S") if conv.created_at else "N/A"

        print(f"{'─'*80}")
        print(f"📅 {timestamp} | 카테고리: {conv.category or '미분류'}")

        # 사용자 메시지
        print(f"\n  👤 사용자:")
        msg = conv.message[:100] + "..." if conv.message and len(conv.message) > 100 else conv.message
        print(f"     {msg or '(없음)'}")

        # AI 응답
        print(f"\n  🤖 AI 응답:")
        resp = conv.response[:150] + "..." if conv.response and len(conv.response) > 150 else conv.response
        print(f"     {resp or '(없음)'}")

        # 성능 메트릭
        if conv.response_latency_ms:
            print(f"\n  ⚡ 응답 시간: {conv.response_latency_ms}ms")

        print()

    # MCDI 분석 결과
    if analyses:
        print(f"\n{'─'*80}")
        print(f"📊 최근 MCDI 분석 ({len(analyses)}건)\n")

        for analysis in analyses:
            timestamp = analysis.created_at.strftime("%m-%d %H:%M") if analysis.created_at else "N/A"
            score = analysis.mcdi_score or 0
            risk = analysis.risk_level or "UNKNOWN"

            # 위험도 색상
            risk_emoji = {
                "GREEN": "🟢",
                "YELLOW": "🟡",
                "ORANGE": "🟠",
                "RED": "🔴"
            }.get(risk, "⚪")

            print(f"   {timestamp} | {risk_emoji} {risk} | MCDI: {score:.1f}")

            if analysis.scores:
                scores = analysis.scores
                print(f"      LR={scores.get('LR', 0):.0f} "
                      f"SD={scores.get('SD', 0):.0f} "
                      f"NC={scores.get('NC', 0):.0f} "
                      f"TO={scores.get('TO', 0):.0f} "
                      f"ER={scores.get('ER', 0):.0f} "
                      f"RT={scores.get('RT', 0):.0f}")


async def list_users():
    """전체 사용자 목록"""
    engine = create_async_session(
        settings.DATABASE_URL.replace("+asyncpg", ""),
        class_=AsyncSession
    )

    async with engine as session:
        query = select(User).order_by(desc(User.created_at))
        result = await session.execute(query)
        users = result.scalars().all()

        print(f"📋 전체 사용자 목록 ({len(users)}명)\n")
        print(f"{'번호':<4} {'이름':<15} {'카카오ID':<20} {'정원이름':<15} {'온보딩':<6} {'마지막활동'}")
        print("─" * 90)

        for i, user in enumerate(users, 1):
            last_active = user.last_interaction_at.strftime("%m-%d %H:%M") if user.last_interaction_at else "없음"
            print(f"{i:<4} {user.name:<15} {user.kakao_id[:20]:<20} "
                  f"{(user.garden_name or '-'):<15} {user.onboarding_day:<6} {last_active}")


async def main():
    """메인"""
    import argparse

    parser = argparse.ArgumentParser(description="대화 내역 조회")
    parser.add_argument("user", nargs="?", help="사용자 이름 또는 ID (없으면 전체)")
    parser.add_argument("-l", "--list", action="store_true", help="사용자 목록만 출력")
    parser.add_argument("-n", "--limit", type=int, default=50, help="최대 출력 건수")

    args = parser.parse_args()

    if args.list:
        await list_users()
    else:
        await show_conversations(args.user, args.limit)


if __name__ == "__main__":
    asyncio.run(main())
