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

const DRAWER_WIDTH_EXPANDED = 240;
const DRAWER_WIDTH_COLLAPSED = 64;

const MAIN_NAV = [
  { label: "Trading", path: "/trading", icon: <TrendingUp size={20} /> },
  { label: "Backtest", path: "/backtest", icon: <History size={20} /> },
  { label: "ML Models", path: "/ml", icon: <Brain size={20} /> },
  { label: "AI Analysis", path: "/analysis", icon: <LineChart size={20} /> },
  { label: "Risk", path: "/risk", icon: <Shield size={20} /> },
  { label: "Audit Log", path: "/audit", icon: <FileText size={20} /> },
];

const ACCOUNT_NAV = [
  { label: "Settings", path: "/settings", icon: <Settings size={20} /> },
];

const itemSx = (collapsed: boolean, isActive: boolean) => ({
  borderRadius: 2,
  mb: 0.5,
  justifyContent: collapsed ? "center" : "flex-start",
  px: collapsed ? 1 : 2,
  ...(isActive
    ? {
        bgcolor: "#3b82f6",
        color: "#fff",
        "&:hover": { bgcolor: "#2563eb" },
        "& .MuiListItemIcon-root": { color: "#fff" },
      }
    : {
        color: "text.secondary",
        "&:hover": { bgcolor: "rgba(59, 130, 246, 0.06)" },
      }),
});

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);

  const drawerWidth = collapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH_EXPANDED;

  const renderItem = (item: { label: string; path: string; icon: React.ReactNode }) => {
    const isActive = pathname === item.path;
    return (
      <ListItemButton
        key={item.path}
        selected={false}
        onClick={() => router.push(item.path)}
        sx={itemSx(collapsed, isActive)}
      >
        <ListItemIcon
          sx={{
            minWidth: collapsed ? 0 : 40,
            color: isActive ? "#fff" : "text.secondary",
          }}
        >
          {item.icon}
        </ListItemIcon>
        {!collapsed && (
          <ListItemText
            primary={item.label}
            primaryTypographyProps={{
              fontSize: 14,
              fontWeight: isActive ? 600 : 400,
            }}
          />
        )}
      </ListItemButton>
    );
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
          borderRight: "1px solid",
          borderColor: "divider",
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
        <TrendingUp size={32} className="text-blue-500" />
        {!collapsed && (
          <Box>
            <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
              ForexAI
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Trading Platform
            </Typography>
          </Box>
        )}
      </Box>

      <Divider sx={{ borderColor: "rgba(148,163,184,0.1)" }} />

      {/* Main Navigation */}
      <List sx={{ px: 1.5, pt: 1 }}>
        {MAIN_NAV.map(renderItem)}
      </List>

      {/* ACCOUNT Section */}
      <Box sx={{ mt: "auto" }}>
        {!collapsed && (
          <Typography
            variant="overline"
            sx={{
              px: 3,
              pt: 2,
              pb: 0.5,
              display: "block",
              color: "text.secondary",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: 1.5,
            }}
          >
            ACCOUNT
          </Typography>
        )}
        {collapsed && <Divider sx={{ borderColor: "rgba(148,163,184,0.1)", mx: 1.5 }} />}

        <List sx={{ px: 1.5, pt: collapsed ? 1 : 0 }}>
          {ACCOUNT_NAV.map(renderItem)}
        </List>

        {/* Hide / Show toggle */}
        <Box sx={{ px: 1.5, pb: 1.5 }}>
          <ListItemButton
            onClick={() => setCollapsed(!collapsed)}
            sx={{
              borderRadius: 2,
              justifyContent: collapsed ? "center" : "flex-start",
              px: collapsed ? 1 : 2,
              color: "text.secondary",
              "&:hover": { bgcolor: "rgba(59, 130, 246, 0.06)" },
            }}
          >
            <ListItemIcon sx={{ minWidth: collapsed ? 0 : 40, color: "text.secondary" }}>
              {collapsed ? <ChevronsRight size={20} /> : <ChevronsLeft size={20} />}
            </ListItemIcon>
            {!collapsed && (
              <ListItemText
                primary="Hide"
                primaryTypographyProps={{ fontSize: 14 }}
              />
            )}
          </ListItemButton>
        </Box>
      </Box>
    </Drawer>
  );
}
