# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Professional Forex AI Trading Platform. Automated trading on MetaTrader 5 with rule-based + ML strategies, strict risk management, and LLM-based analysis (non-execution). All 3 development phases complete.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Supabase (PostgreSQL), Redis, Celery
- **Frontend:** Next.js 14, TypeScript, Material UI v7, Zustand, Recharts, TradingView widget, lucide-react, Framer Motion
- **Trading:** MetaTrader5 Python package — 9 pairs: EURUSD, XAUUSD, DXY, USDCAD, GBPUSD, AUDCAD, EURJPY, USDJPY, EURGBP
- **ML:** XGBoost + scikit-learn, walk-forward validation, feature engineering (RSI, MACD, BB, ATR, EMA, momentum), SMC feature extractor (20 Smart Money Concepts features)
- **AI Analysis:** OpenAI GPT-4o-mini (abstraction layer supports future Claude/Local providers)
- **Auth:** Supabase JWT verification, RBAC (admin only)

## Common Commands

```bash
# Backend (from /backend directory)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (from /frontend directory)
npm install
npm run dev          # http://localhost:3000
npm run build

# Tests
pytest tests/ -v
pytest tests/test_risk_manager.py -v

# Alembic migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Docker (Redis + Celery)
docker-compose up -d redis
docker-compose up celery_worker

# Linting
ruff check app/
ruff format app/
```

## Backend Structure

```
backend/app/
├── main.py                 # FastAPI app + lifespan + global exception handler
├── core/                   # Config, security (JWT), logging, rate limiting, middleware
├── routers/                # API endpoints: health, bot, orders, metrics, backtest, ml, ai
├── services/               # Business logic: bot, orders, metrics, backtest, ml, ai
├── repositories/           # Data access: trade CRUD, audit log persistence
├── models/                 # SQLAlchemy ORM: trade, bot_config, risk_event, audit_log, ml_model
├── schemas/                # Pydantic request/response schemas per domain
├── strategies/             # Trading strategies: bias (SMC V1), fibonacci, ict, manual, hybrid_ml
├── risk/                   # Risk engine: risk_manager, lot_calculator, circuit_breaker, kill_switch
├── execution/              # Orchestrates: signal → risk check → MT5 execution
├── backtesting/            # Engine, simulator (spread/commission/slippage), metrics, optimizer
├── ml/                     # Feature engineering, SMC feature extractor, dataset builder, XGBoost training
├── ai_analysis/            # LLM client (abstraction), trade analyzer, risk review, reports
├── tasks/                  # Celery: backtest + ML background jobs
└── integrations/           # MT5 client (connect, orders, positions, history), Supabase client
```

## Trading Strategies

### BiasStrategy V1 (Smart Money Concepts)
**Status:** ✅ Production-ready | **Tested:** Synthetic data validation complete

**Core Methodology:**
- Daily bias from D1 candle (BULLISH/BEARISH/NEUTRAL with Doji detection)
- London manipulation detection (PDH/PDL sweeps during 02:00-11:30 Bogotá)
- NY session entry (08:00-14:00 Bogotá) with ChoCh or fractal break confirmation
- Shannon entropy filtering for market regime detection

**V1 Optimizations (Feb 2026):**
1. **ChoCh Híbrido** - `tolerance = max(range * 0.35, pip * 2.5)` prevents microscopic tolerances
2. **Fractal Break Fallback** - Emergency entry if no ChoCh in 60 M5 bars (breaks 3H1 high/low)
3. **Bias Neutral** - Doji detection (body <20% of D1 range) → searches sweeps in both directions
4. **Entropy Threshold** - Increased 2.8 → 3.1 for moderate-high volatility acceptance
5. **SMC Feature Extractor** - 20 ML features (PDH/PDL, sessions, sweeps, fractals, entropy, bias)

**Key Files:**
- `backend/app/strategies/bias.py` - Main strategy (~800 lines)
- `backend/app/ml/smc_feature_extractor.py` - SMC-specific ML features (450 lines)
- `backend/tests/test_bias_strategy.py` - Strategy unit tests (25 tests)

**Parameters:**
```python
BiasStrategy(
    entropy_threshold=3.1,           # Shannon entropy filter
    choch_lookback=60,               # M5 bars for ChoCh detection
    london_start_hour=2,             # 02:00 Bogotá (07:00 UTC)
    ny_start_hour=8, ny_end_hour=14, # 08:00-14:00 Bogotá
    min_rr=1.5,                      # Minimum risk-reward ratio
    sl_pips_base=10.0,               # Base stop loss in pips
)
```

**Expected Performance (with real MT5 data):**
- Trades/year: 15-30 (2-3 per week)
- Win rate: 40-55%
- Profit factor: >1.0
- Sharpe ratio: >0.8

