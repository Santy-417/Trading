"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import LoadingSpinner from "@/components/common/LoadingSpinner";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace("/trading");
      } else {
        router.replace("/login");
      }
    });
  }, [router]);

  return <LoadingSpinner message="Loading..." />;
}
