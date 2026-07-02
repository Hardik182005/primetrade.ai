#!/usr/bin/env python3
"""Binance Futures Testnet Trading Bot - CLI entry point."""

import os
import sys
from typing import Optional

# Force UTF-8 output so Unicode characters render on all terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from bot.client import BinanceClient, BinanceClientError
from bot.logging_config import setup_logging, get_logger
from bot.orders import (
    place_market_order,
    place_limit_order,
    place_stop_limit_order,
    place_stop_market_order,
    place_twap_order,
    format_order_summary,
    format_order_response,
)
from bot.validators import (
    ValidationError,
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
)

load_dotenv()

app = typer.Typer(
    name="trading-bot",
    help="Binance Futures Testnet trading bot - place MARKET, LIMIT, STOP-LIMIT, and TWAP orders.",
    add_completion=False,
    pretty_exceptions_show_locals=False,
)
console = Console()
logger = get_logger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_client() -> BinanceClient:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        console.print(
            "[bold red][FAIL] Missing credentials.[/]  Set [cyan]BINANCE_API_KEY[/] and "
            "[cyan]BINANCE_API_SECRET[/] in [green].env[/] or your environment."
        )
        raise typer.Exit(1)
    return BinanceClient(api_key=api_key, api_secret=api_secret)


def _ask_validated(prompt: str, validator, choices=None, current=None):
    """Re-prompt until the validator accepts the value."""
    while True:
        try:
            raw = (
                Prompt.ask(f"[bold]{prompt}[/]", choices=choices)
                if choices
                else Prompt.ask(f"[bold]{prompt}[/]", default=current or "")
            )
            return validator(raw)
        except ValidationError as exc:
            console.print(f"  [red][!] {exc}[/]")


def _interactive_inputs(symbol, side, order_type, quantity, price, stop_price):
    console.rule("[bold #7C3AED]  PrimeTrade - Interactive Order  [/]")
    console.print()

    symbol = _ask_validated(
        "Symbol (e.g. BTCUSDT, ETHUSDT)", validate_symbol,
        current=symbol,
    ) if not symbol else validate_symbol(symbol)

    side = _ask_validated(
        "Side", validate_side, choices=["BUY", "SELL"],
    ) if not side else validate_side(side)

    order_type = _ask_validated(
        "Order type", validate_order_type, choices=["MARKET", "LIMIT", "STOP_MARKET", "TWAP"],
    ) if not order_type else validate_order_type(order_type)

    quantity = _ask_validated(
        "Quantity", validate_quantity,
    ) if not quantity else validate_quantity(str(quantity))

    if order_type in ("LIMIT", "STOP"):
        price = _ask_validated(
            "Price (USDT)", lambda v: validate_price(v, required=True),
        ) if not price else validate_price(str(price), required=True)

    if order_type in ("STOP", "STOP_MARKET"):
        stop_price = _ask_validated(
            "Stop price (USDT)", lambda v: validate_price(v, required=True),
        ) if not stop_price else validate_price(str(stop_price), required=True)

    return symbol, side, order_type, quantity, price, stop_price


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------

