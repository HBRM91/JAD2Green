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
  const [form, setForm] = useState({ clientId: "", name: "", year: new Date().getFullYear(), methodologyId: "" });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [lang, setLang] = useState<"FR" | "EN">("FR");

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
    ]).then(([p, c, m]) => { setProjects(p); setClients(c); setMethodologies(m); setLoading(false); });
  }, [token]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setCreating(true); setCreateError(null);
    try {
      const proj = await apiJson<Project>("/projects", token, {
        method: "POST",
        body: JSON.stringify({ client_id: form.clientId, name: form.name, reporting_year: form.year, methodology_id: form.methodologyId || methodologies[0]?.id }),
      });
      setProjects((p) => [...p, proj]);
      setShowCreate(false);
      setForm({ clientId: "", name: "", year: new Date().getFullYear(), methodologyId: "" });
    } catch { setCreateError(t("createError", lang)); }
    finally { setCreating(false); }
  }

  async function handleLogout() { await supabase.auth.signOut(); router.push("/login"); }

  if (loading) return <Spinner />;

  const active = projects.filter((p) => p.status === "active").length;
  const completed = projects.filter((p) => p.status === "completed").length;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <Topbar onLogout={handleLogout} lang={lang} onLangChange={setLang} />

      {/* Hero strip */}
      <div style={heroStrip}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 1.5rem" }}>
          <p style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.6)", margin: "0 0 0.5rem" }}>
            {t("platform", lang)}
          </p>
          <h1 style={{ fontSize: "2rem", fontWeight: 900, color: "#fff", margin: "0 0 0.5rem" }}>
            {t("heroTitle", lang)}
          </h1>
          <p style={{ color: "rgba(255,255,255,0.75)", fontSize: "0.95rem", margin: 0, maxWidth: 560 }}>
            {t("heroSub", lang)}
          </p>
        </div>
      </div>

      {/* Metrics bar */}
      <div style={metricsBar}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 1.5rem", display: "flex", gap: "3rem", flexWrap: "wrap" }}>
          <Metric value={projects.length} label={t("totalProjects", lang)} />
          <Metric value={active} label={t("activeProjects", lang)} color="var(--green)" />
          <Metric value={completed} label={t("completedProjects", lang)} color="var(--accent)" />
          <Metric value={clients.length} label={t("clients", lang)} color="var(--amber)" />
        </div>
      </div>

      <div style={pageWrap}>
        {/* Projects header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "1.5rem" }}>
          <div>
            <h2 style={{ fontSize: "1.2rem", fontWeight: 800, color: "var(--navy)", margin: 0 }}>{t("myProjects", lang)}</h2>
            <p style={{ color: "var(--muted)", fontSize: "0.85rem", margin: "0.2rem 0 0" }}>{projects.length} {t("projectsCount", lang)}</p>
          </div>
          <button onClick={() => setShowCreate(true)} style={primaryBtn}>+ {t("newProject", lang)}</button>
        </div>

        {/* Create form */}
        {showCreate && (
          <div style={{ ...card, marginBottom: "1.5rem", borderLeft: "4px solid var(--navy)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--navy)", marginBottom: "1.1rem" }}>{t("createProject", lang)}</h3>
            <form onSubmit={handleCreate} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>{t("client", lang)} *</label>
                <select value={form.clientId} onChange={(e) => setForm({ ...form, clientId: e.target.value })} required style={inputStyle}>
                  <option value="">{t("selectClient", lang)}</option>
                  {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>{t("projectName", lang)} *</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required style={inputStyle} placeholder="Ex: Bilan Carbone FY2024" />
              </div>
              <div>
                <label style={labelStyle}>{t("year", lang)} *</label>
                <input type="number" value={form.year} onChange={(e) => setForm({ ...form, year: parseInt(e.target.value) })} required min={2000} max={2100} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>{t("methodology", lang)}</label>
                <select value={form.methodologyId} onChange={(e) => setForm({ ...form, methodologyId: e.target.value })} style={inputStyle}>
                  {methodologies.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
              {createError && <div style={{ gridColumn: "1 / -1", ...errorBox }}>{createError}</div>}
              <div style={{ gridColumn: "1 / -1", display: "flex", gap: "0.75rem" }}>
                <button type="submit" disabled={creating} style={primaryBtn}>{creating ? t("creating", lang) : t("create", lang)}</button>
                <button type="button" onClick={() => setShowCreate(false)} style={ghostBtn}>{t("cancel", lang)}</button>
              </div>
            </form>
          </div>
        )}

        {/* Projects grid */}
        {projects.length === 0 ? (
          <EmptyState onCreate={() => setShowCreate(true)} lang={lang} />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
            {projects.map((p) => <ProjectCard key={p.id} project={p} onClick={() => router.push(`/projects/${p.id}`)} />)}
          </div>
        )}

        {/* Three-step workflow (JAD2 Advisory pattern) */}
        <div style={{ marginTop: "3rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--navy)", textAlign: "center", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: "1.5rem" }}>
            {t("howItWorks", lang)}
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
            {steps(lang).map((s, i) => (
              <div key={i} style={stepCard}>
                <div style={stepNumber}>{i + 1}</div>
                <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--navy)", margin: "0.75rem 0 0.4rem" }}>{s.title}</div>
                <div style={{ fontSize: "0.82rem", color: "var(--muted)", lineHeight: 1.5 }}>{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Topbar({ onLogout, lang, onLangChange }: { onLogout: () => void; lang: "FR" | "EN"; onLangChange: (l: "FR" | "EN") => void }) {
  return (
    <header style={topbarStyle}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={logoChip}>JAD2</span>
        <span style={{ fontSize: "0.65rem", color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600 }}>Advisory</span>
        <span style={{ color: "var(--border)", padding: "0 0.4rem" }}>|</span>
        <span style={{ fontWeight: 700, color: "var(--navy)", fontSize: "0.95rem" }}>Adrar AI</span>
      </div>
      <nav style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
        <span style={{ fontWeight: 600, color: "var(--navy)", fontSize: "0.875rem", borderBottom: "2px solid var(--navy)", paddingBottom: "0.1rem" }}>
          {lang === "FR" ? "Projets" : "Projects"}
        </span>
        <div style={{ display: "flex", gap: "0.25rem" }}>
          {(["FR", "EN"] as const).map((l) => (
            <button key={l} onClick={() => onLangChange(l)} style={{ background: lang === l ? "var(--navy)" : "transparent", color: lang === l ? "#fff" : "var(--muted)", border: "1px solid var(--border)", borderRadius: "0.25rem", padding: "0.2rem 0.5rem", fontSize: "0.75rem", fontWeight: 700, cursor: "pointer" }}>{l}</button>
          ))}
        </div>
        <button onClick={onLogout} style={ghostBtn}>{lang === "FR" ? "Déconnexion" : "Sign out"}</button>
      </nav>
    </header>
  );
}

function Metric({ value, label, color = "var(--navy)" }: { value: number; label: string; color?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.15rem" }}>
      <span style={{ fontSize: "1.75rem", fontWeight: 900, color }}>{value}</span>
      <span style={{ fontSize: "0.8rem", color: "var(--muted)", fontWeight: 500 }}>{label}</span>
    </div>
  );
}

function ProjectCard({ project: p, onClick }: { project: Project; onClick: () => void }) {
  const [hovered, setHovered] = useState(false);
  const colors: Record<string, string> = { active: "#16a34a", completed: "#2563eb", archived: "#94a3b8" };
  const color = colors[p.status] ?? "var(--muted)";
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ ...projectCardStyle, boxShadow: hovered ? "0 4px 16px rgba(26,46,94,0.1)" : "none", borderColor: hovered ? "var(--navy)" : "var(--border)" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.85rem" }}>
        <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color, background: `${color}18`, padding: "0.2rem 0.55rem", borderRadius: "9999px" }}>{p.status}</span>
        <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--muted)" }}>{p.reporting_year}</span>
      </div>
      <h3 style={{ fontWeight: 700, fontSize: "1rem", color: "var(--navy)", margin: "0 0 0.3rem" }}>{p.name}</h3>
      <p style={{ color: "var(--muted)", fontSize: "0.8rem", margin: 0 }}>{new Date(p.created_at).toLocaleDateString("fr-FR")}</p>
      <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "flex-end" }}>
        <span style={{ color: "var(--accent)", fontSize: "0.82rem", fontWeight: 700 }}>Ouvrir →</span>
      </div>
    </div>
  );
}

