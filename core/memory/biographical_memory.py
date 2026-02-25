# core/memory/biographical_memory.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

class BiographicalMemory:
    """
    [신상 기억]
    - 역할: 사용자 프로필 및 고정 정보 관리
    - 저장소: PostgreSQL (Users 테이블)
    - 특징: 영구적, 구조화된 데이터
    """
    def __init__(self, user_id: int, db: AsyncSession):
        self.user_id = user_id
        self.db = db

    async def get_profile(self) -> dict:
        """사용자 기본 정보 조회"""
        # User 모델은 models/user.py에 정의되어 있다고 가정
        result = await self.db.execute(select(User).where(User.id == self.user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {}

        return {
            "name": user.name,
            "age": self._calculate_age(user.birth_year),
            "gender": user.gender,
            "guardian_phone": user.guardian_phone,
            "terms_agreed": user.terms_agreed
        }

    async def update_profile(self, **kwargs):
        """
        사용자 정보 업데이트
        예: memory.update_profile(name="김철수", birth_year=1950)
        """
        result = await self.db.execute(select(User).where(User.id == self.user_id))
        user = result.scalar_one_or_none()

        if user:
            for key, value in kwargs.items():
                # User 모델에 존재하는 필드인지 확인 후 업데이트
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            await self.db.commit()
            await self.db.refresh(user)

    def _calculate_age(self, birth_year: int) -> int:
        if not birth_year:
            return 0
        import datetime
        current_year = datetime.datetime.now().year
        return current_year - birth_year + 1  # 한국 나이 계산 (필요시 만 나이로 변경)