@app.command()
def place(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Trading pair, e.g. BTCUSDT"),
    side: Optional[str] = typer.Option(None, "--side", help="BUY or SELL"),
    order_type: Optional[str] = typer.Option(None, "--type", "-t", help="MARKET | LIMIT | STOP_MARKET | TWAP"),
    quantity: Optional[float] = typer.Option(None, "--qty", "-q", help="Order quantity"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Limit / stop-limit price"),
    stop_price: Optional[float] = typer.Option(None, "--stop-price", help="Stop trigger price (STOP only)"),
    twap_slices: int = typer.Option(5, "--twap-slices", help="Number of TWAP slices"),
    twap_interval: int = typer.Option(30, "--twap-interval", help="Seconds between TWAP slices"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive guided mode"),
    log_file: str = typer.Option("logs/trading_bot.log", "--log-file", help="Path for the log file"),
):
    """Place an order on Binance Futures Testnet (USDT-M)."""
    setup_logging(log_file)
    logger.info("CLI started - pid=%d", os.getpid())

    # Resolve inputs -------------------------------------------------------
    needs_interactive = interactive or not all([symbol, side, order_type, quantity])
    if needs_interactive:
        symbol, side, order_type, quantity, price, stop_price = _interactive_inputs(
            symbol, side, order_type, quantity, price, stop_price
        )
    else:
        try:
            symbol = validate_symbol(symbol)
            side = validate_side(side)
            order_type = validate_order_type(order_type)
            quantity = validate_quantity(str(quantity))
            if order_type in ("LIMIT", "STOP"):
                price = validate_price(str(price) if price else None, required=True)
            if order_type in ("STOP", "STOP_MARKET"):
                stop_price = validate_price(
                    str(stop_price) if stop_price else None, required=True
                )
        except ValidationError as exc:
            console.print(f"[bold red][FAIL] Validation error:[/] {exc}")
            raise typer.Exit(1)

    # Print summary --------------------------------------------------------
    console.print()
    console.print(
        Panel(
            format_order_summary(symbol, side, order_type, quantity, price, stop_price),
            title="[bold]Order Request[/]",
            border_style="#7C3AED",
        )
    )

    client = _get_client()

    # Execute --------------------------------------------------------------
    try:
        if order_type == "MARKET":
            response = place_market_order(client, symbol, side, quantity)
            _print_response(response)

        elif order_type == "LIMIT":
            response = place_limit_order(client, symbol, side, quantity, price)
            _print_response(response)

        elif order_type == "STOP":
            response = place_stop_limit_order(
                client, symbol, side, quantity, price, stop_price
            )
            _print_response(response)

        elif order_type == "STOP_MARKET":
            response = place_stop_market_order(
                client, symbol, side, quantity, stop_price
            )
            _print_response(response)

        elif order_type == "TWAP":
            console.print(
                f"\n[yellow]Executing TWAP: {twap_slices} slices of "
                f"{quantity / twap_slices:.8g} {symbol}, every {twap_interval}s[/]"
            )
            responses = place_twap_order(
                client, symbol, side, quantity, twap_slices, twap_interval
            )
            for idx, resp in enumerate(responses, 1):
                console.print(f"\n[dim]-- Slice {idx}/{twap_slices} --[/]")
                _print_response(resp)
            console.print(
                f"\n[bold green][OK] TWAP complete - {len(responses)} slices executed.[/]"
            )

    except BinanceClientError as exc:
        console.print(f"\n[bold red][FAIL] Order failed:[/] {exc}")
        logger.error("Order failed: %s", exc)
        raise typer.Exit(1)


@app.command()
def price(
    symbol: str = typer.Argument(..., help="Symbol to fetch, e.g. BTCUSDT"),
    log_file: str = typer.Option("logs/trading_bot.log", "--log-file"),
):
    """Fetch the current mark price of a symbol from testnet."""
    setup_logging(log_file)
    try:
        symbol = validate_symbol(symbol)
    except ValidationError as exc:
        console.print(f"[red][!] {exc}[/]")
        raise typer.Exit(1)
    client = _get_client()
    try:
        p = client.get_price(symbol)
        console.print(f"\n[bold]{symbol}[/]  mark price: [bold green]{p:,.2f} USDT[/]\n")
    except BinanceClientError as exc:
        console.print(f"[red][!] {exc}[/]")
        raise typer.Exit(1)


@app.command()
def account(
    log_file: str = typer.Option("logs/trading_bot.log", "--log-file"),
):
    """Show testnet account balance summary."""
    setup_logging(log_file)
    client = _get_client()
    try:
        info = client.get_account_info()
    except BinanceClientError as exc:
        console.print(f"[red][!] {exc}[/]")
        raise typer.Exit(1)

    assets = [a for a in info.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    table = Table(title="Testnet Account Balances", box=box.ROUNDED, border_style="#7C3AED")
    table.add_column("Asset", style="bold")
    table.add_column("Wallet Balance", justify="right")
    table.add_column("Unrealised PnL", justify="right")
    for a in assets:
        pnl = float(a.get("unrealizedProfit", 0))
        pnl_str = f"[green]+{pnl:.4f}[/]" if pnl >= 0 else f"[red]{pnl:.4f}[/]"
        table.add_row(
            a.get("asset"),
            f"{float(a.get('walletBalance', 0)):.4f}",
            pnl_str,
        )
    console.print()
    console.print(table)
    console.print()


# ------------------------------------------------------------------
# Private print helper
# ------------------------------------------------------------------

def _print_response(response: dict) -> None:
    status = response.get("status", "")
    color = "green" if status in ("FILLED", "NEW", "PARTIALLY_FILLED") else "yellow"
    console.print(
        Panel(
            format_order_response(response),
            title=f"[bold {color}]Order Response - {status}[/]",
            border_style=color,
        )
    )
    console.print(
        f"[bold green][OK] Order placed successfully![/]  "
        f"orderId={response.get('orderId')}\n"
    )
    logger.info("CLI: order complete - orderId=%s", response.get("orderId"))


if __name__ == "__main__":
    app()
