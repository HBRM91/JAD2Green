"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";

type Lang = "fr" | "en";

const T = {
  fr: {
    headline: "Adrar AI",
    tagline: "Plateforme de reporting carbone réglementaire pour bureaux d'étude. Bilan Carbone conforme, traçable et sécurisé.",
    features: [
      "Calcul déterministe certifié",
      "Isolation multi-tenant par bureau",
      "Rapport DOCX Bilan Carbone",
      "Traçabilité complète des faits",
    ],
    stats: [
      { label: "Bureaux actifs", value: "120+" },
      { label: "Rapports produits", value: "4 000+" },
      { label: "tCO₂e calculées", value: "2 M+" },
    ],
    form_title: "Connexion consultant",
    form_sub: "Accédez à votre espace de travail",
    email_lbl: "Email professionnel",
    email_ph: "consultant@bureau.ma",
    pwd_lbl: "Mot de passe",
    submit: "Se connecter",
    submitting: "Connexion en cours...",
    error: "Identifiants incorrects. Veuillez réessayer.",
    footer: "JAD2 Advisory · Adrar AI · Tous droits réservés",
    trust: "Plateforme certifiée ISO 14064 · Données hébergées en région",
  },
  en: {
    headline: "Adrar AI",
    tagline: "Regulatory carbon reporting platform for consulting firms. Compliant, traceable, and secure Bilan Carbone.",
    features: [
      "Certified deterministic computation",
      "Per-bureau multi-tenant isolation",
      "Bilan Carbone DOCX report",
      "Full activity fact traceability",
    ],
    stats: [
      { label: "Active bureaux", value: "120+" },
      { label: "Reports produced", value: "4,000+" },
      { label: "tCO₂e computed", value: "2 M+" },
    ],
    form_title: "Consultant Login",
    form_sub: "Access your workspace",
    email_lbl: "Professional email",
    email_ph: "consultant@bureau.ma",
    pwd_lbl: "Password",
    submit: "Sign in",
    submitting: "Signing in...",
    error: "Incorrect credentials. Please try again.",
    footer: "JAD2 Advisory · Adrar AI · All rights reserved",
    trust: "ISO 14064-compliant platform · Data hosted in-region",
  },
};

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  const [lang, setLang] = useState<Lang>("fr");
  const t = T[lang];

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (authError) {
      // Generic message — don't leak auth internals
      setError(t.error);
    } else {
      router.push("/projects");
    }
  }

  return (
    <div style={wrapStyle}>
      {/* Left panel — brand */}
      <div style={brandPanelStyle}>
        <div style={{ maxWidth: 400, width: "100%" }}>
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "2.5rem" }}>
            <span style={logoChip}>JAD2</span>
            <span style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.75rem", letterSpacing: "0.15em", textTransform: "uppercase" }}>Advisory</span>
          </div>

          <h1 style={{ fontSize: "2.2rem", fontWeight: 800, color: "#fff", margin: "0 0 0.75rem", lineHeight: 1.15 }}>
            {t.headline}
          </h1>
          <p style={{ color: "rgba(255,255,255,0.72)", fontSize: "1rem", lineHeight: 1.65, margin: "0 0 2.5rem" }}>
            {t.tagline}
          </p>

          {/* Feature checklist */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", marginBottom: "2.5rem" }}>
            {t.features.map((f) => (
              <div key={f} style={{ display: "flex", alignItems: "center", gap: "0.7rem", color: "rgba(255,255,255,0.88)", fontSize: "0.9rem" }}>
                <span style={{
                  background: "rgba(255,255,255,0.15)",
                  borderRadius: "50%",
                  width: 22, height: 22,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "0.7rem", flexShrink: 0,
                }}>✓</span>
                {f}
              </div>
            ))}
          </div>

          {/* Stats row */}
          <div style={{ display: "flex", gap: "1.5rem", borderTop: "1px solid rgba(255,255,255,0.15)", paddingTop: "1.75rem" }}>
            {t.stats.map((s) => (
              <div key={s.label}>
                <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "#fff" }}>{s.value}</div>
                <div style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.55)", marginTop: "0.1rem" }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Trust badge */}
          <div style={{ marginTop: "1.75rem", background: "rgba(255,255,255,0.08)", borderRadius: "0.4rem", padding: "0.55rem 0.85rem", fontSize: "0.72rem", color: "rgba(255,255,255,0.5)" }}>
            🔒 {t.trust}
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div style={formPanelStyle}>
        {/* Language toggle */}
        <div style={{ position: "absolute", top: "1.25rem", right: "1.5rem" }}>
          <button
            onClick={() => setLang(lang === "fr" ? "en" : "fr")}
            style={{
              background: "none",
              border: "1px solid var(--border)",
              borderRadius: "0.3rem",
              padding: "0.2rem 0.6rem",
              fontSize: "0.72rem",
              fontWeight: 700,
              cursor: "pointer",
              color: "var(--navy)",
              letterSpacing: "0.08em",
            }}
          >
            {lang === "fr" ? "EN" : "FR"}
          </button>
        </div>

        <div style={{ width: "100%", maxWidth: 400 }}>
          <h2 style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--navy)", marginBottom: "0.4rem" }}>
            {t.form_title}
          </h2>
          <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "2rem" }}>
            {t.form_sub}
          </p>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.1rem" }}>
            <div>
              <label style={labelStyle}>{t.email_lbl}</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                style={inputStyle}
                placeholder={t.email_ph}
              />
            </div>
            <div>
              <label style={labelStyle}>{t.pwd_lbl}</label>
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
            <button type="submit" disabled={loading} style={{ ...submitBtnStyle, opacity: loading ? 0.75 : 1 }}>
              {loading ? t.submitting : t.submit}
            </button>
          </form>
          <p style={{ marginTop: "3rem", fontSize: "0.72rem", color: "var(--muted-light)", textAlign: "center" }}>
            {t.footer}
          </p>
        </div>
      </div>
    </div>
  );
}

const wrapStyle: React.CSSProperties = {
  display: "flex",
  minHeight: "100vh",
  position: "relative",
};

const brandPanelStyle: React.CSSProperties = {
  flex: "0 0 460px",
  background: "linear-gradient(160deg, var(--navy-dark) 0%, var(--navy) 60%, var(--navy-light) 100%)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "3rem 3.5rem",
};

const logoChip: React.CSSProperties = {
  display: "inline-block",
  background: "rgba(255,255,255,0.15)",
  color: "#fff",
  fontWeight: 900,
  fontSize: "0.85rem",
  letterSpacing: "0.18em",
  padding: "0.3rem 0.7rem",
  borderRadius: "0.2rem",
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
  fontSize: "0.78rem",
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
  boxSizing: "border-box",
};

const submitBtnStyle: React.CSSProperties = {
  background: "var(--navy)",
  color: "#fff",
  border: "none",
  borderRadius: "0.4rem",
  padding: "0.85rem",
  fontWeight: 700,
  fontSize: "0.95rem",
  cursor: "pointer",
  letterSpacing: "0.02em",
  marginTop: "0.25rem",
  width: "100%",
};
