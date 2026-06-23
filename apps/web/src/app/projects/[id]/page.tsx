"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { apiJson, apiFetch } from "@/lib/api";
import type { ActivityFact, Document, Project, ReportSnapshot, Anomaly } from "@/lib/types";

type Tab = "facts" | "compute" | "results" | "rse";
type Lang = "fr" | "en" | "ar";

const T = {
  fr: {
    back: "← Projets",
    proposed_count: (n: number) => `${n} proposé${n > 1 ? "s" : ""}`,
    validated_count: (n: number) => `${n} validé${n > 1 ? "s" : ""}`,
    snapshots: "Snapshots",
    anomalies_lbl: "Anomalies",
    tab_facts: "Faits d'activité",
    tab_compute: "Calcul",
    tab_results: "Résultats",
    upload_title: "Importer un document",
    upload_btn: "Envoyer",
    uploading: "Envoi...",
    upload_type_err: "Type non supporté. Utilisez PDF, XLSX, CSV ou DOCX.",
    upload_size_err: "Fichier trop volumineux (max 50 Mo).",
    upload_ok: "Document envoyé — extraction en cours.",
    upload_fail: "Échec de l'envoi. Veuillez réessayer.",
    docs_title: "Documents importés",
    doc_pending: "En attente",
    doc_processing: "Extraction...",
    doc_done: "✓ Extrait",
    doc_error: "⚠ Erreur",
    proposed_title: "Faits proposés — validation requise",
    pending: (n: number) => `${n} en attente`,
    validate_notice: "Seul un consultant habilité peut valider ces faits. Chaque validation engage votre responsabilité professionnelle.",
    validate_btn: "Valider",
    validated_title: "Faits validés",
    badge_validated: "✓ validé",
    no_facts: "Aucun fait d'activité. Importez un document pour commencer l'extraction.",
    proposed_warning: (n: number) => `${n} fait(s) encore proposés. Validez-les dans l'onglet "Faits" avant de lancer le calcul.`,
    compute_title: "Paramètres de calcul",
    region_lbl: "Région",
    year_lbl: "Année de reporting",
    gwp_lbl: "Base GWP",
    reconcile_btn: "Vérifier réconciliation",
    compute_btn: "Lancer le calcul d'émissions",
    computing: "Calcul en cours...",
    compute_err: (n: number) => `${n} fait(s) encore proposés. Validez-les d'abord.`,
    compute_fail: "Échec du calcul. Vérifiez que tous les faits sont validés.",
    anomalies_title: "Anomalies détectées",
    export_title: "Export Google Docs",
    export_desc: "Désactivé par défaut (§0.11). Seul le rapport agrégé est envoyé — aucune donnée brute.",
    enabled: "Activé",
    disabled: "Désactivé",
    no_snapshots: "Aucun snapshot. Lancez un calcul depuis l'onglet \"Calcul\".",
    download_btn: "⬇ Télécharger DOCX",
    google_btn: "Google Docs →",
    exporting: "Export...",
    snap_label: "Snapshot",
    hash_lbl: "hash",
    scope_title: "Répartition par scope",
    uncertainty_lbl: "Incertitude (hors totaux, §0.2)",
    reconcile_warn: "Réconciliation",
    ai_disclosure: "Ce rapport a été produit avec l'assistance de l'IA (Adrar AI). Les facteurs d'émission requièrent une validation experte. Adrar AI accélère le reporting expert — aucune garantie de conformité réglementaire automatique.",
    scope2_loc: "Scope 2 location",
    scope2_mkt: "Scope 2 marché",
    total: "Total CO₂e",
    validate_fail: "Échec de la validation",
    google_doc: "Document Google",
    tab_rse: "RSE / AMEE",
  },
  ar: {
    back: "→ المشاريع",
    proposed_count: (n: number) => `${n} مقترح`,
    validated_count: (n: number) => `${n} مُتحقق`,
    snapshots: "لقطات",
    anomalies_lbl: "شذوذات",
    tab_facts: "حقائق النشاط",
    tab_compute: "الحساب",
    tab_results: "النتائج",
    upload_title: "استيراد مستند",
    upload_btn: "رفع",
    uploading: "جارٍ الرفع...",
    upload_type_err: "نوع غير مدعوم. استخدم PDF أو XLSX أو CSV أو DOCX.",
    upload_size_err: "الملف كبير جداً (الحد الأقصى 50 ميغابايت).",
    upload_ok: "تم رفع المستند — الاستخراج قيد التنفيذ.",
    upload_fail: "فشل الرفع. يرجى إعادة المحاولة.",
    docs_title: "المستندات المستوردة",
    doc_pending: "في الانتظار",
    doc_processing: "جارٍ الاستخراج...",
    doc_done: "✓ تم الاستخراج",
    doc_error: "⚠ خطأ",
    proposed_title: "حقائق مقترحة — يلزم التحقق",
    pending: (n: number) => `${n} في الانتظار`,
    validate_notice: "فقط المستشار المعتمد يمكنه التحقق من الحقائق. كل تحقق يُلزم مسؤوليتك المهنية.",
    validate_btn: "تحقق",
    validated_title: "حقائق مُتحقق منها",
    badge_validated: "✓ مُتحقق",
    no_facts: "لا توجد حقائق. استورد مستنداً لبدء الاستخراج.",
    proposed_warning: (n: number) => `${n} حقيقة لا تزال مقترحة. تحقق منها في تبويب "الحقائق" قبل الحساب.`,
    compute_title: "معاملات الحساب",
    region_lbl: "المنطقة",
    year_lbl: "سنة الإبلاغ",
    gwp_lbl: "أساس GWP",
    reconcile_btn: "التحقق من التوفيق",
    compute_btn: "تشغيل حساب الانبعاثات",
    computing: "جارٍ الحساب...",
    compute_err: (n: number) => `${n} حقيقة لا تزال مقترحة. تحقق منها أولاً.`,
    compute_fail: "فشل الحساب. تأكد من التحقق من جميع الحقائق.",
    anomalies_title: "الشذوذات المكتشفة",
    export_title: "تصدير Google Docs",
    export_desc: "معطّل افتراضياً (§0.11). يُرسل التقرير الإجمالي فقط — لا بيانات خام.",
    enabled: "مفعّل",
    disabled: "معطّل",
    no_snapshots: "لا توجد لقطات. شغّل حساباً من تبويب \"الحساب\".",
    download_btn: "⬇ تنزيل DOCX",
    google_btn: "Google Docs →",
    exporting: "جارٍ التصدير...",
    snap_label: "لقطة",
    hash_lbl: "hash",
    scope_title: "توزيع النطاق",
    uncertainty_lbl: "عدم اليقين (منفصل عن الإجماليات، §0.2)",
    reconcile_warn: "توفيق",
    ai_disclosure: "أُنتج هذا التقرير بمساعدة الذكاء الاصطناعي (Adrar AI). تتطلب عوامل الانبعاث التحقق من قبل خبير. Adrar AI يُسرّع التقارير الخبيرة — لا ضمان امتثال تنظيمي تلقائي.",
    scope2_loc: "النطاق 2 (الموقع)",
    scope2_mkt: "النطاق 2 (السوق)",
    total: "إجمالي CO₂e",
    validate_fail: "فشل التحقق",
    google_doc: "مستند Google",
    tab_rse: "RSE / AMEE",
  },
  en: {
    back: "← Projects",
    proposed_count: (n: number) => `${n} proposed`,
    validated_count: (n: number) => `${n} validated`,
    snapshots: "Snapshots",
    anomalies_lbl: "Anomalies",
    tab_facts: "Activity Facts",
    tab_compute: "Compute",
    tab_results: "Results",
    upload_title: "Import Document",
    upload_btn: "Upload",
    uploading: "Uploading...",
    upload_type_err: "Unsupported type. Use PDF, XLSX, CSV or DOCX.",
    upload_size_err: "File too large (max 50 MB).",
    upload_ok: "Document uploaded — extraction queued.",
    upload_fail: "Upload failed. Please retry.",
    docs_title: "Imported Documents",
    doc_pending: "Pending",
    doc_processing: "Extracting...",
    doc_done: "✓ Extracted",
    doc_error: "⚠ Error",
    proposed_title: "Proposed Facts — Validation Required",
    pending: (n: number) => `${n} pending`,
    validate_notice: "Only an authorised consultant may validate facts. Each validation is irreversible and carries professional responsibility.",
    validate_btn: "Validate",
    validated_title: "Validated Facts",
    badge_validated: "✓ validated",
    no_facts: "No activity facts. Import a document to begin extraction.",
    proposed_warning: (n: number) => `${n} fact(s) still proposed. Validate them in the "Facts" tab before computing.`,
    compute_title: "Computation Parameters",
    region_lbl: "Region",
    year_lbl: "Reporting Year",
    gwp_lbl: "GWP Basis",
    reconcile_btn: "Check Reconciliation",
    compute_btn: "Run Emissions Computation",
    computing: "Computing...",
    compute_err: (n: number) => `${n} fact(s) still proposed. Validate them first.`,
    compute_fail: "Computation failed. Ensure all facts are validated.",
    anomalies_title: "Detected Anomalies",
    export_title: "Google Docs Export",
    export_desc: "Off by default (§0.11). Only the aggregate report is sent — no raw data.",
    enabled: "Enabled",
    disabled: "Disabled",
    no_snapshots: "No snapshots. Run a computation from the \"Compute\" tab.",
    download_btn: "⬇ Download DOCX",
    google_btn: "Google Docs →",
    exporting: "Exporting...",
    snap_label: "Snapshot",
    hash_lbl: "hash",
    scope_title: "Scope Breakdown",
    uncertainty_lbl: "Uncertainty (separate from totals, §0.2)",
    reconcile_warn: "Reconciliation",
    ai_disclosure: "This report was produced with AI assistance (Adrar AI). Emission factors require expert validation. Adrar AI accelerates expert reporting — no automatic regulatory compliance guarantee.",
    scope2_loc: "Scope 2 location",
    scope2_mkt: "Scope 2 market",
    total: "Total CO₂e",
    validate_fail: "Validation failed",
    google_doc: "Google Document",
    tab_rse: "RSE / AMEE",
  },
};

