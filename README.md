# Mini Derivatives Exchange

**Paper/simulated derivatives exchange**: order book, limit & market orders, matching engine, positions and PnL. Uses **real market data** from Binance (no API key) for last price and OHLCV. Optional: emit trade events to a gamification backend (e.g. [gamification-core](https://github.com) or quest-saas-api) for quests and leaderboards.

Part of the [Gamification & Mini Exchange](https://github.com) ecosystem. A demo frontend is available in [mini-exchange-ui](https://github.com).

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Event-Driven Matching Engine](#event-driven-matching-engine)
- [System Design](#system-design)
- [API Documentation](#api-documentation)
- [Authentication](#authentication)
- [Gamification Integration](#gamification-integration)
- [Docker Setup](#docker-setup)
- [Local Development](#local-development)
- [Testing](#testing)
- [Scaling & Future Work](#scaling--future-work)

---

## Features

- **Markets**: One or few symbols (e.g. `BTC-PERP`). Default symbol configurable.
- **Order types**: Limit and market. Limit orders rest in the book; market orders match immediately at best available price.
- **Order book**: In-memory book per symbol, rebuilt from DB (open limit orders) on each place/cancel for consistency.
- **Matching**: Price-time priority. Fills update positions and optional gamification events.
- **Positions**: Per user per symbol — size, entry price; updated on each fill.
- **Market data**: Real prices from [Binance public API](https://binance-docs.github.io/apidocs/spot/en/) — ticker (`/api/v3/ticker/price`) and klines (OHLCV) for charts. No API key required.
- **Users**: Create account via `POST /api/v1/users` (returns `user_id`) or full auth via `POST /api/v1/auth/signup` / `POST /api/v1/auth/login` (JWT). Trading endpoints require Bearer token (or optional API key in future).

---

## Architecture

```
┌─────────────────┐     Orders / Book / Positions      ┌──────────────────────┐
│  mini-exchange  │ ◄─────────────────────────────────►│  PostgreSQL           │
│  UI (Next.js)   │     JWT (Bearer)                    │  (orders, positions,  │
└────────┬────────┘                                    │   users)             │
         │                                             └──────────────────────┘
         │                                                          ▲
         │                                             ┌────────────┴────────────┐
         │                                             │  Mini Derivatives API   │
         │                                             │  (FastAPI)              │
         │                                             └────────────┬────────────┘
         │                                                          │
         │                        ┌─────────────────────────────────┤
         │                        │  market_data (Binance)           │  On fill:
         │                        │  orders → matching → positions  │  POST /events
         │                        │  integration (optional)         │  (gamification)
         │                        └─────────────────────────────────┘
```

**Modular monolith** (single deployable):

| Module        | Responsibility                    | Public interface / usage                    |
|---------------|------------------------------------|--------------------------------------------|
| **core**      | Config, DB, app bootstrap          | `Settings`, `get_db`, `get_current_user_id` |
| **market_data** | Fetch price, klines from Binance | `get_price_live(symbol)`, `fetch_klines(...)`; last price updated on fill |
| **orders**    | Order CRUD, validate, submit       | `OrderService.place`, `cancel`, `list_by_user`, `get_order_book` |
| **matching**  | Order book, match, produce fills   | `OrderBook.add(order)` → list of `Fill`; `insert` / `cancel` for book |
| **positions** | Positions and PnL per user         | `PositionService.get_for_user`, `apply_fill` |
| **integration** | On fill: POST to gamification   | `emit_trade_event(user_id, payload)` (if URL + key set) |
| **users**     | User creation (simple or with password) | `UserService.create`, `create_with_password` |
| **auth**      | JWT issue/verify, signup/login     | `create_access_token`, `decode_token`; `/auth/signup`, `/auth/login`, `/auth/me` |

---

## Event-Driven Matching Engine

- **OrderBook** (per symbol): Bids and asks as price levels; each level is a list of `(order_id, user_id, price, quantity)`.
- **Place order**: Order is persisted; book is loaded from DB (all open limit orders for symbol). **Match**: `book.add(order)` runs price-time priority — walk opposite side, generate `Fill` tuples (price, quantity, taker/maker order and user). Fills are applied: update `order.filled_quantity` and `order.status`, update positions via `PositionService.apply_fill`, update market-data last price, and optionally call **integration** `emit_trade_event(taker_user_id, {volume, count, price})`.
- **Remaining quantity**: If limit and not fully filled, order is **inserted** into the book; if market and partially filled, remainder is cancelled.
- **Cancel**: Order status set to `cancelled`; next time the book is loaded, it is excluded (book is always rebuilt from DB for open limit orders). No in-memory state shared across requests.

This keeps matching deterministic and consistent with the DB; the “event” is the fill, which drives positions and gamification.

---

## System Design

### Why modular monolith first?

- Single deployable simplifies ops and deployment; clear module boundaries allow future extraction (e.g. matching or market-data as a separate service) without rewriting core logic.
- Order book rebuilt from DB on each operation trades some throughput for correctness and simplicity (no distributed lock).

### Why PostgreSQL?

- Strong consistency for orders and positions (no double-fill, correct balances).
- Good fit for audit trail (all orders and fills derivable from DB).

### Why not Kafka (for now)?

- Current scale does not require a message bus; integration is best-effort HTTP POST to gamification. For high throughput, a queue (e.g. Redis Streams or Kafka) between exchange and gamification would allow async, retriable delivery without blocking the matching path.

### Scaling strategy

- **Current**: Single instance; DB as source of truth; in-memory book per request. Suitable for paper trading and demos.
- **Future**: Shard by symbol or user; separate read path for order book/positions (e.g. Redis or dedicated read replica); optional event bus for fills.

---

## API Documentation

- **OpenAPI (Swagger)**: [http://localhost:8002/docs](http://localhost:8002/docs) when running (port 8002 in Docker).
- **ReDoc**: [http://localhost:8002/redoc](http://localhost:8002/redoc).

Base path: `/api/v1`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/signup` | Register (email + password); returns JWT and `user_id` |
| `POST` | `/auth/login` | Login; returns JWT and `user_id` |
| `GET`  | `/auth/me` | Current user (Bearer required) |
| `POST` | `/users` | Create user (optional body); returns `user_id` (no auth) |
| `POST` | `/orders` | Place order (Bearer required) |
| `DELETE`| `/orders/{order_id}` | Cancel order (Bearer required) |
| `GET`  | `/orders` | List my orders (`?user_id=` not needed when using JWT; optional `?symbol=`, `?limit=`) |
| `GET`  | `/orders/book` | Order book (`?symbol=BTC-PERP`, `?depth=20`) |
| `GET`  | `/positions` | My positions (Bearer required) |
| `GET`  | `/ticker` | Last price (`?symbol=BTC-PERP`) |
| `GET`  | `/ticker/klines` | OHLCV from Binance (`?symbol=`, `?interval=1h`, `?limit=24`) |

**Health**: `GET /health` → `{"status": "ok"}`.

---

## Authentication

- **Simple flow**: `POST /api/v1/users` creates a user and returns `user_id`. No password; suitable for demos where the UI stores `user_id` (e.g. in localStorage). *Trading endpoints in this setup may use a different auth mechanism if implemented.*
- **Full auth**: `POST /api/v1/auth/signup` (email + password) or `POST /api/v1/auth/login` returns an access token (JWT). Send `Authorization: Bearer <token>` on orders, positions, and `/auth/me`. Token duration and secret are configurable via env.

---

## Gamification Integration

When a fill occurs, the exchange can POST an event to a gamification API so that “trade” and “volume” quests progress.

1. Set env (e.g. in `.env`):
   - `GAMIFICATION_API_URL` — base URL of gamification API (e.g. `http://host.docker.internal:8000` or quest-saas-api URL).
   - `GAMIFICATION_API_KEY` — optional tenant API key (required by quest-saas-api; gamification-core may not use it).
2. On each fill, the **integration** module sends:
   - `POST {GAMIFICATION_API_URL}/api/v1/events`
   - Body: `{"user_id": "<taker_user_id>", "event_type": "trade", "payload": {"volume": <notional>, "count": 1, "price": <fill_price>}}`
   - Headers: `Content-Type: application/json`, `X-API-Key: <GAMIFICATION_API_KEY>` if set.

If URL or key is unset, no request is sent. Failures are best-effort (no retry in this repo); for production, use a queue and a worker.

---

## Docker Setup

**Requirements**: Docker and Docker Compose.

1. Clone and enter the repo:
   ```bash
   cd mini-derivatives-exchange
   ```
2. Copy env:
   ```bash
   cp .env.example .env
   ```
3. Optional: set `GAMIFICATION_API_URL` and `GAMIFICATION_API_KEY` for trade events.
4. Start API and Postgres:
   ```bash
   docker compose up --build
   ```
5. API: **http://localhost:8002**  
   Docs: **http://localhost:8002/docs**  
   DB: host port **5434** (mapped from container 5432).  
   Code is mounted; edit and save for hot reload.
6. Stop:
   ```bash
   docker compose down
   ```

---

## Local Development

- Python 3.11+.
- PostgreSQL 16.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL if not using defaults
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Ensure DB is created and migrations applied (if using Alembic); the app may create tables on startup.

---

## Testing

- **Unit tests**: Matching engine (`OrderBook.add`, `insert`, `cancel`, `to_bids_asks`) with no DB.
- **Integration tests**: Place/cancel orders, list book, positions; optional mock of gamification HTTP.

Run (when added):

```bash
pytest
```

---

## Scaling & Future Work

- **Rate limiting**: Add per-user or per-IP limits on order placement and cancel (e.g. Redis) before production.
- **Leaderboard**: Consume trade events in gamification-core (or quest-saas-api) and expose leaderboards there; this repo only emits events.
- **WebSocket**: Optional live order book and trades stream for the UI.

---

## License

See repository license. Part of the Gamification & Mini Exchange OSS ecosystem; for full architecture and repo map, see `ARCHITECTURE_AND_PROJECTS.md` in the workspace root (if present) or the main ecosystem repo.
