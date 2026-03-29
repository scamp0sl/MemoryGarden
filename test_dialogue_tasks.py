"""
DialogueTasks 간단 검증 스크립트

pytest 없이 tasks.dialogue의 기본 기능을 테스트합니다.
"""

import asyncio
from datetime import datetime
from tasks.dialogue import (
    DialogueTaskManager,
    extract_and_store_memories,
    update_analysis_data,
    update_garden_status,
    process_post_conversation_tasks,
    generate_weekly_report,
    generate_monthly_report,
    cleanup_old_sessions,
    TASK_TYPE_MEMORY_EXTRACTION,
    TASK_TYPE_WEEKLY_REPORT
)


async def test_task_manager():
    """TaskManager 테스트"""
    print("=" * 60)
    print("DialogueTaskManager 테스트")
    print("=" * 60)

    try:
        # 초기화
        manager = DialogueTaskManager()
        print("✅ DialogueTaskManager 초기화 완료")

        # 태스크 큐에 추가
        task_id = await manager.enqueue_task(
            task_type=TASK_TYPE_MEMORY_EXTRACTION,
            task_data={
                "user_id": "test_user",
                "session_id": "test_session",
                "message": "테스트 메시지",
                "response": "테스트 응답",
                "context": {}
            },
            priority=1
        )
        print(f"✅ 태스크 큐에 추가: {task_id}")

        # 태스크 상태 조회
        status = await manager.get_task_status(task_id)
        print(f"✅ 태스크 상태: {status}")

        # 태스크 상태 업데이트
        await manager.update_task_status(
            task_id,
            "completed",
            {"result": "success"}
        )
        print("✅ 태스크 상태 업데이트 완료")

        return True

    except Exception as e:
        print(f"❌ TaskManager 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_extraction():
    """기억 추출 태스크 테스트"""
    print("\n" + "=" * 60)
    print("기억 추출 태스크 테스트")
    print("=" * 60)

    try:
        result = await extract_and_store_memories(
            user_id="test_user",
            session_id="test_session",
            message="오늘 점심에 김치찌개를 먹었어요",
            response="김치찌개 맛있게 드셨군요!",
            context={"conversation_count": 10}
        )

        print(f"추출된 사실: {result['extracted_facts']}개")
        print(f"저장된 메모리: {result['stored_memories']}개")
        print(f"처리 시간: {result['processing_time_ms']:.2f}ms")
        print("✅ 기억 추출 테스트 완료")

        return True

    except Exception as e:
        print(f"❌ 기억 추출 테스트 실패: {e}")
        return False


async def test_analysis_update():
    """분석 데이터 업데이트 테스트"""
    print("\n" + "=" * 60)
    print("분석 데이터 업데이트 테스트")
    print("=" * 60)

    try:
        result = await update_analysis_data(
            user_id="test_user",
            session_id="test_session",
            analysis_result={
                "mcdi_score": 78.5,
                "scores": {
                    "LR": 80.0,
                    "SD": 82.0,
                    "NC": 75.0,
                    "TO": 77.0,
                    "ER": 72.0,
                    "RT": 74.0
                },
                "risk_level": "GREEN"
            }
        )

        print(f"업데이트 완료: {result['updated']}")
        print(f"MCDI 점수: {result['mcdi_score']}")
        print(f"위험도: {result['risk_level']}")
        print("✅ 분석 업데이트 테스트 완료")

        return True

    except Exception as e:
        print(f"❌ 분석 업데이트 테스트 실패: {e}")
        return False


async def test_garden_update():
    """정원 상태 업데이트 테스트"""
    print("\n" + "=" * 60)
    print("정원 상태 업데이트 테스트")
    print("=" * 60)

    try:
        result = await update_garden_status(
            user_id="test_user",
            session_id="test_session",
            conversation_count=50
        )

        print(f"추가된 꽃: {result['flowers_added']}개")
        print(f"추가된 나비: {result['butterflies_added']}개")
        print(f"레벨업: {result['level_up']}")
        print(f"획득 뱃지: {result['badges_earned']}")
        print("✅ 정원 업데이트 테스트 완료")

        return True

    except Exception as e:
        print(f"❌ 정원 업데이트 테스트 실패: {e}")
        return False


async def test_post_conversation_tasks():
    """대화 후 통합 태스크 테스트"""
    print("\n" + "=" * 60)
    print("대화 후 통합 태스크 테스트")
    print("=" * 60)

    try:
        result = await process_post_conversation_tasks(
            user_id="test_user",
            session_id="test_session",
            message="오늘 점심에 김치찌개를 먹었어요",
            response="김치찌개 맛있게 드셨군요!",
            analysis_result={
                "mcdi_score": 78.5,
                "risk_level": "GREEN"
            },
            context={"conversation_count": 50}
        )

        print("\n결과:")
        print(f"  기억 추출: {result['memory_result']}")
        print(f"  분석 업데이트: {result['analysis_result']}")
        print(f"  정원 업데이트: {result['garden_result']}")
        print(f"  총 처리 시간: {result['total_processing_time_ms']:.2f}ms")
        print("✅ 통합 태스크 테스트 완료")

        return True

    except Exception as e:
        print(f"❌ 통합 태스크 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_weekly_report():
    """주간 리포트 생성 테스트"""
    print("\n" + "=" * 60)
    print("주간 리포트 생성 테스트")
    print("=" * 60)

    try:
        report = await generate_weekly_report("test_user")

        print(f"\n리포트 ID: {report['report_id']}")
        print(f"기간: {report['period']}")
        print(f"MCDI 평균: {report['mcdi_trend']['average']}")
        print(f"위험도: {report['risk_summary']['current_level']}")
        print(f"총 대화 수: {report['engagement']['total_conversations']}")
        print(f"연속 일수: {report['engagement']['consecutive_days']}")
        print(f"추가된 꽃: {report['garden_growth']['flowers_added']}개")
        print("✅ 주간 리포트 테스트 완료")

        return True

    except Exception as e:
        print(f"❌ 주간 리포트 테스트 실패: {e}")
        return False


async def test_monthly_report():
    """월간 리포트 생성 테스트"""
    print("\n" + "=" * 60)
    print("월간 리포트 생성 테스트")
    print("=" * 60)

    try:
        report = await generate_monthly_report("test_user")

        print(f"\n리포트 ID: {report['report_id']}")
        print(f"기간: {report['period']}")
        print(f"MCDI 평균: {report['mcdi_analysis']['average']}")
        print(f"추세: {report['mcdi_analysis']['trend']}")
        print(f"총 대화 수: {report['engagement_summary']['total_conversations']}")
        print(f"최대 연속 일수: {report['engagement_summary']['consecutive_days_max']}")
        print(f"현재 레벨: {report['garden_milestones']['current_level']}")
        print(f"획득 뱃지: {report['garden_milestones']['badges_earned']}")
        print("✅ 월간 리포트 테스트 완료")

        return True

    except Exception as e:
        print(f"❌ 월간 리포트 테스트 실패: {e}")
        return False


async def test_session_cleanup():
    """세션 정리 테스크 테스트"""
    print("\n" + "=" * 60)
    print("세션 정리 태스크 테스트")
    print("=" * 60)

    try:
        result = await cleanup_old_sessions(days_to_keep=90)

        print(f"아카이브된 세션: {result['sessions_archived']}개")
        print(f"삭제된 Redis 키: {result['redis_keys_deleted']}개")
        print(f"기준 날짜: {result['cutoff_date']}")
        print("✅ 세션 정리 테스트 완료")

        return True

    except Exception as e:
        print(f"❌ 세션 정리 테스트 실패: {e}")
        return False


async def main():
    """메인 테스트 실행"""
    results = []

    # 개별 태스크 테스트
    results.append(await test_task_manager())
    results.append(await test_memory_extraction())
    results.append(await test_analysis_update())
    results.append(await test_garden_update())

    # 통합 태스크 테스트
    results.append(await test_post_conversation_tasks())

    # 배치 태스크 테스트
    results.append(await test_weekly_report())
    results.append(await test_monthly_report())
    results.append(await test_session_cleanup())

    # 결과 요약
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 모든 테스트 성공! ({passed}/{total})")
    else:
        print(f"⚠️  일부 테스트 실패: {passed}/{total} 통과")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
