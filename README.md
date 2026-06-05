# Brief.ly — Production URL Shortener & Analytics

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-CC0000?style=flat&logo=redis)](https://redis.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Live Demo:** https://url-shortener-mu-lilac.vercel.app  
**API:** https://url-shortener-backend-6owv.onrender.com/health

Brief.ly is a production-grade URL shortener and analytics platform with 
sub-millisecond redirect speeds, real-time click analytics, and secure 
JWT authentication via httpOnly cookies.

---

## 🏛️ Architecture

```mermaid
graph TD
    User([Browser Client]) -->|HTTP / JSON| Frontend[Vercel React Client]
    User -->|HTTP GET Redirect| Redirect[FastAPI Redirect Router]
    Frontend -->|REST API| Backend[FastAPI Backend on Render]
    Backend -->|Async SQLAlchemy| PostgreSQL[(Supabase PostgreSQL)]

    Backend -->|Cache + Rate Limit| Redis[(Upstash Redis)]
    Redirect -->|Cache Hit| Redis
    Redirect -->|Cache Miss| PostgreSQL
```

---

## ✨ Features

- **Sub-millisecond redirects** — Redis cache-first, PostgreSQL fallback
- **httpOnly cookie auth** — JWT tokens never touch localStorage (XSS-safe)
- **GitHub OAuth** — Secure one-time exchange token flow
- **Atomic rate limiting** — Lua script in Redis (5/hr anon, 50/hr auth)
- **Click analytics** — Country (GeoLite2), referrer, daily chart (30 days)
- **Background tasks** — Click recording never blocks the redirect response
- **SSRF prevention** — Private IP ranges blocked on URL input
- **Pagination** — Dashboard links list with page controls
- **Custom aliases** — Set your own short code (e.g. `/my-link`)
- **Link expiry** — Set expiration date and time per link

---

## 💻 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend Framework | FastAPI (async) |
| Database | PostgreSQL via Supabase |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Cache / Rate Limit | Redis via Upstash |
| Authentication | JWT (httpOnly cookies) + GitHub OAuth |
| GeoIP | MaxMind GeoLite2 (local, no API call) |
| Frontend | React 19 + Vite |
| Logging | structlog (JSON in production) |
| Testing | pytest-anyio |
| Load Testing | Locust |
| Backend Hosting | Render |
| Frontend Hosting | Vercel |

---

## 📊 Performance

Locust load test — 10 concurrent users, 30 seconds:

| Metric | Result |
|--------|--------|
| Total Requests | 51 |
| Failed Requests | 0 (0%) |
| Median Latency | 50ms |
| Average Latency | 1395ms |
| 95th Percentile | 5800ms |

---

## 🛠️ Local Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL running locally
- Redis running locally (`docker run -d -p 6379:6379 redis`)

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux / Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your values

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`

### 3. Frontend

```bash
cd frontend
npm install

# Create environment file
echo "VITE_API_BASE_URL=http://localhost:8000" > .env

npm run dev
```

Frontend runs at `http://localhost:5173`

---

## 🧪 Running Tests

```bash
cd backend
# Windows:
.\venv\Scripts\activate
# Linux / Mac:
source venv/bin/activate

pytest
```

---

## 📊 Load Testing

```bash
cd backend
# Windows:
.\venv\Scripts\activate
# Linux / Mac:
source venv/bin/activate

locust -f load-tests/locustfile.py --headless -u 10 -r 2 --run-time 30s \
  --host http://localhost:8000
```

---

## 🚀 Deployment

### Backend (Render)

| Field | Value |
|-------|-------|
| Runtime | Python |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `cd /opt/render/project/src/backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers` |

**Required environment variables on Render:**
```
APP_ENV=production
SECRET_KEY=<64 char hex>
DATABASE_URL=postgresql+asyncpg://postgres.xxxx:password@aws-1-xx.pooler.supabase.com:5432/postgres?ssl=require
REDIS_URL=rediss://default:<token>@host.upstash.io:6379
FRONTEND_URL=https://your-app.vercel.app
ALLOWED_ORIGINS=https://your-app.vercel.app
GITHUB_CLIENT_ID=<your id>
GITHUB_CLIENT_SECRET=<your secret>
GITHUB_REDIRECT_URI=https://your-render-app.onrender.com/api/v1/auth/github/callback
DOCS_USERNAME=<not admin>
DOCS_PASSWORD=<12+ chars>
```

### Frontend (Vercel)

| Field | Value |
|-------|-------|
| Framework | Vite |
| Environment Variable | `VITE_API_BASE_URL=https://your-render-app.onrender.com` |

---

## 💡 What I Learned

- **Fail-open caching**: Redis is a performance layer, never a hard dependency — every Redis call is wrapped in try/except with PostgreSQL fallback
- **httpOnly cookies over localStorage**: Tokens in localStorage are vulnerable to XSS; httpOnly cookies are inaccessible to JavaScript entirely
- **Async session safety**: SQLAlchemy `AsyncSession` is not concurrency-safe — `asyncio.gather()` on a shared session causes `MissingGreenlet` errors
- **PostgreSQL strict mode**: `GROUP BY date_trunc(...)` requires the alias in `ORDER BY` under strict PostgreSQL — SQLite is more lenient
- **Background tasks**: FastAPI `BackgroundTask` runs after the response is sent — zero redirect latency from analytics writes

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
