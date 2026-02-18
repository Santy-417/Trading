"use client";

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
import DashboardIcon from "@mui/icons-material/Dashboard";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import HistoryIcon from "@mui/icons-material/History";
import PsychologyIcon from "@mui/icons-material/Psychology";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import ShieldIcon from "@mui/icons-material/Shield";
import DescriptionIcon from "@mui/icons-material/Description";
import SettingsIcon from "@mui/icons-material/Settings";

const DRAWER_WIDTH = 260;

const NAV_ITEMS = [
  { label: "Dashboard", path: "/", icon: <DashboardIcon /> },
  { label: "Trading", path: "/trading", icon: <ShowChartIcon /> },
  { label: "Backtest", path: "/backtest", icon: <HistoryIcon /> },
  { label: "ML Models", path: "/ml", icon: <PsychologyIcon /> },
  { label: "AI Analysis", path: "/analysis", icon: <AutoGraphIcon /> },
  { label: "Risk", path: "/risk", icon: <ShieldIcon /> },
  { label: "Audit Log", path: "/audit", icon: <DescriptionIcon /> },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          boxSizing: "border-box",
          bgcolor: "background.paper",
          borderRight: "1px solid rgba(148,163,184,0.1)",
        },
      }}
    >
      <Box sx={{ p: 2.5, display: "flex", alignItems: "center", gap: 1.5 }}>
        <ShowChartIcon color="primary" sx={{ fontSize: 32 }} />
        <Box>
          <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
            ForexAI
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Trading Platform
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ borderColor: "rgba(148,163,184,0.1)" }} />

      <List sx={{ px: 1.5, pt: 1 }}>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            selected={pathname === item.path}
            onClick={() => router.push(item.path)}
            sx={{
              borderRadius: 2,
              mb: 0.5,
              "&.Mui-selected": {
                bgcolor: "rgba(59,130,246,0.12)",
                "&:hover": { bgcolor: "rgba(59,130,246,0.18)" },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 40, color: pathname === item.path ? "primary.main" : "text.secondary" }}>
              {item.icon}
            </ListItemIcon>
            <ListItemText
              primary={item.label}
              primaryTypographyProps={{
                fontSize: 14,
                fontWeight: pathname === item.path ? 600 : 400,
              }}
            />
          </ListItemButton>
        ))}
      </List>

      <Box sx={{ mt: "auto", p: 1.5 }}>
        <Divider sx={{ borderColor: "rgba(148,163,184,0.1)", mb: 1 }} />
        <ListItemButton
          onClick={() => router.push("/settings")}
          sx={{ borderRadius: 2 }}
        >
          <ListItemIcon sx={{ minWidth: 40, color: "text.secondary" }}>
            <SettingsIcon />
          </ListItemIcon>
          <ListItemText primary="Settings" primaryTypographyProps={{ fontSize: 14 }} />
        </ListItemButton>
      </Box>
    </Drawer>
  );
}
