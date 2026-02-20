"use client";

import { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  LinearProgress,
  Typography,
  Chip,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import StatCard from "@/components/common/StatCard";
import { Shield, AlertTriangle, Ban, TrendingDown } from "lucide-react";
import api from "@/lib/api";

interface RiskStatus {
  kill_switch_active: boolean;
  circuit_breaker: {
    drawdown_breached: boolean;
    daily_loss_breached: boolean;
    overtrading_breached: boolean;
    current_drawdown: number;
    max_drawdown_limit: number;
    daily_loss: number;
    max_daily_loss: number;
    trades_this_hour: number;
    max_trades_per_hour: number;
  };
  trading_allowed: boolean;
}

export default function RiskPage() {
  const [status, setStatus] = useState<RiskStatus | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const { data } = await api.get("/bot/status");
        if (data.risk_status) setStatus(data.risk_status);
      } catch {
        // Use defaults
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const cb = status?.circuit_breaker;
  const drawdownPct = cb ? (cb.current_drawdown / cb.max_drawdown_limit) * 100 : 0;
  const dailyLossPct = cb ? (cb.daily_loss / cb.max_daily_loss) * 100 : 0;
  const tradingPct = cb ? (cb.trades_this_hour / cb.max_trades_per_hour) * 100 : 0;

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4">Risk Management</Typography>
        <Chip
          label={status?.trading_allowed ? "Trading Allowed" : "Trading Blocked"}
          color={status?.trading_allowed ? "success" : "error"}
        />
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Kill Switch"
            value={status?.kill_switch_active ? "ACTIVE" : "Inactive"}
            icon={Ban}
            color={status?.kill_switch_active ? "#ef4444" : "#22c55e"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Drawdown"
            value={cb ? `${cb.current_drawdown.toFixed(1)}%` : "0%"}
            subtitle={cb ? `Limit: ${cb.max_drawdown_limit}%` : ""}
            icon={TrendingDown}
            color={cb?.drawdown_breached ? "#ef4444" : "#f59e0b"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Daily Loss"
            value={cb ? `$${cb.daily_loss.toFixed(2)}` : "$0"}
            subtitle={cb ? `Limit: $${cb.max_daily_loss.toFixed(2)}` : ""}
            icon={AlertTriangle}
            color={cb?.daily_loss_breached ? "#ef4444" : "#3b82f6"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Trades/Hour"
            value={cb ? `${cb.trades_this_hour}` : "0"}
            subtitle={cb ? `Limit: ${cb.max_trades_per_hour}` : ""}
            icon={Shield}
            color={cb?.overtrading_breached ? "#ef4444" : "#8b5cf6"}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Drawdown</Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(drawdownPct, 100)}
                color={drawdownPct > 80 ? "error" : drawdownPct > 50 ? "warning" : "primary"}
                sx={{ height: 10, borderRadius: 5, mb: 1 }}
              />
              <Typography variant="caption" color="text.secondary">
                {drawdownPct.toFixed(1)}% of limit used
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Daily Loss</Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(dailyLossPct, 100)}
                color={dailyLossPct > 80 ? "error" : dailyLossPct > 50 ? "warning" : "primary"}
                sx={{ height: 10, borderRadius: 5, mb: 1 }}
              />
              <Typography variant="caption" color="text.secondary">
                {dailyLossPct.toFixed(1)}% of limit used
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Overtrading</Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(tradingPct, 100)}
                color={tradingPct > 80 ? "error" : tradingPct > 50 ? "warning" : "primary"}
                sx={{ height: 10, borderRadius: 5, mb: 1 }}
              />
              <Typography variant="caption" color="text.secondary">
                {tradingPct.toFixed(1)}% of limit used
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