function EmptyState({ onCreate, lang }: { onCreate: () => void; lang: "FR" | "EN" }) {
  return (
    <div style={{ textAlign: "center", padding: "4rem 2rem", background: "#fff", borderRadius: "0.75rem", border: "2px dashed var(--border)" }}>
      <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>📊</div>
      <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--navy)", margin: "0 0 0.5rem" }}>
        {lang === "FR" ? "Aucun projet" : "No projects yet"}
      </h3>
      <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
        {lang === "FR" ? "Créez votre premier projet de Bilan Carbone." : "Create your first Carbon Assessment project."}
      </p>
      <button onClick={onCreate} style={primaryBtn}>
        {lang === "FR" ? "+ Nouveau projet" : "+ New project"}
      </button>
    </div>
  );
}

function Spinner() {
  return <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}><div style={{ width: 36, height: 36, border: "3px solid var(--border)", borderTopColor: "var(--navy)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} /></div>;
}

// ── i18n ──────────────────────────────────────────────────────────────────

const i18n = {
  platform:       { FR: "Plateforme · JAD2 Advisory", EN: "Platform · JAD2 Advisory" },
  heroTitle:      { FR: "Pilotage Carbone Réglementaire", EN: "Regulatory Carbon Management" },
  heroSub:        { FR: "Bilan Carbone conforme, traçable et sécurisé pour bureaux d'étude. Calcul déterministe, isolation multi-tenant, rapport DOCX.", EN: "Compliant, traceable and secure Carbon Assessment for consulting firms. Deterministic calculation, multi-tenant isolation, DOCX report." },
  totalProjects:  { FR: "Projets total", EN: "Total projects" },
  activeProjects: { FR: "Projets actifs", EN: "Active projects" },
  completedProjects: { FR: "Terminés", EN: "Completed" },
  clients:        { FR: "Clients", EN: "Clients" },
  myProjects:     { FR: "Mes projets", EN: "My projects" },
  projectsCount:  { FR: "projets", EN: "projects" },
  newProject:     { FR: "Nouveau projet", EN: "New project" },
  createProject:  { FR: "Créer un projet", EN: "Create a project" },
  client:         { FR: "Client", EN: "Client" },
  selectClient:   { FR: "Sélectionner un client...", EN: "Select a client..." },
  projectName:    { FR: "Nom du projet", EN: "Project name" },
  year:           { FR: "Année", EN: "Year" },
  methodology:    { FR: "Méthodologie", EN: "Methodology" },
  create:         { FR: "Créer", EN: "Create" },
  creating:       { FR: "Création...", EN: "Creating..." },
  cancel:         { FR: "Annuler", EN: "Cancel" },
  createError:    { FR: "Impossible de créer le projet.", EN: "Failed to create project." },
  howItWorks:     { FR: "Comment ça marche", EN: "How it works" },
};

function t(key: keyof typeof i18n, lang: "FR" | "EN"): string {
  return i18n[key][lang];
}

function steps(lang: "FR" | "EN") {
  return lang === "FR" ? [
    { title: "Importer les données", desc: "Chargez vos documents (PDF, XLSX, CSV). L'extraction est automatique et traçable, avec provenance par champ." },
    { title: "Valider les faits", desc: "Revue humaine obligatoire : seul le consultant habilité peut promouvoir un fait de 'proposé' à 'validé'." },
    { title: "Calculer & Publier", desc: "Le noyau de calcul déterministe produit le snapshot Bilan Carbone avec rapport DOCX en un clic." },
  ] : [
    { title: "Import data", desc: "Upload your documents (PDF, XLSX, CSV). Extraction is automatic and traceable, with per-field provenance." },
    { title: "Validate facts", desc: "Mandatory human review: only an authorised consultant can promote a fact from 'proposed' to 'validated'." },
    { title: "Compute & Publish", desc: "The deterministic calculation kernel produces the Carbon Assessment snapshot with a DOCX report in one click." },
  ];
}

// ── Styles ─────────────────────────────────────────────────────────────────

const topbarStyle: React.CSSProperties = {
  background: "#fff", borderBottom: "1px solid var(--border)",
  padding: "0 2rem", height: "56px", display: "flex",
  alignItems: "center", justifyContent: "space-between",
  position: "sticky", top: 0, zIndex: 100,
  boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
};
const logoChip: React.CSSProperties = {
  background: "var(--navy)", color: "#fff", fontWeight: 900,
  fontSize: "0.7rem", letterSpacing: "0.15em",
  padding: "0.25rem 0.55rem", borderRadius: "0.2rem",
};
const heroStrip: React.CSSProperties = {
  background: "linear-gradient(135deg, var(--navy-dark) 0%, var(--navy) 60%, var(--navy-light) 100%)",
  padding: "2.5rem 0 2rem",
};
const metricsBar: React.CSSProperties = {
  background: "#fff", borderBottom: "1px solid var(--border)",
  padding: "1.25rem 0",
};
const pageWrap: React.CSSProperties = { maxWidth: 1100, margin: "2rem auto", padding: "0 1.5rem" };
const card: React.CSSProperties = { background: "#fff", border: "1px solid var(--border)", borderRadius: "0.6rem", padding: "1.5rem" };
const projectCardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid var(--border)",
  borderRadius: "0.6rem", padding: "1.25rem", cursor: "pointer",
  transition: "box-shadow 0.15s, border-color 0.15s",
};
const stepCard: React.CSSProperties = {
  background: "#fff", border: "1px solid var(--border)",
  borderRadius: "0.6rem", padding: "1.5rem",
};
const stepNumber: React.CSSProperties = {
  width: 32, height: 32, borderRadius: "50%",
  background: "var(--navy)", color: "#fff",
  fontWeight: 900, fontSize: "0.9rem",
  display: "flex", alignItems: "center", justifyContent: "center",
};
const primaryBtn: React.CSSProperties = {
  background: "var(--navy)", color: "#fff", border: "none",
  borderRadius: "0.4rem", padding: "0.6rem 1.2rem",
  fontWeight: 700, fontSize: "0.875rem", cursor: "pointer",
};
const ghostBtn: React.CSSProperties = {
  background: "none", color: "var(--muted)", border: "1px solid var(--border)",
  borderRadius: "0.4rem", padding: "0.5rem 1rem",
  fontWeight: 600, fontSize: "0.875rem", cursor: "pointer",
};
const labelStyle: React.CSSProperties = {
  display: "block", fontSize: "0.72rem", fontWeight: 700,
  color: "var(--text)", letterSpacing: "0.05em",
  textTransform: "uppercase", marginBottom: "0.35rem",
};
const inputStyle: React.CSSProperties = {
  width: "100%", padding: "0.6rem 0.85rem",
  border: "1.5px solid var(--border)", borderRadius: "0.4rem",
  fontSize: "0.9rem", color: "var(--text)", background: "#fff",
};
const errorBox: React.CSSProperties = {
  background: "#fef2f2", border: "1px solid #fca5a5",
  borderRadius: "0.375rem", padding: "0.6rem 0.85rem",
  color: "var(--red)", fontSize: "0.85rem",
};
