import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import hash_password
from app.modules.users.models import User


def _generate_user_id() -> str:
    return secrets.token_urlsafe(16)


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, display_name: str | None = None) -> User:
        user_id = _generate_user_id()
        user = User(user_id=user_id, display_name=display_name or None)
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def create_with_password(self, email: str, password: str, display_name: str | None = None) -> User:
        user_id = _generate_user_id()
        user = User(
            user_id=user_id,
            email=email.lower(),
            password_hash=hash_password(password),
            display_name=display_name or None,
        )
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user
