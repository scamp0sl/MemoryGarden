"""
최근 일주일간 대화 품질 분석 스크립트

대화이론 관점에서 다양성, 패턴, 문제점 분석

Author: Memory Garden Team
Created: 2026-03-19
"""

import asyncio
import sys
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import json
import re

# Add project root to path
sys.path.insert(0, "/home/admin/docker/MemoryGardenAI")

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.postgres import AsyncSessionLocal
from database.models import Conversation, AnalysisResult, User
from utils.logger import get_logger

logger = get_logger(__name__)


class ConversationQualityAnalyzer:
    """대화 품질 분석기"""
    
    def __init__(self):
        self.results = {}
        
    async def fetch_recent_conversations(
        self, 
        session: AsyncSession, 
        days: int = 7
    ) -> list:
        """최근 N일간 대화 조회"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(Conversation).where(
            Conversation.created_at >= cutoff_date
        ).order_by(Conversation.created_at.desc())
        
        result = await session.execute(query)
        conversations = result.scalars().all()
        
        logger.info(f"Fetched {len(conversations)} conversations from last {days} days")
        return conversations
    
    async def fetch_analysis_results(
        self,
        session: AsyncSession,
        days: int = 7
    ) -> list:
        """최근 N일간 분석 결과 조회"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(AnalysisResult).where(
            AnalysisResult.created_at >= cutoff_date
        ).order_by(AnalysisResult.created_at.desc())
        
        result = await session.execute(query)
        analysis_results = result.scalars().all()
        
        return analysis_results
    
    def analyze_response_patterns(self, conversations: list) -> dict:
        """응답 패턴 분석"""
        
        # 1. 응답 길이 분석
        response_lengths = []
        for conv in conversations:
            if conv.response:
                response_lengths.append(len(conv.response))
        
        # 2. 자주 사용되는 표현 분석
        common_phrases = Counter()
        common_openings = Counter()
        common_endings = Counter()
        
        # 패턴 정의
        opening_patterns = [
            r'^(그렇군요|아 그렇군요|오|네|아|그래요|정말|와)',
            r'(어서 오세요|반갑습니다|안녕하세요)'
        ]
        
        ending_patterns = [
            r'(어떠세요\?|어때요\?|하세요\?|인가요\?|말씀해주세요|들려주세요)$',
            r'(😊|🌿|🌸|💖|🍃|🌺|💪|✨|🌻)'
        ]
        
        # 단조로운 표현 패턴
        repetitive_patterns = [
            '어떠셨어요?', '어떠세요?', '좋으셨겠네요', '좋으셨겠어요',
            '그렇군요', '아 그렇군요', '네 그렇군요',
            '말씀해주세요', '들려주세요', '이야기해주세요'
        ]
        
        repetitive_count = Counter()
        
        for conv in conversations:
            if not conv.response:
                continue
                
            response = conv.response
            
            # 반복 표현 카운트
            for pattern in repetitive_patterns:
                if pattern in response:
                    repetitive_count[pattern] += 1
            
            # 이모지 사용
            emojis = re.findall(r'[😊🌿🌸💖🍃🌺💪✨🌻🍳🍚🍜🍲📅📆🗓️📞💬💭🏥💊]', response)
            
            # 문장 수
            sentences = len(re.split(r'[.!?]', response))
            
            # 질문 수
            questions = response.count('?')
        
        # 3. 질문 유형 분석
        question_types = {
            '개방형 질문': 0,  # 어떻게, 왜, 무엇을
            '폐쇄형 질문': 0,  # 예/아니오
            '선택형 질문': 0,  # A 또는 B
            '유도형 질문': 0   # ~하지 않으세요?
        }
        
        for conv in conversations:
            if not conv.response:
                continue
            response = conv.response
            
            if re.search(r'(어떻게|왜|무엇|무슨|어떤)', response):
                question_types['개방형 질문'] += 1
            if re.search(r'(\?.*\?|또는|아니면)', response):
                question_types['선택형 질문'] += 1
            if re.search(r'(세요\?|나요\?|인가요\?|까요\?)', response):
                if not re.search(r'(어떻게|왜|무엇|무슨|어떤)', response):
                    question_types['폐쇄형 질문'] += 1
        
        return {
            'total_responses': len(response_lengths),
            'avg_response_length': sum(response_lengths) / len(response_lengths) if response_lengths else 0,
            'min_response_length': min(response_lengths) if response_lengths else 0,
            'max_response_length': max(response_lengths) if response_lengths else 0,
            'repetitive_phrases': dict(repetitive_count.most_common(10)),
            'question_types': question_types
        }
    
    def analyze_user_messages(self, conversations: list) -> dict:
        """사용자 메시지 분석"""
        
        message_lengths = []
        categories = Counter()
        message_types = Counter()
        
        # 시간대별 분포
        hourly_dist = defaultdict(int)
        daily_dist = defaultdict(int)
        
        # 어휘 다양성
        all_words = []
        
        for conv in conversations:
            if conv.message:
                message_lengths.append(len(conv.message))
                
                # 단어 수집
                words = re.findall(r'[가-힣]+', conv.message)
                all_words.extend(words)
            
            if conv.category:
                categories[conv.category] += 1
            
            if conv.message_type:
                message_types[conv.message_type] += 1
            
            if conv.created_at:
                hourly_dist[conv.created_at.hour] += 1
                daily_dist[conv.created_at.strftime('%Y-%m-%d')] += 1
        
        # 어휘 다양성 (Type-Token Ratio)
        unique_words = set(all_words)
        ttr = len(unique_words) / len(all_words) if all_words else 0
        
        return {
            'total_messages': len(message_lengths),
            'avg_message_length': sum(message_lengths) / len(message_lengths) if message_lengths else 0,
            'categories': dict(categories.most_common(10)),
            'message_types': dict(message_types),
            'hourly_distribution': dict(sorted(hourly_dist.items())),
            'daily_distribution': dict(sorted(daily_dist.items())),
            'vocabulary_size': len(unique_words),
            'total_words': len(all_words),
            'type_token_ratio': round(ttr, 3)
        }
    
    def analyze_dialogue_theory_compliance(self, conversations: list) -> dict:
        """대화이론 부합성 분석"""
        
        compliance = {
            'grice_maxims': {
                'quantity': {'score': 0, 'issues': []},
                'quality': {'score': 0, 'issues': []},
                'relation': {'score': 0, 'issues': []},
                'manner': {'score': 0, 'issues': []}
            },
            'adjacency_pairs': {'proper': 0, 'improper': 0},
            'turn_taking': {'smooth': 0, 'overlap': 0, 'gap': 0},
            'preference_organization': {'preferred': 0, 'dispreferred': 0}
        }
        
        issues = []
        
        # 1. Grice의 협력원칙 검사
        for conv in conversations:
            if not conv.response:
                continue
            
            response = conv.response
            
            # 양의 준칙 - 너무 짧거나 너무 긴 응답
            if len(response) < 10:
                compliance['grice_maxims']['quantity']['issues'].append(
                    f"응답이 너무 짧음: '{response[:50]}...'"
                )
            elif len(response) > 500:
                compliance['grice_maxims']['quantity']['issues'].append(
                    f"응답이 너무 김: {len(response)}자"
                )
            
            # 방식의 준칙 - 모호한 표현
            vague_phrases = ['좀', '약간', '뭔가', '그냥']
            vague_count = sum(1 for vp in vague_phrases if vp in response)
            if vague_count > 2:
                compliance['grice_maxims']['manner']['issues'].append(
                    f"모호한 표현 과다: {vague_count}회"
                )
            
            # 관계성 준칙 - 주제 변동 확인 (user message와 response 비교)
            if conv.message and conv.response:
                # 간단히, 사용자 메시지의 핵심 단어가 응답에 반영되었는지 확인
                user_words = set(re.findall(r'[가-힣]+', conv.message))
                response_words = set(re.findall(r'[가-힣]+', conv.response))
                overlap = user_words & response_words
                if len(overlap) < 2 and len(user_words) > 3:
                    compliance['grice_maxims']['relation']['issues'].append(
                        f"주제 연결성 부족: 사용자 '{conv.message[:30]}' vs 응답 '{response[:30]}'"
                    )
        
        # 2. 단조로움 검사
        repetitive_score = 0
        repetitive_phrases = [
            '어떠셨어요', '어떠세요', '좋으셨겠네요', '그렇군요', 
            '말씀해주세요', '이야기해주세요'
        ]
        
        phrase_counts = Counter()
        for conv in conversations:
            if not conv.response:
                continue
            for phrase in repetitive_phrases:
                if phrase in conv.response:
                    phrase_counts[phrase] += 1
                    repetitive_score += 1
        
        total_responses = sum(1 for c in conversations if c.response)
        repetitive_ratio = repetitive_score / total_responses if total_responses > 0 else 0
        
        if repetitive_ratio > 0.5:
            issues.append(f"⚠️ 높은 반복성: {round(repetitive_ratio*100, 1)}%의 응답이 상투적 표현 포함")
        
        # 3. 질문 다양성 검사
        question_patterns = Counter()
        for conv in conversations:
            if conv.response and '?' in conv.response:
                # 질문 패턴 추출
                questions = re.findall(r'[^.!?]*\?', conv.response)
                for q in questions:
                    # 패턴 정규화 (구체적 단어 제거)
                    pattern = re.sub(r'[가-힣]{2,}', '___', q.strip())
                    question_patterns[pattern] += 1
        
        top_question_patterns = question_patterns.most_common(5)
        if len(question_patterns) < 5 and total_responses > 10:
            issues.append(f"⚠️ 질문 패턴 다양성 부족: {len(question_patterns)}개 패턴만 사용")
        
        return {
            'repetitive_phrase_ratio': round(repetitive_ratio, 3),
            'repetitive_phrase_counts': dict(phrase_counts.most_common(10)),
            'question_pattern_diversity': len(question_patterns),
            'top_question_patterns': top_question_patterns,
            'issues': issues
        }
    
    def analyze_engagement(self, conversations: list) -> dict:
        """사용자 참여도 분석"""
        
        # 사용자별 대화 수
        user_conversation_counts = Counter()
        
        # 대화 길이 추세
        daily_avg_lengths = defaultdict(list)
        
        # 응답 시간
        response_latencies = []
        
        for conv in conversations:
            if conv.user_id:
                user_conversation_counts[str(conv.user_id)] += 1
            
            if conv.created_at and conv.message:
                date_str = conv.created_at.strftime('%Y-%m-%d')
                daily_avg_lengths[date_str].append(len(conv.message))
            
            if conv.response_latency_ms:
                response_latencies.append(conv.response_latency_ms)
        
        # 일일 평균 계산
        daily_avg = {
            date: sum(lengths) / len(lengths) 
            for date, lengths in daily_avg_lengths.items()
        }
        
        return {
            'unique_users': len(user_conversation_counts),
            'avg_conversations_per_user': sum(user_conversation_counts.values()) / len(user_conversation_counts) if user_conversation_counts else 0,
            'most_active_users': dict(user_conversation_counts.most_common(5)),
            'daily_avg_message_length': daily_avg,
            'avg_response_latency_ms': sum(response_latencies) / len(response_latencies) if response_latencies else 0
        }
    
    def analyze_analysis_scores(self, analysis_results: list) -> dict:
        """분석 점수 분석"""
        
        if not analysis_results:
            return {'message': '분석 결과 없음'}
        
        mcdi_scores = []
        risk_levels = Counter()
        metric_scores = defaultdict(list)
        
        for result in analysis_results:
            if result.mcdi_score:
                mcdi_scores.append(result.mcdi_score)
            
            if result.risk_level:
                risk_levels[result.risk_level] += 1
            
            for metric in ['lr', 'sd', 'nc', 'to', 'er', 'rt']:
                score = getattr(result, f'{metric}_score', None)
                if score:
                    metric_scores[metric.upper()].append(score)
        
        metric_stats = {}
        for metric, scores in metric_scores.items():
            if scores:
                metric_stats[metric] = {
                    'avg': round(sum(scores) / len(scores), 2),
                    'min': min(scores),
                    'max': max(scores),
                    'count': len(scores)
                }
        
        return {
            'total_analyzed': len(analysis_results),
            'mcdi_avg': round(sum(mcdi_scores) / len(mcdi_scores), 2) if mcdi_scores else None,
            'mcdi_min': min(mcdi_scores) if mcdi_scores else None,
            'mcdi_max': max(mcdi_scores) if mcdi_scores else None,
            'risk_distribution': dict(risk_levels),
            'metric_statistics': metric_stats
        }
    
    def generate_report(self, conversations: list, analysis_results: list) -> str:
        """종합 분석 보고서 생성"""
        
        response_patterns = self.analyze_response_patterns(conversations)
        user_messages = self.analyze_user_messages(conversations)
        theory_compliance = self.analyze_dialogue_theory_compliance(conversations)
        engagement = self.analyze_engagement(conversations)
        scores = self.analyze_analysis_scores(analysis_results)
        
        report = []
        report.append("=" * 70)
        report.append("📊 최근 일주일간 대화 품질 분석 보고서")
        report.append(f"   분석 기간: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}")
        report.append("=" * 70)
        
        # 1. 기본 통계
        report.append("\n## 1️⃣ 기본 통계")
        report.append(f"   - 총 대화 수: {response_patterns['total_responses']}건")
        report.append(f"   - 고유 사용자 수: {engagement['unique_users']}명")
        report.append(f"   - 사용자당 평균 대화: {engagement['avg_conversations_per_user']:.1f}건")
        
        # 2. 응답 패턴
        report.append("\n## 2️⃣ 응답 패턴 분석")
        report.append(f"   - 평균 응답 길이: {response_patterns['avg_response_length']:.1f}자")
        report.append(f"   - 응답 길이 범위: {response_patterns['min_response_length']} ~ {response_patterns['max_response_length']}자")
        
        report.append("\n   📌 반복 표현 빈도:")
        for phrase, count in response_patterns['repetitive_phrases'].items():
            pct = count / response_patterns['total_responses'] * 100 if response_patterns['total_responses'] > 0 else 0
            report.append(f"      - '{phrase}': {count}회 ({pct:.1f}%)")
        
        report.append("\n   📌 질문 유형 분포:")
        for qtype, count in response_patterns['question_types'].items():
            report.append(f"      - {qtype}: {count}회")
        
        # 3. 사용자 메시지
        report.append("\n## 3️⃣ 사용자 메시지 분석")
        report.append(f"   - 평균 메시지 길이: {user_messages['avg_message_length']:.1f}자")
        report.append(f"   - 어휘 다양성 (TTR): {user_messages['type_token_ratio']}")
        report.append(f"   - 고유 어휘 수: {user_messages['vocabulary_size']}개")
        
        report.append("\n   📌 카테고리 분포:")
        for cat, count in user_messages['categories'].items():
            report.append(f"      - {cat}: {count}회")
        
        report.append("\n   📌 시간대별 분포:")
        for hour, count in sorted(user_messages['hourly_distribution'].items()):
            bar = "█" * (count // 2) if count > 0 else ""
            report.append(f"      {hour:02d}시: {bar} ({count})")
        
        # 4. 대화이론 부합성
        report.append("\n## 4️⃣ 대화이론 부합성 분석")
        report.append(f"   - 반복 표현 비율: {theory_compliance['repetitive_phrase_ratio']*100:.1f}%")
        report.append(f"   - 질문 패턴 다양성: {theory_compliance['question_pattern_diversity']}개")
        
        if theory_compliance['issues']:
            report.append("\n   ⚠️ 발견된 문제점:")
            for issue in theory_compliance['issues']:
                report.append(f"      {issue}")
        
        # 5. 참여도
        report.append("\n## 5️⃣ 사용자 참여도")
        report.append(f"   - 평균 응답 지연: {engagement['avg_response_latency_ms']:.0f}ms" if engagement['avg_response_latency_ms'] else "   - 응답 지연 데이터 없음")
        
        # 6. 분석 점수
        if scores.get('total_analyzed', 0) > 0:
            report.append("\n## 6️⃣ 인지 분석 점수")
            report.append(f"   - 분석된 대화: {scores['total_analyzed']}건")
            if scores['mcdi_avg']:
                report.append(f"   - MCDI 평균: {scores['mcdi_avg']}")
            report.append(f"   - 위험도 분포: {scores['risk_distribution']}")
        
        # 7. 종합 평가
        report.append("\n" + "=" * 70)
        report.append("## 📋 종합 평가 및 개선 제안")
        report.append("=" * 70)
        
        problems = []
        suggestions = []
        
        # 반복성 검사
        if theory_compliance['repetitive_phrase_ratio'] > 0.3:
            problems.append("❌ 반복적 표현이 과도함 (30% 이상)")
            suggestions.append("→ '어떠셨어요?', '그렇군요' 등 상투어 감소 필요")
        else:
            report.append("✅ 반복적 표현이 적절히 통제됨")
        
        # 질문 다양성 검사
        if theory_compliance['question_pattern_diversity'] < 10:
            problems.append("❌ 질문 패턴이 단조로움")
            suggestions.append("→ 다양한 질문 유형(개방형, 선택형, 유도형) 균형 필요")
        else:
            report.append("✅ 질문 패턴이 다양함")
        
        # 카테고리 다양성 검사
        if len(user_messages['categories']) < 3:
            problems.append("❌ 대화 주제가 편중됨")
            suggestions.append("→ 다양한 주제(일화기억, 시간지남력, 서사구성) 균형 필요")
        else:
            report.append("✅ 대화 주제가 다양함")
        
        # TTR 검사
        if user_messages['type_token_ratio'] < 0.3:
            problems.append("❌ 사용자 어휘 다양성이 낮음")
            suggestions.append("→ 더 풍부한 어휘를 유도하는 질문 필요")
        
        # 시간대 분포 검사
        hourly = user_messages['hourly_distribution']
        if hourly:
            peak_hours = sorted(hourly.items(), key=lambda x: x[1], reverse=True)[:3]
            report.append(f"\n   📊 피크 시간대: {peak_hours}")
        
        if problems:
            report.append("\n### 발견된 문제점:")
            for p in problems:
                report.append(f"   {p}")
        
        if suggestions:
            report.append("\n### 개선 제안:")
            for s in suggestions:
                report.append(f"   {s}")
        
        return "\n".join(report)


async def main():
    """메인 실행 함수"""
    analyzer = ConversationQualityAnalyzer()
    
    async with AsyncSessionLocal() as session:
        # 데이터 조회
        conversations = await analyzer.fetch_recent_conversations(session, days=7)
        analysis_results = await analyzer.fetch_analysis_results(session, days=7)
        
        # 보고서 생성
        report = analyzer.generate_report(conversations, analysis_results)
        print(report)
        
        # JSON 형태로도 저장
        result_data = {
            'generated_at': datetime.now().isoformat(),
            'total_conversations': len(conversations),
            'total_analysis_results': len(analysis_results),
            'response_patterns': analyzer.analyze_response_patterns(conversations),
            'user_messages': analyzer.analyze_user_messages(conversations),
            'theory_compliance': analyzer.analyze_dialogue_theory_compliance(conversations),
            'engagement': analyzer.analyze_engagement(conversations),
            'scores': analyzer.analyze_analysis_scores(analysis_results)
        }
        
        # 결과 저장
        with open('/home/admin/docker/MemoryGardenAI/conversation_quality_report.json', 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2, default=str)
        
        print("\n\n📄 상세 데이터가 conversation_quality_report.json에 저장되었습니다.")


if __name__ == "__main__":
    asyncio.run(main())