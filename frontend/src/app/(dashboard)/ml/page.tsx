"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Typography,
  Alert,
  Skeleton,
  LinearProgress,
  Collapse,
  IconButton,
  Switch,
  FormControlLabel,
  Tooltip,
} from "@mui/material";
import { SelectDropdown } from "@/components/ui/select-dropdown";
import { FormattedNumberInput } from "@/components/ui/formatted-number-input";
import Grid from "@mui/material/Grid";
import {
  Brain,
  Sparkles,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
  Database,
  BarChart3,
  Calendar,
  Download,
  Trash2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import api from "@/lib/api";
import type { TrainResponse, PredictResponse, MLModel } from "@/types";

interface BarEstimate {
  estimated_bars: number;
  warmup_bars: number;
  trading_bars: number;
}

const SYMBOL_OPTIONS = [
  { id: "EURUSD", label: "EUR/USD", description: "Euro vs US Dollar" },
  { id: "XAUUSD", label: "XAU/USD", description: "Gold vs US Dollar" },
  { id: "GBPUSD", label: "GBP/USD", description: "British Pound vs US Dollar" },
  { id: "USDCAD", label: "USD/CAD", description: "US Dollar vs Canadian Dollar" },
  { id: "AUDCAD", label: "AUD/CAD", description: "Australian Dollar vs Canadian Dollar" },
  { id: "EURJPY", label: "EUR/JPY", description: "Euro vs Japanese Yen" },
  { id: "USDJPY", label: "USD/JPY", description: "US Dollar vs Japanese Yen" },
  { id: "EURGBP", label: "EUR/GBP", description: "Euro vs British Pound" },
];

const TIMEFRAME_OPTIONS = [
  { id: "M5", label: "M5", description: "5 minutes" },
  { id: "M15", label: "M15", description: "15 minutes" },
  { id: "H1", label: "H1", description: "1 hour" },
  { id: "H4", label: "H4", description: "4 hours" },
  { id: "D1", label: "D1", description: "Daily" },
];

function Section({
  title,
  icon,
  defaultOpen = true,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Box sx={{ mb: 2 }}>
      <Box
        onClick={() => setOpen(!open)}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          cursor: "pointer",
          py: 1,
          "&:hover": { opacity: 0.8 },
        }}
      >
        {icon}
        <Typography sx={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.03em", textTransform: "uppercase", color: "#94a3b8", flex: 1 }}>
          {title}
        </Typography>
        {open ? <ChevronUp size={14} style={{ color: "#64748b" }} /> : <ChevronDown size={14} style={{ color: "#64748b" }} />}
      </Box>
      <Collapse in={open}>
        <Box sx={{ pt: 0.5 }}>{children}</Box>
      </Collapse>
    </Box>
  );
}

function FeatureBar({ name, value, maxValue }: { name: string; value: number; maxValue: number }) {
  const pct = maxValue > 0 ? (value / maxValue) * 100 : 0;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
        <Typography sx={{ fontSize: 11, color: "#94a3b8", fontFamily: "monospace" }}>{name}</Typography>
        <Typography sx={{ fontSize: 11, color: "text.primary", fontWeight: 600, fontFamily: "monospace" }}>
          {value.toFixed(4)}
        </Typography>
      </Box>
      <Box sx={{ height: 6, borderRadius: 1, bgcolor: "rgba(148,163,184,0.08)", overflow: "hidden" }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          style={{
            height: "100%",
            borderRadius: 4,
            background: `linear-gradient(90deg, #7c3aed, #a78bfa)`,
          }}
        />
      </Box>
    </Box>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: 2,
        bgcolor: `${color}08`,
        border: `1px solid ${color}15`,
      }}
    >
      <Typography sx={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", mb: 0.5 }}>
        {label}
      </Typography>
      <Typography sx={{ fontSize: 18, fontWeight: 700, color, fontFeatureSettings: '"tnum"' }}>
        {value}
      </Typography>
    </Box>
  );
}

