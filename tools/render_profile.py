#!/usr/bin/env python3
"""Draw the three boards on this profile from live GitHub data.

Everything here is regenerated from the GitHub API, so a number that appears on
the page came out of an API response on the run that drew it.

One rule governs the motion: an element's *base* attribute is its final, drawn
state, and a keyframe only replays the entrance on top of it. A renderer that
ignores animation -- a screenshot, a sanitizer that drops <style>, a mail client
-- still gets a complete, correct picture. The inverse (base at zero, real value
only inside the keyframe) fails to a blank image, which is how most generated
README art quietly breaks.

Usage:
    python tools/render_profile.py                  # fetch and write docs/
    python tools/render_profile.py --from FILE      # render a saved payload
    python tools/render_profile.py --out DIR
    python tools/render_profile.py --static         # no animation, for review
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import subprocess
import sys
import urllib.parse
from collections import OrderedDict
from pathlib import Path

USER = "CJstate"

# ------------------------------------------------------------------ palettes
# Two independently tuned sets. The light board is not the dark board with the
# channels inverted: a #3FB950 that reads as "merged" on graphite turns to mush
# on paper, and #5AC8FA disappears entirely.

PALETTES = {
    "dark": {
        "bg": "#0D1117",
        "panel": "#141B22",
        "line": "#222D38",
        "ink": "#EEF4F9",
        "body": "#94A8B8",
        "muted": "#6B8093",
        "faint": "#3C4956",
        "accent": "#5AC8FA",
        "merged": "#46C46A",
        "warm": "#E8B93F",
        "grid": "#1A232C",
        "hot": "#E5534B",
    },
    "light": {
        "bg": "#FFFFFF",
        "panel": "#F3F6F7",
        "line": "#DDE3E7",
        "ink": "#0D1117",
        "body": "#405260",
        "muted": "#6B8093",
        "faint": "#AEB9C1",
        "accent": "#0A7196",
        "merged": "#17753A",
        "warm": "#8A5D00",
        "grid": "#EAEEF0",
        "hot": "#B3301F",
    },
}

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


# ------------------------------------------------------------------ fetching


def gh(*args: str) -> str:
    # encoding="utf-8" is load-bearing, not habit: gh emits UTF-8 whatever the
    # system locale says, and this machine's default (cp936) raises on any
    # title that is not GBK-representable.
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


def count_files(full_name: str, branch: str) -> int:
    """How many files are actually in the repository.

    A star count on a two-week-old repository is a score of zero; the size of
    the thing is a fact. The tree endpoint returns every path in one call.
    """
    try:
        tree = gh_json("api", f"repos/{full_name}/git/trees/{branch}?recursive=1")
    except Exception:
        return 0
    return sum(1 for node in tree.get("tree", []) if node.get("type") == "blob")


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

    open_prs = [
        {
            "repo": repo_of(item),
            "number": item["number"],
            "title": item["title"],
            "url": item["html_url"],
            "created_at": (item.get("created_at") or "")[:10],
        }
        for item in open_items
    ]

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
            "size": r.get("size", 0),
            "files": count_files(r["full_name"], r.get("default_branch") or "main"),
        }
        for r in own
        if not r["fork"] and r["name"] != USER
    ]
    originals.sort(key=lambda r: r["pushed_at"], reverse=True)

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
        "open_prs": open_prs,
        "open_by_repo": open_by_repo,
        "calendar": days,
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
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


class Canvas:
    """Collects SVG parts while resolving palette tokens at emit time."""

    def __init__(self, palette: dict, width: int, height: int, radius: int = 0):
        # The background is the exact colour GitHub paints behind a README, and
        # there is no border: a framed card inside GitHub's own card is what
        # makes a profile read as three boxes stacked on top of each other.
        # Seamless, the type and the plots simply sit on the page.
        self.p = palette
        self.w = width
        self.h = height
        self.parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            f'font-family="{MONO}" role="img">',
            f'<rect width="{width}" height="{height}" fill="{palette["bg"]}"/>',
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
        cls: str | None = None,
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
        if cls:
            attrs.append(f'class="{cls}"')
        self.add(f"<text {' '.join(attrs)}>{esc(body)}</text>")

    def chars(
        self,
        x: float,
        y: float,
        body: str,
        size: float,
        colour: str,
        weight: int,
        family: str,
        tracking: float,
        step: float = 0.028,
        cls: str = "g",
    ) -> None:
        """A line of type whose glyphs settle in one at a time.

        The animation moves colour only, never visibility: the base fill is the
        final colour and every keyframe starts on a colour that is still legible.
        Strip the <style> element and the whole word is simply there, correct.
        """
        spans = []
        for i, ch in enumerate(body):
            shown = "\u00a0" if ch == " " else esc(ch)
            spans.append(
                f'<tspan class="{cls}" style="animation-delay:{i * step:.3f}s">{shown}</tspan>'
            )
        self.add(
            f'<text x="{x:g}" y="{y:g}" font-family="{family}" font-size="{size:g}" '
            f'font-weight="{weight}" fill="{self.p[colour]}" '
            f'letter-spacing="{tracking:g}">{"".join(spans)}</text>'
        )

    def rule(self, x1, y, x2, colour="line", width=1, dash=None, cls=None) -> None:
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        klass = f' class="{cls}"' if cls else ""
        self.add(
            f'<line x1="{x1:g}" y1="{y:g}" x2="{x2:g}" y2="{y:g}" '
            f'stroke="{self.p[colour]}" stroke-width="{width:g}"{extra}{klass}/>'
        )

    def label(self, x, y, body, anchor="start") -> None:
        """The small tracked-out caps used to name a section."""
        self.text(x, y, body.upper(), 9.5, "muted", 500, MONO,
                  anchor=anchor, tracking=1.6)

    def field(self, x, y, w, h, bars=64, step=0.030) -> None:
        """A dense stand of hairlines under a fixed envelope.

        Drawn the way a plotter would draw it: the geometry you see is the
        finished shape, and the animation only lets the stand shimmer. It
        carries no information -- it is texture, so the two traces over it have
        something to be read against. The taper is what stops it reading as a
        barcode: tall through the middle, absent at both ends.
        """
        for i in range(bars):
            t = i / (bars - 1)
            env = abs(math.sin(t * 6.9)) * 0.58 + abs(math.sin(t * 17.3 + 0.7)) * 0.42
            taper = math.sin(math.pi * t) ** 0.55
            height = h * (0.06 + 0.94 * env ** 1.7) * taper
            bx = x + t * w
            self.add(
                f'<line x1="{bx:.1f}" y1="{y + h / 2 - height / 2:.1f}" '
                f'x2="{bx:.1f}" y2="{y + h / 2 + height / 2:.1f}" '
                f'stroke="{self.p["line"]}" stroke-width="1.1" '
                f'stroke-linecap="round" class="wave" '
                f'style="animation-delay:{i * step:.3f}s"/>'
            )

    def style(self, css: str) -> None:
        self.add(f"<style>{css}</style>")

    def finish(self) -> str:
        self.parts.append("</svg>")
        return "\n".join(self.parts)


# GitHub renders README images inside a column about 800px wide at the common
# desktop breakpoint. A 1200px board is therefore downscaled by ~0.66 and every
# 11px label lands at 7px on screen -- legible in the source file, mush in the
# place anyone actually reads it. Every board is drawn at 800px instead, so a
# pixel is a pixel.

W = 800
PAD = 40


def _reduce_motion(names: str) -> str:
    return (
        "@media (prefers-reduced-motion:reduce){"
        + ",".join("." + n for n in names.split())
        + "{animation:none!important}}"
    )


# --------------------------------------------------------------------- intro


def render_intro(scheme: str, data: dict, motion: bool = True) -> str:
    """Who I am, in the fewest words that still say something."""
    p = PALETTES[scheme]
    stats = data["stats"]
    c = Canvas(p, W, 526)
    k = (lambda name: f' class="{name}"') if motion else (lambda name: "")

    c.add("<title>CJstate</title>")

    c.chars(PAD, 80, "CJstate", 44, "ink", 700, SANS, -1.7)

    c.rule(PAD, 104, W - PAD, "line", 1, cls=("draw" if motion else None))

    c.text(PAD, 136, "Backend engineer · LLM tooling.", 19, "ink", 600, SANS, tracking=-0.3)
    c.chars(PAD, 162, "I look for the failures that leave no trace.", 19, "accent",
            500, SANS, -0.3, step=0.014, cls="t")

    prose = [
        "Most of what I do is read a system until it tells me how it breaks. The bugs I",
        "end up fixing are the quiet ones: a symlink Git for Windows checks out as a",
        "16-byte text file, a locale encoding that eats the file you just wrote, a secret",
        "a tool promises to redact and then writes to disk anyway. None of them can fail",
        "in CI, because CI is the machine that already has what the user does not.",
    ]
    for i, line in enumerate(prose):
        c.add(
            f'<text x="{PAD}" y="{194 + i * 20}" font-family="{MONO}" font-size="12.5" '
            f'fill="{p["body"]}">{esc(line)}</text>'
        )

    # ---- the signal: two traces that never agree, over a stand of hairlines
    px, py, pw, ph = PAD, 310, W - 2 * PAD, 124
    mid = py + ph / 2

    c.field(px, py, pw, ph)

    # A reference axis and a tick row: without them the traces are a squiggle,
    # with them they are a plot.
    c.rule(px, mid, px + pw, "line", 1)
    for i in range(13):
        tx = px + (pw / 12) * i
        c.add(
            f'<line x1="{tx:.1f}" y1="{py + ph + 4}" x2="{tx:.1f}" '
            f'y2="{py + ph + 9}" stroke="{p["line"]}" stroke-width="1"/>'
        )

    def trace(freq, phase, amp, n=84):
        pts = []
        for i in range(n + 1):
            t = i / n
            v = (math.sin(t * freq + phase) * 0.62
                 + math.sin(t * freq * 2.7 + phase * 1.9) * 0.38)
            pts.append(f"{px + t * pw:.1f},{mid + v * amp:.1f}")
        return "M" + " L".join(pts)

    for freq, phase, amp, colour in (
        (7.4, 0.4, 30, p["merged"]),
        (9.1, 2.3, 25, p["hot"]),
    ):
        c.add(
            f'<path d="{trace(freq, phase, amp)}" fill="none" stroke="{colour}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'stroke-dasharray="7 5"{k("flow")}/>'
        )

    c.rule(px, py + ph + 10, px + pw, "line", 1)

    c.text(px, py - 12, "green build", 9.5, "muted")
    c.add(f'<circle cx="{px + 74}" cy="{py - 15.5}" r="2.6" fill="{p["merged"]}"/>')
    c.text(px + pw, py - 12, "a real machine", 9.5, "muted", anchor="end")
    c.add(f'<circle cx="{px + pw - 84}" cy="{py - 15.5}" r="2.6" fill="{p["hot"]}"/>')

    # Ornament only, so this is the one element allowed to start invisible.
    c.add(
        f'<rect x="{px + 12}" y="{py + 14}" width="1.4" height="{ph - 28}" '
        f'fill="{p["accent"]}" opacity="0"{k("sweep")}/>'
    )

    c.rule(PAD, 478, W - PAD, "line", 1)
    c.text(
        PAD, 500,
        f'{stats["merged"]} merged \u00b7 {stats["open"]} open \u00b7 {stats["repos"]} upstream repos '
        f'\u00b7 {stats["contributions"]} contributions in 12 months',
        11, "body",
    )
    c.text(W - PAD, 500, data["generated"][:10], 10.5, "faint", anchor="end")

    if motion:
        c.style(
            "@keyframes g{from{fill:" + p["accent"] + "}to{fill:" + p["ink"] + "}}"
            ".g{animation:g .62s cubic-bezier(.22,.7,.3,1) both}"
            "@keyframes t{from{fill:" + p["ink"] + "}to{fill:" + p["accent"] + "}}"
            ".t{animation:t .7s cubic-bezier(.22,.7,.3,1) both}"
            "@keyframes draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
            ".draw{transform-origin:left center;animation:draw .9s cubic-bezier(.5,0,.2,1) .18s both}"
            "@keyframes flow{to{stroke-dashoffset:-18}}"
            ".flow{animation:flow 1.2s linear infinite}"
            "@keyframes bead{0%,100%{opacity:1;r:3.2}50%{opacity:.3;r:2.2}}"
            ".bead{animation:bead 2.8s ease-in-out infinite}"
            "@keyframes sweep{0%{opacity:0;transform:translateX(0)}"
            "12%{opacity:.45}88%{opacity:.45}100%{opacity:0;"
            f"transform:translateX({pw - 48}px)}}"
            ".sweep{animation:sweep 6s linear 1.2s infinite}"
            "@keyframes shimmer{0%,100%{opacity:.42}50%{opacity:1}}"
            ".wave{animation:shimmer 3.6s ease-in-out infinite}"
            + _reduce_motion("g t draw flow bead sweep wave")
        )
    return c.finish()


# ------------------------------------------------------------------ projects


PROJECT_NOTES = {
    "hui-harness": [
        "A coding agent you can replay. Every tool call, model reply and policy",
        "decision lands in a hash-chained log, so a run is verified, not trusted.",
    ],
    "llm-eval-gate": [
        "A CI gate that fails only on a real regression. Relative thresholds and",
        "stderr-aware noise bands over lm-evaluation-harness, so a two-point",
        "wobble inside the error bar pages nobody.",
    ],
}

# Repository names are long enough to collide in a chart gutter, so the two
# that overflow get a short form used only under the bars.
REPO_LABELS = {
    "Mihirajmera/agent-access-review": "agent-access",
    "k8sgpt-ai/k8sgpt": "k8sgpt",
    "k8sgpt-ai/k8sgpt-operator": "k8sgpt-op",
    "DependencyTrack/dependency-track": "dep-track",
}


def render_projects(scheme: str, data: dict, motion: bool = True) -> str:
    """The two things I built, with the numbers that describe them."""
    p = PALETTES[scheme]
    originals = data["originals"][:2]
    c = Canvas(p, W, 372)
    k = (lambda name: f' class="{name}"') if motion else (lambda name: "")

    c.add("<title>Selected work</title>")
    c.label(PAD, 40, "selected work")
    c.rule(PAD, 50, W - PAD, "line", 1, cls=("draw" if motion else None))

    for i, repo in enumerate(originals):
        top = 78 + i * 148
        notes = PROJECT_NOTES.get(repo["name"])
        if not notes:
            desc = repo["description"] or ""
            notes = [desc[j : j + 74] for j in range(0, len(desc), 74)] or [""]

        # A rail on the left that fills downward, one block at a time.
        c.add(
            f'<rect x="{PAD}" y="{top - 14}" width="2" height="{118}" rx="1" '
            f'fill="{p["accent"]}" opacity=".55"'
            + (f' class="rail r{i}"' if motion else "")
            + "/>"
        )
        c.text(PAD + 20, top, repo["name"], 21, "ink", 600, SANS, tracking=-0.4)
        c.text(W - PAD, top - 2, repo["language"].lower() or "code", 11.5, "faint",
               anchor="end")

        for j, line in enumerate(notes):
            c.text(PAD + 20, top + 24 + j * 18, line, 11.8, "body")

        # Facts sit on one line, each a number over its own label. Star counts
        # are deliberately absent: two honest numbers about the code say more
        # than a popularity score that is still zero.
        facts = [
            (f'{repo["files"]}', "files"),
            (f'{repo["size"]}', "kb"),
            (repo["pushed_at"][:7], "last push"),
        ]
        fx = PAD + 20
        for value, name in facts:
            c.text(fx, top + 96, value, 15, "ink", 600, SANS, tracking=-0.3)
            c.text(fx, top + 112, name, 9.5, "muted", tracking=0.9)
            fx += 78

        if i == 0:
            c.rule(PAD + 20, top + 130, W - PAD, "line", 1)

    c.rule(PAD, 344, W - PAD, "line", 1)
    c.text(PAD, 364,
           "Both are stdlib Python. Both exist because a green build told me nothing.",
           11, "body")

    if motion:
        c.style(
            "@keyframes g{from{opacity:0;fill:" + p["accent"] + "}to{opacity:1}}"
            "@keyframes draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
            ".draw{transform-origin:left center;animation:draw .9s cubic-bezier(.5,0,.2,1) .15s both}"
            "@keyframes rail{from{transform:scaleY(0)}to{transform:scaleY(1)}}"
            ".rail{transform-origin:top center;animation:rail .7s cubic-bezier(.5,0,.2,1) both}"
            ".r0{animation-delay:.35s}.r1{animation-delay:.62s}"
            + _reduce_motion("draw rail")
        )
    return c.finish()


# ------------------------------------------------------------- contributions


def render_contributions(scheme: str, data: dict, motion: bool = True) -> str:
    """What landed upstream, newest first, plus the year it happened in."""
    p = PALETTES[scheme]
    stats = data["stats"]
    prs = data["merged_prs"]

    # Geometry first, canvas second: the board is exactly as tall as the rows it
    # has, so the ledger and the total underneath can never disagree.
    head, row_h = 158, 23
    top = head + 26
    shown = prs[:20]
    ribbon_top = top + len(shown) * row_h + 24
    base = ribbon_top + 74
    c = Canvas(p, W, base + 98)
    k = (lambda name: f' class="{name}"') if motion else (lambda name: "")

    c.add("<title>Merged upstream</title>")
    c.label(PAD, 40, "merged upstream")
    c.rule(PAD, 50, W - PAD, "line", 1, cls=("draw" if motion else None))

    # The newest one gets a line of its own: a list is easier to trust when the
    # first entry is spelled out rather than abbreviated to fit a column.
    if prs:
        latest = prs[0]
        c.text(PAD, 78, "latest", 9.5, "merged", 500, tracking=1.4)
        c.text(PAD, 100, clip(latest["title"], 88), 13, "ink", 500, SANS,
               tracking=-0.1)
        c.text(PAD, 120, f'{latest["repo"]}  #{latest["number"]}  '
                         f'+{latest["additions"]} / -{latest["deletions"]}  '
                         f'{latest["merged_at"]}', 10.5, "muted")

    # Fixed columns, not measured text: a repo name is user data and its width
    # is not knowable here, so the number gets its own gutter.
    col_repo, col_num, col_lines, col_date = PAD + 16, 476, W - 148, W - PAD
    c.text(col_repo, head, "repository", 9.5, "muted", tracking=1.2)
    c.text(col_num, head, "pr", 9.5, "muted", tracking=1.2)
    c.text(col_lines, head, "lines", 9.5, "muted", anchor="end", tracking=1.2)
    c.text(col_date, head, "merged", 9.5, "muted", anchor="end", tracking=1.2)
    c.rule(PAD, head + 10, W - PAD, "line", 1)

    for i, pr in enumerate(shown):
        y = top + i * row_h
        c.add(
            f'<circle cx="{PAD + 4}" cy="{y - 4}" r="2.6" fill="{p["merged"]}" '
            f'opacity="{1 - i * 0.05:.2f}"/>'
        )
        c.text(col_repo, y, clip(pr["repo"], 46), 11.5, "ink")
        c.text(col_num, y, f'#{pr["number"]}', 11, "muted")
        c.text(col_lines, y,
               f'+{pr["additions"]}' if pr["additions"] or pr["deletions"] else '\u2014',
               11, "merged", anchor="end")
        c.text(col_date, y, pr["merged_at"][5:], 10.5, "faint", anchor="end")

    # ---- where the lines landed, one column per repository
    c.rule(PAD, ribbon_top - 12, W - PAD, "line", 1)
    c.text(PAD, ribbon_top + 8, "where the lines landed", 9.5, "muted",
           tracking=1.2)

    spread: dict[str, int] = {}
    for pr in prs:
        spread[pr["repo"]] = spread.get(pr["repo"], 0) + pr["additions"]
    columns = sorted(spread.items(), key=lambda kv: -kv[1])[:8]
    peak = max((v for _, v in columns), default=1) or 1
    slot = (W - 2 * PAD) / max(len(columns), 1)
    bar_w = 34
    for i, (repo, lines) in enumerate(columns):
        x = PAD + i * slot + (slot - bar_w) / 2
        hgt = 6 + (lines / peak) * 42
        c.add(
            f'<rect x="{x:.1f}" y="{base - hgt:.1f}" width="{bar_w}" '
            f'height="{hgt:.1f}" rx="2" fill="{p["merged"]}" opacity=".82"'
            + (f' class="col c{i}"' if motion else "")
            + "/>"
        )
        c.text(x + bar_w / 2, base - hgt - 7, str(lines), 10, "body", 500,
               anchor="middle")
        c.text(x + bar_w / 2, base + 15, clip(REPO_LABELS.get(repo, repo.split("/")[-1]), 15), 9,
               "muted", anchor="middle")

    c.rule(PAD, base + 34, W - PAD, "line", 1)
    distinct = len({pr["repo"] for pr in prs})
    figures = [
        (str(stats["merged"]), "merged"),
        (str(stats["additions"]), "lines added"),
        (str(stats["files"]), "files touched"),
        (str(distinct), "upstream repos"),
    ]
    step = (W - 2 * PAD) / 4
    for i, (value, label) in enumerate(figures):
        x = PAD + i * step
        c.text(x, base + 66, value, 26, "ink", 600, SANS, tracking=-1.0)
        c.text(x, base + 84, label, 10, "muted", tracking=0.8)

    if motion:
        # A pulse walks the ledger's leading edge: it reads as a status light and
        # costs one element. Everything above is already complete without it.
        c.add(
            f'<rect x="{PAD + 2}" y="{top - 8}" width="4" height="4" rx="2" '
            f'fill="{p["merged"]}" opacity="0"{k("pulse")}/>'
        )
        c.style(
            "@keyframes draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
            ".draw{transform-origin:left center;animation:draw .9s cubic-bezier(.5,0,.2,1) .15s both}"
            "@keyframes pulse{0%{opacity:0;transform:translateY(0)}"
            "8%{opacity:.9}92%{opacity:.9}100%{opacity:0;"
            f"transform:translateY({row_h * 11}px)}}"
            ".pulse{animation:pulse 7.5s cubic-bezier(.45,0,.55,1) .9s infinite}"
            + _reduce_motion("draw pulse")
        )
    return c.finish()


# -------------------------------------------------------------------- readme

# Everything below is judgement, not measurement: the tables are built from the
# same live payload as the boards, and a PR that is not in the payload cannot
# appear.  A note that no longer has a matching merged/open PR is simply
# skipped, so merging is the only way a row can move from one table to the
# other.

MERGED_NOTES = {
    "k8sgpt-ai/k8sgpt#1851": (
        "Pin `filepath-securejoin` to v0.4.1 to unblock the License Compliance gate."
    ),
    "k8sgpt-ai/k8sgpt#1848": (
        "Assert the `EnsureDirExists` failure portably instead of relying on Unix paths."
    ),
    "syncronix-labs/aegora#52": (
        "Evict the least recently used entry when the cache reaches capacity."
    ),
    "syncronix-labs/aegora#50": (
        "Include the request ID in gateway-generated JSON errors."
    ),
    "k8sgpt-ai/k8sgpt#1841": (
        "Add direct in-process tests for the server-mode analyze handler."
    ),
    "Mihirajmera/agent-access-review#20": (
        "Classify sqlite, brave-search and gdrive MCP servers in the catalog."
    ),
    "Mihirajmera/agent-access-review#19": (
        "Add `--format json` to `scan` for machine-readable findings."
    ),
    "pranshuparmar/witr#245": (
        "Make `TestDetectGitInfo` hermetic against Git repositories above the temp dir."
    ),
    "syncronix-labs/aegora#19": "Add a `--version` flag to the gateway CLI.",
    "bmf-san/ggc#542": "Make the config and command tests pass on Windows.",
    "bmf-san/ggc#541": "Replace Unix-only exec mocks in the git tests with a helper process.",
    "bmf-san/ggc#540": "Make the config, interactive and history tests pass on Windows.",
    "k8sgpt-ai/k8sgpt-operator#855": (
        "Add tolerations to the K8sGPT CRD and chart so the controller can run on "
        "tainted nodes."
    ),
    "pranshuparmar/witr#242": (
        "Root `main.go` was a tracked symlink; Git for Windows checks it out as a "
        "16-byte text file, so `go build` fails on a real clone while CI stays green. "
        "Replaced it with a real entry point and added a lint guard."
    ),
    "pranshuparmar/witr#239": (
        "`--help` silently lost its color legend on terminals without bright ANSI; "
        "fall back by terminal capability instead."
    ),
    "nvm-sh/nvm#3915": (
        "`nvm --help` rendered the set-colors legend as plain text; apply the same "
        "color variables inside the help branch."
    ),
    "DependencyTrack/dependency-track#7096": (
        "README CI badges pointed at a retired branch and 404'd; point them at `main`."
    ),
}

OPEN_HIGHLIGHTS = [
    (
        "syncronix-labs/aegora#68",
        "Optional per-route `timeout` bounding the whole outbound exchange, "
        "including the response body; negative values fail config validation.",
    ),
    (
        "huggingface/accelerate#4360",
        "`debug_launcher` cannot start on Windows: `fork`, `NamedTemporaryFile` and a "
        "hard-coded `lo` interface are all Unix-only assumptions.",
    ),
    (
        "EleutherAI/lm-evaluation-harness#4384",
        "Run the trailing partial chunk in `bootstrap_stderr` instead of dropping it.",
    ),
    (
        "mlflow/mlflow#26206",
        "Artifact images were force-scaled and blurred; size them to the container width.",
    ),
    (
        "k8sgpt-ai/k8sgpt#1845",
        "Mute known findings through an exclusions config key; prints the finding hash "
        "users paste into the config (approved).",
    ),
    (
        "simonw/llm#1737",
        "Templates were written as UTF-8 but read with the locale encoding; use UTF-8 "
        "first with a locale fallback and add regression tests.",
    ),
    (
        "tqdm/tqdm#1880",
        "Strip terminal control sequences from untrusted `desc` / message strings.",
    ),
    (
        "anthropics/skills#1720",
        "`mcp-builder` wrote its evaluation report with the locale encoding; write UTF-8.",
    ),
]

CASE_STUDIES = [
    {
        "title": "simonw/llm#1737 — written as UTF-8, read back with the system locale",
        "url": "https://github.com/simonw/llm/pull/1737",
        "rows": [
            (
                "Symptom",
                "On Windows with a `cp936` default encoding, saving a template and then "
                "running `llm -t <name>` fails with `UnicodeDecodeError: 'gbk' codec "
                "can't decode byte 0xaa in position 16`. The `-f fragment.md` and "
                "`--functions tool.py` paths fail the same way.",
            ),
            (
                "Root cause",
                "The module disagreed with itself: `llm templates edit` wrote via "
                "`path.write_text(DEFAULT_TEMPLATE, \"utf-8\")` (`llm/cli.py:2646`) while "
                "`load_template()` read via `path.read_text()` (`llm/cli.py:4274`), which "
                "uses the locale encoding. The fragment and `--functions` paths "
                "(`llm/cli.py:293`, `llm/cli.py:4287`) were identical.",
            ),
            (
                "Fix",
                "Added `_read_text_file()`: try UTF-8 first, fall back to the locale "
                "encoding only when the file is not valid UTF-8, so old GBK / CP1252 "
                "files keep working. This mirrors the existing "
                "`(\"utf-8\", \"latin-1\")` fallback in `llm embed-multi --files`.",
            ),
            (
                "Evidence",
                "Three regression tests (template, fragment, `--functions`) driven by a "
                "fixture that simulates a non-UTF-8 locale on any platform. All three "
                "failed before (`UnicodeDecodeError: 'ascii' codec...`) and pass after; "
                "the full suite ran `1185 passed, 1 skipped, 6 xfailed, 15 xpassed`.",
            ),
        ],
    },
    {
        "title": "pranshuparmar/witr#242 — CI green, real Windows checkout cannot compile (merged)",
        "url": "https://github.com/pranshuparmar/witr/pull/242",
        "rows": [
            (
                "Symptom",
                "After `git clone`, `go build ./...` fails with `main.go:1:1: expected "
                "'package', found cmd`, `go test ./...` reports `[setup failed]`, and "
                "`make test` / `make lint` are broken on the machine. The repository's "
                "`Tests: Unit (windows-latest)` job was green.",
            ),
            (
                "Root cause",
                "`git ls-files -s main.go` showed mode `120000`: the root entry point was "
                "a symlink to `cmd/witr/main.go`. Git for Windows defaults to "
                "`core.symlinks=false`, so the symlink lands as a 16-byte text file whose "
                "content is the string `cmd/witr/main.go` — a `.go` file that is not a "
                "valid Go package. CI hid it because `actions/checkout` does create real "
                "symlinks.",
            ),
            (
                "Fix",
                "Replaced the root entry point with a real file and moved the entry logic "
                "into `internal/app.Main()` (`SetVersion` + `Execute`), shared by the root "
                "package and `cmd/witr`; added a lint guard that rejects tracked `120000` "
                "files.",
            ),
            (
                "Evidence",
                "`go build ./...`, `go vet ./...`, `gofmt -l .` and `go test ./...` all "
                "pass; seven cross-compilations (linux amd64/loong64, darwin amd64/arm64, "
                "freebsd/amd64, windows amd64/arm64) exit 0; `go build .` and "
                "`go build ./cmd/witr` produce byte-identical `--help` (2237 chars) and "
                "`--version` output.",
            ),
        ],
    },
    {
        "title": "huggingface/accelerate#4360 — three Unix-only assumptions in `debug_launcher`",
        "url": "https://github.com/huggingface/accelerate/pull/4360",
        "rows": [
            (
                "Symptom",
                "On Windows, `accelerate debug_launcher script.py` first fails with "
                "`ValueError: cannot find context for 'fork'`; bypassing that produces "
                "`PermissionError: [Errno 13]` because the child cannot open the "
                "rendezvous file.",
            ),
            (
                "Root cause",
                "Three Unix-only assumptions: (1) `start_method=\"fork\"` is hard-coded "
                "and Windows only has `spawn`; (2) the rendezvous file is created with "
                "`NamedTemporaryFile`, so the parent keeps the handle and the spawned "
                "child cannot open it; (3) `gloo_socket_ifname=\"lo\"` is set "
                "unconditionally even though the Windows loopback interface is not `lo`.",
            ),
            (
                "Fix",
                "`_debug_start_method()` chooses `fork` / `spawn` from platform "
                "capability; `NamedTemporaryFile` became `TemporaryDirectory` (only the "
                "path crosses the process boundary); `_has_loopback_alias()` probes for "
                "`lo` before setting the variable.",
            ),
            (
                "Evidence",
                "Reproduced on a Windows host, then `debug_launcher` started a "
                "multi-process debug session. Relevant tests pass on Python 3.13 + torch "
                "2.9 (`spawn` needs the `if __name__ == \"__main__\"` guard, documented "
                "in the docstring). The PR waits for maintainer workflow approval to run "
                "CI.",
            ),
        ],
    },
]

WORKFLOW_NOTES = [
    (
        "Reproduce, then change code",
        "Every fix starts from a failure message I can paste, and ends with the output "
        "after the fix. The Symptom rows above are the original errors.",
    ),
    (
        "Minimal diff + regression test",
        "Touch only the lines on the root-cause path; no drive-by formatting, renames or "
        "refactors. Where a test is possible, it is written to fail first.",
    ),
    (
        "Environment-class defects, not trends",
        "The bugs I know best only appear in real environments: non-UTF-8 default "
        "encodings, Windows checkouts, first-contributor CI gates, terminal capability "
        "differences. They are expensive to reproduce, so few people report them — and "
        "easy to dismiss as low impact, so I have to show who actually hits them.",
    ),
    (
        "Publish the misses",
        "Early on I sent documentation and formatting changes that maintainers closed as "
        "noise; a reproducible encoding bug was still called low impact because no real "
        "user had reported it and the repro was \"synthetic\". So I now ask before "
        "submitting: does a real user hit this? If not, find a real report or a concrete "
        "usage scenario first — and correct myself publicly when I get it wrong.",
    ),
]

STACK_ROWS = [
    ("Languages", "Python (3.9–3.13) · Go · TypeScript · Shell · PowerShell"),
    (
        "Training / inference",
        "PyTorch · Transformers · Accelerate · PEFT · FSDP · DeepSpeed · vLLM",
    ),
    (
        "Data / evaluation",
        "Datasets · lm-evaluation-harness · MLflow · OpenLLMetry / OpenTelemetry",
    ),
    (
        "Engineering",
        "pytest · ruff · mypy · GitHub Actions (Windows / macOS matrix) · Docker · Kubernetes",
    ),
    (
        "Platforms",
        "Windows + Linux · terminal capability detection · encoding / locale compatibility · cross-compilation",
    ),
]

HUI_TESTS = 139
EVAL_GATE_TESTS = 102


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(out)


def render_readme(data: dict) -> str:
    stats = data["stats"]
    merged = data["merged_prs"]
    open_prs = data.get("open_prs") or []
    open_by_key = {f'{p["repo"]}#{p["number"]}': p for p in open_prs}
    open_repos = len(data.get("open_by_repo") or {})

    merged_rows = [
        [
            f'[`{p["repo"]}`](https://github.com/{p["repo"]})',
            f'[#{p["number"]}]({p["url"]})',
            MERGED_NOTES.get(f'{p["repo"]}#{p["number"]}', p["title"]),
            p["merged_at"],
        ]
        for p in merged
    ]

    open_rows = []
    for key, note in OPEN_HIGHLIGHTS:
        pr = open_by_key.get(key)
        if pr:
            open_rows.append([f'[#{pr["number"]}]({pr["url"]}) `{pr["repo"]}`', note])

    case_blocks = []
    for i, case in enumerate(CASE_STUDIES, 1):
        rows = "\n".join(f"| **{label}** | {text} |" for label, text in case["rows"])
        case_blocks.append(
            f"### {i}. {case['title']}\n\n| | |\n| --- | --- |\n{rows}\n\n"
            f"[View pull request]({case['url']})\n"
        )

    all_open_url = (
        f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Aopen&type=pullrequests"
    )

    return f"""<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/intro-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/intro-light.svg">
  <img src="docs/intro-dark.svg" width="100%" alt="CJstate — I look for the failures that leave no trace">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/work-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/work-light.svg">
  <img src="docs/work-dark.svg" width="100%" alt="hui-harness and llm-eval-gate">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/upstream-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/upstream-light.svg">
  <img src="docs/upstream-dark.svg" width="100%" alt="Merged upstream pull requests, one row each">
