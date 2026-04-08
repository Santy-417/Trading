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
├── services/               # Business logic: bot, orders, metrics, backtest, ml, ai, data_pipeline
├── repositories/           # Data access: trade CRUD, audit log persistence
├── models/                 # SQLAlchemy ORM: trade, bot_config, risk_event, audit_log, ml_model, ohlcv_bar
├── schemas/                # Pydantic request/response schemas per domain
├── strategies/             # Trading strategies: bias (SMC V1), fibonacci, ict, manual, hybrid_ml
├── risk/                   # Risk engine: risk_manager, lot_calculator, circuit_breaker, kill_switch
├── execution/              # Orchestrates: signal → risk check → MT5 execution (crash monitoring + backoff)
├── backtesting/            # Engine, simulator (spread/commission/slippage), metrics, optimizer
├── ml/                     # Feature engineering, SMC feature extractor, dataset builder, XGBoost training
├── ai_analysis/            # LLM client (abstraction), trade analyzer, risk review, reports
├── tasks/                  # Celery: backtest + ML background jobs
└── integrations/           # MT5 client (connect, orders, positions, history), Supabase client

backend/scripts/
├── download_historical_data.py  # Bulk-download OHLCV bars (EURUSD/XAUUSD H1+M15, 2-5 years) into ohlcv_bars table
└── migrate_models_to_storage.py # One-shot migration: local ML pickle files → Supabase Storage bucket

backend/alembic/versions/
├── 002_bot_config_crash_monitoring.py  # Adds error_state, last_error, last_heartbeat, crash_count to bot_config
└── 003_ohlcv_bars.py                   # Creates ohlcv_bars table with unique constraint + indexes
```

## Trading Strategies

### BiasStrategy V1 (Smart Money Concepts)
**Status:** ✅ Production-ready | **Tested:** Real MT5 data (20k bars H1) | **Optimized:** Feb 2026

**Core Methodology:**
- Daily bias from D1 candle (BULLISH/BEARISH/NEUTRAL with Doji detection)
- London manipulation detection (PDH/PDL sweeps during 02:00-11:30 Bogotá)
- NY session entry (08:00-14:00 Bogotá) with ChoCh or fractal break confirmation
- Shannon entropy filtering for market regime detection

**V1 Optimizations (Feb 2026):**
1. **ChoCh Híbrido** - `tolerance = max(range * 0.15, pip * 2.0)` for dynamic volatility-based thresholds
2. **Temporal Swing Filtering** - Uses last 15 M5 bars for swing point selection (prevents stale swing comparisons)
3. **Symmetric ChoCh Logic** - BUY uses `swing_high - tolerance`, SELL uses `swing_low + (pip * 1.5)`
4. **Fractal Break with Liquidity Zones** - BUY: `fractal_high - 3 pips`, SELL: `fractal_low + 1 pip` (calibrated)
5. **Bias Neutral** - Doji detection (body <20% of D1 range) → searches sweeps in both directions
6. **Entropy Threshold** - 3.1 for moderate-high volatility acceptance
7. **Risk-Reward Optimized** - min_rr reduced from 1.5 to 1.3 (maximizes Net Profit on H1 timeframe)
8. **SMC Feature Extractor** - 20 ML features (PDH/PDL, sessions, sweeps, fractals, entropy, bias)

**SELL Trade Surgery (Feb 2026):**
Fixed critical bug where strategy executed 100% BUY trades (210 BUY, 0 SELL on 10k bars). Root cause: asymmetric ChoCh/Fractal logic that blocked all SELL signals. Solution: symmetric temporal swing filtering + liquidity zone thresholds. Post-fix validation shows balanced BUY/SELL distribution with improved profitability.

**Key Files:**
- `backend/app/strategies/bias.py` - Main strategy (~1000 lines, lines 847-1012 contain ChoCh/Fractal logic)
- `backend/app/ml/smc_feature_extractor.py` - SMC-specific ML features (450 lines)
- `backend/tests/test_bias_strategy.py` - Strategy unit tests (25 tests)

**Parameters:**
```python
BiasStrategy(
    model_id=None,                   # ML model ID for confidence filtering (str | None)
    min_ml_confidence=0.65,          # ML confidence threshold (skips trade if below)
    sl_pips_base=10.0,               # Base stop loss in pips
    min_rr=1.3,                      # Minimum risk-reward ratio (optimized Feb 2026)
    london_start_hour=2,             # 02:00 Bogotá (07:00 UTC)
    london_end_hour=11,              # 11:30 Bogotá
    ny_start_hour=8, ny_end_hour=14, # 08:00-14:00 Bogotá
    choch_lookback=60,               # M5 bars for ChoCh detection (configurable, not hardcoded)
    entropy_threshold=3.1,           # Shannon entropy filter
    use_entropy_zscore=True,         # Z-score normalization for entropy
    entropy_window=50,               # Entropy calculation window (bars)
    fvg_lookback=30,                 # Fair Value Gap lookback bars
    sweep_tolerance_pips=3.0,        # PDH/PDL sweep detection tolerance (near-miss allowance)
)
```

**Backtest Results (Real MT5 Data - EURUSD H1):**
```
20k bars (Feb 2026 validation):
- Total Trades: 146
- Win Rate: 56.16%
- Profit Factor: 1.36
- Sharpe Ratio: 2.25
- Max Drawdown: 7.89%
- Net Profit: $1,275.23 (10k initial balance)
- BUY/SELL Distribution: 26 BUY (17.8%), 120 SELL (82.2%)
  Note: Imbalance under calibration - Fractal SELL threshold adjusted to 1.0 pips
        (trade-off between balance and profitability in progress)

