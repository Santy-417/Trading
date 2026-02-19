-- ============================================================================
-- TRADING PLATFORM - OPTIMIZED DATABASE MIGRATION
-- Compatible with Supabase (PostgreSQL 15+)
-- Includes: RLS, Indexes, Triggers, Constraints
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- DROP EXISTING TABLES (if any)
-- ============================================================================
DROP TABLE IF EXISTS public.alembic_version CASCADE;
DROP TABLE IF EXISTS public.audit_logs CASCADE;
DROP TABLE IF EXISTS public.backtest_results CASCADE;
DROP TABLE IF EXISTS public.bot_config CASCADE;
DROP TABLE IF EXISTS public.ml_models CASCADE;
DROP TABLE IF EXISTS public.risk_events CASCADE;
DROP TABLE IF EXISTS public.strategies CASCADE;
DROP TABLE IF EXISTS public.trades CASCADE;

-- ============================================================================
-- CREATE TABLES
-- ============================================================================

-- Alembic version tracking
CREATE TABLE public.alembic_version (
  version_num VARCHAR(32) NOT NULL,
  CONSTRAINT alembic_version_pkey PRIMARY KEY (version_num)
);

-- Trades table (core trading data)
CREATE TABLE public.trades (
  id UUID NOT NULL DEFAULT uuid_generate_v4(),
  symbol VARCHAR(20) NOT NULL,
  direction VARCHAR(10) NOT NULL CHECK (direction IN ('BUY', 'SELL')),
  lot_size NUMERIC(10, 2) NOT NULL CHECK (lot_size > 0),
  entry_price NUMERIC(20, 5) NOT NULL CHECK (entry_price > 0),
  stop_loss NUMERIC(20, 5),
  take_profit NUMERIC(20, 5),
  exit_price NUMERIC(20, 5),
  profit NUMERIC(20, 2) DEFAULT 0,
  commission NUMERIC(20, 2) NOT NULL DEFAULT 0,
  swap NUMERIC(20, 2) NOT NULL DEFAULT 0,
  strategy VARCHAR(50) NOT NULL,
  timeframe VARCHAR(10) NOT NULL,
  mt5_ticket BIGINT UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed', 'pending')),
  opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  closed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT trades_pkey PRIMARY KEY (id),
  CONSTRAINT trades_close_check CHECK (
    (status = 'closed' AND closed_at IS NOT NULL AND exit_price IS NOT NULL) OR
    (status != 'closed')
  )
);

-- Audit logs (system events tracking)
CREATE TABLE public.audit_logs (
  id UUID NOT NULL DEFAULT uuid_generate_v4(),
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50),
  entity_id VARCHAR(100),
  details JSONB DEFAULT '{}'::jsonb,
  ip_address VARCHAR(45),
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT audit_logs_pkey PRIMARY KEY (id)
);

-- Backtest results
CREATE TABLE public.backtest_results (
  id UUID NOT NULL DEFAULT uuid_generate_v4(),
  strategy VARCHAR(50) NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  timeframe VARCHAR(10) NOT NULL,
  total_trades INTEGER NOT NULL DEFAULT 0 CHECK (total_trades >= 0),
  win_rate NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (win_rate >= 0 AND win_rate <= 100),
  net_profit NUMERIC(20, 2) NOT NULL DEFAULT 0,
  profit_factor NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (profit_factor >= 0),
  sharpe_ratio NUMERIC(10, 2) NOT NULL DEFAULT 0,
  max_drawdown_percent NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (max_drawdown_percent >= 0),
  initial_balance NUMERIC(20, 2) NOT NULL DEFAULT 10000 CHECK (initial_balance > 0),
  final_balance NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (final_balance >= 0),
  params JSONB DEFAULT '{}'::jsonb,
  full_metrics JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT backtest_results_pkey PRIMARY KEY (id)
);

-- Bot configuration
CREATE TABLE public.bot_config (
  id UUID NOT NULL DEFAULT uuid_generate_v4(),
  name VARCHAR(100) NOT NULL DEFAULT 'default' UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  strategy VARCHAR(50) NOT NULL DEFAULT 'fibonacci',
  symbols TEXT[] NOT NULL DEFAULT ARRAY['EURUSD', 'XAUUSD'],
  timeframe VARCHAR(10) NOT NULL DEFAULT 'H1',
  risk_per_trade NUMERIC(5, 2) NOT NULL DEFAULT 1.0 CHECK (risk_per_trade > 0 AND risk_per_trade <= 10),
  lot_mode VARCHAR(20) NOT NULL DEFAULT 'percent_risk' CHECK (lot_mode IN ('fixed', 'percent_risk', 'dynamic')),
  fixed_lot NUMERIC(10, 2) NOT NULL DEFAULT 0.01 CHECK (fixed_lot > 0),
  max_trades_per_hour INTEGER NOT NULL DEFAULT 10 CHECK (max_trades_per_hour > 0),
  strategy_params JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT bot_config_pkey PRIMARY KEY (id)
);

