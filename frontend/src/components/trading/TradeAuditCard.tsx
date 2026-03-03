"use client";

import {
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  LinearProgress,
  Typography,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Shield,
  Brain,
  Target,
  Clock,
  Activity,
  Crosshair,
} from "lucide-react";
import type { TradeAudit, TradeAuditMetadata } from "@/types";
import { formatNumberWithDots } from "@/lib/numberFormat";

interface TradeAuditCardProps {
  trade: TradeAudit;
  index: number;
  total: number;
  symbol: string;
  timeframe: string;
}

function buildSmcNarrative(meta: TradeAuditMetadata): string {
  const parts: string[] = [];
  if (meta.daily_bias) parts.push(`${meta.daily_bias} Bias`);
  if (meta.manipulation_type) {
    const readable =
      meta.manipulation_type === "bullish_sweep_pdl"
        ? "London Sweep PDL"
        : meta.manipulation_type === "bearish_sweep_pdh"
          ? "London Sweep PDH"
          : meta.manipulation_type;
    parts.push(readable);
  }
  if (meta.choch_detected) parts.push("M5 ChoCh");
  if (meta.fvg_tp !== null && meta.fvg_tp !== undefined) parts.push("FVG Target");
  return parts.length > 0 ? parts.join(" + ") : "No SMC context";
}

function getExitReasonColor(reason: string): "success" | "error" | "warning" | "default" {
  switch (reason) {
    case "TP": return "success";
    case "SL": return "error";
    case "TIME_CLOSE": return "warning";
    default: return "default";
  }
}

function getExitReasonLabel(reason: string): string {
  switch (reason) {
    case "TP": return "Take Profit";
    case "SL": return "Stop Loss";
    case "TIME_CLOSE": return "Time Close";
    default: return reason || "Unknown";
  }
}

