// Thin fetch wrapper that injects the Supabase session JWT as a Bearer token.
// Every call goes to NEXT_PUBLIC_API_URL.
import { getBrowserClient } from "./supabase";

const API = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function authHeader(): Promise<Record<string, string>> {
  const sb = getBrowserClient();
  const { data } = await sb.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError(401, "Not signed in");
  return { Authorization: `Bearer ${token}` };
}

async function call<T>(
  method: "GET" | "POST" | "PATCH",
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    ...(await authHeader()),
  };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.detail ?? msg;
    } catch {}
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => call<T>("GET", path),
  post: <T>(path: string, body?: unknown) => call<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => call<T>("PATCH", path, body),
};

export async function uploadFile(
  path: string,
  file: File,
): Promise<{ task_id: string; filename: string; status: string }> {
  const headers = await authHeader();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}${path}`, { method: "POST", headers, body: form });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.detail ?? msg;
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json();
}

export async function downloadFile(path: string): Promise<Blob> {
  const headers = await authHeader();
  const res = await fetch(`${API}${path}`, { method: "GET", headers });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return res.blob();
}
