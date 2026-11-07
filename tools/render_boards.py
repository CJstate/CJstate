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
# mint accents. One accent per metric keeps the set coherent.
BG_0 = "#03060d"
BG_1 = "#0a1120"
BG_2 = "#101a30"
CYAN = "#00e5ff"
VIOLET = "#bd34fe"
MINT = "#00ffa3"
AMBER = "#ffb86b"
BLUE = "#6ea8ff"
TEXT_DIM = "#7d8aa5"
FONT_UI = "'Segoe UI', Helvetica, Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Code', Consolas, monospace"


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
        "rendered_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    }


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


DEFS = f"""
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0.35" y2="1">
    <stop offset="0" stop-color="{BG_0}"/>
    <stop offset="0.6" stop-color="{BG_1}"/>
    <stop offset="1" stop-color="{BG_2}"/>
  </linearGradient>
  <linearGradient id="nameGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}"/>
    <stop offset="0.5" stop-color="{BLUE}"/>
    <stop offset="1" stop-color="{VIOLET}"/>
    <animate attributeName="x1" values="-0.4;1.4;-0.4" dur="9s" repeatCount="indefinite"/>
    <animate attributeName="x2" values="0.6;2.4;0.6" dur="9s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{MINT}"/>
    <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>
    <stop offset="0.5" stop-color="{CYAN}" stop-opacity="0.55"/>
    <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="orbitGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0.75"/>
    <stop offset="0.6" stop-color="{VIOLET}" stop-opacity="0.35"/>
    <stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="groundFade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0.5"/>
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


def stars_field(w, h, seed=7, count=70):
    """Two layers of faint blinking stars: a far layer of tiny dots and a
    near layer of a few brighter ones."""
    out = []
    x = seed
    for i in range(count):
        x = (x * 31 + 17) % (w * h)
        sx, sy = x % w, (x // w) % (h - 4)
        phase = (i * 1.37) % 5
        if i % 7 == 0:
            out.append(
                f'<circle cx="{sx}" cy="{sy}" r="1.5" fill="#cfe0ff">'
                f'<animate attributeName="opacity" values="0.15;0.85;0.15" dur="3.4s" '
                f'begin="{phase:.2f}s" repeatCount="indefinite"/></circle>'
            )
        else:
            out.append(
                f'<circle cx="{sx}" cy="{sy}" r="1" fill="#9fb6d9" opacity="0.5">'
                f'<animate attributeName="opacity" values="0.1;0.5;0.1" dur="4.6s" '
                f'begin="{phase:.2f}s" repeatCount="indefinite"/></circle>'
            )
    return "".join(out)


def horizon(w, hy):
    """Static perspective ground: a bright horizon line, rays fanning out of
    the vanish point and depth rows spaced quadratically toward the viewer."""
    parts = [
        f'<line x1="0" y1="{hy}" x2="{w}" y2="{hy}" stroke="{CYAN}" stroke-width="1.4" opacity="0.75" filter="url(#softGlow)"/>'
    ]
    for k in range(-7, 8):
        xb = w / 2 + k * 95
        parts.append(
            f'<line x1="{w / 2:.0f}" y1="{hy}" x2="{xb:.0f}" y2="320" stroke="#1a2c50" stroke-width="1"/>'
        )
    for i in range(1, 9):
        y = hy + (i / 8) ** 2.2 * 130
        parts.append(
            f'<line x1="0" y1="{y:.1f}" x2="{w}" y2="{y:.1f}" stroke="#1a2c50" stroke-width="1"/>'
        )
    # A glowing wavefront that rolls from the horizon toward the viewer.
    parts.append(
        '<rect x="0" y="0" width="%d" height="6" fill="url(#groundFade)" opacity="0">'
        '<animate attributeName="y" values="%d;320" dur="2.8s" repeatCount="indefinite"/>'
        '<animate attributeName="height" values="3;26" dur="2.8s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.8;0" dur="2.8s" repeatCount="indefinite"/>'
        "</rect>" % (w, hy)
    )
    return "".join(parts)


def orbit(w, cx, cy):
    """A tilted orbital ring with one satellite circling it, drawn behind the
    text as a quiet piece of scenery."""
    rx, ry = 105, 34
    return f"""
  <g transform="translate({cx} {cy}) rotate(-16)" opacity="0.8">
    <ellipse rx="{rx}" ry="{ry}" fill="none" stroke="url(#orbitGrad)" stroke-width="1.4"/>
    <circle r="3.4" fill="{MINT}" filter="url(#softGlow)">
      <animateMotion dur="14s" repeatCount="indefinite" path="M {-rx} 0 a {rx} {ry} 0 1 0 {2 * rx} 0 a {rx} {ry} 0 1 0 {-2 * rx} 0"/>
    </circle>
    <circle r="1.6" cx="{rx * 0.35:.0f}" cy="{-ry * 0.6:.0f}" fill="{CYAN}" opacity="0.8">
      <animate attributeName="opacity" values="0.3;0.9;0.3" dur="5s" repeatCount="indefinite"/>
    </circle>
  </g>"""


def rocket_group():
    """A small ship flying an arc across the board with a fading exhaust trail."""
    trail = (
        '<path d="M -14 0 L -70 0" stroke="url(#flame)" stroke-width="3.2" stroke-linecap="round" opacity="0.9">'
        '<animate attributeName="stroke-width" values="3.2;4.8;3.2" dur="0.7s" repeatCount="indefinite"/></path>'
        '<circle cx="-34" cy="0" r="1.8" fill="{MINT}">'
        '<animate attributeName="opacity" values="0.9;0" dur="0.8s" repeatCount="indefinite"/></circle>'
        '<circle cx="-52" cy="-2" r="1.3" fill="{CYAN}">'
        '<animate attributeName="opacity" values="0.7;0" dur="1.1s" begin="0.3s" repeatCount="indefinite"/></circle>'
    ).format(MINT=MINT, CYAN=CYAN)
    body = (
        '<g transform="scale(1.5)">'
        '<path d="M -14 0 L -2 -6.5 L 24 0 L -2 6.5 Z" fill="#dbe7ff" filter="url(#softGlow)"/>'
        '<path d="M -2 -6.5 L 8 -12 L 12 -3.5 Z" fill="{CYAN}" opacity="0.9"/>'
        '<path d="M -2 6.5 L 8 12 L 12 3.5 Z" fill="{CYAN}" opacity="0.9"/>'
        '<circle cx="9" cy="0" r="2.8" fill="{VIOLET}"/>'
        '<path d="M 24 0 L 19 -3.4 L 19 3.4 Z" fill="{BLUE}" opacity="0.85"/>'
        "</g>"
    ).format(CYAN=CYAN, VIOLET=VIOLET, BLUE=BLUE)
    return (
        '<g opacity="0.95">'
        '<animateMotion path="M -80 168 Q 300 40 1000 96" dur="8.5s" rotate="auto" repeatCount="indefinite"/>'
        + trail
        + body
        + "</g>"
    )


def hero_svg(d):
    w, h, hy = 900, 300, 196
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="CJstate mission board">
{DEFS}
<rect width="{w}" height="{h}" fill="url(#sky)" rx="16"/>
{stars_field(w, hy)}
{horizon(w, hy)}
{orbit(w, 762, 66)}
<g font-family="{FONT_UI}">
  <text x="46" y="78" font-size="46" font-weight="700" fill="url(#nameGrad)" filter="url(#glow)" letter-spacing="3">CJSTATE</text>
  <text x="48" y="106" font-size="12.5" fill="{TEXT_DIM}" letter-spacing="4.2">BACKEND · GO INFRASTRUCTURE · K8S TOOLING · PROMETHEUS</text>

  <text x="46" y="158" font-size="54" font-weight="700" fill="{MINT}" filter="url(#glow)">
    {d["merged_prs"]}
    <animate attributeName="opacity" values="0.86;1;0.86" dur="2.6s" repeatCount="indefinite"/>
  </text>
  <rect x="48" y="170" width="150" height="2.2" rx="1" fill="{MINT}" opacity="0.55">
    <animate attributeName="opacity" values="0.3;0.8;0.3" dur="2.6s" repeatCount="indefinite"/>
  </rect>
  <text x="48" y="188" font-size="11.5" fill="{TEXT_DIM}" letter-spacing="3">MERGED PULL REQUESTS · LIVE</text>

  <text x="352" y="154" font-size="30" font-weight="600" fill="{CYAN}">{d["contributions"]}</text>
  <text x="352" y="174" font-size="10.5" fill="{TEXT_DIM}" letter-spacing="2">CONTRIBUTIONS · LAST YEAR</text>

  <text x="622" y="154" font-size="30" font-weight="600" fill="{VIOLET}">{d["merged_repos"]}</text>
  <text x="622" y="174" font-size="10.5" fill="{TEXT_DIM}" letter-spacing="2">REPOS WITH MERGED PRS</text>
</g>
{rocket_group()}
</svg>
"""