</picture>

**I look for the failures that leave no trace** — Windows checkouts, non-UTF-8 locales, terminal capability differences.
Backend engineer working on LLM tooling and Go infrastructure.

[Upstream](#upstream-contributions) · [Case studies](#case-studies) · [Open PRs](#open-pull-requests) · [Projects](#projects) · [Toolchain](#toolchain)

</div>

## At a glance

{md_table(["Metric", "Value"], [
    ["Merged upstream PRs", f"{stats['merged']}"],
    ["Open upstream PRs", f"{stats['open']}"],
    ["Repositories with a merged or open PR", f"{stats['repos']}"],
    ["Lines in merged PRs", f"+{stats['additions']:,} / -{stats['deletions']:,}"],
    ["File changes across merged PRs", f"{stats['files']}"],
    ["Commits, last 12 months", f"{stats['commits']}"],
    ["Contributions, last 12 months", f"{stats['contributions']}"],
])}

## Upstream contributions

Every merged pull request, with the failure it fixed. The board above is the same ledger, drawn from the API.

{md_table(["Project", "PR", "What changed", "Merged"], merged_rows)}

## Case studies

Three root causes, each written up with the failure, the mechanism and the evidence that it is fixed.

{chr(10).join(case_blocks)}
## Open pull requests

{stats['open']} open across {open_repos} upstream repositories. Highlights:

{md_table(["PR", "What it changes"], open_rows)}

[See every open pull request on GitHub]({all_open_url})

## Projects

### [`hui-harness`](https://github.com/CJstate/hui-harness) — a coding agent you can replay

Every tool call, model reply and policy decision lands in a hash-chained JSONL log;
`hui replay` re-executes the session and fails on the first hash mismatch, so a run
is verified rather than trusted.

- {HUI_TESTS} tests; `ruff check` / `ruff format --check` clean; CI matrix Linux / Windows / macOS × Python 3.10–3.13
- **Zero runtime dependencies** (`urllib` / `json` / `subprocess` / `difflib`); `pip install` pulls nothing
- Context compaction drops whole groups: an assistant `tool_call` and its result are never split apart
- Encoding and newlines handled for real Windows environments: UTF-8 → local code page (GBK / CP936) → Latin-1 fallback, preserving BOM and CRLF
- Permission policies: `read-only` / `workspace-write` / `danger-full-access`; about 20 destructive commands require explicit approval and `shell=True` is never used

### [`llm-eval-gate`](https://github.com/CJstate/llm-eval-gate) — turn evaluation noise into a CI verdict

Give it two lm-evaluation-harness result files (`before` / `after`) and it decides
whether the run actually regressed: a relative threshold plus a standard-error band,
instead of "the third decimal went down, turn the build red".

- {EVAL_GATE_TESTS} tests; **zero runtime dependencies** (`dependencies = []` in `pyproject.toml`)
- GitHub Actions green on Ubuntu (Python 3.11 / 3.12 / 3.13), Windows and macOS; the project runs itself as an action
- Model-agnostic: it reads harness result files, not model outputs

## How I work

{md_table(["Habit", "What it means"], [[f"**{name}**", body] for name, body in WORKFLOW_NOTES])}

## Toolchain

{md_table(["Area", "What I use"], [[f"**{name}**", body] for name, body in STACK_ROWS])}

## Open to

AI / LLM infrastructure, training &amp; inference, and evaluation-tooling roles.

The three boards and the contribution tables are regenerated from the GitHub API by `tools/render_profile.py`; the two project test counts are measured locally.
"""


# ---------------------------------------------------------------------- main

BOARDS = (
    ("intro", render_intro),
    ("work", render_projects),
    ("upstream", render_contributions),
)


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
    parser.add_argument(
        "--readme", default=None,
        help="also write the markdown README to this path",
    )
    args = parser.parse_args()

    out = Path(args.out)
    (out / "data").mkdir(parents=True, exist_ok=True)

    data = (
        json.loads(Path(args.source).read_text(encoding="utf-8"))
        if args.source
        else fetch()
    )

    motion = not args.static
    (out / "data" / "live.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    for scheme in ("dark", "light"):
        for name, render in BOARDS:
            (out / f"{name}-{scheme}.svg").write_text(
                render(scheme, data, motion), encoding="utf-8"
            )

    if args.readme:
        Path(args.readme).write_text(
            render_readme(data), encoding="utf-8", newline="\n"
        )

    s = data["stats"]
    print(
        f"rendered: {s['merged']} merged, {s['open']} open, {s['repos']} repos, "
        f"{s['commits']} commits, {s['additions']} lines added"
    )


if __name__ == "__main__":
    main()
