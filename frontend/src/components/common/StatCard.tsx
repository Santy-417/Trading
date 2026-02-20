"use client";

import { Box, Card, CardContent, Typography } from "@mui/material";
import { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: string;
  trend?: "up" | "down" | "neutral";
}

export default function StatCard({ title, value, subtitle, icon: Icon, color = "#3b82f6", trend }: StatCardProps) {
  const trendColor = trend === "up" ? "#22c55e" : trend === "down" ? "#ef4444" : "#94a3b8";

  return (
    <motion.div
      whileHover={{
        y: -4,
        boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)"
      }}
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
      style={{ borderRadius: '8px' }}
    >
      <Card sx={{ height: '100%', transition: 'all 0.2s', cursor: 'pointer' }}>
        <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                {title}
              </Typography>
              <Typography variant="h5" sx={{ color: trend ? trendColor : "text.primary" }}>
                {value}
              </Typography>
              {subtitle && (
                <Typography variant="caption" color="text.secondary">
                  {subtitle}
                </Typography>
              )}
            </Box>
            <Box
              sx={{
                p: 1,
                borderRadius: 2,
                bgcolor: `${color}15`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Icon size={24} style={{ color }} />
            </Box>
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  );
}