-- ML Models registry
CREATE TABLE public.ml_models (
  id UUID NOT NULL DEFAULT uuid_generate_v4(),
  model_id VARCHAR(100) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  timeframe VARCHAR(10) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  metrics JSONB DEFAULT '{}'::jsonb,
  feature_importance JSONB DEFAULT '{}'::jsonb,
  params JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ml_models_pkey PRIMARY KEY (id)
);

-- Risk events tracking
CREATE TABLE public.risk_events (
  id UUID NOT NULL DEFAULT uuid_generate_v4(),
  event_type VARCHAR(50) NOT NULL,
  severity VARCHAR(20) NOT NULL DEFAULT 'warning' CHECK (severity IN ('info', 'warning', 'critical')),
  message TEXT NOT NULL,
  current_value NUMERIC(20, 2),
  threshold_value NUMERIC(20, 2),
  action_taken VARCHAR(50) NOT NULL DEFAULT 'none',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT risk_events_pkey PRIMARY KEY (id)
);

-- Strategy definitions
CREATE TABLE public.strategies (
  id UUID NOT NULL DEFAULT uuid_generate_v4(),
  name VARCHAR(50) NOT NULL UNIQUE,
  description TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
  supported_symbols JSONB DEFAULT '[]'::jsonb,
  supported_timeframes JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT strategies_pkey PRIMARY KEY (id)
);

-- ============================================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Trades table indexes
CREATE INDEX idx_trades_symbol ON public.trades(symbol);
CREATE INDEX idx_trades_status ON public.trades(status);
CREATE INDEX idx_trades_strategy ON public.trades(strategy);
CREATE INDEX idx_trades_mt5_ticket ON public.trades(mt5_ticket) WHERE mt5_ticket IS NOT NULL;
CREATE INDEX idx_trades_opened_at ON public.trades(opened_at DESC);
CREATE INDEX idx_trades_closed_at ON public.trades(closed_at DESC) WHERE closed_at IS NOT NULL;
CREATE INDEX idx_trades_symbol_status ON public.trades(symbol, status);
CREATE INDEX idx_trades_strategy_symbol ON public.trades(strategy, symbol);

-- Audit logs indexes
CREATE INDEX idx_audit_logs_created_at ON public.audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON public.audit_logs(action);
CREATE INDEX idx_audit_logs_entity ON public.audit_logs(entity_type, entity_id);

-- Backtest results indexes
CREATE INDEX idx_backtest_strategy ON public.backtest_results(strategy);
CREATE INDEX idx_backtest_symbol ON public.backtest_results(symbol);
CREATE INDEX idx_backtest_created_at ON public.backtest_results(created_at DESC);
CREATE INDEX idx_backtest_strategy_symbol ON public.backtest_results(strategy, symbol);

