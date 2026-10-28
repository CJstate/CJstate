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

    c.add("<title>Jinhui Chen</title>")

    c.chars(PAD, 80, "Jinhui Chen", 44, "ink", 700, SANS, -1.7)

    c.rule(PAD, 104, W - PAD, "line", 1, cls=("draw" if motion else None))

    c.text(PAD, 136, "Backend engineer.", 19, "ink", 600, SANS, tracking=-0.3)
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
        f'{stats["merged"]} merged upstream \u00b7 {stats["repos"]} public repos '
        f'\u00b7 {stats["contributions"]} contributions this year',
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
    shown = prs[:16]
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

    s = data["stats"]
    print(
        f"rendered: {s['merged']} merged, {s['open']} open, {s['repos']} repos, "
        f"{s['commits']} commits, {s['additions']} lines added"
    )


if __name__ == "__main__":
    main()
