"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { apiJson } from "@/lib/api";
import type { Project, Client } from "@/lib/types";

export default function ProjectsPage() {
  const router = useRouter();
  const supabase = createClient();
  const [token, setToken] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [methodologies, setMethodologies] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    clientId: "",
    name: "",
    year: new Date().getFullYear(),
    methodologyId: "",
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) { router.push("/login"); return; }
      setToken(session.access_token);
    });
  }, []);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiJson<Project[]>("/projects", token),
      apiJson<Client[]>("/clients", token),
      apiJson<{ id: string; name: string }[]>("/methodologies", token).catch(() => []),
    ]).then(([p, c, m]) => {
      setProjects(p);
      setClients(c);
      setMethodologies(m);
      setLoading(false);
    });
  }, [token]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setCreating(true);
    setCreateError(null);
    try {
      const proj = await apiJson<Project>("/projects", token, {
        method: "POST",
        body: JSON.stringify({
          client_id: form.clientId,
          name: form.name,
          reporting_year: form.year,
          methodology_id: form.methodologyId || methodologies[0]?.id,
        }),
      });
      setProjects((p) => [...p, proj]);
      setShowCreate(false);
      setForm({ clientId: "", name: "", year: new Date().getFullYear(), methodologyId: "" });
    } catch {
      setCreateError("Impossible de créer le projet. Vérifiez les informations.");
    } finally {
      setCreating(false);
    }
  }

  async function handleLogout() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  const statusColor: Record<string, string> = {
    active: "#16a34a",
    draft: "#d97706",
    archived: "#94a3b8",
  };

  if (loading) return <Spinner />;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <Topbar onLogout={handleLogout} />

      <div style={pageWrap}>
        {/* Page header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem" }}>
          <div>
            <h1 style={{ fontSize: "1.7rem", fontWeight: 800, color: "var(--navy)", margin: 0 }}>Projets</h1>
            <p style={{ color: "var(--muted)", fontSize: "0.9rem", margin: "0.25rem 0 0" }}>
              {projects.length} projet{projects.length !== 1 ? "s" : ""} actif{projects.length !== 1 ? "s" : ""}
            </p>
          </div>
          <button onClick={() => setShowCreate(true)} style={primaryBtn}>
            + Nouveau projet
          </button>
        </div>

        {/* Create form */}
        {showCreate && (
          <div style={{ ...card, marginBottom: "1.5rem", borderLeft: "4px solid var(--navy)" }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--navy)", marginBottom: "1.25rem" }}>
              Créer un projet
            </h2>
            <form onSubmit={handleCreate} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Client *</label>
                <select value={form.clientId} onChange={(e) => setForm({ ...form, clientId: e.target.value })} required style={inputStyle}>
                  <option value="">Sélectionner un client...</option>
                  {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Nom du projet *</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required style={inputStyle} placeholder="Ex: Bilan Carbone FY2024" />
              </div>
              <div>
                <label style={labelStyle}>Année de reporting *</label>
                <input type="number" value={form.year} onChange={(e) => setForm({ ...form, year: parseInt(e.target.value) })} required min={2000} max={2100} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Méthodologie</label>
                <select value={form.methodologyId} onChange={(e) => setForm({ ...form, methodologyId: e.target.value })} style={inputStyle}>
                  {methodologies.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
              {createError && (
                <div style={{ gridColumn: "1 / -1", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: "0.375rem", padding: "0.6rem 0.85rem", color: "var(--red)", fontSize: "0.85rem" }}>
                  {createError}
                </div>
              )}
              <div style={{ gridColumn: "1 / -1", display: "flex", gap: "0.75rem" }}>
                <button type="submit" disabled={creating} style={primaryBtn}>{creating ? "Création..." : "Créer"}</button>
                <button type="button" onClick={() => setShowCreate(false)} style={ghostBtn}>Annuler</button>
              </div>
            </form>
          </div>
        )}

        {/* Projects grid */}
        {projects.length === 0 ? (
          <EmptyState onCreate={() => setShowCreate(true)} />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
            {projects.map((p) => (
              <div key={p.id} onClick={() => router.push(`/projects/${p.id}`)} style={projectCard}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                  <span style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: statusColor[p.status] ?? "var(--muted)", background: `${statusColor[p.status] ?? "var(--muted)"}18`, padding: "0.2rem 0.6rem", borderRadius: "9999px" }}>
                    {p.status}
                  </span>
                  <span style={{ fontSize: "0.8rem", color: "var(--muted)", fontWeight: 600 }}>{p.reporting_year}</span>
                </div>
                <h3 style={{ fontWeight: 700, fontSize: "1.05rem", color: "var(--navy)", margin: "0 0 0.4rem" }}>{p.name}</h3>
                <p style={{ color: "var(--muted)", fontSize: "0.82rem", margin: 0 }}>
                  Créé le {new Date(p.created_at).toLocaleDateString("fr-FR")}
                </p>
                <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border)", paddingTop: "0.75rem", display: "flex", justifyContent: "flex-end" }}>
                  <span style={{ color: "var(--accent)", fontSize: "0.85rem", fontWeight: 600 }}>Ouvrir →</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Topbar({ onLogout }: { onLogout: () => void }) {
  return (
    <header style={topbarStyle}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <span style={logoChip}>JAD2</span>
        <span style={{ fontWeight: 700, color: "var(--navy)", fontSize: "1rem" }}>Adrar AI</span>
      </div>
      <nav style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
        <span style={{ fontWeight: 600, color: "var(--navy)", fontSize: "0.875rem", borderBottom: "2px solid var(--navy)", paddingBottom: "0.1rem" }}>Projets</span>
        <button onClick={onLogout} style={ghostBtn}>Déconnexion</button>
      </nav>
    </header>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div style={{ textAlign: "center", padding: "4rem 2rem", background: "#fff", borderRadius: "0.75rem", border: "2px dashed var(--border)" }}>
      <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>📊</div>
      <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--navy)", margin: "0 0 0.5rem" }}>Aucun projet</h3>
      <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>Créez votre premier projet de Bilan Carbone.</p>
      <button onClick={onCreate} style={primaryBtn}>+ Nouveau projet</button>
    </div>
  );
}

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <div style={{ width: 36, height: 36, border: "3px solid var(--border)", borderTopColor: "var(--navy)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
    </div>
  );
}

const pageWrap: React.CSSProperties = { maxWidth: "1100px", margin: "0 auto", padding: "2rem 1.5rem" };

const topbarStyle: React.CSSProperties = {
  background: "#fff",
  borderBottom: "1px solid var(--border)",
  padding: "0 2rem",
  height: "56px",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  position: "sticky",
  top: 0,
  zIndex: 100,
  boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
};

const logoChip: React.CSSProperties = {
  background: "var(--navy)",
  color: "#fff",
  fontWeight: 900,
  fontSize: "0.7rem",
  letterSpacing: "0.15em",
  padding: "0.25rem 0.55rem",
  borderRadius: "0.2rem",
};

const card: React.CSSProperties = {
  background: "#fff",
  border: "1px solid var(--border)",
  borderRadius: "0.6rem",
  padding: "1.5rem",
};

const projectCard: React.CSSProperties = {
  background: "#fff",
  border: "1px solid var(--border)",
  borderRadius: "0.6rem",
  padding: "1.25rem",
  cursor: "pointer",
  transition: "box-shadow 0.15s, border-color 0.15s",
};

const primaryBtn: React.CSSProperties = {
  background: "var(--navy)",
  color: "#fff",
  border: "none",
  borderRadius: "0.4rem",
  padding: "0.6rem 1.2rem",
  fontWeight: 700,
  fontSize: "0.875rem",
  cursor: "pointer",
  letterSpacing: "0.01em",
};

const ghostBtn: React.CSSProperties = {
  background: "none",
  color: "var(--muted)",
  border: "1px solid var(--border)",
  borderRadius: "0.4rem",
  padding: "0.55rem 1rem",
  fontWeight: 600,
  fontSize: "0.875rem",
  cursor: "pointer",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.75rem",
  fontWeight: 700,
  color: "var(--text)",
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  marginBottom: "0.35rem",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.6rem 0.85rem",
  border: "1.5px solid var(--border)",
  borderRadius: "0.4rem",
  fontSize: "0.9rem",
  color: "var(--text)",
  background: "#fff",
};
