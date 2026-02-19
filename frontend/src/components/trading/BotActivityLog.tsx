"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, Typography } from "@mui/material";
import api from "@/lib/api";
import type { BotLogEntry } from "@/types";

const LEVEL_COLORS: Record<string, string> = {
  info: "#94a3b8",
  warning: "#f59e0b",
  error: "#ef4444",
};

export default function BotActivityLog() {
  const [logs, setLogs] = useState<BotLogEntry[]>([]);

  const fetchLogs = useCallback(async () => {
    try {
      const { data } = await api.get<BotLogEntry[]>("/bot/logs", { params: { limit: 50 } });
      setLogs(data);
    } catch {
      // Bot may not be running
    }
  }, []);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [fetchLogs]);

  if (logs.length === 0) {
    return (
      <Box sx={{ textAlign: "center", py: 4 }}>
        <Typography variant="body2" color="text.secondary">
          No bot activity yet. Start the bot to see logs.
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        maxHeight: 400,
        overflowY: "auto",
        fontFamily: "monospace",
        fontSize: "0.75rem",
        "&::-webkit-scrollbar": { width: 6 },
        "&::-webkit-scrollbar-thumb": { bgcolor: "divider", borderRadius: 3 },
      }}
    >
      {[...logs].reverse().map((log, i) => {
        const time = new Date(log.timestamp).toLocaleTimeString();
        const color = LEVEL_COLORS[log.level] || "#94a3b8";
        return (
          <Box
            key={i}
            sx={{
              py: 0.5,
              px: 1,
              borderBottom: "1px solid",
              borderColor: "divider",
              "&:hover": { bgcolor: "action.hover" },
            }}
          >
            <Typography component="span" sx={{ color: "text.secondary", fontSize: "inherit", fontFamily: "inherit" }}>
              {time}
            </Typography>
            {" "}
            <Typography
              component="span"
              sx={{ color, fontSize: "inherit", fontFamily: "inherit", fontWeight: 600, textTransform: "uppercase" }}
            >
              {log.level}
            </Typography>
            {" "}
            <Typography component="span" sx={{ color: "text.primary", fontSize: "inherit", fontFamily: "inherit" }}>
              {log.message}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}
