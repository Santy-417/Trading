"use client";

import { Box, Chip, Divider, LinearProgress, Typography } from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Brain,
  Zap,
  Clock,
  Check,
  X,
  Waves,
} from "lucide-react";
import type { SignalMetadata } from "@/types";

interface DecisionViewerProps {
  metadata: SignalMetadata | null;
}

// ── Feature display config ──────────────────────────────────────────────────
const FEATURE_LABELS: Record<
  Exclude<keyof SignalMetadata["features"], "entropy_zscore">,
  string
> = {
  swept_pdh: "PDH Swept",
  swept_pdl: "PDL Swept",
  daily_bias_bullish: "Bullish Bias D1",
  daily_bias_bearish: "Bearish Bias D1",
  is_ny_session: "NY Session",
  fractal_break_high: "Fractal Break High",
  fractal_break_low: "Fractal Break Low",
};

const FEATURE_ORDER: Array<keyof SignalMetadata["features"]> = [
  "swept_pdh",
  "swept_pdl",
  "daily_bias_bullish",
  "daily_bias_bearish",
  "is_ny_session",
  "entropy_zscore",
  "fractal_break_high",
  "fractal_break_low",
];

const SESSION_LABELS: Record<SignalMetadata["session"], string> = {
  london: "London",
  ny: "New York",
  overlap: "London / NY Overlap",
};

// ── Empty state ──────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 1,
        py: 3,
        borderRadius: 2,
        border: "1px dashed rgba(148,163,184,0.12)",
        bgcolor: "rgba(148,163,184,0.03)",
      }}
    >
      <Zap size={20} style={{ color: "#334155" }} />
      <Typography sx={{ fontSize: 12, color: "#475569", fontStyle: "italic" }}>
        Sin datos de señal
      </Typography>
      <Typography sx={{ fontSize: 10, color: "#334155" }}>
        Solo disponible para operaciones del bot
      </Typography>
    </Box>
  );
}

// ── Bias indicator ───────────────────────────────────────────────────────────
function BiasIndicator({ bias }: { bias: SignalMetadata["bias_d1"] }) {
  const config = {
    bullish: { Icon: TrendingUp, color: "#22c55e", label: "Bullish" },
    bearish: { Icon: TrendingDown, color: "#ef4444", label: "Bearish" },
    neutral: { Icon: Minus, color: "#f59e0b", label: "Neutral (Doji)" },
  }[bias];

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
      <config.Icon size={14} style={{ color: config.color }} />
      <Typography sx={{ fontSize: 12, fontWeight: 600, color: config.color }}>
        {config.label}
      </Typography>
    </Box>
  );
}

// ── Feature row ──────────────────────────────────────────────────────────────
function FeatureRow({
  label,
  value,
}: {
  label: string;
  value: boolean | number;
}) {
  // Entropy zscore: numeric, color by threshold
  if (typeof value === "number") {
    const isOk = value <= 1.5;
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
        <Waves size={11} style={{ color: isOk ? "#22c55e" : "#ef4444", flexShrink: 0 }} />
        <Typography sx={{ fontSize: 11, color: "#94a3b8", flex: 1 }}>
          Entropy Z-Score
        </Typography>
        <Typography
          sx={{
            fontSize: 11,
            fontWeight: 700,
            fontFamily: "monospace",
            color: isOk ? "#22c55e" : "#ef4444",
          }}
        >
          {value.toFixed(2)}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
      {value ? (
        <Check size={11} style={{ color: "#22c55e", flexShrink: 0 }} />
      ) : (
        <X size={11} style={{ color: "#ef4444", flexShrink: 0 }} />
      )}
      <Typography
        sx={{
          fontSize: 11,
          color: value ? "#cbd5e1" : "#64748b",
          flex: 1,
        }}
      >
        {label}
      </Typography>
    </Box>
  );
}

