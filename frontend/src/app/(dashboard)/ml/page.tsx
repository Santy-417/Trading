"use client";

import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import api from "@/lib/api";
import type { TrainResponse, PredictResponse, MLModel } from "@/types";

export default function MLPage() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [bars, setBars] = useState(5000);
  const [loading, setLoading] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResponse | null>(null);
  const [prediction, setPrediction] = useState<PredictResponse | null>(null);
  const [models, setModels] = useState<MLModel[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/ml/models").then(({ data }) => setModels(data.models || [])).catch(() => {});
  }, []);

  const handleTrain = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post<TrainResponse>("/ml/train", { symbol, timeframe, bars });
      setTrainResult(data);
      // Refresh models list
      const modelsRes = await api.get("/ml/models");
      setModels(modelsRes.data.models || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Training failed");
    } finally {
      setLoading(false);
    }
  };

  const handlePredict = async (modelId: string) => {
    try {
      const { data } = await api.post<PredictResponse>("/ml/predict", {
        model_id: modelId,
        symbol,
        timeframe,
        bars: 500,
      });
      setPrediction(data);
    } catch {
      setError("Prediction failed");
    }
  };

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        ML Models
      </Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Train New Model
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <FormControl size="small" fullWidth>
                  <InputLabel>Symbol</InputLabel>
                  <Select value={symbol} label="Symbol" onChange={(e) => setSymbol(e.target.value)}>
                    {["EURUSD", "XAUUSD"].map((s) => (
                      <MenuItem key={s} value={s}>{s}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel>Timeframe</InputLabel>
                  <Select value={timeframe} label="Timeframe" onChange={(e) => setTimeframe(e.target.value)}>
                    {["M5", "M15", "H1", "H4", "D1"].map((tf) => (
                      <MenuItem key={tf} value={tf}>{tf}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  size="small"
                  label="Historical Bars"
                  type="number"
                  value={bars}
                  onChange={(e) => setBars(Number(e.target.value))}
                />
                <Button
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={18} /> : <ModelTrainingIcon />}
                  onClick={handleTrain}
                  disabled={loading}
                  fullWidth
                >
                  {loading ? "Training..." : "Train Model"}
                </Button>
              </Box>
              {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
            </CardContent>
          </Card>

          {prediction && (
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1 }}>Prediction</Typography>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  <Chip
                    label={prediction.signal}
                    color={prediction.signal === "BUY" ? "success" : prediction.signal === "SELL" ? "error" : "default"}
                    sx={{ alignSelf: "flex-start" }}
                  />
                  <Typography variant="body2">Probability: {(prediction.probability * 100).toFixed(1)}%</Typography>
                  <Typography variant="body2">Confidence: {prediction.confidence}</Typography>
                </Box>
              </CardContent>
            </Card>
          )}
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          {trainResult && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1 }}>Training Results</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Model ID: {trainResult.model_id}
                </Typography>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 6 }}>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>Metrics</Typography>
                    <Table size="small">
                      <TableBody>
                        {Object.entries(trainResult.metrics).map(([key, val]) => (
                          <TableRow key={key}>
                            <TableCell>{key}</TableCell>
                            <TableCell align="right">{typeof val === "number" ? val.toFixed(4) : val}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Grid>
                  <Grid size={{ xs: 6 }}>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>Top Features</Typography>
                    <Table size="small">
                      <TableBody>
                        {Object.entries(trainResult.top_features).slice(0, 10).map(([key, val]) => (
                          <TableRow key={key}>
                            <TableCell>{key}</TableCell>
                            <TableCell align="right">{typeof val === "number" ? val.toFixed(4) : val}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Saved Models</Typography>
              {models.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 4 }}>
                  No models trained yet
                </Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Model ID</TableCell>
                      <TableCell>Symbol</TableCell>
                      <TableCell>Timeframe</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell align="center">Action</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {models.map((m) => (
                      <TableRow key={m.model_id}>
                        <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{m.model_id.slice(0, 12)}...</TableCell>
                        <TableCell>{m.symbol}</TableCell>
                        <TableCell>{m.timeframe}</TableCell>
                        <TableCell>{new Date(m.created_at).toLocaleDateString()}</TableCell>
                        <TableCell align="center">
                          <Button size="small" startIcon={<AutoFixHighIcon />} onClick={() => handlePredict(m.model_id)}>
                            Predict
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
