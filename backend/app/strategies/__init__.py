from app.strategies.base import BaseStrategy, SignalDirection, TradeSignal
from app.strategies.bias import BiasStrategy
from app.strategies.fibonacci import FibonacciStrategy
from app.strategies.hybrid_ml import HybridMLStrategy
from app.strategies.ict import ICTStrategy
from app.strategies.manual import ManualStrategy

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "fibonacci": FibonacciStrategy,
    "ict": ICTStrategy,
    "manual": ManualStrategy,
    "hybrid_ml": HybridMLStrategy,
    "bias": BiasStrategy,
}


def get_strategy(name: str, **kwargs) -> BaseStrategy:
    """Get a strategy instance by name."""
    strategy_class = STRATEGY_REGISTRY.get(name)
    if strategy_class is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}")
    return strategy_class(**kwargs)
