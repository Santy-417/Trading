"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  TextField,
  Typography,
  Alert,
  Snackbar,
  Stack,
} from "@mui/material";
import api from "@/lib/api";
import { useAppStore } from "@/store";
import type { OrderResponse } from "@/types";
import { OrderTypeSelect, type OrderTypeId } from "@/components/ui/order-type-select";
import { SelectDropdown } from "@/components/ui/select-dropdown";

const SYMBOLS = [
  { id: "EURUSD", label: "EUR/USD", description: "Euro vs US Dollar" },
  { id: "XAUUSD", label: "XAU/USD", description: "Gold vs US Dollar" },
];

// MT5 Error Code Humanization
const ERROR_CODES: Record<number, string> = {
  10004: "Requote - precio cambió, intenta de nuevo",
  10006: "Solicitud rechazada - verifica parámetros",
  10013: "Solicitud inválida",
  10014: "Volumen inválido para este símbolo",
  10015: "Precio inválido",
  10016: "SL/TP muy cerca del precio actual (aumenta distancia)",
  10018: "Mercado cerrado",
  10019: "No hay suficiente dinero",
  10027: "AutoTrading desactivado en MT5",
  10030: "Modo de ejecución no soportado (verificar broker)",
};

// Pip distances for quick-set buttons
const PIP_OPTIONS = [10, 20, 50, 100, 200];

// Pending order type mapping
const PENDING_DIRECTION_MAP: Record<Exclude<OrderTypeId, "market">, string> = {
  buy_limit: "BUY_LIMIT",
  sell_limit: "SELL_LIMIT",
  buy_stop: "BUY_STOP",
  sell_stop: "SELL_STOP",
};

interface SymbolInfo {
  bid: number;
  ask: number;
  digits: number;
  point: number;
  spread: number;
  trade_stops_level: number;
  volume_min: number;
  volume_max: number;
  volume_step: number;
}

