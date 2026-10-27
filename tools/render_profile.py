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


def render_hero(scheme: str, data: dict, motion: bool = True) -> str:
    p = PALETTES[scheme]
    stats = data["stats"]
    c = Canvas(p, 1200, 380)
    cls = (lambda name: f' class="{name}"') if motion else (lambda name: "")

    c.add(
        '<title>Jinhui Chen - upstream contributions, rendered from the GitHub API</title>'
    )

    # ---- identity, left
    c.text(56, 104, "Jinhui Chen", 54, "ink", 700, SANS, tracking=-2.4)
    c.text(56, 148, "I fix the bugs CI cannot see.", 21, "ink", 500, SANS, tracking=-0.3)

    thesis = [
        "Symlinks Git for Windows never checks out. A locale encoding that eats",
        "the file you just wrote. ANSI colour a terminal silently drops.",
    ]
    for i, line in enumerate(thesis):
        c.add(
            f'<text x="56" y="{184 + i * 21}" font-family="{SANS}" font-size="13.5" '
            f'fill="{p["body"]}">{esc(line)}</text>'
        )

    c.text(56, 246, "Go gateways", 12.5, "accent")
    c.text(56, 266, "zero-dependency Python tooling", 12.5, "accent")
    c.text(56, 286, "LLM evaluation harnesses", 12.5, "accent")

    # ---- the receipts, bottom-left, small and unembellished
    c.rule(56, 312, 660)
    c.text(
        56,
        336,
        f'{stats["merged"]} merged upstream \u00b7 {stats["repos"]} repositories '
        f'\u00b7 {stats["additions"]} lines added across {stats["files"]} files',
        12,
        "body",
    )
    c.text(56, 356, f'rendered {data["generated"][:10]} from the GitHub API', 10.5, "muted")

    # ---- oscilloscope, right
    px, py, pw, ph = 744, 56, 400, 268
    c.add(
        f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="10" '
        f'fill="{p["panel"]}" stroke="{p["line"]}"/>'
    )
    for i in range(1, 5):
        gy = py + (ph / 5) * i
        c.add(
            f'<line x1="{px + 1}" y1="{gy:.1f}" x2="{px + pw - 1}" y2="{gy:.1f}" '
            f'stroke="{p["grid"]}" stroke-width="1"/>'
        )
    for i in range(1, 7):
        gx = px + (pw / 7) * i
        c.add(
            f'<line x1="{gx:.1f}" y1="{py + 1}" x2="{gx:.1f}" y2="{py + ph - 1}" '
            f'stroke="{p["grid"]}" stroke-width="1"/>'
        )

    mid = py + ph / 2

    # Green: the shape CI reports. Red: the shape a user reports. They never
    # agree, and the distance between them is the job.
    green = (
        f"M{px + 20},{mid - 30} "
        f"C{px + 78},{mid - 30} {px + 90},{mid + 10} {px + 146},{mid + 10} "
        f"S{px + 214},{mid - 24} {px + 272},{mid - 24} "
        f"S{px + 336},{mid + 14} {px + pw - 20},{mid + 14}"
    )
    red = (
        f"M{px + 20},{mid + 30} "
        f"C{px + 72},{mid + 30} {px + 86},{mid - 20} {px + 140},{mid - 20} "
        f"S{px + 206},{mid + 40} {px + 264},{mid + 40} "
        f"S{px + 330},{mid - 44} {px + pw - 20},{mid - 44}"
    )
    for path, colour in ((green, "merged"), (red, "#E5534B")):
        stroke = p[colour] if colour in p else colour
        c.add(
            f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="1.9" '
            f'stroke-linecap="round" stroke-linejoin="round" '
            f'stroke-dasharray="5 4" stroke-dashoffset="0"{cls("flow")}/>'
        )

    # Endpoint beads on each trace: the CI dot is steady, the user dot
    # breathes, because the second one is the one that keeps changing.
    c.add(f'<circle cx="{px + pw - 20}" cy="{mid + 14}" r="3.4" fill="{p["merged"]}"/>')
    c.add(
        f'<circle cx="{px + pw - 20}" cy="{mid - 44}" r="3.4" fill="#E5534B"{cls("bead")}/>'
    )

    # The sweep is pure ornament on top of a complete picture, so it is the
    # one thing allowed to start at opacity 0.
    c.add(
        f'<rect x="{px + 20}" y="{py + 26}" width="1.5" height="{ph - 52}" '
        f'fill="{p["accent"]}" opacity="0"{cls("sweep")}/>'
    )

    c.text(px + 18, py + 24, "ci status", 10, "muted")
    c.add(f'<circle cx="{px + 82}" cy="{py + 20}" r="3" fill="{p["merged"]}"/>')
    c.text(px + pw - 18, py + 24, "a real machine", 10, "muted", anchor="end")
    c.add(f'<circle cx="{px + pw - 122}" cy="{py + 20}" r="3" fill="#E5534B"/>')
    c.text(px + 18, py + ph - 14, "the distance between these two is the work", 10, "muted")

    if motion:
        c.style(
            "@keyframes flow{to{stroke-dashoffset:-18}}"
            ".flow{animation:flow 1.15s linear infinite}"
            "@keyframes bead{0%,100%{opacity:1;r:3.4}50%{opacity:.35;r:2.4}}"
            ".bead{animation:bead 2.6s ease-in-out infinite}"
            "@keyframes sweep{0%{opacity:0;transform:translateX(0)}"
            "10%{opacity:.5}90%{opacity:.5}100%{opacity:0;"
            f"transform:translateX({pw - 42}px)}}"
            f".sweep{{animation:sweep 5.4s linear 1s infinite}}"
            "@media (prefers-reduced-motion:reduce){"
            ".flow,.bead,.sweep{animation:none}.sweep{opacity:0}}"
        )
    return c.finish()


