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
        df, _ = fetch_stock_data(symbol, period="3mo", interval="1d")
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
    print(f"Screener: Starting scan for {len(HOT_WATCHLIST)} stocks...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scan_single_stock, sym): sym for sym in HOT_WATCHLIST}
        for future in futures:
            try:
                res = future.result()
                # Only include highly actionable setups (BUY or SELL)
                if res and res["signal"] in ["BUY", "SELL"]:
                    results.append(res)
            except Exception as e:
                sym = futures[future]
                print(f"Screener: Exception during {sym} scan: {e}")
                
    # Sort by confidence descending
    results.sort(key=lambda x: x["confidence"], reverse=True)
    print(f"Screener: Scan complete. Found {len(results)} actionable picks.")
    
    # If no picks found, return a small subset of the watchlist with neutral signals 
    # to avoid empty UI for the resume project
    if not results:
        print("Screener: No actionable picks found. Returning top of watchlist as HEALTY.")
        for sym in HOT_WATCHLIST[:3]:
             results.append({"symbol": sym, "signal": "HOLD", "current_price": 0, "confidence": 50, "verdict": "Neutral"})

    return results[:5] # Return top 5 opportunities
