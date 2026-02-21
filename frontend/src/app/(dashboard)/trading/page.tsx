"use client";

import { useCallback, useEffect } from "react";
import { Box, Typography } from "@mui/material";
import Grid from "@mui/material/Grid";
import TradingViewWidget from "@/components/charts/TradingViewWidget";
import TradePanel from "@/components/trading/TradePanel";
import AccountOverview from "@/components/trading/AccountOverview";
import PositionsTable from "@/components/trading/PositionsTable";
import StatCard from "@/components/common/StatCard";
import { TrendingUp, Activity, Layers, AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import { useAppStore } from "@/store";
import type { AccountInfo, PendingOrder, Position } from "@/types";

export default function TradingPage() {
  const { positions, setPositions, setBotStatus, activeSymbol, accountInfo, setAccountInfo, setPendingOrders, pendingOrders } = useAppStore();

  // Map symbol to TradingView format
  const getTradingViewSymbol = (symbol: string) => {
    const mapping: Record<string, string> = {
      "EURUSD": "FX:EURUSD",
      "XAUUSD": "TVC:GOLD",
      "DXY": "TVC:DXY",
      "USDCAD": "FX:USDCAD",
      "GBPUSD": "FX:GBPUSD",
      "AUDCAD": "FX:AUDCAD",
      "EURJPY": "FX:EURJPY",
      "USDJPY": "FX:USDJPY",
      "EURGBP": "FX:EURGBP",
    };
    return mapping[symbol] || "FX:EURUSD"; // fallback
  };

  const fetchData = useCallback(async () => {
    try {
      const [posRes, statusRes, accountRes, pendingRes] = await Promise.allSettled([
        api.get<Position[]>("/orders/open"),
        api.get("/bot/status"),
        api.get<AccountInfo>("/bot/account"),
        api.get<PendingOrder[]>("/orders/pending"),
      ]);
      if (posRes.status === "fulfilled") setPositions(posRes.value.data);
      if (statusRes.status === "fulfilled") setBotStatus(statusRes.value.data);
      if (accountRes.status === "fulfilled") setAccountInfo(accountRes.value.data);
      if (pendingRes.status === "fulfilled") setPendingOrders(pendingRes.value.data);
    } catch {
      // Silent fail on initial load
    }
  }, [setPositions, setBotStatus, setAccountInfo, setPendingOrders]);

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

      {(() => {
        // Derive all stat values from accountInfo (single source of truth)
        const netProfit = accountInfo?.profit ?? 0;
        // Drawdown = unrealized loss (profit when negative), 0 when positive
        const maxDrawdown = accountInfo ? Math.max(0, -accountInfo.profit) : 0;
        return (
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <StatCard
                title="Net Profit"
                value={`$${netProfit.toFixed(2)}`}
                icon={TrendingUp}
                color={netProfit >= 0 ? "#22c55e" : "#ef4444"}
                trend={netProfit >= 0 ? "up" : "down"}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <StatCard
                title="Win Rate"
                value="--"
                icon={Activity}
                color="#3b82f6"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <StatCard
                title="Open Positions"
                value={positions.length}
                icon={Layers}
                color="#8b5cf6"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <StatCard
                title="Max Drawdown"
                value={`$${maxDrawdown.toFixed(2)}`}
                icon={AlertTriangle}
                color={maxDrawdown > 0 ? "#ef4444" : "#f59e0b"}
              />
            </Grid>
          </Grid>
        );
      })()}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 8.4 }}>
          <TradingViewWidget symbol={getTradingViewSymbol(activeSymbol)} height="calc(100vh - 170px)" />
        </Grid>
        <Grid size={{ xs: 12, md: 3.6 }}>
          <TradePanel />
        </Grid>
      </Grid>

      <Box sx={{ mt: 2 }}>
        <PositionsTable positions={positions} onRefresh={fetchData} pendingOrders={pendingOrders} />
      </Box>
    </Box>
  );
}
