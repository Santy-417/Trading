-- Fix mt5_ticket column to support large MT5 ticket numbers
-- MT5 tickets can exceed INT32 range (2,147,483,647)
-- This changes the column from INTEGER to BIGINT

-- Step 1: Drop dependent views
DROP VIEW IF EXISTS public.v_open_positions CASCADE;
DROP VIEW IF EXISTS public.v_today_summary CASCADE;
DROP VIEW IF EXISTS public.v_strategy_performance CASCADE;

-- Step 2: Alter the column type
ALTER TABLE public.trades
  ALTER COLUMN mt5_ticket TYPE BIGINT;

-- Step 3: Recreate the views

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

-- Step 4: Grant view permissions
GRANT SELECT ON public.v_open_positions TO authenticated, service_role;
GRANT SELECT ON public.v_today_summary TO authenticated, service_role;
GRANT SELECT ON public.v_strategy_performance TO authenticated, service_role;

-- Step 5: Verify the change
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'trades'
  AND column_name = 'mt5_ticket';

-- Result should show: mt5_ticket | bigint | null
