from services.data_service import fetch_stock_data
from services.technical_analysis import generate_signal
from concurrent.futures import ThreadPoolExecutor

# Pre-defined hot watchlist for the screener to check (mixed IN and US markets)
HOT_WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS",
    "AAPL", "MSFT", "NVDA", "AMZN", "TSLA"
]

def scan_single_stock(symbol: str) -> dict:
    """Scan a single stock and return actionable intelligence."""
    try:
        # 3 months of data is enough for generating a fast technical signal
        df = fetch_stock_data(symbol, period="3mo", interval="1d")
        analysis = generate_signal(df)
        return {
            "symbol": symbol,
            "signal": analysis["signal"],
            "verdict": analysis["verdict"],
            "confidence": analysis["confidence"],
            "trade_setup": analysis.get("trade_setup"),
            "current_price": analysis["indicators"]["close"],
        }
    except Exception as e:
        print(f"Screener failed to scan {symbol}: {e}")
        return None

def get_top_picks() -> list:
    """
    Expert Feature: AI Screener.
    Scans the hot watchlist in parallel and returns the highest confidence setups.
    """
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scan_single_stock, sym): sym for sym in HOT_WATCHLIST}
        for future in futures:
            res = future.result()
            # Only include highly actionable setups (BUY or SELL)
            if res and res["signal"] in ["BUY", "SELL"]:
                results.append(res)
                
    # Sort by confidence descending
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:5] # Return top 5 opportunities
