# Forex AI Trading Platform

Professional-grade automated Forex trading platform running locally on Windows with MetaTrader 5.

## Features

- Rule-based + ML trading strategies (Fibonacci, ICT, Hybrid ML)
- Strict risk management (circuit breaker, kill switch, daily loss cap, overtrading protection)
- Professional backtesting engine with spread/commission/slippage simulation
- ML module with XGBoost + walk-forward validation
- Supabase Auth (JWT) with RBAC
- LLM-based trade analysis (OpenAI) — isolated, never executes trades
- Background tasks with Celery + Redis
- Full audit logging

## Quick Start

### 1. Clonar repositorio

```bash
git clone https://github.com/Santy-417/Trading.git
cd Trading
```

### 2. Crear virtual environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copiar `.env.example` a `.env` y completar con tus credenciales:

```bash
cp .env.example .env
```

Editar `.env` con:
- Credenciales de Supabase (URL, Anon Key, JWT Secret)
- Connection string de la base de datos (PostgreSQL async)
- Credenciales de MetaTrader 5
- API Key de OpenAI (para Phase 3)

### 5. Levantar Redis (Docker)

```bash
docker-compose up -d redis
```

### 6. Ejecutar servidor

```bash
uvicorn app.main:app --reload --port 8000
```

El servidor estara disponible en `http://localhost:8000/docs`

### 7. Ejecutar tests

```bash
pytest tests/ -v
```

## Project Structure

```
Trading/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app assembly
│   │   ├── core/                # Config, security, middleware, rate limiting, logging
│   │   ├── routers/             # API endpoints (health, bot, orders, metrics, backtest, ml)
│   │   ├── services/            # Business logic layer
│   │   ├── repositories/        # Data access layer
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── strategies/          # Trading strategies (fibonacci, ict, manual, hybrid_ml)
│   │   ├── risk/                # Risk engine (circuit breaker, kill switch, lot calculator)
│   │   ├── execution/           # Execution engine (signal → risk → MT5)
│   │   ├── backtesting/         # Backtesting engine + metrics + simulator
│   │   ├── ml/                  # XGBoost ML pipeline + feature engineering
│   │   ├── tasks/               # Celery background tasks
│   │   └── integrations/        # MT5 client, Supabase client
│   ├── tests/                   # 51 unit tests
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml           # Redis + Celery worker
├── CLAUDE.md
└── README.md
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase JWT verification |
| Trading | MetaTrader5 Python package |
| ML | XGBoost, scikit-learn |
| Task Queue | Celery + Redis |
| Pairs | XAUUSD (Gold), EURUSD |

## Roadmap

- [x] Phase 1: Backend Core + MT5 integration + Risk Engine
- [x] Phase 2: Backtesting Engine + ML Module
- [ ] Phase 3: Frontend (Next.js 14 + Material UI) + AI Analysis (OpenAI)

## Architecture

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.
