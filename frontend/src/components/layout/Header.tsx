"use client";

import { AppBar, Box, Chip, IconButton, Toolbar, Typography } from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import CircleIcon from "@mui/icons-material/Circle";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store";

export default function Header() {
  const router = useRouter();
  const botStatus = useAppStore((s) => s.botStatus);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  const isRunning = botStatus?.state === "running";

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: "background.paper",
        borderBottom: "1px solid rgba(148,163,184,0.1)",
      }}
    >
      <Toolbar sx={{ justifyContent: "space-between" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Typography variant="h6" color="text.primary">
            ForexAI Trading Platform
          </Typography>
          <Chip
            icon={<CircleIcon sx={{ fontSize: 10 }} />}
            label={isRunning ? `Bot: ${botStatus?.strategy}` : "Bot: Stopped"}
            color={isRunning ? "success" : "default"}
            size="small"
            variant="outlined"
          />
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Chip
            label="Demo Account"
            size="small"
            color="warning"
            variant="outlined"
          />
          <IconButton onClick={handleLogout} color="inherit" size="small">
            <LogoutIcon />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
