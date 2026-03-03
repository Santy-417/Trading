"use client";

import { Box, Card, CardContent, Chip, Typography } from "@mui/material";
import { TrendingUp, TrendingDown } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

interface EquityChartProps {
  data: { date: string; equity: number }[];
  title?: string;
  dateRange?: { from: string; to: string };
  timeframe?: string;
}

function CustomTooltip({
  active,
  payload,
  initialBalance,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { date: string; equity: number } }>;
  label?: string;
  initialBalance: number;
}) {
  if (!active || !payload?.length) return null;

  const equity = payload[0].value;
  const pnl = equity - initialBalance;
  const pnlPct = ((pnl / initialBalance) * 100).toFixed(2);
  const peak = payload[0].payload.equity;
  const dd = peak > 0 ? (((peak - equity) / peak) * 100).toFixed(2) : "0.00";

  return (
    <Box
      sx={{
        bgcolor: "rgba(15, 23, 42, 0.95)",
        backdropFilter: "blur(12px)",
        border: "1px solid rgba(148,163,184,0.12)",
        borderRadius: 2,
        p: 1.5,
        minWidth: 160,
      }}
    >
      <Typography sx={{ fontSize: 10, color: "#64748b", mb: 0.75 }}>
        {payload[0].payload.date}
      </Typography>
      <Typography
        sx={{
          fontSize: 14,
          fontWeight: 700,
          color: "text.primary",
          fontFeatureSettings: '"tnum"',
        }}
      >
        ${equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}
      </Typography>
      <Box sx={{ display: "flex", gap: 1.5, mt: 0.5 }}>
        <Typography
          sx={{
            fontSize: 11,
            color: pnl >= 0 ? "#22c55e" : "#ef4444",
            fontFeatureSettings: '"tnum"',
          }}
        >
          {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)} ({pnlPct}%)
        </Typography>
        {parseFloat(dd) > 0 && (
          <Typography
            sx={{ fontSize: 11, color: "#f59e0b", fontFeatureSettings: '"tnum"' }}
          >
            DD: {dd}%
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export default function EquityChart({
  data,
  title = "Equity Curve",
  dateRange,
  timeframe,
}: EquityChartProps) {
  if (!data || data.length === 0) return null;

  const initialBalance = data[0].equity;
  const finalBalance = data[data.length - 1].equity;
  const isProfit = finalBalance >= initialBalance;
  const totalReturn = (
    ((finalBalance - initialBalance) / initialBalance) *
    100
  ).toFixed(2);
  const lineColor = isProfit ? "#22c55e" : "#ef4444";

  return (
    <Card>
      <CardContent sx={{ p: 2.5 }}>
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            mb: 2,
          }}
        >
          <Box>
            <Typography
              variant="h6"
              sx={{ fontSize: 15, fontWeight: 600 }}
            >
              {title}
            </Typography>
            {dateRange && (
              <Typography
                sx={{ fontSize: 11, color: "#64748b", mt: 0.25 }}
              >
                {dateRange.from} → {dateRange.to}
                {timeframe && (
                  <Typography
                    component="span"
                    sx={{ color: "#475569", ml: 0.5 }}
                  >
                    ({timeframe})
                  </Typography>
                )}
              </Typography>
            )}
          </Box>
          <Chip
            icon={
              isProfit ? (
                <TrendingUp size={12} style={{ color: "#22c55e" }} />
              ) : (
                <TrendingDown size={12} style={{ color: "#ef4444" }} />
              )
            }
            label={`${isProfit ? "+" : ""}${totalReturn}%`}
            size="small"
            sx={{
              bgcolor: isProfit
                ? "rgba(34,197,94,0.08)"
                : "rgba(239,68,68,0.08)",
              color: lineColor,
              border: `1px solid ${isProfit ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}`,
              fontSize: 11,
              fontWeight: 600,
              height: 24,
              "& .MuiChip-icon": { ml: 0.3 },
            }}
          />
        </Box>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={lineColor} stopOpacity={0.15} />
                <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(148,163,184,0.06)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              stroke="#475569"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "rgba(148,163,184,0.08)" }}
            />
            <YAxis
              stroke="#475569"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
              width={50}
            />
            <Tooltip
              content={<CustomTooltip initialBalance={initialBalance} />}
              cursor={{
                stroke: "rgba(148,163,184,0.2)",
                strokeDasharray: "4 4",
              }}
            />
            {/* Initial balance reference line */}
            <ReferenceLine
              y={initialBalance}
              stroke="rgba(148,163,184,0.2)"
              strokeDasharray="6 4"
              label={{
                value: `Initial: $${initialBalance.toLocaleString()}`,
                position: "insideTopRight",
                fill: "#64748b",
                fontSize: 10,
              }}
            />
            <Area
              type="monotone"
              dataKey="equity"
              stroke={lineColor}
              fill="url(#equityGrad)"
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 4,
                stroke: lineColor,
                strokeWidth: 2,
                fill: "#0f172a",
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
