<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Binance-Futures_Testnet-F0B90B?style=for-the-badge&logo=binance&logoColor=black" />
  <img src="https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/ElevenLabs-Voice_AI-000000?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Vercel-Deployed-000000?style=for-the-badge&logo=vercel&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

<h1 align="center">⚡ PrimeTrade.ai — Binance Futures Trading Bot</h1>

<p align="center">
  <b>Automated crypto futures trading bot with Market, Limit, Stop-Market & TWAP orders · AI voice chatbot · Live web dashboard</b>
</p>

<p align="center">
  <a href="https://primetrade-ai.vercel.app"><strong>🌐 Live Demo →</strong></a>
</p>

---

## What it does

PrimeTrade.ai is a full-stack trading bot for **Binance Futures Testnet (USDT-M)**. It lets you place orders via a terminal CLI or a slick web dashboard — complete with an animated pipeline, live BTC price, and a voice-enabled AI chatbot that can answer questions about your trades.

```
Your Input → Validators → Bot Engine (HMAC signed) → Binance Testnet API → Order Filled
```

---

## Features

| Feature | Details |
|---|---|
| **4 Order Types** | Market, Limit, Stop-Market, TWAP (time-weighted slices) |
| **HMAC SHA256** | All requests signed per Binance Futures spec |
| **Input Validation** | Symbol regex, price/qty guards, side/type whitelist |
| **Rich CLI** | Typer + Rich coloured output, interactive prompt mode |
| **Flask Web UI** | Dark ticker bar, animated order pipeline, live BTC price card |
| **AI Voice Chatbot** | GPT-4o-mini brain + ElevenLabs voice + Web Speech API mic |
| **Structured Logging** | Rotating file handler (5 MB × 3 backups), per-request context |
| **Vercel Deployment** | Single serverless function via `@vercel/python` |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── client.py          # Binance REST client — HMAC signing, price, orders, account
│   ├── orders.py          # place_market_order, place_limit_order, place_twap_order …
│   ├── validators.py      # validate_symbol, validate_side, validate_quantity …
│   └── logging_config.py  # RotatingFileHandler setup
├── ui/
│   ├── app.py             # Flask app — /trade, /api/order, /api/chat, /api/voice
│   └── templates/
│       ├── base.html      # Ticker bar, navbar, floating AI chatbot
│       ├── index.html     # Landing page — animated 5-node pipeline
│       └── place_order.html  # Trading dashboard — tabs + sidebar
├── api/
│   └── index.py           # Vercel entry point
├── logs/
│   ├── market_order.log   # Live MARKET order output
│   └── limit_order.log    # Live LIMIT order output
├── cli.py                 # CLI entry point
├── requirements.txt
├── vercel.json
└── .env.example
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/Hardik182005/binance-futures-trading-bot.git
cd binance-futures-trading-bot
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_secret
OPENAI_API_KEY=sk-proj-...
ELEVENLABS_API_KEY=your_elevenlabs_key
```

> **Get Binance Testnet keys:** [testnet.binancefuture.com](https://testnet.binancefuture.com) → Sign in with GitHub → API Management → Generate Key

### 3. Run the web dashboard

```bash
python ui/app.py
# Open http://localhost:5000
```

---

## CLI Usage

### Place a MARKET order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

```
╭─ Order Result ────────────────────────────────────╮
│  Symbol     : BTCUSDT                              │
│  Side       : BUY                                  │
│  Type       : MARKET                               │
│  Qty        : 0.001                                │
│  Status     : FILLED                               │
│  Order ID   : 18434401311                          │
╰────────────────────────────────────────────────────╯
```

### Place a LIMIT order

```bash
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --qty 0.05 --price 2600
```

### Place a TWAP order — 5 slices, 30 s apart

```bash
python cli.py place --symbol BTCUSDT --side BUY --type TWAP --qty 0.005 \
  --twap-slices 5 --twap-interval 30
