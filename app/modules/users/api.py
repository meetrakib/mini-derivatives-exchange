from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.users.schemas import UserCreate, UserRead
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
async def create_user(
    data: UserCreate | None = None,
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    user = await svc.create(display_name=data.display_name if data and data.display_name else None)
    return UserRead.model_validate(user)
