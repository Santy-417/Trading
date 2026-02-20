"use client";

import { useCallback, useEffect, useState } from "react";
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
  Stack,
} from "@mui/material";
import { SelectDropdown } from "@/components/ui/select-dropdown";
import api from "@/lib/api";
import type { Trade } from "@/types";

export default function AuditPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [strategyFilter, setStrategyFilter] = useState("");

  const fetchTrades = useCallback(async () => {
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
    }
  }, [page, rowsPerPage, symbolFilter, strategyFilter]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Trade History & Audit Log
      </Typography>

      <Card>
        <CardContent>
          <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
            <Box sx={{ minWidth: 140 }}>
              <SelectDropdown
                label="Symbol"
                value={symbolFilter}
                onValueChange={(v) => { setSymbolFilter(v); setPage(0); }}
                options={[
                  { id: "", label: "All Symbols" },
                  { id: "EURUSD", label: "EUR/USD" },
                  { id: "XAUUSD", label: "XAU/USD" },
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
                  { id: "fibonacci", label: "Fibonacci" },
                  { id: "ict", label: "ICT" },
                  { id: "hybrid_ml", label: "Hybrid ML" },
                  { id: "manual", label: "Manual" },
                ]}
              />
            </Box>
          </Stack>

          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Direction</TableCell>
                  <TableCell>Strategy</TableCell>
                  <TableCell align="right">Lot Size</TableCell>
                  <TableCell align="right">Entry</TableCell>
                  <TableCell align="right">Exit</TableCell>
                  <TableCell align="right">P&L</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {trades.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} sx={{ textAlign: "center", py: 4 }}>
                      <Typography variant="body2" color="text.secondary">No trades found</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  trades.map((trade) => (
                    <TableRow key={trade.id}>
                      <TableCell sx={{ fontSize: 12 }}>
                        {new Date(trade.opened_at).toLocaleString()}
                      </TableCell>
                      <TableCell>{trade.symbol}</TableCell>
                      <TableCell>
                        <Chip
                          label={trade.direction}
                          size="small"
                          color={trade.direction === "BUY" ? "success" : "error"}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{trade.strategy}</TableCell>
                      <TableCell align="right">{trade.lot_size}</TableCell>
                      <TableCell align="right">{trade.entry_price.toFixed(5)}</TableCell>
                      <TableCell align="right">{trade.exit_price?.toFixed(5) ?? "-"}</TableCell>
                      <TableCell
                        align="right"
                        sx={{
                          color: trade.profit != null && trade.profit >= 0 ? "success.main" : "error.main",
                          fontWeight: 600,
                        }}
                      >
                        {trade.profit != null ? `$${trade.profit.toFixed(2)}` : "-"}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={trade.status}
                          size="small"
                          color={trade.status === "closed" ? "default" : "primary"}
                          variant="outlined"
                        />
                      </TableCell>
                    </TableRow>
                  ))
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
          />
        </CardContent>
      </Card>
    </Box>
  );
}
