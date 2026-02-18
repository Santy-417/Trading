// ─── Bot ──────────────────────────────────────────────
export interface BotStartRequest {
  strategy: string;
  symbols: string[];
  timeframe: string;
  risk_per_trade?: number;
  max_daily_loss?: number;
  lot_mode?: "fixed" | "percent_risk" | "dynamic";
  fixed_lot_size?: number;
  strategy_params?: Record<string, unknown>;
}

export interface BotStatusResponse {
  state: string;
  strategy: string | null;
  symbols: string[];
  timeframe: string | null;
  risk_per_trade: number;
  max_daily_loss: number;
  lot_mode: string;
  uptime_seconds: number | null;
}

// ─── Orders ───────────────────────────────────────────
export interface MarketOrderRequest {
  symbol: string;
  direction: "BUY" | "SELL";
  volume: number;
  stop_loss?: number;
  take_profit?: number;
  comment?: string;
}

export interface OrderResponse {
  success: boolean;
  ticket: number | null;
  price: number | null;
  volume: number | null;
  comment: string;
  retcode: number | null;
}

export interface Position {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  price_open: number;
  price_current: number;
  stop_loss: number;
  take_profit: number;
  profit: number;
  swap: number;
  commission: number;
  comment: string;
  time_open: string;
}

// ─── Trades ───────────────────────────────────────────
export interface Trade {
  id: string;
  symbol: string;
  direction: string;
  lot_size: number;
  entry_price: number;
  exit_price: number | null;
  stop_loss: number;
  take_profit: number;
  profit: number | null;
  strategy: string;
  status: string;
  opened_at: string;
  closed_at: string | null;
}

// ─── Backtest ─────────────────────────────────────────
export interface BacktestRequest {
  strategy: string;
  symbol: string;
  timeframe: string;
  bars?: number;
  initial_balance?: number;
  risk_per_trade?: number;
  lot_mode?: string;
}

export interface BacktestResult {
  strategy: string;
  symbol: string;
  timeframe: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  net_profit: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown_percent: number;
  return_percent: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
  expectancy: number;
  initial_balance: number;
  final_balance: number;
  total_profit: number;
  total_loss: number;
  total_bars: number;
  equity_curve: number[];
}

// ─── ML ───────────────────────────────────────────────
export interface TrainRequest {
  symbol: string;
  timeframe: string;
  bars?: number;
  forward_bars?: number;
  model_params?: Record<string, unknown>;
}

export interface TrainResponse {
  model_id: string;
  metrics: Record<string, number>;
  top_features: Record<string, number>;
}

export interface PredictResponse {
  prediction: number;
  probability: number;
  confidence: string;
  signal: string;
}

export interface MLModel {
  model_id: string;
  symbol: string;
  timeframe: string;
  created_at: string;
  metrics: Record<string, number>;
}

// ─── AI Analysis ──────────────────────────────────────
export interface AIResponse {
  analysis: string;
  model_used: string;
}

// ─── Metrics ──────────────────────────────────────────
export interface PerformanceMetrics {
  total_trades: number;
  win_rate: number;
  net_profit: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown: number;
  today_pnl: number;
  open_positions: number;
}

export interface EquityCurvePoint {
  date: string;
  equity: number;
}