```

```
[Slice 1/5] Placed MARKET BUY 0.001 BTCUSDT — orderId=18434401312
[Slice 2/5] Placed MARKET BUY 0.001 BTCUSDT — orderId=18434401313
...
TWAP complete — 5/5 slices filled
```

### Interactive mode

```bash
python cli.py place --interactive
```

### Fetch live BTC price

```bash
python cli.py price BTCUSDT
# BTCUSDT: $60,126.90
```

### Account balances

```bash
python cli.py account
```

```
╭─ Account Balances ─────────────────────────────────╮
│  USDT   walletBalance : 10000.00                   │
│  BTC    walletBalance : 0.05000000                 │
╰────────────────────────────────────────────────────╯
```

---

## Web Dashboard

Start the server:

```bash
python ui/app.py
```

| Page | URL | What it does |
|---|---|---|
| Landing | `/` | Animated pipeline + live BTC price + AI chatbot |
| Dashboard | `/trade` | Place orders + sidebar with account, settings, help |

### API Endpoints

```
GET  /api/price/<symbol>     — Live price from Binance Testnet
POST /api/order              — Place Market / Limit / Stop order
GET  /api/account            — Wallet balances
POST /api/chat               — AI chatbot (OpenAI GPT-4o-mini)
POST /api/voice              — Text-to-speech (ElevenLabs)
```

---

## AI Voice Chatbot (TradeBot)

Every page has a floating **🤖** button. Click it to open TradeBot.

- **Text chat** — Ask anything about trading, order types, BTC price
- **Voice Mode** — Click the mic toggle; speak your question; TradeBot replies out loud via ElevenLabs
- **Start/Stop** — One button to toggle listening on/off
- **Personality** — Sarcastic, witty, scarily knowledgeable about crypto

```
You: "What's BTC doing right now?"
TradeBot: "BTC is currently sitting at $60,126 — basically the price of a used car
           that depreciates 10% overnight. Perfect for our portfolio!"
```

---

## How HMAC Signing Works

```python
import hmac, hashlib, time
from urllib.parse import urlencode

def sign(params: dict, secret: str) -> dict:
    params["timestamp"] = int(time.time() * 1000)
    query_string = urlencode(params)
    params["signature"] = hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return params
```

---

## Deployment (Vercel)

```bash
cd trading_bot
vercel --prod
```

Set environment secrets in Vercel dashboard or CLI:

```bash
vercel env add BINANCE_API_KEY
vercel env add BINANCE_API_SECRET
vercel env add OPENAI_API_KEY
vercel env add ELEVENLABS_API_KEY
```

`vercel.json` routes all traffic through `api/index.py` which imports the Flask app.

---

## Log Output

```
2026-07-02 13:23:44 | INFO  | bot.orders  | Placing MARKET BUY 0.001 BTCUSDT
2026-07-02 13:23:44 | INFO  | bot.client  | POST /fapi/v1/order
2026-07-02 13:23:45 | INFO  | bot.client  | Order placed: orderId=18434401311 status=FILLED
```

Logs rotate at 5 MB, keeping 3 backups. See `logs/market_order.log` and `logs/limit_order.log` for real testnet output.

---

## Assignment Checklist

| Requirement | Status |
|---|---|
| MARKET orders on Binance Futures Testnet | ✅ |
| LIMIT orders | ✅ |
| BUY + SELL sides | ✅ |
| Typer CLI with input validation | ✅ |
| Clear order summary output | ✅ |
| Structured logging (rotating file) | ✅ |
| Exception handling (API + validation) | ✅ |
| **Bonus:** Stop-Market order type | ✅ |
| **Bonus:** TWAP execution (timed slices) | ✅ |
| **Bonus:** Interactive CLI mode | ✅ |
| **Bonus:** Web dashboard (Flask) | ✅ |
| **Bonus:** AI voice chatbot (OpenAI + ElevenLabs) | ✅ |
| **Bonus:** Deployed on Vercel | ✅ |

---

## License

MIT © 2026 Hardik Hinduja
