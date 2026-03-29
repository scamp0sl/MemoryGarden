"""
온보딩 플로우 (SPEC §2.4)

14일 베이스라인 수집 플로우:
    Day 0  : 정원 이름 짓기 + 첫 인사
    Day 1-7 : 관계 형성 + 기초 데이터 수집 (자유 대화)
    Day 8-14: 6개 카테고리 순차 노출 + 선호도 감지
    Day 15+ : 베이스라인 확립 → MCDI 분석 정식 시작

Author: Memory Garden Team
Created: 2026-02-27
"""

from typing import Optional, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, GardenStatus
from database.redis_client import RedisClient
from services.llm_service import default_llm_service
from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================
# 온보딩 단계 상수
# ============================================
ONBOARDING_DAY0_COMPLETE = 1      # 정원 이름 설정 후
ONBOARDING_BASELINE_END = 15      # 베이스라인 수집 완료 (Day 15+부터 정식 분석)

# Day 0 → 정원 이름 저장 후 다음 날짜로 넘어가기 위한 Redis 키
_DAY0_WAITING_KEY = "onboarding_day0_waiting:{user_id}"

# ============================================
# Day별 안내 메시지
# ============================================
DAY0_WELCOME = """안녕하세요! 기억의 정원에 오신 걸 환영해요 🌱

저는 매일 함께 이야기를 나누며 소중한 기억들을 돌봐드리는 정원지기예요.

먼저, 우리 정원의 이름을 지어볼까요?
예를 들어 "봄날 정원", "할머니의 정원", "추억 정원" 같은 이름도 좋아요. 🌸

어떤 이름이 마음에 드세요?"""

DAY0_NAME_SAVED = """{garden_name}이라는 이름이 참 예쁘네요! 🌺

이제 매일 잠깐씩 이야기를 나누면서 {garden_name}을 함께 가꿔봐요.
꽃도 피우고, 나비도 불러오고, 소중한 기억들로 가득 채울 거예요.

내일부터 본격적으로 시작해요! 오늘 잠깐 어떻게 지내셨나요? 😊"""

DAY1_TO_7_GREETING = [
    "안녕하세요! 오늘 {garden_name}에 물을 주러 왔어요 🌿\n오늘 하루 어떻게 보내셨나요?",
    "오늘도 {garden_name}이 잘 자라고 있어요 🌸\n오늘 있었던 일 중에 기억나는 게 있나요?",
    "반가워요! {garden_name}에 오늘은 어떤 이야기를 심어볼까요? 🌻\n요즘 어떻게 지내고 계세요?",
    "오늘도 {garden_name} 방문해 주셨네요 🦋\n최근에 즐거웠던 일이 있으셨나요?",
    "반갑습니다! {garden_name}의 꽃이 오늘도 예쁘게 피어있어요 🌷\n오늘 기분은 어떠세요?",
    "안녕하세요! {garden_name}에 오신 걸 환영해요 🌱\n오늘 누구를 만나셨거나 통화하셨나요?",
    "오늘도 잘 오셨어요! {garden_name}이 점점 예뻐지고 있어요 🌺\n요즘 식사는 잘 하고 계신가요?",
]

DAY8_TO_14_INTRO = [
    "오늘은 옛날 이야기를 해볼까요? 🌿\n어렸을 때 살던 동네가 어디셨는지 궁금해요.",
    "오늘은 가족 이야기를 나눠볼까요? 🌸\n가족 중에서 가장 기억에 남는 분이 계세요?",
    "오늘은 좋아하시는 것들을 알고 싶어요 🌻\n가장 좋아하시는 음식이나 계절이 있으신가요?",
    "오늘 날짜가 {date}이네요 🗓️\n요즘 날씨가 어떤지, 계절 변화를 느끼시나요?",
    "오늘은 특별한 기억 하나를 여쭤볼게요 🌺\n가장 행복했던 때가 언제였는지 기억나세요?",
    "오늘은 요즘 일상을 여쭤볼게요 🦋\n아침에 일어나시면 보통 뭘 제일 먼저 하세요?",
    "오늘은 사진이나 그림으로 이야기해볼까요? 📸\n좋아하는 꽃이나 풍경 사진이 있으시면 보내주세요!",
]


