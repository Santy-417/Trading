"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Skeleton,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { FormattedNumberInput } from "@/components/ui/formatted-number-input";
import {
  Shield,
  AlertTriangle,
  Ban,
  TrendingDown,
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  Zap,
  Settings,
} from "lucide-react";
import { motion } from "framer-motion";
import api from "@/lib/api";

interface RiskStatus {
  kill_switch_active: boolean;
  circuit_breaker: {
    drawdown_breached: boolean;
    daily_loss_breached: boolean;
    overtrading_breached: boolean;
    current_drawdown: number;
    max_drawdown_limit: number;
    daily_loss: number;
    max_daily_loss: number;
    trades_this_hour: number;
    max_trades_per_hour: number;
  };
  trading_allowed: boolean;
}

interface RiskEvent {
  id: number;
  timestamp: string;
  type: "drawdown" | "daily_loss" | "overtrading" | "kill_switch" | "recovered";
  message: string;
  severity: "critical" | "warning" | "info";
}

function CircularGauge({
  value,
  max,
  label,
  unit,
  icon: Icon,
  color,
  breached,
}: {
  value: number;
  max: number;
  label: string;
  unit: string;
  icon: React.ElementType;
  color: string;
  breached: boolean;
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const gaugeColor = breached ? "#ef4444" : pct > 75 ? "#f59e0b" : color;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <Card
      sx={{
        transition: "border-color 0.15s",
        "&:hover": { borderColor: `${gaugeColor}30` },
      }}
    >
      <CardContent sx={{ p: 2.5, textAlign: "center" }}>
        <Box sx={{ position: "relative", display: "inline-flex", mb: 2 }}>
          <svg width={128} height={128} viewBox="0 0 128 128">
            {/* Background circle */}
            <circle
              cx="64"
              cy="64"
              r={radius}
              fill="none"
              stroke="rgba(148,163,184,0.08)"
              strokeWidth="8"
            />
            {/* Progress circle */}
            <motion.circle
              cx="64"
              cy="64"
              r={radius}
              fill="none"
              stroke={gaugeColor}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: offset }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              transform="rotate(-90 64 64)"
              style={{ filter: breached ? `drop-shadow(0 0 8px ${gaugeColor}60)` : "none" }}
            />
          </svg>
          {/* Center content */}
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon size={18} style={{ color: gaugeColor, marginBottom: 4 }} />
            <Typography sx={{ fontSize: 20, fontWeight: 700, color: gaugeColor, fontFeatureSettings: '"tnum"', lineHeight: 1 }}>
              {pct.toFixed(0)}%
            </Typography>
          </Box>
        </Box>

        <Typography sx={{ fontSize: 12, fontWeight: 600, mb: 0.5 }}>
          {label}
        </Typography>
        <Typography sx={{ fontSize: 11, color: "#64748b", fontFeatureSettings: '"tnum"' }}>
          {value.toFixed(unit === "%" ? 1 : 0)}{unit} / {max}{unit}
        </Typography>

        {breached && (
          <Chip
            label="BREACHED"
            size="small"
            sx={{
              mt: 1,
              height: 18,
              fontSize: 9,
              fontWeight: 700,
              bgcolor: "rgba(239,68,68,0.1)",
              color: "#ef4444",
              border: "1px solid rgba(239,68,68,0.2)",
              letterSpacing: "0.05em",
            }}
          />
        )}
      </CardContent>
    </Card>
  );
}

