"""
Market-data tools for Friday.

These tools fetch stock quotes via Yahoo Finance (yfinance) so the agent
can answer finance questions without falling back to brittle shell curls.
"""

import json
from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_quote(symbol: str) -> dict[str, Any]:
    import yfinance as yf

    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Symbol cannot be empty.")

    ticker = yf.Ticker(normalized)

    fast_info = getattr(ticker, "fast_info", {}) or {}

    # fast_info is usually quickest, then fall back to recent history.
    last_price = _safe_float(fast_info.get("last_price"))
    previous_close = _safe_float(fast_info.get("previous_close"))

    if last_price is None:
        history = ticker.history(period="5d", interval="1d")
        if history is not None and not history.empty:
            last_price = _safe_float(history["Close"].iloc[-1])
            if len(history["Close"]) > 1:
                previous_close = _safe_float(history["Close"].iloc[-2])

    info: dict[str, Any] = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    market_cap = _safe_float(fast_info.get("market_cap"))
    if market_cap is None:
        market_cap = _safe_float(info.get("marketCap"))

    pe_ratio = _safe_float(fast_info.get("trailing_pe"))
    if pe_ratio is None:
        pe_ratio = _safe_float(info.get("trailingPE"))

    currency = (
        str(info.get("currency") or fast_info.get("currency") or "USD")
        .strip()
        .upper()
    )

    if last_price is None:
        raise RuntimeError(f"No market data returned for symbol '{normalized}'.")

    change = None
    change_pct = None
    if previous_close not in (None, 0):
        change = last_price - previous_close
        change_pct = (change / previous_close) * 100

    return {
        "symbol": normalized,
        "currency": currency,
        "last_price": round(last_price, 4),
        "previous_close": round(previous_close, 4) if previous_close is not None else None,
        "change": round(change, 4) if change is not None else None,
        "change_percent": round(change_pct, 4) if change_pct is not None else None,
        "market_cap": int(market_cap) if market_cap is not None else None,
        "trailing_pe": round(pe_ratio, 4) if pe_ratio is not None else None,
    }


@tool
def get_stock_quote(symbol: str) -> str:
    """Fetch a real-time-ish stock quote (Yahoo Finance) for one ticker symbol."""
    try:
        quote = _fetch_quote(symbol)
    except Exception as exc:
        return f"ERROR: {exc}"

    payload = {
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "quote": quote,
    }
    return json.dumps(payload, indent=2)


@tool
def compare_stock_prices(symbol_a: str = "NVDA", symbol_b: str = "AMD") -> str:
    """Compare two stock symbols using Yahoo Finance quote data."""
    try:
        first = _fetch_quote(symbol_a)
        second = _fetch_quote(symbol_b)
    except Exception as exc:
        return f"ERROR: {exc}"

    a_price = first["last_price"]
    b_price = second["last_price"]

    comparison: dict[str, Any] = {
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "quotes": [first, second],
    }

    if a_price and b_price:
        comparison["price_difference"] = {
            f"{first['symbol']}_minus_{second['symbol']}": round(a_price - b_price, 4),
            f"{first['symbol']}_to_{second['symbol']}_ratio": round(a_price / b_price, 6),
        }

    return json.dumps(comparison, indent=2)
