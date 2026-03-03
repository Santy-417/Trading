"use client";

import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Alert,
  CircularProgress,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { SelectDropdown } from "@/components/ui/select-dropdown";
import { FormattedNumberInput } from "@/components/ui/formatted-number-input";
import { LineChart, FileText, SlidersHorizontal, Shield, ArrowLeftRight } from "lucide-react";
import api from "@/lib/api";
import type { AIResponse } from "@/types";

type AnalysisType = "trades" | "summary" | "parameters" | "risk" | "compare";

export default function AnalysisPage() {
  const [analysisType, setAnalysisType] = useState<AnalysisType>("trades");
  const [days, setDays] = useState("7");
  const [period, setPeriod] = useState("weekly");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIResponse | null>(null);
  const [error, setError] = useState("");

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

  const analysisOptions = [
    { value: "trades", label: "Trade Analysis", icon: <LineChart size={20} />, desc: "Analyze recent trading patterns" },
    { value: "summary", label: "Performance Summary", icon: <FileText size={20} />, desc: "Generate performance report" },
    { value: "parameters", label: "Parameter Suggestions", icon: <SlidersHorizontal size={20} />, desc: "AI-suggested risk parameters" },
    { value: "risk", label: "Risk Review", icon: <Shield size={20} />, desc: "Review risk events and anomalies" },
    { value: "compare", label: "Strategy Comparison", icon: <ArrowLeftRight size={20} />, desc: "Compare strategy performance" },
  ];

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        AI Analysis
      </Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Analysis Type
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {analysisOptions.map((opt) => (
                  <Button
                    key={opt.value}
                    variant={analysisType === opt.value ? "contained" : "outlined"}
                    startIcon={opt.icon}
                    onClick={() => setAnalysisType(opt.value as AnalysisType)}
                    sx={{ justifyContent: "flex-start", textAlign: "left" }}
                    fullWidth
                  >
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{opt.label}</Typography>
                      <Typography variant="caption" sx={{ opacity: 0.7 }}>{opt.desc}</Typography>
                    </Box>
                  </Button>
                ))}
              </Box>

              <Box sx={{ mt: 3, display: "flex", flexDirection: "column", gap: 2 }}>
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
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={loading ? <CircularProgress size={18} /> : <LineChart size={18} />}
                  onClick={handleAnalyze}
                  disabled={loading}
                  fullWidth
                >
                  {loading ? "Analyzing..." : "Run Analysis"}
                </Button>
              </Box>
              {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ minHeight: 400 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                AI Report
              </Typography>
              {result ? (
                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    Model: {result.model_used}
                  </Typography>
                  <Typography
                    variant="body1"
                    sx={{ whiteSpace: "pre-wrap", lineHeight: 1.8 }}
                  >
                    {result.analysis}
                  </Typography>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 8 }}>
                  Select an analysis type and click &quot;Run Analysis&quot; to generate an AI report
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
