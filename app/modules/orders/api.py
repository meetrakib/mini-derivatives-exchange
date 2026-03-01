from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.orders.schemas import OrderBookRead, OrderBookLevel, OrderCreate, OrderRead
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=201)
async def place_order(
    data: OrderCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    svc = OrderService(db)
    order = await svc.place(
        user_id=user_id,
        symbol=data.symbol,
        side=data.side,
        order_type=data.order_type,
        quantity=data.quantity,
        price=data.price,
    )
    return OrderRead.model_validate(order)


@router.delete("/{order_id}")
async def cancel_order(
    order_id: int,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
):
    svc = OrderService(db)
    order = await svc.cancel(order_id, user_id=user_id)
    if not order:
        raise HTTPException(404, "Order not found or not open")
    return {"ok": True}


@router.get("", response_model=list[OrderRead])
async def list_orders(
    user_id: Annotated[str, Depends(get_current_user_id)],
    symbol: Annotated[str | None, Query()] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    svc = OrderService(db)
    orders = await svc.list_by_user(user_id, symbol=symbol, limit=limit)
    return [OrderRead.model_validate(o) for o in orders]


@router.get("/book", response_model=OrderBookRead)
async def get_order_book(
    symbol: Annotated[str, Query()] = "BTC-PERP",
    depth: int = 20,
    db: AsyncSession = Depends(get_db),
):
    svc = OrderService(db)
    bids_list, asks_list = await svc.get_order_book(symbol, depth=depth)
    return OrderBookRead(
        symbol=symbol,
        bids=[OrderBookLevel(price=p, quantity=q) for p, q in bids_list],
        asks=[OrderBookLevel(price=p, quantity=q) for p, q in asks_list],
    )