export default function ProjectDetailPage() {
  const router = useRouter();
  const { id: projectId } = useParams<{ id: string }>();
  const supabase = createClient();
  const [lang, setLang] = useState<Lang>("fr");
  const t = T[lang];

  const [token, setToken] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [facts, setFacts] = useState<ActivityFact[]>([]);
  const [snapshots, setSnapshots] = useState<ReportSnapshot[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
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
      apiJson<Document[]>(`/projects/${projectId}/documents`, token).catch(() => [] as Document[]),
    ]).then(([proj, f, s, docs]) => {
      setProject(proj);
      setFacts(f);
      setSnapshots(s);
      setDocuments(docs);
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
      setValidateErrors((v) => ({ ...v, [factId]: t.validate_fail }));
    } finally {
      setValidating((v) => ({ ...v, [factId]: false }));
    }
  }

  async function handleCompute(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    const pending = facts.filter((f) => f.state === "proposed");
    if (pending.length > 0) {
      setComputeError(t.compute_err(pending.length));
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
      setComputeError(t.compute_fail);
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
    const allowed = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "text/csv",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];
    if (!allowed.includes(uploadFile.type)) {
      setUploadMsg({ text: t.upload_type_err, ok: false });
      return;
    }
    if (uploadFile.size > 50 * 1024 * 1024) {
      setUploadMsg({ text: t.upload_size_err, ok: false });
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
      setUploadMsg({ text: t.upload_ok, ok: true });
      setUploadFile(null);
      // Refresh document list
      apiJson<Document[]>(`/projects/${projectId}/documents`, token).then(setDocuments).catch(() => {});
    } catch {
      setUploadMsg({ text: t.upload_fail, ok: false });
    } finally {
      setUploading(false);
    }
  }

  if (loading) return <Spinner />;

  const proposed = facts.filter((f) => f.state === "proposed");
  const validated = facts.filter((f) => f.state === "validated");

  const statusColor: Record<string, string> = {
    active: "var(--green)",
    completed: "var(--accent)",
    draft: "var(--muted)",
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      {/* Topbar */}
      <header style={topbarStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button onClick={() => router.push("/projects")} style={backBtn}>{t.back}</button>
          <span style={{ color: "var(--border)" }}>|</span>
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={logoChip}>JAD2</span>
            <span style={{ fontSize: "0.65rem", color: "var(--muted)", letterSpacing: "0.05em", textTransform: "uppercase" }}>Advisory</span>
          </div>
          <span style={{ color: "var(--border)" }}>|</span>
          <span style={{ fontWeight: 700, color: "var(--navy)", fontSize: "0.95rem" }}>{project?.name}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {project && (
            <span style={{
              fontSize: "0.72rem",
              fontWeight: 700,
              padding: "0.2rem 0.6rem",
              borderRadius: "9999px",
              background: `${statusColor[project.status] ?? "var(--muted)"}18`,
              color: statusColor[project.status] ?? "var(--muted)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}>
              {project.status}
            </span>
          )}
          <span style={{ fontSize: "0.8rem", color: "var(--muted)", fontWeight: 600 }}>
            {project?.reporting_year}
          </span>
          {/* Language toggle */}
          <div style={{ display: "flex", gap: "0.2rem" }}>
            {(["fr", "en", "ar"] as Lang[]).map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                style={{
                  background: lang === l ? "var(--navy)" : "none",
                  color: lang === l ? "#fff" : "var(--muted)",
                  border: "1px solid var(--border)",
                  borderRadius: "0.3rem",
                  padding: "0.2rem 0.5rem",
                  fontSize: "0.72rem",
                  fontWeight: 700,
                  cursor: "pointer",
                  letterSpacing: "0.05em",
                }}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Sub-header stats bar */}
      <div style={statsBar}>
        <div style={{ display: "flex", gap: "2rem", alignItems: "center" }}>
          <StatChip label={t.proposed_count(proposed.length)} value={proposed.length} color="var(--amber)" />
          <StatChip label={t.validated_count(validated.length)} value={validated.length} color="var(--green)" />
          <StatChip label={t.snapshots} value={snapshots.length} color="var(--accent)" />
          {anomalies.length > 0 && <StatChip label={t.anomalies_lbl} value={anomalies.length} color="var(--red)" />}
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
          {project?.reporting_frameworks?.map((fw) => (
            <span key={fw} style={{ fontSize: "0.68rem", fontWeight: 700, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", borderRadius: "9999px", padding: "0.15rem 0.5rem" }}>
              {fw.replace(/_/g, " ").toUpperCase()}
            </span>
          ))}
          {project?.sector_code && (
            <span style={{ fontSize: "0.72rem", color: "var(--muted)", fontWeight: 600 }}>
              {project.sector_code}
            </span>
          )}
        </div>
      </div>

      <div style={pageWrap}>
        {/* Tabs */}
        <div style={tabBarStyle}>
          {(["facts", "compute", "results", "rse"] as Tab[]).map((tb) => (
            <button key={tb} onClick={() => setTab(tb)} style={{ ...tabBtnBase, ...(tab === tb ? tabBtnActive : {}) }}>
              {tb === "facts" ? t.tab_facts : tb === "compute" ? t.tab_compute : tb === "results" ? t.tab_results : t.tab_rse}
              {tb === "facts" && facts.length > 0 && (
                <span style={tabBadge}>{facts.length}</span>
              )}
              {tb === "results" && snapshots.length > 0 && (
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
              <h3 style={sectionTitle}>{t.upload_title}</h3>
              <form onSubmit={handleUpload} style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
                <input
                  type="file"
                  onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  accept=".pdf,.xlsx,.csv,.docx"
                  style={{ flex: 1, minWidth: 200, fontSize: "0.875rem" }}
                />
                <button type="submit" disabled={!uploadFile || uploading} style={primaryBtn}>
                  {uploading ? t.uploading : t.upload_btn}
                </button>
              </form>
              {uploadMsg && (
                <div style={{
                  marginTop: "0.6rem", padding: "0.55rem 0.8rem",
                  borderRadius: "0.375rem", fontSize: "0.85rem",
                  background: uploadMsg.ok ? "#f0fdf4" : "#fef2f2",
                  color: uploadMsg.ok ? "var(--green)" : "var(--red)",
                  border: `1px solid ${uploadMsg.ok ? "#86efac" : "#fca5a5"}`,
                }}>
                  {uploadMsg.text}
                </div>
              )}
            </div>

            {/* Manual fact proposition */}
            <ManualFactForm projectId={projectId} token={token!} lang={lang} onAdded={(f) => setFacts((prev) => [f, ...prev])} />

            {/* Document list */}
            {documents.length > 0 && (
              <div style={{ ...sectionCard, marginBottom: "1.5rem" }}>
                <h3 style={sectionTitle}>{t.docs_title}</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                  {documents.map((doc) => {
                    const statusLabel: Record<string, string> = {
                      pending: t.doc_pending,
                      processing: t.doc_processing,
                      done: t.doc_done,
                      error: t.doc_error,
                    };
                    const statusColor: Record<string, string> = {
                      pending: "var(--muted)",
                      processing: "var(--accent)",
                      done: "var(--green)",
                      error: "var(--red)",
                    };
                    const c = statusColor[doc.processing_status] ?? "var(--muted)";
                    return (
                      <div key={doc.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0.75rem", background: "var(--bg)", borderRadius: "0.35rem", fontSize: "0.85rem" }}>
                        <span style={{ color: "var(--text)", fontWeight: 500 }}>{doc.original_filename}</span>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                          {doc.extraction_confidence != null && (
                            <span style={{ fontSize: "0.72rem", color: "var(--muted)" }}>{(doc.extraction_confidence * 100).toFixed(0)}% conf.</span>
                          )}
                          <span style={{ fontSize: "0.72rem", fontWeight: 700, color: c, background: `${c}18`, padding: "0.15rem 0.5rem", borderRadius: "9999px" }}>
                            {statusLabel[doc.processing_status] ?? doc.processing_status}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Proposed facts — validation gate (§0.3/§0.4 — human-only trust boundary) */}
            {proposed.length > 0 && (
              <div style={{ marginBottom: "1.5rem" }}>
                <div style={{ ...sectionCard, borderLeft: "4px solid var(--amber)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
                    <h3 style={{ ...sectionTitle, margin: 0, color: "var(--amber)" }}>
                      {t.proposed_title}
                    </h3>
                    <span style={{ fontSize: "0.75rem", background: "#fef3c7", color: "#92400e", padding: "0.2rem 0.6rem", borderRadius: "9999px", fontWeight: 700 }}>
                      {t.pending(proposed.length)}
                    </span>
                  </div>
                  <p style={{ fontSize: "0.82rem", color: "var(--muted)", marginBottom: "1rem" }}>
                    {t.validate_notice}
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                    {proposed.map((f) => (
                      <FactRow
                        key={f.id}
                        fact={f}
                        onValidate={() => handleValidate(f.id)}
                        validating={validating[f.id]}
                        error={validateErrors[f.id]}
                        validateLabel={t.validate_btn}
                        badgeLabel={t.badge_validated}
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
                  <h3 style={{ ...sectionTitle, margin: 0, color: "var(--green)" }}>{t.validated_title}</h3>
                  <span style={{ fontSize: "0.75rem", background: "#f0fdf4", color: "#166534", padding: "0.2rem 0.6rem", borderRadius: "9999px", fontWeight: 700 }}>
                    {t.validated_count(validated.length)}
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                  {validated.map((f) => (
                    <FactRow key={f.id} fact={f} validateLabel={t.validate_btn} badgeLabel={t.badge_validated} />
                  ))}
                </div>
              </div>
            )}

            {facts.length === 0 && (
              <div style={{ textAlign: "center", padding: "3rem", color: "var(--muted)" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.75rem" }}>📄</div>
                <p>{t.no_facts}</p>
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
                  {t.proposed_warning(proposed.length)}
                </div>
              </div>
            )}

            <div style={sectionCard}>
              <h3 style={sectionTitle}>{t.compute_title}</h3>
              <form onSubmit={handleCompute} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div>
                  <label style={labelStyle}>{t.region_lbl}</label>
                  <input value={computeForm.region} onChange={(e) => setComputeForm({ ...computeForm, region: e.target.value })} style={inputStyle} placeholder="MA" />
                </div>
                <div>
                  <label style={labelStyle}>{t.year_lbl}</label>
                  <input type="number" value={computeForm.reporting_year} onChange={(e) => setComputeForm({ ...computeForm, reporting_year: parseInt(e.target.value) })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>{t.gwp_lbl}</label>
                  <select value={computeForm.gwp_basis} onChange={(e) => setComputeForm({ ...computeForm, gwp_basis: e.target.value })} style={inputStyle}>
                    <option value="AR6">AR6 (recommandé)</option>
                    <option value="AR5">AR5</option>
                    <option value="AR4">AR4</option>
                  </select>
                </div>
                <div style={{ display: "flex", alignItems: "flex-end" }}>
                  <button type="button" onClick={handleReconcile} style={{ ...ghostBtn, width: "100%" }}>
                    {t.reconcile_btn}
                  </button>
                </div>
                {computeError && (
                  <div style={{ gridColumn: "1 / -1", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: "0.375rem", padding: "0.65rem 0.85rem", color: "var(--red)", fontSize: "0.85rem" }}>
                    {computeError}
                  </div>
                )}
                <div style={{ gridColumn: "1 / -1" }}>
                  <button type="submit" disabled={computing || proposed.length > 0} style={{ ...primaryBtn, opacity: proposed.length > 0 ? 0.5 : 1, width: "100%", padding: "0.8rem" }}>
                    {computing ? t.computing : t.compute_btn}
                  </button>
                </div>
              </form>
            </div>

            {anomalies.length > 0 && (
              <div style={{ ...sectionCard, marginTop: "1.5rem" }}>
                <h3 style={sectionTitle}>{t.anomalies_title}</h3>
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
                <div style={{ fontWeight: 700, fontSize: "0.875rem", color: "var(--navy)" }}>{t.export_title}</div>
                <div style={{ fontSize: "0.78rem", color: "var(--muted)", marginTop: "0.2rem" }}>{t.export_desc}</div>
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
                  {googleExportEnabled ? t.enabled : t.disabled}
                </span>
              </label>
            </div>

            {snapshots.length === 0 ? (
              <div style={{ textAlign: "center", padding: "3rem", color: "var(--muted)" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.75rem" }}>📈</div>
                <p>{t.no_snapshots}</p>
              </div>
            ) : (
              snapshots.map((snap) => (
                <SnapshotCard
                  key={snap.id}
                  snap={snap}
                  t={t}
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
        {/* ── RSE / AMEE TAB ── */}
        {tab === "rse" && (
          <RseAmeeTab projectId={projectId} token={token!} lang={lang} project={project} snapshots={snapshots} />
        )}
      </div>
    </div>
  );
}

function RseAmeeTab({ projectId, token, lang, project, snapshots }: {
  projectId: string;
  token: string;
  lang: Lang;
  project: Project | null;
  snapshots: ReportSnapshot[];
}) {
  const lastSnap = snapshots[0];
  const totals = lastSnap?.totals_co2e ?? {};
  const gri = lastSnap?.gri_305_data;

  const lbl = {
    fr: { title: "Reporting RSE & Bilan Énergétique AMEE", bvc: "Statut BVC", amee: "Déclaration AMEE (Loi 47-09)", gri305: "Divulgations GRI 305", ndc: "NDC Maroc 2030", frameworks: "Référentiels actifs", noSnap: "Lancez un calcul pour voir les données RSE.", scope1: "Scope 1", scope2: "Scope 2 (loc.)", scope3: "Scope 3", total: "Total GHG" },
    en: { title: "RSE Reporting & AMEE Energy Audit", bvc: "BVC Status", amee: "AMEE Declaration (Law 47-09)", gri305: "GRI 305 Disclosures", ndc: "Morocco NDC 2030", frameworks: "Active frameworks", noSnap: "Run a computation to see RSE data.", scope1: "Scope 1", scope2: "Scope 2 (loc.)", scope3: "Scope 3", total: "Total GHG" },
    ar: { title: "تقارير RSE وميزانية طاقة AMEE", bvc: "حالة BVC", amee: "إعلان AMEE (قانون 47-09)", gri305: "إفصاحات GRI 305", ndc: "NDC المغرب 2030", frameworks: "الأطر المفعّلة", noSnap: "شغّل حساباً لرؤية بيانات RSE.", scope1: "النطاق 1", scope2: "النطاق 2 (موقع)", scope3: "النطاق 3", total: "إجمالي GHG" },
  }[lang];

  return (
    <div>
      {/* Header */}
      <div style={{ ...sectionCard, marginBottom: "1.5rem", borderLeft: "4px solid #0ea5e9" }}>
        <h3 style={{ ...sectionTitle, color: "#0369a1", margin: 0 }}>{lbl.title}</h3>
      </div>

      {/* BVC + AMEE status */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ ...sectionCard, borderTop: "3px solid #1d4ed8" }}>
          <div style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", marginBottom: "0.5rem" }}>{lbl.bvc}</div>
          {project?.reporting_frameworks?.includes("gri_305") ? (
            <div>
              <span style={{ fontSize: "0.8rem", fontWeight: 700, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", borderRadius: "9999px", padding: "0.2rem 0.6rem" }}>
                GRI 305 actif
              </span>
              <p style={{ fontSize: "0.78rem", color: "var(--muted)", marginTop: "0.5rem", lineHeight: 1.5 }}>
                {lang === "fr" ? "Ce projet est configuré pour la divulgation GRI 305. Les données sont automatiquement calculées lors de chaque snapshot." : lang === "ar" ? "هذا المشروع مهيأ لإفصاح GRI 305. يتم حساب البيانات تلقائياً." : "This project is configured for GRI 305 disclosure. Data is auto-computed on each snapshot."}
              </p>
            </div>
          ) : (
            <p style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
              {lang === "fr" ? "Ajoutez GRI 305 aux référentiels du projet pour activer la divulgation automatique (Rapport RSE BVC)." : lang === "ar" ? "أضف GRI 305 للأطر لتفعيل الإفصاح التلقائي." : "Add GRI 305 to project frameworks to enable automatic disclosure (BVC RSE Report)."}
            </p>
          )}
        </div>
        <div style={{ ...sectionCard, borderTop: "3px solid #16a34a" }}>
          <div style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", marginBottom: "0.5rem" }}>{lbl.amee}</div>
          {project?.reporting_frameworks?.includes("amee") ? (
            <div>
              <span style={{ fontSize: "0.8rem", fontWeight: 700, background: "#f0fdf4", color: "#166534", border: "1px solid #86efac", borderRadius: "9999px", padding: "0.2rem 0.6rem" }}>
                AMEE actif
              </span>
              <p style={{ fontSize: "0.78rem", color: "var(--muted)", marginTop: "0.5rem", lineHeight: 1.5 }}>
                {lang === "fr" ? "Bilan Énergétique AMEE (Loi 47-09). Seuil de déclaration obligatoire : 500 TEP/an." : lang === "ar" ? "ميزانية طاقة AMEE (قانون 47-09). حد الإفصاح الإلزامي: 500 TEP/سنة." : "AMEE Energy Audit (Law 47-09). Mandatory reporting threshold: 500 TEP/year."}
              </p>
            </div>
          ) : (
            <p style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
              {lang === "fr" ? "Ajoutez le référentiel AMEE au projet pour les grandes entreprises consommatrices d'énergie (Loi 47-09)." : lang === "ar" ? "أضف AMEE للمشاريع ذات الاستهلاك العالي للطاقة (قانون 47-09)." : "Add AMEE framework for large energy consumers (Law 47-09)."}
            </p>
          )}
        </div>
      </div>

      {/* Active frameworks */}
      {project?.reporting_frameworks && project.reporting_frameworks.length > 0 && (
        <div style={{ ...sectionCard, marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", marginBottom: "0.75rem" }}>{lbl.frameworks}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {project.reporting_frameworks.map((fw) => (
              <span key={fw} style={{ fontSize: "0.8rem", fontWeight: 700, background: "var(--navy)", color: "#fff", borderRadius: "9999px", padding: "0.25rem 0.75rem" }}>
                {fw.replace(/_/g, " ").toUpperCase()}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* GRI 305 summary from last snapshot */}
      {!lastSnap ? (
        <div style={{ textAlign: "center", padding: "3rem", color: "var(--muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📋</div>
          <p>{lbl.noSnap}</p>
        </div>
      ) : (
        <div>
          {/* GHG summary */}
          <div style={{ ...sectionCard, marginBottom: "1.5rem" }}>
            <div style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", marginBottom: "0.75rem" }}>
              {lbl.gri305} — {lastSnap.reporting_year}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "0.75rem" }}>
              {[
                { label: lbl.scope1, value: gri?.["305-1"] ?? totals["scope1"] ?? 0, color: "#dc2626" },
                { label: lbl.scope2, value: gri?.["305-2-loc"] ?? totals["scope2_location"] ?? 0, color: "#f97316" },
                { label: lbl.scope3, value: gri?.["305-3"] ?? totals["scope3"] ?? 0, color: "#eab308" },
                { label: lbl.total, value: gri?.["305-total-loc"] ?? totals["total"] ?? 0, color: "var(--navy)" },
              ].map((item) => (
                <div key={item.label} style={{ background: "var(--bg)", border: `1.5px solid ${item.color}22`, borderLeft: `3px solid ${item.color}`, borderRadius: "0.5rem", padding: "0.85rem 1rem" }}>
                  <div style={{ fontSize: "1.2rem", fontWeight: 800, color: item.color }}>{Number(item.value).toFixed(2)}</div>
                  <div style={{ fontSize: "0.72rem", color: "var(--muted)", marginTop: "0.1rem" }}>{item.label} tCO₂e</div>
                </div>
              ))}
            </div>
          </div>

          {/* NDC alignment */}
          {lastSnap.ndc_alignment && (lastSnap.ndc_alignment as { progress_pct?: number }).progress_pct != null && (
            <div style={{ ...sectionCard, background: "#f0fdf4", border: "1px solid #86efac" }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "#166534", marginBottom: "0.75rem" }}>
                {lbl.ndc}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "2rem", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "2rem", fontWeight: 900, color: "#166534" }}>
                    {(lastSnap.ndc_alignment as { progress_pct: number }).progress_pct.toFixed(1)}%
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#16a34a" }}>
                    {lang === "fr" ? "vers objectif −45.5%" : lang === "ar" ? "نحو هدف −45.5%" : "toward −45.5% target"}
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div style={{ height: 10, background: "#dcfce7", borderRadius: 5, overflow: "hidden", marginBottom: "0.4rem" }}>
                    <div style={{ height: "100%", width: `${Math.min(100, (lastSnap.ndc_alignment as { progress_pct: number }).progress_pct)}%`, background: "#16a34a", borderRadius: 5 }} />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", color: "#166534" }}>
                    <span>0%</span>
                    <span>45.5% (NDC 2030)</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FactRow({
  fact,
  onValidate,
  validating,
  error,
  validateLabel,
  badgeLabel,
}: {
  fact: ActivityFact;
  onValidate?: () => void;
  validating?: boolean;
  error?: string;
  validateLabel: string;
  badgeLabel: string;
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
            {validating ? "…" : validateLabel}
          </button>
        )}
        {!isProposed && (
          <span style={{ fontSize: "0.75rem", background: "#f0fdf4", color: "#166534", padding: "0.2rem 0.55rem", borderRadius: "9999px", fontWeight: 700, whiteSpace: "nowrap" }}>
            {badgeLabel}
          </span>
        )}
      </div>
      {error && <div style={{ fontSize: "0.78rem", color: "var(--red)", marginTop: "0.4rem" }}>{error}</div>}
    </div>
  );
}

type TKeys = typeof T["fr"];

function SnapshotCard({
  snap,
  t,
  googleExportEnabled,
  exporting,
  exportUrl,
  onDownload,
  onGoogleExport,
}: {
  snap: ReportSnapshot;
  t: TKeys;
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
            {t.snap_label} {snap.reporting_year}
          </div>
          <div style={{ fontSize: "0.78rem", color: "var(--muted)", marginTop: "0.2rem" }}>
            {new Date(snap.created_at).toLocaleString()} · {snap.gwp_basis} · {t.hash_lbl}: <code style={{ fontSize: "0.75rem" }}>{snap.state_hash.slice(0, 16)}…</code>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button onClick={onDownload} style={primaryBtn}>{t.download_btn}</button>
          {googleExportEnabled && (
            <button onClick={onGoogleExport} disabled={exporting} style={ghostBtn}>
              {exporting ? t.exporting : t.google_btn}
            </button>
          )}
        </div>
      </div>

      {exportUrl && (
        <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "0.375rem", padding: "0.6rem 0.85rem", fontSize: "0.85rem", marginBottom: "1rem" }}>
          {t.google_doc}: <a href={exportUrl} target="_blank" rel="noopener noreferrer">{exportUrl}</a>
        </div>
      )}

      {/* KPI cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
        <KpiCard label={t.total} value={`${Number(totalVal).toFixed(2)} t`} accent="var(--navy)" />
        {snap.scope2_location_t && (
          <KpiCard label={t.scope2_loc} value={`${Number(snap.scope2_location_t).toFixed(2)} t`} accent="var(--accent)" />
        )}
        {snap.scope2_market_t && (
          <KpiCard label={t.scope2_mkt} value={`${Number(snap.scope2_market_t).toFixed(2)} t`} accent="var(--accent)" />
        )}
      </div>

      {/* Scope breakdown */}
      {scopeEntries.length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", marginBottom: "0.5rem" }}>
            {t.scope_title}
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

      {/* GRI 305 disclosure breakdown */}
      {snap.gri_305_data && Object.keys(snap.gri_305_data).length > 0 && (
        <div style={{ marginBottom: "0.75rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)", marginBottom: "0.5rem" }}>
            GRI 305 — Émissions
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.5rem" }}>
            {(["305-1", "305-2-loc", "305-2-mkt", "305-3"] as const).map((k) => {
              const val = (snap.gri_305_data as Record<string, number>)[k];
              if (val == null) return null;
              const labels: Record<string, string> = { "305-1": "GRI 305-1 Scope 1", "305-2-loc": "GRI 305-2 Loc.", "305-2-mkt": "GRI 305-2 Mkt.", "305-3": "GRI 305-3 Scope 3" };
              return (
                <div key={k} style={{ background: "#f0f9ff", border: "1px solid #bae6fd", borderRadius: "0.4rem", padding: "0.5rem 0.75rem" }}>
                  <div style={{ fontSize: "0.7rem", color: "#0369a1", fontWeight: 700 }}>{labels[k]}</div>
                  <div style={{ fontSize: "1rem", fontWeight: 800, color: "#0c4a6e" }}>{Number(val).toFixed(2)} t</div>
                </div>
              );
            })}
          </div>
          {/* GRI 305-4: Intensity */}
          {(snap.intensity_metrics as Record<string, number> | null) && (
            <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {Object.entries(snap.intensity_metrics as Record<string, number>).map(([k, v]) => (
                <span key={k} style={{ fontSize: "0.78rem", background: "#f1f5f9", border: "1px solid var(--border)", borderRadius: "0.35rem", padding: "0.25rem 0.6rem", color: "var(--text)" }}>
                  <strong>GRI 305-4</strong> {k}: {Number(v).toFixed(3)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* NDC Morocco alignment */}
      {snap.ndc_alignment && (snap.ndc_alignment as { progress_pct?: number; baseline_emissions?: number; target_emissions?: number }).progress_pct != null && (
        <div style={{ marginBottom: "0.75rem", background: "#f0fdf4", border: "1px solid #86efac", borderRadius: "0.5rem", padding: "0.85rem 1rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "#166534", marginBottom: "0.5rem" }}>
            NDC Maroc 2030 — Objectif −45.5% vs BAU
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: "1.5rem", fontWeight: 900, color: "#166534" }}>
                {(snap.ndc_alignment as { progress_pct: number }).progress_pct.toFixed(1)}%
              </div>
              <div style={{ fontSize: "0.72rem", color: "#166534" }}>progression</div>
            </div>
            <div style={{ flex: 1, minWidth: 120 }}>
              <div style={{ height: 8, background: "#dcfce7", borderRadius: 4, overflow: "hidden" }}>
                <div style={{
                  height: "100%",
                  width: `${Math.min(100, (snap.ndc_alignment as { progress_pct: number }).progress_pct)}%`,
                  background: "var(--green)",
                  borderRadius: 4,
                  transition: "width 0.5s",
                }} />
              </div>
              {(snap.ndc_alignment as { baseline_emissions?: number; target_emissions?: number }).baseline_emissions && (
                <div style={{ fontSize: "0.7rem", color: "var(--muted)", marginTop: "0.25rem" }}>
                  Baseline: {((snap.ndc_alignment as { baseline_emissions: number }).baseline_emissions / 1000).toFixed(1)} kt · Cible: {((snap.ndc_alignment as { target_emissions: number }).target_emissions / 1000).toFixed(1)} kt
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Uncertainty (separate from totals — §0.2) */}
      {snap.uncertainty && Object.keys(snap.uncertainty).length > 0 && (
        <div style={{ fontSize: "0.78rem", color: "var(--muted)", padding: "0.5rem", background: "var(--bg)", borderRadius: "0.3rem" }}>
          {t.uncertainty_lbl}: {JSON.stringify(snap.uncertainty)}
        </div>
      )}

      {/* Reconciliation flags */}
      {snap.reconciliation && (snap.reconciliation as { flags?: unknown[] }).flags?.length ? (
        <div style={{ marginTop: "0.75rem", background: "#fefce8", border: "1px solid #fde68a", borderRadius: "0.375rem", padding: "0.6rem 0.85rem", fontSize: "0.8rem", color: "#92400e" }}>
          ⚠ {t.reconcile_warn}: {JSON.stringify(snap.reconciliation)}
        </div>
      ) : null}

      {/* AI Transparency disclosure — §0.12 */}
      <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border)", paddingTop: "0.75rem", fontSize: "0.72rem", color: "var(--muted-light)" }}>
        {t.ai_disclosure}
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

// ── Morocco-specific activity categories ──────────────────────────────────

const MOROCCO_CATEGORIES = [
  { key: "energie_butane", scope: 1, label: { fr: "Énergie — Butane (bouteilles)", en: "Energy — Butane (cylinders)", ar: "طاقة — غاز البوتان" }, unit: "kg", hint: "bouteilles_12kg ou bouteilles_3kg" },
  { key: "energie_gasoil", scope: 1, label: { fr: "Énergie — Gasoil", en: "Energy — Diesel", ar: "طاقة — ديزل" }, unit: "litres", hint: "" },
  { key: "energie_fuel", scope: 1, label: { fr: "Énergie — Fuel lourd / domestique", en: "Energy — Heavy/Domestic Fuel", ar: "طاقة — وقود ثقيل" }, unit: "litres", hint: "" },
  { key: "electricite_onee", scope: 2, label: { fr: "Électricité — ONEE réseau (location-based)", en: "Electricity — ONEE grid (location-based)", ar: "كهرباء — ONEE شبكة" }, unit: "kWh", hint: "Scope 2 location-based, FE ONEE 2023" },
  { key: "electricite_onee_mkt", scope: 2, label: { fr: "Électricité — ONEE réseau (market-based)", en: "Electricity — ONEE grid (market-based)", ar: "كهرباء — ONEE شبكة (سوقي)" }, unit: "kWh", hint: "Scope 2 market-based" },
  { key: "electricite_pv_autoconso", scope: 2, label: { fr: "Électricité — PV autoconsommation", en: "Electricity — On-site PV (self-consumption)", ar: "كهرباء — طاقة شمسية محلية" }, unit: "kWh", hint: "FE PV: 0.048 kgCO2e/kWh" },
  { key: "transport_oncf_passager", scope: 3, label: { fr: "Transport — ONCF passager (train)", en: "Transport — ONCF passenger (rail)", ar: "نقل — ONCF ركاب (قطار)" }, unit: "passager.km", hint: "FE: 0.0082 kgCO2e/passager.km" },
  { key: "transport_oncf_fret", scope: 3, label: { fr: "Transport — ONCF fret (train)", en: "Transport — ONCF freight (rail)", ar: "نقل — ONCF شحن (قطار)" }, unit: "tonne.km", hint: "" },
  { key: "transport_grand_taxi", scope: 3, label: { fr: "Transport — Grand taxi", en: "Transport — Grand taxi", ar: "نقل — سيارة أجرة كبيرة" }, unit: "passager.km", hint: "" },
  { key: "transport_ctm_bus", scope: 3, label: { fr: "Transport — CTM / bus longue distance", en: "Transport — CTM / long-distance bus", ar: "نقل — CTM حافلة" }, unit: "passager.km", hint: "" },
  { key: "transport_vol_domestique_ma", scope: 3, label: { fr: "Transport aérien — Vol domestique Maroc", en: "Air — Domestic flight Morocco", ar: "نقل جوي — رحلة داخلية المغرب" }, unit: "passager.km", hint: "RAM, Air Arabia Maroc" },
  { key: "transport_vol_moyen_courrier", scope: 3, label: { fr: "Transport aérien — Vol moyen-courrier", en: "Air — Medium-haul flight", ar: "نقل جوي — رحلة متوسطة" }, unit: "passager.km", hint: "" },
  { key: "transport_maritime", scope: 3, label: { fr: "Transport maritime — Conteneur", en: "Maritime — Container shipping", ar: "نقل بحري — حاوية" }, unit: "tonne.km", hint: "" },
  { key: "dechets_decharge_controlee_biogaz", scope: 3, label: { fr: "Déchets — Décharge contrôlée (avec biogaz)", en: "Waste — Controlled landfill (with biogas)", ar: "نفايات — مطرح مراقب (مع الغاز الحيوي)" }, unit: "kg", hint: "FE: 0.47 kgCO2e/kg" },
  { key: "dechets_decharge_sauvage", scope: 3, label: { fr: "Déchets — Décharge sauvage", en: "Waste — Uncontrolled dump", ar: "نفايات — مطرح عشوائي" }, unit: "kg", hint: "FE: 1.15 kgCO2e/kg — spécifique Maroc" },
  { key: "dechets_incineration", scope: 3, label: { fr: "Déchets — Incinération", en: "Waste — Incineration", ar: "نفايات — حرق" }, unit: "kg", hint: "" },
  { key: "eau_onee", scope: 3, label: { fr: "Eau — ONEE eau potable", en: "Water — ONEE drinking water", ar: "ماء — ONEE مياه صالحة للشرب" }, unit: "m3", hint: "FE: 0.305 kgCO2e/m3" },
  { key: "industrie_ciment_clinker", scope: 1, label: { fr: "Industrie — Clinker (calcination)", en: "Industry — Clinker (calcination)", ar: "صناعة — الكلنكر (حرق الجير)" }, unit: "kg_clinker", hint: "Ciments du Maroc, Lafarge, Holcim" },
  { key: "industrie_phosphate_ocp", scope: 1, label: { fr: "Industrie — Phosphate OCP (calcination)", en: "Industry — OCP Phosphate (calcination)", ar: "صناعة — فوسفات OCP" }, unit: "kg", hint: "Procédé OCP spécifique Maroc" },
  { key: "industrie_acier_sonasid", scope: 1, label: { fr: "Industrie — Acier Sonasid (four électrique)", en: "Industry — Sonasid steel (EAF)", ar: "صناعة — فولاذ Sonasid (فرن كهربائي)" }, unit: "kg", hint: "FE: 0.395 kgCO2e/kg" },
  { key: "frigorigene_r410a", scope: 1, label: { fr: "Frigorigènes — R-410A (fuite)", en: "Refrigerants — R-410A (fugitive)", ar: "مبردات — R-410A (تسرب)" }, unit: "kg", hint: "GWP AR6: 2088 — climatisation inverter" },
  { key: "frigorigene_r22", scope: 1, label: { fr: "Frigorigènes — R-22 (fuite)", en: "Refrigerants — R-22 (fugitive)", ar: "مبردات — R-22 (تسرب)" }, unit: "kg", hint: "GWP AR6: 1760 — encore répandu au Maroc (Protocole Montréal)" },
  { key: "agriculture_bovins", scope: 1, label: { fr: "Agriculture — Bovins (fermentation entérique)", en: "Agriculture — Cattle (enteric fermentation)", ar: "زراعة — أبقار (تخمر هضمي)" }, unit: "animal.jour", hint: "FE Maroc: 1.57 kgCO2e/animal.jour" },
  { key: "agriculture_engrais_n2o", scope: 1, label: { fr: "Agriculture — Engrais azotés (N₂O)", en: "Agriculture — Nitrogen fertilisers (N₂O)", ar: "زراعة — أسمدة نيتروجينية (N₂O)" }, unit: "kg_N", hint: "FE: 4.417 kgCO2e/kg_N" },
  { key: "btp_beton", scope: 3, label: { fr: "BTP — Béton B25 (matériaux)", en: "Construction — Concrete B25 (materials)", ar: "بناء — خرسانة B25" }, unit: "kg", hint: "" },
  { key: "achats_papier", scope: 3, label: { fr: "Achats — Papier de bureau", en: "Purchases — Office paper", ar: "مشتريات — ورق مكتبي" }, unit: "kg", hint: "FE: 0.934 kgCO2e/kg" },
  { key: "achats_ordinateur", scope: 3, label: { fr: "Achats — Ordinateur portable (amortissement)", en: "Purchases — Laptop (amortisation)", ar: "مشتريات — حاسوب محمول" }, unit: "unité", hint: "FE: 316 kgCO2e/unité" },
  { key: "deplacements_repas", scope: 3, label: { fr: "Déplacements — Repas (restaurant)", en: "Business travel — Meals", ar: "تنقلات — وجبات طعام" }, unit: "repas", hint: "FE: 2.6 kgCO2e/repas" },
];

function ManualFactForm({ projectId, token, lang, onAdded }: {
  projectId: string;
  token: string;
  lang: Lang;
  onAdded: (f: ActivityFact) => void;
}) {
  const [open, setOpen] = useState(false);
  const [cat, setCat] = useState(MOROCCO_CATEGORIES[0].key);
  const [value, setValue] = useState("");
  const [desc, setDesc] = useState("");
  const [periodStart, setPeriodStart] = useState(`${new Date().getFullYear()}-01-01`);
  const [periodEnd, setPeriodEnd] = useState(`${new Date().getFullYear()}-12-31`);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const selected = MOROCCO_CATEGORIES.find((c) => c.key === cat) ?? MOROCCO_CATEGORIES[0];
  const lbl = { fr: "Proposer un fait (manuel)", en: "Propose a fact (manual)", ar: "اقتراح حقيقة (يدوي)" }[lang];
  const addLbl = { fr: "+ Saisie manuelle", en: "+ Manual entry", ar: "+ إدخال يدوي" }[lang];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true); setErr(null);
    try {
      const fact = await apiJson<ActivityFact>(`/projects/${projectId}/activity`, token, {
        method: "POST",
        body: JSON.stringify({
          category: selected.key,
          description: desc || selected.label[lang],
          activity_value: value,
          activity_unit: selected.unit,
          scope: selected.scope,
          scope2_type: selected.scope === 2 ? (cat.includes("_mkt") ? "market" : "location") : null,
          period_start: periodStart,
          period_end: periodEnd,
          state: "proposed",
        }),
      });
      onAdded(fact);
      setValue(""); setDesc(""); setOpen(false);
    } catch {
      setErr(lang === "fr" ? "Impossible d'ajouter ce fait." : lang === "ar" ? "تعذر إضافة هذه الحقيقة." : "Failed to add this fact.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      {!open ? (
        <button onClick={() => setOpen(true)} style={{ ...ghostBtn, fontSize: "0.82rem" }}>{addLbl}</button>
      ) : (
        <div style={{ ...sectionCard, borderLeft: "4px solid var(--accent)" }}>
          <h3 style={{ ...sectionTitle, color: "var(--accent)" }}>{lbl}</h3>
          <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }}>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>{lang === "fr" ? "Catégorie Maroc" : lang === "ar" ? "الفئة (المغرب)" : "Category (Morocco)"}</label>
              <select value={cat} onChange={(e) => setCat(e.target.value)} style={inputStyle}>
                {MOROCCO_CATEGORIES.map((c) => (
                  <option key={c.key} value={c.key}>{c.label[lang]}</option>
                ))}
              </select>
              {selected.hint && (
                <div style={{ fontSize: "0.72rem", color: "var(--muted)", marginTop: "0.25rem" }}>{selected.hint}</div>
              )}
            </div>
            <div>
              <label style={labelStyle}>{lang === "fr" ? "Valeur" : lang === "ar" ? "القيمة" : "Value"} ({selected.unit})</label>
              <input type="number" step="any" required value={value} onChange={(e) => setValue(e.target.value)} style={inputStyle} placeholder="0" />
            </div>
            <div>
              <label style={labelStyle}>{lang === "fr" ? "Scope" : "Scope"}</label>
              <input readOnly value={`Scope ${selected.scope}`} style={{ ...inputStyle, background: "var(--bg)", color: "var(--muted)" }} />
            </div>
            <div>
              <label style={labelStyle}>{lang === "fr" ? "Début période" : lang === "ar" ? "بداية الفترة" : "Period start"}</label>
              <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>{lang === "fr" ? "Fin période" : lang === "ar" ? "نهاية الفترة" : "Period end"}</label>
              <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} style={inputStyle} />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>{lang === "fr" ? "Description (optionnel)" : lang === "ar" ? "الوصف (اختياري)" : "Description (optional)"}</label>
              <input value={desc} onChange={(e) => setDesc(e.target.value)} style={inputStyle} placeholder={selected.label[lang]} />
            </div>
            {err && <div style={{ gridColumn: "1 / -1", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", color: "var(--red)", fontSize: "0.82rem" }}>{err}</div>}
            <div style={{ gridColumn: "1 / -1", display: "flex", gap: "0.75rem" }}>
              <button type="submit" disabled={submitting} style={primaryBtn}>
                {submitting ? "…" : (lang === "fr" ? "Proposer" : lang === "ar" ? "اقتراح" : "Propose")}
              </button>
              <button type="button" onClick={() => { setOpen(false); setErr(null); }} style={ghostBtn}>
                {lang === "fr" ? "Annuler" : lang === "ar" ? "إلغاء" : "Cancel"}
              </button>
            </div>
          </form>
        </div>
      )}
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
  justifyContent: "space-between",
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
