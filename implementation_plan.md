# URL Shortener & Analytics Platform — Complete Implementation Plan

> **STATUS:** Plan complete. Say **"start building"** when ready to begin Phase 1.

---

## 1. Project Overview

### What We Are Building
A production-quality URL Shortener & Analytics Platform — similar to Bit.ly — where users can:
- Shorten any URL to a 6-character code (e.g. `https://short.ly/aB3xYz`)
- Optionally set a custom alias and expiry date
- View click analytics: clicks per day, top countries, top referrers
- Log in with email/password or GitHub OAuth

### Who Uses It
- Anonymous users: shorten URLs without signing up
- Authenticated users: manage their links and view analytics

### Why Each Technology Was Chosen

| Technology | Why This, Not Something Else |
|---|---|
| **FastAPI** | Async-native, auto Swagger docs, Pydantic v2 validation, fastest Python web framework |
| **PostgreSQL** | ACID-compliant, best for relational analytics queries, industry standard |
| **SQLAlchemy 2.0 async** | Modern async ORM, avoids blocking I/O, connection pooling built-in |
| **Alembic** | Version-controlled DB migrations — same tool used at Google, Stripe |
| **Pydantic v2** | 5–50× faster than v1, strict validation, great error messages |
| **Redis (Upstash)** | Sub-millisecond short_code lookups, rate limiting store |
| **Authlib** | Best-in-class OAuth2 library, used by major companies |
| **React + Vite** | Fastest frontend build tool, instant HMR, industry standard |
| **TanStack Query v5** | Best async data-fetching for React — replaces Redux for server state |
| **Recharts** | Composable charting built for React |
| **Render** | Free Python hosting with real URLs (unlike Heroku which removed free tier) |
| **Supabase** | Free PostgreSQL with dashboard UI, no credit card |
| **Upstash** | Serverless Redis, free tier, REST API — no Redis server to manage |
| **Vercel** | Best free static/React hosting with automatic deploys |

### What This Demonstrates to a Recruiter
- Async Python at scale (FastAPI + SQLAlchemy 2.0 async)
- Repository pattern separating data access from business logic
- OAuth2 integration (GitHub) — real-world auth flow
- Redis caching and rate limiting
- Background tasks (non-blocking click tracking)
- Structured logging with correlation IDs (observability)
- Measurable performance (Locust load test numbers on resume)
- CI-ready (pre-commit hooks, pytest, coverage badge)
- Full deployment pipeline on free infrastructure

---

## 2. Prerequisites & Manual Setup

### Python 3.11+
- Download: https://www.python.org/downloads/ → "Download Python 3.11.x"
- During install: ✅ check **"Add Python to PATH"**
- Verify: `python --version` → should show `Python 3.11.x`

### Node.js 18+
- Download: https://nodejs.org → LTS version
- Verify: `node --version` and `npm --version`

### PostgreSQL (local dev only — we use Supabase in production)
- Download: https://www.postgresql.org/download/windows/
- Remember the password you set for the `postgres` user
- Verify: `psql --version`

### pgAdmin (GUI for PostgreSQL)
- Usually installed alongside PostgreSQL
- Open pgAdmin → connect to local server → right-click Databases → Create → Database → name it `urlshortener`

### Redis (local dev)
- Windows: use WSL2 or Docker (`docker run -d -p 6379:6379 redis`)
- Verify: `redis-cli ping` → should return `PONG`

### Git
- Verify: `git --version`

### VS Code Extensions (install from Extensions panel)
- Python, Pylance, ESLint, Tailwind CSS IntelliSense, GitLens, Thunder Client

---

## 3. External Services & API Keys

### GitHub OAuth App
**What:** Lets users log in with their GitHub account.
1. Go to https://github.com → Settings → Developer Settings → OAuth Apps → New OAuth App
2. **Application name:** `URL Shortener Dev`
3. **Homepage URL:** `http://localhost:5173`
4. **Authorization callback URL:** `http://localhost:8000/api/v1/auth/github/callback`
5. Click Register → you'll see **Client ID** (visible) and **Client Secret** (click "Generate")
6. These become `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in your `.env`

### Supabase (Free PostgreSQL)
**What:** Managed PostgreSQL database, free forever, no credit card.
1. Go to https://supabase.com → Sign up with GitHub
2. New Project → name: `urlshortener` → choose region: **Southeast Asia (Singapore)**
3. Set a strong database password → save it
4. Go to **Project Settings → Database → Connection String → URI**
5. Copy the URI — looks like: `postgresql://postgres:[PASSWORD]@db.xxxx.supabase.co:5432/postgres`
6. This becomes `DATABASE_URL` in Render
7. **Prevent auto-pause:** Sign up at https://uptimerobot.com → Add Monitor → HTTP → URL: your Render `/health` endpoint → Interval: 5 minutes

