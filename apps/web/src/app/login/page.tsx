"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) {
      // Generic message — don't leak auth internals
      setError("Identifiants incorrects. Veuillez réessayer.");
    } else {
      router.push("/projects");
    }
  }

  return (
    <div style={wrapStyle}>
      {/* Left panel — brand */}
      <div style={brandPanelStyle}>
        <div style={{ maxWidth: 380 }}>
          <div style={logoStyle}>JAD2</div>
          <h1 style={{ fontSize: "2rem", fontWeight: 800, color: "#fff", margin: "0 0 0.75rem" }}>
            Adrar AI
          </h1>
          <p style={{ color: "rgba(255,255,255,0.75)", fontSize: "1.05rem", lineHeight: 1.6, margin: 0 }}>
            Plateforme de reporting carbone réglementaire pour bureaux d&apos;étude. Bilan Carbone conforme, traçable et sécurisé.
          </p>
          <div style={{ marginTop: "2.5rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
            {["Calcul déterministe certifié", "Isolation multi-tenant RLS", "Rapport DOCX Bilan Carbone"].map((f) => (
              <div key={f} style={{ display: "flex", alignItems: "center", gap: "0.6rem", color: "rgba(255,255,255,0.85)", fontSize: "0.9rem" }}>
                <span style={{ background: "rgba(255,255,255,0.15)", borderRadius: "50%", width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem" }}>✓</span>
                {f}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div style={formPanelStyle}>
        <div style={{ width: "100%", maxWidth: 400 }}>
          <h2 style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--navy)", marginBottom: "0.4rem" }}>
            Connexion consultant
          </h2>
          <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "2rem" }}>
            Accédez à votre espace de travail
          </p>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.1rem" }}>
            <div>
              <label style={labelStyle}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                style={inputStyle}
                placeholder="consultant@bureau.ma"
              />
            </div>
            <div>
              <label style={labelStyle}>Mot de passe</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                style={inputStyle}
              />
            </div>
            {error && (
              <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: "0.375rem", padding: "0.65rem 0.85rem", color: "#dc2626", fontSize: "0.85rem" }}>
                {error}
              </div>
            )}
            <button type="submit" disabled={loading} style={submitBtnStyle}>
              {loading ? "Connexion en cours..." : "Se connecter"}
            </button>
          </form>
          <p style={{ marginTop: "2.5rem", fontSize: "0.75rem", color: "var(--muted-light)", textAlign: "center" }}>
            JAD2 Advisory · Adrar AI · Tous droits réservés
          </p>
        </div>
      </div>
    </div>
  );
}

const wrapStyle: React.CSSProperties = {
  display: "flex",
  minHeight: "100vh",
};

const brandPanelStyle: React.CSSProperties = {
  flex: "0 0 480px",
  background: "linear-gradient(160deg, var(--navy-dark) 0%, var(--navy) 60%, var(--navy-light) 100%)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "3rem 3.5rem",
};

const logoStyle: React.CSSProperties = {
  display: "inline-block",
  background: "rgba(255,255,255,0.12)",
  color: "#fff",
  fontWeight: 900,
  fontSize: "1rem",
  letterSpacing: "0.15em",
  padding: "0.35rem 0.8rem",
  borderRadius: "0.25rem",
  marginBottom: "1.25rem",
};

const formPanelStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "3rem 2rem",
  background: "#fff",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.8rem",
  fontWeight: 600,
  color: "var(--text)",
  marginBottom: "0.4rem",
  letterSpacing: "0.025em",
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.7rem 0.9rem",
  border: "1.5px solid var(--border)",
  borderRadius: "0.4rem",
  fontSize: "0.95rem",
  color: "var(--text)",
  outline: "none",
  transition: "border-color 0.15s",
};

const submitBtnStyle: React.CSSProperties = {
  background: "var(--navy)",
  color: "#fff",
  border: "none",
  borderRadius: "0.4rem",
  padding: "0.8rem",
  fontWeight: 700,
  fontSize: "0.95rem",
  cursor: "pointer",
  letterSpacing: "0.02em",
  marginTop: "0.25rem",
  transition: "background 0.15s",
};
