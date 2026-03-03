"use client";

import { useState, useCallback } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Chip,
  CircularProgress,
  Snackbar,
  TextField,
  Switch,
  FormControlLabel,
  Divider,
  Collapse,
  Tabs,
  Tab,
} from "@mui/material";
import { SelectDropdown } from "@/components/ui/select-dropdown";
import Grid from "@mui/material/Grid";
import {
  Play,
  Calendar,
  BarChart3,
  GitCompare,
  ChevronDown,
  ChevronUp,
  Target,
  Award,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  Info,
} from "lucide-react";
import EquityChart from "@/components/charts/EquityChart";
import TradeAuditCarousel from "@/components/trading/TradeAuditCarousel";
import api from "@/lib/api";
import type { BacktestResult } from "@/types";
import { formatNumberWithDots } from "@/lib/numberFormat";
import { FormattedNumberInput } from "@/components/ui/formatted-number-input";
import { motion, AnimatePresence } from "framer-motion";

interface BarEstimate {
  estimated_bars: number;
  warmup_bars: number;
  trading_bars: number;
}

/* ---------- Hero Metric Card ---------- */
function HeroMetric({
  label,
  value,
  subtitle,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <Card
      sx={{
        border: `1px solid ${color}18`,
        background: `linear-gradient(135deg, ${color}06 0%, transparent 60%)`,
      }}
    >
      <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <Box>
            <Typography
              sx={{
                fontSize: 11,
                fontWeight: 500,
                color: "#64748b",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                mb: 0.5,
              }}
            >
              {label}
            </Typography>
            <Typography
              sx={{
                fontSize: 26,
                fontWeight: 700,
                color,
                lineHeight: 1.2,
                fontFeatureSettings: '"tnum"',
              }}
            >
              {value}
            </Typography>
            {subtitle && (
              <Typography sx={{ fontSize: 11, color: "#64748b", mt: 0.5 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              bgcolor: `${color}10`,
              border: `1px solid ${color}15`,
            }}
          >
            <Icon size={20} style={{ color }} />
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

/* ---------- Collapsible Section ---------- */
function Section({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Box>
      <Box
        onClick={() => setOpen(!open)}
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          py: 1,
          "&:hover .section-chevron": { color: "text.primary" },
        }}
      >
        <Typography
          sx={{
            fontSize: 11,
            fontWeight: 600,
            color: "#64748b",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          {title}
        </Typography>
        <Box className="section-chevron" sx={{ color: "#475569", transition: "color 0.15s" }}>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </Box>
      </Box>
      <Collapse in={open}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pb: 1 }}>
          {children}
        </Box>
      </Collapse>
    </Box>
  );
}

/* ---------- Metric Row Helper ---------- */
function MetricValue({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        py: 0.75,
        borderBottom: "1px solid rgba(148,163,184,0.06)",
      }}
    >
      <Typography sx={{ fontSize: 12, color: "#94a3b8" }}>{label}</Typography>
      <Typography
        sx={{
          fontSize: 12,
          fontWeight: 600,
          color: color || "text.primary",
          fontFeatureSettings: '"tnum"',
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

/* ========== MAIN PAGE ========== */
export default function BacktestPage() {
  const [strategy, setStrategy] = useState("fibonacci");
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [bars, setBars] = useState("5000");
  const [balance, setBalance] = useState("10000");
  const [risk, setRisk] = useState("1.0");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState("");

  // Date range mode
  const [useDateRange, setUseDateRange] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [warmupBars, setWarmupBars] = useState("200");
  const [estimate, setEstimate] = useState<BarEstimate | null>(null);

  // Compare mode
  const [compareMode, setCompareMode] = useState(false);
  const [resultB, setResultB] = useState<BacktestResult | null>(null);
  const [compareTab, setCompareTab] = useState(0);

  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error" | "warning";
  }>({ open: false, message: "", severity: "success" });

  const fetchEstimate = useCallback(async () => {
    if (!dateFrom || !dateTo) return;
    try {
      const { data } = await api.post<BarEstimate>("/backtest/estimate", {
        timeframe,
        date_from: dateFrom,
        date_to: dateTo,
        timezone: "America/Bogota",
        warmup_bars: parseInt(warmupBars) || 200,
      });
      setEstimate(data);
    } catch {
      setEstimate(null);
    }
  }, [dateFrom, dateTo, timeframe, warmupBars]);

  const handleDateFromChange = (val: string) => {
    setDateFrom(val);
    if (val && dateTo) setTimeout(fetchEstimate, 100);
  };

  const handleDateToChange = (val: string) => {
    setDateTo(val);
    if (dateFrom && val) setTimeout(fetchEstimate, 100);
  };

  const handleRun = async (isCompareB = false) => {
    const balanceNum = parseFloat(balance) || 10000;
    const riskNum = parseFloat(risk) || 1.0;

    if (balanceNum < 100) {
      setSnackbar({ open: true, message: "Initial balance must be at least $100", severity: "error" });
      return;
    }
    if (riskNum < 0.1 || riskNum > 5.0) {
      setSnackbar({ open: true, message: "Risk per trade must be between 0.1% and 5.0%", severity: "error" });
      return;
    }

    if (useDateRange) {
      if (!dateFrom || !dateTo) {
        setSnackbar({ open: true, message: "Both start and end dates are required", severity: "error" });
        return;
      }
      if (new Date(dateTo) <= new Date(dateFrom)) {
        setSnackbar({ open: true, message: "End date must be after start date", severity: "error" });
        return;
      }
    } else {
      const barsNum = parseInt(bars) || 5000;
      if (barsNum < 100 || barsNum > 50000) {
        setSnackbar({ open: true, message: "Bars must be between 100 and 50,000", severity: "error" });
        return;
      }
    }

    setLoading(true);
    setError("");
    if (!isCompareB) setResult(null);

    try {
      const payload: Record<string, unknown> = {
        strategy,
        symbol,
        timeframe,
        initial_balance: balanceNum,
        risk_per_trade: riskNum,
      };

      if (useDateRange) {
        payload.date_from = dateFrom;
        payload.date_to = dateTo;
        payload.timezone = "America/Bogota";
        payload.warmup_bars = parseInt(warmupBars) || 200;
      } else {
        payload.bars = parseInt(bars) || 5000;
      }

      const { data } = await api.post<BacktestResult>("/backtest/run", payload);

      if (data.total_trades === 0) {
        setSnackbar({
          open: true,
          message: "Backtest completed but generated 0 trades. Try different parameters or a longer timeframe.",
          severity: "warning",
        });
      } else {
        setSnackbar({
          open: true,
          message: `Backtest completed: ${data.total_trades} trades, ${data.win_rate.toFixed(1)}% win rate`,
          severity: "success",
        });
      }

      if (isCompareB) {
        setResultB(data);
        setCompareTab(2); // Switch to comparison tab
      } else {
        setResult(data);
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Backtest failed";
      setError(errorMsg);
      setSnackbar({
        open: true,
        message: `Backtest error: ${errorMsg}. Check MT5 connection and parameters.`,
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const equityData = (result?.equity_curve ?? []).map((eq, i) => ({
    date: `T${i}`,
    equity: eq,
  }));

  const dateRangeLabel =
    result?.date_from && result?.date_to
      ? `${result.date_from.split("T")[0]} → ${result.date_to.split("T")[0]}`
      : undefined;

  const initialBal = parseFloat(balance) || 10000;

  return (
    <Box>
      <Grid container spacing={3}>
        {/* ===== LEFT PANEL: Configuration ===== */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Typography
                sx={{ fontSize: 15, fontWeight: 600, mb: 2 }}
              >
                Configuration
              </Typography>

              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                {/* Section 1: Strategy & Market */}
                <Section title="Strategy & Market" defaultOpen={true}>
                  <SelectDropdown
                    label="Strategy"
                    value={strategy}
                    onValueChange={setStrategy}
                    options={[
                      { id: "fibonacci", label: "Fibonacci", description: "Fibonacci retracement/extension" },
                      { id: "ict", label: "ICT", description: "Order blocks, FVG, liquidity" },
                      { id: "hybrid_ml", label: "Hybrid ML", description: "Rules + XGBoost ML combined" },
                      { id: "bias", label: "Bias (SMC+ML)", description: "Smart Money Concepts + ML filter" },
                    ]}
                  />
                  <SelectDropdown
                    label="Symbol"
                    value={symbol}
                    onValueChange={setSymbol}
                    options={[
                      { id: "EURUSD", label: "EUR/USD", description: "Euro vs US Dollar" },
                      { id: "XAUUSD", label: "XAU/USD", description: "Gold vs US Dollar" },
                      { id: "DXY", label: "DXY", description: "US Dollar Index" },
                      { id: "USDCAD", label: "USD/CAD", description: "US Dollar vs Canadian Dollar" },
                      { id: "GBPUSD", label: "GBP/USD", description: "British Pound vs US Dollar" },
                      { id: "AUDCAD", label: "AUD/CAD", description: "Australian Dollar vs Canadian Dollar" },
                      { id: "EURJPY", label: "EUR/JPY", description: "Euro vs Japanese Yen" },
                      { id: "USDJPY", label: "USD/JPY", description: "US Dollar vs Japanese Yen" },
                      { id: "EURGBP", label: "EUR/GBP", description: "Euro vs British Pound" },
                    ]}
                  />
                  <SelectDropdown
                    label="Timeframe"
                    value={timeframe}
                    onValueChange={setTimeframe}
                    options={[
                      { id: "M5", label: "M5", description: "5 minutes" },
                      { id: "M15", label: "M15", description: "15 minutes" },
                      { id: "H1", label: "H1", description: "1 hour" },
                      { id: "H4", label: "H4", description: "4 hours" },
                      { id: "D1", label: "D1", description: "Daily" },
                    ]}
                  />
                </Section>

                <Divider sx={{ borderColor: "rgba(148,163,184,0.06)" }} />

                {/* Section 2: Data Range */}
                <Section title="Data Range" defaultOpen={true}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={useDateRange}
                        onChange={(e) => setUseDateRange(e.target.checked)}
                        size="small"
                      />
                    }
                    label={
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                        {useDateRange ? <Calendar size={14} /> : <BarChart3 size={14} />}
                        <Typography sx={{ fontSize: 13 }}>
                          {useDateRange ? "Date Range" : "Bar Count"}
                        </Typography>
                      </Box>
                    }
                  />

                  <AnimatePresence mode="wait">
                    {useDateRange ? (
                      <motion.div
                        key="dates"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        style={{ display: "flex", flexDirection: "column", gap: 16 }}
                      >
                        <TextField
                          size="small"
                          label="Start Date"
                          type="date"
                          value={dateFrom}
                          onChange={(e) => handleDateFromChange(e.target.value)}
                          slotProps={{ inputLabel: { shrink: true } }}
                          fullWidth
                        />
                        <TextField
                          size="small"
                          label="End Date"
                          type="date"
                          value={dateTo}
                          onChange={(e) => handleDateToChange(e.target.value)}
                          slotProps={{ inputLabel: { shrink: true } }}
                          fullWidth
                        />
                        <FormattedNumberInput
                          size="small"
                          label="Warmup Bars"
                          value={warmupBars}
                          onChange={setWarmupBars}
                          decimals={0}
                          helperText="Indicator pre-calculation (50-500)"
                          fullWidth
                        />
                        {estimate && (
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                              p: 1.5,
                              borderRadius: 2,
                              bgcolor: "rgba(59, 130, 246, 0.06)",
                              border: "1px solid rgba(59, 130, 246, 0.12)",
                            }}
                          >
                            <Info size={14} style={{ color: "#3b82f6", flexShrink: 0 }} />
                            <Typography sx={{ fontSize: 11, color: "#94a3b8" }}>
                              ~{formatNumberWithDots(estimate.estimated_bars, 0)} bars total
                              ({formatNumberWithDots(estimate.warmup_bars, 0)} warmup +{" "}
                              {formatNumberWithDots(estimate.trading_bars, 0)} trading)
                            </Typography>
                          </Box>
                        )}
                      </motion.div>
                    ) : (
                      <motion.div
                        key="bars"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <FormattedNumberInput
                          size="small"
                          label="Bars"
                          value={bars}
                          onChange={setBars}
                          decimals={0}
                          helperText="Min: 100, Max: 50,000 candles"
                          fullWidth
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Section>

                <Divider sx={{ borderColor: "rgba(148,163,184,0.06)" }} />

                {/* Section 3: Risk Configuration */}
                <Section title="Risk Configuration" defaultOpen={false}>
                  <FormattedNumberInput
                    size="small"
                    label="Initial Balance ($)"
                    value={balance}
                    onChange={setBalance}
                    decimals={2}
                    helperText="Minimum: $100"
                    fullWidth
                  />
                  <FormattedNumberInput
                    size="small"
                    label="Risk per Trade (%)"
                    value={risk}
                    onChange={setRisk}
                    decimals={1}
                    helperText="Range: 0.1% - 5.0%"
                    fullWidth
                  />
                </Section>

                {/* Run Button */}
                <Box sx={{ mt: 1 }}>
                  <Button
                    variant="contained"
                    startIcon={
                      loading ? (
                        <CircularProgress size={16} sx={{ color: "inherit" }} />
                      ) : (
                        <Play size={16} />
                      )
                    }
                    onClick={() => handleRun(false)}
                    disabled={loading}
                    fullWidth
                    sx={{
                      py: 1.25,
                      fontSize: 13,
                      fontWeight: 600,
                      bgcolor: compareMode ? "#8b5cf6" : "#3b82f6",
                      "&:hover": {
                        bgcolor: compareMode ? "#7c3aed" : "#2563eb",
                      },
                      borderRadius: 2.5,
                    }}
                  >
                    {loading ? "Running Backtest..." : "Run Backtest"}
                  </Button>
                </Box>

                {/* Compare Mode */}
                {result && (
                  <>
                    <Divider sx={{ borderColor: "rgba(148,163,184,0.06)", mt: 1 }} />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={compareMode}
                          onChange={(e) => {
                            setCompareMode(e.target.checked);
                            if (!e.target.checked) {
                              setResultB(null);
                              setCompareTab(0);
                            }
                          }}
                          size="small"
                        />
                      }
                      label={
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                          <GitCompare size={14} />
                          <Typography sx={{ fontSize: 13 }}>Compare Periods</Typography>
                        </Box>
                      }
                    />

                    {compareMode && (
                      <Button
                        variant="outlined"
                        startIcon={
                          loading ? (
                            <CircularProgress size={16} />
                          ) : (
                            <GitCompare size={16} />
                          )
                        }
                        onClick={() => handleRun(true)}
                        disabled={loading}
                        fullWidth
                        sx={{
                          py: 1,
                          fontSize: 13,
                          borderColor: "rgba(139,92,246,0.3)",
                          color: "#8b5cf6",
                          "&:hover": {
                            borderColor: "#8b5cf6",
                            bgcolor: "rgba(139,92,246,0.06)",
                          },
                          borderRadius: 2.5,
                        }}
                      >
                        {loading ? "Running..." : "Run Period B"}
                      </Button>
                    )}
                  </>
                )}
              </Box>

              {error && (
                <Alert severity="error" sx={{ mt: 2, fontSize: 12 }}>
                  {error}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* ===== RIGHT PANEL: Results ===== */}
        <Grid size={{ xs: 12, md: 8 }}>
          {result ? (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
              {/* Hero Metrics */}
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <HeroMetric
                    label="Net Profit"
                    value={`$${formatNumberWithDots(result.net_profit, 2)}`}
                    subtitle={`from $${formatNumberWithDots(initialBal, 0)} to $${formatNumberWithDots(initialBal + result.net_profit, 0)}`}
                    icon={DollarSign}
                    color={result.net_profit >= 0 ? "#22c55e" : "#ef4444"}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <HeroMetric
                    label="Win Rate"
                    value={`${result.win_rate.toFixed(1)}%`}
                    subtitle={`${result.total_trades} trades executed`}
                    icon={Target}
                    color={result.win_rate >= 50 ? "#22c55e" : "#f59e0b"}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <HeroMetric
                    label="Profit Factor"
                    value={result.profit_factor.toFixed(2)}
                    subtitle={result.profit_factor >= 1.5 ? "Strong edge" : result.profit_factor >= 1.0 ? "Marginal edge" : "Negative edge"}
                    icon={Award}
                    color={result.profit_factor >= 1.5 ? "#22c55e" : result.profit_factor >= 1.0 ? "#f59e0b" : "#ef4444"}
                  />
                </Grid>
              </Grid>

              {/* Strategy info chips */}
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Chip label={result.strategy} size="small" sx={{ bgcolor: "rgba(59,130,246,0.08)", color: "#3b82f6", border: "1px solid rgba(59,130,246,0.15)", fontSize: 11 }} />
                <Chip label={result.symbol} size="small" sx={{ bgcolor: "rgba(139,92,246,0.08)", color: "#8b5cf6", border: "1px solid rgba(139,92,246,0.15)", fontSize: 11 }} />
                <Chip label={result.timeframe} size="small" sx={{ bgcolor: "rgba(148,163,184,0.08)", color: "#94a3b8", border: "1px solid rgba(148,163,184,0.12)", fontSize: 11 }} />
                {dateRangeLabel && (
                  <Chip label={dateRangeLabel} size="small" sx={{ bgcolor: "rgba(148,163,184,0.08)", color: "#94a3b8", border: "1px solid rgba(148,163,184,0.12)", fontSize: 11 }} />
                )}
                {result.warmup_bars > 0 && (
                  <Chip label={`${result.warmup_bars} warmup`} size="small" sx={{ bgcolor: "rgba(148,163,184,0.06)", color: "#64748b", fontSize: 11 }} />
                )}
              </Box>

              {/* Secondary Metrics */}
              <Card>
                <CardContent sx={{ p: 2.5 }}>
                  <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 1.5 }}>
                    Performance Metrics
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <MetricValue label="Sharpe Ratio" value={result.sharpe_ratio.toFixed(2)} color={result.sharpe_ratio > 1 ? "#22c55e" : result.sharpe_ratio > 0 ? "#f59e0b" : "#ef4444"} />
                      <MetricValue label="Sortino Ratio" value={(result.sortino_ratio ?? 0).toFixed(2)} color={(result.sortino_ratio ?? 0) > 1 ? "#22c55e" : "#94a3b8"} />
                      <MetricValue label="Calmar Ratio" value={(result.calmar_ratio ?? 0).toFixed(2)} color={(result.calmar_ratio ?? 0) > 1 ? "#22c55e" : "#94a3b8"} />
                      <MetricValue label="Max Drawdown" value={`${(result.max_drawdown_percent ?? 0).toFixed(2)}%`} color={(result.max_drawdown_percent ?? 0) > 10 ? "#ef4444" : "#f59e0b"} />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <MetricValue label="VaR 95%" value={`$${formatNumberWithDots(result.var_95 ?? 0, 2)}`} color="#ef4444" />
                      <MetricValue label="CVaR 95%" value={`$${formatNumberWithDots(result.cvar_95 ?? 0, 2)}`} color="#ef4444" />
                      <MetricValue label="Avg Win" value={`$${formatNumberWithDots(result.average_win ?? 0, 2)}`} color="#22c55e" />
                      <MetricValue label="Avg Loss" value={`$${formatNumberWithDots(Math.abs(result.average_loss ?? 0), 2)}`} color="#ef4444" />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* BUY/SELL Distribution + Session Analysis */}
              {(result.buy_sell_distribution || result.session_analysis) && (
                <Grid container spacing={2}>
                  {result.buy_sell_distribution && (
                    <Grid size={{ xs: 12, md: 6 }}>
                      <Card sx={{ height: "100%" }}>
                        <CardContent sx={{ p: 2.5 }}>
                          <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 2 }}>
                            BUY/SELL Distribution
                          </Typography>
                          <Box sx={{ display: "flex", gap: 1.5, mb: 2 }}>
                            <Box sx={{ flex: 1 }}>
                              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
                                <ArrowUpRight size={12} style={{ color: "#3b82f6" }} />
                                <Typography sx={{ fontSize: 11, color: "#94a3b8" }}>BUY</Typography>
                              </Box>
                              <Typography sx={{ fontSize: 20, fontWeight: 700, color: "#3b82f6" }}>
                                {result.buy_sell_distribution.buy_count}
                              </Typography>
                              <Typography sx={{ fontSize: 11, color: "#64748b" }}>
                                {result.buy_sell_distribution.buy_pct}%
                              </Typography>
                            </Box>
                            <Box sx={{ flex: 1 }}>
                              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
                                <ArrowDownRight size={12} style={{ color: "#f97316" }} />
                                <Typography sx={{ fontSize: 11, color: "#94a3b8" }}>SELL</Typography>
                              </Box>
                              <Typography sx={{ fontSize: 20, fontWeight: 700, color: "#f97316" }}>
                                {result.buy_sell_distribution.sell_count}
                              </Typography>
                              <Typography sx={{ fontSize: 11, color: "#64748b" }}>
                                {result.buy_sell_distribution.sell_pct}%
                              </Typography>
                            </Box>
                          </Box>
                          {/* Visual bar */}
                          <Box
                            sx={{
                              display: "flex",
                              height: 6,
                              borderRadius: 1,
                              overflow: "hidden",
                              bgcolor: "rgba(148,163,184,0.06)",
                            }}
                          >
                            <Box
                              sx={{
                                width: `${result.buy_sell_distribution.buy_pct}%`,
                                bgcolor: "#3b82f6",
                                borderRadius: "4px 0 0 4px",
                              }}
                            />
                            <Box
                              sx={{
                                width: `${result.buy_sell_distribution.sell_pct}%`,
                                bgcolor: "#f97316",
                                borderRadius: "0 4px 4px 0",
                              }}
                            />
                          </Box>
                          <Typography sx={{ fontSize: 10, color: "#64748b", mt: 1 }}>
                            Ratio: {result.buy_sell_distribution.ratio.toFixed(2)} (target: 0.8-1.2)
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}

                  {result.session_analysis && (
                    <Grid size={{ xs: 12, md: 6 }}>
                      <Card sx={{ height: "100%" }}>
                        <CardContent sx={{ p: 2.5 }}>
                          <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 2 }}>
                            Session Analysis
                          </Typography>
                          {[
                            { name: "London", data: result.session_analysis.london, color: "#3b82f6" },
                            { name: "New York", data: result.session_analysis.ny, color: "#8b5cf6" },
                          ].map((s) => (
                            <Box
                              key={s.name}
                              sx={{
                                p: 1.5,
                                mb: 1,
                                borderRadius: 2,
                                bgcolor: `${s.color}06`,
                                border: `1px solid ${s.color}10`,
                              }}
                            >
                              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                                <Typography sx={{ fontSize: 12, fontWeight: 600, color: s.color }}>
                                  {s.name}
                                </Typography>
                                <Typography
                                  sx={{
                                    fontSize: 12,
                                    fontWeight: 600,
                                    color: s.data.net_profit >= 0 ? "#22c55e" : "#ef4444",
                                  }}
                                >
                                  ${formatNumberWithDots(s.data.net_profit, 2)}
                                </Typography>
                              </Box>
                              <Box sx={{ display: "flex", gap: 2 }}>
                                <Typography sx={{ fontSize: 10, color: "#94a3b8" }}>
                                  {s.data.trades} trades
                                </Typography>
                                <Typography sx={{ fontSize: 10, color: "#94a3b8" }}>
                                  WR: {s.data.win_rate.toFixed(1)}%
                                </Typography>
                                <Typography sx={{ fontSize: 10, color: "#94a3b8" }}>
                                  PF: {s.data.profit_factor.toFixed(2)}
                                </Typography>
                              </Box>
                            </Box>
                          ))}
                        </CardContent>
                      </Card>
                    </Grid>
                  )}
                </Grid>
              )}

              {/* Compare Mode with Tabs */}
              {compareMode && resultB && (
                <Card>
                  <CardContent sx={{ p: 2.5 }}>
                    <Tabs
                      value={compareTab}
                      onChange={(_, v) => setCompareTab(v)}
                      sx={{
                        mb: 2,
                        minHeight: 36,
                        "& .MuiTab-root": { fontSize: 12, minHeight: 36, py: 0.5 },
                      }}
                    >
                      <Tab label="Period A" />
                      <Tab label="Period B" />
                      <Tab label="Comparison" />
                    </Tabs>

                    {compareTab === 2 ? (
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell sx={{ fontWeight: 600, fontSize: 11 }}>Metric</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600, fontSize: 11 }}>Period A</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600, fontSize: 11 }}>Period B</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600, fontSize: 11 }}>Delta</TableCell>
                          </TableRow>
                          {[
                            { label: "Trades", a: result.total_trades, b: resultB.total_trades, fmt: (v: number) => v.toString() },
                            { label: "Win Rate", a: result.win_rate, b: resultB.win_rate, fmt: (v: number) => `${v.toFixed(1)}%` },
                            { label: "Net Profit", a: result.net_profit, b: resultB.net_profit, fmt: (v: number) => `$${formatNumberWithDots(v, 2)}` },
                            { label: "Profit Factor", a: result.profit_factor, b: resultB.profit_factor, fmt: (v: number) => v.toFixed(2) },
                            { label: "Sharpe", a: result.sharpe_ratio, b: resultB.sharpe_ratio, fmt: (v: number) => v.toFixed(2) },
                            { label: "Sortino", a: result.sortino_ratio ?? 0, b: resultB.sortino_ratio ?? 0, fmt: (v: number) => v.toFixed(2) },
                            { label: "Max DD", a: result.max_drawdown_percent ?? 0, b: resultB.max_drawdown_percent ?? 0, fmt: (v: number) => `${v.toFixed(2)}%` },
                          ].map((row) => {
                            const delta = row.b - row.a;
                            const isPositive = row.label === "Max DD" ? delta < 0 : delta > 0;
                            return (
                              <TableRow key={row.label}>
                                <TableCell sx={{ fontSize: 12 }}>{row.label}</TableCell>
                                <TableCell align="right" sx={{ fontSize: 12 }}>{row.fmt(row.a)}</TableCell>
                                <TableCell align="right" sx={{ fontSize: 12 }}>{row.fmt(row.b)}</TableCell>
                                <TableCell
                                  align="right"
                                  sx={{
                                    fontSize: 12,
                                    fontWeight: 600,
                                    color: isPositive ? "#22c55e" : delta === 0 ? "#64748b" : "#ef4444",
                                  }}
                                >
                                  {isPositive && delta > 0 ? "+" : ""}
                                  {row.fmt(delta)}
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    ) : (
                      <Box>
                        {(() => {
                          const r = compareTab === 0 ? result : resultB;
                          return (
                            <Grid container spacing={2}>
                              <Grid size={{ xs: 6 }}>
                                <MetricValue label="Trades" value={r.total_trades.toString()} />
                                <MetricValue label="Win Rate" value={`${r.win_rate.toFixed(1)}%`} />
                                <MetricValue label="Net Profit" value={`$${formatNumberWithDots(r.net_profit, 2)}`} color={r.net_profit >= 0 ? "#22c55e" : "#ef4444"} />
                                <MetricValue label="Profit Factor" value={r.profit_factor.toFixed(2)} />
                              </Grid>
                              <Grid size={{ xs: 6 }}>
                                <MetricValue label="Sharpe" value={r.sharpe_ratio.toFixed(2)} />
                                <MetricValue label="Sortino" value={(r.sortino_ratio ?? 0).toFixed(2)} />
                                <MetricValue label="Calmar" value={(r.calmar_ratio ?? 0).toFixed(2)} />
                                <MetricValue label="Max DD" value={`${(r.max_drawdown_percent ?? 0).toFixed(2)}%`} color="#f59e0b" />
                              </Grid>
                            </Grid>
                          );
                        })()}
                      </Box>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Equity Chart */}
              {equityData.length > 0 && (
                <EquityChart
                  data={equityData}
                  title="Equity Curve"
                  dateRange={
                    dateRangeLabel
                      ? { from: result.date_from?.split("T")[0] ?? "", to: result.date_to?.split("T")[0] ?? "" }
                      : undefined
                  }
                  timeframe={result.timeframe}
                />
              )}

              {/* Trade Audit */}
              {result.trades && result.trades.length > 0 && (
                <TradeAuditCarousel
                  trades={result.trades}
                  symbol={result.symbol}
                  timeframe={result.timeframe}
                />
              )}
            </Box>
          ) : (
            /* Empty state */
            <Card sx={{ height: "100%", minHeight: 400 }}>
              <CardContent
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  py: 8,
                }}
              >
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 3,
                    bgcolor: "rgba(59, 130, 246, 0.06)",
                    border: "1px solid rgba(59, 130, 246, 0.1)",
                    mb: 2,
                  }}
                >
                  <BarChart3 size={32} style={{ color: "#3b82f6" }} />
                </Box>
                <Typography
                  sx={{ fontSize: 15, fontWeight: 600, color: "text.primary", mb: 0.5 }}
                >
                  No Backtest Results
                </Typography>
                <Typography
                  sx={{ fontSize: 12, color: "#64748b", textAlign: "center", maxWidth: 280 }}
                >
                  Configure your strategy, symbol, and timeframe, then run a backtest to see performance metrics
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          variant="filled"
          sx={{ fontSize: 12 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