class OnboardingFlow:
    """
    온보딩 플로우 관리 클래스

    신규 사용자의 14일 베이스라인 수집 플로우를 담당합니다.

    Attributes:
        db: 데이터베이스 세션

    Example:
        >>> flow = OnboardingFlow(db)
        >>> is_onboarding, response = await flow.handle(user, message)
        >>> if is_onboarding:
        ...     return response  # 온보딩 응답 사용
        ... else:
        ...     # 일반 대화 처리
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle(
        self,
        user: User,
        message: str
    ) -> Tuple[bool, Optional[str]]:
        """
        온보딩 플로우 처리

        Args:
            user: 사용자 객체
            message: 사용자 메시지

        Returns:
            (is_onboarding, response)
            - is_onboarding: True이면 온보딩 중 (response 사용)
            - response: 온보딩 응답 메시지 (is_onboarding=True인 경우)

        Example:
            >>> is_ob, resp = await flow.handle(user, "봄날 정원")
            >>> print(is_ob, resp[:20])
            True "봄날 정원이라는 이름이..."
        """
        day = user.onboarding_day

        # Day 15+ → 정식 서비스 (온보딩 종료)
        if day >= ONBOARDING_BASELINE_END:
            return False, None

        # Day 0: 정원 이름 짓기
        if day == 0:
            return True, await self._handle_day0(user, message)

        # Day 1-14: 베이스라인 수집 중
        # 대화는 DialogueManager가 생성하되, 날짜를 매일 증가
        await self._increment_day(user)
        return False, None  # 일반 대화 처리에 위임

    async def get_day0_greeting(self, user: User) -> str:
        """
        Day 0 최초 인사 메시지 (정원 이름이 없는 경우)

        Args:
            user: 사용자 객체

        Returns:
            Day 0 환영 메시지
        """
        # 이미 정원 이름이 있으면 Day 1 인사로 전환
        if user.garden_name:
            return await self.get_daily_greeting(user)
        return DAY0_WELCOME

    async def get_daily_greeting(self, user: User) -> Optional[str]:
        """
        스케줄러가 보내는 일일 인사 메시지

        Day 1-7: 자유 대화형 인사
        Day 8-14: 카테고리 노출형 인사
        Day 15+: None (일반 DialogueManager 처리)

        Args:
            user: 사용자 객체

        Returns:
            일일 인사 메시지 또는 None
        """
        day = user.onboarding_day
        garden_name = user.garden_name or "기억의 정원"

        if day >= ONBOARDING_BASELINE_END:
            return None

        if 1 <= day <= 7:
            # Day 1-7: 자유 대화
            idx = (day - 1) % len(DAY1_TO_7_GREETING)
            return DAY1_TO_7_GREETING[idx].format(garden_name=garden_name)

        if 8 <= day <= 14:
            # Day 8-14: 카테고리 노출
            idx = (day - 8) % len(DAY8_TO_14_INTRO)
            today_str = datetime.now().strftime("%m월 %d일")
            return DAY8_TO_14_INTRO[idx].format(
                garden_name=garden_name,
                date=today_str
            )

        return None

    async def is_baseline_complete(self, user: User) -> bool:
        """
        베이스라인 수집 완료 여부

        Args:
            user: 사용자 객체

        Returns:
            True이면 Day 15+ (정식 분석 가능)
        """
        return user.onboarding_day >= ONBOARDING_BASELINE_END

    async def _handle_day0(self, user: User, message: str) -> str:
        """
        Day 0 처리: 2~3단계 방식

        Step 1: 환영 메시지 발송, Redis 플래그(시도 횟수) 설정
        Step 2: 사용자 입력 → 정원 이름 추출
                - 신뢰도 높으면: 저장 → Day 1 전환
                - 신뢰도 낮으면: 재질문 (2회 한도)
        Step 3: 2회 실패 후 → 기본값으로 저장 후 진행
        """
        # 이름은 있는데 day=0인 예외 케이스 → 바로 Day 1로
        if user.garden_name:
            user.onboarding_day = 1
            await self.db.commit()
            return await self.get_daily_greeting(user)

        redis = RedisClient.get_instance()
        waiting_key = _DAY0_WAITING_KEY.format(user_id=str(user.id))
        retry_key = f"onboarding_day0_retry:{str(user.id)}"

        # Step 1: 환영 메시지를 아직 보내지 않았으면 먼저 보냄
        already_asked = await redis.get(waiting_key)
        if not already_asked:
            await redis.set(waiting_key, "1", ttl=86400)
            await redis.set(retry_key, "0", ttl=86400)
            logger.info(
                "온보딩 Day 0: 정원 이름 환영 메시지 발송",
                extra={"user_id": str(user.id)}
            )
            return DAY0_WELCOME

        # Step 2: 이름 추출 & 신뢰도 검증
        garden_name, confident = self._extract_garden_name_with_confidence(message)

        # 신뢰도 낮으면 재질문 (최대 2회)
        if not confident:
            retry_count = int((await redis.get(retry_key)) or "0")
            if retry_count < 2:
                await redis.set(retry_key, str(retry_count + 1), ttl=86400)
                logger.info(
                    f"온보딩 Day 0: 정원 이름 재질문 (시도 {retry_count + 1}회)",
                    extra={"user_id": str(user.id), "input": message}
                )
                
                # LLM을 활용한 다정하고 능동적인 이름 추천 생성
                try:
                    prompt = (
                        f"당신은 정원지기 AI 챗봇입니다. 사용자가 정원 이름을 고민하거나 "
                        f"이름을 추천해달라고 말하고 있습니다. 메시지: '{message}'\n\n"
                        f"사용자의 메시지에 공감하며, 따뜻하고 예쁜 정원 이름 후보 3가지를 친주하고 화기애애한 말투로 제안해주세요. "
                        f"(예: \"봄날 정원\", \"활기찬 기억의 정원\", \"행복한 뜰\" 등) "
                        f"답변은 150자 이내로 짧게 작성하세요."
                    )
                    llm_recommendation = await default_llm_service.call(
                        prompt=prompt,
                        system_prompt="당신은 다정하고 명랑한 정원지기 어르신 말벗 AI입니다."
                    )
                    return llm_recommendation
                except Exception as e:
                    logger.error(f"Day0 LLM 이름 추천 실패: {e}")
                    return (
                        "정원 이름을 짓기가 어려우신가요? 😅\n\n"
                        "다양한 이름이 가능해요!\n"
                        "예: \"봄날 정원\", \"기억의 궁전\", \"행복의 정원\" 💐\n\n"
                        "어떤 느낌의 이름이 마음에 드시나요?"
                    )
            else:
                # 2회 시도 후에도 실패 → 기본값으로 진행
                garden_name = "소중한 정원"
                logger.info(
                    "온보딩 Day 0: 최대 재시도 초과, 기본값으로 진행",
                    extra={"user_id": str(user.id)}
                )

        # 이름 저장 → Day 1 전환
        user.garden_name = garden_name
        user.onboarding_day = 1
        user.last_interaction_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(user)

        # Redis 플래그 삭제
        await redis.delete(waiting_key)
        await redis.delete(retry_key)

        # GardenStatus 초기화
        await self._init_garden_status(user)

        logger.info(
            "온보딩 Day 0 완료: 정원 이름 저장",
            extra={
                "user_id": str(user.id),
                "garden_name": garden_name
            }
        )

        return DAY0_NAME_SAVED.format(garden_name=garden_name)

    def _extract_garden_name_with_confidence(self, message: str) -> tuple[str, bool]:
        """
        정원 이름 추출 + 신뢰도 반환

        Returns:
            (name, confident)
            - confident=True: 이름으로 신뢰할 수 있는 경우
            - confident=False: 재질문 권장
        """
        import re
        text = message.strip()

        # 비이름 패턴 → 즉시 불신뢰
        non_name_patterns = [
            r'^(음|글쎄|모르겠|어떤|뭐가|뭘로|어떻게|잘 모르|아무|아직|왜|저는|우린|나는|그건|저기)',
            r'이름이 뭐|이름 뭐|어떤 이름|무슨 이름|좋은 이름|이름 추천|추천|알림',
            r'이름이 다른|이름이 같|이름이 왜|이름 문제|이름에',  # "이름이 다른 사람한..." 류
        ]
        for pat in non_name_patterns:
            if re.search(pat, text):
                return text[:5] + "...", False

        # 따옴표 → 최고 신뢰
        quoted = re.search(r'["\']([^"\']{1,20})["\']', text)
        if quoted:
            return quoted.group(1).strip(), True

        # 자연어 패턴 → 신뢰
        patterns = [
            (r'(.+?)\s*(?:이라고|라고)\s*(?:해줘|해|할게|할래|하자|부를게|할거야)', 1),
            (r'(.+?)\s*(?:으로|로)\s*(?:해줘|할게|할래|하자|해|부를게|할거야)', 1),
            (r'(.+?)\s*(?:이라고|라고)\s*(?:짓고|지을게|짓자|짓고 싶)', 1),
            (r'(.+?)\s*(?:은 어때|는 어때|이 어때|어떠)(?:요)?[?]?$', 1),
            (r'(.+?정원|.+?궁전|.+?동산|.+?마을|.+?뜰)\s*(?:이|가)?\s*(?:마음에 들|좋아|좋을|예뻐|예쁘)', 1),
            (r'이름(?:은|이|을)\s*(.+?)(?:\s*(?:으로|로|이야|야|예요|이에요|이라고))?\s*$', 1),
            (r'^(.+?)\s*(?:이야|야|예요|이에요)$', 1),
            (r'그냥\s+(.+?)\s*(?:으로|로)\s*(?:할게|할래|해줘|하자)', 1),
        ]
        for pat, grp in patterns:
            m = re.search(pat, text)
            if m and m.lastindex and m.lastindex >= grp:
                candidate = m.group(grp).strip()
                candidate = re.sub(r'^(?:그냥|음|뭐|저는|저|그|일단|그냥은|전)\s+', '', candidate).strip()
                candidate = re.sub(r'\s*(이라고|라고|으로|로|이야|야|예요|이에요)$', '', candidate).strip()
                if 1 <= len(candidate) <= 20:
                    return candidate, True

        # 짧으면 (15자 이하) 이름으로 신뢰 — 단, 비이름 표현이나 서술형 문장은 제외
        if len(text) <= 15:
            name = re.sub(r'[.,?! ]+$', '', text).strip()
            name = re.sub(r'\s*어때(?:요)?[?]?$', '', name).strip()
            
            non_name_short = [
                r'^(다|별로|싫어|좋아|모르겠|잘 모르|그냥|아무|너무|정말|글쎄|아니|맞아|네|아니요)',
                r'(해|야|어|네|요|다|지|까|나|요\?|잖아)$',  # 서술형 종결어미 (주의: "정원이야"는 위에서 잡힘)
                r'추천',
                r'이름'
            ]
            for pat in non_name_short:
                if re.search(pat, name):
                    return name, False
                    
            if name and len(name) >= 1:
                return name, True

        # 길고 패턴도 없으면 → 불신뢰 (대화 내용이므로 이름으로 저장하지 않아야 함)
        return text[:10] + "...", False


    def _extract_garden_name(self, message: str) -> str:
        """
        사용자 메시지에서 정원 이름 추출

        처리 순서:
        1. 따옴표로 감싼 이름 → 최우선
        2. 자연어 패턴 파싱 (X로 할게/할래, X이라고 해줘, X 어때 등)
        3. 짧은 메시지는 그대로 이름으로 사용
        4. fallback: 20자 절단
        """
        import re
        text = message.strip()

        # 0. 명백히 이름이 아닌 경우 → 기본값
        non_name_patterns = [
            r'^(음|글쎄|모르겠|어떤|뭐가|뭘로|어떻게|잘 모르|아무|아직)',
            r'이름이 뭐|이름 뭐|어떤 이름|무슨 이름',
        ]
        for pat in non_name_patterns:
            if re.search(pat, text):
                return "소중한 정원"

        # 1. 따옴표로 감싼 이름 (최우선)
        quoted = re.search(r'["\']([^"\']{1,20})["\']', text)
        if quoted:
            return quoted.group(1).strip()

        # 2. 자연어 패턴 파싱
        patterns = [
            # "X라고 해줘/할게/할래 등"
            (r'(.+?)\s*(?:이라고|라고)\s*(?:해줘|해|할게|할래|하자|부를게|할거야)', 1),
            # "X로 해줘/할게/할래 등"
            (r'(.+?)\s*(?:으로|로)\s*(?:해줘|할게|할래|하자|해|부를게|할거야)', 1),
            # "X라고 짓고 싶어"
            (r'(.+?)\s*(?:이라고|라고)\s*(?:짓고|지을게|짓자|짓고 싶)', 1),
            # "X 어때/어때요"
            (r'(.+?)\s*(?:은 어때|는 어때|이 어때|어떠)(?:요)?[?]?$', 1),
            # "X이 마음에 들어요/들어" - 특정 정원 이름 형태
            (r'(.+?정원|.+?궁전|.+?동산|.+?마을|.+?뜰)\s*(?:이|가)?\s*(?:마음에 들|좋아|좋을|예뻐|예쁘)', 1),
            # "이름은/이름이 X"
            (r'이름(?:은|이|을)\s*(.+?)(?:\s*(?:으로|로|이야|야|예요|이에요|이라고))?\s*$', 1),
            # "X이야/예요/이에요"
            (r'^(.+?)\s*(?:이야|야|예요|이에요|이에요)$', 1),
            # "그냥 X로 할래" → X 추출
            (r'그냥\s+(.+?)\s*(?:으로|로)\s*(?:할게|할래|해줘|하자)', 1),
        ]

        for pat, grp in patterns:
            m = re.search(pat, text)
            if m and m.lastindex and m.lastindex >= grp:
                candidate = m.group(grp).strip()
                # 앞부분 불필요한 접두어 제거
                candidate = re.sub(r'^(?:그냥|음|뭐|저는|저|그|일단|그냥은|전)\s+', '', candidate).strip()
                # 후행 조사/동사 제거
                candidate = re.sub(r'\s*(이라고|라고|으로|로|이야|야|예요|이에요)$', '', candidate).strip()
                if 1 <= len(candidate) <= 20:
                    return candidate

        # 3. 짧으면 그대로 이름으로 (15자 이하)
        if len(text) <= 15:
            name = re.sub(r'[.,?! ]+$', '', text).strip()
            # "X 어때요?" → "X" 처리
            name = re.sub(r'\s*어때(?:요)?[?]?$', '', name).strip()
            if name:
                return name

        # 4. 20자 절단 fallback
        name = text[:20].strip()
        return name if name else "소중한 정원"

    async def _increment_day(self, user: User) -> None:
        """
        온보딩 날짜 증가 (마지막 상호작용 기준 하루에 1회)

        같은 날 여러 번 대화해도 1회만 증가합니다.
        """
        now = datetime.now()
        last = user.last_interaction_at

        # 마지막 상호작용이 오늘이면 증가하지 않음
        if last and last.date() == now.date():
            return

        if user.onboarding_day < ONBOARDING_BASELINE_END:
            user.onboarding_day += 1

        user.last_interaction_at = now
        await self.db.commit()

        logger.debug(
            f"온보딩 날짜 증가: Day {user.onboarding_day}",
            extra={"user_id": str(user.id)}
        )

    async def _init_garden_status(self, user: User) -> None:
        """
        GardenStatus 레코드 초기화 (신규 사용자 Day 0 완료 시)

        Savepoint를 사용하여 예외 발생 시 트랜잭션이 오염되지 않도록 보호.
        예외는 begin_nested() 밖에서 catch → ROLLBACK TO SAVEPOINT 자동 실행.
        """
        try:
            async with self.db.begin_nested():
                existing = await self.db.execute(
                    select(GardenStatus).where(GardenStatus.user_id == user.id)
                )
                if existing.scalar_one_or_none():
                    return  # 이미 존재

                garden = GardenStatus(
                    user_id=user.id,
                    flower_count=0,
                    butterfly_count=0,
                    consecutive_days=1,
                    total_conversations=0,
                    garden_level=1,
                    last_interaction_at=datetime.now()
                )
                self.db.add(garden)
                # begin_nested() 정상 종료 시 RELEASE SAVEPOINT (외부 tx에 포함)

            logger.info(
                "GardenStatus 초기화 완료",
                extra={"user_id": str(user.id)}
            )
        except Exception as e:
            # begin_nested() 예외 시 ROLLBACK TO SAVEPOINT 자동 실행
            # 외부 트랜잭션은 유지됨
            logger.warning(f"GardenStatus 초기화 실패 (무시): {e}")
