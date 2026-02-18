# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Professional Forex AI Trading Platform. Automated trading on MetaTrader 5 with rule-based + ML strategies, strict risk management, and LLM-based analysis (non-execution).

## Architecture

Monolithic modular system with Clean Architecture + SOLID. 3 phases (all complete):
- **Phase 1 (complete):** Backend (FastAPI) + MT5 integration + Risk engine
- **Phase 2 (complete):** Backtesting engine + ML module (XGBoost)
- **Phase 3 (complete):** Frontend (Next.js 14 + Material UI v7) + AI Analysis (OpenAI)

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Supabase (PostgreSQL), Redis, Celery
- **Frontend:** Next.js 14, TypeScript, Material UI v7, Zustand, Recharts, TradingView widget
- **Trading:** MetaTrader5 Python package, XAUUSD + EURUSD
- **ML:** XGBoost + scikit-learn, walk-forward validation, feature engineering (RSI, MACD, BB, ATR, EMA, momentum)
- **AI Analysis:** OpenAI GPT-4o-mini (abstraction for future Claude/Local support)
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
├── main.py                    # FastAPI app assembly + lifespan + global exception handler
├── core/
│   ├── config.py              # Pydantic Settings (.env loading)
│   ├── security.py            # JWT verification (Supabase)
│   ├── logging_config.py      # Standard Python logging setup
│   ├── rate_limit.py          # SlowAPI rate limiter per IP
│   └── middleware.py          # CORS, security headers, audit logging
├── routers/
│   ├── health.py              # GET /api/v1/health
│   ├── bot.py                 # /api/v1/bot/*
│   ├── orders.py              # /api/v1/orders/*
│   ├── metrics.py             # /api/v1/metrics/*
│   ├── backtest.py            # /api/v1/backtest/*
│   ├── ml.py                  # /api/v1/ml/*
│   └── ai.py                  # /api/v1/ai/*
├── services/
│   ├── bot_service.py         # Bot lifecycle management
│   ├── order_service.py       # Order execution logic
│   ├── metrics_service.py     # Trading metrics aggregation
│   ├── backtest_service.py    # Backtesting orchestration
│   ├── ml_service.py          # ML training/prediction orchestration
│   └── ai_service.py          # AI analysis orchestration
├── repositories/
│   ├── trade_repository.py    # Trade CRUD operations
│   └── audit_repository.py    # Audit log persistence
├── models/
│   ├── base.py                # SQLAlchemy declarative base + mixins
│   ├── trade.py               # Trade history model
│   ├── bot_config.py          # Bot configuration model
│   ├── risk_event.py          # Risk breach events model
│   ├── audit_log.py           # Audit log model
│   ├── strategy_config.py     # Strategy parameters model
│   ├── backtest_result.py     # Backtest results model
│   └── ml_model.py            # ML model metadata
├── schemas/
│   ├── trade.py               # Trade request/response schemas
│   ├── bot.py                 # Bot control schemas
│   ├── order.py               # Order schemas
│   ├── backtest.py            # Backtest config/result schemas
│   ├── ml.py                  # ML training/prediction schemas
│   └── ai.py                  # AI analysis request/response schemas
├── strategies/
│   ├── base.py                # ABC: generate_signal(), TradeSignal, SignalDirection
│   ├── fibonacci.py           # Fibonacci retracement/extension strategy
│   ├── ict.py                 # ICT (Order Blocks, FVG, liquidity sweeps)
│   ├── manual.py              # Manual signal creation
│   └── hybrid_ml.py           # Rules + ML combined strategy
├── risk/
│   ├── risk_manager.py        # Core risk engine (pre-trade validation)
│   ├── lot_calculator.py      # Fixed, % risk, dynamic lot sizing
│   ├── circuit_breaker.py     # Max drawdown, daily loss cap, overtrading protection
│   └── kill_switch.py         # Emergency stop all trading
├── execution/
│   └── execution_engine.py    # Orchestrates: signal → risk check → MT5 execution
├── backtesting/
│   ├── engine.py              # Backtesting motor (strategy + data → metrics)
│   ├── simulator.py           # Trade simulation (spread, commission, slippage)
│   ├── metrics.py             # Sharpe, profit factor, drawdown, equity curve, streaks
│   ├── data_loader.py         # Load historical data from MT5
│   └── optimizer.py           # Parameter optimization
├── ml/
│   ├── feature_engineering.py # Technical indicators (RSI, MACD, BB, ATR, EMA, momentum)
│   ├── dataset_builder.py     # Build labeled datasets from OHLCV
│   ├── model_training.py      # XGBoost training pipeline
│   ├── model_registry.py      # Save/load models + metadata (joblib)
│   ├── prediction.py          # Real-time inference
│   └── optimizer.py           # Grid search + walk-forward validation
├── ai_analysis/
│   ├── llm_client.py          # LLM abstraction (OpenAI now, Claude/Local later)
│   ├── trade_analyzer.py      # Pattern recognition in trades
│   ├── risk_review.py         # Risk anomaly detection
│   └── performance_summary.py # Weekly/monthly natural language reports
├── tasks/
│   ├── celery_app.py          # Celery configuration
│   ├── backtest_tasks.py      # Background backtest jobs
│   └── ml_tasks.py            # Background ML training jobs
├── integrations/
│   ├── metatrader/
│   │   └── mt5_client.py      # MT5 wrapper (connect, orders, positions, history)
│   └── supabase/
│       └── client.py          # SQLAlchemy async engine (lazy init via @lru_cache)
└── utils/
    └── helpers.py
