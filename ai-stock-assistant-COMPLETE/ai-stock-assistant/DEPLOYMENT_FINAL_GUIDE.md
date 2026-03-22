# Final Deployment Guide: AI StockVision

Follow these steps to get your project live on the internet! 🚀

---

## 1. Push your code to GitHub
Make sure all your local changes are committed and pushed to a new GitHub repository.
*   **Repo Name**: `ai-stock-assistant`
*   **Included Folders**: `backend/`, `frontend/`, `models/`, `requirements.txt`.

---

## 2. Deploy the Backend (FastAPI) on [Render.com](https://render.com)
1.  Sign up for a free account on Render.
2.  Click **New +** → **Web Service**.
3.  Connect your GitHub repository.
4.  **Settings**:
    *   **Name**: `ai-stock-backend`
    *   **Runtime**: `Python 3`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5.  **Environment Variables** (Add these in the "Env Vars" tab):
    *   `CORS_ORIGINS`: `*` (or your frontend URL after step 3)
    *   `PYTHON_VERSION`: `3.10.0`
6.  **Deploy!** Copy your Web Service URL (e.g., `https://ai-stock-backend.onrender.com`).

---

## 3. Deploy the Frontend (Dashboard) on [Vercel](https://vercel.com)
1.  Sign up for a free account on Vercel.
2.  Click **Add New** → **Project**.
3.  Connect the same GitHub repo.
4.  **Settings**:
    *   **Framework Preset**: Other / None
    *   **Root Directory**: `frontend`
5.  **Before clicking Deploy**:
    *   Edit your `frontend/index.html` file (on GitHub or locally) and change line 239:
    ```javascript
    const BACKEND_URL = 'https://ai-stock-backend.onrender.com'; // Use your Render URL here
    ```
6.  **Deploy!** Your dashboard will be live at a URL like `https://ai-stock-assistant.vercel.app`.

---

## 4. Final verification
1.  Open your Vercel URL.
2.  Search for a stock (e.g., `IREDA`).
3.  If data populates, your production deployment is successful!

> [!TIP]
> **Cold Starts**: Render's free tier "sleeps" after 15 mins of inactivity. The first request after a break might take 30-60 seconds to wake up. This is normal for free hosting!