### Upstash (Free Redis)
**What:** Serverless Redis for caching and rate limiting.
1. Go to https://upstash.com → Sign up with GitHub
2. Create Database → Type: **Redis** → Region: **AWS ap-south-1 (Mumbai)** → Free tier
3. Go to database details → copy **Redis URL**
4. Looks like: `rediss://default:PASSWORD@HOST.upstash.io:PORT`
5. This becomes `REDIS_URL` in Render

### Render (Free Backend Hosting)
**What:** Hosts our FastAPI backend.
1. Go to https://render.com → Sign up with GitHub
2. New → Web Service → connect your GitHub repo → select backend root
3. **Runtime:** Python 3 | **Build:** `pip install -r requirements.txt`
4. **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables in the Environment tab
6. Live URL format: `https://your-app.onrender.com`
7. ⚠️ **Cold start:** First request after 15 min inactivity takes ~60s (normal for free tier)

### Vercel (Free Frontend Hosting)
**What:** Hosts our React frontend.
1. Go to https://vercel.com → Sign up with GitHub
2. Add New Project → Import Git Repository → select frontend folder
3. Framework preset: **Vite**
4. Add env var: `VITE_API_BASE_URL` = your Render backend URL
5. Live URL format: `https://your-app.vercel.app`

---

## 4. Complete Folder Structure

```
url_project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory, middleware registration
│   │   ├── config.py                # Pydantic BaseSettings — all env vars
│   │   ├── database.py              # SQLAlchemy async engine + session factory
│   │   ├── dependencies.py          # FastAPI Depends() helpers (get_db, get_current_user)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # User ORM model
│   │   │   ├── link.py              # Link ORM model
│   │   │   └── click.py             # Click ORM model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # Pydantic schemas for User (request/response)
│   │   │   ├── link.py              # Pydantic schemas for Link
│   │   │   ├── analytics.py         # Pydantic schemas for Analytics responses
│   │   │   └── token.py             # JWT token schemas
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── user_repo.py         # DB queries for User (DAL layer)
│   │   │   ├── link_repo.py         # DB queries for Link
│   │   │   └── click_repo.py        # DB queries for Click / analytics
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py      # Business logic: register, login, JWT, OAuth
│   │   │   ├── link_service.py      # Business logic: create, validate, cache URL
│   │   │   └── analytics_service.py # Business logic: aggregate click data
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # /api/v1/auth/* endpoints
│   │   │   ├── links.py             # /api/v1/links/* endpoints
│   │   │   ├── analytics.py         # /api/v1/analytics/* endpoints
│   │   │   ├── redirect.py          # GET /{short_code} redirect endpoint
│   │   │   └── health.py            # GET /health and /health/ready
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── correlation_id.py    # Generates X-Request-ID per request
│   │       ├── security_headers.py  # Adds HSTS, X-Frame-Options, etc.
│   │       └── logging.py           # Structured JSON logging via structlog
│   ├── alembic/
│   │   ├── env.py                   # Alembic async migration environment
│   │   ├── script.py.mako           # Migration file template
│   │   └── versions/
│   │       └── 001_initial.py       # First migration: creates all tables + indexes
│   ├── tests/
│   │   ├── conftest.py              # pytest fixtures: test DB, async client, mocked Redis
│   │   ├── test_health.py           # Tests for /health and /health/ready
│   │   ├── test_auth.py             # Tests for register, login, OAuth, token refresh
│   │   ├── test_links.py            # Tests for CRUD link operations
│   │   ├── test_analytics.py        # Tests for click tracking and analytics
│   │   └── test_rate_limiting.py    # Tests for rate limiter behavior
│   ├── load-tests/
│   │   ├── locustfile.py            # Locust performance test scenarios
│   │   └── reports/
│   │       ├── baseline/            # HTML report from first Locust run
│   │       └── optimized/           # HTML report after optimizations
│   ├── .env                         # Local environment variables (gitignored)
│   ├── .env.example                 # Template showing all required env vars
│   ├── alembic.ini                  # Alembic configuration file
│   ├── requirements.txt             # All Python dependencies
│   ├── Dockerfile                   # Backend container definition
│   ├── docker-compose.yml           # Orchestrates backend + postgres + redis
│   ├── .pre-commit-config.yaml      # Pre-commit hooks: ruff, black, mypy
│   ├── pyproject.toml               # Tool config: ruff, black, mypy, pytest
│   └── README.md                    # Full project documentation
├── frontend/
│   ├── src/
│   │   ├── main.jsx                 # React entry point
│   │   ├── App.jsx                  # Router setup, QueryClientProvider
│   │   ├── api/
│   │   │   └── axios.js             # Axios instance with base URL + auth interceptor
│   │   ├── pages/
│   │   │   ├── Landing.jsx          # Homepage with shorten form
│   │   │   ├── Login.jsx            # Login form + GitHub OAuth button
│   │   │   ├── Register.jsx         # Registration form
│   │   │   ├── Dashboard.jsx        # User's links table + analytics chart
│   │   │   └── OAuthCallback.jsx    # Handles GitHub OAuth redirect
│   │   ├── components/
│   │   │   ├── Navbar.jsx           # Top navigation bar
│   │   │   ├── ProtectedRoute.jsx   # Redirects unauthenticated users to /login
│   │   │   └── AnalyticsChart.jsx   # Recharts line chart for clicks per day
│   │   └── hooks/
│   │       └── useAuth.js           # Custom hook for auth state
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
└── postman/
    └── URLShortener.postman_collection.json  # Exported Postman collection
```

