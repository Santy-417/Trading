"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Box, Card, CardContent, Typography, Chip } from "@mui/material";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { supabase } from "@/lib/supabase";
import { TrendingUp, Wifi, WifiOff } from "lucide-react";
import { motion } from "framer-motion";
import api from "@/lib/api";

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

  // Check system health
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
        bgcolor: "#0a0f1e",
      }}
    >
      {/* Animated background orbs */}
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
            x: [0, 30, -20, 0],
            y: [0, -40, 20, 0],
            scale: [1, 1.2, 0.9, 1],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          style={{
            position: "absolute",
            top: "20%",
            left: "15%",
            width: 400,
            height: 400,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)",
            filter: "blur(60px)",
          }}
        />
        <motion.div
          animate={{
            x: [0, -25, 35, 0],
            y: [0, 30, -25, 0],
            scale: [1, 0.85, 1.15, 1],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          style={{
            position: "absolute",
            bottom: "10%",
            right: "10%",
            width: 350,
            height: 350,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)",
            filter: "blur(60px)",
          }}
        />
        <motion.div
          animate={{
            x: [0, 20, -15, 0],
            y: [0, -20, 30, 0],
          }}
          transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
          style={{
            position: "absolute",
            top: "60%",
            left: "60%",
            width: 300,
            height: 300,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(34,197,94,0.06) 0%, transparent 70%)",
            filter: "blur(60px)",
          }}
        />
      </Box>

      {/* Login card */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        <Card
          sx={{
            width: 440,
            maxWidth: "90vw",
            position: "relative",
            background: "rgba(15, 23, 42, 0.75)",
            backdropFilter: "blur(24px)",
            border: "1px solid rgba(148, 163, 184, 0.1)",
            boxShadow:
              "0 0 0 1px rgba(59,130,246,0.05), 0 25px 50px -12px rgba(0,0,0,0.5)",
          }}
        >
          <CardContent sx={{ p: 4 }}>
            {/* Logo & Branding */}
            <Box sx={{ textAlign: "center", mb: 4 }}>
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{
                  type: "spring",
                  stiffness: 200,
                  damping: 15,
                  delay: 0.2,
                }}
              >
                <Box
                  sx={{
                    display: "inline-flex",
                    p: 2,
                    borderRadius: 3,
                    bgcolor: "rgba(59, 130, 246, 0.1)",
                    border: "1px solid rgba(59, 130, 246, 0.2)",
                    mb: 2,
                    boxShadow: "0 0 30px rgba(59, 130, 246, 0.15)",
                  }}
                >
                  <TrendingUp size={40} style={{ color: "#3b82f6" }} />
                </Box>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35, duration: 0.4 }}
              >
                <Typography
                  variant="h4"
                  sx={{ fontWeight: 700, letterSpacing: "-0.02em" }}
                >
                  ForexAI
                </Typography>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.45, duration: 0.4 }}
              >
                <Typography
                  variant="body2"
                  sx={{ color: "#94a3b8", mt: 0.5, letterSpacing: "0.05em" }}
                >
                  Professional Algorithmic Trading
                </Typography>
              </motion.div>
            </Box>

            {/* Auth form */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55, duration: 0.4 }}
            >
              <Auth
                supabaseClient={supabase}
                appearance={{
                  theme: ThemeSupa,
                  variables: {
                    default: {
                      colors: {
                        brand: "#3b82f6",
                        brandAccent: "#2563eb",
                        inputBackground: "rgba(15, 23, 42, 0.6)",
                        inputText: "#f1f5f9",
                        inputBorder: "rgba(148,163,184,0.15)",
                        inputBorderFocus: "#3b82f6",
                        inputBorderHover: "rgba(59,130,246,0.4)",
                      },
                      borderWidths: {
                        buttonBorderWidth: "1px",
                        inputBorderWidth: "1px",
                      },
                      radii: {
                        borderRadiusButton: "10px",
                        buttonBorderRadius: "10px",
                        inputBorderRadius: "10px",
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
              transition={{ delay: 0.8, duration: 0.4 }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "center",
                  mt: 3,
                  pt: 2,
                  borderTop: "1px solid rgba(148,163,184,0.08)",
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
          </CardContent>
        </Card>

        {/* Version */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.4 }}
        >
          <Typography
            variant="caption"
            sx={{
              display: "block",
              textAlign: "center",
              mt: 2,
              color: "#475569",
              fontSize: 11,
            }}
          >
            ForexAI Trading Platform v1.0
          </Typography>
        </motion.div>
      </motion.div>
    </Box>
  );
}
