#!/usr/bin/env python3
"""Render the profile boards from live GitHub data.

Every number comes from the GitHub API at render time. The boards are plain
SVG committed into docs/ so they load from the same origin as the README and
never depend on a third-party renderer being reachable.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com"
USER = "CJstate"

# Deep-space palette: near-black background, neon cyan primary, violet and
# mint accents. One accent per board keeps the set coherent.
BG_0 = "#04070f"
BG_1 = "#0a1120"
CYAN = "#00e5ff"
VIOLET = "#bd34fe"
MINT = "#00ffa3"
TEXT_DIM = "#7d8aa5"


def api(path):
    token = os.environ.get("GH_TOKEN", "")
    req = urllib.request.Request(
        API + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-render",
            "Authorization": f"Bearer {token}" if token else "",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read())


def graphql(query):
    token = os.environ.get("GH_TOKEN", "")
    req = urllib.request.Request(
        API + "/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "profile-render",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read())


def collect_data():
    user = api(f"/users/{USER}")
    merged_q = urllib.parse.quote(f"author:{USER} type:pr is:merged")
    month = time.strftime("%Y-%m-01")
    merged = api(f"/search/issues?q={merged_q}&per_page=100")
    open_prs = api(
        "/search/issues?q=" + urllib.parse.quote(f"author:{USER} type:pr is:open")
    )
    merged_month = api(f"/search/issues?q={merged_q}%20merged:%3E{month}")
    repos_with_merged = len(
        {item["repository_url"].rsplit("/", 2)[-1] for item in merged["items"]}
    )
    repos = api(f"/users/{USER}/repos?per_page=100")
    contrib = graphql(
        """
        query { user(login: "%s") {
          contributionsCollection { contributionCalendar { totalContributions } }
        } }
        """
        % USER
    )
    return {
        "repos": user["public_repos"],
        "merged_prs": merged["total_count"],
        "merged_repos": repos_with_merged,
        "merged_month": merged_month["total_count"],
        "open_prs": open_prs["total_count"],
        "contributions": contrib["data"]["user"]["contributionsCollection"][
            "contributionCalendar"
        ]["totalContributions"],
    }


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def stars_field(w, h, seed=7):
    """A scatter of faint blinking stars used behind every board."""
    out = []
    x = seed
    for i in range(42):
        x = (x * 31 + 17) % (w * h)
        sx, sy = x % w, (x // w) % h
        phase = (i * 1.37) % 5
        out.append(
            f'<circle cx="{sx}" cy="{sy}" r="1.1" fill="#9fb6d9" opacity="0.5">'
            f'<animate attributeName="opacity" values="0.12;0.55;0.12" dur="4.2s" '
            f'begin="{phase:.2f}s" repeatCount="indefinite"/></circle>'
        )
    return "".join(out)


def grid_field(w, h, step=46):
    lines = []
    for gx in range(0, w, step):
        lines.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{h}" stroke="#12203a" stroke-width="1"/>')
    for gy in range(0, h, step):
        lines.append(f'<line x1="0" y1="{gy}" x2="{w}" y2="{gy}" stroke="#12203a" stroke-width="1"/>')
    return "".join(lines)


DEFS = f"""
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{BG_0}"/>
    <stop offset="0.55" stop-color="{BG_1}"/>
    <stop offset="1" stop-color="#101a30"/>
  </linearGradient>
  <linearGradient id="nameGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}"/>
    <stop offset="0.55" stop-color="#6ea8ff"/>
    <stop offset="1" stop-color="{VIOLET}"/>
  </linearGradient>
  <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{MINT}"/>
    <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </linearGradient>
  <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="3.2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="softGlow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="1.6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
"""


def rocket_group():
    """A small ship flying an arc across the board, with a flickering flame."""
    body = (
        '<g transform="scale(1.05)">'
        '<path d="M -14 0 L 2 -5 L 20 0 L 2 5 Z" fill="#dbe7ff" filter="url(#softGlow)"/>'
        '<circle cx="6" cy="0" r="2.2" fill="{CYAN}"/>'
        '<path d="M -14 0 L -34 0" stroke="url(#flame)" stroke-width="3.4" stroke-linecap="round">'
        '<animate attributeName="stroke-width" values="3.4;4.6;3.4" dur="0.9s" repeatCount="indefinite"/></path>'
        "</g>"
    ).format(CYAN=CYAN)
    return (
        '<g opacity="0.95">'
        f'<animateMotion path="M -60 176 Q 300 26 980 92" dur="7s" rotate="auto" repeatCount="indefinite"/>'
        + body
        + "</g>"
    )


def hero_svg(d):
    w, h = 900, 240
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="CJstate mission board">
{DEFS}
<rect width="{w}" height="{h}" fill="url(#sky)" rx="16"/>
{''.join([f'<path d="M {x} 0 L {x} {h} M 0 {y} L {w} {y}" stroke="#0e1a30" stroke-width="1" fill="none"/>' for x, y in []])}
{grid_field(w, h)}
{stars_field(w, h)}
<g font-family="'Segoe UI', Helvetica, Arial, sans-serif">
  <text x="46" y="86" font-size="46" font-weight="700" fill="url(#nameGrad)" filter="url(#glow)" letter-spacing="2">CJSTATE</text>
  <text x="48" y="118" font-size="13" fill="{TEXT_DIM}" letter-spacing="4">BACKEND · GO INFRASTRUCTURE · K8S TOOLING</text>

  <line x1="48" y1="140" x2="852" y2="140" stroke="#1b2b4a" stroke-width="1"/>

  <text x="48" y="188" font-size="52" font-weight="700" fill="{MINT}" filter="url(#glow)">
    {d["merged_prs"]}
    <animate attributeName="opacity" values="0.86;1;0.86" dur="2.6s" repeatCount="indefinite"/>
  </text>
  <text x="48" y="210" font-size="12" fill="{TEXT_DIM}" letter-spacing="3">MERGED PULL REQUESTS · LIVE</text>

  <text x="360" y="184" font-size="30" font-weight="600" fill="{CYAN}">{d["contributions"]}</text>
  <text x="360" y="204" font-size="11" fill="{TEXT_DIM}" letter-spacing="2">CONTRIBUTIONS · LAST YEAR</text>

  <text x="650" y="184" font-size="30" font-weight="600" fill="{VIOLET}">{d["merged_repos"]}</text>
  <text x="650" y="204" font-size="11" fill="{TEXT_DIM}" letter-spacing="2">REPOS WITH MERGED PRS</text>
</g>
{rocket_group()}
</svg>
"""


