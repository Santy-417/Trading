BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001_initial

CREATE TABLE trades (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    symbol VARCHAR(20) NOT NULL, 
    direction VARCHAR(10) NOT NULL, 
    lot_size NUMERIC(10, 4) NOT NULL, 
    entry_price NUMERIC(18, 8) NOT NULL, 
    stop_loss NUMERIC(18, 8), 
    take_profit NUMERIC(18, 8), 
    exit_price NUMERIC(18, 8), 
    profit NUMERIC(18, 4), 
    commission NUMERIC(10, 4) DEFAULT 0, 
    swap NUMERIC(10, 4) DEFAULT 0, 
    strategy VARCHAR(50) NOT NULL, 
    timeframe VARCHAR(10) NOT NULL, 
    mt5_ticket INTEGER, 
    status VARCHAR(20) DEFAULT 'open' NOT NULL, 
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    closed_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_trades_symbol ON trades (symbol);

CREATE INDEX ix_trades_status ON trades (status);

CREATE INDEX ix_trades_opened_at ON trades (opened_at);

CREATE INDEX ix_trades_strategy ON trades (strategy);

CREATE TABLE bot_config (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(100) DEFAULT 'default', 
    is_active BOOLEAN DEFAULT false, 
    strategy VARCHAR(50) DEFAULT 'fibonacci' NOT NULL, 
    symbols VARCHAR[] DEFAULT ARRAY['EURUSD','XAUUSD'], 
    timeframe VARCHAR(10) DEFAULT 'H1', 
    risk_per_trade NUMERIC(5, 2) DEFAULT 1.0, 
    lot_mode VARCHAR(20) DEFAULT 'percent_risk', 
    fixed_lot NUMERIC(10, 4) DEFAULT 0.01, 
    max_trades_per_hour INTEGER DEFAULT 10, 
    strategy_params JSONB DEFAULT '{}', 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE risk_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    event_type VARCHAR(50) NOT NULL, 
    severity VARCHAR(20) DEFAULT 'warning' NOT NULL, 
    message TEXT NOT NULL, 
    current_value NUMERIC(18, 4), 
    threshold_value NUMERIC(18, 4), 
    action_taken VARCHAR(50) DEFAULT 'none', 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_risk_events_type ON risk_events (event_type);

CREATE INDEX ix_risk_events_severity ON risk_events (severity);

CREATE INDEX ix_risk_events_created ON risk_events (created_at);

CREATE TABLE audit_logs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    action VARCHAR(100) NOT NULL, 
    entity_type VARCHAR(50), 
    entity_id VARCHAR(50), 
    details JSONB, 
    ip_address VARCHAR(45), 
    user_agent TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_created ON audit_logs (created_at);

CREATE TABLE strategies (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR(50) NOT NULL, 
    description TEXT, 
    is_active BOOLEAN DEFAULT true, 
    parameters JSONB DEFAULT '{}', 
    supported_symbols JSONB, 
    supported_timeframes JSONB, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE TABLE backtest_results (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    strategy VARCHAR(50) NOT NULL, 
    symbol VARCHAR(20) NOT NULL, 
    timeframe VARCHAR(10) NOT NULL, 
    total_trades INTEGER DEFAULT 0, 
    win_rate NUMERIC(6, 2) DEFAULT 0, 
    net_profit NUMERIC(18, 2) DEFAULT 0, 
    profit_factor NUMERIC(8, 2) DEFAULT 0, 
    sharpe_ratio NUMERIC(8, 2) DEFAULT 0, 
    max_drawdown_percent NUMERIC(6, 2) DEFAULT 0, 
    initial_balance NUMERIC(18, 2) DEFAULT 10000, 
    final_balance NUMERIC(18, 2) DEFAULT 0, 
    params JSONB, 
    full_metrics JSONB, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE ml_models (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    model_id VARCHAR(100) NOT NULL, 
    name VARCHAR(50) NOT NULL, 
    symbol VARCHAR(20) NOT NULL, 
    timeframe VARCHAR(10) NOT NULL, 
    is_active BOOLEAN DEFAULT false, 
    metrics JSONB, 
    feature_importance JSONB, 
    params JSONB, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (model_id)
);

INSERT INTO alembic_version (version_num) VALUES ('001_initial') RETURNING alembic_version.version_num;

COMMIT;

