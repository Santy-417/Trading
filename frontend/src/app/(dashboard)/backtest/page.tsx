"use client";

import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Chip,
  CircularProgress,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import EquityChart from "@/components/charts/EquityChart";
import api from "@/lib/api";
import type { BacktestResult } from "@/types";

export default function BacktestPage() {
  const [strategy, setStrategy] = useState("fibonacci");
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [bars, setBars] = useState(5000);
  const [balance, setBalance] = useState(10000);
  const [risk, setRisk] = useState(1.0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState("");

  const handleRun = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post<BacktestResult>("/backtest/run", {
        strategy,
        symbol,
        timeframe,
        bars,
        initial_balance: balance,
        risk_per_trade: risk,
      });
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Backtest failed");
    } finally {
      setLoading(false);
    }
  };

  const equityData = result?.equity_curve.map((eq, i) => ({
    date: `T${i}`,
    equity: eq,
  })) ?? [];

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
                <FormControl size="small" fullWidth>
                  <InputLabel>Strategy</InputLabel>
                  <Select value={strategy} label="Strategy" onChange={(e) => setStrategy(e.target.value)}>
                    {["fibonacci", "ict", "hybrid_ml"].map((s) => (
                      <MenuItem key={s} value={s}>{s}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel>Symbol</InputLabel>
                  <Select value={symbol} label="Symbol" onChange={(e) => setSymbol(e.target.value)}>
                    {["EURUSD", "XAUUSD"].map((s) => (
                      <MenuItem key={s} value={s}>{s}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel>Timeframe</InputLabel>
                  <Select value={timeframe} label="Timeframe" onChange={(e) => setTimeframe(e.target.value)}>
                    {["M5", "M15", "H1", "H4", "D1"].map((tf) => (
                      <MenuItem key={tf} value={tf}>{tf}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  size="small"
                  label="Bars"
                  type="number"
                  value={bars}
                  onChange={(e) => setBars(Number(e.target.value))}
                />
                <TextField
                  size="small"
                  label="Initial Balance ($)"
                  type="number"
                  value={balance}
                  onChange={(e) => setBalance(Number(e.target.value))}
                />
                <TextField
                  size="small"
                  label="Risk per Trade (%)"
                  type="number"
                  value={risk}
                  onChange={(e) => setRisk(Number(e.target.value))}
                  inputProps={{ step: 0.5, min: 0.1, max: 10 }}
                />
                <Button
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={18} /> : <PlayArrowIcon />}
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
                          <TableRow><TableCell>Net Profit</TableCell><TableCell align="right" sx={{ color: result.net_profit >= 0 ? "success.main" : "error.main" }}><strong>${result.net_profit.toFixed(2)}</strong></TableCell></TableRow>
                          <TableRow><TableCell>Profit Factor</TableCell><TableCell align="right"><strong>{result.profit_factor.toFixed(2)}</strong></TableCell></TableRow>
                          <TableRow><TableCell>Sharpe Ratio</TableCell><TableCell align="right"><strong>{result.sharpe_ratio.toFixed(2)}</strong></TableCell></TableRow>
                          <TableRow><TableCell>Max Drawdown</TableCell><TableCell align="right"><strong>{result.max_drawdown.toFixed(2)}%</strong></TableCell></TableRow>
                        </TableBody>
                      </Table>
                    </Grid>
                    <Grid size={{ xs: 6 }}>
                      <Table size="small">
                        <TableBody>
                          <TableRow><TableCell>Return</TableCell><TableCell align="right"><strong>{result.return_percent.toFixed(2)}%</strong></TableCell></TableRow>
                          <TableRow><TableCell>Avg Win</TableCell><TableCell align="right" sx={{ color: "success.main" }}>${result.avg_win.toFixed(2)}</TableCell></TableRow>
                          <TableRow><TableCell>Avg Loss</TableCell><TableCell align="right" sx={{ color: "error.main" }}>${result.avg_loss.toFixed(2)}</TableCell></TableRow>
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
    </Box>
  );
}
