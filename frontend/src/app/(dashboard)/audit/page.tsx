"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  TablePagination,
  Button,
  TextField,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Skeleton,
  Tooltip,
} from "@mui/material";
import { SelectDropdown } from "@/components/ui/select-dropdown";
import {
  FileText,
  Download,
  X,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ArrowUpRight,
  ArrowDownRight,
  RotateCcw,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import api from "@/lib/api";
import type { Trade } from "@/types";

type SortField = "date" | "profit" | "lot_size";
type SortDir = "asc" | "desc";

export default function AuditPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [strategyFilter, setStrategyFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [loading, setLoading] = useState(true);
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);

  const fetchTrades = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page: page + 1,
        page_size: rowsPerPage,
      };
      if (symbolFilter) params.symbol = symbolFilter;
      if (strategyFilter) params.strategy = strategyFilter;

      const { data } = await api.get("/orders/history", { params });
      setTrades(data.trades || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error("Failed to fetch trade history:", error);
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, symbolFilter, strategyFilter]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  // Client-side sorting and date filtering
  const sortedTrades = useMemo(() => {
    let filtered = [...trades];

    // Date filtering
    if (dateFrom) {
      const from = new Date(dateFrom);
      filtered = filtered.filter((t) => new Date(t.opened_at) >= from);
    }
    if (dateTo) {
      const to = new Date(dateTo);
      to.setHours(23, 59, 59, 999);
      filtered = filtered.filter((t) => new Date(t.opened_at) <= to);
    }

    // Sorting
    filtered.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case "date":
          cmp = new Date(a.opened_at).getTime() - new Date(b.opened_at).getTime();
          break;
        case "profit":
          cmp = (a.profit ?? 0) - (b.profit ?? 0);
          break;
        case "lot_size":
          cmp = a.lot_size - b.lot_size;
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return filtered;
  }, [trades, dateFrom, dateTo, sortField, sortDir]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const handleReset = () => {
    setSymbolFilter("");
    setStrategyFilter("");
    setDateFrom("");
    setDateTo("");
    setPage(0);
  };

  const handleExportCSV = () => {
    const headers = ["Date", "Symbol", "Direction", "Strategy", "Lot Size", "Entry", "Exit", "P&L", "Commission", "Swap", "Status"];
    const rows = sortedTrades.map((t) => [
      new Date(t.opened_at).toISOString(),
      t.symbol,
      t.direction,
      t.strategy,
      t.lot_size,
      t.entry_price.toFixed(5),
      t.exit_price?.toFixed(5) ?? "",
      t.profit?.toFixed(2) ?? "",
      t.commission?.toFixed(2) ?? "0",
      t.swap?.toFixed(2) ?? "0",
      t.status,
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trades_${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown size={12} style={{ opacity: 0.3 }} />;
    return sortDir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />;
  };

  const hasFilters = symbolFilter || strategyFilter || dateFrom || dateTo;

  return (
    <Box>
      {/* Page header */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 2,
              bgcolor: "rgba(59, 130, 246, 0.1)",
              border: "1px solid rgba(59, 130, 246, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <FileText size={22} style={{ color: "#7c3aed" }} />
          </Box>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.2, fontSize: 20 }}>
              Audit Log
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.25 }}>
              <Typography variant="caption" sx={{ color: "#64748b", fontSize: 11 }}>
                Trade History
              </Typography>
              <Chip
                label={`${total} trade${total !== 1 ? "s" : ""}`}
                size="small"
                sx={{
                  height: 18,
                  fontSize: 9,
                  fontWeight: 600,
                  bgcolor: "rgba(148,163,184,0.06)",
                  color: "#94a3b8",
                }}
              />
            </Box>
          </Box>
        </Box>

        <Button
          variant="outlined"
          size="small"
          startIcon={<Download size={14} />}
          onClick={handleExportCSV}
          disabled={sortedTrades.length === 0}
          sx={{
            textTransform: "none",
            fontSize: 12,
            fontWeight: 600,
            borderColor: "rgba(148,163,184,0.15)",
            color: "#94a3b8",
            "&:hover": { borderColor: "rgba(124,58,237,0.3)", color: "#7c3aed" },
          }}
        >
          Export CSV
        </Button>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
            <Box sx={{ minWidth: 140 }}>
              <SelectDropdown
                label="Symbol"
                value={symbolFilter}
                onValueChange={(v) => { setSymbolFilter(v); setPage(0); }}
                options={[
                  { id: "", label: "All Symbols" },
                  { id: "EURUSD", label: "EUR/USD" },
                  { id: "XAUUSD", label: "XAU/USD" },
                  { id: "DXY", label: "DXY" },
                  { id: "USDCAD", label: "USD/CAD" },
                  { id: "GBPUSD", label: "GBP/USD" },
                  { id: "AUDCAD", label: "AUD/CAD" },
                  { id: "EURJPY", label: "EUR/JPY" },
                  { id: "USDJPY", label: "USD/JPY" },
                  { id: "EURGBP", label: "EUR/GBP" },
                ]}
              />
            </Box>
            <Box sx={{ minWidth: 140 }}>
              <SelectDropdown
                label="Strategy"
                value={strategyFilter}
                onValueChange={(v) => { setStrategyFilter(v); setPage(0); }}
                options={[
                  { id: "", label: "All Strategies" },
                  { id: "bias", label: "Bias V1 (SMC)" },
                  { id: "fibonacci", label: "Fibonacci" },
                  { id: "ict", label: "ICT" },
                  { id: "hybrid_ml", label: "Hybrid ML" },
                  { id: "manual", label: "Manual" },
                ]}
              />
            </Box>
            <TextField
              type="date"
              label="From"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
              size="small"
              InputLabelProps={{ shrink: true }}
              sx={{
                width: 160,
                "& .MuiOutlinedInput-root": {
                  fontSize: 12,
                  "& fieldset": { borderColor: "rgba(148,163,184,0.15)" },
                },
                "& .MuiInputLabel-root": { fontSize: 12 },
              }}
            />
            <TextField
              type="date"
              label="To"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
              size="small"
              InputLabelProps={{ shrink: true }}
              sx={{
                width: 160,
                "& .MuiOutlinedInput-root": {
                  fontSize: 12,
                  "& fieldset": { borderColor: "rgba(148,163,184,0.15)" },
                },
                "& .MuiInputLabel-root": { fontSize: 12 },
              }}
            />
            {hasFilters && (
              <Tooltip title="Reset all filters" arrow>
                <IconButton
                  size="small"
                  onClick={handleReset}
                  sx={{
                    color: "#64748b",
                    "&:hover": { color: "#ef4444", bgcolor: "rgba(239,68,68,0.08)" },
                  }}
                >
                  <RotateCcw size={16} />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell
                    onClick={() => handleSort("date")}
                    sx={{ cursor: "pointer", userSelect: "none", "&:hover": { color: "text.primary" } }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                      Date <SortIcon field="date" />
                    </Box>
                  </TableCell>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Direction</TableCell>
                  <TableCell>Strategy</TableCell>
                  <TableCell
                    align="right"
                    onClick={() => handleSort("lot_size")}
                    sx={{ cursor: "pointer", userSelect: "none", "&:hover": { color: "text.primary" } }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 0.5 }}>
                      Lot <SortIcon field="lot_size" />
                    </Box>
                  </TableCell>
                  <TableCell align="right">Entry</TableCell>
                  <TableCell align="right">Exit</TableCell>
                  <TableCell
                    align="right"
                    onClick={() => handleSort("profit")}
                    sx={{ cursor: "pointer", userSelect: "none", "&:hover": { color: "text.primary" } }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 0.5 }}>
                      P&L <SortIcon field="profit" />
                    </Box>
                  </TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 9 }).map((_, j) => (
                        <TableCell key={j}>
                          <Skeleton variant="text" width={j === 0 ? 120 : 60} />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : sortedTrades.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align="center" sx={{ py: 8 }}>
                      <Box sx={{ textAlign: "center" }}>
                        <FileText size={40} style={{ color: "#334155", marginBottom: 12 }} />
                        <Typography sx={{ color: "#64748b", fontSize: 13 }}>
                          {hasFilters
                            ? "No trades match your filters"
                            : "No trade history found"}
                        </Typography>
                        <Typography sx={{ color: "#475569", fontSize: 11, mt: 0.5, mb: 2 }}>
                          {hasFilters
                            ? "Try adjusting or resetting filters"
                            : "Close positions or sync from MetaTrader 5"}
                        </Typography>
                        {hasFilters && (
                          <Button
                            variant="outlined"
                            size="small"
                            startIcon={<RotateCcw size={14} />}
                            onClick={handleReset}
                            sx={{ textTransform: "none", fontSize: 12 }}
                          >
                            Reset Filters
                          </Button>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedTrades.map((trade) => {
                    const isProfit = (trade.profit ?? 0) >= 0;
                    return (
                      <TableRow
                        key={trade.id}
                        hover
                        onClick={() => setSelectedTrade(trade)}
                        sx={{
                          cursor: "pointer",
                          transition: "background-color 0.1s",
                          "&:hover": { bgcolor: "rgba(148,163,184,0.04)" },
                        }}
                      >
                        <TableCell sx={{ fontSize: 11, fontFamily: "monospace", color: "#94a3b8" }}>
                          {new Date(trade.opened_at).toLocaleDateString()}{" "}
                          <span style={{ color: "#475569" }}>
                            {new Date(trade.opened_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Typography sx={{ fontSize: 12, fontWeight: 600 }}>{trade.symbol}</Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={trade.direction}
                            size="small"
                            sx={{
                              height: 20,
                              fontSize: 10,
                              fontWeight: 600,
                              bgcolor: trade.direction === "BUY" ? "rgba(59,130,246,0.08)" : "rgba(249,115,22,0.08)",
                              color: trade.direction === "BUY" ? "#3b82f6" : "#f97316",
                              border: `1px solid ${trade.direction === "BUY" ? "rgba(59,130,246,0.2)" : "rgba(249,115,22,0.2)"}`,
                            }}
                          />
                        </TableCell>
                        <TableCell sx={{ fontSize: 11, color: "#94a3b8" }}>{trade.strategy}</TableCell>
                        <TableCell align="right" sx={{ fontSize: 11, fontFamily: "monospace" }}>
                          {trade.lot_size}
                        </TableCell>
                        <TableCell align="right" sx={{ fontSize: 11, fontFamily: "monospace" }}>
                          {trade.entry_price.toFixed(5)}
                        </TableCell>
                        <TableCell align="right" sx={{ fontSize: 11, fontFamily: "monospace" }}>
                          {trade.exit_price?.toFixed(5) ?? "-"}
                        </TableCell>
                        <TableCell align="right">
                          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 0.5 }}>
                            {isProfit ? (
                              <ArrowUpRight size={12} style={{ color: "#22c55e" }} />
                            ) : (
                              <ArrowDownRight size={12} style={{ color: "#ef4444" }} />
                            )}
                            <Typography
                              sx={{
                                fontSize: 12,
                                fontWeight: 600,
                                color: isProfit ? "#22c55e" : "#ef4444",
                                fontFeatureSettings: '"tnum"',
                              }}
                            >
                              {trade.profit != null ? `$${trade.profit.toFixed(2)}` : "-"}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box
                            sx={{
                              width: 6,
                              height: 6,
                              borderRadius: "50%",
                              bgcolor: trade.status === "closed" ? "#64748b" : "#22c55e",
                              display: "inline-block",
                            }}
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, p) => setPage(p)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value)); setPage(0); }}
            rowsPerPageOptions={[10, 25, 50, 100]}
            sx={{
              borderTop: "1px solid rgba(148,163,184,0.06)",
              "& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows": {
                fontSize: 12,
              },
            }}
          />
        </CardContent>
      </Card>

      {/* Trade Detail Modal */}
      <AnimatePresence>
        {selectedTrade && (
          <Dialog
            open={!!selectedTrade}
            onClose={() => setSelectedTrade(null)}
            maxWidth="sm"
            fullWidth
            PaperProps={{
              sx: {
                bgcolor: "background.paper",
                backgroundImage: "none",
                border: "1px solid rgba(148,163,184,0.1)",
              },
            }}
          >
            <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", pb: 1 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Typography sx={{ fontSize: 16, fontWeight: 600 }}>Trade Detail</Typography>
                <Chip
                  label={selectedTrade.direction}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: 10,
                    fontWeight: 600,
                    bgcolor: selectedTrade.direction === "BUY" ? "rgba(59,130,246,0.08)" : "rgba(249,115,22,0.08)",
                    color: selectedTrade.direction === "BUY" ? "#3b82f6" : "#f97316",
                  }}
                />
                <Chip
                  label={selectedTrade.symbol}
                  size="small"
                  sx={{ height: 20, fontSize: 10, fontWeight: 600, bgcolor: "rgba(148,163,184,0.06)", color: "#94a3b8" }}
                />
              </Box>
              <IconButton size="small" onClick={() => setSelectedTrade(null)} sx={{ color: "#64748b" }}>
                <X size={18} />
              </IconButton>
            </DialogTitle>
            <DialogContent dividers sx={{ borderColor: "rgba(148,163,184,0.08)" }}>
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.15 }}
              >
                {/* P&L Hero */}
                <Box
                  sx={{
                    textAlign: "center",
                    py: 2.5,
                    mb: 2.5,
                    borderRadius: 2,
                    bgcolor: (selectedTrade.profit ?? 0) >= 0 ? "rgba(34,197,94,0.04)" : "rgba(239,68,68,0.04)",
                    border: `1px solid ${(selectedTrade.profit ?? 0) >= 0 ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)"}`,
                  }}
                >
                  <Typography sx={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", mb: 0.5 }}>
                    Net Profit / Loss
                  </Typography>
                  <Typography
                    sx={{
                      fontSize: 28,
                      fontWeight: 800,
                      color: (selectedTrade.profit ?? 0) >= 0 ? "#22c55e" : "#ef4444",
                      fontFeatureSettings: '"tnum"',
                    }}
                  >
                    {(selectedTrade.profit ?? 0) >= 0 ? "+" : ""}${(selectedTrade.profit ?? 0).toFixed(2)}
                  </Typography>
                </Box>

                {/* Details grid */}
                <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
                  {[
                    { label: "Entry Price", value: selectedTrade.entry_price.toFixed(5) },
                    { label: "Exit Price", value: selectedTrade.exit_price?.toFixed(5) ?? "-" },
                    { label: "Entry Time", value: new Date(selectedTrade.opened_at).toLocaleString() },
                    { label: "Exit Time", value: selectedTrade.closed_at ? new Date(selectedTrade.closed_at).toLocaleString() : "-" },
                    { label: "Strategy", value: selectedTrade.strategy },
                    { label: "Lot Size", value: selectedTrade.lot_size.toString() },
                    { label: "Stop Loss", value: selectedTrade.stop_loss?.toFixed(5) ?? "-" },
                    { label: "Take Profit", value: selectedTrade.take_profit?.toFixed(5) ?? "-" },
                    { label: "Commission", value: `$${(selectedTrade.commission ?? 0).toFixed(2)}` },
                    { label: "Swap", value: `$${(selectedTrade.swap ?? 0).toFixed(2)}` },
                    { label: "MT5 Ticket", value: selectedTrade.mt5_ticket?.toString() ?? "-" },
                    { label: "Status", value: selectedTrade.status },
                  ].map((item) => (
                    <Box key={item.label}>
                      <Typography sx={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", mb: 0.25 }}>
                        {item.label}
                      </Typography>
                      <Typography sx={{ fontSize: 13, fontWeight: 500, fontFamily: "monospace" }}>
                        {item.value}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </motion.div>
            </DialogContent>
          </Dialog>
        )}
      </AnimatePresence>
    </Box>
  );
}
