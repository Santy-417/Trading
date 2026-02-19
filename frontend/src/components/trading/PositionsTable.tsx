"use client";

import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  Box,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import api from "@/lib/api";
import type { Position } from "@/types";

interface PositionsTableProps {
  positions: Position[];
  onRefresh: () => void;
}

export default function PositionsTable({ positions, onRefresh }: PositionsTableProps) {
  const handleClose = async (ticket: number) => {
    try {
      await api.post("/orders/close", { ticket });
      onRefresh();
    } catch {
      alert("Failed to close position");
    }
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6">Open Positions ({positions.length})</Typography>
          <Button size="small" onClick={onRefresh}>Refresh</Button>
        </Box>

        {positions.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", py: 4 }}>
            No open positions
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Ticket</TableCell>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell align="right">Volume</TableCell>
                  <TableCell align="right">Entry</TableCell>
                  <TableCell align="right">Current</TableCell>
                  <TableCell align="right">SL</TableCell>
                  <TableCell align="right">TP</TableCell>
                  <TableCell align="right">P&L</TableCell>
                  <TableCell align="center">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {positions.map((pos) => (
                  <TableRow key={pos.ticket}>
                    <TableCell>{pos.ticket}</TableCell>
                    <TableCell>{pos.symbol}</TableCell>
                    <TableCell>
                      <Chip
                        label={pos.type}
                        size="small"
                        color={pos.type === "BUY" ? "success" : "error"}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">{pos.volume}</TableCell>
                    <TableCell align="right">{pos.price_open.toFixed(5)}</TableCell>
                    <TableCell align="right">{pos.price_current.toFixed(5)}</TableCell>
                    <TableCell align="right">{pos.stop_loss && pos.stop_loss !== 0 ? pos.stop_loss.toFixed(5) : "-"}</TableCell>
                    <TableCell align="right">{pos.take_profit && pos.take_profit !== 0 ? pos.take_profit.toFixed(5) : "-"}</TableCell>
                    <TableCell
                      align="right"
                      sx={{ color: pos.profit >= 0 ? "success.main" : "error.main", fontWeight: 600 }}
                    >
                      ${pos.profit.toFixed(2)}
                    </TableCell>
                    <TableCell align="center">
                      <Button
                        size="small"
                        color="error"
                        startIcon={<CloseIcon />}
                        onClick={() => handleClose(pos.ticket)}
                      >
                        Close
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>
    </Card>
  );
}
