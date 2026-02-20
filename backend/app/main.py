from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.logging_config import get_logger, setup_logging
from app.core.middleware import setup_middleware
from app.core.rate_limit import limiter
from app.integrations.metatrader.mt5_client import mt5_client
from app.routers import ai, backtest, bot, health, metrics, ml, orders

settings = get_settings()
setup_logging("INFO")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[OK] Settings validated for environment: %s", settings.app_env)
    logger.info("     - API: /api/v1")
    logger.info("     - Debug: %s", settings.app_debug)
    logger.info("     - CORS: %s", settings.cors_origins)

    # Initialize MT5 connection on startup so backtesting and ML endpoints
    # are available without needing to start the bot first.
    try:
        await mt5_client.initialize()
        logger.info("[OK] MT5 connection established on startup")
    except Exception as exc:
        logger.warning(
            "MT5 initialization failed on startup (trading features unavailable): %s", exc
        )

    yield

    logger.info("Application shutdown")
    try:
        await mt5_client.shutdown()
    except Exception:
        pass


app = FastAPI(
    title="Forex AI Trading Platform",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
setup_middleware(app)

# Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(bot.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(backtest.router, prefix="/api/v1")
app.include_router(ml.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception at %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
