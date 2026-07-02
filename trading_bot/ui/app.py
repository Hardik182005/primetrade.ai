"""Flask web UI for the Binance Futures Testnet trading bot."""

import sys
import os

# Ensure trading_bot root is on sys.path so `bot.*` imports work from any cwd
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from typing import Tuple

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

from bot.client import BinanceClient, BinanceClientError
from bot.logging_config import get_logger, setup_logging
from bot.orders import place_limit_order, place_market_order, place_stop_limit_order
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

load_dotenv()
setup_logging("logs/trading_bot_ui.log")
logger = get_logger(__name__)

import os as _os
_template_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "templates")
app = Flask(__name__, template_folder=_template_dir)


def _client() -> Tuple[BinanceClient, None]:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise BinanceClientError(
            "API credentials not set. Add BINANCE_API_KEY and BINANCE_API_SECRET to .env"
        )
    return BinanceClient(api_key=api_key, api_secret=api_secret)


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/trade")
def trade():
    return render_template("place_order.html")


# ------------------------------------------------------------------
# REST API endpoints consumed by the UI
# ------------------------------------------------------------------

@app.route("/api/price/<symbol>")
def api_price(symbol: str):
    try:
        sym = validate_symbol(symbol)
        client = _client()
        p = client.get_price(sym)
        return jsonify({"symbol": sym, "price": p})
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 422
    except BinanceClientError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/order", methods=["POST"])
def api_order():
    data = request.get_json(silent=True) or {}
    logger.info("UI order request: %s", data)

    try:
        symbol = validate_symbol(data.get("symbol", ""))
        side = validate_side(data.get("side", ""))
        order_type = validate_order_type(data.get("type", ""))
        quantity = validate_quantity(str(data.get("quantity", "")))
        price = None
        stop_price = None
        if order_type in ("LIMIT", "STOP"):
            price = validate_price(str(data.get("price", "")), required=True)
        if order_type == "STOP":
            stop_price = validate_price(str(data.get("stopPrice", "")), required=True)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 422

    try:
        client = _client()
        if order_type == "MARKET":
            resp = place_market_order(client, symbol, side, quantity)
        elif order_type == "LIMIT":
            resp = place_limit_order(client, symbol, side, quantity, price)
        elif order_type == "STOP":
            resp = place_stop_limit_order(client, symbol, side, quantity, price, stop_price)
        else:
            return jsonify({"error": "TWAP is only available via the CLI."}), 400

        logger.info("UI order success: orderId=%s status=%s", resp.get("orderId"), resp.get("status"))
        return jsonify({"success": True, "order": resp})

    except BinanceClientError as exc:
        logger.error("UI order failed: %s", exc)
        return jsonify({"error": str(exc)}), 400


@app.route("/api/account")
def api_account():
    try:
        client = _client()
        info = client.get_account_info()
        assets = [
            a for a in info.get("assets", [])
            if float(a.get("walletBalance", 0)) > 0
        ]
        return jsonify({"assets": assets})
    except BinanceClientError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/orders")
def api_orders():
    symbol = request.args.get("symbol", "").strip()
    try:
        client = _client()
        orders = client.get_open_orders(symbol or None)
        return jsonify({"orders": orders})
    except BinanceClientError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        from openai import OpenAI as _OpenAI
    except ImportError:
        return jsonify({"error": "openai package not installed. Run: pip install openai"}), 500

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key:
        return jsonify({"error": "OPENAI_API_KEY not configured"}), 500

    btc_price = "unknown"
    try:
        bc = _client()
        btc_price = f"${float(bc.get_price('BTCUSDT')):,.2f}"
    except Exception:
        pass

    system_prompt = (
        f"You are TradeBot, the witty AI sidekick for PrimeTrade.ai — a Binance Futures Testnet trading bot. "
        f"You are sharp, sarcastic in a fun way, and scarily knowledgeable about crypto trading. "
        f"Live BTC price right now: {btc_price}. "
        f"This bot supports Market, Limit, Stop-Market, and TWAP orders on Binance Futures Testnet (USDT-M). "
        f"Users can place orders via the Trade Dashboard at /trade. "
        f"The bot uses HMAC SHA256 signed requests to Binance testnet.binancefuture.com. "
        f"If asked about placing an order, guide them to the Trade tab. "
        f"Keep answers SHORT (2-3 sentences max), conversational, punchy, and entertaining — like a Wall Street quant who moonlights as a stand-up comedian. "
        f"Never use markdown formatting. No asterisks, no hashtags, no bullet dashes. Plain text only. "
        f"If you don't know something, make a self-deprecating joke about it."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-8:]:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        oai = _OpenAI(api_key=openai_key)
        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=180,
            temperature=0.88,
        )
        reply = resp.choices[0].message.content.strip()
        logger.info("Chat reply generated: %d chars", len(reply))
        return jsonify({"reply": reply})
    except Exception as exc:
        logger.error("OpenAI error: %s", exc)
        return jsonify({"error": f"AI error: {str(exc)[:120]}"}), 500


@app.route("/api/voice", methods=["POST"])
def api_voice():
    import requests as _req
    from flask import Response as _Resp

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Empty text"}), 400

    el_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not el_key:
        return jsonify({"error": "ELEVENLABS_API_KEY not configured"}), 500

    voice_id = "ErXwobaYiN019PkySvjV"  # Antoni — energetic conversational voice
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": el_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.3},
    }

    r = _req.post(url, json=payload, headers=headers, timeout=25)
    if r.status_code != 200:
        logger.error("ElevenLabs error %s: %s", r.status_code, r.text[:200])
        return jsonify({"error": f"ElevenLabs {r.status_code}: {r.text[:120]}"}), 500

    return _Resp(
        r.content,
        mimetype="audio/mpeg",
        headers={"Content-Disposition": "inline", "Cache-Control": "no-cache"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0", use_reloader=False)
