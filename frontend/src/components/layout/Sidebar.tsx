"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  Tooltip,
  Avatar,
  Chip,
} from "@mui/material";
import {
  TrendingUp,
  History,
  Brain,
  LineChart,
  Shield,
  FileText,
  Settings,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useAppStore } from "@/store";

const DRAWER_WIDTH_EXPANDED = 240;
const DRAWER_WIDTH_COLLAPSED = 64;

const MAIN_NAV = [
  { label: "Trading", path: "/trading", icon: <TrendingUp size={20} /> },
  { label: "Backtest", path: "/backtest", icon: <History size={20} /> },
  { label: "ML Models", path: "/ml", icon: <Brain size={20} /> },
  { label: "AI Analysis", path: "/analysis", icon: <LineChart size={20} /> },
  { label: "Risk", path: "/risk", icon: <Shield size={20} />, badgeKey: "risk" },
  { label: "Audit Log", path: "/audit", icon: <FileText size={20} /> },
];

const ACCOUNT_NAV = [
  { label: "Settings", path: "/settings", icon: <Settings size={20} /> },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const botStatus = useAppStore((s) => s.botStatus);

  const drawerWidth = collapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH_EXPANDED;

  const renderItem = (item: {
    label: string;
    path: string;
    icon: React.ReactNode;
    badgeKey?: string;
  }) => {
    const isActive = pathname === item.path;

    // Show risk badge when bot is running (circuit breaker could be active)
    const showBadge = item.badgeKey === "risk" && botStatus?.state === "running";

    const button = (
      <ListItemButton
        key={item.path}
        selected={false}
        onClick={() => router.push(item.path)}
        sx={{
          borderRadius: 2,
          mb: 0.5,
          justifyContent: collapsed ? "center" : "flex-start",
          px: collapsed ? 1 : 2,
          position: "relative",
          overflow: "hidden",
          ...(isActive
            ? {
                bgcolor: "rgba(59, 130, 246, 0.08)",
                color: "#3b82f6",
                "&:hover": { bgcolor: "rgba(59, 130, 246, 0.12)" },
                "& .MuiListItemIcon-root": { color: "#3b82f6" },
                "&::before": {
                  content: '""',
                  position: "absolute",
                  left: 0,
                  top: "20%",
                  bottom: "20%",
                  width: 3,
                  borderRadius: "0 4px 4px 0",
                  bgcolor: "#3b82f6",
                },
              }
            : {
                color: "text.secondary",
                "&:hover": {
                  bgcolor: "rgba(148, 163, 184, 0.06)",
                  color: "text.primary",
                  "& .MuiListItemIcon-root": { color: "text.primary" },
                },
              }),
        }}
      >
        <ListItemIcon
          sx={{
            minWidth: collapsed ? 0 : 40,
            color: isActive ? "#3b82f6" : "text.secondary",
            transition: "color 0.15s",
          }}
        >
          {item.icon}
        </ListItemIcon>
        {!collapsed && (
          <ListItemText
            primary={item.label}
            primaryTypographyProps={{
              fontSize: 13,
              fontWeight: isActive ? 600 : 400,
              letterSpacing: "0.01em",
            }}
          />
        )}
        {showBadge && !collapsed && (
          <Box
            sx={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              bgcolor: "#22c55e",
              boxShadow: "0 0 8px rgba(34,197,94,0.5)",
              flexShrink: 0,
            }}
          />
        )}
        {showBadge && collapsed && (
          <Box
            sx={{
              position: "absolute",
              top: 8,
              right: 8,
              width: 6,
              height: 6,
              borderRadius: "50%",
              bgcolor: "#22c55e",
              boxShadow: "0 0 8px rgba(34,197,94,0.5)",
            }}
          />
        )}
      </ListItemButton>
    );

    if (collapsed) {
      return (
        <Tooltip key={item.path} title={item.label} placement="right" arrow>
          {button}
        </Tooltip>
      );
    }

    return button;
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: drawerWidth,
          transition: "width 0.3s ease-in-out",
          boxSizing: "border-box",
          bgcolor: "background.paper",
          borderRight: "1px solid rgba(148, 163, 184, 0.08)",
          overflow: "hidden",
        },
      }}
    >
      {/* Logo */}
      <Box
        sx={{
          p: 2.5,
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          justifyContent: collapsed ? "center" : "flex-start",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 36,
            height: 36,
            borderRadius: 2,
            bgcolor: "rgba(59, 130, 246, 0.1)",
            border: "1px solid rgba(59, 130, 246, 0.15)",
            flexShrink: 0,
          }}
        >
          <TrendingUp size={20} style={{ color: "#3b82f6" }} />
        </Box>
        {!collapsed && (
          <Box>
            <Typography
              variant="h6"
              sx={{ lineHeight: 1.2, fontSize: 16, fontWeight: 700 }}
            >
              ForexAI
            </Typography>
            <Typography
              variant="caption"
              sx={{ color: "#64748b", fontSize: 10, letterSpacing: "0.05em" }}
            >
              Trading Platform
            </Typography>
          </Box>
        )}
      </Box>

      <Divider sx={{ borderColor: "rgba(148,163,184,0.08)", mx: 1.5 }} />

      {/* Main Navigation */}
      {!collapsed && (
        <Typography
          variant="overline"
          sx={{
            px: 3,
            pt: 2,
            pb: 0.5,
            display: "block",
            color: "#64748b",
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: 1.5,
          }}
        >
          NAVIGATION
        </Typography>
      )}
      <List sx={{ px: 1.5, pt: collapsed ? 1.5 : 0 }}>
        {MAIN_NAV.map(renderItem)}
      </List>

      {/* ACCOUNT Section */}
      <Box sx={{ mt: "auto" }}>
        <Divider sx={{ borderColor: "rgba(148,163,184,0.08)", mx: 1.5 }} />

        {!collapsed && (
          <Typography
            variant="overline"
            sx={{
              px: 3,
              pt: 1.5,
              pb: 0.5,
              display: "block",
              color: "#64748b",
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: 1.5,
            }}
          >
            ACCOUNT
          </Typography>
        )}

        <List sx={{ px: 1.5, pt: collapsed ? 1 : 0 }}>
          {ACCOUNT_NAV.map(renderItem)}
        </List>

        {/* User avatar + Demo badge */}
        {!collapsed && (
          <Box
            sx={{
              px: 2,
              py: 1.5,
              mx: 1.5,
              mb: 1,
              borderRadius: 2,
              bgcolor: "rgba(148, 163, 184, 0.04)",
              display: "flex",
              alignItems: "center",
              gap: 1.5,
            }}
          >
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: "rgba(59, 130, 246, 0.15)",
                color: "#3b82f6",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              ST
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography
                variant="body2"
                sx={{ fontSize: 12, fontWeight: 500, lineHeight: 1.3 }}
              >
                Santiago
              </Typography>
              <Chip
                label="Demo"
                size="small"
                sx={{
                  height: 16,
                  fontSize: 9,
                  fontWeight: 600,
                  letterSpacing: "0.05em",
                  bgcolor: "rgba(245, 158, 11, 0.1)",
                  color: "#f59e0b",
                  border: "1px solid rgba(245, 158, 11, 0.2)",
                  mt: 0.25,
                }}
              />
            </Box>
          </Box>
        )}

        {collapsed && (
          <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
            <Tooltip title="Santiago (Demo)" placement="right" arrow>
              <Avatar
                sx={{
                  width: 32,
                  height: 32,
                  bgcolor: "rgba(59, 130, 246, 0.15)",
                  color: "#3b82f6",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                ST
              </Avatar>
            </Tooltip>
          </Box>
        )}

        {/* Collapse toggle */}
        <Box sx={{ px: 1.5, pb: 1.5 }}>
          <Tooltip
            title={collapsed ? "Expand" : ""}
            placement="right"
            arrow
            disableHoverListener={!collapsed}
          >
            <ListItemButton
              onClick={() => setCollapsed(!collapsed)}
              sx={{
                borderRadius: 2,
                justifyContent: collapsed ? "center" : "flex-start",
                px: collapsed ? 1 : 2,
                color: "#64748b",
                "&:hover": {
                  bgcolor: "rgba(148, 163, 184, 0.06)",
                  color: "text.primary",
                },
              }}
            >
              <ListItemIcon
                sx={{ minWidth: collapsed ? 0 : 40, color: "inherit" }}
              >
                {collapsed ? (
                  <ChevronsRight size={18} />
                ) : (
                  <ChevronsLeft size={18} />
                )}
              </ListItemIcon>
              {!collapsed && (
                <ListItemText
                  primary="Collapse"
                  primaryTypographyProps={{ fontSize: 13 }}
                />
              )}
            </ListItemButton>
          </Tooltip>
        </Box>
      </Box>
    </Drawer>
  );
}
