from app.core.config import settings

_last_price: float = settings.mock_price


def get_price(symbol: str | None = None) -> float:
    global _last_price
    return _last_price


def set_price(price: float) -> None:
    global _last_price
    _last_price = price


def update_from_fill(price: float) -> None:
    set_price(price)


async def get_price_live(symbol: str = "BTC-PERP") -> float:
    """Fetch from Binance if available; else return cached or mock."""
    from app.modules.market_data.binance import fetch_price
    global _last_price
    live = await fetch_price(symbol)
    if live is not None:
        _last_price = live
    return _last_price
