"""
============================================================
Model Training Script
============================================================
Trains and saves LSTM, Prophet, and ARIMA models for a
given stock symbol. Run this offline to pre-build model
weights so the API serves predictions instantly.

Usage:
  python scripts/train_models.py --symbol NIFTY
  python scripts/train_models.py --symbol RELIANCE --epochs 30
  python scripts/train_models.py --symbols NIFTY TCS AAPL --epochs 25
============================================================
"""

import sys
import os
import json
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from services.data_service    import fetch_stock_data
from services.lstm_service    import train_and_predict
from services.prophet_service import forecast_with_prophet
from services.arima_service   import forecast_with_arima

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("train")

RESULTS_DIR = Path(__file__).parent.parent / "models"
RESULTS_DIR.mkdir(exist_ok=True)


def train_symbol(symbol: str, epochs: int, period: str) -> dict:
    """
    Train all three models for a symbol and save results.
    Returns a summary dict with metrics for each model.
    """
    log.info(f"{'='*52}")
    log.info(f"  Training: {symbol}  |  period={period}  |  epochs={epochs}")
    log.info(f"{'='*52}")

    t0 = time.time()

    # ── Fetch data ────────────────────────────────────────
    log.info(f"[1/4] Fetching {symbol} data ({period})...")
    try:
        df = fetch_stock_data(symbol, period=period)
        log.info(f"      {len(df)} rows | {df.index[0].date()} → {df.index[-1].date()}")
    except Exception as e:
        log.error(f"Data fetch failed: {e}")
        return {"symbol": symbol, "status": "error", "error": str(e)}

    results = {"symbol": symbol, "period": period, "rows": len(df), "models": {}}

    # ── LSTM ─────────────────────────────────────────────
    log.info(f"[2/4] Training LSTM (epochs={epochs})...")
    t1 = time.time()
    try:
        lstm_result = train_and_predict(df, symbol, epochs=epochs, use_cache=False)
        elapsed     = round(time.time() - t1, 1)
        results["models"]["lstm"] = {
            "status":    "ok",
            "rmse":      lstm_result["metrics"]["rmse"],
            "mae":       lstm_result["metrics"]["mae"],
            "mape":      lstm_result["metrics"]["mape"],
            "direction": lstm_result["direction"],
            "elapsed_s": elapsed,
        }
        log.info(
            f"      LSTM done in {elapsed}s | "
            f"RMSE={lstm_result['metrics']['rmse']:.4f} | "
            f"MAPE={lstm_result['metrics']['mape']:.2f}% | "
            f"{lstm_result['direction']}"
        )
    except Exception as e:
        results["models"]["lstm"] = {"status": "error", "error": str(e)}
        log.error(f"      LSTM failed: {e}")

    # ── Prophet ──────────────────────────────────────────
    log.info(f"[3/4] Training Prophet...")
    t1 = time.time()
    try:
        prophet_result = forecast_with_prophet(df, symbol)
        elapsed        = round(time.time() - t1, 1)
        results["models"]["prophet"] = {
            "status":    "ok",
            "rmse":      prophet_result["metrics"]["rmse"],
            "mae":       prophet_result["metrics"]["mae"],
            "mape":      prophet_result["metrics"]["mape"],
            "direction": prophet_result["direction"],
            "elapsed_s": elapsed,
        }
        log.info(
            f"      Prophet done in {elapsed}s | "
            f"RMSE={prophet_result['metrics']['rmse']:.4f} | "
            f"{prophet_result['direction']}"
        )
    except Exception as e:
        results["models"]["prophet"] = {"status": "error", "error": str(e)}
        log.error(f"      Prophet failed: {e}")

    # ── ARIMA ────────────────────────────────────────────
    log.info(f"[4/4] Running ARIMA (auto-order selection)...")
    t1 = time.time()
    try:
        arima_result = forecast_with_arima(df, symbol)
        elapsed      = round(time.time() - t1, 1)
        results["models"]["arima"] = {
            "status":    "ok",
            "order":     arima_result.get("order"),
            "rmse":      arima_result["metrics"]["rmse"],
            "mae":       arima_result["metrics"]["mae"],
            "mape":      arima_result["metrics"]["mape"],
            "direction": arima_result["direction"],
            "elapsed_s": elapsed,
            "adf_stationary": arima_result.get("adf_test", {}).get("stationary"),
        }
        log.info(
            f"      ARIMA{arima_result.get('order')} done in {elapsed}s | "
            f"RMSE={arima_result['metrics']['rmse']:.4f} | "
            f"ADF stationary={arima_result.get('adf_test', {}).get('stationary')}"
        )
    except Exception as e:
        results["models"]["arima"] = {"status": "error", "error": str(e)}
        log.error(f"      ARIMA failed: {e}")

    # ── Summary ──────────────────────────────────────────
    results["total_elapsed_s"] = round(time.time() - t0, 1)
    results["trained_at"]      = datetime.now().isoformat()
    results["status"]          = "ok"

    # Find best model
    ok_models = {k: v for k, v in results["models"].items() if v.get("status") == "ok"}
    if ok_models:
        best_k = min(ok_models, key=lambda k: ok_models[k]["rmse"])
        results["best_model"] = best_k
        log.info(f"\n  ✓ Best model: {best_k.upper()} (RMSE={ok_models[best_k]['rmse']:.4f})")

    # Save results JSON
    out_path = RESULTS_DIR / f"{symbol.replace('^','').replace('.','_')}_training_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info(f"  Results saved → {out_path}")
    log.info(f"  Total time: {results['total_elapsed_s']}s\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="Train all forecasting models for stock symbols")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbol",  type=str,           help="Single symbol (e.g. NIFTY)")
    group.add_argument("--symbols", nargs="+",           help="Multiple symbols")
    parser.add_argument("--epochs", type=int, default=20, help="LSTM training epochs (default: 20)")
    parser.add_argument("--period", default="2y",         help="Historical data period (default: 2y)")
    args   = parser.parse_args()

    symbols = args.symbols if args.symbols else [args.symbol]

    print(f"\n{'='*52}")
    print(f"  AI StockVision — Model Training Pipeline")
    print(f"  Symbols : {symbols}")
    print(f"  Epochs  : {args.epochs}")
    print(f"  Period  : {args.period}")
    print(f"{'='*52}\n")

    all_results = []
    for sym in symbols:
        r = train_symbol(sym, args.epochs, args.period)
        all_results.append(r)

    # Print comparison table
    print(f"\n{'='*70}")
    print(f"  TRAINING SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Symbol':12} {'LSTM RMSE':>10} {'Prophet RMSE':>13} {'ARIMA RMSE':>11} {'Best':>8} {'Time':>6}")
    print(f"  {'-'*68}")
    for r in all_results:
        if r.get("status") != "ok":
            print(f"  {r['symbol']:12}  ERROR: {r.get('error','unknown')}")
            continue
        m    = r["models"]
        lstm_r   = m.get("lstm",   {}).get("rmse", float("inf"))
        prop_r   = m.get("prophet",{}).get("rmse", float("inf"))
        arima_r  = m.get("arima",  {}).get("rmse", float("inf"))
        best     = r.get("best_model", "—")
        elapsed  = r.get("total_elapsed_s", 0)
        print(
            f"  {r['symbol']:12}"
            f"  {lstm_r:>9.4f}"
            f"  {prop_r:>12.4f}"
            f"  {arima_r:>10.4f}"
            f"  {best.upper():>8}"
            f"  {elapsed:>4}s"
        )
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
