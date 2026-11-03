// JARVIS AI NEWS feedback relay (Cloudflare Worker).
// The site is static, so it cannot hold a GitHub key. This Worker holds one (secret GITHUB_TOKEN,
// fine-grained, Issues: read and write on one repo) and turns each rating into a GitHub issue
// labelled `feedback` and `rating-N`. It stores nothing and logs no IP address.
//
// Guards (basic, by design): only the site's origin, JSON under 4 KB, a honeypot field,
// strict field limits, and at most PER_HOUR posts per visitor per hour (best effort, per data centre).
// If spam gets through anyway, add Cloudflare Turnstile.

const PER_HOUR = 5;
const WORDS = ["", "Not useful", "Needs work", "It's okay", "Really good", "Love it"];

function cors(origin) {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function json(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...(origin ? cors(origin) : {}) },
  });
}

// Plain text only: no @mentions (they would notify people), no markdown headings or HTML.
export function clean(value, max) {
  return String(value ?? "")
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .replace(/\r\n?/g, "\n")
    .replace(/@/g, "@​")
    .replace(/</g, "&lt;")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
    .slice(0, max);
}

export function buildIssue(input) {
  const rating = Number(input.rating);
  if (!Number.isInteger(rating) || rating < 1 || rating > 5) return { error: "rating must be 1 to 5" };
  const message = clean(input.message, 1000);
  const name = clean(input.name, 60).replace(/\n/g, " ");
  const page = clean(input.page, 120).replace(/\n/g, " ");
  const version = clean(input.version, 20).replace(/[^0-9A-Za-z.\-]/g, "");
  const stars = "★".repeat(rating) + "☆".repeat(5 - rating);
  const firstLine = message.split("\n")[0].slice(0, 60);
  const title = `Feedback: ${rating}★ ${WORDS[rating]}${firstLine ? " · " + firstLine : ""}`;
  const quote = message ? message.split("\n").map((l) => "> " + l).join("\n") : "_No comment._";
  const body = [
    `**Rating:** ${stars} (${rating}/5, ${WORDS[rating]})`,
    "",
    "**What should we improve?**",
    "",
    quote,
    "",
    `**From:** ${name || "Anonymous"}`,
    `**Page:** ${page || "unknown"} · app v${version || "?"}`,
    "",
    "<sub>Sent from the JARVIS AI NEWS app through the feedback Worker. No email or IP address is recorded.</sub>",
  ].join("\n");
  return { title, body, labels: ["feedback", `rating-${rating}`] };
}

async function overLimit(request) {
  if (typeof caches === "undefined") return false;
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const hour = new Date().toISOString().slice(0, 13);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(ip + "|" + hour));
  const key = new Request("https://rate.limit/" + [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join(""));
  const hit = await caches.default.match(key);
  const n = hit ? Number(await hit.text()) : 0;
  if (n >= PER_HOUR) return true;
  await caches.default.put(key, new Response(String(n + 1), { headers: { "Cache-Control": "max-age=3600" } }));
  return false;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
    const ok = allowed.includes(origin);

    if (request.method === "OPTIONS") return new Response(null, { status: ok ? 204 : 403, headers: ok ? cors(origin) : {} });
    if (request.method !== "POST") return json({ ok: true, service: "jarvis-feedback" }, 200, ok ? origin : "");
    if (!ok) return json({ error: "origin not allowed" }, 403, "");
    if (!env.GITHUB_TOKEN || !env.REPO) return json({ error: "not configured" }, 503, origin);

    const raw = await request.text();
    if (raw.length > 4096) return json({ error: "too large" }, 413, origin);
    let input;
    try { input = JSON.parse(raw); } catch { return json({ error: "bad json" }, 400, origin); }
    if (input.website) return json({ ok: true }, 200, origin); // honeypot: pretend success, file nothing
    const issue = buildIssue(input);
    if (issue.error) return json({ error: issue.error }, 400, origin);
    if (await overLimit(request)) return json({ error: "slow down" }, 429, origin);

    const gh = await fetch(`https://api.github.com/repos/${env.REPO}/issues`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "jarvis-feedback-worker",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(issue),
    });
    if (!gh.ok) return json({ error: "github " + gh.status }, 502, origin);
    const made = await gh.json();
    return json({ ok: true, number: made.number }, 201, origin);
  },
};
