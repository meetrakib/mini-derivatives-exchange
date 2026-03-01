from fastapi import APIRouter, Query

from app.modules.market_data.binance import fetch_klines
from app.modules.market_data.service import get_price_live

router = APIRouter(prefix="/ticker", tags=["ticker"])


@router.get("")
async def get_ticker(symbol: str = Query(default="BTC-PERP")):
    price = await get_price_live(symbol)
    return {"symbol": symbol, "last": price}


@router.get("/klines")
async def get_klines(
    symbol: str = Query(default="BTC-PERP"),
    interval: str = Query(default="1h", description="1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(default=24, le=500),
):
    """OHLCV from Binance (real market data). For chart."""
    klines = await fetch_klines(symbol=symbol, interval=interval, limit=limit)
    return {"symbol": symbol, "interval": interval, "klines": klines}
