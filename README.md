# Forex AI Trading Platform

Professional-grade automated Forex trading platform running locally on Windows with MetaTrader 5.

## Features

- Rule-based + ML trading strategies (Fibonacci, ICT, Hybrid ML)
- **9 trading pairs:** EURUSD, XAUUSD, DXY, USDCAD, GBPUSD, AUDCAD, EURJPY, USDJPY, EURGBP
- Strict risk management (circuit breaker, kill switch, daily loss cap, overtrading protection)
- Professional backtesting engine with spread/commission/slippage simulation
- **European number formatting:** Results display with dot thousand separators (5.000 instead of 5,000)
- **User feedback:** Snackbar alerts for backtest results and errors
- ML module with XGBoost + walk-forward validation
- AI-powered trade analysis with OpenAI (GPT-4o-mini) — isolated, never executes trades
- Modern dark theme UI with collapsible sidebar (240px ↔ 64px)
- 21st.dev inspired components (Radix UI + Tailwind + lucide-react icons)
- Position modification (SL/TP updates, partial close)
- Development auth bypass for faster iteration
- Frontend dashboard with TradingView charts
- Supabase Auth (JWT) with RBAC
- Background tasks with Celery + Redis
- Full audit logging with commission/swap tracking

## Quick Start

### 1. Clonar repositorio

```bash
git clone https://github.com/Santy-417/Trading.git
cd Trading
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus credenciales
```

### 3. Levantar Redis (Docker)

```bash
docker-compose up -d redis
```

### 4. Ejecutar backend

```bash
uvicorn app.main:app --reload --port 8000
```

API disponible en `http://localhost:8000/docs`

### 5. Frontend

```bash
cd frontend
npm install  # Includes: lucide-react, framer-motion, radix-ui, clsx, tailwind-merge
cp .env.local.example .env.local
# Editar .env.local con tus credenciales de Supabase
npm run dev  # OR npm run dev:clean to clear cache first
```

Dashboard disponible en `http://localhost:3000`
- **Development mode:** Auth bypassed automatically (no login required)
- **Collapsible sidebar:** Click bottom toggle button to collapse/expand
- **Dark mode:** Enabled by default with Tailwind CSS variables

### 6. Ejecutar tests

```bash
cd backend
pytest tests/ -v
```

## Project Structure

```
Trading/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app assembly
│   │   ├── core/                # Config, security, middleware, rate limiting, logging
│   │   ├── routers/             # API endpoints (health, bot, orders, metrics, backtest, ml, ai)
│   │   ├── services/            # Business logic layer
│   │   ├── repositories/        # Data access layer
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── strategies/          # Trading strategies (fibonacci, ict, manual, hybrid_ml)
│   │   ├── risk/                # Risk engine (circuit breaker, kill switch, lot calculator)
│   │   ├── execution/           # Execution engine (signal → risk → MT5)
│   │   ├── backtesting/         # Backtesting engine + metrics + simulator
│   │   ├── ml/                  # XGBoost ML pipeline + feature engineering
│   │   ├── ai_analysis/         # LLM-powered trade analysis (OpenAI)
│   │   ├── tasks/               # Celery background tasks
│   │   └── integrations/        # MT5 client, Supabase client
│   ├── tests/                   # 51 unit tests
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js 14 pages (App Router)
│   │   │   ├── login/           # Supabase Auth login
│   │   │   └── (dashboard)/     # Protected routes
│   │   │       ├── trading/     # Live trading + TradingView chart + bot control
│   │   │       ├── backtest/    # Backtesting config + results + equity chart
│   │   │       ├── ml/          # ML model training + prediction
│   │   │       ├── analysis/    # AI-powered trade analysis
│   │   │       ├── risk/        # Risk management dashboard
│   │   │       ├── audit/       # Trade history + audit log
│   │   │       └── settings/    # Platform info
│   │   ├── components/          # Reusable UI components
│   │   │   ├── layout/          # Sidebar, Header, AppShell
│   │   │   ├── charts/          # TradingView widget, Equity chart (Recharts)
│   │   │   ├── trading/         # Bot control, Positions table
│   │   │   └── common/          # StatCard, LoadingSpinner
│   │   ├── lib/                 # Supabase client, API client (Axios + JWT), MUI theme
│   │   ├── store/               # Zustand state management
│   │   └── types/               # TypeScript interfaces
│   ├── package.json
│   └── .env.local.example
├── docker-compose.yml           # Redis + Celery worker
├── CLAUDE.md
└── README.md
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async) |
| Frontend | Next.js 14, TypeScript, Material UI v7, Recharts |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase JWT verification |
| Trading | MetaTrader5 Python package |
| ML | XGBoost, scikit-learn |
| AI Analysis | OpenAI GPT-4o-mini (abstraction for future Claude/Local) |
| Task Queue | Celery + Redis |
| State Mgmt | Zustand |
| Charts | TradingView Advanced Chart, Recharts |
| Pairs | EURUSD, XAUUSD, DXY, USDCAD, GBPUSD, AUDCAD, EURJPY, USDJPY, EURGBP |

## Roadmap

- [x] Phase 1: Backend Core + MT5 integration + Risk Engine
- [x] Phase 2: Backtesting Engine + ML Module
- [x] Phase 3: Frontend (Next.js 14 + Material UI) + AI Analysis (OpenAI)

## Architecture

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

## Troubleshooting

### Audit Logs Empty
**Cause:** No closed trades in database yet.
**Solution:**
1. Close existing positions in Trading page (`/trading`), OR
2. Run historical sync: `python backend/sync_mt5_positions.py`, OR
3. Wait for bot to close trades naturally

### Backtest Returns 0 Trades
**Cause:** Insufficient historical data or strict strategy parameters.
**Solution:**
- Increase "Bars" parameter (try 10,000+)
- Verify MT5 has historical data for selected symbol/timeframe
- Adjust strategy parameters

### Symbol Not Found Error
**Cause:** Symbol not available in MT5 broker.
**Solution:** Add symbol in MT5 Market Watch first
