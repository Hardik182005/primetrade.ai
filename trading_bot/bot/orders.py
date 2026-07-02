import time
from typing import Dict, Any, List, Optional

from bot.client import BinanceClient
from bot.logging_config import get_logger

logger = get_logger(__name__)


def _kv(label: str, value: Any) -> str:
    return f"  {label:<11}: {value}"


def format_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> str:
    rows = [
        _kv("Symbol", symbol),
        _kv("Side", side),
        _kv("Type", order_type),
        _kv("Quantity", quantity),
    ]
    if price is not None:
        rows.append(_kv("Price", price))
    if stop_price is not None:
        rows.append(_kv("Stop Price", stop_price))
    return "\n".join(rows)


def format_order_response(response: Dict[str, Any]) -> str:
    avg_price = response.get("avgPrice", response.get("price", "N/A"))
    rows = [
        _kv("Order ID",  response.get("orderId",      "N/A")),
        _kv("Symbol",    response.get("symbol",        "N/A")),
        _kv("Side",      response.get("side",          "N/A")),
        _kv("Type",      response.get("type",          "N/A")),
        _kv("Status",    response.get("status",        "N/A")),
        _kv("Exec Qty",  response.get("executedQty",   "0")),
        _kv("Avg Price", avg_price),
    ]
    return "\n".join(rows)


# ------------------------------------------------------------------
# Order placement helpers
# ------------------------------------------------------------------

def place_market_order(
    client: BinanceClient, symbol: str, side: str, quantity: float
) -> Dict[str, Any]:
    logger.info("=== MARKET ORDER ===  %s %s  qty=%s", side, symbol, quantity)
    return client.place_order(symbol=symbol, side=side, order_type="MARKET", quantity=quantity)


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
) -> Dict[str, Any]:
    logger.info(
        "=== LIMIT ORDER ===  %s %s  qty=%s  price=%s", side, symbol, quantity, price
    )
    return client.place_order(
        symbol=symbol, side=side, order_type="LIMIT", quantity=quantity, price=price
    )


def place_stop_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    stop_price: float,
) -> Dict[str, Any]:
    logger.info(
        "=== STOP-LIMIT ORDER ===  %s %s  qty=%s  price=%s  stop=%s",
        side, symbol, quantity, price, stop_price,
    )
    return client.place_order(
        symbol=symbol,
        side=side,
        order_type="STOP",
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )


def place_stop_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    stop_price: float,
) -> Dict[str, Any]:
    """Stop-Market order: triggers as a market order when stopPrice is hit."""
    logger.info(
        "=== STOP-MARKET ORDER ===  %s %s  qty=%s  stop=%s",
        side, symbol, quantity, stop_price,
    )
    return client.place_order(
        symbol=symbol,
        side=side,
        order_type="STOP_MARKET",
        quantity=quantity,
        stop_price=stop_price,
    )


def place_twap_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    total_quantity: float,
    slices: int = 5,
    interval_seconds: int = 30,
) -> List[Dict[str, Any]]:
    """Split a large order into equal market slices executed at fixed intervals."""
    qty_per_slice = round(total_quantity / slices, 8)
    logger.info(
        "=== TWAP ORDER ===  %s %s  total=%s  slices=%d  interval=%ds  qty_each=%s",
        side, symbol, total_quantity, slices, interval_seconds, qty_per_slice,
    )
    results: List[Dict[str, Any]] = []
    for i in range(1, slices + 1):
        logger.info("TWAP slice %d/%d -- placing MARKET order qty=%s", i, slices, qty_per_slice)
        result = client.place_order(
            symbol=symbol, side=side, order_type="MARKET", quantity=qty_per_slice
        )
        results.append(result)
        logger.info(
            "TWAP slice %d done -- orderId=%s  status=%s",
            i, result.get("orderId"), result.get("status"),
        )
        if i < slices:
            time.sleep(interval_seconds)
    logger.info("TWAP complete -- %d slices filled", len(results))
    return results
