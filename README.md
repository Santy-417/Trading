# Forex AI Trading Platform

Professional-grade automated Forex trading platform running locally on Windows with MetaTrader 5, machine learning strategies, and AI-powered analysis.

## Features

### Trading & Execution
- **Automated trading** on MetaTrader 5 with rule-based and ML strategies
- **5 strategies:** BiasStrategy V1 (Smart Money Concepts), Fibonacci retracement, ICT (Order Blocks, FVG, liquidity sweeps), Manual, Hybrid ML
- **9 trading pairs:** EURUSD, XAUUSD, DXY, USDCAD, GBPUSD, AUDCAD, EURJPY, USDJPY, EURGBP
- **Position management:** Market/limit orders, SL/TP updates, partial close

### Risk Management
- Circuit breaker (max drawdown protection)
- Kill switch (emergency stop all trading)
- Daily loss cap and overtrading protection
- Pre-trade risk validation on every execution

### Backtesting
- Historical strategy testing with spread, commission, and slippage simulation
- Performance metrics: Sharpe ratio, profit factor, max drawdown, equity curve, win/loss streaks
- Parameter optimization with grid search

### Machine Learning
- XGBoost model training with walk-forward validation
- Feature engineering: RSI, MACD, Bollinger Bands, ATR, EMA, momentum indicators
- **SMC Feature Extractor:** 20 Smart Money Concepts features (PDH/PDL, sessions, sweeps, fractals, entropy, bias)
- Real-time prediction and model registry

### AI Analysis
- Trade pattern recognition and risk anomaly detection
- Drawdown explanation and parameter suggestions
- Weekly/monthly natural language performance reports
- Strategy comparison analysis
- **Isolated from execution** — AI never places trades

### Frontend & UI
- **Professional UI** with glassmorphism login, animated backgrounds, and Framer Motion transitions
- TradingView Advanced Chart integration with real-time data
- **Sidebar:** Collapsible (240px/64px), left-border active indicator, user avatar, risk badge, tooltips
- **Header:** Contextual breadcrumb, live dual clock (UTC + Bogota), active session indicator (Asian/London/NY)
- **Trading Page:** Symbol context header with P&L chip, session-aware stat cards with sparkline backgrounds
- **Backtest Page:** Collapsible form sections, hero metric cards, compare mode with tabs, enhanced equity chart
- **Equity Chart:** Initial balance reference line, custom tooltip (P&L + drawdown), return % badge
- Dark theme with semantic colors (green profit, red loss, amber warning)
- European number formatting (5.000 instead of 5,000)
- 21st.dev inspired components (Radix UI + Tailwind + lucide-react + Framer Motion)

### Infrastructure
- Supabase Auth (JWT) with RBAC (admin only)
- Development auth bypass for faster iteration
- Background tasks with Celery + Redis
- Full audit logging with commission/swap tracking
- Trade history with MT5 fallback when database is empty

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Login** | Glassmorphism card with animated gradient orbs, system health indicator, Framer Motion stagger animations |
| **Trading** | Symbol context header with P&L chip, stat cards with sparklines, TradingView chart, bot control, positions table |
| **Backtest** | Collapsible config sections, hero metrics (Net Profit/Win Rate/Profit Factor), date range mode with warmup, compare mode tabs, session analysis, BUY/SELL distribution, enhanced equity chart |
| **ML Models** | Train XGBoost models, view predictions, manage saved model registry |
| **AI Analysis** | AI trade pattern analysis, risk review, drawdown explanation, performance summaries |
| **Risk** | Real-time risk gauges — max drawdown, daily loss, overtrading protection status |
| **Audit Log** | Trade history with symbol/date filters, pagination, commission and swap tracking |
| **Settings** | Platform information and system status |

## BiasStrategy V1 (Smart Money Concepts)

**Status:** ✅ Production-ready | **Optimization:** V1 complete + SELL Surgery (Feb 2026)

Professional SMC-based strategy with symmetric BUY/SELL logic, tested on real MT5 data (20k bars H1).

