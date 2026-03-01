from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.positions.schemas import PositionRead
from app.modules.positions.service import PositionService

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=list[PositionRead])
async def list_positions(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    svc = PositionService(db)
    positions = await svc.get_for_user(user_id)
    return [PositionRead.model_validate(p) for p in positions]
