"use client";

/**
 * Settings Page — Bot Configuration
 *
 * ─── SPEC para Santiago ──────────────────────────────────────────────────────
 * Se necesitan 2 endpoints nuevos en backend/app/routers/bot.py:
 *
 * 1) GET /api/v1/bot/config
 *    Retorna la configuración activa de bot_config (primera fila is_active=true,
 *    o la última creada si no hay ninguna activa).
 *    Response:
 *    {
 *      "id": "uuid",
 *      "name": "default",
 *      "strategy": "bias",
 *      "symbols": ["EURUSD", "XAUUSD"],
 *      "timeframe": "H1",
 *      "risk_per_trade": 1.0,
 *      "lot_mode": "percent_risk",    // "fixed" | "percent_risk" | "dynamic"
 *      "fixed_lot": 0.01,
 *      "max_trades_per_hour": 10,
 *      "strategy_params": {
 *        "entropy_threshold": 3.1,
 *        "choch_lookback": 60,
 *        "min_rr": 1.3,
 *        "sl_pips_base": 10.0,
 *        "sweep_tolerance_pips": 3.0
 *      },
 *      "is_active": false,
 *      "error_state": false,
 *      "crash_count": 0,
 *      "last_heartbeat": "2026-04-08T20:00:00Z" | null
 *    }
 *
 * 2) PATCH /api/v1/bot/config
 *    Actualiza solo los campos enviados. El bot NO necesita reiniciarse
 *    para campos de riesgo; sí necesita reinicio para strategy/symbols/timeframe.
 *    Body (todos opcionales):
 *    {
 *      "strategy": "bias",
 *      "symbols": ["EURUSD", "XAUUSD"],
 *      "timeframe": "H1",
 *      "risk_per_trade": 1.5,
 *      "lot_mode": "percent_risk",
 *      "fixed_lot": 0.01,
 *      "max_trades_per_hour": 10,
 *      "strategy_params": { ... }
 *    }
 *    Response: igual que GET /api/v1/bot/config (config actualizada)
 *
 * Implementación sugerida:
 *   - Nuevo BotConfigResponse + BotConfigUpdateRequest en schemas/bot.py
 *   - Service que hace SELECT WHERE is_active=True LIMIT 1, luego UPDATE
 *   - Si no existe fila activa, crear una nueva con los defaults
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  Skeleton,
  Snackbar,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  AlertTriangle,
  Bot,
  ChevronDown,
  ChevronRight,
  Info,
  RotateCcw,
  Save,
  Settings,
  Shield,
  Zap,
} from "lucide-react";
import api from "@/lib/api";
import type { BotStatusResponse } from "@/types";

// ── Constants ─────────────────────────────────────────────────────────────────
const ALL_SYMBOLS = ["EURUSD", "XAUUSD", "DXY", "USDCAD", "GBPUSD", "AUDCAD", "EURJPY", "USDJPY", "EURGBP"];
const STRATEGIES  = [
  { value: "bias",      label: "Bias V1 (Smart Money Concepts)" },
  { value: "fibonacci", label: "Fibonacci" },
  { value: "ict",       label: "ICT" },
  { value: "hybrid_ml", label: "Hybrid ML" },
  { value: "manual",    label: "Manual" },
];
const TIMEFRAMES  = ["M5", "M15", "M30", "H1", "H4", "D1"];
const LOT_MODES   = [
  { value: "percent_risk", label: "% del balance (percent_risk)" },
  { value: "fixed",        label: "Lote fijo (fixed)" },
  { value: "dynamic",      label: "Dinámico ML (dynamic)" },
];

// ── Types ─────────────────────────────────────────────────────────────────────
interface BotConfig {
  id?: string;
  name?: string;
  strategy: string;
  symbols: string[];
  timeframe: string;
  risk_per_trade: number;
  lot_mode: string;
  fixed_lot: number;
  max_trades_per_hour: number;
  strategy_params: StrategyParams;
  is_active?: boolean;
  error_state?: boolean;
  crash_count?: number;
  last_heartbeat?: string | null;
}

interface StrategyParams {
  entropy_threshold: number;
  choch_lookback: number;
  min_rr: number;
  sl_pips_base: number;
  sweep_tolerance_pips: number;
}

const DEFAULT_CONFIG: BotConfig = {
  strategy:           "bias",
  symbols:            ["EURUSD", "XAUUSD"],
  timeframe:          "H1",
  risk_per_trade:     1.0,
  lot_mode:           "percent_risk",
  fixed_lot:          0.01,
  max_trades_per_hour:10,
  strategy_params: {
    entropy_threshold:    3.1,
    choch_lookback:       60,
    min_rr:               1.3,
    sl_pips_base:         10.0,
    sweep_tolerance_pips: 3.0,
  },
};

// ── Helper: detect changed fields (shallow + strategy_params) ─────────────────
function getDirtyFields(original: BotConfig, current: BotConfig): Partial<BotConfig> {
  const patch: Partial<BotConfig> = {};

  const topFields: (keyof BotConfig)[] = [
    "strategy", "timeframe", "risk_per_trade", "lot_mode",
    "fixed_lot", "max_trades_per_hour",
  ];
  for (const key of topFields) {
    if (original[key] !== current[key]) {
      (patch as Record<string, unknown>)[key] = current[key];
    }
  }

  // symbols: compare as sorted joined strings
  if ([...original.symbols].sort().join() !== [...current.symbols].sort().join()) {
    patch.symbols = current.symbols;
  }

  // strategy_params: compare each field
  const spOrig = original.strategy_params;
  const spCurr = current.strategy_params;
  const spKeys = Object.keys(spCurr) as (keyof StrategyParams)[];
  const changedSp = spKeys.some((k) => spOrig[k] !== spCurr[k]);
  if (changedSp) patch.strategy_params = current.strategy_params;

  return patch;
}

// ── Section collapse helper ───────────────────────────────────────────────────
function Section({
  icon: Icon,
  title,
  children,
  defaultOpen = true,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Box>
      <Box
        onClick={() => setOpen((o) => !o)}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          cursor: "pointer",
          py: 1,
          "&:hover": { opacity: 0.75 },
        }}
      >
        <Icon size={14} style={{ color: "#8b5cf6" }} />
        <Typography
          sx={{
            fontSize: 11,
            fontWeight: 700,
            color: "#64748b",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            flex: 1,
          }}
        >
          {title}
        </Typography>
        {open ? (
          <ChevronDown size={14} style={{ color: "#475569" }} />
        ) : (
          <ChevronRight size={14} style={{ color: "#475569" }} />
        )}
      </Box>
      {open && <Box sx={{ pl: 0.5, pb: 1 }}>{children}</Box>}
    </Box>
  );
}

// ── Row layout for a single setting ──────────────────────────────────────────
function SettingRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 2,
        py: 0.75,
      }}
    >
      <Box sx={{ flex: 1 }}>
        <Typography variant="body2" color="text.secondary" sx={{ fontSize: 13 }}>
          {label}
        </Typography>
        {hint && (
          <Typography sx={{ fontSize: 10, color: "#475569", mt: 0.15 }}>{hint}</Typography>
        )}
      </Box>
      <Box sx={{ flex: "0 0 auto", minWidth: 180, display: "flex", justifyContent: "flex-end" }}>
        {children}
      </Box>
    </Box>
  );
}

// ── Inline number input ───────────────────────────────────────────────────────
function NumInput({
  value,
  onChange,
  min,
  max,
  step = 1,
  width = 100,
}: {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  width?: number;
}) {
  return (
    <TextField
      type="number"
      size="small"
      value={value}
      onChange={(e) => {
        const v = parseFloat(e.target.value);
        if (!isNaN(v) && v >= min && v <= max) onChange(v);
      }}
      inputProps={{ min, max, step }}
      sx={{
        width,
        "& .MuiInputBase-input": { fontSize: 13, py: 0.6, textAlign: "right" },
        "& .MuiOutlinedInput-root fieldset": { borderColor: "rgba(148,163,184,0.2)" },
        "& input[type=number]::-webkit-inner-spin-button": { opacity: 0.4 },
      }}
    />
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function SettingsPage() {
  const [config, setConfig] = useState<BotConfig>(DEFAULT_CONFIG);
  const originalRef = useRef<BotConfig>(DEFAULT_CONFIG);
  const [loading, setLoading]       = useState(true);
  const [saving, setSaving]         = useState(false);
  const [endpointMissing, setEndpointMissing] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [snackbar, setSnackbar]     = useState<{ open: boolean; message: string; severity: "success" | "error" }>({
    open: false, message: "", severity: "success",
  });

  // ── Load config ─────────────────────────────────────────────────────────────
  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<BotConfig>("/bot/config");
      const loaded: BotConfig = {
        ...DEFAULT_CONFIG,
        ...data,
        strategy_params: { ...DEFAULT_CONFIG.strategy_params, ...(data.strategy_params ?? {}) },
      };
      setConfig(loaded);
      originalRef.current = structuredClone(loaded);
      setEndpointMissing(false);
    } catch (err: unknown) {
      // Endpoint not yet implemented — fall back to /bot/status for partial data
      const status = err as { response?: { status?: number } };
      if (status?.response?.status === 404 || status?.response?.status === 422) {
        setEndpointMissing(true);
        try {
          const { data: statusData } = await api.get<BotStatusResponse>("/bot/status");
          const partial: BotConfig = {
            ...DEFAULT_CONFIG,
            strategy:   statusData.strategy  ?? DEFAULT_CONFIG.strategy,
            symbols:    statusData.symbols?.length ? statusData.symbols : DEFAULT_CONFIG.symbols,
            timeframe:  statusData.timeframe ?? DEFAULT_CONFIG.timeframe,
            risk_per_trade: statusData.risk_per_trade ?? DEFAULT_CONFIG.risk_per_trade,
            lot_mode:   statusData.lot_mode  ?? DEFAULT_CONFIG.lot_mode,
          };
          setConfig(partial);
          originalRef.current = structuredClone(partial);
        } catch {
          /* keep defaults */
        }
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadConfig(); }, [loadConfig]);

  // ── Update helpers ───────────────────────────────────────────────────────────
  const set = <K extends keyof BotConfig>(key: K, value: BotConfig[K]) =>
    setConfig((prev) => ({ ...prev, [key]: value }));

  const setSp = <K extends keyof StrategyParams>(key: K, value: number) =>
    setConfig((prev) => ({
      ...prev,
      strategy_params: { ...prev.strategy_params, [key]: value },
    }));

  const toggleSymbol = (sym: string) =>
    setConfig((prev) => ({
      ...prev,
      symbols: prev.symbols.includes(sym)
        ? prev.symbols.filter((s) => s !== sym)
        : [...prev.symbols, sym],
    }));

  // ── Save ─────────────────────────────────────────────────────────────────────
  const handleSave = async () => {
    setConfirmOpen(false);
    setSaving(true);
    try {
      const patch = getDirtyFields(originalRef.current, config);
      if (Object.keys(patch).length === 0) {
        setSnackbar({ open: true, message: "Sin cambios para guardar", severity: "success" });
        return;
      }
      const { data } = await api.patch<BotConfig>("/bot/config", patch);
      const saved: BotConfig = {
        ...DEFAULT_CONFIG,
        ...data,
        strategy_params: { ...DEFAULT_CONFIG.strategy_params, ...(data.strategy_params ?? {}) },
      };
      setConfig(saved);
      originalRef.current = structuredClone(saved);
      setSnackbar({ open: true, message: "Configuración guardada correctamente", severity: "success" });
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: string } } };
      if (e?.response?.status === 404) {
        setSnackbar({
          open: true,
          message: "Endpoint /bot/config no implementado aún — contacta a Santiago",
          severity: "error",
        });
      } else {
        const detail = e?.response?.data?.detail ?? "Error al guardar la configuración";
        setSnackbar({ open: true, message: detail, severity: "error" });
      }
    } finally {
      setSaving(false);
    }
  };

  const isDirty = Object.keys(getDirtyFields(originalRef.current, config)).length > 0;

  // ── Select component (native MUI Select via TextField) ───────────────────────
  const SelectField = ({
    value,
    onChange,
    options,
  }: {
    value: string;
    onChange: (v: string) => void;
    options: { value: string; label: string }[];
  }) => (
    <TextField
      select
      size="small"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      SelectProps={{ native: true }}
      sx={{
        width: 220,
        "& .MuiInputBase-input": { fontSize: 12, py: 0.7 },
        "& .MuiOutlinedInput-root fieldset": { borderColor: "rgba(148,163,184,0.2)" },
      }}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </TextField>
  );

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Settings
      </Typography>

      {/* ── Endpoint missing banner ── */}
      {endpointMissing && !loading && (
        <Alert
          severity="warning"
          icon={<AlertTriangle size={16} />}
          sx={{ mb: 2, fontSize: 12 }}
        >
          <strong>GET /api/v1/bot/config</strong> aún no está implementado. Los valores mostrados
          son parciales (de <code>/bot/status</code>) o defaults. Los cambios no se persistirán
          hasta que Santiago implemente el endpoint.
        </Alert>
      )}

      {/* ── Bot Configuration Card ── */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          {/* Header */}
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Settings size={16} style={{ color: "#8b5cf6" }} />
              <Typography variant="h6">Configuración del Bot</Typography>
            </Box>
            <Box sx={{ display: "flex", gap: 1 }}>
              <Tooltip title="Recargar desde el servidor">
                <Button
                  size="small"
                  variant="text"
                  startIcon={<RotateCcw size={13} />}
                  onClick={loadConfig}
                  disabled={loading || saving}
                  sx={{ fontSize: 11, color: "#64748b" }}
                >
                  Recargar
                </Button>
              </Tooltip>
              <Button
                size="small"
                variant="contained"
                startIcon={
                  saving ? <CircularProgress size={12} color="inherit" /> : <Save size={13} />
                }
                disabled={!isDirty || saving || loading}
                onClick={() => setConfirmOpen(true)}
                sx={{
                  fontSize: 11,
                  fontWeight: 700,
                  bgcolor: "#7c3aed",
                  "&:hover": { bgcolor: "#6d28d9" },
                  "&:disabled": { bgcolor: "rgba(124,58,237,0.2)", color: "rgba(255,255,255,0.3)" },
                }}
              >
                {saving ? "Guardando…" : "Guardar cambios"}
              </Button>
            </Box>
          </Box>

          <Divider sx={{ mb: 2, borderColor: "rgba(148,163,184,0.1)" }} />

          {loading ? (
            <Stack spacing={2}>
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} variant="rounded" height={36} />
              ))}
            </Stack>
          ) : (
            <Stack spacing={0}>
              {/* ── TRADING ── */}
              <Section icon={Bot} title="Trading">
                <Stack spacing={0} divider={<Divider sx={{ borderColor: "rgba(148,163,184,0.07)" }} />}>
                  <SettingRow label="Estrategia" hint="Motor de señales activo">
                    <SelectField
                      value={config.strategy}
                      onChange={(v) => set("strategy", v)}
                      options={STRATEGIES}
                    />
                  </SettingRow>

                  <SettingRow
                    label="Pares de trading"
                    hint={`${config.symbols.length} seleccionados`}
                  >
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, justifyContent: "flex-end", maxWidth: 280 }}>
                      {ALL_SYMBOLS.map((sym) => {
                        const active = config.symbols.includes(sym);
                        return (
                          <Chip
                            key={sym}
                            label={sym}
                            size="small"
                            onClick={() => toggleSymbol(sym)}
                            sx={{
                              height: 22,
                              fontSize: 10,
                              fontWeight: 600,
                              cursor: "pointer",
                              bgcolor: active ? "rgba(124,58,237,0.12)" : "rgba(148,163,184,0.06)",
                              color:   active ? "#c4b5fd" : "#64748b",
                              border: `1px solid ${active ? "rgba(124,58,237,0.3)" : "rgba(148,163,184,0.12)"}`,
                              "&:hover": { opacity: 0.8 },
                            }}
                          />
                        );
                      })}
                    </Box>
                  </SettingRow>

                  <SettingRow label="Timeframe" hint="Marco temporal de análisis">
                    <SelectField
                      value={config.timeframe}
                      onChange={(v) => set("timeframe", v)}
                      options={TIMEFRAMES.map((tf) => ({ value: tf, label: tf }))}
                    />
                  </SettingRow>
                </Stack>
              </Section>

              <Divider sx={{ borderColor: "rgba(148,163,184,0.1)", my: 1 }} />

              {/* ── RISK ── */}
              <Section icon={Shield} title="Gestión de Riesgo">
                <Stack spacing={0} divider={<Divider sx={{ borderColor: "rgba(148,163,184,0.07)" }} />}>
                  <SettingRow
                    label="Riesgo por operación"
                    hint="Porcentaje del balance arriesgado por trade"
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <NumInput
                        value={config.risk_per_trade}
                        onChange={(v) => set("risk_per_trade", v)}
                        min={0.1}
                        max={5.0}
                        step={0.1}
                        width={80}
                      />
                      <Typography sx={{ fontSize: 12, color: "#64748b" }}>%</Typography>
                    </Box>
                  </SettingRow>

                  <SettingRow label="Modo de lote" hint="Cómo se calcula el tamaño de posición">
                    <SelectField
                      value={config.lot_mode}
                      onChange={(v) => set("lot_mode", v)}
                      options={LOT_MODES}
                    />
                  </SettingRow>

                  {config.lot_mode === "fixed" && (
                    <SettingRow label="Lote fijo" hint="Tamaño de lote cuando modo=fixed">
                      <NumInput
                        value={config.fixed_lot}
                        onChange={(v) => set("fixed_lot", v)}
                        min={0.01}
                        max={100}
                        step={0.01}
                        width={100}
                      />
                    </SettingRow>
                  )}

                  <SettingRow
                    label="Máx. trades por hora"
                    hint="Límite de overtrading del circuit breaker"
                  >
                    <NumInput
                      value={config.max_trades_per_hour}
                      onChange={(v) => set("max_trades_per_hour", v)}
                      min={1}
                      max={50}
                      step={1}
                      width={80}
                    />
                  </SettingRow>
                </Stack>
              </Section>

              <Divider sx={{ borderColor: "rgba(148,163,184,0.1)", my: 1 }} />

              {/* ── BIAS STRATEGY PARAMS ── */}
              <Section icon={Zap} title="Parámetros BiasStrategy V1" defaultOpen={false}>
                <Alert
                  severity="info"
                  icon={<Info size={14} />}
                  sx={{ mb: 1.5, fontSize: 11, py: 0.5 }}
                >
                  Solo aplica cuando la estrategia activa es <strong>Bias V1</strong>.
                  Cambiar estos valores requiere reiniciar el bot.
                </Alert>
                <Stack spacing={0} divider={<Divider sx={{ borderColor: "rgba(148,163,184,0.07)" }} />}>
                  <Grid container>
                    <Grid size={{ xs: 12, md: 6 }}>
                      <SettingRow label="Entropy threshold" hint="Máx. entropía Shannon aceptada (2.2–3.5)">
                        <NumInput
                          value={config.strategy_params.entropy_threshold}
                          onChange={(v) => setSp("entropy_threshold", v)}
                          min={2.0} max={4.0} step={0.05} width={90}
                        />
                      </SettingRow>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                      <SettingRow label="ChoCh lookback" hint="Barras M5 para detectar swings (20–100)">
                        <NumInput
                          value={config.strategy_params.choch_lookback}
                          onChange={(v) => setSp("choch_lookback", v)}
                          min={20} max={100} step={5} width={90}
                        />
                      </SettingRow>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                      <SettingRow label="Min Risk/Reward" hint="RR mínimo para abrir trade (1.0–3.0)">
                        <NumInput
                          value={config.strategy_params.min_rr}
                          onChange={(v) => setSp("min_rr", v)}
                          min={1.0} max={3.0} step={0.1} width={90}
                        />
                      </SettingRow>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                      <SettingRow label="SL pips base" hint="Stop loss base en pips (5–30)">
                        <NumInput
                          value={config.strategy_params.sl_pips_base}
                          onChange={(v) => setSp("sl_pips_base", v)}
                          min={5} max={30} step={0.5} width={90}
                        />
                      </SettingRow>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                      <SettingRow label="Sweep tolerance" hint="Tolerancia near-miss en pips (0.5–10)">
                        <NumInput
                          value={config.strategy_params.sweep_tolerance_pips}
                          onChange={(v) => setSp("sweep_tolerance_pips", v)}
                          min={0.5} max={10} step={0.5} width={90}
                        />
                      </SettingRow>
                    </Grid>
                  </Grid>
                </Stack>
              </Section>

              {/* ── Dirty indicator ── */}
              {isDirty && (
                <Box sx={{ mt: 1.5, display: "flex", alignItems: "center", gap: 0.75 }}>
                  <Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: "#f59e0b" }} />
                  <Typography sx={{ fontSize: 11, color: "#f59e0b" }}>
                    Tienes cambios sin guardar
                  </Typography>
                </Box>
              )}
            </Stack>
          )}
        </CardContent>
      </Card>

      {/* ── Runtime status (read-only) ── */}
      {!loading && (config.is_active !== undefined || config.error_state !== undefined) && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1.5 }}>
              Estado del sistema
            </Typography>
            <Stack spacing={1}>
              <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="body2" color="text.secondary">Bot activo</Typography>
                <FormControlLabel
                  control={<Switch checked={config.is_active ?? false} size="small" disabled />}
                  label=""
                  sx={{ mr: 0 }}
                />
              </Box>
              {config.error_state && (
                <>
                  <Divider sx={{ borderColor: "rgba(148,163,184,0.1)" }} />
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Typography variant="body2" color="text.secondary">Estado de error</Typography>
                    <Chip label={`Error (${config.crash_count} crashes)`} size="small" color="error" variant="outlined" />
                  </Box>
                </>
              )}
              {config.last_heartbeat && (
                <>
                  <Divider sx={{ borderColor: "rgba(148,163,184,0.1)" }} />
                  <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                    <Typography variant="body2" color="text.secondary">Último heartbeat</Typography>
                    <Typography variant="body2">
                      {new Date(config.last_heartbeat).toLocaleString()}
                    </Typography>
                  </Box>
                </>
              )}
            </Stack>
          </CardContent>
        </Card>
      )}

      {/* ── Platform Info (existing, unchanged) ── */}
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
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", justifyContent: "flex-end" }}>
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

      {/* ── Confirm Dialog ── */}
      <Dialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { bgcolor: "background.paper", backgroundImage: "none", border: "1px solid rgba(148,163,184,0.1)" } }}
      >
        <DialogTitle sx={{ fontSize: 15, fontWeight: 600 }}>
          Confirmar cambios
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Se actualizarán los siguientes campos:
          </Typography>
          <Box
            sx={{
              borderRadius: 1,
              bgcolor: "rgba(148,163,184,0.04)",
              border: "1px solid rgba(148,163,184,0.08)",
              p: 1.5,
            }}
          >
            {Object.keys(getDirtyFields(originalRef.current, config)).map((key) => (
              <Typography key={key} sx={{ fontSize: 12, fontFamily: "monospace", color: "#c4b5fd" }}>
                • {key}
              </Typography>
            ))}
          </Box>
          {(config.strategy !== originalRef.current.strategy ||
            config.timeframe !== originalRef.current.timeframe ||
            JSON.stringify(config.symbols) !== JSON.stringify(originalRef.current.symbols)) && (
            <Alert severity="warning" sx={{ mt: 1.5, fontSize: 11, py: 0.5 }}>
              Cambios en estrategia, timeframe o símbolos requieren <strong>reiniciar el bot</strong>.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)} sx={{ fontSize: 12 }}>
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            variant="contained"
            sx={{ fontSize: 12, bgcolor: "#7c3aed", "&:hover": { bgcolor: "#6d28d9" } }}
          >
            Confirmar
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Snackbar ── */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