### Core Methodology
1. **Daily Bias** - D1 candle analysis (BULLISH/BEARISH/NEUTRAL with Doji detection)
2. **London Manipulation** - PDH/PDL sweep detection (02:00-11:30 Bogotá)
3. **NY Session Entry** - ChoCh or fractal break confirmation (08:00-14:00 Bogotá)
4. **Shannon Entropy Filter** - Market regime detection to avoid erratic conditions

### V1 Optimizations (Feb 2026)
- **SELL Trade Surgery:** Fixed critical bug (100% BUY trades, 0% SELL) with symmetric ChoCh/Fractal logic
- **Temporal Swing Filtering:** Uses last 15 M5 bars for swing point selection (prevents stale comparisons)
- **ChoCh Symmetric Logic:** `tolerance = max(range * 0.15, pip * 2.0)` for BUY and SELL
- **Fractal Liquidity Zones:** BUY: `fractal_high - 3 pips`, SELL: `fractal_low + 1 pip` (calibrated)
- **Risk-Reward Optimized:** min_rr reduced from 1.5 to 1.3 (maximizes Net Profit on H1 timeframe)
- **Bias Neutral:** Doji detection (body <20% of D1 range) → searches sweeps in both PDH and PDL
- **Entropy Threshold:** 3.1 for moderate-high volatility acceptance
- **SMC Feature Extractor:** 20 ML features for future model training

### Backtest Results (Real MT5 Data - EURUSD H1)
```
20k bars (Feb 2026 validation):
Total Trades: 146 | Win Rate: 56.16% | Profit Factor: 1.36
Sharpe Ratio: 2.25 | Max Drawdown: 7.89% | Net Profit: $1,275
BUY/SELL Distribution: 26 BUY (17.8%), 120 SELL (82.2%)
Note: Imbalance under calibration - Fractal SELL threshold at 1.0 pips

10k bars (min_rr optimization baseline):
Total Trades: 304 | Win Rate: 49.67% | Profit Factor: 1.31
Net Profit: $2,437 (optimal for min_rr=1.3)

7k bars (post-surgery validation):
Total Trades: 41 | Win Rate: 73.17% | Profit Factor: 3.38
Sharpe Ratio: 8.33 | Net Profit: $1,526
```

**Recommended Timeframe:** H1 (tested and optimized). M15 not recommended without full re-optimization.

**Known Calibration Status:**
- BUY/SELL balance calibration in progress (target ratio: 0.8-1.2)
- Fractal SELL threshold adjusted to 1.0 pips (trade-off between balance and profitability)
- ChoCh SELL threshold at 1.5 pips (minimal impact on distribution)

**Files:**
- `backend/app/strategies/bias.py` - Main strategy (1000 lines, ChoCh/Fractal logic lines 847-1012)
- `backend/app/ml/smc_feature_extractor.py` - ML features (450 lines)
- `backend/tests/test_bias_strategy.py` - Unit tests (25 tests)

---

## Architecture

The platform follows **Clean Architecture + SOLID** principles with a monolithic modular design:

```
Signal Flow:  MT5 Market Data → Strategy (Rules/ML) → Risk Engine → Execution → MT5
AI Flow:      Trade History → LLM Analysis → Reports (never touches execution)
```

- **Strategies** generate signals (BUY/SELL/HOLD) from market data
- **Risk Engine** validates every signal before execution (lot sizing, drawdown limits, daily caps)
- **Execution Engine** sends validated orders to MetaTrader 5
- **AI Analysis** runs in parallel — reads trade data, generates insights, but never executes

Development was completed in 3 phases + V1 optimization + UI redesign:
1. Backend Core + MT5 integration + Risk Engine
2. Backtesting Engine + ML Module (XGBoost)
3. Frontend (Next.js 14 + Material UI) + AI Analysis (OpenAI)
4. **BiasStrategy V1 Optimization** - Smart Money Concepts refinement + SELL trade surgery + min_rr optimization (Feb 2026)
5. **UI/UX Redesign** - Professional trading interface: glassmorphism login, session-aware header, hero metrics, collapsible backtest form, enhanced equity chart (Mar 2026)

## Quick Start

### 1. Clone repository

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
# Edit .env with your credentials (Supabase, OpenAI, MT5)
```

### 3. Start Redis (Docker)

```bash
docker-compose up -d redis
```

### 4. Run backend

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### 5. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with Supabase credentials
npm run dev
```