---

## 5. Backend Implementation Plan

### Build Order & Patterns Demonstrated

| # | File | Pattern / Practice |
|---|---|---|
| 1 | `venv` + `requirements.txt` | Dependency isolation |
| 2 | `config.py` | 12-Factor App: env-based config |
| 3 | `database.py` | Async SQLAlchemy 2.0, connection pooling |
| 4 | `models/` | ORM models with proper indexes |
| 5 | Alembic setup | Version-controlled schema migrations |
| 6 | `schemas/` | Pydantic v2 validation layer |
| 7 | `repositories/` | Repository pattern (DAL) |
| 8 | `services/` | Business logic layer |
| 9 | `routers/` | API versioning under `/api/v1/` |
| 10 | `middleware/` | Cross-cutting concerns |
| 11 | `main.py` | App factory pattern |
| 12 | `tests/` | pytest with async support |
| 13 | `locustfile.py` | Load testing |
| 14 | Docker | Containerization |

### Key requirements.txt packages
```
fastapi[all]          # Web framework with uvicorn bundled
sqlalchemy[asyncio]   # Async ORM
asyncpg               # Async PostgreSQL driver
alembic               # DB migrations
pydantic-settings     # Environment config with validation
python-jose[cryptography]  # JWT tokens
passlib[bcrypt]       # Password hashing
authlib               # OAuth2 (GitHub login)
httpx                 # Async HTTP client (used by authlib)
redis                 # Redis client
fastapi-limiter       # Rate limiting via Redis
structlog             # Structured JSON logging
pre-commit            # Git hooks runner
ruff                  # Fast Python linter
black                 # Code formatter
mypy                  # Static type checker
pytest                # Test framework
pytest-asyncio        # Async test support
httpx                 # Test HTTP client (AsyncClient)
pytest-cov            # Coverage reports
locust                # Load testing
```

---

## 6. Swagger Docs Plan

- **Access UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc` (cleaner read-only view)
- **Auth in Swagger:** Click "Authorize" button → paste Bearer token

### App Metadata (set in `main.py`)
```python
app = FastAPI(
    title="URL Shortener & Analytics API",
    description="Production-quality URL shortener with JWT auth, GitHub OAuth, and click analytics.",
    version="1.0.0",
    contact={"name": "Your Name", "email": "you@email.com"},
    license_info={"name": "MIT"},
)
```

### Tags (groups endpoints in Swagger)
- `auth` — Register, login, token refresh, GitHub OAuth
- `links` — Create, list, delete short URLs
- `analytics` — Click analytics endpoints
- `health` — Health check endpoints

Every endpoint will have: summary, description, request body example, success response example, error response examples (401, 422, 429, 500).

---

## 7. Postman Plan

### Setup
1. Download Postman: https://www.postman.com/downloads/
2. Create Workspace: "URL Shortener Project"
3. Create Collection: "URL Shortener API"
4. Create Environments: **Local** and **Production**

### Environment Variables
| Variable | Local Value | Production Value |
|---|---|---|
| `base_url` | `http://localhost:8000` | `https://your-app.onrender.com` |
| `token` | *(auto-filled by login script)* | *(auto-filled)* |
| `refresh_token` | *(auto-filled)* | *(auto-filled)* |
| `short_code` | *(auto-filled after create)* | *(auto-filled)* |

### Auto-save token script (on Login request → Tests tab)
```javascript
const res = pm.response.json();
pm.environment.set("token", res.access_token);
pm.environment.set("refresh_token", res.refresh_token);
```

