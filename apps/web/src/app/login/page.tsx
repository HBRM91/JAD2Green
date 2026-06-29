"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { getBrowserClient } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const sb = getBrowserClient();
      const { error: err } = await sb.auth.signInWithPassword({ email, password });
      if (err) {
        setError(err.message);
        return;
      }
      router.replace("/projects");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white p-6 rounded-lg shadow space-y-4"
      >
        <h1 className="text-xl font-semibold">Adrar AI</h1>
        <p className="text-sm text-slate-500">Connectez-vous à votre bureau d&apos;étude.</p>
        <label className="block text-sm">
          <span className="text-slate-700">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full border rounded px-3 py-2"
            autoComplete="email"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-700">Mot de passe</span>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full border rounded px-3 py-2"
            autoComplete="current-password"
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full bg-slate-900 text-white rounded px-3 py-2 disabled:opacity-50"
        >
          {busy ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </main>
  );
}
