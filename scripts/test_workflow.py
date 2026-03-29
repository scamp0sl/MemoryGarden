#!/usr/bin/env python3
"""
Workflow 모듈 테스트 스크립트

Pipeline, SessionWorkflow 테스트.

Usage:
    python scripts/test_workflow.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.workflow import (
    Pipeline,
    Step,
    PipelineContext,
    create_context,
    SessionWorkflow,
)
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================
# 테스트용 커스텀 Step 클래스들
# ============================================

class DummyStep1(Step):
    """테스트용 더미 단계 1"""

    def __init__(self):
        super().__init__("dummy_step_1", retries=1)

    async def execute(self, context: PipelineContext) -> dict:
        await asyncio.sleep(0.1)  # 시뮬레이션
        context.set("step1_result", "success")
        return {"message": "Step 1 completed"}


class DummyStep2(Step):
    """테스트용 더미 단계 2"""

    def __init__(self):
        super().__init__("dummy_step_2", retries=1)

    async def execute(self, context: PipelineContext) -> dict:
        await asyncio.sleep(0.1)
        step1_result = context.get("step1_result")
        context.set("step2_result", f"processed_{step1_result}")
        return {"message": "Step 2 completed", "previous": step1_result}


class FailingStep(Step):
    """테스트용 실패 단계"""

    def __init__(self, skip_on_error: bool = False):
        super().__init__(
            "failing_step",
            retries=2,
            skip_on_error=skip_on_error
        )

    async def execute(self, context: PipelineContext) -> dict:
        raise Exception("Intentional failure for testing")


class TestPipeline(Pipeline):
    """테스트용 파이프라인"""

    def __init__(self):
        super().__init__("test_pipeline")
        self.add_steps([
            DummyStep1(),
            DummyStep2()
        ])


async def test_pipeline_basic():
    """파이프라인 기본 기능 테스트"""
    print("=" * 60)
    print("🔍 Pipeline Basic Test")
    print("=" * 60)

    print("\n1️⃣ Create Pipeline with 2 Steps")
    try:
        pipeline = TestPipeline()
        print(f"✅ Pipeline created: {pipeline.name}")
        print(f"   - Steps: {len(pipeline.steps)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n2️⃣ Run Pipeline")
    try:
        context = create_context(
            "test_pipeline_1",
            {"input_data": "test"}
        )

        result = await pipeline.run(context)

        print(f"✅ Pipeline executed")
        print(f"   - Status: {result.status.value}")
        print(f"   - Total time: {result.total_execution_time_ms:.2f}ms")
        print(f"   - Steps completed: {len(result.step_results)}")

        # 각 단계 결과
        for step_result in result.step_results:
            print(f"\n   Step '{step_result.step_name}':")
            print(f"      - Status: {step_result.status.value}")
            print(f"      - Time: {step_result.execution_time_ms:.2f}ms")
            print(f"      - Output: {step_result.output}")

        # 컨텍스트 확인
        print(f"\n   Context data:")
        print(f"      - step1_result: {context.get('step1_result')}")
        print(f"      - step2_result: {context.get('step2_result')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    return True


async def test_pipeline_error_handling():
    """파이프라인 에러 핸들링 테스트"""
    print("\n" + "=" * 60)
    print("🔍 Pipeline Error Handling Test")
    print("=" * 60)

    print("\n1️⃣ Test Pipeline with Failing Step (Stop on Error)")
    try:
        pipeline = Pipeline("error_test_1")
        pipeline.add_steps([
            DummyStep1(),
            FailingStep(skip_on_error=False),  # 실패 시 중단
            DummyStep2()  # 실행되지 않음
        ])

        context = create_context("error_test_1", {})
        result = await pipeline.run(context)

        print(f"✅ Pipeline executed with expected failure")
        print(f"   - Status: {result.status.value}")  # FAILED
        print(f"   - Error: {result.error}")
        print(f"   - Steps completed: {sum(1 for sr in result.step_results if sr.status.value == 'completed')}")
        print(f"   - Steps failed: {sum(1 for sr in result.step_results if sr.status.value == 'failed')}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    print("\n2️⃣ Test Pipeline with Failing Step (Skip on Error)")
    try:
        pipeline = Pipeline("error_test_2")
        pipeline.add_steps([
            DummyStep1(),
            FailingStep(skip_on_error=True),  # 실패해도 계속
            DummyStep2()  # 실행됨
        ])

        context = create_context("error_test_2", {})
        result = await pipeline.run(context)

        print(f"✅ Pipeline executed with skipped failure")
        print(f"   - Status: {result.status.value}")  # COMPLETED
        print(f"   - Steps completed: {sum(1 for sr in result.step_results if sr.status.value == 'completed')}")
        print(f"   - Steps failed: {sum(1 for sr in result.step_results if sr.status.value == 'failed')}")
        print(f"   - Steps skipped: {sum(1 for sr in result.step_results if sr.status.value == 'skipped')}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def test_session_workflow():
    """SessionWorkflow 테스트"""
    print("\n" + "=" * 60)
    print("🔍 SessionWorkflow Test")
    print("=" * 60)

    workflow = SessionWorkflow()

    print("\n1️⃣ Process Single Message")
    try:
        result = await workflow.process_message(
            user_id="test_user_workflow",
            message="오늘 점심에 된장찌개 먹었어요",
            message_type="text"
        )

        print(f"✅ Message processed")
        print(f"   - Success: {result['success']}")
        print(f"   - Response: {result.get('response', '')[:100]}...")
        print(f"   - Session ID: {result.get('session_id')}")
        print(f"   - MCDI Score: {result.get('mcdi_score')}")
        print(f"   - Risk Level: {result.get('risk_level')}")
        print(f"   - Execution time: {result.get('execution_time_ms', 0):.2f}ms")

        if result.get('garden_status'):
            garden = result['garden_status']
            print(f"\n   Garden Status:")
            print(f"      - Flowers: {garden.get('flower_count')}")
            print(f"      - Level: {garden.get('garden_level')}")
            print(f"      - Weather: {garden.get('weather')}")

        if result.get('achievements'):
            print(f"\n   Achievements: {result['achievements']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n2️⃣ Process Multiple Messages (Conversation)")
    try:
        messages = [
            "딸이 오늘 전화했어요",
            "고향은 부산이에요",
            "좋아하는 음식은 된장찌개예요"
        ]

        for i, msg in enumerate(messages, 1):
            print(f"\n   Message {i}: {msg}")
            result = await workflow.process_message(
                user_id="test_user_workflow",
                message=msg
            )

            if result['success']:
                print(f"      ✅ Response: {result['response'][:80]}...")
                print(f"      - Flowers: {result.get('garden_status', {}).get('flower_count')}")
            else:
                print(f"      ❌ Error: {result.get('error')}")

            await asyncio.sleep(0.5)  # 대화 간 간격

        print(f"\n   ✅ Conversation completed ({len(messages)} messages)")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def test_workflow_performance():
    """워크플로우 성능 테스트"""
    print("\n" + "=" * 60)
    print("🔍 Workflow Performance Test")
    print("=" * 60)

    workflow = SessionWorkflow()

    print("\n1️⃣ Process 10 Messages (Performance)")
    try:
        start_time = asyncio.get_event_loop().time()

        for i in range(10):
            result = await workflow.process_message(
                user_id=f"perf_test_user_{i}",
                message=f"테스트 메시지 {i}"
            )

            if not result['success']:
                print(f"   ⚠️ Message {i} failed: {result.get('error')}")

        end_time = asyncio.get_event_loop().time()
        total_time = (end_time - start_time) * 1000

        print(f"✅ Performance test completed")
        print(f"   - Total messages: 10")
        print(f"   - Total time: {total_time:.2f}ms")
        print(f"   - Average per message: {total_time / 10:.2f}ms")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def test_integration():
    """통합 테스트 (전체 플로우)"""
    print("\n" + "=" * 60)
    print("🔍 Integration Test (Full Flow)")
    print("=" * 60)

    workflow = SessionWorkflow()

    print("\n1️⃣ Simulate Real Conversation Session")
    try:
        user_id = "integration_test_user"

        # 온보딩 대화
        onboarding_messages = [
            ("이름은 홍길동이에요", "introduce"),
            ("딸 이름은 수진이에요", "family"),
            ("고향은 부산이에요", "hometown"),
        ]

        for msg, topic in onboarding_messages:
            result = await workflow.process_message(
                user_id=user_id,
                message=msg
            )

            print(f"   {topic}: {msg}")
            print(f"      → {result['response'][:60]}...")

            await asyncio.sleep(0.3)

        # 일상 대화
        daily_messages = [
            "오늘 점심에 된장찌개 먹었어요",
            "딸이 전화했어요",
            "날씨가 좋네요",
        ]

        print(f"\n2️⃣ Daily Conversations")
        for msg in daily_messages:
            result = await workflow.process_message(
                user_id=user_id,
                message=msg
            )

            print(f"   User: {msg}")
            print(f"      → {result['response'][:60]}...")
            print(f"      - Flowers: {result.get('garden_status', {}).get('flower_count')}")

            await asyncio.sleep(0.3)

        print(f"\n   ✅ Integration test completed")
        print(f"   - Total messages: {len(onboarding_messages) + len(daily_messages)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    return True


async def main():
    """메인 테스트 실행"""
    print("\n")
    print("=" * 60)
    print("🚀 Workflow Test Suite")
    print("=" * 60)

    try:
        # 1. Pipeline 기본 테스트
        basic_success = await test_pipeline_basic()

        # 2. Pipeline 에러 핸들링 테스트
        error_success = await test_pipeline_error_handling()

        # 3. SessionWorkflow 테스트
        session_success = await test_session_workflow()

        # 4. 성능 테스트
        perf_success = await test_workflow_performance()

        # 5. 통합 테스트
        integration_success = await test_integration()

        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"  Pipeline Basic: {'✅ PASS' if basic_success else '❌ FAIL'}")
        print(f"  Pipeline Error Handling: {'✅ PASS' if error_success else '❌ FAIL'}")
        print(f"  SessionWorkflow: {'✅ PASS' if session_success else '❌ FAIL'}")
        print(f"  Performance: {'✅ PASS' if perf_success else '❌ FAIL'}")
        print(f"  Integration Test: {'✅ PASS' if integration_success else '❌ FAIL'}")
        print("=" * 60)

        all_success = all([
            basic_success,
            error_success,
            session_success,
            perf_success,
            integration_success
        ])

        if all_success:
            print("\n✅ All tests passed!")
            print("\n📌 Next steps:")
            print("   1. Integrate with FastAPI endpoints")
            print("   2. Add Kakao webhook handler")
            print("   3. Implement full MCDI calculation (6 metrics)")
            print("   4. Connect to actual databases (PostgreSQL, TimescaleDB)")
            print("=" * 60)
            return True
        else:
            print("\n⚠️  Some tests failed. Check logs for details.")
            return False

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