10k bars (min_rr optimization baseline):
- Total Trades: 304
- Win Rate: 49.67%
- Profit Factor: 1.31
- Net Profit: $2,436.84 (optimal for min_rr=1.3)

7k bars (initial post-surgery validation):
- Total Trades: 41
- Win Rate: 73.17%
- Profit Factor: 3.38
- Sharpe Ratio: 8.33
- Net Profit: $1,526.33
```

**Recommended Timeframe:** H1 (tested and optimized). M15 not recommended without full re-optimization of all parameters.

**Known Calibration Status:**
- Fractal SELL threshold currently at 1.0 pips (improved balance but reduced profitability)
- Investigating optimal value between 1.0-3.0 pips for balance vs profitability trade-off
- ChoCh SELL threshold at 1.5 pips (minimal impact, most SELL trades come from Fractal Break)

## Frontend Structure

```
frontend/src/
├── app/                    # Next.js 14 App Router
│   ├── login/              # Glassmorphism login with animated background + system status
│   └── (dashboard)/        # Protected route group (auth guard)
│       ├── trading/        # TradingView chart, bot control, positions table, symbol context header
│       ├── backtest/       # Collapsible config form, hero metrics, equity chart, compare mode tabs
│       ├── ml/             # Train models, predictions, model registry
│       ├── analysis/       # AI trade patterns, risk review, performance reports
│       ├── risk/           # Risk gauges: drawdown, daily loss, overtrading
│       ├── audit/          # Trade history with filters + pagination (MT5 fallback)
│       └── settings/       # Platform info
├── components/
│   ├── layout/             # Sidebar (avatar, tooltips, risk badge), Header (breadcrumb, dual clock, session indicator), AppShell
│   ├── charts/             # EquityChart (balance reference line, custom tooltip with P&L + drawdown)
│   ├── trading/            # TradePanel, BotControl, ManualTradeForm, PositionsTable, TradeAuditCarousel, BotActivityLog, AccountOverview
│   ├── common/             # StatCard (sparkline background, semantic colors, subtitles)
│   └── ui/                 # FormattedNumberInput, SelectDropdown, Button, Avatar, Popover
├── lib/                    # api.ts (Axios+JWT), supabase.ts, theme.ts, utils.ts, numberFormat.ts
├── store/                  # Zustand: botStatus, positions, pendingOrders, metrics, accountInfo, sidebarOpen, activeSymbol (default: "EURUSD"), loading
└── types/                  # TypeScript interfaces for all API types
```

## UI Design System (Mar 2026)

**Design Philosophy:** Professional trading platform feel, not generic dashboard. Domain-specific design with institutional trading aesthetics.

**Key UI Features:**
- **Login:** Glassmorphism card + animated gradient orbs + system health indicator + Framer Motion stagger animations
- **Sidebar:** Left border active indicator (blue), user avatar with Demo badge, tooltips in collapsed mode, risk badge when bot active
- **Header:** Contextual breadcrumb, live dual clock (UTC + Bogotá), active session indicator (Asian/London/NY), bot status chip
- **StatCard:** Optional sparkline background (Recharts mini), semantic colors, uppercase labels with letter-spacing
- **Trading Page:** Symbol context header with flag + P&L chip, session-aware layout
- **Backtest Page:** Collapsible form sections (Strategy/Data Range/Risk), hero metric cards (Net Profit, Win Rate, Profit Factor) with gradient backgrounds, compare mode with tabs (Period A/B/Comparison), estimation banner
- **EquityChart:** Initial balance ReferenceLine, custom tooltip (equity + P&L + drawdown), return % chip, date range subtitle

**Color Palette:**
- Primary: #7c3aed (Violet) | Secondary: #4f46e5 (Indigo)
- Profit: #22c55e (Green) | Loss: #ef4444 (Red) | Warning: #f59e0b (Amber)
- Background: #0a0a1a (default) | Card/Paper: #13112b
- Text: #f1f5f9 (Primary) | #94a3b8 (Secondary) | #64748b (Muted)

## Tests (~115 tests)

```
backend/tests/
├── conftest.py                  # Test environment variables setup
├── test_risk_manager.py         # 4 classes — LotCalculator, KillSwitch, CircuitBreaker, RiskManager (20 tests)
├── test_bias_strategy.py        # 10 classes — BiasRegistration, DailyBias, Entropy, FVG, ChoCh, MLFilter, NewsFilter (25 tests)
├── test_backtesting.py          # 4 classes — Metrics, Simulator, BacktestEngine, Hardening (18 tests)
├── test_ml.py                   # 3 classes — FeatureEngineering, DatasetBuilder, ModelTrainer (9 tests)
├── test_strategies.py           # 5 classes — StrategyRegistry, TradeSignal, Manual, Fibonacci, ICT (13 tests)
└── test_execution_engine.py     # 7 classes — SignalFlow (BUY/SELL), RiskGates, LoopResilience, CrashMonitoring, NoSignal (30 tests)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/bot/start` | Start trading bot |
| POST | `/api/v1/bot/stop` | Stop trading bot |
| POST | `/api/v1/bot/kill` | Kill switch (emergency stop) |
| POST | `/api/v1/bot/reset-kill` | Reset kill switch and circuit breaker |
| GET | `/api/v1/bot/account` | MT5 account info (balance, equity, margin, leverage) |
| GET | `/api/v1/bot/logs` | Bot activity logs (limit 50–200) |
| GET | `/api/v1/bot/status` | Bot status |
| POST | `/api/v1/orders/market` | Place market order |
| POST | `/api/v1/orders/limit` | Place limit order |
| POST | `/api/v1/orders/close` | Close position |
| POST | `/api/v1/orders/modify` | Modify SL/TP or partial close on position |
| POST | `/api/v1/orders/cancel` | Cancel pending order |
| GET | `/api/v1/orders/pending` | List pending orders |
| GET | `/api/v1/orders/symbol-info` | Symbol info (bid/ask, stops level) |
| GET | `/api/v1/orders/open` | List open positions |
| GET | `/api/v1/orders/history` | Trade history (DB first, MT5 fallback) |
| GET | `/api/v1/metrics/performance` | Performance metrics |
| GET | `/api/v1/metrics/equity-curve` | Equity curve data |
| POST | `/api/v1/backtest/run` | Run backtest |
| POST | `/api/v1/backtest/estimate` | Estimate bar count for a date range |
| POST | `/api/v1/backtest/optimize` | Optimize parameters |
| GET | `/api/v1/backtest/results` | Historical backtest results |
| POST | `/api/v1/ml/train` | Train ML model |
| POST | `/api/v1/ml/validate` | Walk-forward validation |
| POST | `/api/v1/ml/predict` | Get ML prediction |
| GET | `/api/v1/ml/models` | List saved models |
| DELETE | `/api/v1/ml/models/{model_id}` | Delete ML model by ID |
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
- Sidebar: collapsible (240px ↔ 64px), left-border active indicator, avatar + Demo badge, tooltips collapsed
- Header: breadcrumb, dual clock (UTC + Bogotá), session indicator (Asian/London/NY), bot status chip
- Dark mode via CSS variables in globals.css (Tailwind `dark:` class)
- Development mode bypasses auth (NODE_ENV=development uses dev-bypass-token)
- Backtest inputs use FormattedNumberInput component (no browser spinners)
- Backtest form uses collapsible sections (Strategy & Market, Data Range, Risk Configuration)
- Backtest results: hero metrics (3 cards) + secondary metrics (2-column layout) + BUY/SELL distribution + session analysis
- Compare mode: tab-based (Period A | Period B | Comparison) with delta calculations
- EquityChart: ReferenceLine for initial balance, custom tooltip (P&L + drawdown), return % chip
- StatCard: optional sparkline background, semantic colors, uppercase labels
- Login: glassmorphism + animated gradient orbs + system health check + Framer Motion stagger
- Framer Motion for all page transitions and interactive animations

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
