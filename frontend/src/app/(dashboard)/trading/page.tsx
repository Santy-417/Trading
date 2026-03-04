"use client";

import { useCallback, useEffect } from "react";
import { Box, Typography, Chip } from "@mui/material";
import Grid from "@mui/material/Grid";
import TradingViewWidget from "@/components/charts/TradingViewWidget";
import TradePanel from "@/components/trading/TradePanel";
import AccountOverview from "@/components/trading/AccountOverview";
import PositionsTable from "@/components/trading/PositionsTable";
import StatCard from "@/components/common/StatCard";
import {
  TrendingUp,
  Activity,
  Layers,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import api from "@/lib/api";
import { useAppStore } from "@/store";
import type { AccountInfo, PendingOrder, Position } from "@/types";

const SYMBOL_DISPLAY: Record<string, { label: string; flag: string }> = {
  EURUSD: { label: "EUR/USD", flag: "EU" },
  XAUUSD: { label: "XAU/USD", flag: "Au" },
  DXY: { label: "DXY", flag: "US" },
  USDCAD: { label: "USD/CAD", flag: "CA" },
  GBPUSD: { label: "GBP/USD", flag: "GB" },
  AUDCAD: { label: "AUD/CAD", flag: "AC" },
  EURJPY: { label: "EUR/JPY", flag: "JP" },
  USDJPY: { label: "USD/JPY", flag: "JP" },
  EURGBP: { label: "EUR/GBP", flag: "GB" },
};

export default function TradingPage() {
  const {
    positions,
    setPositions,
    setBotStatus,
    activeSymbol,
    accountInfo,
    setAccountInfo,
    setPendingOrders,
    pendingOrders,
  } = useAppStore();

  const getTradingViewSymbol = (symbol: string) => {
    const mapping: Record<string, string> = {
      EURUSD: "FX:EURUSD",
      XAUUSD: "TVC:GOLD",
      DXY: "TVC:DXY",
      USDCAD: "FX:USDCAD",
      GBPUSD: "FX:GBPUSD",
      AUDCAD: "FX:AUDCAD",
      EURJPY: "FX:EURJPY",
      USDJPY: "FX:USDJPY",
      EURGBP: "FX:EURGBP",
    };
    return mapping[symbol] || "FX:EURUSD";
  };

  const fetchData = useCallback(async () => {
    try {
      const [posRes, statusRes, accountRes, pendingRes] =
        await Promise.allSettled([
          api.get<Position[]>("/orders/open"),
          api.get("/bot/status"),
          api.get<AccountInfo>("/bot/account"),
          api.get<PendingOrder[]>("/orders/pending"),
        ]);
      if (posRes.status === "fulfilled") setPositions(posRes.value.data);
      if (statusRes.status === "fulfilled") setBotStatus(statusRes.value.data);
      if (accountRes.status === "fulfilled")
        setAccountInfo(accountRes.value.data);
      if (pendingRes.status === "fulfilled")
        setPendingOrders(pendingRes.value.data);
    } catch {
      // Silent fail on polling
    }
  }, [setPositions, setBotStatus, setAccountInfo, setPendingOrders]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const netProfit = accountInfo?.profit ?? 0;
  const maxDrawdown = accountInfo ? Math.max(0, -accountInfo.profit) : 0;
  const symbolInfo = SYMBOL_DISPLAY[activeSymbol] || {
    label: activeSymbol,
    flag: "--",
  };

  return (
    <Box>
      {/* Page header with symbol context */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mb: 2.5,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 2,
              bgcolor: "rgba(124, 58, 237, 0.1)",
              border: "1px solid rgba(124, 58, 237, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 12,
              color: "#7c3aed",
              letterSpacing: "-0.02em",
            }}
          >
            {symbolInfo.flag}
          </Box>
          <Box>
            <Typography
              variant="h5"
              sx={{ fontWeight: 700, lineHeight: 1.2, fontSize: 20 }}
            >
              {symbolInfo.label}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.25 }}>
              <Typography
                variant="caption"
                sx={{ color: "#64748b", fontSize: 11 }}
              >
                Live Trading
              </Typography>
              {accountInfo && (
                <Chip
                  icon={
                    netProfit >= 0 ? (
                      <ArrowUpRight
                        size={10}
                        style={{ color: "#22c55e" }}
                      />
                    ) : (
                      <ArrowDownRight
                        size={10}
                        style={{ color: "#ef4444" }}
                      />
                    )
                  }
                  label={`${netProfit >= 0 ? "+" : ""}$${netProfit.toFixed(2)}`}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: 10,
                    fontWeight: 600,
                    bgcolor:
                      netProfit >= 0
                        ? "rgba(34,197,94,0.08)"
                        : "rgba(239,68,68,0.08)",
                    color: netProfit >= 0 ? "#22c55e" : "#ef4444",
                    border: `1px solid ${netProfit >= 0 ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}`,
                    "& .MuiChip-icon": { ml: 0.3 },
                  }}
                />
              )}
            </Box>
          </Box>
        </Box>
      </Box>

      <AccountOverview />

      {/* Stat cards */}
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
            subtitle="No closed trades yet"
            icon={Activity}
            color="#7c3aed"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Open Positions"
            value={positions.length}
            subtitle={
              positions.length > 0
                ? `${positions.length} active trade${positions.length > 1 ? "s" : ""}`
                : "No open trades"
            }
            icon={Layers}
            color="#8b5cf6"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Unrealized P&L"
            value={`$${maxDrawdown.toFixed(2)}`}
            icon={AlertTriangle}
            color={maxDrawdown > 0 ? "#ef4444" : "#64748b"}
            trend={maxDrawdown > 0 ? "down" : "neutral"}
          />
        </Grid>
      </Grid>

      {/* Chart + Trade Panel */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 8.4 }}>
          <TradingViewWidget
            symbol={getTradingViewSymbol(activeSymbol)}
            height="calc(100vh - 170px)"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 3.6 }}>
          <TradePanel />
        </Grid>
      </Grid>

      {/* Positions */}
      <Box sx={{ mt: 2 }}>
        <PositionsTable
          positions={positions}
          onRefresh={fetchData}
          pendingOrders={pendingOrders}
        />
      </Box>
    </Box>
  );
}
