"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, Card, CardContent, Chip, Skeleton, Tooltip, Typography } from "@mui/material";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Clock,
  Pause,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";
import api from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface SignalStatus {
  bot_state: "ACTIVO" | "DETENIDO" | "ERROR";
  is_running: boolean;
  block_reason: string | null;
  block_detail: string | null;
  daily_bias: "BULLISH" | "BEARISH" | "NEUTRAL" | null;
  sweep_detected: boolean;
  last_trade: {
    symbol: string;
    direction: "BUY" | "SELL";
    volume: number;
    ticket: number;
    entry_price: number;
    stop_loss: number;
    take_profit: number;
    executed_at: string;
  } | null;
  current_session: "london" | "ny" | "overlap" | "closed";
  ny_open_minutes: number | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCountdown(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h === 0) return `${m}m`;
  return `${h}h ${m}m`;
}

function timeAgo(isoDate: string): string {
  const diff = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000);
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`;
  return `${Math.floor(diff / 86400)}d`;
}

const BLOCK_LABELS: Record<string, string> = {
  sin_bias_d1:      "Sin sesgo D1",
  sin_sweep:        "Sin sweep detectado",
  bias_neutral:     "Bias D1 neutral",
  fuera_sesion_ny:  "Fuera de sesión NY",
  entropia_alta:    "Entropía alta",
  sin_choch:        "Sin ChoCh / Fractal",
  confianza_ml_baja:"ML confidence baja",
  rr_insuficiente:  "R/R insuficiente",
};

// ── Session config ────────────────────────────────────────────────────────────

const SESSION_CONFIG = {
  london:  { label: "London",   color: "#f59e0b", bg: "rgba(245,158,11,0.08)"  },
  ny:      { label: "New York", color: "#22c55e", bg: "rgba(34,197,94,0.08)"   },
  overlap: { label: "Overlap",  color: "#3b82f6", bg: "rgba(59,130,246,0.08)"  },
  closed:  { label: "Cerrado",  color: "#64748b", bg: "rgba(100,116,139,0.08)" },
};

// ── Display state derivation ──────────────────────────────────────────────────

type DisplayState = "active" | "waiting" | "blocked";

function deriveDisplayState(status: SignalStatus): DisplayState {
  if (status.bot_state === "ERROR")    return "blocked";
  if (status.bot_state === "DETENIDO") return "waiting";
  // ACTIVO
  if (status.block_reason) return "waiting";
  return "active";
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function LastSignalBadge() {
  const [signalStatus, setSignalStatus] = useState<SignalStatus | null>(null);
  const [loading, setLoading] = useState(true);
  // Live countdown — updated every second client-side
  const [nyMinsLive, setNyMinsLive] = useState<number | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get<SignalStatus>("/bot/signal-status");
      setSignalStatus(res.data);
      setNyMinsLive(res.data.ny_open_minutes);
    } catch {
      // silent — badge degrades gracefully
    } finally {
      setLoading(false);
    }
  }, []);

  // 30s polling
  useEffect(() => {
    fetchStatus();
    const poll = setInterval(fetchStatus, 30_000);
    return () => clearInterval(poll);
  }, [fetchStatus]);

  // 1s countdown tick
  useEffect(() => {
    const tick = setInterval(() => {
      setNyMinsLive((prev) => {
        if (prev === null || prev <= 0) return null;
        return prev - 1 / 60; // decrement by 1 second
      });
    }, 1_000);
    return () => clearInterval(tick);
  }, []);

  if (loading) {
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
          <Skeleton variant="rounded" width="100%" height={52} />
        </CardContent>
      </Card>
    );
  }

  if (!signalStatus) return null;

  const displayState = deriveDisplayState(signalStatus);
  const sessionCfg = SESSION_CONFIG[signalStatus.current_session];
  const nyMinsDisplay = nyMinsLive !== null ? Math.round(nyMinsLive) : null;

  const stateConfig = {
    active:  { label: "ACTIVO",    color: "#22c55e", bg: "rgba(34,197,94,0.08)",   Icon: Wifi,          dot: "#22c55e" },
    waiting: { label: "EN ESPERA", color: "#f59e0b", bg: "rgba(245,158,11,0.08)",  Icon: Pause,         dot: "#f59e0b" },
    blocked: { label: "BLOQUEADO", color: "#ef4444", bg: "rgba(239,68,68,0.08)",   Icon: AlertTriangle, dot: "#ef4444" },
  }[displayState];

  const { block_reason, block_detail, last_trade } = signalStatus;
  const blockLabel = block_reason ? (BLOCK_LABELS[block_reason] ?? block_reason) : null;

  return (
    <Card
      sx={{
        mb: 2,
        border: "1px solid",
        borderColor: `${stateConfig.dot}22`,
        bgcolor: "background.paper",
      }}
    >
      <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: { xs: 1.5, md: 2.5 },
          }}
        >
          {/* ── Bot state chip ── */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Box sx={{ position: "relative", display: "flex", alignItems: "center" }}>
              {displayState === "active" && (
                <Box
                  sx={{
                    position: "absolute",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: stateConfig.dot,
                    top: -1,
                    left: -1,
                    "@keyframes pulse": {
                      "0%,100%": { opacity: 1, transform: "scale(1)" },
                      "50%":     { opacity: 0.5, transform: "scale(1.8)" },
                    },
                    animation: "pulse 2s ease-in-out infinite",
                  }}
                />
              )}
              <stateConfig.Icon size={14} style={{ color: stateConfig.color }} />
            </Box>
            <Chip
              label={stateConfig.label}
              size="small"
              sx={{
                height: 22,
                fontSize: 10,
                fontWeight: 800,
                letterSpacing: "0.04em",
                bgcolor: stateConfig.bg,
                color: stateConfig.color,
                border: `1px solid ${stateConfig.dot}33`,
              }}
            />
            {/* Daily bias pill */}
            {signalStatus.daily_bias && (
              <Chip
                label={signalStatus.daily_bias}
                size="small"
                sx={{
                  height: 18,
                  fontSize: 9,
                  fontWeight: 700,
                  bgcolor:
                    signalStatus.daily_bias === "BULLISH"
                      ? "rgba(34,197,94,0.08)"
                      : signalStatus.daily_bias === "BEARISH"
                      ? "rgba(239,68,68,0.08)"
                      : "rgba(100,116,139,0.08)",
                  color:
                    signalStatus.daily_bias === "BULLISH"
                      ? "#22c55e"
                      : signalStatus.daily_bias === "BEARISH"
                      ? "#ef4444"
                      : "#64748b",
                }}
              />
            )}
          </Box>

          <Box sx={{ width: "1px", height: 28, bgcolor: "rgba(148,163,184,0.1)", display: { xs: "none", md: "block" } }} />

          {/* ── Block reason ── */}
          {blockLabel && (
            <Tooltip title={block_detail ?? blockLabel} arrow>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, cursor: "help" }}>
                <WifiOff size={12} style={{ color: "#ef4444" }} />
                <Typography sx={{ fontSize: 11, color: "#ef4444", fontWeight: 600 }}>
                  {blockLabel}
                </Typography>
              </Box>
            </Tooltip>
          )}

          {/* ── Session ── */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
            <Activity size={12} style={{ color: sessionCfg.color }} />
            <Typography sx={{ fontSize: 11, color: "#64748b" }}>Sesión:</Typography>
            <Chip
              label={sessionCfg.label}
              size="small"
              sx={{
                height: 18,
                fontSize: 9,
                fontWeight: 700,
                bgcolor: sessionCfg.bg,
                color: sessionCfg.color,
                border: `1px solid ${sessionCfg.color}33`,
              }}
            />
          </Box>

          {/* ── NY countdown / open indicator ── */}
          {nyMinsDisplay !== null && nyMinsDisplay > 0 ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
              <Clock size={12} style={{ color: "#8b5cf6" }} />
              <Typography sx={{ fontSize: 11, color: "#64748b" }}>
                NY en:{" "}
                <Typography
                  component="span"
                  sx={{ fontSize: 11, fontWeight: 700, color: "#c4b5fd", fontFamily: "monospace" }}
                >
                  {formatCountdown(nyMinsDisplay)}
                </Typography>
              </Typography>
            </Box>
          ) : signalStatus.ny_open_minutes === null ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
              <Zap size={12} style={{ color: "#22c55e" }} />
              <Typography sx={{ fontSize: 11, color: "#22c55e", fontWeight: 600 }}>
                Ventana NY abierta
              </Typography>
            </Box>
          ) : null}

          {/* ── Last executed trade ── */}
          {last_trade && (
            <>
              <Box sx={{ width: "1px", height: 28, bgcolor: "rgba(148,163,184,0.1)", display: { xs: "none", md: "block" } }} />
              <Tooltip
                title={`Ticket #${last_trade.ticket} · Entrada: ${last_trade.entry_price} · SL: ${last_trade.stop_loss} · TP: ${last_trade.take_profit}`}
                arrow
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, cursor: "default" }}>
                  {last_trade.direction === "BUY" ? (
                    <ArrowUpRight size={13} style={{ color: "#22c55e" }} />
                  ) : (
                    <ArrowDownRight size={13} style={{ color: "#ef4444" }} />
                  )}
                  <Typography sx={{ fontSize: 11, color: "#94a3b8" }}>
                    Último:{" "}
                    <Typography
                      component="span"
                      sx={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: last_trade.direction === "BUY" ? "#22c55e" : "#ef4444",
                      }}
                    >
                      {last_trade.direction} {last_trade.symbol}
                    </Typography>
                  </Typography>
                  <Typography sx={{ fontSize: 10, color: "#475569" }}>
                    · {timeAgo(last_trade.executed_at)}
                  </Typography>
                </Box>
              </Tooltip>
            </>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
