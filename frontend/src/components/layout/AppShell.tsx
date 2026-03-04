"use client";

import { useEffect, useState, useRef } from "react";
import { usePathname } from "next/navigation";
import { Box } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import Sidebar from "./Sidebar";
import Header from "./Header";

function RouteLoader() {
  const pathname = usePathname();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const prevPathRef = useRef(pathname);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (pathname !== prevPathRef.current) {
      prevPathRef.current = pathname;
      setLoading(true);
      setProgress(0);

      let p = 0;
      timerRef.current = setInterval(() => {
        p += Math.random() * 25 + 10;
        if (p >= 90) {
          p = 90;
          if (timerRef.current) clearInterval(timerRef.current);
        }
        setProgress(p);
      }, 50);

      const complete = setTimeout(() => {
        if (timerRef.current) clearInterval(timerRef.current);
        setProgress(100);
        setTimeout(() => setLoading(false), 150);
      }, 300);

      return () => {
        clearTimeout(complete);
        if (timerRef.current) clearInterval(timerRef.current);
      };
    }
  }, [pathname]);

  if (!loading) return null;

  return (
    <Box
      sx={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 999,
        height: 3,
        pointerEvents: "none",
      }}
    >
      <motion.div
        initial={{ width: "0%" }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 0.15, ease: "easeOut" }}
        style={{
          height: "100%",
          background: "linear-gradient(90deg, #7c3aed, #a78bfa)",
          borderRadius: "0 2px 2px 0",
          boxShadow: "0 0 12px rgba(124, 58, 237, 0.6)",
        }}
      />
    </Box>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      {/* Content column — position:relative so RouteLoader is scoped here */}
      <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column", position: "relative" }}>
        <RouteLoader />
        <Header />
        <Box component="main" sx={{ flexGrow: 1, p: 3, overflow: "auto" }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </Box>
      </Box>
    </Box>
  );
}
