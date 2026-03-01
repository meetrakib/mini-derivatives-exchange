"""Binance public API — no API key required. See https://binance-docs.github.io/apidocs/spot/en/."""

import httpx

BINANCE_BASE = "https://api.binance.com/api/v3"

# Our symbol (BTC-PERP) maps to Binance spot BTCUSDT for reference price/klines
SYMBOL_MAP = {"BTC-PERP": "BTCUSDT"}


def _binance_symbol(symbol: str) -> str:
    return SYMBOL_MAP.get(symbol, "BTCUSDT")


async def fetch_price(symbol: str = "BTC-PERP") -> float | None:
    """Current last price from Binance spot."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{BINANCE_BASE}/ticker/price", params={"symbol": _binance_symbol(symbol)})
            if r.is_success:
                data = r.json()
                return float(data["price"])
    except Exception:
        pass
    return None


async def fetch_klines(
    symbol: str = "BTC-PERP",
    interval: str = "1h",
    limit: int = 24,
) -> list[dict]:
    """
    Kline/candlestick from Binance. Returns list of { time, open, high, low, close, volume }.
    Intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{BINANCE_BASE}/klines",
                params={"symbol": _binance_symbol(symbol), "interval": interval, "limit": min(limit, 500)},
            )
            if not r.is_success:
                return []
            arr = r.json()
            return [
                {
                    "time": row[0],
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
                for row in arr
            ]
    except Exception:
        return []
