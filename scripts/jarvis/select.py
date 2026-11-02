"""Relevance filter, India/global routing, duplicate clustering, ranking and categorisation."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from .common import domain_of, jaccard, title_fingerprint, title_tokens, normalize_url

AI_RE = re.compile(
    r"\b(ai|a\.i\.|artificial intelligence|machine learning|deep learning|neural|llms?|large language model|"
    r"generative|genai|chatgpt|openai|anthropic|claude|gemini|deepmind|copilot|llama|mistral|qwen|deepseek|"
    r"sarvam|krutrim|bharatgen|indiaai|gpu|gpus|nvidia|inference|chatbot|agentic|ai agents?|foundation model|"
    r"transformer model|diffusion model|computer vision|speech recognition|robotics|humanoid|autonomous)\b",
    re.I,
)
INDIA_RE = re.compile(
    r"\b(india|indian|indians|bharat|meity|indiaai|trai|niti aayog|rbi|sebi|isro|c-dac|"
    r"bengaluru|bangalore|mumbai|delhi|new delhi|chennai|hyderabad|pune|kolkata|noida|gurugram|ahmedabad|"
    r"tamil nadu|karnataka|maharashtra|kerala|telangana|andhra pradesh|gujarat|bihar|uttar pradesh|"
    r"reliance|jio|infosys|tcs|wipro|hcltech|tech mahindra|ola krutrim|sarvam|zoho|flipkart|paytm|"
    r"vaishnaw|crore|lakh|₹)\b",
    re.I,
)

CATEGORY_RULES = [
    ("safety", r"\b(security|breach|backdoor|malware|vulnerab|exploit|deepfake|nudify|misuse|jailbreak|safety|alignment|scam|fraud|privacy)\b"),
    ("policy", r"\b(regulat|law|bill|act\b|policy|guideline|ministry|minister|government|parliament|court|lawsuit|antitrust|competition|probe|investigat|cma|ftc|eu ai act|trai|meity|consultation|cabinet)\b"),
    ("infrastructure", r"\b(gpu|gpus|chip|chips|semiconductor|data cent(?:er|re)|supercluster|compute|megawatt|\bmw\b|gigawatt|\bgw\b|nvidia|amd|tpu|kernel|linux|server|cloud region)\b"),
    ("business", r"\b(raises?|raised|funding|series [a-e]|seed|valuation|ipo|acquir|acquisition|merger|revenue|earnings|investment|investors|deal|deals|partnership|agreement)\b"),
    ("research", r"\b(paper|research|benchmark|study|researchers|model card|open[- ]weights?|parameters|state[- ]of[- ]the[- ]art|arxiv)\b"),
    ("products", r"\b(launch|launches|launched|release|releases|released|rolls? out|unveil|introduc|available|beta|update|feature|app)\b"),
    ("applications", r"\b(healthcare|hospital|education|school|agricultur|farm|bank|finance|retail|manufactur|legal|telecom|energy)\b"),
]

IMPACT_WEIGHTS = [
    (r"\b(launch|release|unveil|introduc)\w*", 6),
    (r"\b(regulat|law|guideline|ban|probe|investigat)\w*", 7),
    (r"\b(acquir|merger|ipo)\w*", 7),
    (r"\$\s?\d|\b\d+(\.\d+)?\s?(billion|bn|trillion|crore)\b|₹", 5),
    (r"\b(breach|backdoor|vulnerab|exploit)\w*", 6),
    (r"\b(gpt|gemini|claude|llama|qwen|deepseek|mistral|sarvam)\b", 4),
    (r"\b(first|record|largest)\b", 3),
]


def is_ai_relevant(text: str) -> bool:
    return bool(AI_RE.search(text))


def is_india(text: str) -> bool:
    return len(INDIA_RE.findall(text)) >= 1


def categorize(text: str, region: str, valid: set[str]) -> str:
    low = text.lower()
    if region == "india" and re.search(r"\b(startup|founder|raises|seed|series [a-e])\b", low) and "startups" in valid:
        return "startups"
    for key, pattern in CATEGORY_RULES:
        if key in valid and re.search(pattern, low):
            return key
    return "products" if "products" in valid else sorted(valid)[0]


def impact_score(text: str) -> int:
    return sum(w for p, w in IMPACT_WEIGHTS if re.search(p, text, re.I))


class Candidate:
    def __init__(self, item, region: str):
        self.item = item
        self.region = region
        self.tokens = title_tokens(item.title)
        self.cluster: list = [item]
        self.score = 0.0
        self.rejection: str | None = None

    @property
    def url(self):
        return self.item.url


def build_candidates(items, cfg: dict, now: datetime, seen: dict, blocked: list[str], log: list) -> list[Candidate]:
    ed = cfg["edition"]
    window_start = now - timedelta(hours=ed["lookback_hours"])
    future_limit = now + timedelta(minutes=cfg["verification"]["future_tolerance_minutes"])
    seen_urls = set(seen.get("urls", {}))
    seen_titles = set(seen.get("titles", {}))
    out: list[Candidate] = []
    for it in items:
        blob = f"{it.title} {it.description}"
        reason = None
        if it.published is None:
            reason = "no publication date in feed"
        elif it.published < window_start:
            reason = "outside lookback window"
        elif it.published > future_limit:
            reason = "publication date in the future"
        elif not it.source.get("ai_only") and not is_ai_relevant(blob):
            reason = "not AI-related"
        elif any(b.lower() in blob.lower() for b in blocked):
            reason = "blocked content pattern (sponsored / forecast / advertorial)"
        elif normalize_url(it.url) in seen_urls:
            reason = "already published in an earlier edition"
        elif title_fingerprint(it.title) in seen_titles:
            reason = "same headline already published in an earlier edition"
        if reason:
            if reason not in ("outside lookback window", "not AI-related"):
                log.append({"title": it.title, "url": it.url, "reason": reason})
            continue
        region = "india" if (it.source["region"] == "india" or is_india(blob)) else "global"
        out.append(Candidate(it, region))
    return out


def cluster(cands: list[Candidate], threshold: float) -> list[Candidate]:
    """Merge the same story reported by several outlets; keep the most trusted, earliest report."""
    cands = sorted(cands, key=lambda c: (-c.item.source["trust"], c.item.published))
    merged: list[Candidate] = []
    for c in cands:
        home = next((m for m in merged if jaccard(m.tokens, c.tokens) >= threshold), None)
        if home is None:
            merged.append(c)
        else:
            if domain_of(c.url) not in {domain_of(x.url) for x in home.cluster}:
                home.cluster.append(c.item)
            if c.region == "india":
                home.region = "india"
    return merged


def rank(cands: list[Candidate], now: datetime, lookback_hours: int) -> list[Candidate]:
    for c in cands:
        age_h = max(0.0, (now - c.item.published).total_seconds() / 3600)
        recency = max(0.0, 10.0 * (1 - age_h / max(1, lookback_hours)))
        c.score = (
            c.item.source["trust"] * 10
            + (len(c.cluster) - 1) * 8
            + impact_score(f"{c.item.title} {c.item.description}")
            + recency
        )
    return sorted(cands, key=lambda c: -c.score)


def pick(cands: list[Candidate], region: str, limit: int, per_source: int) -> list[Candidate]:
    chosen, counts = [], {}
    for c in cands:
        if c.region != region or c.rejection:
            continue
        sid = c.item.source["id"]
        if counts.get(sid, 0) >= per_source:
            continue
        chosen.append(c)
        counts[sid] = counts.get(sid, 0) + 1
        if len(chosen) >= limit:
            break
    return chosen
