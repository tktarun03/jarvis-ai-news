"""Original, copyright-free cover art: one deterministic SVG per story (seeded by its id)."""
from __future__ import annotations

import math
import random
from html import escape

W, H = 1200, 675
INK = "#121316"
INK2 = "#1B1C1F"
BRASS = "#D4B47C"


def _flow_lines(rnd: random.Random, color: str) -> str:
    paths = []
    for i in range(14):
        y0 = rnd.uniform(-40, H + 40)
        amp = rnd.uniform(18, 70)
        freq = rnd.uniform(0.0025, 0.007)
        phase = rnd.uniform(0, math.tau)
        pts = []
        for x in range(-20, W + 40, 40):
            y = y0 + amp * math.sin(x * freq + phase) + (x / W) * rnd.uniform(-60, 60)
            pts.append(f"{x},{y:.1f}")
        op = 0.05 + 0.10 * (i % 3) / 2
        paths.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="1.4" opacity="{op:.2f}"/>')
    return "".join(paths)


def _dots(rnd: random.Random) -> str:
    out = []
    for _ in range(46):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.choice([1.2, 1.6, 2.2])}" fill="#ECECEE" opacity="{rnd.uniform(.08, .28):.2f}"/>')
    return "".join(out)


def _glyph(cat: str, color: str, rnd: random.Random) -> str:
    cx, cy = 900, 320
    s = f'stroke="{color}" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"'
    if cat == "research":
        nodes = [(cx + 150 * math.cos(a), cy + 150 * math.sin(a)) for a in [rnd.uniform(0, math.tau) for _ in range(7)]]
        lines = "".join(f'<line x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" {s} opacity=".55"/>' for x, y in nodes)
        dots = "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="10" fill="{color}"/>' for x, y in nodes)
        rings = "".join(f'<circle cx="{cx}" cy="{cy}" r="{r}" {s} opacity="{o}"/>' for r, o in ((80, .9), (150, .35), (215, .18)))
        return rings + lines + dots + f'<circle cx="{cx}" cy="{cy}" r="22" fill="{color}"/>'
    if cat == "products":
        return "".join(
            f'<rect x="{cx - 150 + i * 34}" y="{cy - 150 + i * 34}" width="260" height="190" rx="26" {s} opacity="{0.35 + i * 0.22:.2f}"/>'
            for i in range(3)) + f'<circle cx="{cx + 40}" cy="{cy + 40}" r="16" fill="{color}"/>'
    if cat == "business":
        bars = []
        for i in range(6):
            h = 60 + i * 38 + rnd.uniform(-14, 14)
            bars.append(f'<rect x="{cx - 190 + i * 64}" y="{cy + 170 - h:.0f}" width="40" height="{h:.0f}" rx="8" fill="{color}" opacity="{0.35 + i * 0.12:.2f}"/>')
        return "".join(bars) + f'<polyline points="{cx-190},{cy+80} {cx-60},{cy+20} {cx+40},{cy+40} {cx+200},{cy-120}" {s}/>'
    if cat == "policy":
        cols = "".join(f'<line x1="{cx - 120 + i * 60}" y1="{cy - 40}" x2="{cx - 120 + i * 60}" y2="{cy + 130}" {s}/>' for i in range(5))
        return (f'<polygon points="{cx-170},{cy-50} {cx},{cy-150} {cx+170},{cy-50}" {s}/>' + cols +
                f'<line x1="{cx-180}" y1="{cy+150}" x2="{cx+180}" y2="{cy+150}" {s}/>'
                f'<circle cx="{cx}" cy="{cy-85}" r="12" fill="{color}"/>')
    if cat == "infrastructure":
        pins = []
        for i in range(6):
            o = -125 + i * 50
            pins += [f'<line x1="{cx+o}" y1="{cy-150}" x2="{cx+o}" y2="{cy-190}" {s}/>',
                     f'<line x1="{cx+o}" y1="{cy+150}" x2="{cx+o}" y2="{cy+190}" {s}/>',
                     f'<line x1="{cx-150}" y1="{cy+o}" x2="{cx-190}" y2="{cy+o}" {s}/>',
                     f'<line x1="{cx+150}" y1="{cy+o}" x2="{cx+190}" y2="{cy+o}" {s}/>']
        return (f'<rect x="{cx-150}" y="{cy-150}" width="300" height="300" rx="28" {s}/>'
                f'<rect x="{cx-80}" y="{cy-80}" width="160" height="160" rx="16" fill="{color}" opacity=".85"/>' + "".join(pins))
    if cat == "safety":
        return (f'<path d="M{cx} {cy-180} L{cx+150} {cy-120} L{cx+150} {cy+10} C{cx+150} {cy+110} {cx+70} {cy+170} {cx} {cy+200} '
                f'C{cx-70} {cy+170} {cx-150} {cy+110} {cx-150} {cy+10} L{cx-150} {cy-120} Z" {s}/>'
                f'<path d="M{cx-55} {cy+5} L{cx-12} {cy+50} L{cx+65} {cy-45}" stroke="{color}" fill="none" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
    if cat == "applications":
        hexes = []
        for q, r in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)):
            x = cx + 92 * (q + r / 2)
            y = cy + 80 * r
            pts = " ".join(f"{x + 50 * math.cos(math.radians(60 * k + 30)):.0f},{y + 50 * math.sin(math.radians(60 * k + 30)):.0f}" for k in range(6))
            fill = f'fill="{color}" opacity=".85"' if (q, r) == (0, 0) else f'fill="none" stroke="{color}" stroke-width="3" opacity=".6"'
            hexes.append(f'<polygon points="{pts}" {fill}/>')
        return "".join(hexes)
    # startups and anything else: an ascending spark trail
    pts = [(cx - 200 + i * 70, cy + 150 - i * i * 9) for i in range(7)]
    trail = "".join(f'<circle cx="{x}" cy="{y}" r="{5 + i * 3}" fill="{color}" opacity="{0.25 + i * 0.11:.2f}"/>' for i, (x, y) in enumerate(pts))
    return trail + f'<path d="M{pts[-1][0]} {pts[-1][1]-60} l14 46 l46 14 l-46 14 l-14 46 l-14 -46 l-46 -14 l46 -14 Z" fill="{BRASS}"/>'