```

## Frontend Structure

```
frontend/src/
├── app/
│   ├── layout.tsx             # Root layout + MUI ThemeProvider
│   ├── page.tsx               # Root redirect (auth check → /trading or /login)
│   ├── providers.tsx          # MUI dark theme + CssBaseline
│   ├── login/page.tsx         # Supabase Auth UI login
│   └── (dashboard)/           # Protected route group (auth guard)
│       ├── layout.tsx         # AppShell (Sidebar + Header + main content)
│       ├── trading/page.tsx   # Live trading: TradingView chart, bot control, positions
│       ├── backtest/page.tsx  # Backtest config, results table, equity curve
│       ├── ml/page.tsx        # Train models, view predictions, model list
│       ├── analysis/page.tsx  # AI analysis: trade patterns, risk review, reports
│       ├── risk/page.tsx      # Risk gauges: drawdown, daily loss, overtrading
│       ├── audit/page.tsx     # Trade history with filters + pagination
│       └── settings/page.tsx  # Platform info
├── components/
│   ├── layout/                # Sidebar, Header, AppShell
│   ├── charts/                # TradingViewWidget, EquityChart (Recharts)
│   ├── trading/               # BotControl, PositionsTable
│   └── common/                # StatCard, LoadingSpinner
├── lib/
│   ├── api.ts                 # Axios instance + JWT interceptor
│   ├── supabase.ts            # Supabase client
│   └── theme.ts               # MUI dark theme configuration
├── store/index.ts             # Zustand store (bot status, positions, metrics)
└── types/index.ts             # TypeScript interfaces for all API types
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
| GET | `/api/v1/orders/history` | Trade history (paginated, filterable) |
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

## Critical Rules

- LLM must NEVER execute trades
- Execution engine must NOT depend on LLM
- No business logic inside routers (use services layer)
- No raw SQL (ORM only)
- No hardcoded credentials (use .env)
- No blocking calls inside async endpoints
- No silent error handling
- Risk engine must be checked before every trade execution
- Standard Python logging (not structlog/JSON)
- Swagger docs available at `/docs`
- Frontend uses MUI v7 Grid with `size={{ xs, md }}` syntax (not `item` prop)
