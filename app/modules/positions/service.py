from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.positions.models import Position


class PositionService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create(self, user_id: str, symbol: str) -> Position:
        r = await self._db.execute(select(Position).where(Position.user_id == user_id, Position.symbol == symbol))
        pos = r.scalar_one_or_none()
        if pos:
            return pos
        pos = Position(user_id=user_id, symbol=symbol)
        self._db.add(pos)
        await self._db.flush()
        await self._db.refresh(pos)
        return pos

    async def apply_fill(self, user_id: str, symbol: str, side: str, price: float, quantity: float) -> None:
        pos = await self.get_or_create(user_id, symbol)
        if side == "buy":
            new_size = pos.size + quantity
            if pos.size == 0:
                new_entry = price
            else:
                new_entry = (pos.entry_price * pos.size + price * quantity) / new_size
        else:
            new_size = pos.size - quantity
            new_entry = pos.entry_price if new_size != 0 else 0.0
        pos.size = new_size
        pos.entry_price = new_entry
        await self._db.flush()

    async def get_for_user(self, user_id: str) -> list[Position]:
        r = await self._db.execute(select(Position).where(Position.user_id == user_id, Position.size != 0))
        return list(r.scalars().all())
