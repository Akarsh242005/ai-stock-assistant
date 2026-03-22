"""
============================================================
Signal Alert Service
============================================================
Watches a list of stocks and sends alerts when strong
BUY or SELL signals are detected.

Supports:
  - Console output (always)
  - Slack webhooks
  - Email via SMTP

Usage:
  python scripts/run_alerts.py --symbols NIFTY RELIANCE TCS
  python scripts/run_alerts.py --symbols AAPL MSFT --interval 3600
============================================================
"""

import sys
import os
import time
import json
import smtplib
import argparse
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Allow importing from backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from services.data_service       import fetch_stock_data, fetch_stock_info
from services.technical_analysis import generate_signal

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("alerts")

# ── Alert thresholds ──────────────────────────────────────
MIN_CONFIDENCE = 72     # Only alert if confidence >= this
STRONG_SIGNALS = ("BUY", "SELL")  # Skip HOLD


# ═══════════════════════════════════════════════════════════
# FORMATTERS
# ═══════════════════════════════════════════════════════════

def format_alert_text(symbol: str, result: dict, info: dict) -> str:
    """Human-readable alert message."""
    sig   = result["signal"]
    conf  = result["confidence"]
    score = result["score"]
    ind   = result["indicators"]
    reasons = result["reasons"]

    arrow = "▲" if sig == "BUY" else "▼"
    lines = [
        f"{'='*54}",
        f"  {arrow}  SIGNAL ALERT: {sig}  |  {symbol}",
        f"{'='*54}",
        f"  Stock     : {info.get('name', symbol)}",
        f"  Price     : {ind['close']} {info.get('currency', 'INR')}",
        f"  Signal    : {sig}",
        f"  Confidence: {conf}%",
        f"  Score     : {'+' if score > 0 else ''}{score}",
        f"  Time      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"  Indicators:",
        f"    RSI (14)  : {ind['rsi']}",
        f"    MACD      : {ind['macd']}",
        f"    SMA 50    : {ind['sma_50']}",
        f"    SMA 200   : {ind['sma_200']}",
        f"    Close     : {ind['close']}",
        f"",
        f"  Reasons:",
    ]
    for r in reasons:
        lines.append(f"    › {r}")
    lines.append(f"{'='*54}")
    return "\n".join(lines)


def format_slack_payload(symbol: str, result: dict, info: dict) -> dict:
    """Slack Block Kit message payload."""
    sig    = result["signal"]
    conf   = result["confidence"]
    ind    = result["indicators"]
    emoji  = ":large_green_circle:" if sig == "BUY" else ":red_circle:"
    color  = "#00e5a0" if sig == "BUY" else "#ff3860"

    return {
        "attachments": [{
            "color": color,
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"{emoji}  {sig} Signal — {symbol}"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Stock*\n{info.get('name', symbol)}"},
                        {"type": "mrkdwn", "text": f"*Price*\n{ind['close']} {info.get('currency','INR')}"},
                        {"type": "mrkdwn", "text": f"*Confidence*\n{conf}%"},
                        {"type": "mrkdwn", "text": f"*RSI (14)*\n{ind['rsi']}"},
                        {"type": "mrkdwn", "text": f"*MACD*\n{ind['macd']}"},
                        {"type": "mrkdwn", "text": f"*SMA 50/200*\n{ind['sma_50']} / {ind['sma_200']}"},
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Signal Reasons:*\n" + "\n".join(f"› {r}" for r in result["reasons"])
                    }
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn",
                                  "text": f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST"}]
                }
            ]
        }]
    }


# ═══════════════════════════════════════════════════════════
# DELIVERY CHANNELS
# ═══════════════════════════════════════════════════════════

def send_slack(webhook_url: str, payload: dict) -> bool:
    """POST alert to Slack webhook."""
    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log.error(f"Slack delivery failed: {e}")
        return False


def send_email(
    to_addr:   str,
    subject:   str,
    body_text: str,
    smtp_host: str  = "smtp.gmail.com",
    smtp_port: int  = 587,
    from_addr: str  = "",
    password:  str  = "",
) -> bool:
    """Send signal alert via SMTP (Gmail / any provider)."""
    if not from_addr or not password:
        log.warning("Email credentials not configured — skipping email")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to_addr
        msg.attach(MIMEText(body_text, "plain"))

        # Minimal HTML version
        html_body = f"""
        <html><body style="font-family:monospace;background:#080c10;color:#e6edf3;padding:20px">
        <pre style="background:#0d1117;border:1px solid #21262d;padding:16px;border-radius:8px;
                    color:{'#00e5a0' if 'BUY' in subject else '#ff3860'}">{body_text}</pre>
        </body></html>"""
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(from_addr, password)
            server.sendmail(from_addr, to_addr, msg.as_string())
        return True
    except Exception as e:
        log.error(f"Email delivery failed: {e}")
        return False