# ---------------------------------------------------------- the metrics board


def render_metrics(scheme: str, data: dict, motion: bool = True) -> str:
    """The activity ledger: every merged pull request, one row each.

    Deliberately not a bar chart. The trailing year has eight empty months
    and a burst at the end, so a monthly histogram spends two thirds of its
    ink saying "nothing happened" -- an honest chart that argues against
    itself. The rows below are the same data stated as evidence: what landed
    where, and how much of it.
    """
    p = PALETTES[scheme]
    stats = data["stats"]
    prs = data["merged_prs"]
    c = Canvas(p, 1200, 392)
    cls = (lambda name: f' class="{name}"') if motion else (lambda name: "")

    c.add(
        "<title>Merged upstream contributions, rendered from the GitHub API</title>"
    )

    # ---- right rail: the four totals, stacked
    rail_x = 846
    c.add(
        f'<line x1="{rail_x - 34}" y1="56" x2="{rail_x - 34}" y2="336" '
        f'stroke="{p["line"]}"/>'
    )
    figures = [
        (str(stats["merged"]), "merged upstream", "merged"),
        (str(stats["additions"]), "lines added", "ink"),
        (str(stats["files"]), "files touched", "ink"),
        (str(stats["repos"]), "repositories", "accent"),
    ]
    for i, (value, label, colour) in enumerate(figures):
        y = 104 + i * 72
        c.text(rail_x, y, value, 40, colour, 700, tracking=-1.8)
        c.text(rail_x, y + 22, label, 11.5, "body")
        if i:
            c.add(
                f'<line x1="{rail_x}" y1="{y - 42}" x2="1156" y2="{y - 42}" '
                f'stroke="{p["grid"]}"/>'
            )

    # ---- left: the ledger itself
    c.text(44, 40, "merged upstream", 11, "muted")
    c.text(720, 40, "lines", 10.5, "muted", anchor="end")
    c.text(800, 40, "merged", 10.5, "muted", anchor="end")
    c.rule(44, 52, rail_x - 34)

    row_h = 23
    for i, pr in enumerate(prs[:12]):
        y = 76 + i * row_h
        base = y - 4
        # the dot: merged, so it is green and it stays green
        c.add(
            f'<circle cx="48" cy="{base}" r="2.6" fill="{p["merged"]}" '
            f'opacity="{1 - i * 0.055:.2f}"/>'
        )
        c.text(60, y, f'{pr["repo"]}', 11, "ink")
        c.text(
            60 + 7.05 * len(pr["repo"]) + 8, y, f'#{pr["number"]}', 11, "muted"
        )
        c.text(720, y, f'+{pr["additions"]}', 10.5, "merged", anchor="end")
        c.text(800, y, pr["merged_at"][5:], 10, "faint", anchor="end")

    c.rule(44, 356, rail_x - 34)
    c.text(
        44,
        374,
        f'{stats["merged"]} merged across {stats["repos"]} repositories '
        f'\u00b7 {stats["open"]} still in review \u00b7 {stats["commits"]} commits in the last year',
        10.5,
        "muted",
    )
    c.text(
        1156, 374, f'rendered {data["generated"][:10]} from the GitHub API',
        10.5, "muted", anchor="end",
    )

    if motion:
        # A pulse runs down the ledger's leading edge: it reads as a status
        # light and costs one element. Everything above is already complete
        # without it.
        c.add(
            f'<rect x="46" y="64" width="4" height="4" rx="2" fill="{p["merged"]}" '
            f'opacity="0"{cls("pulse")}/>'
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
