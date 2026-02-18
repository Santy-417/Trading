"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Box, Card, CardContent, Typography } from "@mui/material";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { supabase } from "@/lib/supabase";
import ShowChartIcon from "@mui/icons-material/ShowChart";

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") {
        router.push("/");
      }
    });
    return () => subscription.unsubscribe();
  }, [router]);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
      }}
    >
      <Card sx={{ width: 420, maxWidth: "90vw" }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ textAlign: "center", mb: 3 }}>
            <ShowChartIcon color="primary" sx={{ fontSize: 48, mb: 1 }} />
            <Typography variant="h5">ForexAI Trading</Typography>
            <Typography variant="body2" color="text.secondary">
              Sign in to your account
            </Typography>
          </Box>

          <Auth
            supabaseClient={supabase}
            appearance={{
              theme: ThemeSupa,
              variables: {
                default: {
                  colors: {
                    brand: "#3b82f6",
                    brandAccent: "#2563eb",
                    inputBackground: "#0f172a",
                    inputText: "#f1f5f9",
                    inputBorder: "rgba(148,163,184,0.2)",
                  },
                },
              },
            }}
            theme="dark"
            providers={[]}
          />
        </CardContent>
      </Card>
    </Box>
  );
}
