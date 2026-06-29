"use client";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getBrowserClient } from "@/lib/supabase";
import { api, ApiError } from "@/lib/api";

type Client = { id: string; name: string; sector: string | null; created_at: string };
type Project = {
  id: string;
  client_id: string;
  name: string;
  reporting_year: number;
  methodology_id: string;
  status: string;
  created_at: string;
};
type Methodology = { id: string; name: string; version: string };

export default function ProjectsPage() {
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [methods, setMethods] = useState<Methodology[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  const [clientName, setClientName] = useState("");
  const [clientSector, setClientSector] = useState("");

  const [projName, setProjName] = useState("");
  const [projClient, setProjClient] = useState("");
  const [projYear, setProjYear] = useState(new Date().getFullYear());
  const [projMethod, setProjMethod] = useState("");

  async function load() {
    setBusy(true);
    setError(null);
    try {
      // ponytail: methodologies is a reference table — no dedicated endpoint,
      // so seed it from a constant rather than adding a new route.
      // The seed id for Bilan Carbone v8 is fixed.
      setMethods([
        {
          id: "00000000-0000-0000-0000-000000000001",
          name: "Bilan Carbone",
          version: "8.0",
        },
      ]);
      const [cs, ps] = await Promise.all([api.get<Client[]>("/clients"), api.get<Project[]>("/projects")]);
      setClients(cs);
      setProjects(ps);
      if (ps.length && !projClient) setProjClient(ps[0].client_id);
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
  }, []);

  async function signOut() {
    const sb = getBrowserClient();
    await sb.auth.signOut();
    router.replace("/login");
  }

  async function createClient(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post<Client>("/clients", { name: clientName, sector: clientSector || null });
      setClientName("");
      setClientSector("");
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function createProject(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await api.post<Project>("/projects", {
        client_id: projClient,
        name: projName,
        reporting_year: Number(projYear),
        methodology_id: projMethod || methods[0]?.id,
      });
      setProjName("");
      await load();
      router.push(`/projects/${created.id}`);
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
      else setError((e as Error).message);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-8 max-w-5xl mx-auto space-y-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projets</h1>
        <button
          onClick={signOut}
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          Se déconnecter
        </button>
      </header>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </p>
      )}

      <section className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-lg font-medium">Nouveau client</h2>
        <form onSubmit={createClient} className="flex gap-3 items-end">
          <label className="flex-1 text-sm">
            <span className="text-slate-700">Nom</span>
            <input
              required
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label className="flex-1 text-sm">
            <span className="text-slate-700">Secteur (optionnel)</span>
            <input
              value={clientSector}
              onChange={(e) => setClientSector(e.target.value)}
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <button
            type="submit"
            className="bg-slate-900 text-white rounded px-4 py-2 text-sm"
          >
            Créer
          </button>
        </form>
      </section>

      <section className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-lg font-medium">Nouveau projet</h2>
        <form onSubmit={createProject} className="grid grid-cols-2 gap-3">
          <label className="text-sm">
            <span className="text-slate-700">Client</span>
            <select
              required
              value={projClient}
              onChange={(e) => setProjClient(e.target.value)}
              className="mt-1 block w-full border rounded px-3 py-2"
            >
              <option value="">— choisir —</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="text-slate-700">Nom du projet</span>
            <input
              required
              value={projName}
              onChange={(e) => setProjName(e.target.value)}
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label className="text-sm">
            <span className="text-slate-700">Année de reporting</span>
            <input
              type="number"
              required
              value={projYear}
              onChange={(e) => setProjYear(Number(e.target.value))}
              className="mt-1 block w-full border rounded px-3 py-2"
            />
          </label>
          <label className="text-sm">
            <span className="text-slate-700">Méthodologie</span>
            <select
              value={projMethod}
              onChange={(e) => setProjMethod(e.target.value)}
              className="mt-1 block w-full border rounded px-3 py-2"
            >
              {methods.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} v{m.version}
                </option>
              ))}
            </select>
          </label>
          <div className="col-span-2 flex justify-end">
            <button
              type="submit"
              className="bg-slate-900 text-white rounded px-4 py-2 text-sm"
            >
              Créer le projet
            </button>
          </div>
        </form>
      </section>

      <section className="bg-white rounded-lg shadow">
        <h2 className="text-lg font-medium p-6 pb-3">Projets existants</h2>
        {busy ? (
          <p className="px-6 pb-6 text-sm text-slate-500">Chargement…</p>
        ) : projects.length === 0 ? (
          <p className="px-6 pb-6 text-sm text-slate-500">Aucun projet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-left">
              <tr>
                <th className="px-6 py-2 font-medium">Nom</th>
                <th className="px-6 py-2 font-medium">Année</th>
                <th className="px-6 py-2 font-medium">Statut</th>
                <th className="px-6 py-2" />
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="border-t">
                  <td className="px-6 py-2">{p.name}</td>
                  <td className="px-6 py-2">{p.reporting_year}</td>
                  <td className="px-6 py-2">{p.status}</td>
                  <td className="px-6 py-2 text-right">
                    <Link
                      href={`/projects/${p.id}`}
                      className="text-slate-900 hover:underline"
                    >
                      Ouvrir →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