function MetricsAndFeatures({ metrics, top_features }: { metrics: Record<string, number>; top_features: Record<string, number> }) {
  const entries = Object.entries(top_features).slice(0, 10);
  const maxVal = entries.length > 0 ? Math.max(...entries.map(([, v]) => (typeof v === "number" ? v : 0))) : 1;
  return (
    <>
      <Grid container spacing={1.5} sx={{ mb: 3 }}>
        {Object.entries(metrics).map(([key, val]) => {
          const numVal = typeof val === "number" ? val : parseFloat(String(val));
          const isGood = numVal > 0.6;
          const color = isGood ? "#22c55e" : numVal > 0.4 ? "#f59e0b" : "#ef4444";
          return (
            <Grid size={{ xs: 6, sm: 4 }} key={key}>
              <MetricCard
                label={key.replace(/_/g, " ")}
                value={typeof val === "number" ? val.toFixed(4) : String(val)}
                color={color}
              />
            </Grid>
          );
        })}
      </Grid>
      <Typography sx={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.03em", mb: 1.5 }}>
        Top Features
      </Typography>
      {entries.map(([key, val]) => (
        <FeatureBar key={key} name={key} value={typeof val === "number" ? val : 0} maxValue={maxVal} />
      ))}
    </>
  );
}

function exportModelJSON(modelId: string, metrics: Record<string, number>, top_features: Record<string, number>, extra?: Record<string, unknown>) {
  const data = { model_id: modelId, metrics, top_features, ...extra };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `model_${modelId.slice(0, 16)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function MLPage() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [bars, setBars] = useState("5000");
  const [loading, setLoading] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResponse | null>(null);
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [models, setModels] = useState<MLModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [error, setError] = useState("");
  const [predictingId, setPredictingId] = useState<string | null>(null);
  const [expandedModelId, setExpandedModelId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Date range mode
  const [useDateRange, setUseDateRange] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [warmupBars, setWarmupBars] = useState("200");
  const [estimate, setEstimate] = useState<BarEstimate | null>(null);

  const fetchModels = useCallback(async () => {
    try {
      const { data } = await api.get("/ml/models");
      setModels(data.models || []);
    } catch {
      // silent
    } finally {
      setModelsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  const fetchEstimate = useCallback(async (from: string, to: string, wb: string, tf: string) => {
    if (!from || !to) return;
    try {
      const { data } = await api.post<BarEstimate>("/backtest/estimate", {
        timeframe: tf,
        date_from: from,
        date_to: to,
        timezone: "America/Bogota",
        warmup_bars: parseInt(wb) || 200,
      });
      setEstimate(data);
    } catch {
      setEstimate(null);
    }
  }, []);

  const handleDateFromChange = (val: string) => {
    setDateFrom(val);
    if (val && dateTo) setTimeout(() => fetchEstimate(val, dateTo, warmupBars, timeframe), 100);
  };

  const handleDateToChange = (val: string) => {
    setDateTo(val);
    if (dateFrom && val) setTimeout(() => fetchEstimate(dateFrom, val, warmupBars, timeframe), 100);
  };

  const handleWarmupChange = (val: string) => {
    setWarmupBars(val);
    if (dateFrom && dateTo) setTimeout(() => fetchEstimate(dateFrom, dateTo, val, timeframe), 100);
  };

  const handleTrain = async () => {
    if (useDateRange) {
      if (!dateFrom || !dateTo) {
        setError("Both start and end dates are required");
        return;
      }
      if (new Date(dateTo) <= new Date(dateFrom)) {
        setError("End date must be after start date");
        return;
      }
    } else {
      const barsNum = parseInt(bars) || 5000;
      if (barsNum < 500 || barsNum > 50000) {
        setError("Historical bars must be between 500 and 50,000");
        return;
      }
    }

    setLoading(true);
    setError("");
    setPrediction(null);

    try {
      const payload = useDateRange
        ? { symbol, timeframe, date_from: dateFrom, date_to: dateTo, timezone: "America/Bogota", warmup_bars: parseInt(warmupBars) || 200 }
        : { symbol, timeframe, bars: parseInt(bars) || 5000 };

      const { data } = await api.post<TrainResponse>("/ml/train", payload);
      setTrainResult(data);
      await fetchModels();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Training failed");
    } finally {
      setLoading(false);
    }
  };

  const handlePredict = async (modelId: string) => {
    setPredictingId(modelId);
    const model = models.find((m) => m.model_id === modelId);
    try {
      const { data } = await api.post<PredictResponse>("/ml/predict", {
        model_id: modelId,
        symbol: model?.symbol ?? symbol,
        timeframe: model?.timeframe ?? timeframe,
        bars: 500,
      });
      setPrediction(data);
      setError("");
    } catch {
      setError("Prediction failed");
    } finally {
      setPredictingId(null);
    }
  };

  const handleDelete = async (modelId: string) => {
    if (confirmDeleteId !== modelId) {
      setConfirmDeleteId(modelId);
      setTimeout(() => setConfirmDeleteId((c) => (c === modelId ? null : c)), 3000);
      return;
    }
    setDeletingId(modelId);
    setConfirmDeleteId(null);
    try {
      await api.delete(`/ml/models/${modelId}`);
      if (expandedModelId === modelId) setExpandedModelId(null);
      await fetchModels();
    } catch {
      setError("Failed to delete model");
    } finally {
      setDeletingId(null);
    }
  };

  const signalColor = prediction?.signal === "BUY" ? "#22c55e" : prediction?.signal === "SELL" ? "#ef4444" : "#64748b";
  const SignalIcon = prediction?.signal === "BUY" ? TrendingUp : prediction?.signal === "SELL" ? TrendingDown : Minus;

  return (
    <Box>
      {/* Page header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            bgcolor: "rgba(139, 92, 246, 0.1)",
            border: "1px solid rgba(139, 92, 246, 0.15)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Brain size={22} style={{ color: "#8b5cf6" }} />
        </Box>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.2, fontSize: 20 }}>
            ML Models
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.25 }}>
            <Typography variant="caption" sx={{ color: "#64748b", fontSize: 11 }}>
              XGBoost Pipeline
            </Typography>
            <Chip
              label="XGBoost"
              size="small"
              sx={{
                height: 18,
                fontSize: 9,
                fontWeight: 600,
                bgcolor: "rgba(139, 92, 246, 0.08)",
                color: "#8b5cf6",
                border: "1px solid rgba(139, 92, 246, 0.2)",
              }}
            />
          </Box>
        </Box>
      </Box>

      <Grid container spacing={2.5}>
        {/* Left panel - Config */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Section title="Model Configuration" icon={<Brain size={14} style={{ color: "#8b5cf6" }} />}>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <SelectDropdown
                    label="Symbol"
                    value={symbol}
                    onValueChange={setSymbol}
                    options={SYMBOL_OPTIONS}
                  />
                  <SelectDropdown
                    label="Timeframe"
                    value={timeframe}
                    onValueChange={setTimeframe}
                    options={TIMEFRAME_OPTIONS}
                  />
                </Box>
              </Section>

              <Section title="Training Data" icon={<Database size={14} style={{ color: "#7c3aed" }} />}>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                  {/* Toggle */}
                  <FormControlLabel
                    control={
                      <Switch
                        checked={useDateRange}
                        onChange={(e) => {
                          setUseDateRange(e.target.checked);
                          setEstimate(null);
                        }}
                        size="small"
                      />
                    }
                    label={
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                        {useDateRange ? <Calendar size={13} style={{ color: "#7c3aed" }} /> : <BarChart3 size={13} style={{ color: "#94a3b8" }} />}
                        <Typography sx={{ fontSize: 12, color: useDateRange ? "#a78bfa" : "#94a3b8" }}>
                          {useDateRange ? "Date Range" : "Bar Count"}
                        </Typography>
                      </Box>
                    }
                    sx={{ ml: 0, mb: 0.5 }}
                  />

                  <AnimatePresence mode="wait">
                    {!useDateRange ? (
                      <motion.div
                        key="bars"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <FormattedNumberInput
                          size="small"
                          label="Historical Bars"
                          value={bars}
                          onChange={setBars}
                          decimals={0}
                          helperText="Min: 500, Max: 50.000 candles"
                          fullWidth
                        />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="daterange"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                          <Box>
                            <Typography sx={{ fontSize: 11, color: "#64748b", mb: 0.5 }}>Start Date</Typography>
                            <input
                              type="date"
                              value={dateFrom}
                              onChange={(e) => handleDateFromChange(e.target.value)}
                              style={{
                                width: "100%",
                                padding: "8px 10px",
                                borderRadius: 8,
                                border: "1px solid rgba(139,92,246,0.15)",
                                background: "rgba(15,10,40,0.5)",
                                color: "#f1f5f9",
                                fontSize: 13,
                                outline: "none",
                                boxSizing: "border-box",
                                colorScheme: "dark",
                              }}
                            />
                          </Box>
                          <Box>
                            <Typography sx={{ fontSize: 11, color: "#64748b", mb: 0.5 }}>End Date</Typography>
                            <input
                              type="date"
                              value={dateTo}
                              onChange={(e) => handleDateToChange(e.target.value)}
                              style={{
                                width: "100%",
                                padding: "8px 10px",
                                borderRadius: 8,
                                border: "1px solid rgba(139,92,246,0.15)",
                                background: "rgba(15,10,40,0.5)",
                                color: "#f1f5f9",
                                fontSize: 13,
                                outline: "none",
                                boxSizing: "border-box",
                                colorScheme: "dark",
                              }}
                            />
                          </Box>
                          <FormattedNumberInput
                            size="small"
                            label="Warmup Bars"
                            value={warmupBars}
                            onChange={handleWarmupChange}
                            decimals={0}
                            helperText="Bars for indicator pre-calculation"
                            fullWidth
                          />
                          {estimate && (
                            <Box
                              sx={{
                                p: 1.5,
                                borderRadius: 1.5,
                                bgcolor: "rgba(124, 58, 237, 0.04)",
                                border: "1px solid rgba(124, 58, 237, 0.12)",
                              }}
                            >
                              <Typography sx={{ fontSize: 11, color: "#a78bfa", fontWeight: 600, mb: 0.25 }}>
                                ~{estimate.estimated_bars.toLocaleString()} bars total
                              </Typography>
                              <Typography sx={{ fontSize: 10, color: "#64748b" }}>
                                {estimate.warmup_bars} warmup + {estimate.trading_bars.toLocaleString()} training
                              </Typography>
                            </Box>
                          )}
                        </Box>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Box>
              </Section>

              <Button
                variant="contained"
                startIcon={
                  loading ? (
                    <CircularProgress size={18} sx={{ color: "inherit" }} />
                  ) : (
                    <Brain size={18} />
                  )
                }
                onClick={handleTrain}
                disabled={loading}
                fullWidth
                sx={{
                  mt: 1,
                  bgcolor: "#8b5cf6",
                  "&:hover": { bgcolor: "#7c3aed" },
                  textTransform: "none",
                  fontWeight: 600,
                  py: 1.2,
                }}
              >
                {loading ? "Training Model..." : "Train Model"}
              </Button>

              {loading && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress
                    sx={{
                      borderRadius: 1,
                      bgcolor: "rgba(139, 92, 246, 0.08)",
                      "& .MuiLinearProgress-bar": {
                        bgcolor: "#8b5cf6",
                      },
                    }}
                  />
                  <Typography sx={{ fontSize: 10, color: "#64748b", mt: 0.5, textAlign: "center" }}>
                    Training in progress...
                  </Typography>
                </Box>
              )}

              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <Alert severity="error" sx={{ mt: 2, fontSize: 12 }}>{error}</Alert>
                  </motion.div>
                )}
              </AnimatePresence>
            </CardContent>
          </Card>

          {/* Prediction card */}
          <AnimatePresence>
            {prediction && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.2 }}
              >
                <Card sx={{ mt: 2 }}>
                  <CardContent sx={{ p: 2.5 }}>
                    <Typography sx={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.03em", mb: 2 }}>
                      Prediction Result
                    </Typography>

                    {/* Signal */}
                    <Box sx={{ textAlign: "center", mb: 2.5 }}>
                      <Box
                        sx={{
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          width: 56,
                          height: 56,
                          borderRadius: 3,
                          bgcolor: `${signalColor}10`,
                          border: `1px solid ${signalColor}25`,
                          mb: 1.5,
                        }}
                      >
                        <SignalIcon size={28} style={{ color: signalColor }} />
                      </Box>
                      <Typography sx={{ fontSize: 24, fontWeight: 800, color: signalColor, letterSpacing: "-0.02em" }}>
                        {prediction.signal}
                      </Typography>
                    </Box>

                    {/* Probability bar */}
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                        <Typography sx={{ fontSize: 11, color: "#64748b" }}>Probability</Typography>
                        <Typography sx={{ fontSize: 11, fontWeight: 600, color: "text.primary" }}>
                          {(prediction.probability * 100).toFixed(1)}%
                        </Typography>
                      </Box>
                      <Box sx={{ height: 8, borderRadius: 1, bgcolor: "rgba(148,163,184,0.08)", overflow: "hidden" }}>
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${prediction.probability * 100}%` }}
                          transition={{ duration: 0.6, ease: "easeOut" }}
                          style={{
                            height: "100%",
                            borderRadius: 4,
                            background: `linear-gradient(90deg, ${signalColor}, ${signalColor}aa)`,
                          }}
                        />
                      </Box>
                    </Box>

                    {/* Confidence */}
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 1,
                        p: 1,
                        borderRadius: 1.5,
                        bgcolor: "rgba(148,163,184,0.04)",
                      }}
                    >
                      <Zap size={14} style={{ color: "#f59e0b" }} />
                      <Typography sx={{ fontSize: 12, fontWeight: 600 }}>
                        Confidence: <span style={{ color: "#f59e0b" }}>{prediction.confidence}</span>
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </Grid>

        {/* Right panel - Results & Models */}
        <Grid size={{ xs: 12, md: 8 }}>
          {/* Training Results */}
          <AnimatePresence>
            {trainResult && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Card sx={{ mb: 2.5 }}>
                  <CardContent sx={{ p: 2.5 }}>
                    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2.5 }}>
                      <Box>
                        <Typography sx={{ fontSize: 15, fontWeight: 600 }}>
                          Training Results
                        </Typography>
                        <Typography sx={{ fontSize: 11, color: "#64748b", fontFamily: "monospace", mt: 0.25 }}>
                          {trainResult.model_id}
                        </Typography>
                      </Box>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        {trainResult.metrics.accuracy !== undefined && (
                          <Chip
                            label={`${(trainResult.metrics.accuracy * 100).toFixed(1)}% accuracy`}
                            size="small"
                            sx={{
                              height: 24,
                              fontSize: 11,
                              fontWeight: 600,
                              bgcolor: trainResult.metrics.accuracy > 0.6 ? "rgba(34,197,94,0.08)" : "rgba(245,158,11,0.08)",
                              color: trainResult.metrics.accuracy > 0.6 ? "#22c55e" : "#f59e0b",
                              border: `1px solid ${trainResult.metrics.accuracy > 0.6 ? "rgba(34,197,94,0.2)" : "rgba(245,158,11,0.2)"}`,
                            }}
                          />
                        )}
                        <Tooltip title="Export JSON" arrow>
                          <IconButton
                            size="small"
                            onClick={() =>
                              exportModelJSON(
                                trainResult.model_id,
                                trainResult.metrics as Record<string, number>,
                                trainResult.top_features as Record<string, number>,
                                { symbol, timeframe, trained_at: new Date().toISOString() }
                              )
                            }
                            sx={{
                              color: "#64748b",
                              "&:hover": { color: "#8b5cf6", bgcolor: "rgba(139,92,246,0.08)" },
                            }}
                          >
                            <Download size={16} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>

                    <MetricsAndFeatures
                      metrics={trainResult.metrics as Record<string, number>}
                      top_features={trainResult.top_features as Record<string, number>}
                    />
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Saved Models */}
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
                <Typography sx={{ fontSize: 15, fontWeight: 600 }}>
                  Saved Models
                </Typography>
                {models.length > 0 && (
                  <Chip
                    label={`${models.length} model${models.length > 1 ? "s" : ""}`}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: 10,
                      fontWeight: 600,
                      bgcolor: "rgba(148,163,184,0.06)",
                      color: "#94a3b8",
                    }}
                  />
                )}
              </Box>

              {modelsLoading ? (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} variant="rectangular" height={56} sx={{ borderRadius: 2 }} />
                  ))}
                </Box>
              ) : models.length === 0 ? (
                <Box sx={{ textAlign: "center", py: 6 }}>
                  <Brain size={40} style={{ color: "#334155", marginBottom: 12 }} />
                  <Typography sx={{ color: "#64748b", fontSize: 13 }}>
                    No models trained yet
                  </Typography>
                  <Typography sx={{ color: "#475569", fontSize: 11, mt: 0.5 }}>
                    Train your first XGBoost model using the configuration panel
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {models.map((m) => {
                    const isExpanded = expandedModelId === m.model_id;
                    const modelMetrics = (m.metrics || {}) as Record<string, number>;
                    const modelFeatures = (m.feature_importance || {}) as Record<string, number>;
                    return (
                      <Box key={m.model_id}>
                        <Box
                          onClick={() => setExpandedModelId(isExpanded ? null : m.model_id)}
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 2,
                            p: 1.5,
                            borderRadius: isExpanded ? "12px 12px 0 0" : 2,
                            bgcolor: isExpanded ? "rgba(139, 92, 246, 0.06)" : "rgba(148,163,184,0.03)",
                            border: "1px solid",
                            borderColor: isExpanded ? "rgba(139, 92, 246, 0.2)" : "rgba(148,163,184,0.06)",
                            borderBottom: isExpanded ? "none" : undefined,
                            cursor: "pointer",
                            transition: "border-color 0.15s, background-color 0.15s",
                            "&:hover": {
                              borderColor: "rgba(139, 92, 246, 0.2)",
                              bgcolor: "rgba(139, 92, 246, 0.04)",
                            },
                          }}
                        >
                          <Box
                            sx={{
                              width: 36,
                              height: 36,
                              borderRadius: 1.5,
                              bgcolor: "rgba(139, 92, 246, 0.08)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              flexShrink: 0,
                            }}
                          >
                            <BarChart3 size={18} style={{ color: "#8b5cf6" }} />
                          </Box>
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography sx={{ fontSize: 12, fontWeight: 600, fontFamily: "monospace" }}>
                              {m.model_id.slice(0, 20)}...
                            </Typography>
                            <Box sx={{ display: "flex", gap: 1, mt: 0.25 }}>
                              <Chip
                                label={m.symbol}
                                size="small"
                                sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: "rgba(124,58,237,0.08)", color: "#7c3aed" }}
                              />
                              <Chip
                                label={m.timeframe}
                                size="small"
                                sx={{ height: 16, fontSize: 9, fontWeight: 600, bgcolor: "rgba(148,163,184,0.06)", color: "#94a3b8" }}
                              />
                              <Typography sx={{ fontSize: 10, color: "#475569" }}>
                                {new Date(m.created_at).toLocaleDateString()}
                              </Typography>
                            </Box>
                          </Box>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                            {/* Predict button */}
                            <Tooltip title="Predict" arrow>
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handlePredict(m.model_id);
                                }}
                                disabled={predictingId === m.model_id || deletingId === m.model_id}
                                sx={{
                                  color: "#8b5cf6",
                                  bgcolor: "rgba(139, 92, 246, 0.08)",
                                  border: "1px solid rgba(139, 92, 246, 0.15)",
                                  "&:hover": { bgcolor: "rgba(139, 92, 246, 0.15)" },
                                  width: 30,
                                  height: 30,
                                }}
                              >
                                {predictingId === m.model_id ? (
                                  <CircularProgress size={12} sx={{ color: "#8b5cf6" }} />
                                ) : (
                                  <Sparkles size={14} />
                                )}
                              </IconButton>
                            </Tooltip>
                            {/* Delete button — two-step confirm */}
                            <Tooltip title={confirmDeleteId === m.model_id ? "Click again to confirm" : "Delete model"} arrow>
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDelete(m.model_id);
                                }}
                                disabled={deletingId === m.model_id}
                                sx={{
                                  color: confirmDeleteId === m.model_id ? "#ef4444" : "#475569",
                                  bgcolor: confirmDeleteId === m.model_id ? "rgba(239,68,68,0.1)" : "transparent",
                                  border: "1px solid",
                                  borderColor: confirmDeleteId === m.model_id ? "rgba(239,68,68,0.3)" : "transparent",
                                  "&:hover": {
                                    color: "#ef4444",
                                    bgcolor: "rgba(239,68,68,0.08)",
                                    borderColor: "rgba(239,68,68,0.2)",
                                  },
                                  width: 30,
                                  height: 30,
                                  transition: "all 0.15s",
                                }}
                              >
                                {deletingId === m.model_id ? (
                                  <CircularProgress size={12} sx={{ color: "#ef4444" }} />
                                ) : (
                                  <Trash2 size={14} />
                                )}
                              </IconButton>
                            </Tooltip>
                            {isExpanded ? (
                              <ChevronUp size={16} style={{ color: "#64748b" }} />
                            ) : (
                              <ChevronDown size={16} style={{ color: "#64748b" }} />
                            )}
                          </Box>
                        </Box>

                        {/* Expanded content */}
                        <Collapse in={isExpanded}>
                          <Box
                            sx={{
                              p: 2,
                              borderRadius: "0 0 12px 12px",
                              bgcolor: "rgba(139, 92, 246, 0.03)",
                              border: "1px solid rgba(139, 92, 246, 0.2)",
                              borderTop: "none",
                            }}
                          >
                            <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1.5 }}>
                              <Tooltip title="Export JSON" arrow>
                                <IconButton
                                  size="small"
                                  onClick={() => exportModelJSON(m.model_id, modelMetrics, modelFeatures, {
                                    symbol: m.symbol,
                                    timeframe: m.timeframe,
                                    created_at: m.created_at,
                                  })}
                                  sx={{
                                    color: "#64748b",
                                    fontSize: 11,
                                    gap: 0.5,
                                    borderRadius: 1,
                                    px: 1,
                                    "&:hover": { color: "#8b5cf6", bgcolor: "rgba(139,92,246,0.08)" },
                                  }}
                                >
                                  <Download size={14} />
                                  <Typography sx={{ fontSize: 11 }}>Export JSON</Typography>
                                </IconButton>
                              </Tooltip>
                            </Box>
                            {Object.keys(modelMetrics).length > 0 ? (
                              <MetricsAndFeatures metrics={modelMetrics} top_features={modelFeatures} />
                            ) : (
                              <Typography sx={{ fontSize: 12, color: "#64748b", textAlign: "center", py: 2 }}>
                                No metrics available for this model
                              </Typography>
                            )}
                          </Box>
                        </Collapse>
                      </Box>
                    );
                  })}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