def tagline_svg():
    """Three taglines cross-fading in a loop. No blinking caret: each line
    fades in, holds, and hands over to the next."""
    w, h, dur = 700, 86, 13.5
    lines = [
        "Fixing the bugs CI never catches",
        "Go infrastructure · Kubernetes tooling · Prometheus",
        "Test-first, every time",
    ]
    parts = []
    for i, text in enumerate(lines):
        t0 = i * dur / 3
        if t0 == 0:
            values = "0;1;1;0;0"
            key_times = f"0;{0.04:.3f};{(dur / 3 - 1.1) / dur:.3f};{dur / 3 / dur:.3f};1"
        else:
            values = "0;0;1;1;0;0"
            key_times = (
                f"0;{t0 / dur:.3f};{t0 / dur + 0.04:.3f};"
                f"{(t0 + dur / 3 - 1.1) / dur:.3f};{(t0 + dur / 3) / dur:.3f};1"
            )
        parts.append(
            f'<text x="34" y="52" font-size="19" font-weight="600" fill="{CYAN}" font-family="{FONT_MONO}" opacity="0">{esc(text)}'
            f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" dur="{dur}s" repeatCount="indefinite"/></text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="taglines">
{DEFS}
<rect width="{w}" height="{h}" fill="none"/>
<text x="12" y="52" font-size="19" font-weight="600" fill="{MINT}" font-family="{FONT_MONO}">&gt;</text>
{''.join(parts)}
<line x1="12" y1="70" x2="{w - 12}" y2="70" stroke="#1b2b4a" stroke-width="1"/>
<rect x="12" y="69" width="90" height="2" rx="1" fill="url(#sweep)">
  <animate attributeName="x" values="12;{w - 102};12" dur="9s" repeatCount="indefinite"/>
</rect>
</svg>
"""


def stat_card(x, y, w, h, accent, label, value, delay):
    # Always-visible card with a breathing border glow; no entrance-delay
    # animation, which renders unreliably in static contexts.
    return f"""
  <g>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#0b1424" stroke="#223a66" stroke-width="1.2"/>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" stroke="{accent}" stroke-width="1.1" opacity="0.3">
      <animate attributeName="opacity" values="0.1;0.55;0.1" dur="3.4s" begin="{delay}s" repeatCount="indefinite"/>
    </rect>
    <rect x="{x}" y="{y}" width="3.5" height="{h}" rx="1.5" fill="{accent}" filter="url(#softGlow)">
      <animate attributeName="opacity" values="0.55;1;0.55" dur="3s" begin="{delay}s" repeatCount="indefinite"/>
    </rect>
    <text x="{x + 22}" y="{y + 42}" font-size="26" font-weight="700" fill="{accent}" filter="url(#softGlow)" font-family="{FONT_UI}">{value}</text>
    <text x="{x + 22}" y="{y + 62}" font-size="10" fill="{TEXT_DIM}" letter-spacing="2" font-family="{FONT_UI}">{esc(label.upper())}</text>
  </g>"""


def stats_svg(d):
    w, h = 900, 208
    cards = [
        (MINT, "Merged PRs · live", d["merged_prs"]),
        (CYAN, "Contributions · last year", d["contributions"]),
        (VIOLET, "Repos with merged PRs", d["merged_repos"]),
        (AMBER, "Merged this month", d["merged_month"]),
        (BLUE, "PRs in flight", d["open_prs"]),
        (MINT, "Public repos", d["repos"]),
    ]
    body = []
    cw, ch, gap = 275, 62, 18
    for i, (accent, label, value) in enumerate(cards):
        x = 24 + (i % 3) * (cw + gap)
        y = 52 + (i // 3) * (ch + gap)
        body.append(stat_card(x, y, cw, ch, accent, label, value, 0.12 * i))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Live GitHub metrics">
{DEFS}
<rect width="{w}" height="{h}" fill="url(#sky)" rx="14"/>
{stars_field(w, h, seed=11, count=40)}
<text x="24" y="32" font-size="12" font-weight="600" fill="{TEXT_DIM}" letter-spacing="3.5" font-family="{FONT_UI}">LIVE GITHUB METRICS</text>
<text x="{w - 24}" y="32" font-size="10" fill="{TEXT_DIM}" text-anchor="end" letter-spacing="1.5" font-family="{FONT_MONO}">REFRESHED {esc(d["rendered_at"])}</text>
{''.join(body)}
</svg>
"""


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = collect_data()
    boards = {
        "hero.svg": hero_svg(data),
        "typing.svg": tagline_svg(),
        "stats.svg": stats_svg(data),
    }
    for name, svg in boards.items():
        (out_dir / name).write_text(svg, encoding="utf-8", newline="\n")
        print(f"wrote {out_dir / name}")


if __name__ == "__main__":
    main()
