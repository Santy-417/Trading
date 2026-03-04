"use client";

import { Box, Card, CardContent, Typography } from "@mui/material";
import { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: string;
  trend?: "up" | "down" | "neutral";
  sparklineData?: number[];
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = "#7c3aed",
  trend,
  sparklineData,
}: StatCardProps) {
  const trendColor =
    trend === "up" ? "#22c55e" : trend === "down" ? "#ef4444" : "#94a3b8";

  // Transform sparkline data for Recharts
  const chartData = sparklineData?.map((v, i) => ({ i, v }));

  return (
    <motion.div
      whileHover={{
        y: -2,
        transition: { type: "spring", stiffness: 400, damping: 25 },
      }}
      style={{ borderRadius: "12px", height: "100%" }}
    >
      <Card
        sx={{
          height: "100%",
          cursor: "default",
          position: "relative",
          overflow: "hidden",
          transition: "border-color 0.2s",
          "&:hover": {
            borderColor: `${color}30`,
          },
        }}
      >
        {/* Sparkline background */}
        {chartData && chartData.length > 1 && (
          <Box
            sx={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              height: 40,
              opacity: 0.4,
              pointerEvents: "none",
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id={`sparkGrad-${title}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={trendColor} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={trendColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={trendColor}
                  strokeWidth={1.5}
                  fill={`url(#sparkGrad-${title})`}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        )}

        <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 }, position: "relative" }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
            }}
          >
            <Box sx={{ flex: 1 }}>
              <Typography
                variant="body2"
                sx={{
                  color: "#64748b",
                  fontSize: 11,
                  fontWeight: 500,
                  letterSpacing: "0.03em",
                  textTransform: "uppercase",
                  mb: 0.75,
                }}
              >
                {title}
              </Typography>
              <Typography
                variant="h5"
                sx={{
                  color: trend ? trendColor : "text.primary",
                  fontWeight: 700,
                  fontSize: 22,
                  lineHeight: 1.2,
                  fontFeatureSettings: '"tnum"',
                }}
              >
                {value}
              </Typography>
              {subtitle && (
                <Typography
                  variant="caption"
                  sx={{ color: "#64748b", fontSize: 11, mt: 0.5, display: "block" }}
                >
                  {subtitle}
                </Typography>
              )}
            </Box>
            <Box
              sx={{
                p: 1,
                borderRadius: 2,
                bgcolor: `${color}10`,
                border: `1px solid ${color}15`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Icon size={20} style={{ color }} />
            </Box>
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  );
}
