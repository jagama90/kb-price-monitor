import { createClient } from "npm:@supabase/supabase-js@2.95.0";

const allowedOrigin = "https://jagama90.github.io";
const repo = "jagama90/kb-price-monitor";
const listenerPath = ".github/workflows/manual-refresh-listener.yml";
const cors = {
  "Access-Control-Allow-Origin": allowedOrigin,
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Content-Type": "application/json",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: cors });

function serviceKey() {
  try {
    const raw = Deno.env.get("SUPABASE_SECRET_KEYS");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.default) return String(parsed.default);
    }
  } catch {}
  return Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
}

async function validateGitHubRun(token: string, runId: string) {
  if (!token || !/^\d+$/.test(runId)) return false;
  const r = await fetch(`https://api.github.com/repos/${repo}/actions/runs/${runId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "kb-price-monitor-manual-refresh",
    },
  });
  if (!r.ok) return false;
  const d = await r.json();
  if (!(String(d?.id) === runId &&
    d?.repository?.full_name === repo &&
    d?.path === listenerPath &&
    ["queued", "in_progress"].includes(String(d?.status || "")))) return false;

  const branch = await fetch(`https://api.github.com/repos/${repo}/branches/main`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "kb-price-monitor-manual-refresh",
    },
  });
  if (!branch.ok) return false;
  const b = await branch.json();
  return String(d?.head_sha || "") === String(b?.commit?.sha || "");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });

  const url = Deno.env.get("SUPABASE_URL") ?? "";
  const key = serviceKey();
  if (!url || !key) return json({ ok: false, error: "server_config" }, 500);
  const db = createClient(url, key, { auth: { persistSession: false } });

  const latest = async (source?: string) => {
    let q = db
      .from("manual_refresh_requests")
      .select("id,requested_at,source,dispatched_at,dispatched_by,dispatch_attempts");
    if (source) q = q.eq("source", source);
    const { data, error } = await q
      .order("requested_at", { ascending: false })
      .limit(1)
      .maybeSingle();
    if (error) throw error;
    return data;
  };

  if (req.method === "GET") {
    try {
      const id = new URL(req.url).searchParams.get("id");
      if (id && /^\d+$/.test(id)) {
        const { data, error } = await db
          .from("manual_refresh_requests")
          .select("id,requested_at,source,dispatched_at,dispatched_by,dispatch_attempts")
          .eq("id", Number(id))
          .maybeSingle();
        if (error) throw error;
        return json({ ok: true, request: data });
      }
      const { count } = await db
        .from("manual_refresh_requests")
        .select("id", { count: "exact", head: true })
        .is("dispatched_at", null);
      return json({ ok: true, latest: await latest(), pending_count: count ?? 0 });
    } catch (e) {
      return json({ ok: false, error: String(e) }, 500);
    }
  }

  if (req.method !== "POST") return json({ ok: false, error: "method_not_allowed" }, 405);

  let body: any = {};
  try { body = await req.json(); } catch {}
  const action = String(body?.action || "request");

  if (action === "request") {
    const origin = req.headers.get("origin") || "";
    if (origin !== allowedOrigin) return json({ ok: false, error: "origin_not_allowed" }, 403);
    try {
      const requestedSource = body?.source === "dashboard_validation" ? "dashboard_validation" : "dashboard";
      const prev = await latest(requestedSource);
      if (prev?.requested_at) {
        const age = Date.now() - new Date(prev.requested_at).getTime();
        if (Number.isFinite(age) && age < 5 * 60 * 1000) {
          return json({ ok: true, accepted: false, reason: "cooldown", request: prev });
        }
      }
      const { data, error } = await db
        .from("manual_refresh_requests")
        .insert({ source: requestedSource })
        .select("id,requested_at,source,dispatched_at,dispatched_by,dispatch_attempts")
        .single();
      if (error) throw error;
      return json({ ok: true, accepted: true, request: data }, 202);
    } catch (e) {
      return json({ ok: false, error: String(e) }, 500);
    }
  }

  if (action === "claim" || action === "release") {
    const runId = String(body?.run_id || "");
    const token = String(body?.github_token || "");
    if (!(await validateGitHubRun(token, runId))) {
      return json({ ok: false, error: "listener_auth_failed" }, 403);
    }

    try {
      if (action === "release") {
        const requestId = Number(body?.request_id);
        if (!Number.isFinite(requestId)) return json({ ok: false, error: "bad_request_id" }, 400);
        const { data, error } = await db
          .from("manual_refresh_requests")
          .update({ dispatched_at: null, dispatched_by: null })
          .eq("id", requestId)
          .eq("dispatched_by", runId)
          .select("id,requested_at,dispatched_at,dispatched_by,dispatch_attempts")
          .maybeSingle();
        if (error) throw error;
        return json({ ok: true, released: Boolean(data), request: data });
      }

      const { data: pending, error: pendingError } = await db
        .from("manual_refresh_requests")
        .select("id,requested_at,source,dispatch_attempts")
        .is("dispatched_at", null)
        .order("requested_at", { ascending: true })
        .limit(1)
        .maybeSingle();
      if (pendingError) throw pendingError;
      if (!pending) return json({ ok: true, claimed: false });

      const { data, error } = await db
        .from("manual_refresh_requests")
        .update({
          dispatched_at: new Date().toISOString(),
          dispatched_by: runId,
          dispatch_attempts: Number(pending.dispatch_attempts || 0) + 1,
        })
        .eq("id", pending.id)
        .is("dispatched_at", null)
        .select("id,requested_at,source,dispatched_at,dispatched_by,dispatch_attempts")
        .maybeSingle();
      if (error) throw error;
      return json({ ok: true, claimed: Boolean(data), request: data });
    } catch (e) {
      return json({ ok: false, error: String(e) }, 500);
    }
  }

  return json({ ok: false, error: "unknown_action" }, 400);
});
