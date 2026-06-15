# API

FastAPI runs with:

```bash
make fastapi
```

Docs are available at `/docs`.

Implemented endpoints:

- `GET /health`
- `GET /broker/status`
- `POST /broker/connect`
- `POST /broker/disconnect`
- `GET /broker/account`
- `GET /broker/symbols/{symbol}`
- `GET /broker/tick/{symbol}`
- `GET /broker/positions`
- `GET /broker/orders`
- `POST /bot/start`
- `POST /bot/stop`
- `POST /bot/kill-switch`
- `POST /bot/reset-kill-switch`
- `GET /bot/status`
- `POST /live/arm`
- `POST /live/disarm`
- `POST /live/run-once`
- `POST /live/place-order`
- `POST /live/close-position`
- `POST /live/close-all-positions`
- `POST /backtests/run`
- `GET /backtests/{id}`
- `GET /signals/recent`
- `GET /risk/events`
- `POST /ai/signal-explanation`
- `POST /ai/trade-review`

Password values are never returned.
