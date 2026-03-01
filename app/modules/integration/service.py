import httpx

from app.core.config import settings


async def emit_trade_event(user_id: str, payload: dict) -> bool:
    if not settings.gamification_api_url or not settings.gamification_api_key:
        return False
    url = settings.gamification_api_url.rstrip("/") + "/api/v1/events"
    headers = {"Content-Type": "application/json", "X-API-Key": settings.gamification_api_key}
    body = {"user_id": user_id, "event_type": "trade", "payload": payload}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(url, json=body, headers=headers)
            return r.is_success
    except Exception:
        return False