// ── Main component ───────────────────────────────────────────────────────────
export default function DecisionViewer({ metadata }: DecisionViewerProps) {
  if (!metadata) return <EmptyState />;

  const isChoCh = metadata.entry_type === "choch";
  const mlPct =
    metadata.ml_confidence !== null && metadata.ml_confidence !== undefined
      ? metadata.ml_confidence * 100
      : null;

  // Split features into two columns
  const leftFeatures = FEATURE_ORDER.filter((_, i) => i % 2 === 0);
  const rightFeatures = FEATURE_ORDER.filter((_, i) => i % 2 !== 0);

  return (
    <Box>
      {/* Section header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 1.5 }}>
        <Zap size={13} style={{ color: "#7c3aed" }} />
        <Typography
          sx={{
            fontSize: 10,
            fontWeight: 700,
            color: "#64748b",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
          }}
        >
          Signal Decision
        </Typography>
      </Box>

      {/* Entry type + Bias + Session row */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 1.5,
          mb: 2,
        }}
      >
        {/* Entry type */}
        <Box>
          <Typography
            sx={{
              fontSize: 9,
              color: "#475569",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              mb: 0.5,
            }}
          >
            Entry Type
          </Typography>
          <Chip
            label={isChoCh ? "ChoCh" : "Fractal Break"}
            size="small"
            sx={{
              height: 22,
              fontSize: 10,
              fontWeight: 700,
              bgcolor: isChoCh
                ? "rgba(59,130,246,0.1)"
                : "rgba(249,115,22,0.1)",
              color: isChoCh ? "#3b82f6" : "#f97316",
              border: `1px solid ${isChoCh ? "rgba(59,130,246,0.2)" : "rgba(249,115,22,0.2)"}`,
            }}
          />
        </Box>

        {/* D1 Bias */}
        <Box>
          <Typography
            sx={{
              fontSize: 9,
              color: "#475569",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              mb: 0.5,
            }}
          >
            D1 Bias
          </Typography>
          <BiasIndicator bias={metadata.bias_d1} />
        </Box>

        {/* Session */}
        <Box>
          <Typography
            sx={{
              fontSize: 9,
              color: "#475569",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              mb: 0.5,
            }}
          >
            Session
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Clock size={11} style={{ color: "#8b5cf6" }} />
            <Typography sx={{ fontSize: 11, fontWeight: 600, color: "#c4b5fd" }}>
              {SESSION_LABELS[metadata.session]}
            </Typography>
          </Box>
        </Box>
      </Box>

      <Divider sx={{ borderColor: "rgba(148,163,184,0.07)", mb: 1.5 }} />

      {/* Features checklist */}
      <Typography
        sx={{
          fontSize: 9,
          color: "#475569",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          mb: 1,
        }}
      >
        Features
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          columnGap: 2,
          rowGap: 0.75,
          mb: 2,
        }}
      >
        {/* Left column */}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
          {leftFeatures.map((key) => (
            <FeatureRow
              key={key}
              label={key !== "entropy_zscore" ? FEATURE_LABELS[key as keyof typeof FEATURE_LABELS] : ""}
              value={metadata.features[key]}
            />
          ))}
        </Box>
        {/* Right column */}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
          {rightFeatures.map((key) => (
            <FeatureRow
              key={key}
              label={key !== "entropy_zscore" ? FEATURE_LABELS[key as keyof typeof FEATURE_LABELS] : ""}
              value={metadata.features[key]}
            />
          ))}
        </Box>
      </Box>

      {/* ML Confidence */}
      {mlPct !== null && (
        <>
          <Divider sx={{ borderColor: "rgba(148,163,184,0.07)", mb: 1.5 }} />
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.75 }}>
            <Brain size={12} style={{ color: "#8b5cf6" }} />
            <Typography
              sx={{
                fontSize: 9,
                color: "#475569",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              ML Confidence
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <LinearProgress
              variant="determinate"
              value={mlPct}
              sx={{
                flex: 1,
                height: 5,
                borderRadius: 3,
                bgcolor: "rgba(148,163,184,0.1)",
                "& .MuiLinearProgress-bar": {
                  borderRadius: 3,
                  bgcolor:
                    mlPct >= 85
                      ? "#22c55e"
                      : mlPct >= 65
                      ? "#3b82f6"
                      : "#f59e0b",
                },
              }}
            />
            <Typography
              sx={{
                fontSize: 12,
                fontWeight: 700,
                fontFamily: "monospace",
                color:
                  mlPct >= 85
                    ? "#22c55e"
                    : mlPct >= 65
                    ? "#3b82f6"
                    : "#f59e0b",
                minWidth: 36,
                textAlign: "right",
              }}
            >
              {mlPct.toFixed(0)}%
            </Typography>
          </Box>
        </>
      )}

      {/* Sweep magnitude */}
      {metadata.sweep_magnitude_pips !== null &&
        metadata.sweep_magnitude_pips !== undefined && (
          <Box sx={{ mt: 1.5, display: "flex", alignItems: "center", gap: 0.75 }}>
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                bgcolor: "#8b5cf6",
                flexShrink: 0,
              }}
            />
            <Typography sx={{ fontSize: 11, color: "#94a3b8" }}>
              Sweep magnitude:{" "}
              <Typography
                component="span"
                sx={{ fontSize: 11, fontWeight: 700, color: "#c4b5fd", fontFamily: "monospace" }}
              >
                {metadata.sweep_magnitude_pips.toFixed(1)} pips
              </Typography>
            </Typography>
          </Box>
        )}
    </Box>
  );
}
