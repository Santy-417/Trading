"use client";

import { useState } from "react";
import { Card, CardContent, Tab, Tabs } from "@mui/material";
import ManualTradeForm from "./ManualTradeForm";
import BotControl from "./BotControl";
import BotActivityLog from "./BotActivityLog";

export default function TradePanel() {
  const [tab, setTab] = useState(0);

  return (
    <Card sx={{ height: "100%" }}>
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        variant="fullWidth"
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          "& .MuiTab-root": { fontSize: "0.8rem", minHeight: 42, py: 0 },
        }}
      >
        <Tab label="Manual Trade" />
        <Tab label="Bot Control" />
        <Tab label="Bot Logs" />
      </Tabs>
      <CardContent sx={{ pt: 2 }}>
        {tab === 0 && <ManualTradeForm />}
        {tab === 1 && <BotControl embedded />}
        {tab === 2 && <BotActivityLog />}
      </CardContent>
    </Card>
  );
}
