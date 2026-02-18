"use client";

import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  Alert,
  CircularProgress,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import AssessmentIcon from "@mui/icons-material/Assessment";
import TuneIcon from "@mui/icons-material/Tune";
import ShieldIcon from "@mui/icons-material/Shield";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import api from "@/lib/api";
import type { AIResponse } from "@/types";

type AnalysisType = "trades" | "summary" | "parameters" | "risk" | "compare";

export default function AnalysisPage() {
  const [analysisType, setAnalysisType] = useState<AnalysisType>("trades");
  const [days, setDays] = useState(7);
  const [period, setPeriod] = useState("weekly");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIResponse | null>(null);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      let endpoint = "";
      let payload: Record<string, unknown> = {};

      switch (analysisType) {
        case "trades":
          endpoint = "/ai/analyze-trades";
          payload = { days };
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
          payload = { days };
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
    { value: "trades", label: "Trade Analysis", icon: <AutoGraphIcon />, desc: "Analyze recent trading patterns" },
    { value: "summary", label: "Performance Summary", icon: <AssessmentIcon />, desc: "Generate performance report" },
    { value: "parameters", label: "Parameter Suggestions", icon: <TuneIcon />, desc: "AI-suggested risk parameters" },
    { value: "risk", label: "Risk Review", icon: <ShieldIcon />, desc: "Review risk events and anomalies" },
    { value: "compare", label: "Strategy Comparison", icon: <CompareArrowsIcon />, desc: "Compare strategy performance" },
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
                  <TextField
                    size="small"
                    label="Days to analyze"
                    type="number"
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                    inputProps={{ min: 1, max: 90 }}
                    fullWidth
                  />
                )}
                {analysisType === "summary" && (
                  <FormControl size="small" fullWidth>
                    <InputLabel>Period</InputLabel>
                    <Select value={period} label="Period" onChange={(e) => setPeriod(e.target.value)}>
                      <MenuItem value="weekly">Weekly</MenuItem>
                      <MenuItem value="monthly">Monthly</MenuItem>
                    </Select>
                  </FormControl>
                )}
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={loading ? <CircularProgress size={18} /> : <AutoGraphIcon />}
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
