"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ApiError, api, downloadFile, uploadFile } from "@/lib/api";
import { getBrowserClient } from "@/lib/supabase";

type Project = {
  id: string;
  client_id: string;
  name: string;
  reporting_year: number;
  methodology_id: string;
  status: string;
};
type Fact = {
  id: string;
  category: string;
  sub_category: string | null;
  description: string | null;
  activity_value: string;
  activity_unit: string;
  period_start: string;
  period_end: string;
  scope: number;
  scope2_type: string | null;
  state: "proposed" | "validated";
  provenance: Record<string, unknown>;
  created_at: string;
};
type Snapshot = {
  id: string;
  reporting_year: number;
  state_hash: string;
  totals_co2e: Record<string, number>;
  scope2_location_t: string | null;
  scope2_market_t: string | null;
  gwp_basis: string;
  uncertainty: Record<string, unknown>;
  reconciliation: Record<string, unknown>;
  factor_set_versions: string[];
  computation_trace: unknown[];
  created_at: string;
};

export default function ProjectDetailPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const router = useRouter();

  const [project, setProject] = useState<Project | null>(null);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [computeOpen, setComputeOpen] = useState(false);

  // compute form
  const [year, setYear] = useState(new Date().getFullYear());
  const [gwp, setGwp] = useState<"AR4" | "AR5" | "AR6">("AR5");
  const [region, setRegion] = useState("MA");

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const [p, f, s] = await Promise.all([
        api.get<Project>(`/projects/${projectId}`),
        api.get<Fact[]>(`/projects/${projectId}/activity`),
        api.get<Snapshot[]>(`/projects/${projectId}/snapshots`),
      ]);
      setProject(p);
      setFacts(f);
      setSnapshots(s);
      setYear(p.reporting_year);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    (async () => {
      const sb = getBrowserClient();
      const { data } = await sb.auth.getSession();
      if (!data.session) {
        router.replace("/login");
        return;
      }
      await load();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = (e.currentTarget.elements.namedItem("file") as HTMLInputElement)
      ?.files?.[0];
    if (!f) return;
    setError(null);
    try {
      await uploadFile(`/projects/${projectId}/documents`, f);
      e.currentTarget.reset();
      // extraction is async; give the worker a moment before reload
      setTimeout(load, 1500);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // §0 inv 3 + 4: validation is the ONLY human-gated path to validated.
  // Explicit button click + consultant's reviewer note = human action.
  async function onValidate(factId: string) {
    setError(null);
    try {
      await api.patch(`/projects/${projectId}/activity/${factId}/validate`, {
        reviewer_note: notes[factId] || null,
      });
      setNotes((n) => ({ ...n, [factId]: "" }));
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function onPropose(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const scope = Number(fd.get("scope"));
    const body = {
      category: String(fd.get("category")),
      sub_category: fd.get("sub_category") || null,
      description: fd.get("description") || null,
      activity_value: String(fd.get("activity_value")),
      activity_unit: String(fd.get("activity_unit")),
      period_start: String(fd.get("period_start")),
      period_end: String(fd.get("period_end")),
      scope,
      scope2_type: scope === 2 ? String(fd.get("scope2_type") || "location") : null,
      provenance: { source: "manual_ui_entry" },
    };
    setError(null);
    try {
      await api.post(`/projects/${projectId}/activity`, body);
      form.reset();
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function onCompute(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post(`/projects/${projectId}/compute`, {
        reporting_year: year,
        gwp_basis: gwp,
        methodology_id: project?.methodology_id,
        region,
      });
      setComputeOpen(false);
      await load();
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
      else setError((e as Error).message);
    }
  }

  async function onDownload(snapId: string) {
    setError(null);
    try {
      const blob = await downloadFile(
        `/projects/${projectId}/snapshots/${snapId}/report`,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bilan_carbone_${projectId}_${snapId.slice(0, 8)}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // §0 inv 11: Google export is opt-in, default OFF at the bureau level.
  // The button is separate from download so the consultant actively chooses
  // export — never auto-fired, never bundled into download.
  async function onExportGoogle(snapId: string) {
    setError(null);
    try {
      const res = await api.post<{ doc_url?: string; id?: string }>(
        `/projects/${projectId}/snapshots/${snapId}/export`,
      );
      if (res.doc_url) {
        alert(`Exporté vers Google Docs : ${res.doc_url}`);
      } else {
        alert("Export terminé.");
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setError(
          "Export Google désactivé. Activez Google Export dans les paramètres du bureau (par défaut : OFF).",
        );
      } else {
        setError((e as Error).message);
      }
    }
  }

  if (busy && !project) {
    return <main className="p-8 text-slate-500">Chargement…</main>;
  }

  return (
    <main className="min-h-screen bg-slate-50 p-8 max-w-6xl mx-auto space-y-8">
      <header className="flex items-center justify-between">
        <div>
          <Link href="/projects" className="text-sm text-slate-500 hover:underline">
            ← Tous les projets
          </Link>
          <h1 className="text-2xl font-semibold mt-1">{project?.name ?? "…"}</h1>
          <p className="text-sm text-slate-500">
            Année {project?.reporting_year} · statut {project?.status}
          </p>
        </div>
      </header>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </p>
      )}

      {/* ── DOCUMENT UPLOAD ──────────────────────────────────────── */}
      <section className="bg-white rounded-lg shadow p-6 space-y-3">
        <h2 className="text-lg font-medium">Document source</h2>
        <form onSubmit={onUpload} className="flex gap-3 items-end">
          <input
            type="file"
            name="file"
            accept=".pdf,.xlsx,.xls,.csv,.docx"
            className="text-sm"
          />
          <button
            type="submit"
            className="bg-slate-900 text-white rounded px-4 py-2 text-sm"
          >
            Téléverser
          </button>
          <span className="text-xs text-slate-500">
            L&apos;extraction crée des faits en état <code>proposed</code>.
          </span>
        </form>
      </section>

      {/* ── ACTIVITY FACTS (proposed → validated) ────────────────── */}
      <section className="bg-white rounded-lg shadow">
        <h2 className="text-lg font-medium p-6 pb-3">Faits d&apos;activité</h2>
        {facts.length === 0 ? (
          <p className="px-6 pb-6 text-sm text-slate-500">Aucun fait.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-left">
              <tr>
                <th className="px-6 py-2 font-medium">Catégorie</th>
                <th className="px-6 py-2 font-medium">Valeur</th>
                <th className="px-6 py-2 font-medium">Unité</th>
                <th className="px-6 py-2 font-medium">Période</th>
                <th className="px-6 py-2 font-medium">Scope</th>
                <th className="px-6 py-2 font-medium">État</th>
                <th className="px-6 py-2 font-medium">Note reviewer</th>
                <th className="px-6 py-2" />
              </tr>
            </thead>
            <tbody>
              {facts.map((f) => (
                <tr key={f.id} className="border-t align-top">
                  <td className="px-6 py-2">
                    {f.category}
                    {f.sub_category ? ` / ${f.sub_category}` : ""}
                  </td>
                  <td className="px-6 py-2">{f.activity_value}</td>
                  <td className="px-6 py-2">{f.activity_unit}</td>
                  <td className="px-6 py-2">
                    {f.period_start} → {f.period_end}
                  </td>
                  <td className="px-6 py-2">
                    {f.scope}
                    {f.scope2_type ? ` (${f.scope2_type})` : ""}
                  </td>
                  <td className="px-6 py-2">
                    <span
                      className={
                        f.state === "validated"
                          ? "text-green-700 font-medium"
                          : "text-amber-700"
                      }
                    >
                      {f.state}
                    </span>
                  </td>
                  <td className="px-6 py-2">
                    {f.state === "proposed" ? (
                      <input
                        type="text"
                        placeholder="Note (optionnelle)"
                        value={notes[f.id] ?? ""}
                        onChange={(e) =>
                          setNotes((n) => ({ ...n, [f.id]: e.target.value }))
                        }
                        className="border rounded px-2 py-1 w-40"
                      />
                    ) : (
                      <span className="text-xs text-slate-500">
                        {String((f.provenance as Record<string, unknown>).reviewer_note ?? "—")}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-2 text-right">
                    {f.state === "proposed" && (
                      <button
                        onClick={() => onValidate(f.id)}
                        className="bg-slate-900 text-white rounded px-3 py-1 text-xs"
                      >
                        Valider
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* ── MANUAL ENTRY (propose new fact) ─────────────────────── */}
      <section className="bg-white rounded-lg shadow p-6 space-y-3">
        <h2 className="text-lg font-medium">Saisir un fait manuellement</h2>
        <form onSubmit={onPropose} className="grid grid-cols-4 gap-3 text-sm">
          <label>
            <span className="text-slate-700">Catégorie</span>
            <input
              required
              name="category"
              placeholder="ex. scope2_electricity"
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label>
            <span className="text-slate-700">Sous-catégorie</span>
            <input
              name="sub_category"
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label>
            <span className="text-slate-700">Valeur</span>
            <input
              required
              name="activity_value"
              type="number"
              step="0.0001"
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label>
            <span className="text-slate-700">Unité</span>
            <input
              required
              name="activity_unit"
              placeholder="ex. kWh"
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label>
            <span className="text-slate-700">Début</span>
            <input
              required
              name="period_start"
              type="date"
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label>
            <span className="text-slate-700">Fin</span>
            <input
              required
              name="period_end"
              type="date"
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label>
            <span className="text-slate-700">Scope</span>
            <select
              required
              name="scope"
              defaultValue="2"
              className="mt-1 block w-full border rounded px-3 py-2"
            >
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
            </select>
          </label>
          <label>
            <span className="text-slate-700">Scope 2 type</span>
            <select
              name="scope2_type"
              defaultValue="location"
              className="mt-1 block w-full border rounded px-3 py-2"
            >
              <option value="location">location</option>
              <option value="market">market</option>
            </select>
          </label>
          <label className="col-span-3">
            <span className="text-slate-700">Description</span>
            <input
              name="description"
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <div className="col-span-4 flex justify-end">
            <button
              type="submit"
              className="bg-slate-900 text-white rounded px-4 py-2 text-sm"
            >
              Proposer (état : proposed)
            </button>
          </div>
        </form>
      </section>

      {/* ── COMPUTE ─────────────────────────────────────────────── */}
      <section className="bg-white rounded-lg shadow p-6 space-y-3">
        <h2 className="text-lg font-medium">Calcul des émissions</h2>
        <p className="text-sm text-slate-500">
          Bloqué tant que des faits sont en état <code>proposed</code> (§0 inv 10).
        </p>
        {!computeOpen ? (
          <button
            onClick={() => setComputeOpen(true)}
            className="bg-slate-900 text-white rounded px-4 py-2 text-sm"
          >
            Calculer
          </button>
        ) : (
          <form onSubmit={onCompute} className="grid grid-cols-3 gap-3 text-sm items-end">
            <label>
              <span className="text-slate-700">Année</span>
              <input
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="mt-1 block w-full border rounded px-3 py-2"
              />
            </label>
            <label>
              <span className="text-slate-700">Base GWP</span>
              <select
                value={gwp}
                onChange={(e) => setGwp(e.target.value as "AR4" | "AR5" | "AR6")}
                className="mt-1 block w-full border rounded px-3 py-2"
              >
                <option value="AR4">AR4</option>
                <option value="AR5">AR5</option>
                <option value="AR6">AR6</option>
              </select>
            </label>
            <label>
              <span className="text-slate-700">Région</span>
              <input
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="mt-1 block w-full border rounded px-3 py-2"
              />
            </label>
            <div className="col-span-3 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setComputeOpen(false)}
                className="text-slate-600 text-sm"
              >
                Annuler
              </button>
              <button
                type="submit"
                className="bg-slate-900 text-white rounded px-4 py-2 text-sm"
              >
                Lancer le calcul
              </button>
            </div>
          </form>
        )}
      </section>

      {/* ── SNAPSHOTS ───────────────────────────────────────────── */}
      <section className="bg-white rounded-lg shadow">
        <h2 className="text-lg font-medium p-6 pb-3">Snapshots (immuables)</h2>
        {snapshots.length === 0 ? (
          <p className="px-6 pb-6 text-sm text-slate-500">Aucun snapshot.</p>
        ) : (
          <ul className="divide-y">
            {snapshots.map((s) => (
              <li key={s.id} className="p-6 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">
                      {new Date(s.created_at).toLocaleString("fr-FR")} ·{" "}
                      {s.gwp_basis} · hash {s.state_hash.slice(0, 12)}…
                    </p>
                    <p className="text-xs text-slate-500">
                      Scope 2 (location): {s.scope2_location_t ?? "—"} t ·{" "}
                      Scope 2 (market): {s.scope2_market_t ?? "—"} t ·{" "}
                      Total CO₂e:{" "}
                      {Object.entries(s.totals_co2e)
                        .map(([k, v]) => `${k}=${v}`)
                        .join(", ")}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => onDownload(s.id)}
                      className="bg-slate-900 text-white rounded px-3 py-1 text-xs"
                    >
                      Télécharger DOCX
                    </button>
                    {/* §0 inv 11: opt-in Google export, default OFF (bureau flag). */}
                    <button
                      onClick={() => onExportGoogle(s.id)}
                      className="bg-white border border-slate-300 text-slate-700 rounded px-3 py-1 text-xs"
                      title="Export Google Docs (opt-in, désactivé par défaut au niveau du bureau)"
                    >
                      Exporter vers Google Docs
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
