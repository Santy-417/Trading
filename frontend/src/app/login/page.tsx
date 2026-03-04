"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Box, Typography, Chip } from "@mui/material";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { supabase } from "@/lib/supabase";
import { TrendingUp, Wifi, WifiOff } from "lucide-react";
import { motion } from "framer-motion";
import api from "@/lib/api";

// --- Geometric Waves Background (Canvas) ---
function GeometricWavesBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const time = Date.now() * 0.001;
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Draw floating geometric shapes
    const shapes = 18;
    for (let i = 0; i < shapes; i++) {
      const t = time * 0.3 + i * 1.7;
      const x = w * (0.1 + 0.8 * ((Math.sin(t * 0.4 + i) * 0.5 + 0.5)));
      const y = h * (0.1 + 0.8 * ((Math.cos(t * 0.3 + i * 0.7) * 0.5 + 0.5)));
      const size = 30 + Math.sin(t * 0.5) * 20 + i * 4;
      const rotation = t * 0.2 + i;
      const opacity = 0.03 + Math.sin(t * 0.6 + i) * 0.02;

      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(rotation);
      ctx.globalAlpha = opacity;

      // Alternate between hexagons and triangles
      if (i % 3 === 0) {
        // Hexagon
        ctx.beginPath();
        for (let j = 0; j < 6; j++) {
          const angle = (Math.PI / 3) * j - Math.PI / 6;
          const hx = Math.cos(angle) * size;
          const hy = Math.sin(angle) * size;
          if (j === 0) { ctx.moveTo(hx, hy); } else { ctx.lineTo(hx, hy); }
        }
        ctx.closePath();
        const colors = ["#7c3aed", "#6d28d9", "#4f46e5", "#818cf8"];
        ctx.strokeStyle = colors[i % colors.length];
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else if (i % 3 === 1) {
        // Triangle
        ctx.beginPath();
        for (let j = 0; j < 3; j++) {
          const angle = (Math.PI * 2 / 3) * j - Math.PI / 2;
          const tx = Math.cos(angle) * size;
          const ty = Math.sin(angle) * size;
          if (j === 0) { ctx.moveTo(tx, ty); } else { ctx.lineTo(tx, ty); }
        }
        ctx.closePath();
        ctx.strokeStyle = "#818cf8";
        ctx.lineWidth = 1;
        ctx.stroke();
      } else {
        // Diamond
        ctx.beginPath();
        ctx.moveTo(0, -size);
        ctx.lineTo(size * 0.6, 0);
        ctx.lineTo(0, size);
        ctx.lineTo(-size * 0.6, 0);
        ctx.closePath();
        ctx.strokeStyle = "#a78bfa";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      ctx.restore();
    }

    // Sine wave lines
    for (let wave = 0; wave < 4; wave++) {
      ctx.beginPath();
      ctx.globalAlpha = 0.04 + wave * 0.01;
      const waveColors = ["#7c3aed", "#4f46e5", "#818cf8", "#6d28d9"];
      ctx.strokeStyle = waveColors[wave];
      ctx.lineWidth = 1;

      for (let x = 0; x < w; x += 3) {
        const y2 = h * (0.3 + wave * 0.15) +
          Math.sin(x * 0.003 + time * (0.5 + wave * 0.2)) * 60 +
          Math.sin(x * 0.007 + time * 0.3) * 30;
        if (x === 0) { ctx.moveTo(x, y2); } else { ctx.lineTo(x, y2); }
      }
      ctx.stroke();
    }

    animRef.current = requestAnimationFrame(draw);
  }, []);

  useEffect(() => {
    animRef.current = requestAnimationFrame(draw);
    const handleResize = () => {
      if (canvasRef.current) {
        canvasRef.current.width = window.innerWidth;
        canvasRef.current.height = window.innerHeight;
      }
    };
    window.addEventListener("resize", handleResize);
    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", handleResize);
    };
  }, [draw]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    />
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [systemOnline, setSystemOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") {
        router.push("/");
      }
    });
    return () => subscription.unsubscribe();
  }, [router]);

  useEffect(() => {
    api
      .get("/health")
      .then(() => setSystemOnline(true))
      .catch(() => setSystemOnline(false));
  }, []);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        overflow: "hidden",
        bgcolor: "#06050f",
      }}
    >
      {/* Ambient glow orbs behind everything */}
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          overflow: "hidden",
          pointerEvents: "none",
        }}
      >
        <motion.div
          animate={{
            x: [0, 40, -30, 0],
            y: [0, -50, 30, 0],
            scale: [1, 1.3, 0.85, 1],
          }}
          transition={{ duration: 22, repeat: Infinity, ease: "linear" }}
          style={{
            position: "absolute",
            top: "15%",
            left: "10%",
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(124,58,237,0.15) 0%, transparent 70%)",
            filter: "blur(80px)",
          }}
        />
        <motion.div
          animate={{
            x: [0, -35, 40, 0],
            y: [0, 40, -30, 0],
            scale: [1, 0.8, 1.2, 1],
          }}
          transition={{ duration: 28, repeat: Infinity, ease: "linear" }}
          style={{
            position: "absolute",
            bottom: "5%",
            right: "5%",
            width: 450,
            height: 450,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(79,70,229,0.12) 0%, transparent 70%)",
            filter: "blur(80px)",
          }}
        />
        <motion.div
          animate={{
            x: [0, 25, -20, 0],
            y: [0, -25, 35, 0],
          }}
          transition={{ duration: 35, repeat: Infinity, ease: "linear" }}
          style={{
            position: "absolute",
            top: "55%",
            left: "55%",
            width: 350,
            height: 350,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(167,139,250,0.08) 0%, transparent 70%)",
            filter: "blur(80px)",
          }}
        />
      </Box>

      {/* Geometric waves canvas */}
      <GeometricWavesBackground />

      {/* Login card - Liquid Glass */}
      <motion.div
        initial={{ opacity: 0, y: 32, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        style={{ position: "relative", zIndex: 1 }}
      >
        <Box
          sx={{
            width: 440,
            maxWidth: "90vw",
            position: "relative",
            borderRadius: "24px",
            background: "rgba(255, 255, 255, 0.03)",
            backdropFilter: "blur(40px) saturate(1.8)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            boxShadow:
              "0 0 80px rgba(124,58,237,0.08), 0 32px 64px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)",
            overflow: "hidden",
            // Light reflection pseudo-element via gradient overlay
            "&::before": {
              content: '""',
              position: "absolute",
              inset: 0,
              borderRadius: "24px",
              background:
                "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, transparent 40%, transparent 60%, rgba(124,58,237,0.03) 100%)",
              pointerEvents: "none",
            },
          }}
        >
          <Box sx={{ position: "relative", p: 4 }}>
            {/* Logo & Branding */}
            <Box sx={{ textAlign: "center", mb: 4 }}>
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{
                  type: "spring",
                  stiffness: 180,
                  damping: 14,
                  delay: 0.2,
                }}
              >
                <Box
                  sx={{
                    display: "inline-flex",
                    p: 2,
                    borderRadius: 3,
                    bgcolor: "rgba(124, 58, 237, 0.1)",
                    border: "1px solid rgba(124, 58, 237, 0.25)",
                    mb: 2.5,
                    boxShadow: "0 0 40px rgba(124, 58, 237, 0.2), 0 0 80px rgba(124, 58, 237, 0.08)",
                  }}
                >
                  <TrendingUp size={40} style={{ color: "#a78bfa" }} />
                </Box>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35, duration: 0.5 }}
              >
                <Typography
                  variant="h3"
                  sx={{
                    fontWeight: 800,
                    letterSpacing: "-0.03em",
                    fontSize: 36,
                    background: "linear-gradient(135deg, #e2d5ff 0%, #a78bfa 40%, #7c3aed 100%)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text",
                  }}
                >
                  NextFlow
                </Typography>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.4 }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    color: "#a78bfa",
                    mt: 0.5,
                    letterSpacing: "0.15em",
                    fontWeight: 500,
                    textTransform: "uppercase",
                    fontSize: 13,
                  }}
                >
                  TradingAI
                </Typography>
              </motion.div>
            </Box>

            {/* Auth form */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.5 }}
            >
              <Auth
                supabaseClient={supabase}
                appearance={{
                  theme: ThemeSupa,
                  variables: {
                    default: {
                      colors: {
                        brand: "#7c3aed",
                        brandAccent: "#6d28d9",
                        inputBackground: "rgba(15, 10, 40, 0.5)",
                        inputText: "#f1f5f9",
                        inputBorder: "rgba(139,92,246,0.15)",
                        inputBorderFocus: "#7c3aed",
                        inputBorderHover: "rgba(124,58,237,0.4)",
                      },
                      borderWidths: {
                        buttonBorderWidth: "1px",
                        inputBorderWidth: "1px",
                      },
                      radii: {
                        borderRadiusButton: "12px",
                        buttonBorderRadius: "12px",
                        inputBorderRadius: "12px",
                      },
                      space: {
                        inputPadding: "12px 16px",
                        buttonPadding: "12px 16px",
                      },
                      fontSizes: {
                        baseBodySize: "14px",
                        baseInputSize: "14px",
                        baseLabelSize: "13px",
                        baseButtonSize: "14px",
                      },
                    },
                  },
                }}
                theme="dark"
                providers={[]}
              />
            </motion.div>

            {/* System status */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.9, duration: 0.4 }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "center",
                  mt: 3,
                  pt: 2,
                  borderTop: "1px solid rgba(139,92,246,0.08)",
                }}
              >
                {systemOnline === null ? (
                  <Typography variant="caption" sx={{ color: "#64748b" }}>
                    Checking system status...
                  </Typography>
                ) : (
                  <Chip
                    icon={
                      systemOnline ? (
                        <Wifi size={12} style={{ color: "#22c55e" }} />
                      ) : (
                        <WifiOff size={12} style={{ color: "#f59e0b" }} />
                      )
                    }
                    label={systemOnline ? "System Online" : "System Offline"}
                    size="small"
                    variant="outlined"
                    sx={{
                      borderColor: systemOnline
                        ? "rgba(34,197,94,0.3)"
                        : "rgba(245,158,11,0.3)",
                      color: systemOnline ? "#22c55e" : "#f59e0b",
                      fontSize: 11,
                      height: 24,
                      "& .MuiChip-icon": { ml: 0.5 },
                    }}
                  />
                )}
              </Box>
            </motion.div>
          </Box>
        </Box>

        {/* Version */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.1, duration: 0.4 }}
        >
          <Typography
            variant="caption"
            sx={{
              display: "block",
              textAlign: "center",
              mt: 2.5,
              color: "rgba(167, 139, 250, 0.4)",
              fontSize: 11,
              letterSpacing: "0.05em",
            }}
          >
            NextFlow TradingAI v2.0
          </Typography>
        </motion.div>
      </motion.div>
    </Box>
  );
}
