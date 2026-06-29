"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getBrowserClient } from "@/lib/supabase";

export default function Home() {
  const router = useRouter();
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    (async () => {
      const sb = getBrowserClient();
      const { data } = await sb.auth.getSession();
      router.replace(data.session ? "/projects" : "/login");
    })().finally(() => setBusy(false));
  }, [router]);
  return (
    <main className="min-h-screen flex items-center justify-center text-slate-500">
      {busy ? "Loading…" : "Redirecting…"}
    </main>
  );
}
