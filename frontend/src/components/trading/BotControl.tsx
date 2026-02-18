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
  Typography,
  Alert,
  Chip,
  Stack,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopIcon from "@mui/icons-material/Stop";
import ReportProblemIcon from "@mui/icons-material/ReportProblem";
import api from "@/lib/api";
import { useAppStore } from "@/store";

const STRATEGIES = ["fibonacci", "ict", "hybrid_ml"];
const SYMBOLS = ["EURUSD", "XAUUSD"];
const TIMEFRAMES = ["M5", "M15", "H1", "H4", "D1"];

export default function BotControl() {
  const { botStatus, setBotStatus } = useAppStore();
  const [strategy, setStrategy] = useState("fibonacci");
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isRunning = botStatus?.state === "running";

  const handleStart = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/bot/start", {
        strategy,
        symbols: [symbol],
        timeframe,
        risk_per_trade: 1.0,
        lot_mode: "percent_risk",
      });
      setBotStatus(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start bot";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/bot/stop", {});
      setBotStatus(data);
    } catch {
      setError("Failed to stop bot");
    } finally {
      setLoading(false);
    }
  };

  const handleKill = async () => {
    if (!confirm("KILL SWITCH: This will close ALL open positions. Continue?")) return;
    setLoading(true);
    try {
      await api.post("/bot/kill", { close_positions: true });
      setBotStatus(null);
    } catch {
      setError("Failed to activate kill switch");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Bot Control
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
            {error}
          </Alert>
        )}

        {isRunning ? (
          <Box>
            <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
              <Chip label={`Strategy: ${botStatus.strategy}`} color="primary" />
              <Chip label={`Symbols: ${botStatus.symbols?.join(", ")}`} />
              <Chip label={`TF: ${botStatus.timeframe}`} />
            </Stack>
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                color="warning"
                startIcon={<StopIcon />}
                onClick={handleStop}
                disabled={loading}
              >
                Stop Bot
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<ReportProblemIcon />}
                onClick={handleKill}
                disabled={loading}
              >
                Kill Switch
              </Button>
            </Stack>
          </Box>
        ) : (
          <Box>
            <Stack spacing={2} sx={{ mb: 2 }}>
              <FormControl size="small" fullWidth>
                <InputLabel>Strategy</InputLabel>
                <Select value={strategy} label="Strategy" onChange={(e) => setStrategy(e.target.value)}>
                  {STRATEGIES.map((s) => (
                    <MenuItem key={s} value={s}>{s}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" fullWidth>
                <InputLabel>Symbol</InputLabel>
                <Select value={symbol} label="Symbol" onChange={(e) => setSymbol(e.target.value)}>
                  {SYMBOLS.map((s) => (
                    <MenuItem key={s} value={s}>{s}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" fullWidth>
                <InputLabel>Timeframe</InputLabel>
                <Select value={timeframe} label="Timeframe" onChange={(e) => setTimeframe(e.target.value)}>
                  {TIMEFRAMES.map((tf) => (
                    <MenuItem key={tf} value={tf}>{tf}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
            <Button
              variant="contained"
              color="success"
              startIcon={<PlayArrowIcon />}
              onClick={handleStart}
              disabled={loading}
              fullWidth
            >
              Start Bot
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
