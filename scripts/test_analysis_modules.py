#!/usr/bin/env python3
"""
Analysis 모듈 테스트 스크립트

EmotionAnalyzer, GardenMapper, ReportGenerator 테스트.

Usage:
    python scripts/test_analysis_modules.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.analysis import (
    EmotionAnalyzer,
    GardenMapper,
    ReportGenerator,
    EmotionTrend,
    ReportType,
)
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_emotion_analyzer():
    """EmotionAnalyzer 테스트"""
    print("=" * 60)
    print("🔍 EmotionAnalyzer Test")
    print("=" * 60)

    analyzer = EmotionAnalyzer()

    # 테스트 감정 이력 (1주일간)
    emotion_history = [
        {"emotion": "joy", "intensity": 0.8, "timestamp": (datetime.now() - timedelta(days=6)).isoformat()},
        {"emotion": "joy", "intensity": 0.7, "timestamp": (datetime.now() - timedelta(days=5)).isoformat()},
        {"emotion": "neutral", "intensity": 0.5, "timestamp": (datetime.now() - timedelta(days=4)).isoformat()},
        {"emotion": "sadness", "intensity": 0.6, "timestamp": (datetime.now() - timedelta(days=3)).isoformat()},
        {"emotion": "joy", "intensity": 0.9, "timestamp": (datetime.now() - timedelta(days=2)).isoformat()},
        {"emotion": "joy", "intensity": 0.8, "timestamp": (datetime.now() - timedelta(days=1)).isoformat()},
        {"emotion": "joy", "intensity": 0.85, "timestamp": datetime.now().isoformat()},
    ]

    print("\n1️⃣ Analyze Trend (Weekly)")
    try:
        result = await analyzer.analyze_trend(
            user_id="test_user_emotion",
            emotion_history=emotion_history,
            period="weekly"
        )

        print(f"✅ Trend analysis completed")
        print(f"   - Dominant emotion: {result.dominant_emotion}")
        print(f"   - Trend: {result.trend.value}")
        print(f"   - Pattern: {result.pattern.value}")
        print(f"   - Volatility: {result.volatility:.3f}")
        print(f"   - Positive ratio: {result.positive_ratio:.2%}")
        print(f"   - Negative ratio: {result.negative_ratio:.2%}")

        print("\n   📊 Emotion Distribution:")
        for emotion, ratio in result.emotion_distribution.items():
            print(f"      {emotion}: {ratio:.2%}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n2️⃣ Compare Periods")
    try:
        # 이전 주 데이터
        previous_history = [
            {"emotion": "neutral", "intensity": 0.5, "timestamp": (datetime.now() - timedelta(days=13)).isoformat()},
            {"emotion": "sadness", "intensity": 0.6, "timestamp": (datetime.now() - timedelta(days=12)).isoformat()},
            {"emotion": "neutral", "intensity": 0.5, "timestamp": (datetime.now() - timedelta(days=11)).isoformat()},
            {"emotion": "sadness", "intensity": 0.7, "timestamp": (datetime.now() - timedelta(days=10)).isoformat()},
            {"emotion": "neutral", "intensity": 0.5, "timestamp": (datetime.now() - timedelta(days=9)).isoformat()},
            {"emotion": "sadness", "intensity": 0.6, "timestamp": (datetime.now() - timedelta(days=8)).isoformat()},
            {"emotion": "neutral", "intensity": 0.5, "timestamp": (datetime.now() - timedelta(days=7)).isoformat()},
        ]

        comparison = await analyzer.compare_periods(
            user_id="test_user_emotion",
            period1_history=previous_history,
            period2_history=emotion_history
        )

        print(f"✅ Period comparison completed")
        print(f"   - Change: {comparison['change']}")
        print(f"   - Positive change: {comparison['positive_change']:.2%}")
        print(f"   - Negative change: {comparison['negative_change']:.2%}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def test_garden_mapper():
    """GardenMapper 테스트"""
    print("\n" + "=" * 60)
    print("🔍 GardenMapper Test")
    print("=" * 60)

    mapper = GardenMapper()
    test_user_id = "test_user_garden"

    print("\n1️⃣ Get Initial Garden Status")
    try:
        status = await mapper.get_garden_status(test_user_id)

        print(f"✅ Initial status retrieved")
        print(f"   - Flower count: {status.flower_count}")
        print(f"   - Butterfly count: {status.butterfly_count}")
        print(f"   - Garden level: {status.garden_level}")
        print(f"   - Weather: {status.weather.value}")
        print(f"   - Status message: {status.status_message}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n2️⃣ Update Garden Status (First Conversation)")
    try:
        update = await mapper.update_garden_status(
            user_id=test_user_id,
            mcdi_score=75.0,
            risk_level="GREEN"
        )

        print(f"✅ Garden status updated")
        print(f"   - New flower count: {update.current_status.flower_count}")
        print(f"   - Consecutive days: {update.current_status.consecutive_days}")
        print(f"   - Level up: {update.level_up}")
        print(f"   - Achievements: {update.achievements_unlocked}")

        if update.current_status.achievement_message:
            print(f"   - Achievement message: {update.current_status.achievement_message}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n3️⃣ Simulate Multiple Days")
    try:
        # 7일 연속 대화 시뮬레이션
        for day in range(1, 8):
            update = await mapper.update_garden_status(
                user_id=test_user_id,
                mcdi_score=75.0 - day * 0.5,  # 점수 약간씩 감소
                risk_level="GREEN"
            )

            if day in [3, 7]:  # 3일차, 7일차에 특별 출력
                print(f"   Day {day}:")
                print(f"      - Flowers: {update.current_status.flower_count}")
                print(f"      - Butterflies: {update.current_status.butterfly_count}")
                print(f"      - Level: {update.current_status.garden_level}")
                print(f"      - Consecutive days: {update.current_status.consecutive_days}")

                if update.achievements_unlocked:
                    print(f"      - Unlocked: {update.achievements_unlocked}")

        print(f"\n   ✅ 7-day simulation completed")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n4️⃣ Test Different Risk Levels")
    try:
        risk_levels = ["GREEN", "YELLOW", "ORANGE", "RED"]

        for risk in risk_levels:
            update = await mapper.update_garden_status(
                user_id=f"test_user_{risk}",
                mcdi_score=80 - risk_levels.index(risk) * 20,
                risk_level=risk
            )

            print(f"   {risk}:")
            print(f"      - Weather: {update.current_status.weather.value}")
            print(f"      - Message: {update.current_status.status_message}")

        print(f"\n   ✅ Risk level mapping verified")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def test_report_generator():
    """ReportGenerator 테스트"""
    print("\n" + "=" * 60)
    print("🔍 ReportGenerator Test")
    print("=" * 60)

    generator = ReportGenerator()
    test_user_id = "test_user_report"

    # 테스트 데이터 준비 (정원 상태 생성)
    mapper = GardenMapper()
    for _ in range(5):
        await mapper.update_garden_status(
            user_id=test_user_id,
            mcdi_score=75.0,
            risk_level="GREEN"
        )

    print("\n1️⃣ Generate Weekly Report (Guardian)")
    try:
        report = await generator.generate_weekly_report(
            user_id=test_user_id,
            user_name="홍길동",
            report_type=ReportType.GUARDIAN
        )

        print(f"✅ Weekly report generated")
        print(f"   - Period: {report.period_start.date()} ~ {report.period_end.date()}")
        print(f"   - MCDI average: {report.cognitive_metrics.mcdi_average}")
        print(f"   - MCDI trend: {report.cognitive_metrics.mcdi_trend}")
        print(f"   - Total conversations: {report.engagement_metrics.total_conversations}")
        print(f"   - Consecutive days: {report.engagement_metrics.consecutive_days}")
        print(f"   - Current risk: {report.current_risk_level}")

        if report.observations:
            print("\n   📋 Observations:")
            for obs in report.observations[:3]:
                print(f"      - {obs}")

        if report.concerns:
            print("\n   ⚠️ Concerns:")
            for concern in report.concerns:
                print(f"      - {concern}")

        if report.recommendations:
            print("\n   💡 Recommendations:")
            for rec in report.recommendations[:3]:
                print(f"      - {rec}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n2️⃣ Generate Weekly Report (Clinical)")
    try:
        report = await generator.generate_weekly_report(
            user_id=test_user_id,
            user_name="홍길동",
            report_type=ReportType.CLINICAL
        )

        print(f"✅ Clinical report generated")
        print(f"   - Report type: {report.report_type.value}")
        print(f"   - Risk level: {report.current_risk_level}")

        if report.recommendations:
            print("\n   💡 Clinical Recommendations:")
            for rec in report.recommendations[:3]:
                print(f"      - {rec}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n3️⃣ Generate Monthly Report")
    try:
        report = await generator.generate_monthly_report(
            user_id=test_user_id,
            user_name="홍길동",
            report_type=ReportType.CLINICAL
        )

        print(f"✅ Monthly report generated")
        print(f"   - Period: {report.period_start.date()} ~ {report.period_end.date()}")
        print(f"   - Weekly summaries included: {len(report.weekly_summaries)}")
        print(f"   - MCDI average: {report.cognitive_metrics.mcdi_average}")
        print(f"   - Total conversations: {report.engagement_metrics.total_conversations}")

        if report.detailed_observations:
            print(f"\n   📝 Detailed Observations (preview):")
            lines = report.detailed_observations.split('\n')[:5]
            for line in lines:
                print(f"      {line}")

        if report.medical_recommendations:
            print(f"\n   🏥 Medical Recommendations:")
            for rec in report.medical_recommendations:
                print(f"      - {rec}")

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

    test_user_id = "test_user_integration"

    # 1. 정원 초기화
    mapper = GardenMapper()

    print("\n1️⃣ Simulate 30 Days of Conversations")
    try:
        for day in range(1, 31):
            # 하루 2~3회 대화
            for _ in range(2):
                mcdi_score = 75.0 + np.random.normal(0, 5)  # 정규분포
                risk_level = "GREEN" if mcdi_score >= 70 else "YELLOW"

                await mapper.update_garden_status(
                    user_id=test_user_id,
                    mcdi_score=mcdi_score,
                    risk_level=risk_level
                )

        print(f"   ✅ 30 days simulated (60 conversations)")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. 최종 정원 상태 확인
    print("\n2️⃣ Final Garden Status")
    try:
        garden_status = await mapper.get_garden_status(test_user_id)

        print(f"   - Flowers: {garden_status.flower_count}")
        print(f"   - Butterflies: {garden_status.butterfly_count}")
        print(f"   - Level: {garden_status.garden_level}")
        print(f"   - Consecutive days: {garden_status.consecutive_days}")
        print(f"   - Season badge: {garden_status.season_badge}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # 3. 월간 리포트 생성
    print("\n3️⃣ Generate Final Monthly Report")
    try:
        generator = ReportGenerator()
        report = await generator.generate_monthly_report(
            user_id=test_user_id,
            user_name="테스트사용자",
            report_type=ReportType.GUARDIAN
        )

        print(f"   ✅ Monthly report generated successfully")
        print(f"   - MCDI average: {report.cognitive_metrics.mcdi_average}")
        print(f"   - Total conversations: {report.engagement_metrics.total_conversations}")
        print(f"   - Growth: Level {report.growth_metrics.garden_level}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    return True


async def main():
    """메인 테스트 실행"""
    import numpy as np  # numpy를 여기서 import (integration test에서 사용)

    print("\n")
    print("=" * 60)
    print("🚀 Analysis Modules Test Suite")
    print("=" * 60)

    try:
        # 1. EmotionAnalyzer 테스트
        emotion_success = await test_emotion_analyzer()

        # 2. GardenMapper 테스트
        garden_success = await test_garden_mapper()

        # 3. ReportGenerator 테스트
        report_success = await test_report_generator()

        # 4. 통합 테스트
        integration_success = await test_integration()

        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"  EmotionAnalyzer: {'✅ PASS' if emotion_success else '❌ FAIL'}")
        print(f"  GardenMapper: {'✅ PASS' if garden_success else '❌ FAIL'}")
        print(f"  ReportGenerator: {'✅ PASS' if report_success else '❌ FAIL'}")
        print(f"  Integration Test: {'✅ PASS' if integration_success else '❌ FAIL'}")
        print("=" * 60)

        all_success = all([
            emotion_success,
            garden_success,
            report_success,
            integration_success
        ])

        if all_success:
            print("\n✅ All tests passed!")
            print("\n📌 Next steps:")
            print("   1. Integrate TimescaleDB for emotion/MCDI history")
            print("   2. Integrate PostgreSQL for user data")
            print("   3. Connect to core/workflow/message_processor.py")
            print("   4. Add visualization endpoints to API")
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
