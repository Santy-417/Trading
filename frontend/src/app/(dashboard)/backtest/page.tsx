"use client";

import { useState } from "react";
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
} from "@mui/material";
import { SelectDropdown } from "@/components/ui/select-dropdown";
import Grid from "@mui/material/Grid";
import { Play } from "lucide-react";
import EquityChart from "@/components/charts/EquityChart";
import api from "@/lib/api";
import type { BacktestResult } from "@/types";
import { formatNumberWithDots } from "@/lib/numberFormat";
import { FormattedNumberInput } from "@/components/ui/formatted-number-input";

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
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error" | "warning";
  }>({ open: false, message: "", severity: "success" });

  const handleRun = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { data } = await api.post<BacktestResult>("/backtest/run", {
        strategy,
        symbol,
        timeframe,
        bars: parseInt(bars) || 5000,
        initial_balance: parseFloat(balance) || 10000,
        risk_per_trade: parseFloat(risk) || 1.0,
      });

      // Check if result has trades
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

      setResult(data);
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

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Backtesting
      </Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Configuration
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <SelectDropdown
                  label="Strategy"
                  value={strategy}
                  onValueChange={setStrategy}
                  options={[
                    { id: "fibonacci", label: "Fibonacci", description: "Fibonacci retracement/extension" },
                    { id: "ict", label: "ICT", description: "Order blocks, FVG, liquidity" },
                    { id: "hybrid_ml", label: "Hybrid ML", description: "Rules + XGBoost ML combined" },
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
                <FormattedNumberInput
                  size="small"
                  label="Bars"
                  value={bars}
                  onChange={setBars}
                  decimals={0}
                  helperText="Number of historical candles to backtest"
                  fullWidth
                />
                <FormattedNumberInput
                  size="small"
                  label="Initial Balance ($)"
                  value={balance}
                  onChange={setBalance}
                  decimals={2}
                  helperText="Starting account balance"
                  fullWidth
                />
                <FormattedNumberInput
                  size="small"
                  label="Risk per Trade (%)"
                  value={risk}
                  onChange={setRisk}
                  decimals={1}
                  helperText="Risk percentage per trade (0.1 - 10)"
                  fullWidth
                />
                <Button
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={18} /> : <Play size={18} />}
                  onClick={handleRun}
                  disabled={loading}
                  fullWidth
                >
                  {loading ? "Running..." : "Run Backtest"}
                </Button>
              </Box>
              {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          {result ? (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <Card>
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                    <Typography variant="h6">Results</Typography>
                    <Box sx={{ display: "flex", gap: 1 }}>
                      <Chip label={result.strategy} color="primary" size="small" />
                      <Chip label={result.symbol} size="small" />
                      <Chip label={result.timeframe} size="small" />
                    </Box>
                  </Box>
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 6 }}>
                      <Table size="small">
                        <TableBody>
                          <TableRow><TableCell>Total Trades</TableCell><TableCell align="right"><strong>{result.total_trades}</strong></TableCell></TableRow>
                          <TableRow><TableCell>Win Rate</TableCell><TableCell align="right"><strong>{result.win_rate.toFixed(1)}%</strong></TableCell></TableRow>
                          <TableRow><TableCell>Net Profit</TableCell><TableCell align="right" sx={{ color: result.net_profit >= 0 ? "success.main" : "error.main" }}><strong>${formatNumberWithDots(result.net_profit, 2)}</strong></TableCell></TableRow>
                          <TableRow><TableCell>Profit Factor</TableCell><TableCell align="right"><strong>{result.profit_factor.toFixed(2)}</strong></TableCell></TableRow>
                          <TableRow><TableCell>Sharpe Ratio</TableCell><TableCell align="right"><strong>{result.sharpe_ratio.toFixed(2)}</strong></TableCell></TableRow>
                          <TableRow><TableCell>Max Drawdown</TableCell><TableCell align="right"><strong>{(result.max_drawdown_percent ?? 0).toFixed(2)}%</strong></TableCell></TableRow>
                        </TableBody>
                      </Table>
                    </Grid>
                    <Grid size={{ xs: 6 }}>
                      <Table size="small">
                        <TableBody>
                          <TableRow><TableCell>Return</TableCell><TableCell align="right"><strong>{result.return_percent.toFixed(2)}%</strong></TableCell></TableRow>
                          <TableRow><TableCell>Avg Win</TableCell><TableCell align="right" sx={{ color: "success.main" }}>${formatNumberWithDots(result.average_win ?? 0, 2)}</TableCell></TableRow>
                          <TableRow><TableCell>Avg Loss</TableCell><TableCell align="right" sx={{ color: "error.main" }}>${formatNumberWithDots(Math.abs(result.average_loss ?? 0), 2)}</TableCell></TableRow>
                          <TableRow><TableCell>Max Consecutive Wins</TableCell><TableCell align="right">{result.max_consecutive_wins}</TableCell></TableRow>
                          <TableRow><TableCell>Max Consecutive Losses</TableCell><TableCell align="right">{result.max_consecutive_losses}</TableCell></TableRow>
                          <TableRow><TableCell>Expectancy</TableCell><TableCell align="right"><strong>${result.expectancy.toFixed(2)}</strong></TableCell></TableRow>
                        </TableBody>
                      </Table>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
              {equityData.length > 0 && <EquityChart data={equityData} />}
            </Box>
          ) : (
            <Card>
              <CardContent sx={{ textAlign: "center", py: 8 }}>
                <Typography variant="h6" color="text.secondary">
                  Configure and run a backtest to see results
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
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
