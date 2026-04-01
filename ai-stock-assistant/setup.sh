#!/bin/bash
set -e
echo "╔══════════════════════════════════════════╗"
echo "║  AI StockVision — Quick Setup            ║"
echo "╚══════════════════════════════════════════╝"
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
mkdir -p models
echo "✓ Setup complete!"
echo ""
echo "Run:  cd backend && uvicorn main:app --reload"
echo "Then: open frontend/index.html"
