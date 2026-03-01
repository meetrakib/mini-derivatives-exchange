from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from app.modules.orders.models import Order


class Fill(NamedTuple):
    price: float
    quantity: float
    taker_order_id: int
    taker_user_id: str
    maker_order_id: int
    maker_user_id: str
    symbol: str
    side: str


def _book_key(price: float, desc: bool) -> float:
    return -price if desc else price


class OrderBook:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.bids: dict[float, list[tuple[int, str, float, float]]] = {}
        self.asks: dict[float, list[tuple[int, str, float, float]]] = {}

    def add(self, order: Order) -> list[Fill]:
        if order.status != "open" or order.filled_quantity >= order.quantity:
            return []
        remaining = order.quantity - order.filled_quantity
        fills: list[Fill] = []
        book = self.asks if order.side == "buy" else self.bids
        prices = sorted(book.keys(), reverse=(order.side == "sell"))
        for price in prices:
            if remaining <= 0:
                break
            if order.side == "buy" and order.price is not None and price > order.price:
                break
            if order.side == "sell" and order.price is not None and price < order.price:
                break
            level = book[price]
            while level and remaining > 0:
                oid, uid, _, qty = level[0]
                fill_qty = min(qty, remaining)
                fill_price = price
                fills.append(Fill(price=fill_price, quantity=fill_qty, taker_order_id=order.id, taker_user_id=order.user_id, maker_order_id=oid, maker_user_id=uid, symbol=order.symbol, side=order.side))
                remaining -= fill_qty
                if fill_qty >= qty:
                    level.pop(0)
                else:
                    level[0] = (oid, uid, price, qty - fill_qty)
            if not level:
                del book[price]
        return fills

    def insert(self, order: Order) -> None:
        if order.order_type == "market":
            return
        price = order.price or 0.0
        book = self.bids if order.side == "buy" else self.asks
        qty = order.quantity - order.filled_quantity
        if qty <= 0:
            return
        key = _book_key(price, order.side == "buy")
        if key not in book:
            book[key] = []
        book[key].append((order.id, order.user_id, price, qty))

    def cancel(self, order: Order) -> None:
        price = order.price or 0.0
        book = self.bids if order.side == "buy" else self.asks
        key = _book_key(price, order.side == "buy")
        if key not in book:
            return
        level = book[key]
        for i, (oid, *_ ) in enumerate(level):
            if oid == order.id:
                level.pop(i)
                break
        if not level:
            del book[key]

    def best_bid(self) -> float | None:
        if not self.bids:
            return None
        return max(self.bids.keys())

    def best_ask(self) -> float | None:
        if not self.asks:
            return None
        return min(self.asks.keys())

    def mid_price(self) -> float | None:
        bid, ask = self.best_bid(), self.best_ask()
        if bid is not None and ask is not None:
            return (bid + ask) / 2
        return bid or ask

    def to_bids_asks(self, depth: int = 20) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        bids_list: list[tuple[float, float]] = []
        for key in sorted(self.bids.keys(), reverse=True)[:depth]:
            level = self.bids[key]
            total = sum(x[3] for x in level)
            price = level[0][2] if level else key
            bids_list.append((price, total))
        asks_list: list[tuple[float, float]] = []
        for key in sorted(self.asks.keys())[:depth]:
            level = self.asks[key]
            total = sum(x[3] for x in level)
            price = level[0][2] if level else key
            asks_list.append((price, total))
        return (bids_list, asks_list)
