import { createClient } from "npm:@supabase/supabase-js@2.95.0";

const allowedOrigin = "https://jagama90.github.io";
const cors = {
  "Access-Control-Allow-Origin": allowedOrigin,
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Content-Type": "application/json",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: cors });

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });

  const url = Deno.env.get("SUPABASE_URL") ?? "";
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  if (!url || !key) return json({ ok: false, error: "server_config" }, 500);

  const db = createClient(url, key, { auth: { persistSession: false } });
  const latest = async () => {
    const { data, error } = await db
      .from("manual_refresh_requests")
      .select("id,requested_at,source")
      .order("requested_at", { ascending: false })
      .limit(1)
      .maybeSingle();
    if (error) throw error;
    return data;
  };

  if (req.method === "GET") {
    try {
      return json({ ok: true, latest: await latest() });
    } catch (e) {
      return json({ ok: false, error: String(e) }, 500);
    }
  }

  if (req.method !== "POST") return json({ ok: false, error: "method_not_allowed" }, 405);

  const origin = req.headers.get("origin") || "";
  if (origin !== allowedOrigin) return json({ ok: false, error: "origin_not_allowed" }, 403);

  try {
    const prev = await latest();
    if (prev?.requested_at) {
      const age = Date.now() - new Date(prev.requested_at).getTime();
      if (Number.isFinite(age) && age < 5 * 60 * 1000) {
        return json({ ok: true, accepted: false, reason: "cooldown", request: prev });
      }
    }

    const { data, error } = await db
      .from("manual_refresh_requests")
      .insert({ source: "dashboard" })
      .select("id,requested_at,source")
      .single();
    if (error) throw error;

    return json({ ok: true, accepted: true, request: data }, 202);
  } catch (e) {
    return json({ ok: false, error: String(e) }, 500);
  }
});