export default function ManualTradeForm() {
  const { activeSymbol, setActiveSymbol } = useAppStore();
  const [orderType, setOrderType] = useState<OrderTypeId>("market");
  const [volume, setVolume] = useState("0.01");
  const [limitPrice, setLimitPrice] = useState("");
  const [sl, setSl] = useState("");
  const [tp, setTp] = useState("");
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState<SymbolInfo | null>(null);
  const [errors, setErrors] = useState<{
    volume?: string;
    sl?: string;
    tp?: string;
    limitPrice?: string;
  }>({});
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({ open: false, message: "", severity: "success" });

  const isMarket = orderType === "market";
  const isBuySide = orderType === "market" || orderType === "buy_limit" || orderType === "buy_stop";

  const fetchSymbolInfo = useCallback(async () => {
    try {
      const { data } = await api.get<SymbolInfo>("/orders/symbol-info", {
        params: { symbol: activeSymbol },
      });
      setInfo(data);
    } catch {
      // MT5 may not be connected
    }
  }, [activeSymbol]);

  useEffect(() => {
    fetchSymbolInfo();
    const interval = setInterval(fetchSymbolInfo, 3000);
    return () => clearInterval(interval);
  }, [fetchSymbolInfo]);

  // Reset limit price when switching order types
  useEffect(() => {
    setLimitPrice("");
    setErrors({});
  }, [orderType]);

  const formatPrice = (price: number) => {
    if (!info) return price.toString();
    return price.toFixed(info.digits);
  };

  const pipValue = info
    ? info.point * (info.digits === 3 || info.digits === 5 ? 10 : 1)
    : 0;

  const setSLByPips = (pips: number, direction: "BUY" | "SELL") => {
    if (!info) return;
    const price = direction === "BUY" ? info.ask : info.bid;
    const slPrice =
      direction === "BUY"
        ? price - pips * pipValue
        : price + pips * pipValue;
    setSl(formatPrice(slPrice));
  };

  const setTPByPips = (pips: number, direction: "BUY" | "SELL") => {
    if (!info) return;
    const price = direction === "BUY" ? info.ask : info.bid;
    const tpPrice =
      direction === "BUY"
        ? price + pips * pipValue
        : price - pips * pipValue;
    setTp(formatPrice(tpPrice));
  };

  // TAB autocomplete handlers
  const handleSLKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Tab" && !sl && info) {
      e.preventDefault();
      setSl(formatPrice(info.bid));
    }
  };

  const handleTPKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Tab" && !tp && info) {
      e.preventDefault();
      setTp(formatPrice(info.ask));
    }
  };

  const handleLimitPriceKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Tab" && !limitPrice && info) {
      e.preventDefault();
      setLimitPrice(formatPrice(isBuySide ? info.bid : info.ask));
    }
  };

  const handleNumericInput = (value: string, setter: (v: string) => void) => {
    if (value === "" || /^\d*\.?\d*$/.test(value)) {
      setter(value);
    }
  };

  const getLimitPriceHint = () => {
    if (!info) return "Press TAB to autocomplete";
    switch (orderType) {
      case "buy_limit":
        return `Debajo del precio actual (< ${formatPrice(info.ask)})`;
      case "sell_limit":
        return `Encima del precio actual (> ${formatPrice(info.bid)})`;
      case "buy_stop":
        return `Encima del precio actual (> ${formatPrice(info.ask)})`;
      case "sell_stop":
        return `Debajo del precio actual (< ${formatPrice(info.bid)})`;
      default:
        return "Press TAB to autocomplete";
    }
  };

  const validate = (direction: "BUY" | "SELL"): boolean => {
    const newErrors: typeof errors = {};
    const vol = parseFloat(volume);

    if (isNaN(vol) || vol <= 0) {
      newErrors.volume = "Must be > 0";
    } else if (info) {
      if (vol < info.volume_min) newErrors.volume = `Min: ${info.volume_min}`;
      if (vol > info.volume_max) newErrors.volume = `Max: ${info.volume_max}`;
    }

    if (!isMarket) {
      if (!limitPrice) {
        newErrors.limitPrice = "Price is required for pending orders";
      } else if (isNaN(parseFloat(limitPrice))) {
        newErrors.limitPrice = "Invalid number";
      }
    }

    if (sl && info) {
      const slVal = parseFloat(sl);
      if (isNaN(slVal)) {
        newErrors.sl = "Invalid number";
      } else {
        const price = direction === "BUY" ? info.ask : info.bid;
        const minDist = Math.max(info.trade_stops_level, 1) * info.point;
        if (direction === "BUY" && slVal >= price) {
          newErrors.sl = "SL must be below price for BUY";
        } else if (direction === "SELL" && slVal <= price) {
          newErrors.sl = "SL must be above price for SELL";
        } else if (direction === "BUY" && price - slVal < minDist) {
          newErrors.sl = `Min distance: ${formatPrice(price - minDist)}`;
        } else if (direction === "SELL" && slVal - price < minDist) {
          newErrors.sl = `Min distance: ${formatPrice(price + minDist)}`;
        }
      }
    }

    if (tp && info) {
      const tpVal = parseFloat(tp);
      if (isNaN(tpVal)) {
        newErrors.tp = "Invalid number";
      } else {
        const price = direction === "BUY" ? info.ask : info.bid;
        const minDist = Math.max(info.trade_stops_level, 1) * info.point;
        if (direction === "BUY" && tpVal <= price) {
          newErrors.tp = "TP must be above price for BUY";
        } else if (direction === "SELL" && tpVal >= price) {
          newErrors.tp = "TP must be below price for SELL";
        } else if (direction === "BUY" && tpVal - price < minDist) {
          newErrors.tp = `Min distance: ${formatPrice(price + minDist)}`;
        } else if (direction === "SELL" && price - tpVal < minDist) {
          newErrors.tp = `Min distance: ${formatPrice(price - minDist)}`;
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleTrade = async (direction: "BUY" | "SELL") => {
    if (!validate(direction)) return;

    setLoading(true);
    try {
      if (isMarket) {
        // Market execution
        const { data } = await api.post<OrderResponse>("/orders/market", {
          symbol: activeSymbol,
          direction,
          volume: parseFloat(volume),
          stop_loss: sl ? parseFloat(sl) : undefined,
          take_profit: tp ? parseFloat(tp) : undefined,
          comment: "manual",
        });
        if (data.success) {
          const timestamp = new Date().toLocaleTimeString();
          setSnackbar({
            open: true,
            message: `✓ ${direction} ${volume} ${activeSymbol} @ ${data.price}\nSL: ${sl || "None"} | TP: ${tp || "None"}\nTicket: #${data.ticket} | ${timestamp}`,
            severity: "success",
          });
          setSl("");
          setTp("");
        } else {
          const friendlyMsg =
            data.retcode
              ? ERROR_CODES[data.retcode] || data.comment
              : data.comment;
          setSnackbar({
            open: true,
            message: `Error: ${friendlyMsg}${data.retcode ? ` (code ${data.retcode})` : ""}`,
            severity: "error",
          });
        }
      } else {
        // Pending order (limit / stop)
        const pendingDirection =
          PENDING_DIRECTION_MAP[orderType as Exclude<OrderTypeId, "market">];
        const { data } = await api.post<OrderResponse>("/orders/limit", {
          symbol: activeSymbol,
          direction: pendingDirection,
          volume: parseFloat(volume),
          price: parseFloat(limitPrice),
          stop_loss: sl ? parseFloat(sl) : undefined,
          take_profit: tp ? parseFloat(tp) : undefined,
          comment: "manual-pending",
        });
        if (data.success) {
          const timestamp = new Date().toLocaleTimeString();
          setSnackbar({
            open: true,
            message: `✓ ${pendingDirection} placed @ ${limitPrice}\nVolume: ${volume} | SL: ${sl || "None"} | TP: ${tp || "None"}\nTicket: #${data.ticket} | ${timestamp}`,
            severity: "success",
          });
          setLimitPrice("");
          setSl("");
          setTp("");
        } else {
          const friendlyMsg =
            data.retcode
              ? ERROR_CODES[data.retcode] || data.comment
              : data.comment;
          setSnackbar({
            open: true,
            message: `Error: ${friendlyMsg}${data.retcode ? ` (code ${data.retcode})` : ""}`,
            severity: "error",
          });
        }
      }
    } catch (err: unknown) {
      setSnackbar({
        open: true,
        message: err instanceof Error ? err.message : "Order failed",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  // Determine SL pip buttons direction
  const slTpDirection = isBuySide ? "BUY" : "SELL";

  return (
    <Box>
      <Stack spacing={1.5}>
        {/* Symbol selector */}
        <SelectDropdown options={SYMBOLS} value={activeSymbol} onValueChange={setActiveSymbol} label="Symbol" />

        {/* Order type selector (21st.dev dropdown) */}
        <OrderTypeSelect value={orderType} onValueChange={setOrderType} />

        {/* Live price display */}
        {info && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              gap: 2,
              py: 0.5,
            }}
          >
            <Typography
              variant="body2"
              sx={{ fontFamily: "monospace", fontWeight: 700 }}
            >
              <Typography
                component="span"
                sx={{
                  color: "#22c55e",
                  fontFamily: "inherit",
                  fontWeight: "inherit",
                  fontSize: "inherit",
                }}
              >
                BID {formatPrice(info.bid)}
              </Typography>
            </Typography>
            <Typography
              variant="body2"
              sx={{ fontFamily: "monospace", fontWeight: 700 }}
            >
              <Typography
                component="span"
                sx={{
                  color: "#3b82f6",
                  fontFamily: "inherit",
                  fontWeight: "inherit",
                  fontSize: "inherit",
                }}
              >
                ASK {formatPrice(info.ask)}
              </Typography>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              spread: {info.spread}
            </Typography>
          </Box>
        )}

        {/* Price field — only for pending orders */}
        {!isMarket && (
          <TextField
            size="small"
            label="Price"
            value={limitPrice}
            onChange={(e) => handleNumericInput(e.target.value, setLimitPrice)}
            onKeyDown={handleLimitPriceKeyDown}
            error={!!errors.limitPrice}
            helperText={errors.limitPrice || getLimitPriceHint()}
            placeholder={info ? formatPrice(isBuySide ? info.bid : info.ask) : ""}
            fullWidth
            autoFocus
          />
        )}

        {/* Volume */}
        <TextField
          size="small"
          label="Volume (lots)"
          value={volume}
          onChange={(e) => handleNumericInput(e.target.value, setVolume)}
          error={!!errors.volume}
          helperText={
            errors.volume ||
            (info ? `Min: ${info.volume_min} / Step: ${info.volume_step}` : "")
          }
          fullWidth
        />

        {/* Stop Loss */}
        <Box>
          <TextField
            size="small"
            label="Stop Loss (price)"
            value={sl}
            onChange={(e) => handleNumericInput(e.target.value, setSl)}
            onKeyDown={handleSLKeyDown}
            error={!!errors.sl}
            helperText={errors.sl || "Optional — press TAB to autocomplete"}
            placeholder={info ? formatPrice(info.bid) : "Optional"}
            fullWidth
          />
          <Stack
            direction="row"
            spacing={0.5}
            sx={{ mt: 0.5, flexWrap: "wrap", gap: 0.5 }}
          >
            {PIP_OPTIONS.map((pips) => (
              <Chip
                key={`sl-${pips}`}
                label={`${pips}p`}
                size="small"
                variant="outlined"
                onClick={() => setSLByPips(pips, slTpDirection)}
                sx={{ fontSize: "0.7rem", height: 22, cursor: "pointer" }}
              />
            ))}
            {sl && (
              <Chip
                label="Clear"
                size="small"
                color="error"
                variant="outlined"
                onClick={() => {
                  setSl("");
                  setErrors((e) => ({ ...e, sl: undefined }));
                }}
                sx={{ fontSize: "0.7rem", height: 22, cursor: "pointer" }}
              />
            )}
          </Stack>
        </Box>

        {/* Take Profit */}
        <Box>
          <TextField
            size="small"
            label="Take Profit (price)"
            value={tp}
            onChange={(e) => handleNumericInput(e.target.value, setTp)}
            onKeyDown={handleTPKeyDown}
            error={!!errors.tp}
            helperText={errors.tp || "Optional — press TAB to autocomplete"}
            placeholder={info ? formatPrice(info.ask) : "Optional"}
            fullWidth
          />
          <Stack
            direction="row"
            spacing={0.5}
            sx={{ mt: 0.5, flexWrap: "wrap", gap: 0.5 }}
          >
            {PIP_OPTIONS.map((pips) => (
              <Chip
                key={`tp-${pips}`}
                label={`${pips}p`}
                size="small"
                variant="outlined"
                onClick={() => setTPByPips(pips, slTpDirection)}
                sx={{ fontSize: "0.7rem", height: 22, cursor: "pointer" }}
              />
            ))}
            {tp && (
              <Chip
                label="Clear"
                size="small"
                color="error"
                variant="outlined"
                onClick={() => {
                  setTp("");
                  setErrors((e) => ({ ...e, tp: undefined }));
                }}
                sx={{ fontSize: "0.7rem", height: 22, cursor: "pointer" }}
              />
            )}
          </Stack>
        </Box>

        {/* Trade buttons */}
        {isMarket ? (
          // Market: BUY + SELL
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              fullWidth
              disabled={loading || !info}
              onClick={() => handleTrade("BUY")}
              startIcon={
                loading ? (
                  <CircularProgress size={16} color="inherit" />
                ) : null
              }
              sx={{
                bgcolor: "#16a34a",
                "&:hover": { bgcolor: "#15803d" },
                fontWeight: 700,
                py: 1.2,
              }}
            >
              BUY{info ? ` ${formatPrice(info.ask)}` : ""}
            </Button>
            <Button
              variant="contained"
              fullWidth
              disabled={loading || !info}
              onClick={() => handleTrade("SELL")}
              startIcon={
                loading ? (
                  <CircularProgress size={16} color="inherit" />
                ) : null
              }
              sx={{
                bgcolor: "#dc2626",
                "&:hover": { bgcolor: "#b91c1c" },
                fontWeight: 700,
                py: 1.2,
              }}
            >
              SELL{info ? ` ${formatPrice(info.bid)}` : ""}
            </Button>
          </Stack>
        ) : isBuySide ? (
          // Buy Limit / Buy Stop: single green button
          <Button
            variant="contained"
            fullWidth
            disabled={loading || !info}
            onClick={() => handleTrade("BUY")}
            startIcon={
              loading ? <CircularProgress size={16} color="inherit" /> : null
            }
            sx={{
              bgcolor: "#16a34a",
              "&:hover": { bgcolor: "#15803d" },
              fontWeight: 700,
              py: 1.2,
            }}
          >
            {loading ? "Placing..." : `PLACE ${orderType.replace("_", " ").toUpperCase()}`}
          </Button>
        ) : (
          // Sell Limit / Sell Stop: single red button
          <Button
            variant="contained"
            fullWidth
            disabled={loading || !info}
            onClick={() => handleTrade("SELL")}
            startIcon={
              loading ? <CircularProgress size={16} color="inherit" /> : null
            }
            sx={{
              bgcolor: "#dc2626",
              "&:hover": { bgcolor: "#b91c1c" },
              fontWeight: 700,
              py: 1.2,
            }}
          >
            {loading ? "Placing..." : `PLACE ${orderType.replace("_", " ").toUpperCase()}`}
          </Button>
        )}
      </Stack>

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