export default function TradeAuditCard({
  trade,
  index,
  total,
  symbol,
  timeframe,
}: TradeAuditCardProps) {
  const isProfit = trade.profit >= 0;
  const meta = trade.signal_metadata;
  const hasSmcData = meta && (meta.daily_bias || meta.manipulation_type || meta.choch_detected);
  const hasMlData = meta && meta.ml_confidence !== null && meta.ml_confidence !== undefined;

  return (
    <Card
      sx={{
        width: { xs: "100%", md: 420 },
        minHeight: 380,
        borderLeft: `4px solid`,
        borderLeftColor: isProfit ? "success.main" : "error.main",
        bgcolor: "background.paper",
      }}
    >
      <CardContent sx={{ p: 2.5 }}>
        {/* Header */}
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={trade.direction}
              size="small"
              color={trade.direction === "BUY" ? "success" : "error"}
              sx={{ fontWeight: 700, minWidth: 52 }}
            />
            <Typography variant="subtitle2" color="text.secondary">
              {symbol}
            </Typography>
            <Chip label={timeframe} size="small" variant="outlined" sx={{ height: 22, fontSize: 11 }} />
          </Box>
          <Box sx={{ textAlign: "right" }}>
            <Typography
              variant="h6"
              sx={{ color: isProfit ? "success.main" : "error.main", fontWeight: 700, lineHeight: 1.2 }}
            >
              {isProfit ? "+" : ""}${formatNumberWithDots(trade.profit, 2)}
            </Typography>
            {trade.exit_reason && (
              <Chip
                label={getExitReasonLabel(trade.exit_reason)}
                size="small"
                color={getExitReasonColor(trade.exit_reason)}
                variant="outlined"
                sx={{ mt: 0.5, height: 20, fontSize: 10 }}
              />
            )}
          </Box>
        </Box>

        <Divider sx={{ mb: 1.5 }} />

        {/* Technical Data */}
        <Box sx={{ mb: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
            <Crosshair size={14} />
            <Typography variant="caption" color="text.secondary" fontWeight={600}>
              Trade Details
            </Typography>
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0.5, pl: 2.5 }}>
            <Typography variant="caption" color="text.secondary">
              Entry: <strong>{formatNumberWithDots(trade.entry_price, 5)}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Exit: <strong>{formatNumberWithDots(trade.exit_price, 5)}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              SL: <strong>{formatNumberWithDots(trade.stop_loss, 5)}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              TP: <strong>{formatNumberWithDots(trade.take_profit, 5)}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Lot: <strong>{trade.lot_size}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              RR: <strong>{trade.risk_reward.toFixed(2)}</strong>
            </Typography>
          </Box>
          {trade.entry_time && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, pl: 2.5, mt: 0.5 }}>
              <Clock size={11} />
              <Typography variant="caption" color="text.secondary" fontSize={10}>
                {trade.entry_time}
              </Typography>
            </Box>
          )}
        </Box>

        <Divider sx={{ mb: 1.5 }} />

        {/* SMC Context */}
        <Box sx={{ mb: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
            <Target size={14} />
            <Typography variant="caption" color="text.secondary" fontWeight={600}>
              SMC Context
            </Typography>
          </Box>
          <Box sx={{ pl: 2.5 }}>
            {hasSmcData ? (
              <Typography variant="body2" sx={{ color: "primary.main", fontWeight: 500 }}>
                {buildSmcNarrative(meta)}
              </Typography>
            ) : (
              <Typography variant="caption" color="text.secondary" fontStyle="italic">
                No SMC context available
              </Typography>
            )}
          </Box>
        </Box>

        <Divider sx={{ mb: 1.5 }} />

        {/* ML Insights */}
        <Box sx={{ mb: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
            <Brain size={14} />
            <Typography variant="caption" color="text.secondary" fontWeight={600}>
              ML Insights
            </Typography>
          </Box>
          <Box sx={{ pl: 2.5 }}>
            {hasMlData ? (
              <>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ minWidth: 75 }}>
                    Confidence
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={(meta.ml_confidence ?? 0) * 100}
                    sx={{
                      flex: 1,
                      height: 6,
                      borderRadius: 3,
                      bgcolor: "rgba(148,163,184,0.15)",
                      "& .MuiLinearProgress-bar": {
                        bgcolor: (meta.ml_confidence ?? 0) >= 0.85 ? "success.main" : "warning.main",
                      },
                    }}
                  />
                  <Typography variant="caption" fontWeight={700} sx={{ minWidth: 36, textAlign: "right" }}>
                    {((meta.ml_confidence ?? 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                {meta.entropy !== null && meta.entropy !== undefined && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                    <Activity size={11} />
                    <Typography variant="caption" color="text.secondary">
                      Entropy: <strong>{meta.entropy.toFixed(2)}</strong>
                      {meta.entropy_zscore !== null && meta.entropy_zscore !== undefined && (
                        <> (Z: {meta.entropy_zscore.toFixed(2)})</>
                      )}
                    </Typography>
                  </Box>
                )}
              </>
            ) : (
              <Typography variant="caption" color="text.secondary" fontStyle="italic">
                No ML model used
              </Typography>
            )}
          </Box>
        </Box>

        <Divider sx={{ mb: 1.5 }} />

        {/* Risk Management */}
        <Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
            <Shield size={14} />
            <Typography variant="caption" color="text.secondary" fontWeight={600}>
              Risk Management
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1, pl: 2.5 }}>
            <Chip
              icon={isProfit ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              label={`Risk: ${trade.effective_risk.toFixed(1)}%`}
              size="small"
              variant="outlined"
              sx={{ height: 24, fontSize: 11 }}
            />
            <Chip
              label={`RR: ${trade.risk_reward.toFixed(2)}`}
              size="small"
              variant="outlined"
              color={trade.risk_reward >= 1.5 ? "success" : "default"}
              sx={{ height: 24, fontSize: 11 }}
            />
            <Chip
              label={`Commission: $${formatNumberWithDots(trade.commission, 2)}`}
              size="small"
              variant="outlined"
              sx={{ height: 24, fontSize: 11 }}
            />
          </Box>
        </Box>

        {/* Trade counter */}
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", textAlign: "right", mt: 1.5, fontSize: 10 }}
        >
          Trade {index + 1} of {total}
        </Typography>
      </CardContent>
    </Card>
  );
}