export default function RiskPage() {
  const [status, setStatus] = useState<RiskStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const eventIdRef = useRef(0);
  const prevStatusRef = useRef<RiskStatus | null>(null);

  // Config values (display only — read from current risk status)
  const [maxDrawdown, setMaxDrawdown] = useState("10.0");
  const [maxDailyLoss, setMaxDailyLoss] = useState("3.0");
  const [maxTrades, setMaxTrades] = useState("10");

  const trackEvents = useCallback((current: RiskStatus) => {
    const prev = prevStatusRef.current;
    if (!prev) {
      prevStatusRef.current = current;
      return;
    }

    const newEvents: RiskEvent[] = [];

    if (!prev.circuit_breaker.drawdown_breached && current.circuit_breaker.drawdown_breached) {
      newEvents.push({ id: ++eventIdRef.current, timestamp: new Date().toISOString(), type: "drawdown", message: `Drawdown breached ${current.circuit_breaker.current_drawdown.toFixed(1)}%`, severity: "critical" });
    }
    if (!prev.circuit_breaker.daily_loss_breached && current.circuit_breaker.daily_loss_breached) {
      newEvents.push({ id: ++eventIdRef.current, timestamp: new Date().toISOString(), type: "daily_loss", message: `Daily loss limit reached ($${current.circuit_breaker.daily_loss.toFixed(2)})`, severity: "critical" });
    }
    if (!prev.circuit_breaker.overtrading_breached && current.circuit_breaker.overtrading_breached) {
      newEvents.push({ id: ++eventIdRef.current, timestamp: new Date().toISOString(), type: "overtrading", message: `Overtrading detected (${current.circuit_breaker.trades_this_hour} trades/hr)`, severity: "warning" });
    }
    if (!prev.kill_switch_active && current.kill_switch_active) {
      newEvents.push({ id: ++eventIdRef.current, timestamp: new Date().toISOString(), type: "kill_switch", message: "Kill switch activated", severity: "critical" });
    }
    if (prev.kill_switch_active && !current.kill_switch_active) {
      newEvents.push({ id: ++eventIdRef.current, timestamp: new Date().toISOString(), type: "recovered", message: "Kill switch deactivated", severity: "info" });
    }

    if (newEvents.length > 0) {
      setEvents((prev) => [...newEvents, ...prev].slice(0, 50));
    }

    prevStatusRef.current = current;
  }, []);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const { data } = await api.get("/bot/status");
        setFetchError(null);
        if (data.risk_status) {
          setStatus(data.risk_status);
          trackEvents(data.risk_status);

          // Sync config values from current limits
          const cb = data.risk_status.circuit_breaker;
          if (cb) {
            setMaxDrawdown(cb.max_drawdown_limit.toString());
            setMaxDailyLoss(cb.max_daily_loss.toString());
            setMaxTrades(cb.max_trades_per_hour.toString());
          }
        }
      } catch {
        setFetchError("Backend unreachable — risk data unavailable");
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [trackEvents]);

  const cb = status?.circuit_breaker;

  const eventIcon = (type: string) => {
    switch (type) {
      case "drawdown": return <TrendingDown size={14} />;
      case "daily_loss": return <AlertTriangle size={14} />;
      case "overtrading": return <Activity size={14} />;
      case "kill_switch": return <Ban size={14} />;
      case "recovered": return <CheckCircle size={14} />;
      default: return <Zap size={14} />;
    }
  };

  const severityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "#ef4444";
      case "warning": return "#f59e0b";
      default: return "#22c55e";
    }
  };

  return (
    <Box>
      {/* Page header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            bgcolor: "rgba(245, 158, 11, 0.1)",
            border: "1px solid rgba(245, 158, 11, 0.15)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Shield size={22} style={{ color: "#f59e0b" }} />
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.2, fontSize: 20 }}>
            Risk Management
          </Typography>
          <Typography variant="caption" sx={{ color: "#64748b", fontSize: 11 }}>
            Real-time risk monitoring
          </Typography>
        </Box>
      </Box>

      {/* Status Banner */}
      {loading ? (
        <Skeleton variant="rectangular" height={48} sx={{ borderRadius: 2, mb: 3 }} />
      ) : (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              p: 2,
              mb: 3,
              borderRadius: 2,
              bgcolor: fetchError
                ? "rgba(245,158,11,0.06)"
                : status?.trading_allowed
                ? "rgba(34,197,94,0.06)"
                : "rgba(239,68,68,0.06)",
              border: `1px solid ${fetchError
                ? "rgba(245,158,11,0.2)"
                : status?.trading_allowed
                ? "rgba(34,197,94,0.15)"
                : "rgba(239,68,68,0.15)"}`,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              {fetchError ? (
                <AlertTriangle size={20} style={{ color: "#f59e0b" }} />
              ) : status?.trading_allowed ? (
                <CheckCircle size={20} style={{ color: "#22c55e" }} />
              ) : (
                <XCircle size={20} style={{ color: "#ef4444" }} />
              )}
              <Box>
                <Typography sx={{ fontSize: 14, fontWeight: 600, color: fetchError ? "#f59e0b" : status?.trading_allowed ? "#22c55e" : "#ef4444" }}>
                  {fetchError ? "Backend Unreachable" : status?.trading_allowed ? "Trading Active" : "Trading Halted"}
                </Typography>
                {fetchError && (
                  <Typography sx={{ fontSize: 11, color: "#64748b", mt: 0.25 }}>
                    {fetchError}
                  </Typography>
                )}
              </Box>
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              {status?.kill_switch_active && !fetchError && (
                <Chip
                  icon={<Ban size={12} style={{ color: "#ef4444" }} />}
                  label="Kill Switch ON"
                  size="small"
                  sx={{
                    height: 24,
                    fontSize: 10,
                    fontWeight: 600,
                    bgcolor: "rgba(239,68,68,0.08)",
                    color: "#ef4444",
                    border: "1px solid rgba(239,68,68,0.2)",
                    "& .MuiChip-icon": { ml: 0.3 },
                  }}
                />
              )}
              <Typography sx={{ fontSize: 10, color: "#64748b" }}>
                {fetchError ? "Retrying..." : "Updates every 5s"}
              </Typography>
            </Box>
          </Box>
        </motion.div>
      )}

      {/* Circular Gauges */}
      {loading ? (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {[1, 2, 3].map((i) => (
            <Grid size={{ xs: 12, md: 4 }} key={i}>
              <Skeleton variant="rectangular" height={240} sx={{ borderRadius: 2 }} />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, md: 4 }}>
            <CircularGauge
              value={cb?.current_drawdown ?? 0}
              max={cb?.max_drawdown_limit ?? 10}
              label="Max Drawdown"
              unit="%"
              icon={TrendingDown}
              color="#f59e0b"
              breached={cb?.drawdown_breached ?? false}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <CircularGauge
              value={cb?.daily_loss ?? 0}
              max={cb?.max_daily_loss ?? 300}
              label="Daily Loss"
              unit=""
              icon={AlertTriangle}
              color="#7c3aed"
              breached={cb?.daily_loss_breached ?? false}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <CircularGauge
              value={cb?.trades_this_hour ?? 0}
              max={cb?.max_trades_per_hour ?? 10}
              label="Trades / Hour"
              unit=""
              icon={Activity}
              color="#8b5cf6"
              breached={cb?.overtrading_breached ?? false}
            />
          </Grid>
        </Grid>
      )}

      <Grid container spacing={2.5}>
        {/* Event Timeline */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
                <Clock size={16} style={{ color: "#64748b" }} />
                <Typography sx={{ fontSize: 15, fontWeight: 600 }}>
                  Risk Events
                </Typography>
                {events.length > 0 && (
                  <Chip
                    label={events.length}
                    size="small"
                    sx={{ height: 18, fontSize: 9, fontWeight: 600, bgcolor: "rgba(148,163,184,0.06)", color: "#94a3b8" }}
                  />
                )}
              </Box>

              {events.length === 0 ? (
                <Box sx={{ textAlign: "center", py: 5 }}>
                  <Shield size={36} style={{ color: "#334155", marginBottom: 12 }} />
                  <Typography sx={{ color: "#64748b", fontSize: 13 }}>
                    No risk events this session
                  </Typography>
                  <Typography sx={{ color: "#475569", fontSize: 11, mt: 0.5 }}>
                    Events will appear when circuit breaker thresholds are breached
                  </Typography>
                </Box>
              ) : (
                <Box
                  sx={{
                    maxHeight: 360,
                    overflowY: "auto",
                    "&::-webkit-scrollbar": { width: 4 },
                    "&::-webkit-scrollbar-thumb": { bgcolor: "rgba(148,163,184,0.15)", borderRadius: 2 },
                  }}
                >
                  {events.map((event) => (
                    <Box
                      key={event.id}
                      sx={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 1.5,
                        py: 1.5,
                        borderBottom: "1px solid rgba(148,163,184,0.06)",
                        "&:last-child": { borderBottom: "none" },
                      }}
                    >
                      <Box
                        sx={{
                          width: 28,
                          height: 28,
                          borderRadius: 1.5,
                          bgcolor: `${severityColor(event.severity)}10`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                          color: severityColor(event.severity),
                          mt: 0.25,
                        }}
                      >
                        {eventIcon(event.type)}
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography sx={{ fontSize: 12, fontWeight: 500 }}>
                          {event.message}
                        </Typography>
                        <Typography sx={{ fontSize: 10, color: "#475569", mt: 0.25 }}>
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </Typography>
                      </Box>
                      <Chip
                        label={event.severity}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: 9,
                          fontWeight: 600,
                          bgcolor: `${severityColor(event.severity)}10`,
                          color: severityColor(event.severity),
                          textTransform: "uppercase",
                          letterSpacing: "0.03em",
                        }}
                      />
                    </Box>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Configuration */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2.5 }}>
                <Settings size={16} style={{ color: "#64748b" }} />
                <Typography sx={{ fontSize: 15, fontWeight: 600 }}>
                  Limit Configuration
                </Typography>
              </Box>

              <Typography sx={{ fontSize: 10, color: "#64748b", mb: 2, lineHeight: 1.5 }}>
                Current risk limits from the bot configuration. These values are read-only and reflect the active risk engine thresholds.
              </Typography>

              <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
                <Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <TrendingDown size={14} style={{ color: "#f59e0b" }} />
                    <Typography sx={{ fontSize: 12, fontWeight: 600 }}>Max Drawdown</Typography>
                  </Box>
                  <FormattedNumberInput
                    size="small"
                    label="Percentage (%)"
                    value={maxDrawdown}
                    onChange={setMaxDrawdown}
                    decimals={1}
                    fullWidth
                    disabled
                  />
                </Box>

                <Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <AlertTriangle size={14} style={{ color: "#7c3aed" }} />
                    <Typography sx={{ fontSize: 12, fontWeight: 600 }}>Max Daily Loss</Typography>
                  </Box>
                  <FormattedNumberInput
                    size="small"
                    label="Percentage (%)"
                    value={maxDailyLoss}
                    onChange={setMaxDailyLoss}
                    decimals={1}
                    fullWidth
                    disabled
                  />
                </Box>

                <Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <Activity size={14} style={{ color: "#8b5cf6" }} />
                    <Typography sx={{ fontSize: 12, fontWeight: 600 }}>Max Trades / Hour</Typography>
                  </Box>
                  <FormattedNumberInput
                    size="small"
                    label="Count"
                    value={maxTrades}
                    onChange={setMaxTrades}
                    decimals={0}
                    fullWidth
                    disabled
                  />
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
