#!/usr/bin/env python3
"""Render the profile's metrics board SVGs from live GitHub data.

Everything shown is fetched at render time: merged/open PR counts via the
search API, the contribution calendar via GraphQL. No third-party card
services, no cached or invented numbers.

Usage:
    python tools/render_profile.py            # writes docs/metrics-*.svg
    python tools/render_profile.py --out DIR  # override output directory
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- fetching


def gh(*args: str) -> str:
    # encoding="utf-8" on purpose: gh emits UTF-8 regardless of the system
    # locale, and the default on Windows (cp936) dies on PR titles that are
    # not GBK — the exact bug class this profile talks about.
    out = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    return out.stdout


def fetch_pr_stats() -> dict:
    """Merged/open PR counts, distinct repos touched, first merge date."""
    q_merged = "author:CJstate type:pr is:merged"
    q_open = "author:CJstate type:pr is:open is:public"
    merged = json.loads(
        gh("api", f"search/issues?q={q_merged}&per_page=100")
    )
    opened = json.loads(gh("api", f"search/issues?q={q_open}&per_page=100"))
    repos = sorted(
        {item["repository_url"].rsplit("/", 2)[-2:] and item["repository_url"].split("/repos/")[-1]
         for item in merged.get("items", [])}
        | {item["repository_url"].split("/repos/")[-1]
           for item in opened.get("items", [])}
    )
    merge_dates = [
        item["closed_at"][:10]
        for item in merged.get("items", [])
        if item.get("closed_at")
    ]
    return {
        "merged": merged.get("total_count", 0),
        "open": opened.get("total_count", 0),
        "repos": len(repos),
        "first_merge": min(merge_dates) if merge_dates else None,
    }


def fetch_calendar(user: str = "CJstate") -> list[tuple[str, int]]:
    """365 days of contributions, oldest first."""
    q = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    raw = gh("api", "graphql", "-f", f"query={q}", "-f", f"login={user}")
    data = json.loads(raw)
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    return days[-371:]  # full grid worth (~53 weeks)


# ---------------------------------------------------------------- svg bits


def fmt(n: int) -> str:
    return f"{n:,}"


def esc(s: str) -> str:
    return s.replace("&", "&").replace("<", "<").replace(">", ">")


LEVELS = {
    "dark": ["#151c2e", "#16385c", "#1e5c8c", "#2b8fb3", "#3fd0b0"],
    "light": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
}


def heat_color(count: int, theme: str) -> str:
    lv = LEVELS[theme]
    if count <= 0:
        return lv[0]
    if count <= 2:
        return lv[1]
    if count <= 5:
        return lv[2]
    if count <= 9:
        return lv[3]
    return lv[4]


def render_metrics(stats: dict, days: list[tuple[str, int]], theme: str) -> str:
    dark = theme == "dark"
    bg0, bg1 = ("#0a0f1c", "#0e1830") if dark else ("#ffffff", "#f6f8fa")
    ink = "#e8eefc" if dark else "#1f2328"
    mut = "#8ea0c0" if dark else "#656d76"
    grid = "#1c2740" if dark else "#d7dde4"
    accent0, accent1 = "#6ea8fe", "#3fd0b0"

    # heatmap geometry: weeks x 7, cell 11px, gap 3
    cell, gap = 11, 3
    weeks = (len(days) + 6) // 7
    heat_w = weeks * (cell + gap)
    x0, y0 = 80, 190

    cells = []
    for i, (day, count) in enumerate(days):
        wk, dow = divmod(i, 7)
        x = x0 + wk * (cell + gap)
        y = y0 + dow * (cell + gap)
        cells.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{heat_color(count, theme)}"/>'
        )
    heat = "\n      ".join(cells)

    total_year = sum(c for _, c in days)
    first_merge = stats.get("first_merge")
    first_merge_txt = f"first upstream merge · {first_merge}" if first_merge else "upstream contributor"

    blocks = [
        (fmt(stats["merged"]), "PRs merged upstream"),
        (fmt(stats["open"]), "PRs in review"),
        (fmt(stats["repos"]), "repositories touched"),
        (fmt(total_year), "contributions · 12 mo"),
    ]
    bx, bw, bgap = 80, 236, 24
    stat_svg = []
    for i, (val, label) in enumerate(blocks):
        x = bx + i * (bw + bgap)
        stat_svg.append(
            f'''
    <text x="{x}" y="118" font-family="'Segoe UI',Helvetica,Arial,sans-serif" font-size="42" font-weight="700" fill="{accent0 if i % 2 == 0 else accent1}">{esc(val)}</text>
    <text x="{x}" y="146" font-family="'Segoe UI',Helvetica,Arial,sans-serif" font-size="13.5" letter-spacing="0.6" fill="{mut}">{esc(label.upper())}</text>'''
        )
    stats_svg = "\n   ".join(stat_svg)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="332" viewBox="0 0 1200 332" role="img" aria-label="Contribution metrics">
  <defs>
    <linearGradient id="mbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{bg0}"/><stop offset="1" stop-color="{bg1}"/>
    </linearGradient>
    <linearGradient id="mrule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{accent0}"/><stop offset="0.5" stop-color="{accent1}"/><stop offset="1" stop-color="{accent1}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="332" fill="url(#mbg)" rx="14"/>
  <rect x="80" y="42" width="46" height="4" rx="2" fill="url(#mrule)"/>
  <text x="80" y="70" font-family="'Segoe UI',Helvetica,Arial,sans-serif" font-size="14" letter-spacing="2" fill="{mut}">UPSTREAM ACTIVITY · ROLLING 12 MONTHS</text>
   {stats_svg}
  <line x1="80" y1="160" x2="1120" y2="160" stroke="{grid}" stroke-width="1"/>
      {heat}
  <text x="80" y="300" font-family="'Segoe UI',Helvetica,Arial,sans-serif" font-size="13" fill="{mut}">least ─ most · {esc(first_merge_txt)} · generated from the GitHub API, no manual numbers</text>
</svg>
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs")
    ap.add_argument("--user", default="CJstate")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    stats = fetch_pr_stats()
    days = fetch_calendar(args.user)
    for theme in ("dark", "light"):
        svg = render_metrics(stats, days, theme)
        path = out / f"metrics-{theme}.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"wrote {path} ({len(svg)} bytes)")
    print("stats:", json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print("gh failed:", e.stderr, file=sys.stderr)
        sys.exit(1)
