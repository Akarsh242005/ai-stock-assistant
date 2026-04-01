# Deployment Guide

Complete step-by-step instructions for deploying AI StockVision to production.

---

## Option 1 — Render (Recommended, Free Tier)

Render gives you a free persistent web service. Cold starts apply on free tier (~30s).

### Backend

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set:
   - **Name**: `ai-stockvision-api`
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

5. Environment Variables (optional):
   ```
   LSTM_EPOCHS=15
   LSTM_USE_CACHE=true
   LOG_LEVEL=INFO
   ```

6. Click **Deploy**. Your API will be at:
   `https://ai-stockvision-api.onrender.com/api/docs`

### Frontend

1. Open `frontend/index.html`
2. Update the API constant at the top of the `<script>` block:
   ```js
   const API = 'https://ai-stockvision-api.onrender.com/api';
   ```
3. Deploy `frontend/` to Render as a **Static Site** (or Vercel/Netlify)

---

## Option 2 — Railway

Railway is free with $5/month credit (more than enough for this project).

```bash
# Install Railway CLI
npm install -g @railway/cli

railway login
railway init
railway up

# Set environment variables
railway variables set LSTM_EPOCHS=15
railway variables set CORS_ORIGINS=https://your-frontend.vercel.app
```

---

## Option 3 — Vercel (Frontend) + Render (Backend)

Best for clean separation. Frontend on Vercel CDN, backend on Render.

### Frontend → Vercel

```bash
npm install -g vercel
cd frontend
vercel deploy
```

Set environment variable in Vercel dashboard:
```
VITE_API_URL = https://your-render-api.onrender.com/api
```

### Backend → Render

Follow Option 1 Backend steps above.

---

## Option 4 — Docker on Any VPS (DigitalOcean / Linode / AWS EC2)

Best for full control and no cold starts.

### Prerequisites
- Ubuntu 22.04 VPS with Docker installed
- Domain name (optional)

### Steps

```bash
# 1. Clone on server
git clone https://github.com/yourusername/ai-stock-assistant.git
cd ai-stock-assistant

# 2. Configure environment
cp .env.example .env
nano .env   # set CORS_ORIGINS to your domain

# 3. Start services
docker-compose up -d --build

# 4. Check logs
docker-compose logs -f backend

# 5. Verify
curl http://localhost:8000/api/health
```

### Nginx reverse proxy (optional, for custom domain)

```nginx
# /etc/nginx/sites-available/stockvision
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/stockvision /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# Add SSL with: sudo certbot --nginx -d api.yourdomain.com
```

---

## Option 5 — AWS EC2 (Production-Grade)

For a scalable, production deployment.

```bash
# Launch EC2 (t3.small recommended — t2.micro may OOM on LSTM training)
# AMI: Amazon Linux 2023 or Ubuntu 22.04
# Security Group: open port 8000 (or 80/443 via ALB)

# SSH in and setup
sudo yum update -y  # or apt update
sudo yum install -y git python3.10 python3-pip

# Install OpenCV dependencies
sudo yum install -y libgl1-mesa-glx libglib2.0

git clone https://github.com/yourusername/ai-stock-assistant.git
cd ai-stock-assistant
pip3 install -r requirements.txt

# Run with systemd (stays alive after logout)
sudo tee /etc/systemd/system/stockvision.service << EOF
[Unit]
Description=AI StockVision API
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/ai-stock-assistant/backend
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable stockvision
sudo systemctl start stockvision
sudo systemctl status stockvision
```

---

## Option 6 — Streamlit Cloud (Simplest, No Backend Needed)

Deploy just the Streamlit dashboard — it runs ML models directly in the browser session.

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo → Set main file: `dashboard/streamlit_app.py`
4. Click Deploy

Free. Public URL. No server management.

> Note: First load is slow (~60s) as dependencies install. Models train per session (no persistence).

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server port |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `LSTM_WINDOW_SIZE` | `60` | Look-back window for LSTM (days) |
| `LSTM_FORECAST_DAYS` | `7` | Days to predict ahead |
| `LSTM_EPOCHS` | `20` | Training epochs (reduce to 10 for faster cold starts) |
| `LSTM_USE_CACHE` | `true` | Load saved weights instead of retraining |
| `DEFAULT_PERIOD` | `2y` | Historical data period |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `ALERT_WEBHOOK_URL` | — | Slack webhook for signal alerts |
| `ALERT_EMAIL_TO` | — | Destination email for alerts |

---

## Production Checklist

Before going live:

- [ ] Set `CORS_ORIGINS` to your specific frontend domain (not `*`)
- [ ] Set `LSTM_USE_CACHE=true` to avoid retraining on every cold start
- [ ] Pre-train models with `make train` and commit `.h5` files (or use persistent disk)
- [ ] Add API rate limiting (e.g. `slowapi` package)
- [ ] Set up health check monitoring (UptimeRobot free tier works)
- [ ] Add error tracking (Sentry free tier)
- [ ] Use HTTPS everywhere (Render/Railway/Vercel do this automatically)

---

## Estimated Costs

| Platform | Cost | Notes |
|----------|------|-------|
| Render Free | $0/month | Cold starts, 512MB RAM |
| Render Starter | $7/month | No cold starts, 512MB RAM |
| Railway Hobby | $5/month credit | Usually enough for this project |
| DigitalOcean Droplet | $6/month | 1GB RAM, full control |
| AWS EC2 t3.micro | ~$8/month | 1GB RAM |
| AWS EC2 t3.small | ~$15/month | 2GB RAM — recommended for LSTM |
| Streamlit Cloud | Free | ML runs in session, no persistence |
