"use client";

import { Box, CircularProgress, Typography } from "@mui/material";

export default function LoadingSpinner({ message = "Loading..." }: { message?: string }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", py: 8, gap: 2 }}>
      <CircularProgress />
      <Typography variant="body2" color="text.secondary">{message}</Typography>
    </Box>
  );
}