Dashboard available at `http://localhost:3000`

> **Development mode:** Auth is bypassed automatically (no login required).
> **Collapsible sidebar:** Click the "Hide" toggle at the bottom to collapse/expand.

### 6. Run tests

```bash
cd backend
pytest tests/ -v    # 51 unit tests
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
│   │   ├── strategies/          # Trading strategies (bias SMC V1, fibonacci, ict, manual, hybrid_ml)
│   │   ├── risk/                # Risk engine (circuit breaker, kill switch, lot calculator)
│   │   ├── execution/           # Execution engine (signal → risk → MT5)
│   │   ├── backtesting/         # Backtesting engine + metrics + simulator
│   │   ├── ml/                  # XGBoost ML pipeline + feature engineering + SMC extractor
│   │   ├── ai_analysis/         # LLM-powered trade analysis (OpenAI)
│   │   ├── tasks/               # Celery background tasks
│   │   └── integrations/        # MT5 client, Supabase client
│   ├── tests/                   # 51 unit tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js 14 pages (App Router)
│   │   │   ├── login/           # Supabase Auth login
│   │   │   └── (dashboard)/     # Protected routes (7 pages)
│   │   ├── components/          # layout/, charts/, trading/, common/, ui/
│   │   ├── lib/                 # API client, Supabase, theme, number formatting
│   │   ├── store/               # Zustand state management
│   │   └── types/               # TypeScript interfaces
│   ├── package.json
│   └── .env.local.example
├── docker-compose.yml           # Redis + Celery worker
├── CLAUDE.md                    # AI coding guidelines
└── README.md
```

For detailed file-by-file documentation, see [CLAUDE.md](CLAUDE.md).

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async) |
| Frontend | Next.js 14, TypeScript, Material UI v7, Recharts |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase JWT verification, RBAC |
| Trading | MetaTrader5 Python package |
| ML | XGBoost, scikit-learn |
| AI Analysis | OpenAI GPT-4o-mini |
| Task Queue | Celery + Redis |
| State Mgmt | Zustand |
| Charts | TradingView Advanced Chart, Recharts |
| Icons | lucide-react |

## Roadmap

- [x] Phase 1: Backend Core + MT5 integration + Risk Engine
- [x] Phase 2: Backtesting Engine + ML Module
- [x] Phase 3: Frontend (Next.js 14 + Material UI) + AI Analysis (OpenAI)
- [x] Phase 4: BiasStrategy V1 Optimization + SELL Trade Surgery (Feb 2026)
- [x] Phase 5: UI/UX Redesign - Professional trading interface (Mar 2026)

## Testing & Development

```bash
# Run all tests (51 total)
pytest tests/ -v

# Run specific test module
pytest tests/test_risk_manager.py -v

# Linting
ruff check app/
ruff format app/

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Clear frontend cache (if build errors)
rm -rf frontend/.next && cd frontend && npm run build
```

## Troubleshooting

### Audit Logs Empty
**Cause:** No closed trades in database yet.
**Solution:**
1. Close existing positions in Trading page, OR
2. The system automatically falls back to MT5 `history_deals_get()` when DB is empty
3. See `backend/SYNC_INSTRUCTIONS.md` for manual sync options

### Backtest Returns 0 Trades
**Cause:** Insufficient historical data or strict strategy parameters.
**Solution:**
- Increase "Bars" parameter (try 10,000+)
- Verify MT5 has historical data for selected symbol/timeframe
- Adjust strategy parameters (wider SL/TP ranges)

### Symbol Not Found Error
**Cause:** Symbol not available in MT5 broker.
**Solution:** Add symbol in MT5 Market Watch first

### Bot Not Starting
**Cause:** MT5 not connected or terminal not running.
**Solution:**
- Ensure MetaTrader 5 is open and logged in
- Check that the symbol is visible in Market Watch
- Verify backend `.env` has correct MT5 credentials

### No Metrics Displayed
**Cause:** No trades have been executed yet.
**Solution:**
- Start the bot and wait for signals, OR
- Place a manual trade from the Trading page
- Metrics update after trades are opened/closed

### Frontend Build Errors
**Cause:** Stale Next.js cache.
**Solution:** `rm -rf frontend/.next && cd frontend && npm run build`