def typing_svg():
    """Three rotating lines typed by a sweeping clip mask with a blinking caret."""
    w, h, dur = 640, 92, 13.5
    lines = [
        ("Fixing the bugs CI never catches", 0.0),
        ("Go infrastructure · Kubernetes tooling · Prometheus", dur / 3),
        ("Test-first, every time", 2 * dur / 3),
    ]
    parts = []
    for text, begin in lines:
        x = 40
        clip_id = "clip" + str(int(begin * 100))
        sweep = (dur / 3) - 1.2
        parts.append(
            f'<clipPath id="{clip_id}"><rect x="{x}" y="0" width="0" height="{h}">'
            f'<animate attributeName="width" values="0;0;{w - 2 * x};{w - 2 * x};0" keyTimes="0;{begin / dur:.3f};{(begin + sweep) / dur:.3f};{(begin + dur / 3 - 0.6) / dur:.3f};{(begin + dur / 3 - 0.1) / dur:.3f}" dur="{dur}s" repeatCount="indefinite"/>'
            f"</rect></clipPath>"
            f'<text x="{x}" y="56" font-size="20" font-weight="600" fill="{CYAN}" font-family="\'JetBrains Mono\', Consolas, monospace" clip-path="url(#{clip_id})">{esc(text)}</text>'
        )
    caret = (
        f'<rect x="38" y="34" width="3" height="26" fill="{MINT}" filter="url(#softGlow)">'
        '<animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/>'
        f'<animate attributeName="x" values="38;{w - 60};38" keyTimes="0;0.46;0.92" dur="{dur}s" repeatCount="indefinite"/>'
        "</rect>"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="typing">
{DEFS}
<rect width="{w}" height="{h}" fill="none"/>
{''.join(parts)}
{caret}
</svg>
"""


def stat_card(x, y, w, h, accent, label, value, delay):
    return f"""
  <g opacity="0">
    <animate attributeName="opacity" values="0;1" begin="{delay}s" dur="0.6s" fill="freeze"/>
    <animateTransform attributeName="transform" type="translate" from="0 10" to="0 0" begin="{delay}s" dur="0.6s" fill="freeze"/>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#0b1424" stroke="#1c2d4f" stroke-width="1"/>
    <rect x="{x}" y="{y}" width="3.5" height="{h}" rx="1.5" fill="{accent}" filter="url(#softGlow)">
      <animate attributeName="opacity" values="0.55;1;0.55" dur="3s" repeatCount="indefinite"/>
    </rect>
    <text x="{x + 22}" y="{y + 44}" font-size="27" font-weight="700" fill="{accent}" font-family="'Segoe UI', Helvetica, sans-serif">{value}</text>
    <text x="{x + 22}" y="{y + 66}" font-size="10.5" fill="{TEXT_DIM}" letter-spacing="2.2" font-family="'Segoe UI', sans-serif">{esc(label.upper())}</text>
  </g>"""


def stats_svg(d):
    w, h = 900, 190
    cards = [
        (MINT, "Merged PRs · live", d["merged_prs"]),
        (CYAN, "Contributions · last year", d["contributions"]),
        (VIOLET, "Repos with merged PRs", d["merged_repos"]),
        ("#ffb86b", "Merged this month", d["merged_month"]),
        ("#6ea8ff", "PRs in flight", d["open_prs"]),
        (MINT, "Public repos", d["repos"]),
    ]
    body = []
    cw, ch, gap = 275, 62, 18
    for i, (accent, label, value) in enumerate(cards):
        x = 24 + (i % 3) * (cw + gap)
        y = 30 + (i // 3) * (ch + gap)
        body.append(stat_card(x, y, cw, ch, accent, label, value, 0.12 * i))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Live GitHub metrics">
{DEFS}
<rect width="{w}" height="{h}" fill="url(#sky)" rx="14"/>
{grid_field(w, h, 52)}
{stars_field(w, h, seed=11)}
{''.join(body)}
</svg>
"""


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = collect_data()
    boards = {
        "hero.svg": hero_svg(data),
        "typing.svg": typing_svg(),
        "stats.svg": stats_svg(data),
    }
    for name, svg in boards.items():
        (out_dir / name).write_text(svg, encoding="utf-8", newline="\n")
        print(f"wrote {out_dir / name}")


if __name__ == "__main__":
    main()
