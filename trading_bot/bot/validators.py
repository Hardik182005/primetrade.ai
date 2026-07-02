import re
from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP", "STOP_MARKET", "TWAP"}
SYMBOL_RE = re.compile(r"^[A-Z]{2,10}USDT$")


class ValidationError(ValueError):
    pass


def validate_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s:
        raise ValidationError("Symbol cannot be empty.")
    if not SYMBOL_RE.match(s):
        raise ValidationError(
            f"Invalid symbol '{s}'. Expected format: BTCUSDT, ETHUSDT, etc."
        )
    return s


def validate_side(side: str) -> str:
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValidationError(f"Side must be BUY or SELL, got '{s}'.")
    return s


def validate_order_type(order_type: str) -> str:
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type must be MARKET, LIMIT, STOP, or TWAP — got '{t}'."
        )
    return t


def validate_quantity(quantity: str) -> float:
    try:
        q = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Quantity must be a positive number, got '{quantity}'.")
    if q <= 0:
        raise ValidationError(f"Quantity must be greater than zero, got {q}.")
    return q


def validate_price(price: Optional[str], required: bool = True) -> Optional[float]:
    if price is None or str(price).strip() in ("", "None"):
        if required:
            raise ValidationError("Price is required for LIMIT and STOP orders.")
        return None
    try:
        p = float(price)
    except (ValueError, TypeError):
        raise ValidationError(f"Price must be a positive number, got '{price}'.")
    if p <= 0:
        raise ValidationError(f"Price must be greater than zero, got {p}.")
    return p
