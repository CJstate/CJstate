#!/usr/bin/env python3
"""Render every visual on this profile from live GitHub data.

No third-party card service is involved. The SVGs and the JSON that feeds
them are regenerated straight from the GitHub REST and GraphQL APIs by
.github/workflows/profile.yml, so when a number appears on this profile it
came out of an API response on the run that drew it.

Design rule for the motion: every element's *base* attribute is its final,
fully-drawn state, and animation only replays an entrance on top of it. A
renderer that ignores animation -- a screenshot, a sanitizer that drops
<style>, an email client -- still shows a complete, correct picture. The
inverse (base at zero, real value only in the keyframe) fails to a blank
image, which is how most generated README art quietly breaks.

Usage:
    python tools/render_profile.py                  # fetch and write docs/
    python tools/render_profile.py --from FILE      # render a saved payload
    python tools/render_profile.py --out DIR
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import urllib.parse
from collections import OrderedDict
from pathlib import Path

USER = "CJstate"

# ------------------------------------------------------------------ palettes
# Two independently tuned sets. The light board is not the dark board with
# the channels inverted: a #3FB950 that reads as "merged" on graphite turns
# to mush on paper, and #5AC8FA disappears entirely.

PALETTES = {
    "dark": {
        "bg": "#0E1318",
        "panel": "#151C23",
        "line": "#232E38",
        "ink": "#EDF3F8",
        "body": "#93A7B7",
        "muted": "#6C8093",
        "faint": "#3D4A57",
        "accent": "#5AC8FA",
        "merged": "#46C46A",
        "pending": "#E8B93F",
        "grid": "#1B242C",
    },
    "light": {
        "bg": "#FCFCFB",
        "panel": "#F4F6F7",
        "line": "#DFE4E8",
        "ink": "#0E1318",
        "body": "#41535F",
        "muted": "#6C8093",
        "faint": "#AFBAC2",
        "accent": "#0A7196",
        "merged": "#17753A",
        "pending": "#8A5D00",
        "grid": "#EDF0F2",
    },
}

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


# ------------------------------------------------------------------ fetching


def gh(*args: str) -> str:
    # encoding="utf-8" is load-bearing, not habit: gh emits UTF-8 whatever
    # the system locale says, and this machine's default (cp936) raises on
    # any title that is not GBK-representable.
    proc = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8"
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"gh {' '.join(args)} failed")
    return proc.stdout


def gh_json(*args: str):
    return json.loads(gh(*args))


CALENDAR_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def search(query: str) -> dict:
    return gh_json("api", f"search/issues?q={urllib.parse.quote(query)}&per_page=100")


def repo_of(item: dict) -> str:
    return item["repository_url"].split("/repos/", 1)[-1]


def monthly(days: list[dict]) -> list[dict]:
    """Fold the contribution calendar into trailing calendar months."""
    buckets: "OrderedDict[str, int]" = OrderedDict()
    for day in days:
        buckets[day["d"][:7]] = buckets.get(day["d"][:7], 0) + day["c"]
    return [{"m": k, "c": buckets[k]} for k in list(buckets)[-12:]]


def fetch() -> dict:
    merged_items = search(f"author:{USER} type:pr is:merged").get("items", [])
    open_items = search(f"author:{USER} type:pr is:open").get("items", [])

    prs = []
    for item in merged_items:
        repo = repo_of(item)
        num = item["number"]
        detail = gh_json("api", f"repos/{repo}/pulls/{num}")
        prs.append(
            {
                "repo": repo,
                "number": num,
                "title": item["title"],
                "merged_at": (detail.get("merged_at") or "")[:10],
                "additions": detail.get("additions", 0),
                "deletions": detail.get("deletions", 0),
                "changed_files": detail.get("changed_files", 0),
                "url": item["html_url"],
            }
        )
    prs.sort(key=lambda p: p["merged_at"], reverse=True)

    open_by_repo: "OrderedDict[str, int]" = OrderedDict()
    for item in sorted(open_items, key=repo_of):
        repo = repo_of(item)
        open_by_repo[repo] = open_by_repo.get(repo, 0) + 1

    repos = sorted({p["repo"] for p in prs} | set(open_by_repo))

    cal = gh_json(
        "api", "graphql", "-f", f"query={CALENDAR_QUERY}", "-f", f"login={USER}"
    )
    collection = cal["data"]["user"]["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    days = [
        {"d": day["date"], "c": day["contributionCount"]}
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    ]

    own = gh_json("api", f"users/{USER}/repos?per_page=100&sort=pushed")
    originals = [
        {
            "name": r["name"],
            "description": r.get("description") or "",
            "language": r.get("language") or "",
            "url": r["html_url"],
            "topics": r.get("topics", []),
            "pushed_at": (r.get("pushed_at") or "")[:10],
        }
        for r in own
        if not r["fork"] and r["name"] != USER
    ]

    return {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": {
            "merged": len(prs),
            "open": len(open_items),
            "repos": len(repos),
            "commits": collection["totalCommitContributions"],
            "contributions": calendar["totalContributions"],
            "originals": len(originals),
            "additions": sum(p["additions"] for p in prs),
            "deletions": sum(p["deletions"] for p in prs),
            "files": sum(p["changed_files"] for p in prs),
        },
        "merged_prs": prs,
        "open_by_repo": open_by_repo,
        "calendar": days,
        "monthly": monthly(days),
        "originals": originals,
    }


# --------------------------------------------------------------------- svg io


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


class Canvas:
    """Collects SVG parts while resolving palette tokens at emit time."""

    def __init__(self, palette: dict, width: int, height: int, radius: int = 16):
        self.p = palette
        self.w = width
        self.h = height
        self.parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            f'font-family="{MONO}" role="img">',
            f'<rect width="{width}" height="{height}" rx="{radius}" fill="{palette["bg"]}"/>',
            f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" '
            f'rx="{radius}" fill="none" stroke="{palette["line"]}"/>',
        ]

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def text(
        self,
        x: float,
        y: float,
        body: str,
        size: float = 13,
        colour: str = "body",
        weight: int = 400,
        family: str | None = None,
        anchor: str = "start",
        tracking: float | None = None,
        opacity: float | None = None,
    ) -> None:
        attrs = [
            f'x="{x:g}"',
            f'y="{y:g}"',
            f'font-family="{family or MONO}"',
            f'font-size="{size:g}"',
            f'font-weight="{weight}"',
            f'fill="{self.p[colour]}"',
            f'text-anchor="{anchor}"',
        ]
        if tracking is not None:
            attrs.append(f'letter-spacing="{tracking:g}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity:g}"')
        self.add(f"<text {' '.join(attrs)}>{esc(body)}</text>")

    def rule(self, x1, y, x2, colour="line", width=1, dash=None) -> None:
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<line x1="{x1:g}" y1="{y:g}" x2="{x2:g}" y2="{y:g}" '
            f'stroke="{self.p[colour]}" stroke-width="{width:g}"{extra}/>'
        )

    def style(self, css: str) -> None:
        self.add(f"<style>{css}</style>")

    def finish(self) -> str:
        self.parts.append("</svg>")
        return "\n".join(self.parts)


def stagger(count: int, step: float = 0.055, base: float = 0.1) -> str:
    return "".join(f".i{n}{{animation-delay:{base + n * step:.3f}s}}" for n in range(count))


# ------------------------------------------------------------------- the hero


# ------------------------------------------------------------------- the hero

# GitHub renders README images inside a column that is about 800px wide at the
# common desktop breakpoint. A 1200px board is therefore downscaled by ~0.66 and
# every 11px label lands at 7px on screen -- legible in the source file, mush in
# the place anyone actually reads it. Both boards are drawn at 800px instead, so
# a pixel is a pixel.

W = 800


def render_hero(scheme: str, data: dict, motion: bool = True) -> str:
    p = PALETTES[scheme]
    stats = data["stats"]
    c = Canvas(p, W, 452)
    cls = (lambda name: f' class="{name}"') if motion else (lambda name: "")

    c.add(
        '<title>Jinhui Chen - upstream contributions, rendered from the GitHub API</title>'
    )

    # ---- identity
    c.text(40, 78, "Jinhui Chen", 40, "ink", 700, SANS, tracking=-1.8)
    c.text(40, 112, "I fix the bugs CI cannot see.", 17, "ink", 500, SANS, tracking=-0.2)

    thesis = [
        "Symlinks Git for Windows never checks out. A locale encoding that eats",
        "the file you just wrote. ANSI colour a terminal silently drops.",
    ]
    for i, line in enumerate(thesis):
        c.add(
            f'<text x="40" y="{144 + i * 20}" font-family="{SANS}" font-size="12.5" '
            f'fill="{p["body"]}">{esc(line)}</text>'
        )

    # ---- the oscilloscope: the whole thesis in one picture
    px, py, pw, ph = 40, 186, W - 80, 150
    c.add(
        f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="10" '
        f'fill="{p["panel"]}" stroke="{p["line"]}"/>'
    )
    for i in range(1, 4):
        gy = py + (ph / 4) * i
        c.add(
            f'<line x1="{px + 1}" y1="{gy:.1f}" x2="{px + pw - 1}" y2="{gy:.1f}" '
            f'stroke="{p["grid"]}" stroke-width="1"/>'
        )
    for i in range(1, 9):
        gx = px + (pw / 9) * i
        c.add(
            f'<line x1="{gx:.1f}" y1="{py + 1}" x2="{gx:.1f}" y2="{py + ph - 1}" '
            f'stroke="{p["grid"]}" stroke-width="1"/>'
        )

    mid = py + ph / 2 + 6

    # Green: the shape CI reports. Red: the shape a user reports. They never
    # agree, and the distance between them is the job.
    green = (
        f"M{px + 22},{mid - 22} "
        f"C{px + 96},{mid - 22} {px + 112},{mid + 8} {px + 186},{mid + 8} "
        f"S{px + 268},{mid - 18} {px + 344},{mid - 18} "
        f"S{px + 430},{mid + 12} {px + pw - 26},{mid + 12}"
    )
    red = (
        f"M{px + 22},{mid + 24} "
        f"C{px + 92},{mid + 24} {px + 110},{mid - 16} {px + 180},{mid - 16} "
        f"S{px + 262},{mid + 30} {px + 338},{mid + 30} "
        f"S{px + 424},{mid - 34} {px + pw - 26},{mid - 34}"
    )
    for path, colour in ((green, "merged"), (red, "#E5534B")):
        stroke = p[colour] if colour in p else colour
        c.add(
            f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="1.9" '
            f'stroke-linecap="round" stroke-linejoin="round" '
            f'stroke-dasharray="5 4" stroke-dashoffset="0"{cls("flow")}/>'
        )

    c.add(f'<circle cx="{px + pw - 26}" cy="{mid + 12}" r="3.4" fill="{p["merged"]}"/>')
    c.add(
        f'<circle cx="{px + pw - 26}" cy="{mid - 34}" r="3.4" fill="#E5534B"{cls("bead")}/>'
    )

    # Pure ornament, so it is the one element allowed to start invisible.
    c.add(
        f'<rect x="{px + 22}" y="{py + 30}" width="1.5" height="{ph - 60}" '
        f'fill="{p["accent"]}" opacity="0"{cls("sweep")}/>'
    )

    c.text(px + 14, py + 22, "ci status", 10.5, "muted")
    c.add(f'<circle cx="{px + 78}" cy="{py + 18}" r="3" fill="{p["merged"]}"/>')
    c.text(px + pw - 14, py + 22, "a real machine", 10.5, "muted", anchor="end")
    c.add(f'<circle cx="{px + pw - 116}" cy="{py + 18}" r="3" fill="#E5534B"/>')
    c.text(px + 14, py + ph - 12, "the distance between these two is the work", 10.5, "muted")

    # ---- the receipts, stated plainly
    c.rule(40, 358, W - 40)
    c.text(
        40,
        380,
        f'{stats["merged"]} merged upstream \u00b7 {stats["repos"]} repositories '
        f'\u00b7 {stats["additions"]} lines added across {stats["files"]} files',
        12,
        "body",
    )
    c.text(
        40, 404, "Go gateways  \u00b7  zero-dependency Python tooling  \u00b7  "
                 "LLM evaluation harnesses",
        12, "accent",
    )
    c.text(40, 428, f'rendered {data["generated"][:10]} from the GitHub API', 10.5, "muted")

    if motion:
        c.style(
            "@keyframes flow{to{stroke-dashoffset:-18}}"
            ".flow{animation:flow 1.15s linear infinite}"
            "@keyframes bead{0%,100%{opacity:1;r:3.4}50%{opacity:.35;r:2.4}}"
            ".bead{animation:bead 2.6s ease-in-out infinite}"
            "@keyframes sweep{0%{opacity:0;transform:translateX(0)}"
            "10%{opacity:.5}90%{opacity:.5}100%{opacity:0;"
            f"transform:translateX({pw - 48}px)}}"
            f".sweep{{animation:sweep 5.4s linear 1s infinite}}"
            "@media (prefers-reduced-motion:reduce){"
            ".flow,.bead,.sweep{animation:none}.sweep{opacity:0}}"
        )
    return c.finish()


# ---------------------------------------------------------- the metrics board


def render_metrics(scheme: str, data: dict, motion: bool = True) -> str:
    """The activity ledger: every merged pull request, one row each.

    Deliberately not a bar chart. The trailing year has eight empty months and
    a burst at the end, so a monthly histogram spends two thirds of its ink
    saying "nothing happened" -- an honest chart that argues against itself.
    The rows below are the same data stated as evidence: what landed where, and
    how much of it.
    """
    p = PALETTES[scheme]
    stats = data["stats"]
    prs = data["merged_prs"]

    row_h = 24
    top = 62
    body_h = row_h * 12
    rail_y = top + body_h + 30
    h = rail_y + 96
    c = Canvas(p, W, h)
    cls = (lambda name: f' class="{name}"') if motion else (lambda name: "")

    c.add(
        "<title>Merged upstream contributions, rendered from the GitHub API</title>"
    )

    # ---- the ledger: columns are named once, then never repeated
    col_repo, col_lines, col_date = 40, W - 132, W - 40
    c.text(col_repo, 40, "merged upstream", 10.5, "muted")
    c.text(col_lines, 40, "lines", 10.5, "muted", anchor="end")
    c.text(col_date, 40, "merged", 10.5, "muted", anchor="end")
    c.rule(40, 50, W - 40)

    for i, pr in enumerate(prs[:12]):
        y = top + 14 + i * row_h
        c.add(
            f'<circle cx="{col_repo + 4}" cy="{y - 4}" r="2.8" fill="{p["merged"]}" '
            f'opacity="{1 - i * 0.055:.2f}"/>'
        )
        c.text(col_repo + 16, y, f'{pr["repo"]}', 11.5, "ink")
        c.text(
            col_repo + 16 + 7.35 * len(pr["repo"]) + 9, y, f'#{pr["number"]}',
            11.5, "muted",
        )
        c.text(col_lines, y, f'+{pr["additions"]}', 11, "merged", anchor="end")
        c.text(col_date, y, pr["merged_at"][5:], 11, "faint", anchor="end")

    # ---- the totals, in one row under the ledger
    c.rule(40, rail_y - 14, W - 40)
    figures = [
        (str(stats["merged"]), "merged", "merged"),
        (str(stats["additions"]), "lines added", "ink"),
        (str(stats["files"]), "files touched", "ink"),
        (str(stats["repos"]), "repositories", "accent"),
    ]
    step = (W - 80) / 4
    for i, (value, label, colour) in enumerate(figures):
        x = 40 + i * step
        c.text(x, rail_y + 34, value, 34, colour, 700, tracking=-1.4)
        c.text(x, rail_y + 56, label, 11, "body")
        if i:
            c.add(
                f'<line x1="{x - 20:g}" y1="{rail_y + 4}" x2="{x - 20:g}" '
                f'y2="{rail_y + 62}" stroke="{p["line"]}"/>'
            )

    c.text(
        40,
        h - 14,
        f'{stats["open"]} still in review \u00b7 {stats["commits"]} commits in the last year',
        10.5,
        "muted",
    )
    c.text(
        W - 40, h - 14, f'rendered {data["generated"][:10]} from the GitHub API',
        10.5, "muted", anchor="end",
    )

    if motion:
        # A pulse runs down the ledger's leading edge: it reads as a status
        # light and costs one element. Everything above is already complete
        # without it.
        c.add(
            f'<rect x="{col_repo + 2}" y="{top}" width="4" height="4" rx="2" '
            f'fill="{p["merged"]}" opacity="0"{cls("pulse")}/>'
        )
        c.style(
            "@keyframes pulse{0%{opacity:0;transform:translateY(0)}"
            "10%{opacity:.9}90%{opacity:.9}100%{opacity:0;"
            f"transform:translateY({row_h * 11}px)}}"
            f".pulse{{animation:pulse 7s cubic-bezier(.45,0,.55,1) .8s infinite}}"
            "@media (prefers-reduced-motion:reduce){.pulse{animation:none}}"
        )
    return c.finish()


# ---------------------------------------------------------------------- main


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs")
    parser.add_argument(
        "--from", dest="source", default=None,
        help="render from a saved payload instead of calling the API",
    )
    parser.add_argument(
        "--static", action="store_true",
        help="omit animation so the output can be checked as a still image",
    )
    args = parser.parse_args()

    out = Path(args.out)
    (out / "data").mkdir(parents=True, exist_ok=True)

    if args.source:
        data = json.loads(Path(args.source).read_text(encoding="utf-8"))
    else:
        data = fetch()

    motion = not args.static
    (out / "data" / "live.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for scheme in ("dark", "light"):
        (out / f"hero-{scheme}.svg").write_text(
            render_hero(scheme, data, motion), encoding="utf-8"
        )
        (out / f"metrics-{scheme}.svg").write_text(
            render_metrics(scheme, data, motion), encoding="utf-8"
        )

    s = data["stats"]
    print(
        f"rendered: {s['merged']} merged, {s['open']} open, {s['repos']} repos, "
        f"{s['commits']} commits, {s['additions']} lines added"
    )


if __name__ == "__main__":
    main()
