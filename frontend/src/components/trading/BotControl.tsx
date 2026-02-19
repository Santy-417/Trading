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

interface BotControlProps {
  embedded?: boolean;
}

export default function BotControl({ embedded = false }: BotControlProps) {
  const { botStatus, setBotStatus, activeSymbol, setActiveSymbol } = useAppStore();
  const [strategy, setStrategy] = useState("fibonacci");
  const [timeframe, setTimeframe] = useState("H1");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isRunning = botStatus?.state === "running";
  const killSwitchActive = botStatus?.risk?.kill_switch_active === true;

  const handleResetKill = async () => {
    setLoading(true);
    setError("");
    try {
      await api.post("/bot/reset-kill", {});
      // Refresh bot status
      const { data } = await api.get("/bot/status");
      setBotStatus(data);
    } catch {
      setError("Failed to reset kill switch");
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/bot/start", {
        strategy,
        symbols: [activeSymbol],
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

  const content = (
    <>
      {!embedded && (
        <Typography variant="h6" sx={{ mb: 2 }}>
          Bot Control
        </Typography>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {killSwitchActive && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={handleResetKill} disabled={loading}>
              Reset
            </Button>
          }
        >
          Kill switch is active. Reset to trade.
        </Alert>
      )}

      {isRunning ? (
        <Box>
          <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
            <Chip label={`Strategy: ${botStatus.strategy}`} color="primary" size="small" />
            <Chip label={`Symbols: ${botStatus.symbols?.join(", ")}`} size="small" />
            <Chip label={`TF: ${botStatus.timeframe}`} size="small" />
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
              <Select value={activeSymbol} label="Symbol" onChange={(e) => setActiveSymbol(e.target.value)}>
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
    </>
  );

  if (embedded) return content;

  return (
    <Card>
      <CardContent>{content}</CardContent>
    </Card>
  );
}
