# SM Arena + Шашки (готовий пакет)

Цей архів містить твій бот SM Arena з доданою грою **Шашки**.

## Що додано
- `app/checkers_game/*` — модуль шашок (PvP у групі, 8×8, обов’язкове взяття, ланцюжки, дамки)
- `app/main.py` — підключено `checkers_router`
- `app/keyboards.py` — у меню додано кнопку **♟️ Шашки**
- `app/i18n.py` — додано переклад `menu_checkers` для всіх мов

## Як запустити
1) Встанови залежності:
   `pip install -r requirements.txt`
2) Впиши токен в `.env` (BOT_TOKEN=...)
   (і не заливай токен у репозиторій)
3) Запуск:
   `python -m app.main`

## Як грати
- У групі: `/checkers` або кнопка меню **♟️ Шашки**
- В приваті: бот підкаже, що PvP краще запускати у групі.


## LiqPay payments (Checkout + webhook)

Add to `.env`:

```
LIQPAY_PUBLIC_KEY=...
LIQPAY_PRIVATE_KEY=...
WEBHOOK_BASE_URL=https://your-domain
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8080
```

Run bot (starts webhook server on WEBHOOK_PORT automatically):

```
python -m app.main
```

Test endpoints:
- `GET /healthz`
- LiqPay callback: `POST /liqpay/callback`
- Payment redirect: `/pay/<order_id>`

### Payment smoke-check (local)

Run with bot/webhook already started:

```powershell
python scripts/payment_smoke_check.py
```

Expected output:
- `OK coins_delta=...`
- `OK coins_idempotent=True`
- `OK failure_keeps_new=True`
- `OK vip_extended_seconds=...`

### Payment diagnostics command

Admin-only command in bot:
- `/paydiag` -> shows payment config flags + order/revenue summary (24h)

### Log controls

Optional env vars:

```dotenv
LOG_LEVEL=INFO
LOG_MAX_MB=10
LOG_BACKUP_COUNT=5
```



## ✅ Production features added (this build)

- LiqPay Checkout + webhook (signature verify + idempotency)
- Coin packs + VIP 30d
- VIP automation:
  - daily coins (+VIP_DAILY_COINS)
  - weekly pack (random shop skin, else +30 coins)
- Admin stats:
  - /stats (today / 7d / 30d revenue + top SKU + arena fee)
- Arena fee (coins) from tournaments:
  - ARENA_FEE_PCT% cut from tournament prize pool, stored to arena revenue

## Local run + public webhook (ngrok)

1) Start the bot:
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

2) In another terminal, start ngrok:
```powershell
ngrok http 8080
```

3) Copy the https URL into .env:
WEBHOOK_BASE_URL=https://xxxx.ngrok-free.dev

4) LiqPay store settings:
Callback URL = https://xxxx.ngrok-free.dev/liqpay/callback
Result URL   = https://xxxx.ngrok-free.dev/

## Railway deploy (24/7)

### Required files in repo
- `Procfile`:
  - `web: python -m app.main`
- `.gitignore`:
  - ignore `.env`, `venv/`, logs, local sqlite files.

### Railway variables
Set in Railway service -> Variables:

```dotenv
BOT_TOKEN=...
ADMIN_IDS=123456789,987654321
LIQPAY_PUBLIC_KEY=...
LIQPAY_PRIVATE_KEY=...
WEBHOOK_BASE_URL=https://<your-service>.up.railway.app
WEBHOOK_HOST=0.0.0.0
```

Notes:
- `WEBHOOK_PORT` is optional on Railway (auto-falls back to platform `PORT`).
- For persistent SQLite on Railway Volume, set:
  - `DB_PATH=/data/sm_arena.db`

### LiqPay callback URLs
- Callback URL: `https://<your-service>.up.railway.app/liqpay/callback`
- Result URL: `https://<your-service>.up.railway.app/pay/success`
