"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { apiJson, apiFetch } from "@/lib/api";
import type { ActivityFact, Project, ReportSnapshot, Anomaly } from "@/lib/types";

type Tab = "facts" | "compute" | "results";

export default function ProjectDetailPage() {
  const router = useRouter();
  const { id: projectId } = useParams<{ id: string }>();
  const supabase = createClient();

  const [token, setToken] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [facts, setFacts] = useState<ActivityFact[]>([]);
  const [snapshots, setSnapshots] = useState<ReportSnapshot[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [tab, setTab] = useState<Tab>("facts");
  const [loading, setLoading] = useState(true);

  const [computeForm, setComputeForm] = useState({
    methodology_id: "",
    region: "MA",
    reporting_year: new Date().getFullYear(),
    gwp_basis: "AR6",
  });
  const [computing, setComputing] = useState(false);
  const [computeError, setComputeError] = useState<string | null>(null);

  const [validating, setValidating] = useState<Record<string, boolean>>({});
  const [validateErrors, setValidateErrors] = useState<Record<string, string>>({});

  // §0.11: Google export default OFF — never auto-enable
  const [googleExportEnabled, setGoogleExportEnabled] = useState(false);
  const [exporting, setExporting] = useState<Record<string, boolean>>({});
  const [exportUrls, setExportUrls] = useState<Record<string, string>>({});

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) { router.push("/login"); return; }
      setToken(session.access_token);
    });
  }, []);

  useEffect(() => {
    if (!token || !projectId) return;
    Promise.all([
      apiJson<Project>(`/projects/${projectId}`, token),
      apiJson<ActivityFact[]>(`/projects/${projectId}/activity`, token),
      apiJson<ReportSnapshot[]>(`/projects/${projectId}/snapshots`, token),
    ]).then(([proj, f, s]) => {
      setProject(proj);
      setFacts(f);
      setSnapshots(s);
      setComputeForm((c) => ({
        ...c,
        reporting_year: proj.reporting_year,
        methodology_id: proj.methodology_id,
      }));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [token, projectId]);

  async function handleValidate(factId: string) {
    if (!token) return;
    setValidating((v) => ({ ...v, [factId]: true }));
    setValidateErrors((v) => { const n = { ...v }; delete n[factId]; return n; });
    try {
      const updated = await apiJson<ActivityFact>(
        `/projects/${projectId}/activity/${factId}/validate`,
        token,
        { method: "PATCH" }
      );
      setFacts((f) => f.map((x) => (x.id === factId ? updated : x)));
    } catch {
      setValidateErrors((v) => ({ ...v, [factId]: "Échec de la validation" }));
    } finally {
      setValidating((v) => ({ ...v, [factId]: false }));
    }
  }

  async function handleCompute(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    const pending = facts.filter((f) => f.state === "proposed");
    if (pending.length > 0) {
      setComputeError(`${pending.length} fait(s) encore en état "proposé". Validez-les d'abord.`);
      return;
    }
    setComputing(true);
    setComputeError(null);
    try {
      const snap = await apiJson<ReportSnapshot>(`/projects/${projectId}/compute`, token, {
        method: "POST",
        body: JSON.stringify(computeForm),
      });
      setSnapshots((s) => [snap, ...s]);
      setTab("results");
    } catch {
      setComputeError("Échec du calcul. Vérifiez que tous les faits sont validés et que les données sont complètes.");
    } finally {
      setComputing(false);
    }
  }

  async function handleReconcile() {
    if (!token) return;
    try {
      const flagged = await apiJson<Anomaly[]>(`/projects/${projectId}/reconcile`, token, {
        method: "POST",
      });
      setAnomalies(flagged);
    } catch {
      // silently skip — reconcile is advisory
    }
  }

  async function handleDownloadReport(snapId: string) {
    if (!token) return;
    try {
      const res = await apiFetch(`/projects/${projectId}/snapshots/${snapId}/report`, token);
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bilan_carbone_${projectId}_${snapId}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Non-sensitive error — don't expose internals
    }
  }

  async function handleGoogleExport(snapId: string) {
    if (!token || !googleExportEnabled) return;
    setExporting((e) => ({ ...e, [snapId]: true }));
    try {
      const result = await apiJson<{ doc_url: string }>(
        `/projects/${projectId}/snapshots/${snapId}/export`,
        token,
        {
          method: "POST",
          body: JSON.stringify({ google_access_token: "" }),
        }
      );
      setExportUrls((u) => ({ ...u, [snapId]: result.doc_url }));
    } catch {
      // Export failure — user can retry
    } finally {
      setExporting((e) => ({ ...e, [snapId]: false }));
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !uploadFile) return;

    // Client-side type check (defence-in-depth; backend re-validates)
    const allowed = ["application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/csv", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
    if (!allowed.includes(uploadFile.type)) {
      setUploadMsg({ text: "Type de fichier non supporté. Utilisez PDF, XLSX, CSV ou DOCX.", ok: false });
      return;
    }
    if (uploadFile.size > 50 * 1024 * 1024) {
      setUploadMsg({ text: "Fichier trop volumineux (max 50 Mo).", ok: false });
      return;
    }

    setUploading(true);
    setUploadMsg(null);
    const fd = new FormData();
    fd.append("file", uploadFile);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/projects/${projectId}/documents`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: fd,
        }
      );
      if (!res.ok) throw new Error();
      setUploadMsg({ text: "Document envoyé — extraction en cours (traitement asynchrone).", ok: true });
      setUploadFile(null);
    } catch {
      setUploadMsg({ text: "Échec de l'envoi. Veuillez réessayer.", ok: false });
    } finally {
      setUploading(false);
    }
  }

  if (loading) return <Spinner />;

  const proposed = facts.filter((f) => f.state === "proposed");
  const validated = facts.filter((f) => f.state === "validated");

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      {/* Topbar */}
      <header style={topbarStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button onClick={() => router.push("/projects")} style={backBtn}>← Projets</button>
          <span style={{ color: "var(--border)" }}>|</span>
          <span style={logoChip}>JAD2</span>
          <span style={{ fontWeight: 700, color: "var(--navy)", fontSize: "1rem" }}>{project?.name}</span>
        </div>
        <span style={{ fontSize: "0.8rem", color: "var(--muted)", fontWeight: 600 }}>
          Année {project?.reporting_year} · {project?.status}
        </span>
      </header>

      {/* Stats bar */}
      <div style={statsBar}>
        <StatChip label="Proposés" value={proposed.length} color="var(--amber)" />
        <StatChip label="Validés" value={validated.length} color="var(--green)" />
        <StatChip label="Snapshots" value={snapshots.length} color="var(--accent)" />
        {anomalies.length > 0 && <StatChip label="Anomalies" value={anomalies.length} color="var(--red)" />}
      </div>

      <div style={pageWrap}>
        {/* Tabs */}
        <div style={tabBarStyle}>
          {(["facts", "compute", "results"] as Tab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)} style={{ ...tabBtnBase, ...(tab === t ? tabBtnActive : {}) }}>
              {t === "facts" ? "Faits d'activité" : t === "compute" ? "Calcul" : "Résultats"}
              {t === "facts" && facts.length > 0 && (
                <span style={tabBadge}>{facts.length}</span>
              )}
              {t === "results" && snapshots.length > 0 && (
                <span style={tabBadge}>{snapshots.length}</span>
              )}
            </button>
          ))}
        </div>

        {/* ── FACTS TAB ── */}
        {tab === "facts" && (
          <div>
            {/* Upload */}
            <div style={{ ...sectionCard, marginBottom: "1.5rem" }}>
              <h3 style={sectionTitle}>Importer un document</h3>
              <form onSubmit={handleUpload} style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
                <input
                  type="file"
                  onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  accept=".pdf,.xlsx,.csv,.docx"
                  style={{ flex: 1, minWidth: 200, fontSize: "0.875rem" }}
                />
                <button type="submit" disabled={!uploadFile || uploading} style={primaryBtn}>
                  {uploading ? "Envoi..." : "Envoyer"}
                </button>
              </form>
              {uploadMsg && (
                <div style={{ marginTop: "0.6rem", padding: "0.55rem 0.8rem", borderRadius: "0.375rem", fontSize: "0.85rem", background: uploadMsg.ok ? "#f0fdf4" : "#fef2f2", color: uploadMsg.ok ? "var(--green)" : "var(--red)", border: `1px solid ${uploadMsg.ok ? "#86efac" : "#fca5a5"}` }}>
                  {uploadMsg.text}
                </div>
              )}
            </div>

            {/* Proposed facts — validation gate (§0.3/§0.4 — human-only trust boundary) */}
            {proposed.length > 0 && (
              <div style={{ marginBottom: "1.5rem" }}>
                <div style={{ ...sectionCard, borderLeft: "4px solid var(--amber)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
                    <h3 style={{ ...sectionTitle, margin: 0, color: "var(--amber)" }}>
                      Faits proposés — validation requise
                    </h3>
                    <span style={{ fontSize: "0.75rem", background: "#fef3c7", color: "#92400e", padding: "0.2rem 0.6rem", borderRadius: "9999px", fontWeight: 700 }}>
                      {proposed.length} en attente
                    </span>
                  </div>
                  <p style={{ fontSize: "0.82rem", color: "var(--muted)", marginBottom: "1rem" }}>
                    Seul un consultant habilité peut valider ces faits. Chaque validation est irréversible et engage votre responsabilité professionnelle.
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                    {proposed.map((f) => (
                      <FactRow
                        key={f.id}
                        fact={f}
                        onValidate={() => handleValidate(f.id)}
                        validating={validating[f.id]}
                        error={validateErrors[f.id]}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Validated facts */}
            {validated.length > 0 && (
              <div style={sectionCard}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                  <h3 style={{ ...sectionTitle, margin: 0, color: "var(--green)" }}>Faits validés</h3>
                  <span style={{ fontSize: "0.75rem", background: "#f0fdf4", color: "#166534", padding: "0.2rem 0.6rem", borderRadius: "9999px", fontWeight: 700 }}>
                    {validated.length} validé{validated.length > 1 ? "s" : ""}
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                  {validated.map((f) => <FactRow key={f.id} fact={f} />)}
                </div>
              </div>
            )}

            {facts.length === 0 && (
              <div style={{ textAlign: "center", padding: "3rem", color: "var(--muted)" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.75rem" }}>📄</div>
                <p>Aucun fait d&apos;activité. Importez un document pour commencer l&apos;extraction.</p>
              </div>
            )}
          </div>
        )}

        {/* ── COMPUTE TAB ── */}
        {tab === "compute" && (
          <div>
            {proposed.length > 0 && (
              <div style={{ background: "#fefce8", border: "1px solid #fde68a", borderRadius: "0.5rem", padding: "0.9rem 1.1rem", marginBottom: "1.5rem", display: "flex", gap: "0.6rem", alignItems: "flex-start" }}>
                <span>⚠️</span>
                <div style={{ fontSize: "0.875rem", color: "#92400e" }}>
                  <strong>{proposed.length} fait(s)</strong> encore en état proposé. Validez-les dans l&apos;onglet &quot;Faits d&apos;activité&quot; avant de lancer le calcul.
                </div>
              </div>
            )}

            <div style={sectionCard}>
              <h3 style={sectionTitle}>Paramètres de calcul</h3>
              <form onSubmit={handleCompute} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label style={labelStyle}>Région</label>
                  <input value={computeForm.region} onChange={(e) => setComputeForm({ ...computeForm, region: e.target.value })} style={inputStyle} placeholder="MA" />
                </div>
                <div>
                  <label style={labelStyle}>Année de reporting</label>
                  <input type="number" value={computeForm.reporting_year} onChange={(e) => setComputeForm({ ...computeForm, reporting_year: parseInt(e.target.value) })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Base GWP</label>
                  <select value={computeForm.gwp_basis} onChange={(e) => setComputeForm({ ...computeForm, gwp_basis: e.target.value })} style={inputStyle}>
                    <option value="AR6">AR6 (recommandé)</option>
                    <option value="AR5">AR5</option>
                    <option value="AR4">AR4</option>
                  </select>
                </div>
                <div style={{ display: "flex", alignItems: "flex-end" }}>
                  <button type="button" onClick={handleReconcile} style={{ ...ghostBtn, width: "100%" }}>
                    Vérifier réconciliation
                  </button>
                </div>
                {computeError && (
                  <div style={{ gridColumn: "1 / -1", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: "0.375rem", padding: "0.65rem 0.85rem", color: "var(--red)", fontSize: "0.85rem" }}>
                    {computeError}
                  </div>
                )}
                <div style={{ gridColumn: "1 / -1" }}>
                  <button type="submit" disabled={computing || proposed.length > 0} style={{ ...primaryBtn, opacity: proposed.length > 0 ? 0.5 : 1, width: "100%", padding: "0.8rem" }}>
                    {computing ? "Calcul en cours..." : "Lancer le calcul d'émissions"}
                  </button>
                </div>
              </form>
            </div>

            {anomalies.length > 0 && (
              <div style={{ ...sectionCard, marginTop: "1.5rem" }}>
                <h3 style={sectionTitle}>Anomalies détectées</h3>
                {anomalies.map((a) => (
                  <div key={a.id} style={{
                    display: "flex", gap: "0.75rem", alignItems: "flex-start",
                    padding: "0.75rem", borderRadius: "0.375rem", marginBottom: "0.5rem",
                    background: a.severity === "warning" ? "#fefce8" : "#f0fdf4",
                    border: `1px solid ${a.severity === "warning" ? "#fde68a" : "#86efac"}`,
                    fontSize: "0.875rem",
                  }}>
                    <span>{a.severity === "warning" ? "⚠️" : "ℹ️"}</span>
                    <div>
                      <strong style={{ textTransform: "capitalize" }}>{a.anomaly_type.replace(/_/g, " ")}</strong>
                      <div style={{ color: "var(--muted)", marginTop: "0.15rem" }}>{a.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── RESULTS TAB ── */}
        {tab === "results" && (
          <div>
            {/* Google export opt-in — §0.11: default OFF */}
            <div style={{ ...sectionCard, marginBottom: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: "0.875rem", color: "var(--navy)" }}>Export Google Docs</div>
                <div style={{ fontSize: "0.78rem", color: "var(--muted)", marginTop: "0.2rem" }}>
                  Désactivé par défaut (§0.11). Seul le rapport agrégé est envoyé — aucune donnée brute.
                </div>
              </div>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <div
                  onClick={() => setGoogleExportEnabled((v) => !v)}
                  style={{
                    width: 42, height: 24, borderRadius: 12,
                    background: googleExportEnabled ? "var(--navy)" : "var(--border)",
                    position: "relative", cursor: "pointer", transition: "background 0.2s",
                  }}
                >
                  <div style={{
                    position: "absolute", top: 3, left: googleExportEnabled ? 21 : 3,
                    width: 18, height: 18, borderRadius: "50%", background: "#fff",
                    transition: "left 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                  }} />
                </div>
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text)" }}>
                  {googleExportEnabled ? "Activé" : "Désactivé"}
                </span>
              </label>
            </div>

            {snapshots.length === 0 ? (
              <div style={{ textAlign: "center", padding: "3rem", color: "var(--muted)" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.75rem" }}>📈</div>
                <p>Aucun snapshot. Lancez un calcul depuis l&apos;onglet &quot;Calcul&quot;.</p>
              </div>
            ) : (
              snapshots.map((snap) => (
                <SnapshotCard
                  key={snap.id}
                  snap={snap}
                  googleExportEnabled={googleExportEnabled}
                  exporting={exporting[snap.id] ?? false}
                  exportUrl={exportUrls[snap.id]}
                  onDownload={() => handleDownloadReport(snap.id)}
                  onGoogleExport={() => handleGoogleExport(snap.id)}
                />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function FactRow({
  fact,
  onValidate,
  validating,
  error,
}: {
  fact: ActivityFact;
  onValidate?: () => void;
  validating?: boolean;
  error?: string;
}) {
  const isProposed = fact.state === "proposed";
  return (
    <div style={{
      background: isProposed ? "#fffbeb" : "#f9fafb",
      border: `1px solid ${isProposed ? "#fde68a" : "var(--border)"}`,
      borderRadius: "0.4rem",
      padding: "0.85rem 1rem",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--navy)" }}>
            {fact.description || fact.category}
          </div>
          <div style={{ color: "var(--muted)", fontSize: "0.78rem", marginTop: "0.2rem" }}>
            {fact.category}
            {fact.sub_category ? ` › ${fact.sub_category}` : ""}
            {" · "}Scope {fact.scope}
            {fact.scope2_type ? ` (${fact.scope2_type})` : ""}
            {" · "}{fact.activity_value} {fact.activity_unit}
            {" · "}{fact.period_start} — {fact.period_end}
          </div>
        </div>
        {onValidate && isProposed && (
          <button
            onClick={onValidate}
            disabled={validating}
            style={{
              background: "var(--amber)", color: "#fff", border: "none",
              borderRadius: "0.35rem", padding: "0.45rem 0.85rem",
              fontWeight: 700, fontSize: "0.8rem", cursor: "pointer",
              whiteSpace: "nowrap", opacity: validating ? 0.6 : 1,
            }}
          >
            {validating ? "..." : "Valider"}
          </button>
        )}
        {!isProposed && (
          <span style={{ fontSize: "0.75rem", background: "#f0fdf4", color: "#166534", padding: "0.2rem 0.55rem", borderRadius: "9999px", fontWeight: 700, whiteSpace: "nowrap" }}>
            ✓ validé
          </span>
        )}
      </div>
      {error && <div style={{ fontSize: "0.78rem", color: "var(--red)", marginTop: "0.4rem" }}>{error}</div>}
    </div>
  );
}

function SnapshotCard({
  snap,
  googleExportEnabled,
  exporting,
  exportUrl,
  onDownload,
  onGoogleExport,
}: {
  snap: ReportSnapshot;
  googleExportEnabled: boolean;
  exporting: boolean;
  exportUrl?: string;
  onDownload: () => void;
  onGoogleExport: () => void;
}) {
  const totals = snap.totals_co2e ?? {};
  const totalVal = totals["total"] ?? Object.values(totals).filter((_, i) => Object.keys(totals)[i] !== "total").reduce((a, b) => a + b, 0);
  const scopeEntries = Object.entries(totals).filter(([k]) => k !== "total");

  return (
    <div style={{ ...sectionCard, marginBottom: "1.25rem" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.75rem" }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: "1.05rem", color: "var(--navy)" }}>
            Snapshot {snap.reporting_year}
          </div>
          <div style={{ fontSize: "0.78rem", color: "var(--muted)", marginTop: "0.2rem" }}>
            {new Date(snap.created_at).toLocaleString("fr-FR")} · {snap.gwp_basis} · hash: <code style={{ fontSize: "0.75rem" }}>{snap.state_hash.slice(0, 16)}…</code>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button onClick={onDownload} style={primaryBtn}>⬇ Télécharger DOCX</button>
          {googleExportEnabled && (
            <button onClick={onGoogleExport} disabled={exporting} style={ghostBtn}>
              {exporting ? "Export..." : "Google Docs →"}
            </button>
          )}
        </div>
      </div>

      {exportUrl && (
        <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "0.375rem", padding: "0.6rem 0.85rem", fontSize: "0.85rem", marginBottom: "1rem" }}>
          Document Google : <a href={exportUrl} target="_blank" rel="noopener noreferrer">{exportUrl}</a>
        </div>
      )}

      {/* KPI cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
        <KpiCard label="Total CO₂e" value={`${Number(totalVal).toFixed(2)} t`} accent="var(--navy)" />
        {snap.scope2_location_t && (
          <KpiCard label="Scope 2 location" value={`${Number(snap.scope2_location_t).toFixed(2)} t`} accent="var(--accent)" />
        )}
        {snap.scope2_market_t && (
          <KpiCard label="Scope 2 marché" value={`${Number(snap.scope2_market_t).toFixed(2)} t`} accent="var(--accent)" />
        )}
      </div>

      {/* Scope breakdown */}
      {scopeEntries.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", marginBottom: "0.5rem" }}>
            Répartition par scope
          </div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {scopeEntries.map(([scope, val]) => {
              const pct = totalVal > 0 ? ((val / totalVal) * 100).toFixed(1) : "0";
              return (
                <div key={scope} style={{ background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "0.375rem", padding: "0.4rem 0.75rem", fontSize: "0.85rem" }}>
                  <strong>{scope}</strong>: {Number(val).toFixed(2)} t <span style={{ color: "var(--muted)" }}>({pct}%)</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Uncertainty (separate from totals — §0.2) */}
      {snap.uncertainty && Object.keys(snap.uncertainty).length > 0 && (
        <div style={{ fontSize: "0.78rem", color: "var(--muted)", padding: "0.5rem", background: "var(--bg)", borderRadius: "0.3rem" }}>
          Incertitude (hors totaux, §0.2) : {JSON.stringify(snap.uncertainty)}
        </div>
      )}

      {/* Reconciliation flags */}
      {snap.reconciliation && (snap.reconciliation as { flags?: unknown[] }).flags?.length ? (
        <div style={{ marginTop: "0.75rem", background: "#fefce8", border: "1px solid #fde68a", borderRadius: "0.375rem", padding: "0.6rem 0.85rem", fontSize: "0.8rem", color: "#92400e" }}>
          ⚠ Réconciliation : {JSON.stringify(snap.reconciliation)}
        </div>
      ) : null}

      {/* AI Transparency disclosure — §0.12 */}
      <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border)", paddingTop: "0.75rem", fontSize: "0.72rem", color: "var(--muted-light)" }}>
        Ce rapport a été produit avec l&apos;assistance de l&apos;IA (Adrar AI). Les facteurs d&apos;émission requièrent une validation experte. Adrar AI accélère le reporting expert — aucune garantie de conformité réglementaire automatique.
      </div>
    </div>
  );
}

function KpiCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{ background: "var(--bg)", border: `1.5px solid ${accent}22`, borderRadius: "0.5rem", padding: "0.85rem 1rem", borderLeft: `3px solid ${accent}` }}>
      <div style={{ fontSize: "1.25rem", fontWeight: 800, color: accent }}>{value}</div>
      <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "0.15rem" }}>{label}</div>
    </div>
  );
}

function StatChip({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <span style={{ fontWeight: 800, fontSize: "1.1rem", color }}>{value}</span>
      <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>{label}</span>
    </div>
  );
}

function Spinner() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <div style={{ width: 36, height: 36, border: "3px solid var(--border)", borderTopColor: "var(--navy)", borderRadius: "50%" }} />
    </div>
  );
}

const topbarStyle: React.CSSProperties = {
  background: "#fff",
  borderBottom: "1px solid var(--border)",
  padding: "0 1.5rem",
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

const statsBar: React.CSSProperties = {
  background: "#fff",
  borderBottom: "1px solid var(--border)",
  padding: "0 2rem",
  height: "44px",
  display: "flex",
  alignItems: "center",
  gap: "2rem",
};

const pageWrap: React.CSSProperties = { maxWidth: "900px", margin: "0 auto", padding: "2rem 1.5rem" };

const tabBarStyle: React.CSSProperties = {
  display: "flex",
  borderBottom: "2px solid var(--border)",
  marginBottom: "1.75rem",
  gap: 0,
};

const tabBtnBase: React.CSSProperties = {
  background: "none",
  border: "none",
  borderBottom: "2px solid transparent",
  marginBottom: "-2px",
  padding: "0.65rem 1.25rem",
  fontWeight: 600,
  fontSize: "0.9rem",
  cursor: "pointer",
  color: "var(--muted)",
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
};

const tabBtnActive: React.CSSProperties = {
  borderBottomColor: "var(--navy)",
  color: "var(--navy)",
};

const tabBadge: React.CSSProperties = {
  background: "var(--navy)",
  color: "#fff",
  borderRadius: "9999px",
  fontSize: "0.7rem",
  fontWeight: 700,
  padding: "0.1rem 0.45rem",
};

const sectionCard: React.CSSProperties = {
  background: "#fff",
  border: "1px solid var(--border)",
  borderRadius: "0.6rem",
  padding: "1.5rem",
};

const sectionTitle: React.CSSProperties = {
  fontSize: "0.875rem",
  fontWeight: 700,
  color: "var(--navy)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: "1rem",
};

const primaryBtn: React.CSSProperties = {
  background: "var(--navy)",
  color: "#fff",
  border: "none",
  borderRadius: "0.4rem",
  padding: "0.55rem 1rem",
  fontWeight: 700,
  fontSize: "0.85rem",
  cursor: "pointer",
  letterSpacing: "0.01em",
  whiteSpace: "nowrap",
};

const ghostBtn: React.CSSProperties = {
  background: "none",
  color: "var(--muted)",
  border: "1px solid var(--border)",
  borderRadius: "0.4rem",
  padding: "0.5rem 0.9rem",
  fontWeight: 600,
  fontSize: "0.85rem",
  cursor: "pointer",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.72rem",
  fontWeight: 700,
  color: "var(--text)",
  letterSpacing: "0.05em",
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

const backBtn: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--muted)",
  cursor: "pointer",
  fontSize: "0.85rem",
  fontWeight: 600,
  padding: 0,
};