**Backtest Validation:**
- Synthetic data (10k bars): 3 trades generated, all V1 features operational
- Real MT5 data: Ready for execution via `python backend/run_v1_backtest.py`

## Frontend Structure

```
frontend/src/
├── app/                    # Next.js 14 App Router
│   ├── login/              # Supabase Auth UI
│   └── (dashboard)/        # Protected route group (auth guard)
│       ├── trading/        # TradingView chart, bot control, positions table
│       ├── backtest/       # Config form, results table, equity curve chart
│       ├── ml/             # Train models, predictions, model registry
│       ├── analysis/       # AI trade patterns, risk review, performance reports
│       ├── risk/           # Risk gauges: drawdown, daily loss, overtrading
│       ├── audit/          # Trade history with filters + pagination (MT5 fallback)
│       └── settings/       # Platform info
├── components/             # layout/ (Sidebar, Header, AppShell), charts/, trading/, common/, ui/
├── lib/                    # api.ts (Axios+JWT), supabase.ts, theme.ts, utils.ts, numberFormat.ts
├── store/                  # Zustand (bot status, positions, metrics)
└── types/                  # TypeScript interfaces for all API types
```

## Tests (51 tests)

```
backend/tests/
├── conftest.py              # Test environment variables setup
├── test_risk_manager.py     # Lot calculator, kill switch, circuit breaker, risk manager
├── test_strategies.py       # Strategy registry, trade signals, manual/fibonacci/ICT strategies
├── test_backtesting.py      # Metrics, simulator, backtest engine
└── test_ml.py               # Feature engineering, dataset builder, model trainer
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/bot/start` | Start trading bot |
| POST | `/api/v1/bot/stop` | Stop trading bot |
| POST | `/api/v1/bot/kill` | Kill switch (emergency stop) |
| GET | `/api/v1/bot/status` | Bot status |
| POST | `/api/v1/orders/market` | Place market order |
| POST | `/api/v1/orders/limit` | Place limit order |
| POST | `/api/v1/orders/close` | Close position |
| GET | `/api/v1/orders/open` | List open positions |
| GET | `/api/v1/orders/history` | Trade history (DB first, MT5 fallback) |
| GET | `/api/v1/metrics/performance` | Performance metrics |
| GET | `/api/v1/metrics/equity-curve` | Equity curve data |
| POST | `/api/v1/backtest/run` | Run backtest |
| POST | `/api/v1/backtest/optimize` | Optimize parameters |
| GET | `/api/v1/backtest/results` | Historical backtest results |
| POST | `/api/v1/ml/train` | Train ML model |
| POST | `/api/v1/ml/validate` | Walk-forward validation |
| POST | `/api/v1/ml/predict` | Get ML prediction |
| GET | `/api/v1/ml/models` | List saved models |
| POST | `/api/v1/ai/analyze-trades` | AI trade pattern analysis |
| POST | `/api/v1/ai/explain-drawdown` | AI drawdown explanation |
| POST | `/api/v1/ai/suggest-parameters` | AI parameter suggestions |
| POST | `/api/v1/ai/risk-review` | AI risk anomaly review |
| POST | `/api/v1/ai/performance-summary` | AI performance report |
| POST | `/api/v1/ai/compare-strategies` | AI strategy comparison |

## Coding Conventions

### Backend
- No business logic inside routers (use services layer)
- No raw SQL (ORM only via SQLAlchemy)
- No blocking calls inside async endpoints
- No silent error handling — always log errors
- Standard Python logging (not structlog/JSON)
- Risk engine must be checked before every trade execution
- Swagger docs available at `/docs`

### Frontend
- MUI v7 Grid with `size={{ xs, md }}` syntax (NOT `item` prop)
- lucide-react icons only (NOT @mui/icons-material)
- Sidebar: collapsible (240px ↔ 64px), segmented sections (MAIN_NAV + ACCOUNT)
- Dark mode via CSS variables in globals.css (Tailwind `dark:` class)
- Development mode bypasses auth (NODE_ENV=development uses dev-bypass-token)
- Backtest inputs use FormattedNumberInput component (no browser spinners)

### Data & Formatting
- No hardcoded credentials (use .env)
- European number format: dots as thousand separators (5.000), comma as decimal (2.575,50)
- Utility: `formatNumberWithDots()` / `parseFormattedNumber()` in `frontend/src/lib/numberFormat.ts`
- Component: `FormattedNumberInput` in `frontend/src/components/ui/formatted-number-input.tsx`
- Trade history: DB-first with MT5 `history_deals_get()` fallback when DB is empty

### Trading Rules
- LLM must NEVER execute trades — AI analysis is advisory only
- Execution engine must NOT depend on LLM
- 9 supported pairs: EURUSD, XAUUSD, DXY, USDCAD, GBPUSD, AUDCAD, EURJPY, USDJPY, EURGBP
- Risk validation: circuit breaker, kill switch, daily loss cap, overtrading protection
