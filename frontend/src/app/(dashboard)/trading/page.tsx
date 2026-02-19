"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, Typography } from "@mui/material";
import Grid from "@mui/material/Grid";
import TradingViewWidget from "@/components/charts/TradingViewWidget";
import TradePanel from "@/components/trading/TradePanel";
import AccountOverview from "@/components/trading/AccountOverview";
import PositionsTable from "@/components/trading/PositionsTable";
import StatCard from "@/components/common/StatCard";
import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import api from "@/lib/api";
import { useAppStore } from "@/store";
import type { Position, PerformanceMetrics } from "@/types";

export default function TradingPage() {
  const { positions, setPositions, setBotStatus, activeSymbol } = useAppStore();
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);

  // Map symbol to TradingView format
  const getTradingViewSymbol = (symbol: string) => {
    if (symbol === "EURUSD") return "FX:EURUSD";
    if (symbol === "XAUUSD") return "TVC:GOLD";
    return "FX:EURUSD"; // fallback
  };

  const fetchData = useCallback(async () => {
    try {
      const [posRes, statusRes, metricsRes] = await Promise.allSettled([
        api.get<Position[]>("/orders/open"),
        api.get("/bot/status"),
        api.get("/metrics/performance"),
      ]);
      if (posRes.status === "fulfilled") setPositions(posRes.value.data);
      if (statusRes.status === "fulfilled") setBotStatus(statusRes.value.data);
      if (metricsRes.status === "fulfilled") setMetrics(metricsRes.value.data);
    } catch {
      // Silent fail on initial load
    }
  }, [setPositions, setBotStatus]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Live Trading
      </Typography>

      <AccountOverview />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Net Profit"
            value={metrics ? `$${(metrics.net_profit ?? 0).toFixed(2)}` : "$0.00"}
            icon={TrendingUpIcon}
            color="#22c55e"
            trend={metrics && metrics.net_profit >= 0 ? "up" : "down"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Win Rate"
            value={metrics ? `${(metrics.win_rate ?? 0).toFixed(1)}%` : "0%"}
            icon={ShowChartIcon}
            color="#3b82f6"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Open Positions"
            value={metrics?.open_positions ?? positions.length}
            icon={AccountBalanceIcon}
            color="#8b5cf6"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Max Drawdown"
            value={metrics ? `$${(metrics.max_drawdown ?? 0).toFixed(2)}` : "$0.00"}
            icon={WarningAmberIcon}
            color="#f59e0b"
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 8.4 }}>
          <TradingViewWidget symbol={getTradingViewSymbol(activeSymbol)} height={800} />
        </Grid>
        <Grid size={{ xs: 12, md: 3.6 }}>
          <TradePanel />
        </Grid>
      </Grid>

      <Box sx={{ mt: 2 }}>
        <PositionsTable positions={positions} onRefresh={fetchData} />
      </Box>
    </Box>
  );
}
