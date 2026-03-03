"use client";

import { useState, useCallback } from "react";
import { Box, IconButton, Typography, Chip } from "@mui/material";
import { ChevronLeft, ChevronRight, FileText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import TradeAuditCard from "./TradeAuditCard";
import type { TradeAudit } from "@/types";

interface TradeAuditCarouselProps {
  trades: TradeAudit[];
  symbol: string;
  timeframe: string;
}

const variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction < 0 ? 300 : -300,
    opacity: 0,
  }),
};

const transition = { type: "spring" as const, stiffness: 300, damping: 30 };

export default function TradeAuditCarousel({
  trades,
  symbol,
  timeframe,
}: TradeAuditCarouselProps) {
  const [[currentIndex, direction], setPage] = useState([0, 0]);

  const paginate = useCallback(
    (newDirection: number) => {
      setPage(([prev]) => {
        const next = prev + newDirection;
        if (next < 0 || next >= trades.length) return [prev, 0];
        return [next, newDirection];
      });
    },
    [trades.length]
  );

  if (trades.length === 0) {
    return null;
  }

  const wins = trades.filter((t) => t.profit >= 0).length;
  const losses = trades.length - wins;

  return (
    <Box
      sx={{
        bgcolor: "background.paper",
        borderRadius: 2,
        border: "1px solid rgba(148,163,184,0.1)",
        p: 3,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <FileText size={20} />
          <Typography variant="h6" fontWeight={600}>
            Trade Audit Portfolio
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Chip
            label={`${wins}W`}
            size="small"
            color="success"
            variant="outlined"
            sx={{ fontWeight: 600 }}
          />
          <Chip
            label={`${losses}L`}
            size="small"
            color="error"
            variant="outlined"
            sx={{ fontWeight: 600 }}
          />
        </Box>
      </Box>

      {/* Carousel */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 2,
        }}
      >
        <IconButton
          onClick={() => paginate(-1)}
          disabled={currentIndex === 0}
          sx={{
            bgcolor: "rgba(148,163,184,0.08)",
            "&:hover": { bgcolor: "rgba(148,163,184,0.15)" },
          }}
        >
          <ChevronLeft size={20} />
        </IconButton>

        <Box
          sx={{
            overflow: "hidden",
            width: { xs: "100%", md: 420 },
            minHeight: 400,
            position: "relative",
          }}
        >
          <AnimatePresence initial={false} custom={direction} mode="wait">
            <motion.div
              key={currentIndex}
              custom={direction}
              variants={variants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={transition}
              style={{ position: "absolute", width: "100%" }}
            >
              <TradeAuditCard
                trade={trades[currentIndex]}
                index={currentIndex}
                total={trades.length}
                symbol={symbol}
                timeframe={timeframe}
              />
            </motion.div>
          </AnimatePresence>
        </Box>

        <IconButton
          onClick={() => paginate(1)}
          disabled={currentIndex === trades.length - 1}
          sx={{
            bgcolor: "rgba(148,163,184,0.08)",
            "&:hover": { bgcolor: "rgba(148,163,184,0.15)" },
          }}
        >
          <ChevronRight size={20} />
        </IconButton>
      </Box>

      {/* Counter */}
      <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
        <Chip
          label={`Trade ${currentIndex + 1} de ${trades.length}`}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 500 }}
        />
      </Box>
    </Box>
  );
}
