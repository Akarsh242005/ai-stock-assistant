"""
============================================================
Data Pipeline Script
============================================================
Batch-fetches historical OHLCV data for a watchlist,
validates it, and caches to Parquet for fast reuse.

Usage:
  python scripts/fetch_data.py
  python scripts/fetch_data.py --symbols NIFTY AAPL MSFT
  python scripts/fetch_data.py --period 5y --output ./data

Output files:
  data/NIFTY_1d.parquet
  data/RELIANCE_NS_1d.parquet
  data/summary.json
============================================================
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))
from services.data_service import fetch_stock_data, fetch_stock_info, resolve_ticker

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")


# ── Default watchlist ─────────────────────────────────────
DEFAULT_SYMBOLS = [
    "NIFTY", "SENSEX",
    "RELIANCE", "TCS", "INFOSYS", "HDFC", "WIPRO",
    "AAPL", "MSFT", "GOOGL", "TSLA", "AMZN",
]


# ═══════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════

def validate_df(df: pd.DataFrame, symbol: str) -> tuple[bool, list]:
    """
    Run quality checks on fetched DataFrame.
    Returns (is_valid, list_of_warnings).
    """
    warnings = []

    if df.empty:
        return False, ["DataFrame is empty"]

    if len(df) < 50:
        warnings.append(f"Only {len(df)} rows — too few for reliable modelling (need 50+)")

    # Check for required columns
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in df.columns:
            return False, [f"Missing required column: {col}"]

    # Check for nulls
    null_counts = df[["Open", "High", "Low", "Close"]].isnull().sum()
    if null_counts.any():
        warnings.append(f"Nulls detected: {null_counts[null_counts > 0].to_dict()}")

    # Check OHLC logic: High >= Low, High >= Close, Low <= Close
    bad_high_low = (df["High"] < df["Low"]).sum()
    if bad_high_low > 0:
        warnings.append(f"{bad_high_low} rows where High < Low (data quality issue)")

    # Check for zero or negative prices
    if (df["Close"] <= 0).any():
        warnings.append("Negative or zero close prices found — check data source")

    # Check date index
    if not isinstance(df.index, pd.DatetimeIndex):
        warnings.append("Index is not DatetimeIndex — may cause issues with models")

    # Missing trading days (rough check: > 5% gaps vs expected)
    if len(df) > 10:
        expected_days = pd.bdate_range(df.index[0], df.index[-1])
        coverage      = len(df) / len(expected_days) * 100
        if coverage < 85:
            warnings.append(f"Date coverage {coverage:.1f}% — possible missing trading days")

    return True, warnings


def compute_statistics(df: pd.DataFrame) -> dict:
    """Compute summary statistics for the dataset."""
    close    = df["Close"]
    returns  = close.pct_change().dropna()

    return {
        "rows":           len(df),
        "date_from":      df.index[0].strftime("%Y-%m-%d"),
        "date_to":        df.index[-1].strftime("%Y-%m-%d"),
        "close_latest":   round(float(close.iloc[-1]), 4),
        "close_min":      round(float(close.min()), 4),
        "close_max":      round(float(close.max()), 4),
        "daily_return_mean": round(float(returns.mean() * 100), 4),
        "daily_return_std":  round(float(returns.std() * 100), 4),
        "annual_vol_pct":    round(float(returns.std() * (252 ** 0.5) * 100), 2),
        "total_return_pct":  round(float((close.iloc[-1] / close.iloc[0] - 1) * 100), 2),
        "null_count":        int(df[["Close"]].isnull().sum().sum()),
    }


# ═══════════════════════════════════════════════════════════
# FETCH + CACHE
# ═══════════════════════════════════════════════════════════

def fetch_and_cache(
    symbol:    str,
    period:    str,
    interval:  str,
    output_dir: Path,
    force:     bool = False,
) -> dict:
    """
    Fetch data for one symbol, validate, and save to parquet.
    Returns a result summary dict.
    """
    ticker   = resolve_ticker(symbol)
    safe     = ticker.replace("^", "").replace(".", "_")
    filename = output_dir / f"{safe}_{interval}.parquet"

    # Skip if cached and not forced
    if filename.exists() and not force:
        log.info(f"{symbol:12} CACHED  →  {filename.name}")
        df = pd.read_parquet(filename)
        is_valid, warnings = validate_df(df, symbol)
        return {
            "symbol": symbol, "ticker": ticker, "status": "cached",
            "file": str(filename), "warnings": warnings,
            "stats": compute_statistics(df),
        }

    # Fetch
    try:
        log.info(f"{symbol:12} Fetching ({period}, {interval})...")
        df = fetch_stock_data(symbol, period=period, interval=interval)

        is_valid, warnings = validate_df(df, symbol)
        if not is_valid:
            log.error(f"{symbol:12} INVALID — {warnings}")
            return {"symbol": symbol, "ticker": ticker, "status": "invalid", "warnings": warnings}

        if warnings:
            for w in warnings:
                log.warning(f"{symbol:12} {w}")

        # Save
        df.to_parquet(filename)
        stats = compute_statistics(df)
        log.info(
            f"{symbol:12} OK  →  {len(df)} rows  |  "
            f"{stats['date_from']} → {stats['date_to']}  |  "
            f"latest={stats['close_latest']}"
        )

        return {
            "symbol":  symbol,
            "ticker":  ticker,
            "status":  "ok",
            "file":    str(filename),
            "warnings": warnings,
            "stats":   stats,
        }

    except Exception as e:
        log.error(f"{symbol:12} ERROR — {e}")
        return {"symbol": symbol, "ticker": ticker, "status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Batch stock data pipeline")
    parser.add_argument("--symbols",  nargs="*",     default=DEFAULT_SYMBOLS)
    parser.add_argument("--period",   default="2y",  help="yfinance period (1y/2y/5y/max)")
    parser.add_argument("--interval", default="1d",  help="Data interval (1d/1h/5m)")
    parser.add_argument("--output",   default="data", help="Output directory")
    parser.add_argument("--force",    action="store_true", help="Re-fetch even if cached")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*58}")
    print(f"  AI StockVision — Data Pipeline")
    print(f"  Symbols:  {len(args.symbols)} stocks")
    print(f"  Period:   {args.period}  |  Interval: {args.interval}")
    print(f"  Output:   {output_dir.resolve()}")
    print(f"{'='*58}\n")

    results = []
    for sym in args.symbols:
        r = fetch_and_cache(sym, args.period, args.interval, output_dir, args.force)
        results.append(r)

    # Save summary JSON
    summary = {
        "generated_at": datetime.now().isoformat(),
        "period":        args.period,
        "interval":      args.interval,
        "total":         len(results),
        "ok":            sum(1 for r in results if r["status"] in ("ok", "cached")),
        "errors":        sum(1 for r in results if r["status"] == "error"),
        "symbols":       results,
    }
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*58}")
    print(f"  Pipeline complete")
    print(f"  ✓ Success : {summary['ok']}/{summary['total']}")
    print(f"  ✗ Errors  : {summary['errors']}/{summary['total']}")
    print(f"  Summary   → {summary_path}")
    print(f"{'='*58}\n")

    if summary["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
