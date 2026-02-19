"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, Typography } from "@mui/material";
import api from "@/lib/api";
import type { AccountInfo } from "@/types";

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Box sx={{ textAlign: "center", px: 2 }}>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.7rem", textTransform: "uppercase" }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: "monospace", color: color || "text.primary" }}>
        {value}
      </Typography>
    </Box>
  );
}

export default function AccountOverview() {
  const [account, setAccount] = useState<AccountInfo | null>(null);

  const fetchAccount = useCallback(async () => {
    try {
      const { data } = await api.get<AccountInfo>("/bot/account");
      setAccount(data);
    } catch {
      // MT5 may not be connected
    }
  }, []);

  useEffect(() => {
    fetchAccount();
    const interval = setInterval(fetchAccount, 1000);
    return () => clearInterval(interval);
  }, [fetchAccount]);

  if (!account) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "background.paper", borderRadius: 1, p: 1.5, mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Connecting to MT5...
        </Typography>
      </Box>
    );
  }

  const profitColor = account.profit >= 0 ? "#22c55e" : "#ef4444";

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexWrap: "wrap",
        gap: 1,
        bgcolor: "background.paper",
        borderRadius: 1,
        p: 1.5,
        mb: 2,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stat label="Balance" value={`$${account.balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
      <Box sx={{ width: "1px", height: 30, bgcolor: "divider" }} />
      <Stat label="Equity" value={`$${account.equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
      <Box sx={{ width: "1px", height: 30, bgcolor: "divider" }} />
      <Stat label="Profit" value={`$${account.profit.toFixed(2)}`} color={profitColor} />
      <Box sx={{ width: "1px", height: 30, bgcolor: "divider" }} />
      <Stat label="Free Margin" value={`$${account.free_margin.toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
      <Box sx={{ width: "1px", height: 30, bgcolor: "divider" }} />
      <Stat label="Margin" value={`$${account.margin.toFixed(2)}`} />
      <Box sx={{ width: "1px", height: 30, bgcolor: "divider" }} />
      <Stat label="Leverage" value={`1:${account.leverage}`} />
      <Box sx={{ width: "1px", height: 30, bgcolor: "divider" }} />
      <Stat label="Server" value={account.server} />
    </Box>
  );
}
