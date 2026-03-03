"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import {
  AppBar,
  Box,
  Chip,
  IconButton,
  Toolbar,
  Typography,
  Tooltip,
} from "@mui/material";
import { LogOut, Clock, Circle } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store";

const PAGE_TITLES: Record<string, string> = {
  "/trading": "Live Trading",
  "/backtest": "Backtesting",
  "/ml": "ML Models",
  "/analysis": "AI Analysis",
  "/risk": "Risk Management",
  "/audit": "Audit Log",
  "/settings": "Settings",
};

function getActiveSession(): { name: string; color: string } {
  const now = new Date();
  const utcH = now.getUTCHours();
  const utcM = now.getUTCMinutes();
  const mins = utcH * 60 + utcM;

  // Asian: 00:00-06:00 UTC
  if (mins < 360) return { name: "Asian", color: "#f59e0b" };
  // London: 07:00-16:30 UTC
  if (mins >= 420 && mins < 990) return { name: "London", color: "#3b82f6" };
  // NY: 13:00-21:30 UTC
  if (mins >= 780 && mins < 1290) return { name: "New York", color: "#8b5cf6" };
  // Off-hours
  return { name: "Off-Hours", color: "#64748b" };
}

function formatTime(date: Date, tz: string): string {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: tz,
  });
}

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const botStatus = useAppStore((s) => s.botStatus);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  const isRunning = botStatus?.state === "running";
  const pageTitle = PAGE_TITLES[pathname] || "Dashboard";
  const session = getActiveSession();

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: "background.paper",
        borderBottom: "1px solid rgba(148,163,184,0.08)",
      }}
    >
      <Toolbar
        sx={{
          justifyContent: "space-between",
          minHeight: "56px !important",
          px: 2.5,
        }}
      >
        {/* Left: Breadcrumb + Bot status */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Box>
            <Typography
              variant="caption"
              sx={{ color: "#64748b", fontSize: 10, letterSpacing: "0.05em" }}
            >
              Dashboard
            </Typography>
            <Typography
              variant="h6"
              color="text.primary"
              sx={{ fontSize: 16, fontWeight: 600, lineHeight: 1.2 }}
            >
              {pageTitle}
            </Typography>
          </Box>

          <Chip
            icon={
              <Circle
                size={8}
                fill={isRunning ? "#22c55e" : "#64748b"}
                style={{ color: isRunning ? "#22c55e" : "#64748b" }}
              />
            }
            label={
              isRunning ? `${botStatus?.strategy}` : "Bot Stopped"
            }
            size="small"
            variant="outlined"
            sx={{
              borderColor: isRunning
                ? "rgba(34,197,94,0.25)"
                : "rgba(148,163,184,0.15)",
              color: isRunning ? "#22c55e" : "#64748b",
              fontSize: 11,
              height: 26,
              "& .MuiChip-icon": { ml: 0.5 },
            }}
          />
        </Box>

        {/* Right: Session + Clock + Logout */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          {/* Active session indicator */}
          <Tooltip title={`${session.name} Session Active`} arrow>
            <Chip
              label={session.name}
              size="small"
              sx={{
                bgcolor: `${session.color}12`,
                color: session.color,
                border: `1px solid ${session.color}25`,
                fontSize: 11,
                height: 26,
                fontWeight: 500,
              }}
            />
          </Tooltip>

          {/* Clock */}
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1.5,
              py: 0.5,
              borderRadius: 1.5,
              bgcolor: "rgba(148, 163, 184, 0.04)",
            }}
          >
            <Clock size={14} style={{ color: "#64748b" }} />
            <Box>
              <Typography
                sx={{
                  fontSize: 11,
                  fontFamily: "'JetBrains Mono', monospace",
                  color: "text.primary",
                  fontWeight: 500,
                  lineHeight: 1.3,
                }}
              >
                {formatTime(time, "UTC")}
                <Typography
                  component="span"
                  sx={{ color: "#64748b", fontSize: 9, ml: 0.5 }}
                >
                  UTC
                </Typography>
              </Typography>
              <Typography
                sx={{
                  fontSize: 10,
                  fontFamily: "'JetBrains Mono', monospace",
                  color: "#64748b",
                  lineHeight: 1.3,
                }}
              >
                {formatTime(time, "America/Bogota")}
                <Typography
                  component="span"
                  sx={{ color: "#475569", fontSize: 9, ml: 0.5 }}
                >
                  COL
                </Typography>
              </Typography>
            </Box>
          </Box>

          {/* Logout */}
          <Tooltip title="Sign out" arrow>
            <IconButton
              onClick={handleLogout}
              size="small"
              sx={{
                color: "#64748b",
                "&:hover": { color: "#ef4444", bgcolor: "rgba(239,68,68,0.08)" },
              }}
            >
              <LogOut size={18} />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
