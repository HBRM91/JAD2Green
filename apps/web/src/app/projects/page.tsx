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
  const [showCreateClient, setShowCreateClient] = useState(false);
  const [clientForm, setClientForm] = useState({ name: "", sector: "", naics_code: "", secteur_maroc: "", is_listed_bvc: false, rse_reporting_required: false });
  const [creatingClient, setCreatingClient] = useState(false);
  const [createClientError, setCreateClientError] = useState<string | null>(null);
  const [form, setForm] = useState({
    clientId: "", name: "", year: new Date().getFullYear(), methodologyId: "",
    reportingFrameworks: [] as string[], sectorCode: "", language: "fr",
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [lang, setLang] = useState<"FR" | "EN" | "AR">("FR");

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
        body: JSON.stringify({
          client_id: form.clientId, name: form.name, reporting_year: form.year,
          methodology_id: form.methodologyId || methodologies[0]?.id,
          reporting_frameworks: form.reportingFrameworks.length ? form.reportingFrameworks : null,
          sector_code: form.sectorCode || null,
          language: form.language,
        }),
      });
      setProjects((p) => [...p, proj]);
      setShowCreate(false);
      setForm({ clientId: "", name: "", year: new Date().getFullYear(), methodologyId: "", reportingFrameworks: [], sectorCode: "", language: "fr" });
    } catch { setCreateError(t("createError", lang)); }
    finally { setCreating(false); }
  }

  async function handleCreateClient(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setCreatingClient(true); setCreateClientError(null);
    try {
      const client = await apiJson<Client>("/clients", token, {
        method: "POST",
        body: JSON.stringify({
          name: clientForm.name, sector: clientForm.sector || null,
          naics_code: clientForm.naics_code || null,
          secteur_maroc: clientForm.secteur_maroc || null,
          is_listed_bvc: clientForm.is_listed_bvc,
          rse_reporting_required: clientForm.rse_reporting_required,
        }),
      });
      setClients((c) => [...c, client]);
      setShowCreateClient(false);
      setClientForm({ name: "", sector: "", naics_code: "", secteur_maroc: "", is_listed_bvc: false, rse_reporting_required: false });
    } catch { setCreateClientError(lang === "FR" ? "Impossible de créer le client." : lang === "AR" ? "تعذر إنشاء العميل." : "Failed to create client."); }
    finally { setCreatingClient(false); }
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
          <div style={{ display: "flex", gap: "0.6rem" }}>
            <button onClick={() => { setShowCreateClient(true); setShowCreate(false); }} style={ghostBtn}>
              + {lang === "FR" ? "Nouveau client" : lang === "AR" ? "+ عميل جديد" : "+ New client"}
            </button>
            <button onClick={() => { setShowCreate(true); setShowCreateClient(false); }} style={primaryBtn}>+ {t("newProject", lang)}</button>
          </div>
        </div>

        {/* Create client form */}
        {showCreateClient && (
          <div style={{ ...card, marginBottom: "1.5rem", borderLeft: "4px solid var(--accent)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--accent)", marginBottom: "1.1rem" }}>
              {lang === "FR" ? "Nouveau client" : lang === "AR" ? "عميل جديد" : "New client"}
            </h3>
            <form onSubmit={handleCreateClient} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>{lang === "FR" ? "Nom de l'entreprise" : lang === "AR" ? "اسم الشركة" : "Company name"} *</label>
                <input value={clientForm.name} onChange={(e) => setClientForm({ ...clientForm, name: e.target.value })} required style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>{lang === "FR" ? "Secteur Maroc" : lang === "AR" ? "القطاع (المغرب)" : "Morocco sector"}</label>
                <select value={clientForm.secteur_maroc} onChange={(e) => setClientForm({ ...clientForm, secteur_maroc: e.target.value })} style={inputStyle}>
                  <option value="">{lang === "FR" ? "Sélectionner..." : lang === "AR" ? "اختر..." : "Select..."}</option>
                  {MOROCCO_SECTORS.map((s) => <option key={s.code} value={s.code}>{s.label[lang]}</option>)}
                </select>
              </div>
              <div>
                <label style={labelStyle}>{lang === "FR" ? "Code NAICS" : "NAICS code"}</label>
                <input value={clientForm.naics_code} onChange={(e) => setClientForm({ ...clientForm, naics_code: e.target.value })} style={inputStyle} placeholder="ex: C24" />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", paddingTop: "1.2rem" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", cursor: "pointer", fontSize: "0.82rem", fontWeight: 600, color: "var(--text)" }}>
                  <input type="checkbox" checked={clientForm.is_listed_bvc} onChange={(e) => setClientForm({ ...clientForm, is_listed_bvc: e.target.checked })} />
                  {lang === "FR" ? "Coté Bourse BVC" : lang === "AR" ? "مُدرج في BVC" : "Listed on BVC"}
                </label>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", paddingTop: "1.2rem" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", cursor: "pointer", fontSize: "0.82rem", fontWeight: 600, color: "var(--text)" }}>
                  <input type="checkbox" checked={clientForm.rse_reporting_required} onChange={(e) => setClientForm({ ...clientForm, rse_reporting_required: e.target.checked })} />
                  {lang === "FR" ? "Rapport RSE obligatoire" : lang === "AR" ? "تقرير RSE إلزامي" : "RSE report required"}
                </label>
              </div>
              {createClientError && <div style={{ gridColumn: "1 / -1", ...errorBox }}>{createClientError}</div>}
              <div style={{ gridColumn: "1 / -1", display: "flex", gap: "0.75rem" }}>
                <button type="submit" disabled={creatingClient} style={primaryBtn}>{creatingClient ? "…" : (lang === "FR" ? "Créer" : lang === "AR" ? "إنشاء" : "Create")}</button>
                <button type="button" onClick={() => setShowCreateClient(false)} style={ghostBtn}>{t("cancel", lang)}</button>
              </div>
            </form>
          </div>
        )}

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
              <div>
                <label style={labelStyle}>{t("sectorCode", lang)}</label>
                <select value={form.sectorCode} onChange={(e) => setForm({ ...form, sectorCode: e.target.value })} style={inputStyle}>
                  <option value="">{lang === "FR" ? "Sélectionner..." : lang === "AR" ? "اختر..." : "Select..."}</option>
                  {MOROCCO_SECTORS.map((s) => <option key={s.code} value={s.code}>{s.label[lang]}</option>)}
                </select>
              </div>
              <div>
                <label style={labelStyle}>{t("reportLang", lang)}</label>
                <select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} style={inputStyle}>
                  <option value="fr">Français</option>
                  <option value="en">English</option>
                  <option value="ar">العربية</option>
                </select>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={{ ...labelStyle, marginBottom: "0.6rem" }}>{t("frameworks", lang)}</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {REPORTING_FRAMEWORKS.map((f) => {
                    const checked = form.reportingFrameworks.includes(f.key);
                    return (
                      <button
                        key={f.key}
                        type="button"
                        onClick={() => setForm((prev) => ({
                          ...prev,
                          reportingFrameworks: checked
                            ? prev.reportingFrameworks.filter((x) => x !== f.key)
                            : [...prev.reportingFrameworks, f.key],
                        }))}
                        style={{
                          background: checked ? "var(--navy)" : "#fff",
                          color: checked ? "#fff" : "var(--muted)",
                          border: `1.5px solid ${checked ? "var(--navy)" : "var(--border)"}`,
                          borderRadius: "9999px",
                          padding: "0.3rem 0.8rem",
                          fontSize: "0.78rem",
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        {f.label}
                      </button>
                    );
                  })}
                </div>
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

        {/* Clients overview */}
        {clients.length > 0 && (
          <div style={{ marginTop: "2.5rem" }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--navy)", margin: "0 0 1rem" }}>
              {lang === "FR" ? "Portefeuille clients" : lang === "AR" ? "محفظة العملاء" : "Client portfolio"}
              <span style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--muted)", marginLeft: "0.5rem" }}>({clients.length})</span>
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "0.75rem" }}>
              {clients.map((c) => (
                <div key={c.id} style={{ background: "#fff", border: "1px solid var(--border)", borderRadius: "0.75rem", padding: "1rem 1.1rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.4rem" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.9rem", color: "var(--navy)" }}>{c.name}</span>
                    <div style={{ display: "flex", gap: "0.3rem" }}>
                      {c.is_listed_bvc && <span style={{ fontSize: "0.6rem", fontWeight: 700, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", borderRadius: "9999px", padding: "0.1rem 0.4rem" }}>BVC</span>}
                      {c.rse_reporting_required && <span style={{ fontSize: "0.6rem", fontWeight: 700, background: "#f0fdf4", color: "#166534", border: "1px solid #86efac", borderRadius: "9999px", padding: "0.1rem 0.4rem" }}>RSE</span>}
                    </div>
                  </div>
                  {c.secteur_maroc && <p style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600, margin: 0 }}>{c.secteur_maroc}</p>}
                  <p style={{ fontSize: "0.72rem", color: "var(--muted)", margin: "0.25rem 0 0" }}>
                    {projects.filter((p) => p.client_id === c.id).length} {lang === "FR" ? "projet(s)" : lang === "AR" ? "مشروع" : "project(s)"}
                  </p>
                </div>
              ))}
            </div>
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

        {/* Footer */}
        <footer style={{ marginTop: "4rem", borderTop: "1px solid var(--border)", paddingTop: "2rem", paddingBottom: "2rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "2rem" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <span style={{ ...logoChip, fontSize: "0.65rem" }}>JAD2</span>
                <span style={{ fontSize: "0.75rem", color: "var(--muted)", fontWeight: 600, letterSpacing: "0.08em" }}>Advisory</span>
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--muted-light)", margin: 0, maxWidth: 280, lineHeight: 1.5 }}>
                {lang === "FR" ? "Plateforme de reporting carbone réglementaire pour bureaux d'étude. Calcul ISO 14064 conforme et traçable."
                  : lang === "AR" ? "منصة إعداد تقارير الكربون التنظيمية لمكاتب الدراسات. حساب متوافق مع ISO 14064 وقابل للتتبع."
                  : "Regulatory carbon reporting platform for consulting firms. ISO 14064 compliant and traceable computation."}
              </p>
            </div>
            <div style={{ display: "flex", gap: "3rem" }}>
              <div>
                <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--navy)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.6rem" }}>
                  {lang === "FR" ? "Conformité" : lang === "AR" ? "الامتثال" : "Compliance"}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                  {["ISO 14064-1", "Bilan Carbone® ADEME", "IPCC AR6 GWP"].map((item) => (
                    <span key={item} style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{item}</span>
                  ))}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--navy)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "0.6rem" }}>
                  {lang === "FR" ? "Sécurité" : lang === "AR" ? "الأمان" : "Security"}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                  {[
                    lang === "FR" ? "Isolation multi-tenant RLS" : lang === "AR" ? "عزل متعدد المستأجرين" : "Multi-tenant RLS isolation",
                    lang === "FR" ? "Chiffrement données at rest" : lang === "AR" ? "تشفير البيانات" : "Data at rest encryption",
                    lang === "FR" ? "Hébergement en région" : lang === "AR" ? "استضافة داخل المنطقة" : "In-region hosting",
                  ].map((item) => (
                    <span key={item} style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{item}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div style={{ marginTop: "1.5rem", fontSize: "0.72rem", color: "var(--muted-light)", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
            {lang === "FR" ? "© JAD2 Advisory · Adrar AI · Ce rapport contient une assistance IA — les facteurs d'émission requièrent une validation experte (§0.12)."
              : lang === "AR" ? "© JAD2 Advisory · Adrar AI · يحتوي هذا التقرير على مساعدة ذكاء اصطناعي — تتطلب عوامل الانبعاث التحقق من قبل خبير (§0.12)."
              : "© JAD2 Advisory · Adrar AI · This report contains AI assistance — emission factors require expert validation (§0.12)."}
          </div>
        </footer>
      </div>
    </div>
  );
}

function Topbar({ onLogout, lang, onLangChange }: { onLogout: () => void; lang: "FR" | "EN" | "AR"; onLangChange: (l: "FR" | "EN" | "AR") => void }) {
  const isRtl = lang === "AR";
  return (
    <header style={{ ...topbarStyle, direction: isRtl ? "rtl" : "ltr" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={logoChip}>JAD2</span>
        <span style={{ fontSize: "0.65rem", color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600 }}>Advisory</span>
        <span style={{ color: "var(--border)", padding: "0 0.4rem" }}>|</span>
        <span style={{ fontWeight: 700, color: "var(--navy)", fontSize: "0.95rem" }}>Adrar AI</span>
      </div>
      <nav style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
        <span style={{ fontWeight: 600, color: "var(--navy)", fontSize: "0.875rem", borderBottom: "2px solid var(--navy)", paddingBottom: "0.1rem" }}>
          {lang === "FR" ? "Projets" : lang === "AR" ? "المشاريع" : "Projects"}
        </span>
        <div style={{ display: "flex", gap: "0.25rem" }}>
          {(["FR", "EN", "AR"] as const).map((l) => (
            <button key={l} onClick={() => onLangChange(l)} style={{ background: lang === l ? "var(--navy)" : "transparent", color: lang === l ? "#fff" : "var(--muted)", border: "1px solid var(--border)", borderRadius: "0.25rem", padding: "0.2rem 0.5rem", fontSize: "0.75rem", fontWeight: 700, cursor: "pointer" }}>{l}</button>
          ))}
        </div>
        <button onClick={onLogout} style={ghostBtn}>{lang === "FR" ? "Déconnexion" : lang === "AR" ? "تسجيل الخروج" : "Sign out"}</button>
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
  const fwColors: Record<string, string> = { gri_305: "#1d4ed8", amee: "#16a34a", iso_14064: "#7c3aed", ghg_protocol: "#0369a1", csrd_esrs: "#b45309", tcfd: "#dc2626", cdp: "#0891b2", bilan_carbone: "#374151" };
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ ...projectCardStyle, boxShadow: hovered ? "0 4px 16px rgba(26,46,94,0.1)" : "none", borderColor: hovered ? "var(--navy)" : "var(--border)" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.85rem" }}>
        <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color, background: `${color}18`, padding: "0.2rem 0.55rem", borderRadius: "9999px" }}>{p.status}</span>
        <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
          {p.language && <span style={{ fontSize: "0.65rem", fontWeight: 700, color: "var(--muted)", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "0.25rem", padding: "0.1rem 0.35rem" }}>{p.language.toUpperCase()}</span>}
          <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--muted)" }}>{p.reporting_year}</span>
        </div>
      </div>
      <h3 style={{ fontWeight: 700, fontSize: "1rem", color: "var(--navy)", margin: "0 0 0.3rem" }}>{p.name}</h3>
      {p.sector_code && <p style={{ color: "var(--accent)", fontSize: "0.75rem", fontWeight: 600, margin: "0 0 0.3rem" }}>{p.sector_code}</p>}
      <p style={{ color: "var(--muted)", fontSize: "0.8rem", margin: 0 }}>{new Date(p.created_at).toLocaleDateString("fr-FR")}</p>
      {p.reporting_frameworks && p.reporting_frameworks.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.75rem" }}>
          {p.reporting_frameworks.slice(0, 4).map((fw) => {
            const c = fwColors[fw] ?? "#374151";
            return <span key={fw} style={{ fontSize: "0.62rem", fontWeight: 700, color: "#fff", background: c, borderRadius: "9999px", padding: "0.15rem 0.45rem" }}>{fw.replace(/_/g, " ").toUpperCase()}</span>;
          })}
          {p.reporting_frameworks.length > 4 && <span style={{ fontSize: "0.62rem", color: "var(--muted)" }}>+{p.reporting_frameworks.length - 4}</span>}
        </div>
      )}
      <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "flex-end" }}>
        <span style={{ color: "var(--accent)", fontSize: "0.82rem", fontWeight: 700 }}>Ouvrir →</span>
      </div>
    </div>
  );
}

