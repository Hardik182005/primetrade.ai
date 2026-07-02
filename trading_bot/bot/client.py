import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger(__name__)

TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceClientError(Exception):
    pass


class BinanceClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _safe_log_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in params.items() if k != "signature"}

    def _handle_response(self, response: requests.Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            logger.error(
                "Non-JSON response (HTTP %d): %s",
                response.status_code,
                response.text[:200],
            )
            raise BinanceClientError(
                f"Non-JSON response (HTTP {response.status_code}): {response.text[:200]}"
            )

        if response.status_code != 200:
            code = data.get("code", response.status_code)
            msg = data.get("msg", "Unknown API error")
            logger.error("Binance API error %s: %s", code, msg)
            raise BinanceClientError(f"API error {code}: {msg}")

        logger.debug("Response: %s", data)
        return data

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Any:
        params = dict(params or {})
        if signed:
            params = self._sign(params)
        url = f"{self.base_url}{endpoint}"
        logger.debug("GET  %s  params=%s", endpoint, self._safe_log_params(params))
        try:
            response = self.session.get(url, params=params, timeout=10)
            return self._handle_response(response)
        except requests.exceptions.RequestException as exc:
            logger.error("Network error on GET %s: %s", endpoint, exc)
            raise BinanceClientError(f"Network error: {exc}") from exc

    def _post(self, endpoint: str, params: Dict[str, Any]) -> Any:
        params = self._sign(params)
        url = f"{self.base_url}{endpoint}"
        logger.info("POST %s  params=%s", endpoint, self._safe_log_params(params))
        try:
            response = self.session.post(
                url, data=params, timeout=10,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as exc:
            logger.error("Network error on POST %s: %s", endpoint, exc)
            raise BinanceClientError(f"Network error: {exc}") from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
        }
        if order_type.upper() in ("LIMIT", "STOP"):
            if price is None:
                raise BinanceClientError("price is required for LIMIT / STOP orders.")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force
        if order_type.upper() in ("STOP", "STOP_MARKET"):
            if stop_price is None:
                raise BinanceClientError("stop_price is required for STOP / STOP_MARKET orders.")
            params["stopPrice"] = str(stop_price)
        # STOP_MARKET does not take a limit price
        if order_type.upper() == "STOP_MARKET" and "price" in params:
            del params["price"]
            params.pop("timeInForce", None)
        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing %s %s order: symbol=%s  qty=%s  price=%s",
            order_type, side, symbol, quantity, price,
        )
        result = self._post("/fapi/v1/order", params)
        logger.info(
            "Order placed: orderId=%s  status=%s",
            result.get("orderId"), result.get("status"),
        )
        return result

    def get_account_info(self) -> Dict[str, Any]:
        return self._get("/fapi/v2/account", signed=True)

    def get_exchange_info(self) -> Dict[str, Any]:
        return self._get("/fapi/v1/exchangeInfo")

    def get_price(self, symbol: str) -> float:
        data = self._get("/fapi/v1/ticker/price", {"symbol": symbol.upper()})
        return float(data["price"])

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol.upper()
        return self._get("/fapi/v1/openOrders", params, signed=True)
