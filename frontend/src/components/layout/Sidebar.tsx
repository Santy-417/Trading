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
  IconButton,
} from "@mui/material";
import {
  Home,
  TrendingUp,
  History,
  Brain,
  LineChart,
  Shield,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const DRAWER_WIDTH_EXPANDED = 240;
const DRAWER_WIDTH_COLLAPSED = 64;

const NAV_ITEMS = [
  { label: "Dashboard", path: "/", icon: <Home size={20} /> },
  { label: "Trading", path: "/trading", icon: <TrendingUp size={20} /> },
  { label: "Backtest", path: "/backtest", icon: <History size={20} /> },
  { label: "ML Models", path: "/ml", icon: <Brain size={20} /> },
  { label: "AI Analysis", path: "/analysis", icon: <LineChart size={20} /> },
  { label: "Risk", path: "/risk", icon: <Shield size={20} /> },
  { label: "Audit Log", path: "/audit", icon: <FileText size={20} /> },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);

  const drawerWidth = collapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH_EXPANDED;

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
        },
      }}
    >
      <Box sx={{ p: 2.5, display: "flex", alignItems: "center", gap: 1.5, justifyContent: collapsed ? "center" : "flex-start" }}>
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

      <List sx={{ px: 1.5, pt: 1 }}>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            selected={pathname === item.path}
            onClick={() => router.push(item.path)}
            sx={{
              borderRadius: collapsed ? 1 : 2,
              mb: 0.5,
              justifyContent: collapsed ? "center" : "flex-start",
              px: collapsed ? 1 : 2,
              "&:hover": {
                bgcolor: "rgba(59, 130, 246, 0.04)",
              },
              "&.Mui-selected": {
                bgcolor: "rgba(59, 130, 246, 0.08)",
                borderLeft: "2px solid #3b82f6",
                "&:hover": {
                  bgcolor: "rgba(59, 130, 246, 0.12)"
                },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: collapsed ? 0 : 40, color: pathname === item.path ? "primary.main" : "text.secondary" }}>
              {item.icon}
            </ListItemIcon>
            {!collapsed && (
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: 14,
                  fontWeight: pathname === item.path ? 600 : 400,
                }}
              />
            )}
          </ListItemButton>
        ))}
      </List>

      <Box sx={{ mt: "auto", p: 1.5 }}>
        <Divider sx={{ borderColor: "rgba(148,163,184,0.1)", mb: 1 }} />
        <ListItemButton
          onClick={() => router.push("/settings")}
          sx={{
            borderRadius: collapsed ? 1 : 2,
            justifyContent: collapsed ? "center" : "flex-start",
            px: collapsed ? 1 : 2,
            "&:hover": {
              bgcolor: "rgba(59, 130, 246, 0.04)",
            },
          }}
        >
          <ListItemIcon sx={{ minWidth: collapsed ? 0 : 40, color: "text.secondary" }}>
            <Settings size={20} />
          </ListItemIcon>
          {!collapsed && (
            <ListItemText primary="Settings" primaryTypographyProps={{ fontSize: 14 }} />
          )}
        </ListItemButton>

        {/* Toggle Button */}
        <Box sx={{ mt: 1, borderTop: 1, borderColor: "divider", pt: 1 }}>
          <IconButton
            onClick={() => setCollapsed(!collapsed)}
            sx={{
              width: "100%",
              borderRadius: 1,
              "&:hover": {
                bgcolor: "rgba(59, 130, 246, 0.04)",
              },
            }}
          >
            {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
          </IconButton>
        </Box>
      </Box>
    </Drawer>
  );
}
