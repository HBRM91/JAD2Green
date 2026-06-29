"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log to monitoring service in production
    // Never expose error details to the user
  }, [error]);

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "2rem",
    }}>
      <div style={{ textAlign: "center", maxWidth: 420 }}>
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.4rem",
          background: "var(--navy)",
          color: "#fff",
          padding: "0.3rem 0.75rem 0.3rem 0.55rem",
          borderRadius: "0.3rem",
          marginBottom: "2rem",
        }}>
          <span style={{ fontWeight: 900, fontSize: "0.8rem", letterSpacing: "0.15em" }}>JAD2</span>
          <span style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.65rem", letterSpacing: "0.1em", textTransform: "uppercase" }}>Advisory</span>
        </div>

        <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>⚠</div>
        <h1 style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--navy)", margin: "0 0 0.75rem" }}>
          Une erreur est survenue
        </h1>
        <p style={{ color: "var(--muted)", fontSize: "0.9rem", margin: "0 0 2rem", lineHeight: 1.6 }}>
          Nous n&apos;avons pas pu charger cette page. Veuillez réessayer ou retourner aux projets.
        </p>
        <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
          <button
            onClick={reset}
            style={{
              background: "var(--navy)",
              color: "#fff",
              border: "none",
              padding: "0.65rem 1.25rem",
              borderRadius: "0.4rem",
              fontWeight: 700,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            Réessayer
          </button>
          <Link href="/projects" style={{
            display: "inline-block",
            background: "none",
            color: "var(--muted)",
            border: "1px solid var(--border)",
            textDecoration: "none",
            padding: "0.65rem 1.25rem",
            borderRadius: "0.4rem",
            fontWeight: 600,
            fontSize: "0.875rem",
          }}>
            ← Projets
          </Link>
        </div>
      </div>
    </div>
  );
}