### Pre-request script (on Collection level)
```javascript
pm.request.headers.add({ key: "Authorization", value: "Bearer " + pm.environment.get("token") });
```

### All Requests to Create (in order)
1. **Health Check** — GET `{{base_url}}/health`
2. **Register** — POST `{{base_url}}/api/v1/auth/register` + JSON body
3. **Login** — POST `{{base_url}}/api/v1/auth/login` + auto-save token script
4. **Get Current User** — GET `{{base_url}}/api/v1/auth/me`
5. **GitHub OAuth** — GET `{{base_url}}/api/v1/auth/github` (open in browser)
6. **Create Short URL** — POST `{{base_url}}/api/v1/links`
7. **Create with Custom Alias** — POST with `"custom_alias": "mylink"`
8. **Create with Expiry** — POST with `"expires_at": "2025-12-31T00:00:00Z"`
9. **List My Links** — GET `{{base_url}}/api/v1/links`
10. **Delete a Link** — DELETE `{{base_url}}/api/v1/links/{{short_code}}`
11. **Redirect** — GET `{{base_url}}/{{short_code}}` (expect 307 redirect)
12. **My Analytics** — GET `{{base_url}}/api/v1/analytics/me`
13. **Link Analytics** — GET `{{base_url}}/api/v1/analytics/{{short_code}}`

### Export & Badge
- Export collection JSON → save to `/postman/URLShortener.postman_collection.json`
- Import to Postman public API → get badge URL → add to README

---

## 8. Frontend Implementation Plan

### Setup Commands
```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install react-router-dom @tanstack/react-query axios recharts
```

### All Pages & Components

| File | What It Does |
|---|---|
| `Landing.jsx` | Shorten form (works without login), shows result short URL |
| `Login.jsx` | Email/password form + "Login with GitHub" button |
| `Register.jsx` | Registration form with validation |
| `Dashboard.jsx` | Table of user's links + delete button + analytics chart |
| `OAuthCallback.jsx` | Receives `?code=` from GitHub, POSTs to backend, saves token |
| `Navbar.jsx` | Shows logo, links, logout button |
| `ProtectedRoute.jsx` | Checks for token, redirects to /login if missing |
| `AnalyticsChart.jsx` | Recharts `<LineChart>` showing clicks per day (last 30 days) |
| `axios.js` | Axios instance: attaches Bearer token, redirects to /login on 401 |

---

## 9. Database Indexing Plan

| Table | Column(s) | Index Type | Why |
|---|---|---|---|
| `users` | `email` | UNIQUE | Login lookup by email |
| `users` | `github_id` | UNIQUE | OAuth lookup |
| `links` | `short_code` | UNIQUE | Every redirect lookup — most critical |
| `links` | `(user_id, created_at)` | Composite | List user's links sorted by date |
| `clicks` | `link_id` | B-tree | Analytics: all clicks for a link |
| `clicks` | `(link_id, clicked_at)` | Composite | Analytics: clicks per day query |

All indexes are added in the Alembic migration file. You can verify them in Supabase Table Editor → your table → Indexes tab.

---

## 10. Testing Plan

### conftest.py provides:
- `async_client` fixture — AsyncClient pointing at test app
- `test_db` fixture — separate test database, migrated fresh per session
- `mock_redis` fixture — mocked Redis so tests don't need a real Redis

### Test Files

| File | What It Tests |
|---|---|
| `test_health.py` | GET /health returns 200, GET /health/ready returns DB + Redis status |
| `test_auth.py` | Register, login, duplicate email (409), wrong password (401), token refresh |
| `test_links.py` | Create, list, delete, custom alias, expiry, duplicate alias (409) |
| `test_analytics.py` | Click recorded after redirect, analytics endpoint returns correct data |
| `test_rate_limiting.py` | 6th request in 1hr returns 429 for anonymous users |

### Run Tests
```bash
pytest --cov=app --cov-report=html -v
```
Coverage report opens at `htmlcov/index.html`. Target: **80%+ coverage**.

---

## 11. Performance Testing — Locust

### What the Numbers Mean
- **p50 (median):** 50% of requests finished in under X ms
- **p95:** 95% of requests finished in under X ms — your "typical worst case"
- **p99:** 99% finished under X ms — catches outliers
- **req/sec (throughput):** Requests your app handles per second
- **Error rate:** % of requests that failed (target: <1%)

### locustfile.py Tasks

```python
class RedirectUser(HttpUser):   # weight=70 — most common real-world action
    # hits GET /{short_code}

class AuthenticatedUser(HttpUser):  # weight=20
    # logs in, then creates short URLs

class AnalyticsUser(HttpUser):  # weight=10
    # fetches analytics endpoint
```

