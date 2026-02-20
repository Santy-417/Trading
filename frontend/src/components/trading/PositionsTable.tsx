"use client";

import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import EditIcon from "@mui/icons-material/Edit";
import CancelIcon from "@mui/icons-material/Cancel";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import api from "@/lib/api";
import type { PendingOrder, Position } from "@/types";
import { useAppStore } from "@/store";

interface PositionsTableProps {
  positions: Position[];
  onRefresh: () => void;
  pendingOrders?: PendingOrder[];
}

type ConfirmAction =
  | { kind: "close"; ticket: number; symbol: string; type: string; profit: number }
  | { kind: "cancel"; ticket: number; symbol: string; orderType: string }
  | { kind: "close_all" }
  | { kind: "close_winners" }
  | { kind: "close_losers" };

const PENDING_TYPE_COLOR: Record<string, "success" | "error" | "warning"> = {
  BUY_LIMIT: "success",
  BUY_STOP: "success",
  SELL_LIMIT: "error",
  SELL_STOP: "error",
};

export default function PositionsTable({
  positions,
  onRefresh,
  pendingOrders = [],
}: PositionsTableProps) {
  const { accountInfo } = useAppStore();

  // ── Modify dialog state ──
  const [modifyTarget, setModifyTarget] = useState<Position | null>(null);
  const [modifySL, setModifySL] = useState("");
  const [modifyTP, setModifyTP] = useState("");
  const [modifyVolume, setModifyVolume] = useState("");
  const [modifyLoading, setModifyLoading] = useState(false);

  // ── Confirmation dialog state ──
  const [confirmAction, setConfirmAction] = useState<ConfirmAction | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);

  // ── Snackbar ──
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({ open: false, message: "", severity: "success" });

  const showSnackbar = (message: string, severity: "success" | "error") =>
    setSnackbar({ open: true, message, severity });

  // ── Modify helpers ──
  const openModifyDialog = (pos: Position) => {
    setModifyTarget(pos);
    setModifySL(pos.stop_loss && pos.stop_loss !== 0 ? pos.stop_loss.toFixed(5) : "");
    setModifyTP(pos.take_profit && pos.take_profit !== 0 ? pos.take_profit.toFixed(5) : "");
    setModifyVolume("");
  };

  const closeModifyDialog = () => {
    setModifyTarget(null);
    setModifySL("");
    setModifyTP("");
    setModifyVolume("");
  };

  const handleNumericInput = (value: string, setter: (v: string) => void) => {
    if (value === "" || /^\d*\.?\d*$/.test(value)) setter(value);
  };

  // ── Confirmation helpers ──
  const getConfirmTitle = (action: ConfirmAction): string => {
    switch (action.kind) {
      case "close":
        return `Close Position #${action.ticket}`;
      case "cancel":
        return `Cancel Order #${action.ticket}`;
      case "close_all":
        return `Close All Positions (${positions.length})`;
      case "close_winners":
        return `Close All Winning Positions`;
      case "close_losers":
        return `Close All Losing Positions`;
    }
  };

  const getConfirmBody = (action: ConfirmAction): string => {
    switch (action.kind) {
      case "close":
        return `${action.type} ${action.symbol} — P&L: $${action.profit.toFixed(2)}. This action cannot be undone.`;
      case "cancel":
        return `${action.orderType} ${action.symbol}. This pending order will be removed.`;
      case "close_all":
        return `All ${positions.length} open position${positions.length !== 1 ? "s" : ""} will be closed at market price. This cannot be undone.`;
      case "close_winners": {
        const winners = positions.filter((p) => p.profit > 0);
        return `${winners.length} winning position${winners.length !== 1 ? "s" : ""} will be closed at market price.`;
      }
      case "close_losers": {
        const losers = positions.filter((p) => p.profit < 0);
        return `${losers.length} losing position${losers.length !== 1 ? "s" : ""} will be closed at market price.`;
      }
    }
  };

  // ── Execute confirmed action ──
  const executeConfirm = async () => {
    if (!confirmAction) return;
    setConfirmLoading(true);
    try {
      if (confirmAction.kind === "close") {
        await api.post("/orders/close", { ticket: confirmAction.ticket });
        showSnackbar(`Position #${confirmAction.ticket} closed`, "success");
      } else if (confirmAction.kind === "cancel") {
        await api.post("/orders/cancel", { ticket: confirmAction.ticket });
        showSnackbar(`Order #${confirmAction.ticket} cancelled`, "success");
      } else {
        // Bulk operations
        let targets: Position[] = [];
        if (confirmAction.kind === "close_all") targets = positions;
        else if (confirmAction.kind === "close_winners")
          targets = positions.filter((p) => p.profit > 0);
        else if (confirmAction.kind === "close_losers")
          targets = positions.filter((p) => p.profit < 0);

        const results = await Promise.allSettled(
          targets.map((p) => api.post("/orders/close", { ticket: p.ticket }))
        );
        const succeeded = results.filter((r) => r.status === "fulfilled").length;
        const failed = results.filter((r) => r.status === "rejected").length;
        if (failed === 0) {
          showSnackbar(`${succeeded} position${succeeded !== 1 ? "s" : ""} closed successfully`, "success");
        } else {
          showSnackbar(`${succeeded} closed, ${failed} failed`, "error");
        }
      }
      onRefresh();
    } catch {
      showSnackbar("Operation failed", "error");
    } finally {
      setConfirmLoading(false);
      setConfirmAction(null);
    }
  };

  // ── Modify submit ──
  const handleModify = async () => {
    if (!modifyTarget) return;
    setModifyLoading(true);
    try {
      const body: Record<string, number> = { ticket: modifyTarget.ticket };
      if (modifySL) body.stop_loss = parseFloat(modifySL);
      if (modifyTP) body.take_profit = parseFloat(modifyTP);
      if (modifyVolume) body.volume = parseFloat(modifyVolume);

      const { data } = await api.post<{ success: boolean; comment: string }>(
        "/orders/modify",
        body
      );

      if (data.success) {
        showSnackbar(
          modifyVolume
            ? `Partial close: ${modifyVolume} lots from #${modifyTarget.ticket}`
            : `Position #${modifyTarget.ticket} modified`,
          "success"
        );
        closeModifyDialog();
        onRefresh();
      } else {
        showSnackbar(`Modify failed: ${data.comment}`, "error");
      }
    } catch {
      showSnackbar("Failed to modify position", "error");
    } finally {
      setModifyLoading(false);
    }
  };

  // ── Footer calculations ──
  const totalProfit = positions.reduce((sum, p) => sum + p.profit, 0);
  const balance = accountInfo?.balance ?? null;
  const equity = accountInfo?.equity ?? null;
  const margin = accountInfo?.margin ?? null;
  const freeMargin = accountInfo?.free_margin ?? null;
  const marginLevel =
    margin && margin > 0 && equity !== null ? (equity / margin) * 100 : null;

  const fmt = (v: number | null) =>
    v !== null
      ? `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : "--";

  const winners = positions.filter((p) => p.profit > 0);
  const losers = positions.filter((p) => p.profit < 0);

  return (
    <>
      <Card>
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>

          {/* ── Header ── */}
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", px: 2, pt: 2, pb: 1 }}>
            <Typography variant="h6">Positions & Orders</Typography>
            <Button size="small" onClick={onRefresh}>Refresh</Button>
          </Box>

          {/* ── Open Positions label + bulk buttons ── */}
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", px: 2, pb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
              Open Positions ({positions.length})
            </Typography>
            {positions.length > 0 && (
              <Stack direction="row" spacing={0.5}>
                {winners.length > 0 && (
                  <Tooltip title={`Close ${winners.length} winning position${winners.length !== 1 ? "s" : ""}`}>
                    <Button
                      size="small"
                      variant="outlined"
                      color="success"
                      sx={{ fontSize: "0.65rem", py: 0.25, px: 1, minWidth: 0 }}
                      onClick={() => setConfirmAction({ kind: "close_winners" })}
                    >
                      Close Winners ({winners.length})
                    </Button>
                  </Tooltip>
                )}
                {losers.length > 0 && (
                  <Tooltip title={`Close ${losers.length} losing position${losers.length !== 1 ? "s" : ""}`}>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      sx={{ fontSize: "0.65rem", py: 0.25, px: 1, minWidth: 0 }}
                      onClick={() => setConfirmAction({ kind: "close_losers" })}
                    >
                      Close Losers ({losers.length})
                    </Button>
                  </Tooltip>
                )}
                <Tooltip title="Close all open positions">
                  <Button
                    size="small"
                    variant="outlined"
                    color="warning"
                    sx={{ fontSize: "0.65rem", py: 0.25, px: 1, minWidth: 0 }}
                    onClick={() => setConfirmAction({ kind: "close_all" })}
                  >
                    Close All
                  </Button>
                </Tooltip>
              </Stack>
            )}
          </Box>

          {/* ── Open positions table ── */}
          {positions.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 2, px: 2 }}>
              No open positions
            </Typography>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ "& th": { fontSize: "0.7rem", py: 0.5 } }}>
                    <TableCell>Ticket</TableCell>
                    <TableCell>Symbol</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell align="right">Volume</TableCell>
                    <TableCell align="right">Entry</TableCell>
                    <TableCell align="right">Current</TableCell>
                    <TableCell align="right">SL</TableCell>
                    <TableCell align="right">TP</TableCell>
                    <TableCell align="right">P&L</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {positions.map((pos) => (
                    <TableRow key={pos.ticket}>
                      <TableCell sx={{ fontSize: "0.75rem" }}>{pos.ticket}</TableCell>
                      <TableCell sx={{ fontSize: "0.75rem" }}>{pos.symbol}</TableCell>
                      <TableCell>
                        <Chip
                          label={pos.type}
                          size="small"
                          color={pos.type === "BUY" ? "success" : "error"}
                          variant="outlined"
                          sx={{ fontSize: "0.65rem", height: 20 }}
                        />
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>{pos.volume}</TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>{pos.price_open.toFixed(5)}</TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>{pos.price_current.toFixed(5)}</TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>
                        {pos.stop_loss && pos.stop_loss !== 0 ? pos.stop_loss.toFixed(5) : "-"}
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>
                        {pos.take_profit && pos.take_profit !== 0 ? pos.take_profit.toFixed(5) : "-"}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ color: pos.profit >= 0 ? "success.main" : "error.main", fontWeight: 600, fontSize: "0.75rem" }}
                      >
                        ${pos.profit.toFixed(2)}
                      </TableCell>
                      <TableCell align="center">
                        <Stack direction="row" spacing={0.5} justifyContent="center">
                          <Tooltip title="Modify SL/TP or partial close">
                            <IconButton size="small" color="primary" onClick={() => openModifyDialog(pos)}>
                              <EditIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Close position">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() =>
                                setConfirmAction({
                                  kind: "close",
                                  ticket: pos.ticket,
                                  symbol: pos.symbol,
                                  type: pos.type,
                                  profit: pos.profit,
                                })
                              }
                            >
                              <CloseIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {/* ── Pending Orders section ── */}
          <Divider sx={{ mt: 1 }} />
          <Box sx={{ px: 2, pt: 1, pb: 0.5, bgcolor: "rgba(59,130,246,0.04)" }}>
            <Typography variant="caption" color="primary.light" sx={{ fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
              Pending Orders ({pendingOrders.length})
            </Typography>
          </Box>

          {pendingOrders.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 2, bgcolor: "rgba(59,130,246,0.04)" }}>
              No pending orders
            </Typography>
          ) : (
            <TableContainer sx={{ bgcolor: "rgba(59,130,246,0.04)" }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ "& th": { fontSize: "0.7rem", py: 0.5 } }}>
                    <TableCell>Ticket</TableCell>
                    <TableCell>Symbol</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell align="right">Volume</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">Current</TableCell>
                    <TableCell align="right">SL</TableCell>
                    <TableCell align="right">TP</TableCell>
                    <TableCell align="center">Cancel</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pendingOrders.map((order) => (
                    <TableRow key={order.ticket}>
                      <TableCell sx={{ fontSize: "0.75rem" }}>{order.ticket}</TableCell>
                      <TableCell sx={{ fontSize: "0.75rem" }}>{order.symbol}</TableCell>
                      <TableCell>
                        <Chip
                          label={order.type.replace("_", " ")}
                          size="small"
                          color={PENDING_TYPE_COLOR[order.type] ?? "warning"}
                          variant="outlined"
                          sx={{ fontSize: "0.65rem", height: 20 }}
                        />
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>{order.volume_current}</TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>{order.price_open.toFixed(5)}</TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>{order.price_current.toFixed(5)}</TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>
                        {order.stop_loss && order.stop_loss !== 0 ? order.stop_loss.toFixed(5) : "-"}
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: "0.75rem" }}>
                        {order.take_profit && order.take_profit !== 0 ? order.take_profit.toFixed(5) : "-"}
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="Cancel order">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() =>
                              setConfirmAction({
                                kind: "cancel",
                                ticket: order.ticket,
                                symbol: order.symbol,
                                orderType: order.type,
                              })
                            }
                          >
                            <CancelIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {/* ── Footer bar (MT5 style) ── */}
          <Divider />
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 0,
              px: 2,
              py: 1,
              bgcolor: "rgba(0,0,0,0.2)",
            }}
          >
            {[
              {
                label: "Profit",
                value: fmt(totalProfit),
                color: totalProfit >= 0 ? "success.main" : "error.main",
                bold: true,
              },
              { label: "Balance", value: fmt(balance) },
              { label: "Equity", value: fmt(equity) },
              { label: "Margin", value: fmt(margin) },
              {
                label: "Free Margin",
                value: fmt(freeMargin),
                color: freeMargin !== null && freeMargin < 0 ? "error.main" : undefined,
              },
              {
                label: "Margin Level",
                value: marginLevel !== null ? `${marginLevel.toFixed(2)}%` : "--",
                color:
                  marginLevel === null
                    ? undefined
                    : marginLevel < 100
                    ? "error.main"
                    : marginLevel < 200
                    ? "warning.main"
                    : "success.main",
              },
            ].map((item, i, arr) => (
              <Box
                key={item.label}
                sx={{
                  pr: 2,
                  mr: 2,
                  borderRight: i < arr.length - 1 ? "1px solid" : "none",
                  borderColor: "divider",
                }}
              >
                <Typography variant="caption" color="text.secondary" display="block">
                  {item.label}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: item.bold ? 700 : 600,
                    fontFamily: "monospace",
                    color: item.color ?? "inherit",
                  }}
                >
                  {item.value}
                </Typography>
              </Box>
            ))}
          </Box>
        </CardContent>
      </Card>

      {/* ── Confirmation Dialog ── */}
      <Dialog
        open={!!confirmAction}
        onClose={() => !confirmLoading && setConfirmAction(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <WarningAmberIcon color="warning" fontSize="small" />
          {confirmAction ? getConfirmTitle(confirmAction) : ""}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {confirmAction ? getConfirmBody(confirmAction) : ""}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmAction(null)} disabled={confirmLoading}>
            Cancel
          </Button>
          <Button
            onClick={executeConfirm}
            variant="contained"
            color={
              confirmAction?.kind === "close_winners"
                ? "success"
                : confirmAction?.kind === "close_losers"
                ? "error"
                : "warning"
            }
            disabled={confirmLoading}
            startIcon={
              confirmLoading ? (
                <span
                  style={{
                    width: 14,
                    height: 14,
                    border: "2px solid currentColor",
                    borderTopColor: "transparent",
                    borderRadius: "50%",
                    display: "inline-block",
                    animation: "spin 0.6s linear infinite",
                  }}
                />
              ) : null
            }
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Modify Position Dialog ── */}
      <Dialog open={!!modifyTarget} onClose={closeModifyDialog} maxWidth="xs" fullWidth>
        <DialogTitle>
          Modify Position #{modifyTarget?.ticket}
          {modifyTarget && (
            <Typography variant="caption" display="block" color="text.secondary">
              {modifyTarget.type} {modifyTarget.volume} {modifyTarget.symbol} @{" "}
              {modifyTarget.price_open.toFixed(5)} — P&L: ${modifyTarget.profit.toFixed(2)}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              size="small"
              label="Stop Loss"
              value={modifySL}
              onChange={(e) => handleNumericInput(e.target.value, setModifySL)}
              placeholder="Leave empty to keep current"
              helperText={
                modifyTarget?.stop_loss && modifyTarget.stop_loss !== 0
                  ? `Current: ${modifyTarget.stop_loss.toFixed(5)}`
                  : "No SL set"
              }
              fullWidth
            />
            <TextField
              size="small"
              label="Take Profit"
              value={modifyTP}
              onChange={(e) => handleNumericInput(e.target.value, setModifyTP)}
              placeholder="Leave empty to keep current"
              helperText={
                modifyTarget?.take_profit && modifyTarget.take_profit !== 0
                  ? `Current: ${modifyTarget.take_profit.toFixed(5)}`
                  : "No TP set"
              }
              fullWidth
            />
            <TextField
              size="small"
              label="Close Volume (partial close)"
              value={modifyVolume}
              onChange={(e) => handleNumericInput(e.target.value, setModifyVolume)}
              placeholder="Leave empty to only update SL/TP"
              helperText={
                modifyTarget
                  ? `Max: ${modifyTarget.volume} lots — leave empty to only update SL/TP`
                  : ""
              }
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeModifyDialog} disabled={modifyLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleModify}
            variant="contained"
            disabled={modifyLoading}
            startIcon={
              modifyLoading ? (
                <span
                  style={{
                    width: 14,
                    height: 14,
                    border: "2px solid currentColor",
                    borderTopColor: "transparent",
                    borderRadius: "50%",
                    display: "inline-block",
                    animation: "spin 0.6s linear infinite",
                  }}
                />
              ) : null
            }
          >
            {modifyVolume ? "Partial Close" : "Apply Changes"}
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
    </>
  );
}
