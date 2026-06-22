import Link from "next/link";

export default function NotFound() {
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

        <div style={{ fontSize: "4rem", fontWeight: 900, color: "var(--navy)", lineHeight: 1, marginBottom: "0.5rem" }}>404</div>
        <h1 style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--navy)", margin: "0 0 0.75rem" }}>
          Page introuvable
        </h1>
        <p style={{ color: "var(--muted)", fontSize: "0.9rem", margin: "0 0 2rem", lineHeight: 1.6 }}>
          Cette page n&apos;existe pas ou vous n&apos;avez pas les droits d&apos;accès nécessaires.
        </p>
        <Link href="/projects" style={{
          display: "inline-block",
          background: "var(--navy)",
          color: "#fff",
          textDecoration: "none",
          padding: "0.7rem 1.5rem",
          borderRadius: "0.4rem",
          fontWeight: 700,
          fontSize: "0.9rem",
        }}>
          ← Retour aux projets
        </Link>
      </div>
    </div>
  );
}
