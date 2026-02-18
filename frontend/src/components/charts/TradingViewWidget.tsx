"use client";

import { useEffect, useRef } from "react";
import { Box, Card, CardContent, Typography } from "@mui/material";

interface TradingViewWidgetProps {
  symbol?: string;
  height?: number;
}

export default function TradingViewWidget({
  symbol = "FX:EURUSD",
  height = 500,
}: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clear previous widget
    containerRef.current.innerHTML = "";

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol,
      interval: "60",
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: "en",
      backgroundColor: "rgba(15, 23, 42, 1)",
      gridColor: "rgba(148, 163, 184, 0.06)",
      allow_symbol_change: true,
      calendar: false,
      support_host: "https://www.tradingview.com",
    });

    containerRef.current.appendChild(script);
  }, [symbol]);

  return (
    <Card>
      <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
        <Box sx={{ p: 2, pb: 0 }}>
          <Typography variant="h6">Chart</Typography>
        </Box>
        <Box
          ref={containerRef}
          sx={{ height, "& .tradingview-widget-container": { height: "100%" } }}
          className="tradingview-widget-container"
        />
      </CardContent>
    </Card>
  );
}
