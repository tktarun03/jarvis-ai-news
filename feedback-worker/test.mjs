// node feedback-worker/test.mjs  (offline; GitHub is mocked)
import assert from "node:assert/strict";
import worker, { buildIssue, clean } from "./worker.js";

const env = { REPO: "o/r", GITHUB_TOKEN: "t", ALLOWED_ORIGINS: "https://tktarun03.github.io" };
const O = "https://tktarun03.github.io";
let sent = null;
globalThis.fetch = async (url, init) => { sent = { url, init }; return new Response(JSON.stringify({ number: 7 }), { status: 201 }); };
const post = (body, origin = O) => worker.fetch(new Request("https://w/", { method: "POST", headers: { Origin: origin, "Content-Type": "application/json" }, body: typeof body === "string" ? body : JSON.stringify(body) }), env);

assert.equal(clean("hi @arun <b>", 50), "hi @​arun &lt;b>");
assert.ok(buildIssue({ rating: 0 }).error);
assert.ok(buildIssue({ rating: 6 }).error);
assert.ok(buildIssue({ rating: "x" }).error);
const i = buildIssue({ rating: 4, message: "More India stories\nplease", name: "Ravi", page: "/jarvis-ai-news/", version: "1.9.0" });
assert.deepEqual(i.labels, ["feedback", "rating-4"]);
assert.match(i.title, /^Feedback: 4★ Really good · More India stories$/);
assert.match(i.body, /★★★★☆/);

let r = await post({ rating: 5, message: "Love it" });
assert.equal(r.status, 201);
assert.equal(sent.url, "https://api.github.com/repos/o/r/issues");
assert.deepEqual(JSON.parse(sent.init.body).labels, ["feedback", "rating-5"]);
assert.equal(r.headers.get("Access-Control-Allow-Origin"), O);

sent = null;
r = await post({ rating: 5, website: "spam.example" });
assert.equal(r.status, 200); assert.equal(sent, null, "honeypot files nothing");
assert.equal((await post({ rating: 5 }, "https://evil.example")).status, 403);
assert.equal((await post("x".repeat(5000))).status, 413);
assert.equal((await post("{not json")).status, 400);
assert.equal((await post({ rating: 9 })).status, 400);
const pre = await worker.fetch(new Request("https://w/", { method: "OPTIONS", headers: { Origin: O } }), env);
assert.equal(pre.status, 204);
console.log("worker tests ok");
