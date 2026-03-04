"use client";

import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Typography,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { SelectDropdown } from "@/components/ui/select-dropdown";
import { FormattedNumberInput } from "@/components/ui/formatted-number-input";
import {
  LineChart,
  SlidersHorizontal,
  Shield,
  ArrowLeftRight,
  Sparkles,
  Copy,
  Check,
  Brain,
  BarChart3,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import api from "@/lib/api";
import type { AIResponse } from "@/types";

type AnalysisType = "trades" | "summary" | "parameters" | "risk" | "compare";

const ANALYSIS_OPTIONS: {
  value: AnalysisType;
  label: string;
  icon: React.ReactNode;
  desc: string;
  color: string;
}[] = [
  { value: "trades", label: "Trade Analysis", icon: <LineChart size={20} />, desc: "Analyze recent trading patterns", color: "#7c3aed" },
  { value: "summary", label: "Performance", icon: <BarChart3 size={20} />, desc: "Generate performance report", color: "#22c55e" },
  { value: "parameters", label: "Parameters", icon: <SlidersHorizontal size={20} />, desc: "AI-suggested risk parameters", color: "#8b5cf6" },
  { value: "risk", label: "Risk Review", icon: <Shield size={20} />, desc: "Review risk events and anomalies", color: "#f59e0b" },
  { value: "compare", label: "Compare", icon: <ArrowLeftRight size={20} />, desc: "Compare strategy performance", color: "#ec4899" },
];

export default function AnalysisPage() {
  const [analysisType, setAnalysisType] = useState<AnalysisType>("trades");
  const [days, setDays] = useState("7");
  const [period, setPeriod] = useState("weekly");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIResponse | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleAnalyze = async () => {
    const daysNum = parseInt(days) || 7;
    if ((analysisType === "trades" || analysisType === "risk") && (daysNum < 1 || daysNum > 90)) {
      setError("Days must be between 1 and 90");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      let endpoint = "";
      let payload: Record<string, unknown> = {};
      switch (analysisType) {
        case "trades":
          endpoint = "/ai/analyze-trades";
          payload = { days: daysNum };
          break;
        case "summary":
          endpoint = "/ai/performance-summary";
          payload = { period };
          break;
        case "parameters":
          endpoint = "/ai/suggest-parameters";
          payload = {};
          break;
        case "risk":
          endpoint = "/ai/risk-review";
          payload = { days: daysNum };
          break;
        case "compare":
          endpoint = "/ai/compare-strategies";
          payload = { strategies: ["fibonacci", "ict", "hybrid_ml"], days: 30 };
          break;
      }
      const { data } = await api.post<AIResponse>(endpoint, payload);
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (result?.analysis) {
      await navigator.clipboard.writeText(result.analysis);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const currentOption = ANALYSIS_OPTIONS.find((o) => o.value === analysisType)!;

  return (
    <Box>
      {/* Page header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            bgcolor: "rgba(59, 130, 246, 0.1)",
            border: "1px solid rgba(124, 58, 237, 0.15)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Sparkles size={22} style={{ color: "#7c3aed" }} />
        </Box>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.2, fontSize: 20 }}>
            AI Analysis
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.25 }}>
            <Typography variant="caption" sx={{ color: "#64748b", fontSize: 11 }}>
              GPT-4o-mini powered insights
            </Typography>
            <Chip
              label="AI"
              size="small"
              sx={{
                height: 18,
                fontSize: 9,
                fontWeight: 600,
                bgcolor: "rgba(124, 58, 237, 0.08)",
                color: "#7c3aed",
                border: "1px solid rgba(124, 58, 237, 0.2)",
              }}
            />
          </Box>
        </Box>
      </Box>

      {/* Analysis type selector - horizontal cards */}
      <Box sx={{ display: "flex", gap: 1.5, mb: 3, overflowX: "auto", pb: 0.5 }}>
        {ANALYSIS_OPTIONS.map((opt) => {
          const isSelected = analysisType === opt.value;
          return (
            <motion.div
              key={opt.value}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              <Card
                onClick={() => setAnalysisType(opt.value)}
                sx={{
                  cursor: "pointer",
                  minWidth: 150,
                  transition: "border-color 0.15s, background-color 0.15s",
                  ...(isSelected
                    ? {
                        borderColor: `${opt.color}40`,
                        bgcolor: `${opt.color}08`,
                      }
                    : {
                        "&:hover": {
                          borderColor: "rgba(148,163,184,0.15)",
                        },
                      }),
                }}
              >
                <CardContent sx={{ p: "14px !important" }}>
                  <Box
                    sx={{
                      width: 36,
                      height: 36,
                      borderRadius: 2,
                      bgcolor: `${opt.color}${isSelected ? "15" : "08"}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      mb: 1.5,
                      transition: "background-color 0.15s",
                    }}
                  >
                    <Box sx={{ color: opt.color }}>{opt.icon}</Box>
                  </Box>
                  <Typography sx={{ fontSize: 12, fontWeight: 600, mb: 0.25 }}>
                    {opt.label}
                  </Typography>
                  <Typography sx={{ fontSize: 10, color: "#64748b", lineHeight: 1.3 }}>
                    {opt.desc}
                  </Typography>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </Box>

      <Grid container spacing={2.5}>
        {/* Left - Input area */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Typography sx={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.03em", mb: 2 }}>
                Configuration
              </Typography>

              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {(analysisType === "trades" || analysisType === "risk") && (
                  <FormattedNumberInput
                    size="small"
                    label="Days to analyze"
                    value={days}
                    onChange={setDays}
                    decimals={0}
                    helperText="Range: 1 - 90 days"
                    fullWidth
                  />
                )}
                {analysisType === "summary" && (
                  <SelectDropdown
                    label="Period"
                    value={period}
                    onValueChange={setPeriod}
                    options={[
                      { id: "weekly", label: "Weekly", description: "Last 7 days summary" },
                      { id: "monthly", label: "Monthly", description: "Last 30 days summary" },
                    ]}
                  />
                )}
                {analysisType === "parameters" && (
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      bgcolor: "rgba(139, 92, 246, 0.04)",
                      border: "1px solid rgba(139, 92, 246, 0.1)",
                    }}
                  >
                    <Typography sx={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.5 }}>
                      AI will analyze your current strategy configuration and suggest optimized risk parameters based on recent performance.
                    </Typography>
                  </Box>
                )}
                {analysisType === "compare" && (
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      bgcolor: "rgba(236, 72, 153, 0.04)",
                      border: "1px solid rgba(236, 72, 153, 0.1)",
                    }}
                  >
                    <Typography sx={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.5 }}>
                      Compares Fibonacci, ICT, and Hybrid ML strategies over the last 30 days.
                    </Typography>
                  </Box>
                )}

                <Button
                  variant="contained"
                  startIcon={
                    loading ? (
                      <CircularProgress size={18} sx={{ color: "inherit" }} />
                    ) : (
                      <Sparkles size={18} />
                    )
                  }
                  onClick={handleAnalyze}
                  disabled={loading}
                  fullWidth
                  sx={{
                    bgcolor: currentOption.color,
                    "&:hover": { filter: "brightness(0.9)" },
                    textTransform: "none",
                    fontWeight: 600,
                    py: 1.2,
                  }}
                >
                  {loading ? "Analyzing..." : "Run Analysis"}
                </Button>
              </Box>

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
        </Grid>

        {/* Right - Result area */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ minHeight: 400 }}>
            <CardContent sx={{ p: 2.5 }}>
              {/* Result header */}
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                  <Typography sx={{ fontSize: 15, fontWeight: 600 }}>
                    Analysis Result
                  </Typography>
                  {result && (
                    <>
                      <Chip
                        label={currentOption.label}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: 9,
                          fontWeight: 600,
                          bgcolor: `${currentOption.color}08`,
                          color: currentOption.color,
                          border: `1px solid ${currentOption.color}20`,
                        }}
                      />
                      <Chip
                        icon={<Brain size={10} style={{ color: "#64748b" }} />}
                        label={result.model_used}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: 9,
                          bgcolor: "rgba(148,163,184,0.06)",
                          color: "#94a3b8",
                          "& .MuiChip-icon": { ml: 0.3 },
                        }}
                      />
                    </>
                  )}
                </Box>
                {result && (
                  <Tooltip title={copied ? "Copied!" : "Copy to clipboard"} arrow>
                    <IconButton
                      size="small"
                      onClick={handleCopy}
                      sx={{
                        color: copied ? "#22c55e" : "#64748b",
                        "&:hover": { bgcolor: "rgba(148,163,184,0.08)" },
                      }}
                    >
                      {copied ? <Check size={16} /> : <Copy size={16} />}
                    </IconButton>
                  </Tooltip>
                )}
              </Box>

              {/* Result content */}
              {loading ? (
                <Box sx={{ textAlign: "center", py: 8 }}>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    style={{ display: "inline-block", marginBottom: 16 }}
                  >
                    <Sparkles size={32} style={{ color: currentOption.color }} />
                  </motion.div>
                  <Typography sx={{ color: "#64748b", fontSize: 13, mt: 1 }}>
                    AI is analyzing your data...
                  </Typography>
                  <Typography sx={{ color: "#475569", fontSize: 11, mt: 0.5 }}>
                    This may take a few seconds
                  </Typography>
                </Box>
              ) : result ? (
                <AnimatePresence>
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Box
                      sx={{
                        maxHeight: 500,
                        overflowY: "auto",
                        pr: 1,
                        "&::-webkit-scrollbar": { width: 4 },
                        "&::-webkit-scrollbar-thumb": {
                          bgcolor: "rgba(148,163,184,0.15)",
                          borderRadius: 2,
                        },
                      }}
                    >
                      <Typography
                        sx={{
                          whiteSpace: "pre-wrap",
                          lineHeight: 1.8,
                          fontSize: 13,
                          color: "#cbd5e1",
                        }}
                      >
                        {result.analysis}
                      </Typography>
                    </Box>
                  </motion.div>
                </AnimatePresence>
              ) : (
                <Box sx={{ textAlign: "center", py: 8 }}>
                  <Sparkles size={40} style={{ color: "#334155", marginBottom: 12 }} />
                  <Typography sx={{ color: "#64748b", fontSize: 13 }}>
                    Select an analysis type and run it
                  </Typography>
                  <Typography sx={{ color: "#475569", fontSize: 11, mt: 0.5 }}>
                    AI will generate insights based on your trading data
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