def save_alert_log(symbol: str, result: dict) -> None:
    """Append alert to local JSON log file."""
    log_dir  = os.path.join(os.path.dirname(__file__), "../data")
    log_file = os.path.join(log_dir, "alerts.jsonl")
    os.makedirs(log_dir, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "symbol":    symbol,
        "signal":    result["signal"],
        "confidence": result["confidence"],
        "score":     result["score"],
        "indicators": result["indicators"],
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ═══════════════════════════════════════════════════════════
# MAIN WATCHER LOOP
# ═══════════════════════════════════════════════════════════

def check_symbol(symbol: str, cfg: dict) -> dict | None:
    """
    Fetch latest data for symbol, compute signal.
    Returns alert dict if a strong signal is found, else None.
    """
    try:
        df     = fetch_stock_data(symbol, period="3mo")
        info   = fetch_stock_info(symbol)
        result = generate_signal(df)

        log.info(
            f"{symbol:12} | {result['signal']:5} | "
            f"conf={result['confidence']}% | "
            f"RSI={result['indicators']['rsi']:.1f}"
        )

        if (
            result["signal"] in STRONG_SIGNALS
            and result["confidence"] >= MIN_CONFIDENCE
        ):
            return {"symbol": symbol, "result": result, "info": info}

    except Exception as e:
        log.error(f"Failed to check {symbol}: {e}")

    return None


def run_watcher(symbols: list, interval: int, cfg: dict) -> None:
    """
    Main loop: check all symbols every `interval` seconds.
    Sends alerts when strong signals are detected.
    """
    log.info(f"Starting signal watcher for: {symbols}")
    log.info(f"Check interval: {interval}s | Min confidence: {MIN_CONFIDENCE}%")
    log.info("─" * 54)

    while True:
        log.info(f"Scanning {len(symbols)} symbols...")
        alerts_fired = 0

        for sym in symbols:
            alert = check_symbol(sym, cfg)
            if not alert:
                continue

            symbol = alert["symbol"]
            result = alert["result"]
            info   = alert["info"]

            # Console output (always)
            print("\n" + format_alert_text(symbol, result, info))

            # Save to log
            save_alert_log(symbol, result)
            alerts_fired += 1

            # Slack
            if cfg.get("slack_webhook"):
                payload = format_slack_payload(symbol, result, info)
                ok = send_slack(cfg["slack_webhook"], payload)
                log.info(f"Slack alert {'sent' if ok else 'FAILED'} for {symbol}")

            # Email
            if cfg.get("email_to"):
                sig  = result["signal"]
                subj = f"🚨 {sig} Signal — {symbol} ({result['confidence']}% confidence)"
                body = format_alert_text(symbol, result, info)
                ok = send_email(
                    to_addr   = cfg["email_to"],
                    subject   = subj,
                    body_text = body,
                    from_addr = cfg.get("email_from", ""),
                    password  = cfg.get("email_password", ""),
                )
                log.info(f"Email alert {'sent' if ok else 'FAILED'} for {symbol}")

        log.info(f"Scan complete — {alerts_fired} alert(s) fired. Next in {interval}s.\n")
        time.sleep(interval)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Stock Signal Alert Watcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/alert_service.py --symbols NIFTY RELIANCE
  python scripts/alert_service.py --symbols AAPL MSFT --interval 1800
  python scripts/alert_service.py --symbols TCS --slack https://hooks.slack.com/...
        """
    )
    parser.add_argument("--symbols",  nargs="+", required=True, help="Stock symbols to watch")
    parser.add_argument("--interval", type=int,  default=3600,  help="Check interval in seconds (default: 3600)")
    parser.add_argument("--slack",    type=str,  default="",    help="Slack webhook URL for alerts")
    parser.add_argument("--email-to", type=str,  default="",    help="Destination email for alerts")
    parser.add_argument("--once",     action="store_true",       help="Run once and exit (no loop)")

    args = parser.parse_args()

    cfg = {
        "slack_webhook":  args.slack or os.getenv("ALERT_WEBHOOK_URL", ""),
        "email_to":       args.email_to or os.getenv("ALERT_EMAIL_TO", ""),
        "email_from":     os.getenv("ALERT_EMAIL_FROM", ""),
        "email_password": os.getenv("ALERT_EMAIL_PASSWORD", ""),
    }

    if args.once:
        for sym in args.symbols:
            alert = check_symbol(sym, cfg)
            if alert:
                print(format_alert_text(alert["symbol"], alert["result"], alert["info"]))
    else:
        run_watcher(args.symbols, args.interval, cfg)