def render_cover(story_id: str, category: str, category_label: str, color: str, source_domain: str, date_label: str) -> str:
    rnd = random.Random(int(story_id, 16))
    gx, gy = rnd.uniform(650, 1050), rnd.uniform(120, 520)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(category_label)} cover">
<defs>
<radialGradient id="g" cx="{gx/W:.3f}" cy="{gy/H:.3f}" r="0.75">
<stop offset="0" stop-color="{color}" stop-opacity=".34"/><stop offset=".55" stop-color="{color}" stop-opacity=".06"/><stop offset="1" stop-color="{INK}" stop-opacity="0"/>
</radialGradient>
<linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{INK2}"/><stop offset="1" stop-color="{INK}"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#b)"/>
<rect width="{W}" height="{H}" fill="url(#g)"/>
{_flow_lines(rnd, color)}
{_dots(rnd)}
<g>{_glyph(category, color, rnd)}</g>
<g transform="translate(64 64)" fill="none" stroke="#ECECEE" stroke-width="2.4" opacity=".9">
<circle cx="22" cy="22" r="20"/><circle cx="22" cy="22" r="13" stroke-dasharray="1.5 4" stroke-linecap="round" opacity=".7"/>
<path d="M22 13 l2.6 6.4 6.4 2.6 -6.4 2.6 -2.6 6.4 -2.6 -6.4 -6.4 -2.6 6.4 -2.6 Z" fill="{BRASS}" stroke="none"/>
</g>
<text x="124" y="95" font-family="Hanken Grotesk, Helvetica Neue, Arial, sans-serif" font-size="30" font-weight="300" letter-spacing="1" fill="#ECECEE">JARVIS</text>
<text x="64" y="560" font-family="IBM Plex Mono, Menlo, monospace" font-size="24" letter-spacing="4" fill="{color}">{escape(category_label.upper())}</text>
<line x1="64" y1="585" x2="300" y2="585" stroke="{color}" stroke-width="2" opacity=".6"/>
<text x="64" y="625" font-family="IBM Plex Mono, Menlo, monospace" font-size="22" fill="#8D9098">{escape(source_domain)}</text>
<text x="{W-64}" y="625" text-anchor="end" font-family="IBM Plex Mono, Menlo, monospace" font-size="22" fill="#8D9098">{escape(date_label)}</text>
</svg>
"""
