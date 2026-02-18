"use client";

import { Box, Card, CardContent, Typography, Divider, Chip, Stack } from "@mui/material";

export default function SettingsPage() {
  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Settings
      </Typography>

      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Platform Info</Typography>
          <Stack spacing={1.5}>
            <Box sx={{ display: "flex", justifyContent: "space-between" }}>
              <Typography variant="body2" color="text.secondary">Version</Typography>
              <Typography variant="body2">1.0.0</Typography>
            </Box>
            <Divider sx={{ borderColor: "rgba(148,163,184,0.1)" }} />
            <Box sx={{ display: "flex", justifyContent: "space-between" }}>
              <Typography variant="body2" color="text.secondary">Backend</Typography>
              <Chip label="FastAPI" size="small" variant="outlined" />
            </Box>
            <Divider sx={{ borderColor: "rgba(148,163,184,0.1)" }} />
            <Box sx={{ display: "flex", justifyContent: "space-between" }}>
              <Typography variant="body2" color="text.secondary">Trading Pairs</Typography>
              <Box sx={{ display: "flex", gap: 0.5 }}>
                <Chip label="EURUSD" size="small" />
                <Chip label="XAUUSD" size="small" />
              </Box>
            </Box>
            <Divider sx={{ borderColor: "rgba(148,163,184,0.1)" }} />
            <Box sx={{ display: "flex", justifyContent: "space-between" }}>
              <Typography variant="body2" color="text.secondary">MT5 Broker</Typography>
              <Typography variant="body2">MetaQuotes-Demo</Typography>
            </Box>
            <Divider sx={{ borderColor: "rgba(148,163,184,0.1)" }} />
            <Box sx={{ display: "flex", justifyContent: "space-between" }}>
              <Typography variant="body2" color="text.secondary">AI Model</Typography>
              <Chip label="GPT-4o-mini" size="small" color="secondary" variant="outlined" />
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
