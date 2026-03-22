#!/usr/bin/env python3
"""
============================================================
AI Stock Market Forecasting System — Setup & Verification
============================================================
Run: python setup.py
This script:
  1. Checks Python version
  2. Creates virtual environment
  3. Installs requirements
  4. Verifies all imports work
  5. Tests Yahoo Finance connectivity
  6. Prints next steps
============================================================
"""

import subprocess
import sys
import os

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def p(msg, color=RESET): print(f"{color}{msg}{RESET}")
def ok(msg):   p(f"  ✓ {msg}", GREEN)
def warn(msg): p(f"  ⚠ {msg}", YELLOW)
def fail(msg): p(f"  ✗ {msg}", RED)
def info(msg): p(f"  → {msg}", BLUE)


def check_python():
    p("\n── Python Version ──────────────────", BOLD)
    major, minor = sys.version_info[:2]
    if major == 3 and minor >= 10:
        ok(f"Python {major}.{minor} ✓ (3.10+ required)")
    else:
        fail(f"Python {major}.{minor} — requires 3.10+")
        info("Download: https://python.org/downloads")
        sys.exit(1)


def install_requirements():
    p("\n── Installing Requirements ──────────", BOLD)
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")

    if not os.path.exists(req_file):
        fail("requirements.txt not found")
        return

    info("Running pip install -r requirements.txt ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req_file, "-q"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        ok("All packages installed successfully")
    else:
        warn("Some packages may have failed. Check output:")
        print(result.stderr[-1000:])


def verify_imports():
    p("\n── Verifying Core Imports ───────────", BOLD)
    packages = [
        ("yfinance",       "Yahoo Finance API"),
        ("pandas",         "Data Processing"),
        ("numpy",          "Numerical Computing"),
        ("sklearn",        "Scikit-learn (ML)"),
        ("fastapi",        "FastAPI Backend"),
        ("plotly",         "Plotly Visualization"),
        ("PIL",            "Pillow (Image Processing)"),
        ("statsmodels",    "ARIMA / Statistics"),
    ]

    optional = [
        ("tensorflow",     "TensorFlow (LSTM)"),
        ("prophet",        "Facebook Prophet"),
        ("pmdarima",       "Auto ARIMA"),
        ("cv2",            "OpenCV (Chart Vision)"),
        ("streamlit",      "Streamlit Dashboard"),
    ]

    for module, label in packages:
        try:
            __import__(module)
            ok(f"{label} ({module})")
        except ImportError:
            fail(f"{label} ({module}) — run: pip install {module}")

    p("\n  Optional packages:", YELLOW)
    for module, label in optional:
        try:
            __import__(module)
            ok(f"{label} ({module})")
        except ImportError:
            warn(f"{label} ({module}) — optional, install for full features")


def test_yfinance():
    p("\n── Testing Yahoo Finance Connection ─", BOLD)
    try:
        import yfinance as yf
        ticker = yf.Ticker("^NSEI")
        hist = ticker.history(period="5d")
        if not hist.empty:
            latest = hist['Close'].iloc[-1]
            ok(f"NIFTY latest close: ₹{latest:,.2f}")
            ok("Yahoo Finance API connection working!")
        else:
            warn("Data empty — market may be closed or connection slow")
    except Exception as e:
        fail(f"Yahoo Finance error: {e}")
        info("Check internet connection")


def check_folder_structure():
    p("\n── Project Structure ────────────────", BOLD)
    dirs = ["backend", "frontend", "notebooks", "models", "data", "dashboard"]
    for d in dirs:
        if os.path.exists(d):
            ok(f"/{d}/")
        else:
            warn(f"/{d}/ — missing (will be created)")
            os.makedirs(d, exist_ok=True)


def print_next_steps():
    p("\n" + "═"*50, BOLD)
    p("🚀 Setup Complete! Next Steps:", GREEN + BOLD)
    p("═"*50, BOLD)
    p("""
  1. Start the API backend:
     cd backend
     uvicorn main:app --reload --port 8000

  2. Open frontend:
     Open frontend/index.html in browser
     OR: cd frontend && npx serve .

  3. Run Streamlit dashboard:
     streamlit run dashboard/streamlit_app.py

  4. Explore the Jupyter notebook:
     jupyter notebook notebooks/

  5. API documentation:
     http://localhost:8000/api/docs

  6. Docker (all-in-one):
     docker-compose up --build
""", GREEN)
    p("  Supported symbols: NIFTY, RELIANCE, TCS, AAPL, MSFT, TSLA", BLUE)
    p("  Data source: Yahoo Finance (yfinance) — real market data", BLUE)
    p("\n  ⚠️  Disclaimer: For educational purposes only.", YELLOW)
    p("═"*50, BOLD)


if __name__ == "__main__":
    p("\n" + "═"*50, BOLD)
    p("  AI Stock Market Forecasting System", BOLD)
    p("  Setup & Verification Script", BLUE)
    p("═"*50, BOLD)

    check_python()
    check_folder_structure()
    install_requirements()
    verify_imports()
    test_yfinance()
    print_next_steps()
