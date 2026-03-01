from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.integration.service import emit_trade_event
from app.modules.market_data.service import update_from_fill
from app.modules.matching.engine import Fill, OrderBook
from app.modules.orders.models import Order
from app.modules.positions.service import PositionService


async def load_book_async(db: AsyncSession, symbol: str) -> OrderBook:
    from sqlalchemy import select
    r = await db.execute(select(Order).where(Order.symbol == symbol, Order.status == "open", Order.order_type == "limit"))
    orders = list(r.scalars().all())
    book = OrderBook(symbol)
    for o in orders:
        book.insert(o)
    return book


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._position_svc = PositionService(db)

    async def place(
        self,
        user_id: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None,
    ) -> Order:
        if order_type == "market":
            price = None
        order = Order(
            user_id=user_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            filled_quantity=0.0,
            status="open",
        )
        self._db.add(order)
        await self._db.flush()
        await self._db.refresh(order)

        book = await load_book_async(self._db, symbol)
        fills = book.add(order)
        for fill in fills:
            order.filled_quantity += fill.quantity
            maker = await self.get_by_id(fill.maker_order_id)
            if maker:
                maker.filled_quantity += fill.quantity
                if maker.filled_quantity >= maker.quantity:
                    maker.status = "filled"
            await self._position_svc.apply_fill(fill.taker_user_id, fill.symbol, fill.side, fill.price, fill.quantity)
            maker_side = "sell" if fill.side == "buy" else "buy"
            await self._position_svc.apply_fill(fill.maker_user_id, fill.symbol, maker_side, fill.price, fill.quantity)
            update_from_fill(fill.price)
            await emit_trade_event(fill.taker_user_id, {"volume": fill.quantity * fill.price, "count": 1, "price": fill.price})
        if order.filled_quantity >= order.quantity:
            order.status = "filled"
        else:
            if order.order_type == "limit":
                book.insert(order)
            else:
                order.status = "cancelled"
        await self._db.flush()
        return order

    async def cancel(self, order_id: int, user_id: str | None = None) -> Order | None:
        r = await self._db.execute(select(Order).where(Order.id == order_id))
        order = r.scalar_one_or_none()
        if not order or order.status != "open":
            return None
        if user_id is not None and order.user_id != user_id:
            return None
        order.status = "cancelled"
        await self._db.flush()
        return order

    async def get_by_id(self, order_id: int) -> Order | None:
        r = await self._db.execute(select(Order).where(Order.id == order_id))
        return r.scalar_one_or_none()

    async def list_by_user(self, user_id: str, symbol: str | None = None, limit: int = 50) -> list[Order]:
        q = select(Order).where(Order.user_id == user_id).order_by(Order.id.desc()).limit(limit)
        if symbol:
            q = q.where(Order.symbol == symbol)
        r = await self._db.execute(q)
        return list(r.scalars().all())

    async def get_order_book(self, symbol: str, depth: int = 20) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        book = await load_book_async(self._db, symbol)
        return book.to_bids_asks(depth)