### Test Sequence
1. **Baseline:** 100 users, 10/sec spawn, 60 seconds → save HTML report
2. **Verify optimizations:** Redis cache hits, background tasks, DB indexes, pool settings
3. **Optimized:** Same parameters → save HTML report
4. **Compare table:** Before/after p50, p95, p99, req/sec, error rate

### Resume Bullet Points (example — fill with your real numbers)
- *"Reduced URL redirect p95 latency from 340ms to 28ms by adding Redis caching layer"*
- *"Sustained 850 req/sec with <0.1% error rate under 100 concurrent users via Locust load test"*
- *"Improved analytics query performance 4× by adding composite index on (link_id, clicked_at)"*

---

## 12. Deployment Plan (100% Free)

### Step-by-Step Order
1. **Push code to GitHub** — Render and Vercel will auto-deploy from this
2. **Supabase** — Create project → copy DATABASE_URL
3. **Run Alembic migrations** against Supabase URL → verify tables in Table Editor
4. **Upstash** — Create Redis → copy REDIS_URL
5. **Render** — Create Web Service → set all env vars → deploy → copy live URL
6. **Vercel** — Import frontend → set VITE_API_BASE_URL → deploy → copy live URL
7. **Update GitHub OAuth App** — change callback URL to Render URL
8. **UptimeRobot** — Set up monitor on Render /health to prevent cold starts
9. **End-to-end test** in Postman with Production environment

### All Render Environment Variables
```
APP_ENV=production
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=<from Supabase>
REDIS_URL=<from Upstash>
GITHUB_CLIENT_ID=<from GitHub>
GITHUB_CLIENT_SECRET=<from GitHub>
GITHUB_REDIRECT_URI=https://your-app.onrender.com/api/v1/auth/github/callback
FRONTEND_URL=https://your-app.vercel.app
ALLOWED_ORIGINS=https://your-app.vercel.app
API_VERSION=v1
```

---

## 13. README Plan

### Sections
1. **Banner** — project title + screenshot (use GitHub's markdown to embed image)
2. **Live Demo** — links to Vercel frontend and Render Swagger docs
3. **Badges** — tech stack badges from https://shields.io
4. **What It Does** — 3 sentences
5. **Architecture Diagram** — draw.io or Mermaid: Browser → Vercel → Render → Supabase/Upstash
6. **Features List** — bullet points
7. **Tech Stack Table**
8. **Local Setup** — 5 commands to get running
9. **Environment Variables Table** — name, description, example
10. **Running Tests** — `pytest` command
11. **API Docs** — link to `/docs`
12. **Postman Badge** — from public collection
13. **Performance Results** — Locust before/after table
14. **What I Learned** — why FastAPI, why Redis, what was hard
15. **License** — MIT

---

## 14. Git & GitHub Plan

### .gitignore (key entries)
```
__pycache__/
*.pyc
.env
venv/
.coverage
htmlcov/
load-tests/reports/
node_modules/
dist/
.env.local
```

### Conventional Commit Format
```
feat: add GitHub OAuth login endpoint
fix: handle expired links returning 410 instead of 404
perf: add Redis cache for short_code lookups
test: add rate limiting test for anonymous users
docs: add Locust performance results to README
chore: add pre-commit hooks with ruff and black
refactor: extract link validation into service layer
```

### Branch Strategy
- `main` — always deployable, Render + Vercel auto-deploy from this
- `feat/auth` — work in progress for auth phase
- `feat/links` — link management phase
- Merge via PR when phase is complete

### Auto-Deploy Setup
- **Render:** Connect GitHub repo → "Auto-Deploy: Yes" → every push to `main` triggers redeploy
- **Vercel:** Connect GitHub repo → every push to `main` triggers redeploy

---

## Build Phase Order

| Phase | What Gets Built |
|---|---|
| **Phase 1** | Git init, venv, requirements.txt, config.py, database.py |
| **Phase 2** | DB models, Alembic migrations, run against Supabase |
| **Phase 3** | Schemas, repositories, services |
| **Phase 4** | All API routers (auth, links, analytics, redirect, health) |
| **Phase 5** | Middleware (correlation ID, security headers, exception handler) |
| **Phase 6** | main.py app factory, Docker setup |
| **Phase 7** | pytest test suite |
| **Phase 8** | Frontend (React + Vite + Tailwind) |
| **Phase 9** | Deployment (Supabase → Upstash → Render → Vercel) |
| **Phase 10** | Locust load testing + README |

---

> ✅ Plan complete across all 14 sections.
> 
> **Say "start building" and I will begin Phase 1.**