-- ML Models indexes
CREATE INDEX idx_ml_models_symbol ON public.ml_models(symbol);
CREATE INDEX idx_ml_models_active ON public.ml_models(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_ml_models_created_at ON public.ml_models(created_at DESC);

-- Risk events indexes
CREATE INDEX idx_risk_events_created_at ON public.risk_events(created_at DESC);
CREATE INDEX idx_risk_events_severity ON public.risk_events(severity);
CREATE INDEX idx_risk_events_type ON public.risk_events(event_type);

-- ============================================================================
-- CREATE TRIGGER FUNCTION FOR updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ATTACH TRIGGERS TO TABLES
-- ============================================================================

CREATE TRIGGER update_trades_updated_at
  BEFORE UPDATE ON public.trades
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_audit_logs_updated_at
  BEFORE UPDATE ON public.audit_logs
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_backtest_results_updated_at
  BEFORE UPDATE ON public.backtest_results
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_bot_config_updated_at
  BEFORE UPDATE ON public.bot_config
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_ml_models_updated_at
  BEFORE UPDATE ON public.ml_models
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_risk_events_updated_at
  BEFORE UPDATE ON public.risk_events
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_strategies_updated_at
  BEFORE UPDATE ON public.strategies
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- ENABLE ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.backtest_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategies ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- CREATE RLS POLICIES (Admin-only access via service_role)
-- ============================================================================

-- Trades policies
CREATE POLICY "Enable all access for service_role" ON public.trades
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable read for authenticated users" ON public.trades
  FOR SELECT
  TO authenticated
  USING (true);

-- Audit logs policies
CREATE POLICY "Enable all access for service_role" ON public.audit_logs
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable read for authenticated users" ON public.audit_logs
  FOR SELECT
  TO authenticated
  USING (true);

-- Backtest results policies
CREATE POLICY "Enable all access for service_role" ON public.backtest_results
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable read for authenticated users" ON public.backtest_results
  FOR SELECT
  TO authenticated
  USING (true);

-- Bot config policies
CREATE POLICY "Enable all access for service_role" ON public.bot_config
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable read for authenticated users" ON public.bot_config
  FOR SELECT
  TO authenticated
  USING (true);

-- ML models policies
CREATE POLICY "Enable all access for service_role" ON public.ml_models
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable read for authenticated users" ON public.ml_models
  FOR SELECT
  TO authenticated
  USING (true);

-- Risk events policies
CREATE POLICY "Enable all access for service_role" ON public.risk_events
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable read for authenticated users" ON public.risk_events
  FOR SELECT
  TO authenticated
  USING (true);

-- Strategies policies
CREATE POLICY "Enable all access for service_role" ON public.strategies
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable read for authenticated users" ON public.strategies
  FOR SELECT
  TO authenticated
  USING (true);

-- ============================================================================
-- INSERT DEFAULT DATA
-- ============================================================================

-- Default bot configuration
INSERT INTO public.bot_config (name, is_active, strategy, symbols, timeframe, risk_per_trade, lot_mode, fixed_lot, max_trades_per_hour, strategy_params)
VALUES (
  'default',
  FALSE,
  'fibonacci',
  ARRAY['EURUSD', 'XAUUSD'],
  'H1',
  1.0,
  'percent_risk',
  0.01,
  10,
  '{}'::jsonb
) ON CONFLICT (name) DO NOTHING;

-- Default strategies
INSERT INTO public.strategies (name, description, is_active, parameters, supported_symbols, supported_timeframes)
VALUES
  ('fibonacci', 'Fibonacci retracement and extension based strategy', TRUE, '{"retracement_levels": [0.382, 0.5, 0.618], "extension_levels": [1.272, 1.618]}'::jsonb, '["EURUSD", "XAUUSD"]'::jsonb, '["M15", "H1", "H4"]'::jsonb),
  ('ict', 'ICT (Inner Circle Trader) strategy with order blocks and FVG', TRUE, '{"min_ob_size": 20, "fvg_threshold": 0.5}'::jsonb, '["EURUSD", "XAUUSD"]'::jsonb, '["M15", "H1", "H4"]'::jsonb),
  ('hybrid_ml', 'Hybrid strategy combining rules and machine learning', TRUE, '{"min_ml_confidence": 0.6, "use_technical_filters": true}'::jsonb, '["EURUSD", "XAUUSD"]'::jsonb, '["H1", "H4"]'::jsonb),
  ('manual', 'Manual trade execution', TRUE, '{}'::jsonb, '["EURUSD", "XAUUSD"]'::jsonb, '["M1", "M5", "M15", "H1", "H4", "D1"]'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- Set Alembic version
INSERT INTO public.alembic_version (version_num) VALUES ('initial_migration_2026_02_19');

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- Grant table permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;

-- Grant sequence permissions
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- ============================================================================
-- CREATE VIEWS (Optional - for easier querying)
-- ============================================================================

-- View: Open positions with calculated profit
CREATE OR REPLACE VIEW public.v_open_positions AS
SELECT
  id,
  symbol,
  direction,
  lot_size,
  entry_price,
  stop_loss,
  take_profit,
  strategy,
  timeframe,
  mt5_ticket,
  opened_at,
  EXTRACT(EPOCH FROM (NOW() - opened_at)) / 3600 AS hours_open,
  profit AS current_profit
FROM public.trades
WHERE status = 'open'
ORDER BY opened_at DESC;

-- View: Today's trading summary
CREATE OR REPLACE VIEW public.v_today_summary AS
SELECT
  COUNT(*) FILTER (WHERE status = 'closed') AS total_closed_today,
  COUNT(*) FILTER (WHERE status = 'open') AS total_open,
  COALESCE(SUM(profit) FILTER (WHERE status = 'closed'), 0) AS closed_pnl,
  COALESCE(SUM(profit) FILTER (WHERE status = 'open'), 0) AS open_pnl,
  COALESCE(SUM(profit), 0) AS total_pnl
FROM public.trades
WHERE opened_at >= CURRENT_DATE;

-- View: Performance by strategy
CREATE OR REPLACE VIEW public.v_strategy_performance AS
SELECT
  strategy,
  COUNT(*) AS total_trades,
  COUNT(*) FILTER (WHERE profit > 0) AS winning_trades,
  COUNT(*) FILTER (WHERE profit < 0) AS losing_trades,
  ROUND(AVG(profit), 2) AS avg_profit,
  ROUND(SUM(profit), 2) AS net_profit,
  ROUND(
    (COUNT(*) FILTER (WHERE profit > 0)::NUMERIC / NULLIF(COUNT(*), 0) * 100),
    2
  ) AS win_rate_percent
FROM public.trades
WHERE status = 'closed'
GROUP BY strategy
ORDER BY net_profit DESC;

-- Grant view permissions
GRANT SELECT ON public.v_open_positions TO authenticated, service_role;
GRANT SELECT ON public.v_today_summary TO authenticated, service_role;
GRANT SELECT ON public.v_strategy_performance TO authenticated, service_role;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Verify tables
SELECT
  schemaname,
  tablename,
  rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Verify indexes
SELECT
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

COMMENT ON DATABASE postgres IS 'Trading Platform Database - Optimized with RLS, Indexes, and Triggers';