function EmptyState({ onCreate, lang }: { onCreate: () => void; lang: "FR" | "EN" | "AR" }) {
  const txt = {
    FR: { title: "Aucun projet", sub: "Créez votre premier projet de Bilan Carbone.", btn: "+ Nouveau projet" },
    EN: { title: "No projects yet", sub: "Create your first Carbon Assessment project.", btn: "+ New project" },
    AR: { title: "لا توجد مشاريع", sub: "أنشئ مشروع بصمة الكربون الأول.", btn: "+ مشروع جديد" },
  }[lang];
  return (
    <div style={{ textAlign: "center", padding: "4rem 2rem", background: "#fff", borderRadius: "0.75rem", border: "2px dashed var(--border)", direction: lang === "AR" ? "rtl" : "ltr" }}>
      <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>📊</div>
      <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--navy)", margin: "0 0 0.5rem" }}>{txt.title}</h3>
      <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>{txt.sub}</p>
      <button onClick={onCreate} style={primaryBtn}>{txt.btn}</button>
    </div>
  );
}

function Spinner() {
  return <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}><div style={{ width: 36, height: 36, border: "3px solid var(--border)", borderTopColor: "var(--navy)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} /></div>;
}

// ── i18n ──────────────────────────────────────────────────────────────────

const i18n = {
  platform:          { FR: "Plateforme · JAD2 Advisory", EN: "Platform · JAD2 Advisory", AR: "منصة · JAD2 Advisory" },
  heroTitle:         { FR: "Pilotage Carbone Réglementaire", EN: "Regulatory Carbon Management", AR: "إدارة الكربون التنظيمية" },
  heroSub:           { FR: "Bilan Carbone conforme, traçable et sécurisé pour bureaux d'étude. Calcul déterministe, isolation multi-tenant, rapport DOCX.", EN: "Compliant, traceable and secure Carbon Assessment for consulting firms. Deterministic calculation, multi-tenant isolation, DOCX report.", AR: "تقييم الكربون المتوافق والقابل للتتبع لمكاتب الدراسات. حساب حتمي وعزل متعدد المستأجرين وتقرير DOCX." },
  totalProjects:     { FR: "Projets total", EN: "Total projects", AR: "إجمالي المشاريع" },
  activeProjects:    { FR: "Projets actifs", EN: "Active projects", AR: "المشاريع النشطة" },
  completedProjects: { FR: "Terminés", EN: "Completed", AR: "مكتملة" },
  clients:           { FR: "Clients", EN: "Clients", AR: "العملاء" },
  myProjects:        { FR: "Mes projets", EN: "My projects", AR: "مشاريعي" },
  projectsCount:     { FR: "projets", EN: "projects", AR: "مشاريع" },
  newProject:        { FR: "Nouveau projet", EN: "New project", AR: "مشروع جديد" },
  createProject:     { FR: "Créer un projet", EN: "Create a project", AR: "إنشاء مشروع" },
  client:            { FR: "Client", EN: "Client", AR: "العميل" },
  selectClient:      { FR: "Sélectionner un client...", EN: "Select a client...", AR: "اختر عميلاً..." },
  projectName:       { FR: "Nom du projet", EN: "Project name", AR: "اسم المشروع" },
  year:              { FR: "Année", EN: "Year", AR: "السنة" },
  methodology:       { FR: "Méthodologie", EN: "Methodology", AR: "المنهجية" },
  frameworks:        { FR: "Référentiels de reporting", EN: "Reporting frameworks", AR: "أطر إعداد التقارير" },
  sectorCode:        { FR: "Secteur d'activité", EN: "Activity sector", AR: "قطاع النشاط" },
  reportLang:        { FR: "Langue du rapport", EN: "Report language", AR: "لغة التقرير" },
  create:            { FR: "Créer", EN: "Create", AR: "إنشاء" },
  creating:          { FR: "Création...", EN: "Creating...", AR: "جارٍ الإنشاء..." },
  cancel:            { FR: "Annuler", EN: "Cancel", AR: "إلغاء" },
  createError:       { FR: "Impossible de créer le projet.", EN: "Failed to create project.", AR: "تعذر إنشاء المشروع." },
  howItWorks:        { FR: "Comment ça marche", EN: "How it works", AR: "كيف يعمل" },
};

function t(key: keyof typeof i18n, lang: "FR" | "EN" | "AR"): string {
  return i18n[key][lang];
}

function steps(lang: "FR" | "EN" | "AR") {
  const s = {
    FR: [
      { title: "Importer les données", desc: "Chargez vos documents (PDF, XLSX, CSV). L'extraction est automatique et traçable, avec provenance par champ." },
      { title: "Valider les faits", desc: "Revue humaine obligatoire : seul le consultant habilité peut promouvoir un fait de 'proposé' à 'validé'." },
      { title: "Calculer & Publier", desc: "Le noyau de calcul déterministe produit le snapshot Bilan Carbone avec rapport DOCX en un clic." },
    ],
    EN: [
      { title: "Import data", desc: "Upload your documents (PDF, XLSX, CSV). Extraction is automatic and traceable, with per-field provenance." },
      { title: "Validate facts", desc: "Mandatory human review: only an authorised consultant can promote a fact from 'proposed' to 'validated'." },
      { title: "Compute & Publish", desc: "The deterministic calculation kernel produces the Carbon Assessment snapshot with a DOCX report in one click." },
    ],
    AR: [
      { title: "استيراد البيانات", desc: "ارفع مستنداتك (PDF، XLSX، CSV). الاستخراج تلقائي وقابل للتتبع مع توثيق مصدر كل حقل." },
      { title: "التحقق من الحقائق", desc: "مراجعة بشرية إلزامية: فقط المستشار المعتمد يمكنه الترقية من 'مقترح' إلى 'مُتحقق'." },
      { title: "الحساب والنشر", desc: "نواة الحساب الحتمية تنتج لقطة بيان الكربون مع تقرير DOCX بنقرة واحدة." },
    ],
  };
  return s[lang];
}

const REPORTING_FRAMEWORKS = [
  { key: "bilan_carbone", label: "Bilan Carbone®" },
  { key: "iso_14064", label: "ISO 14064-1" },
  { key: "ghg_protocol", label: "GHG Protocol" },
  { key: "gri_305", label: "GRI 305" },
  { key: "amee", label: "AMEE Bilan Énergétique" },
  { key: "csrd", label: "CSRD/ESRS" },
  { key: "tcfd", label: "TCFD" },
  { key: "cdp", label: "CDP" },
];

const MOROCCO_SECTORS: { code: string; label: { FR: string; EN: string; AR: string } }[] = [
  { code: "A01", label: { FR: "Agriculture & Élevage", EN: "Agriculture & Livestock", AR: "الزراعة والثروة الحيوانية" } },
  { code: "B08", label: { FR: "Industries Extractives (Mines, Phosphates)", EN: "Extractive Industries (Mining, Phosphates)", AR: "الصناعات الاستخراجية (مناجم، فوسفات)" } },
  { code: "C23", label: { FR: "Industrie du Ciment & Matériaux", EN: "Cement & Construction Materials", AR: "صناعة الإسمنت والمواد" } },
  { code: "C24", label: { FR: "Sidérurgie & Métallurgie", EN: "Steel & Metallurgy", AR: "الصلب والمعادن" } },
  { code: "C13", label: { FR: "Industrie Textile & Habillement", EN: "Textile & Clothing", AR: "صناعة النسيج والملابس" } },
  { code: "D35", label: { FR: "Production d'Énergie (ONEE, EnR)", EN: "Energy Production (ONEE, RES)", AR: "إنتاج الطاقة (ONEE، طاقة متجددة)" } },
  { code: "E38", label: { FR: "Collecte & Traitement des Déchets", EN: "Waste Collection & Treatment", AR: "جمع ومعالجة النفايات" } },
  { code: "F41", label: { FR: "BTP & Construction", EN: "Construction", AR: "البناء والأشغال العامة" } },
  { code: "G46", label: { FR: "Commerce & Distribution", EN: "Trade & Distribution", AR: "التجارة والتوزيع" } },
  { code: "H49", label: { FR: "Transport Terrestre (ONCF, CTM)", EN: "Land Transport (Rail, Bus)", AR: "النقل البري (سكة حديد، حافلات)" } },
  { code: "H50", label: { FR: "Transport Maritime & Portuaire", EN: "Maritime & Port Transport", AR: "النقل البحري والموانئ" } },
  { code: "I55", label: { FR: "Hôtellerie & Tourisme", EN: "Hospitality & Tourism", AR: "الضيافة والسياحة" } },
  { code: "J61", label: { FR: "Télécom & Numérique", EN: "Telecom & Digital", AR: "الاتصالات والرقمي" } },
  { code: "K64", label: { FR: "Finance & Banque", EN: "Finance & Banking", AR: "المالية والبنوك" } },
  { code: "O84", label: { FR: "Administration Publique", EN: "Public Administration", AR: "الإدارة العامة" } },
  { code: "P85", label: { FR: "Éducation", EN: "Education", AR: "التعليم" } },
  { code: "Q86", label: { FR: "Santé & Pharmacie", EN: "Health & Pharmaceuticals", AR: "الصحة والأدوية" } },
];

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
