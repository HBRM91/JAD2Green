// ponytail: single browser client factory — no need to thread the client through
// React context when every page can call getBrowserClient() on mount.
import { createBrowserClient } from "@supabase/ssr";

let cached: ReturnType<typeof createBrowserClient> | null = null;

export function getBrowserClient() {
  if (cached) return cached;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) {
    throw new Error(
      "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set",
    );
  }
  cached = createBrowserClient(url, anon);
  return cached;
}

export type Session = Awaited<
  ReturnType<ReturnType<typeof getBrowserClient>["auth"]["getSession"]>
>["data"]["session"];
