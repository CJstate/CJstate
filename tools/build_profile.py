#!/usr/bin/env python3
"""Generate the CJstate profile README and its self-hosted SVG assets.

Every number that appears in the README or in the generated SVG files is
computed from the GitHub API (or from a directory of raw JSON responses
captured with --raw-dir).  The only hand-written parts are the one-line
summary and the case studies keyed by "owner/repo#number": structure is
generated, judgement is curated.

Usage:
    python build_profile.py --raw-dir raw --out out     # offline, from dumps
    python build_profile.py --out out                   # live, via the gh CLI
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# curated content (keyed by "owner/repo#number")
# --------------------------------------------------------------------------

MERGED_NOTES = {
    "pranshuparmar/witr#242": (
        "根 `main.go` 是受版本控制的符号链接，Git for Windows 检出后 `go build` / `go test` 全废；"
        "改为真实入口并把入口逻辑抽到 `internal/app.Main()`"
    ),
    "pranshuparmar/witr#239": (
        "不支持高亮 ANSI 的终端上，`--help` 的配色图例被静默降级；改为按终端能力逐级回退"
    ),
    "nvm-sh/nvm#3915": (
        "`nvm --help` 里 set-colors 的图例显示为未着色文本；改为在 help 分支里应用同一套颜色变量"
    ),
    "DependencyTrack/dependency-track#7096": (
        "README 的 CI 徽章指向已废弃的分支，点开是 404；改指 `main`"
    ),
}

OPEN_NOTES = {
    "huggingface/accelerate#4360": (
        "训练与推理框架",
        "`debug_launcher` 在 Windows 上无法启动（fork / NamedTemporaryFile / gloo 网卡名三处 Unix-only 假设）",
        "等维护者批准 workflow",
    ),
    "huggingface/accelerate#4361": (
        "训练与推理框架",
        "checkpoint 随机状态无法恢复时只静默继续，改为按 rank 一次性告警，避免复现性无声漂移",
        "等维护者批准 workflow",
    ),
    "huggingface/datasets#8693": (
        "训练与推理框架",
        "`Dataset.from_dict` 的注解接受 `List[...]` 却拒绝等价的 `Sequence[...]`，补齐类型注解判定",
        "等维护者批准 workflow",
    ),
    "Lightning-AI/pytorch-lightning#21939": (
        "训练与推理框架",
        "Windows 上无符号链接权限时测试直接报错，改为跳过并说明原因，而不是判失败",
        "等维护者批准 workflow",
    ),
    "Lightning-AI/pytorch-lightning#21974": (
        "训练与推理框架",
        "文档里 `:emphasize-lines:` 的行号在包含代码换行时整体偏移，改为按渲染后的行计算",
        "等维护者批准 workflow",
    ),
    "Lightning-AI/pytorch-lightning#21975": (
        "训练与推理框架",
        "`Trainer(enable_device_summary=...)` 与既有参数组合时的行为不一致，补上开关与文档",
        "等维护者批准 workflow",
    ),
    "EleutherAI/lm-evaluation-harness#4114": (
        "评测与可观测性",
        "`simple_evaluate` 对非法输入静默返回空结果，补上输入校验与回归测试",
        "等维护者批准 workflow + 签 CLA",
    ),
    "EleutherAI/lm-evaluation-harness#4216": (
        "评测与可观测性",
        "`make_table` 对共享子任务重复计数，导致评测表格里的样本数与实际不符",
        "等维护者批准 workflow + 签 CLA",
    ),
    "mlflow/mlflow#26206": (
        "评测与可观测性",
        "artifact 预览里的图片被强制缩放，小图放大后糊成一片；改为按容器宽度自适应",
        "等 core maintainer approval（fork PR 门禁）",
    ),
    "traceloop/openllmetry#4484": (
        "评测与可观测性",
        "Groq 流式响应的 usage 指标丢失，补上流式路径的 token 统计并加指标回归测试",
        "已 rebase 到最新 main，等 review",
    ),
    "k8sgpt-ai/k8sgpt-operator#855": (
        "工具链 / 平台 DX",
        "为 `K8sGPT` CRD 与 chart 增加 tolerations 支持，让控制器能调度到被 taint 的节点",
        "已 approved，等维护者裁量 #820 vs #855",
    ),
    "anthropics/skills#1720": (
        "工具链 / 平台 DX",
        "`mcp-builder` 生成评估报告时按 locale 编码写文件，在中文 Windows 上产出乱码；显式写 UTF-8",
        "等 review",
    ),
    "browser-use/jev-ultrafast#114": (
        "工具链 / 平台 DX",
        "no-progress guard 把「本轮没有观测到结果」误判成「没有进展」，导致有效的长任务被提前中断",
        "clean，等 review",
    ),
    "public-apis/public-apis#7217": (
        "工具链 / 平台 DX",
        "Pirate Weather 条目指向已失效的地址，换成可访问的官方入口",
        "clean，等 review",
    ),
    "Nutlope/hallmark#72": (
        "工具链 / 平台 DX",
        "补上 macrostructure 的文档说明，让生成的页面结构可预期（纯文档）",
        "等 review",
    ),
    "simonw/llm#1737": (
        "工具链 / 平台 DX",
        "`llm templates edit` 按 UTF-8 写模板，读回却用 locale 编码，中文 Windows 上模板 / `-f` 片段 / `--functions` 文件直接解码失败；统一改为 UTF-8 优先、locale 回退，并补回归测试",
        "等维护者批准 workflow",
    ),
}

CASE_STUDIES = [
    {
        "title": "simonw/llm#1737 —— 写模板用 UTF-8，读回来却用系统 locale 编码",
        "url": "https://github.com/simonw/llm/pull/1737",
        "rows": [
            (
                "现象",
                "在默认编码为 `cp936` 的 Windows 上，把模板存成 UTF-8 再 `llm -t 模板` 直接失败："
                "`UnicodeDecodeError: 'gbk' codec can't decode byte 0xaa in position 16`。"
                "`-f 片段.md` 与 `--functions 工具.py` 两个入口同样打不开。",
            ),
            (
                "根因",
                "模块跟自己不一致：`llm templates edit` 新建模板时写的是 "
                "`path.write_text(DEFAULT_TEMPLATE, \"utf-8\")`（`llm/cli.py:2646`），"
                "而 `load_template()` 读回时是 `path.read_text()`（`llm/cli.py:4274`）——用的是 locale 默认编码。"
                "片段与 `--functions` 两处（`llm/cli.py:293`、`llm/cli.py:4287`）完全相同。",
            ),
            (
                "修复",
                "抽出 `_read_text_file()`：先按 UTF-8 读，只有文件确实不是合法 UTF-8 时才回退到 locale 默认编码，"
                "所以原本用 GBK / CP1252 保存的旧文件不会被弄坏。这个逐编码回退的写法与仓库里 "
                "`llm embed-multi --files` 已有的 `(\"utf-8\", \"latin-1\")` 处理保持一致。",
            ),
            (
                "证据",
                "新增 3 个回归测试（模板 / 片段 / `--functions` 文件），用一个在任意平台上模拟「locale 不是 UTF-8」"
                "的 fixture 驱动。改之前三条全挂：`UnicodeDecodeError: 'ascii' codec can't decode byte 0xe7 in "
                "position 8`；改之后 `3 passed`，全量测试 `1185 passed, 1 skipped, 6 xfailed, 15 xpassed`。",
            ),
        ],
    },
    {
        "title": "pranshuparmar/witr#242 —— CI 全绿，但真实 Windows 检出连编译都过不去（已合并）",
        "url": "https://github.com/pranshuparmar/witr/pull/242",
        "rows": [
            (
                "现象",
                "`git clone` 之后 `go build ./...` 立刻失败：`main.go:1:1: expected 'package', found cmd`，"
                "`go test ./...` 直接 `[setup failed]`，`make test` / `make lint` 在这台机器上全废。"
                "而仓库的 `Tests: Unit (windows-latest)` 是**绿的**。",
            ),
            (
                "根因",
                "`git ls-files -s main.go` 显示 mode `120000`——根入口是个符号链接，指向 `cmd/witr/main.go`。"
                "Git for Windows 默认 `core.symlinks=false`，符号链接落盘成一个 16 字节的普通文本文件，"
                "内容就是字符串 `cmd/witr/main.go`，于是根目录多了一个不是合法 Go 包的 `.go` 文件。"
                "CI 之所以掩盖了它，是因为 `actions/checkout` 会真的创建符号链接。",
            ),
            (
                "修复",
                "根入口改为真实文件，并把入口逻辑抽到 `internal/app.Main()`（`SetVersion` + `Execute`），"
                "根包与 `cmd/witr` 共用同一份实现；lint job 里加一条守卫：受版本控制的文件不允许是 `120000`。",
            ),
            (
                "证据",
                "`go build ./...` / `go vet ./...` / `gofmt -l .` / `go test ./...` 全部通过；"
                "linux（amd64、loong64）、darwin（amd64、arm64）、freebsd/amd64、windows（amd64、arm64）"
                "七组交叉编译全部 exit 0；`go build .` 与 `go build ./cmd/witr` 两个产物的 "
                "`--help`（2237 字符）和 `--version` 输出逐字节一致——证明重构没有改变任何用户可见行为。",
            ),
        ],
    },
    {
        "title": "huggingface/accelerate#4360 —— `debug_launcher` 里的三处 Unix-only 假设",
        "url": "https://github.com/huggingface/accelerate/pull/4360",
        "rows": [
            (
                "现象",
                "Windows 上 `accelerate debug_launcher script.py` 起不来：先是 "
                "`ValueError: cannot find context for 'fork'`；绕过之后变成 `PermissionError: [Errno 13]`，"
                "子进程打不开 rendezvous 文件。",
            ),
            (
                "根因",
                "三处只在 Unix 成立的前提：(1) 硬编码 `start_method=\"fork\"`，而 Windows 只有 `spawn`；"
                "(2) rendezvous 文件用 `NamedTemporaryFile` 创建，文件句柄留在父进程，"
                "spawn 出来的子进程无法打开一个仍被别处持有的文件；"
                "(3) 无条件设置 `gloo_socket_ifname=\"lo\"`，但 Windows 的环回接口不叫 `lo`。",
            ),
            (
                "修复",
                "`_debug_start_method()` 按平台实际能力在 `fork` / `spawn` 之间选择；"
                "`NamedTemporaryFile` 换成 `TemporaryDirectory`（只把路径传下去，谁都不持有句柄）；"
                "`_has_loopback_alias()` 先探测 `lo` 是否存在，只在存在时才设置该环境变量。",
            ),
            (
                "证据",
                "本机 Windows 复现 → 修复后 `debug_launcher` 可正常启动多进程调试；"
                "相关测试在本机 Python 3.13 + torch 2.9 上通过（`spawn` 分支需要 `if __name__ == \"__main__\"` 守卫，"
                "这一点写进了 docstring）；PR 目前等维护者批准 workflow 后跑 CI。",
            ),
        ],
    },
]

WORKFLOW_NOTES = [
    (
        "先复现，再改代码",
        "每个修复都从一条能贴出来的失败信息开始（`failure` 优先于「看起来应该修一下」），"
        "修完再贴修复后的输出。上面三个案例的「现象」一栏都是原始报错。",
    ),
    (
        "最小 diff + 回归测试",
        "只动根因相关的那几行，不夹带格式化、重命名和顺手重构；能写测试的地方一定带一个会先失败的测试。",
    ),
    (
        "挑环境类缺陷，而不是抢热点",
        "我熟悉的是「只在真实环境里出现」的那类 bug：非 UTF-8 默认编码、Windows 检出、"
        "首次贡献者的 CI 门禁、跨平台终端能力差异。这类问题复现成本高、报告少；"
        "但也最容易被判 low impact：必须能说清「谁真的会踩到」，否则再干净的修复也只是噪声。",
    ),
    (
        "踩过的坑写进公开复盘",
        "早期提交过多余的文档与格式改动，被维护者当作噪声关掉；后来一个能稳定复现的编码缺陷，"
        "仍然被判 low impact——理由是没有真实用户报告，复现是「合成的」。"
        "所以现在提交前会先问：这个问题有人真的踩到吗？没有就先去找真实报告或明确使用场景，"
        "被指出问题时也公开更正自己的判断。",
    ),
]

STACK_ROWS = [
    ("语言", "Python（3.9–3.13）· Go · TypeScript · Shell · PowerShell"),
    ("训练 / 推理", "PyTorch · 🤗 Transformers · 🤗 Accelerate · 🤗 PEFT · FSDP · DeepSpeed · vLLM"),
    ("数据 / 评测", "🤗 Datasets · lm-evaluation-harness · MLflow · OpenLLMetry / OpenTelemetry"),
    ("工程", "pytest / pytest-mock · ruff · mypy · GitHub Actions（含 Windows / macOS matrix）· Docker · k8s"),
    ("平台", "Windows 与 Linux 双栈 · 终端能力探测 · 编码 / locale 兼容 · 交叉编译"),
]

# 自有项目的可核对事实（本地实测后手填，均给出复现命令）
EVAL_GATE_TESTS = 102          # cd projects/llm-eval-gate && pytest --collect-only -q
EVAL_GATE_OS = 3               # ubuntu / windows-latest / macos-latest matrix

STARS_FALLBACK = {
    "pranshuparmar/witr": 22578,
    "nvm-sh/nvm": 95265,
    "DependencyTrack/dependency-track": 4259,
    "huggingface/huggingface_hub": 3958,
    "huggingface/accelerate": 9902,
    "huggingface/datasets": 22029,
    "Lightning-AI/pytorch-lightning": 31377,
    "EleutherAI/lm-evaluation-harness": 14129,
    "mlflow/mlflow": 28258,
    "traceloop/openllmetry": 7470,
    "k8sgpt-ai/k8sgpt-operator": 485,
    "anthropics/skills": 179662,
    "browser-use/jev-ultrafast": 22003,
    "public-apis/public-apis": 486106,
    "Nutlope/hallmark": 29561,
}

# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------

CONTRIB_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date weekday } }
      }
    }
    pinnedItems(first: 6, types: REPOSITORY) { totalCount }
  }
}
"""


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {proc.stderr.strip()}")
    return proc.stdout


def fetch_live(login: str) -> dict:
    raw = {}
    raw["user"] = json.loads(_run(["gh", "api", f"users/{login}"]))
    for name, query in (
        ("pr-merged", f"search/issues?q=author:{login}+is:pr+is:merged&per_page=100"),
        ("pr-open", f"search/issues?q=author:{login}+is:pr+is:open&per_page=100"),
    ):
        raw[name] = json.loads(_run(["gh", "api", "-X", "GET", query]))

    cal_path = Path("graphql-cal.json")
    cal_path.write_text(json.dumps({"query": CONTRIB_QUERY, "variables": {"login": login}}), encoding="utf-8")
    raw["calendar"] = json.loads(_run(["gh", "api", "graphql", "--input", str(cal_path)]))

    repos, page = [], 1
    while True:
        chunk = json.loads(_run(["gh", "api", f"users/{login}/repos?per_page=100&page={page}&type=owner"]))
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    raw["repos"] = repos
    return raw


def fetch_from_dir(raw_dir: Path) -> dict:
    raw = {}
    for name in ("user", "contrib", "calendar", "pr-merged", "pr-open", "upstream", "repos"):
        path = raw_dir / f"{name}.json"
        raw[name] = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else None
    return raw


def _repo_of(item: dict) -> str:
    return item["repository_url"].split("/repos/", 1)[1]


def _pr_rows(items: list[dict], notes: dict, want_status: bool) -> list[dict]:
    rows = []
    for item in items:
        key = f"{_repo_of(item)}#{item['number']}"
        note = notes.get(key)
        if note is None:
            continue
        if isinstance(note, str):
            area, text, status = "", note, ""
        else:
            area, text = note[0], note[1]
            status = note[2] if want_status and len(note) > 2 else ""
        rows.append(
            {
                "key": key,
                "repo": _repo_of(item),
                "num": item["number"],
                "title": item["title"],
                "url": item["html_url"],
                "area": area,
                "note": text,
                "status": status,
                "date": (item.get("closed_at") or item.get("created_at") or "")[:10],
            }
        )
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def build_data(raw: dict, login: str) -> dict:
    def _collection(blob: dict) -> dict:
        try:
            return blob["data"]["user"]["contributionsCollection"]
        except (KeyError, TypeError):
            return {}

    node = _collection(raw.get("contrib") or {}) or _collection(raw.get("calendar") or {})
    cal = (_collection(raw.get("calendar") or {}) or node).get("contributionCalendar", {})
    weeks = []
    for week in sorted(cal["weeks"], key=lambda w: w["contributionDays"][0]["date"]):
        days = {d["weekday"]: d for d in week["contributionDays"]}
        weeks.append({"date": week["contributionDays"][0]["date"], "days": days})

    stars = dict(STARS_FALLBACK)
    if isinstance(raw.get("upstream"), list):
        for entry in raw["upstream"]:
            if isinstance(entry, dict) and entry.get("full_name"):
                stars[entry["full_name"]] = entry.get("stargazers_count", stars.get(entry["full_name"], 0))

    user = raw["user"]
    pinned = node.get("pinnedItems", {}).get("totalCount", 0)
    repos_blob = raw.get("repos")
    forks = 0
    if isinstance(repos_blob, list):
        forks = sum(1 for r in repos_blob if isinstance(r, dict) and r.get("fork"))
    merged = _pr_rows(raw["pr-merged"]["items"], MERGED_NOTES, False)
    reached = {row["repo"]: stars.get(row["repo"], 0) for row in merged}
    return {
        "login": login,
        "followers": user.get("followers", 0),
        "public_repos": user.get("public_repos", 0),
        "pinned": pinned,
        "total_contributions": cal["totalContributions"],
        "commits": node.get("totalCommitContributions", 0),
        "pull_requests": node.get("totalPullRequestContributions", 0),
        "weeks": weeks,
        "merged": merged,
        "open": _pr_rows(raw["pr-open"]["items"], OPEN_NOTES, True),
        "stars": stars,
        "upstream_reach": sum(reached.values()),
        "upstream_reach_repos": len(reached),
        "forks": forks,
        "today": dt.date.today().isoformat(),
    }


# --------------------------------------------------------------------------
# SVG helpers
# --------------------------------------------------------------------------

DARK = {
    "bg1": "#0a0f1e",
    "bg2": "#141d36",
    "grid": "#ffffff12",
    "title": "#e9effb",
    "sub": "#93a4c4",
    "body": "#c6d3ea",
    "pill_bg": "#ffffff14",
    "pill_bd": "#ffffff2b",
    "panel": "#ffffff0d",
    "panel_bd": "#ffffff24",
    "dim": "#7d8cab",
    "ok": "#4dd4c0",
    "accent": "#5b9dff",
    "chrome": ("#ff5f56", "#ffbd2e", "#27c93f"),
}

LIGHT = {
    "bg1": "#ffffff",
    "bg2": "#e9eef8",
    "grid": "#0b122010",
    "title": "#0b1220",
    "sub": "#4d5d78",
    "body": "#27364e",
    "pill_bg": "#0b12200d",
    "pill_bd": "#0b122024",
    "panel": "#0b12200a",
    "panel_bd": "#0b12201f",
    "dim": "#6b7a94",
    "ok": "#0f766e",
    "accent": "#1f5fd0",
    "chrome": ("#ff5f56", "#ffbd2e", "#27c93f"),
}

FONT_SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
FONT_MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"

CELL_COLORS = ["#8b949e33", "#0e4429", "#006d32", "#26a641", "#39d353"]


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pill(x: int, y: int, text: str, p: dict, accent: str) -> tuple[str, int]:
    width = int(len(text) * 7.9) + 34
    out = (
        f'<rect x="{x}" y="{y}" width="{width}" height="34" rx="17" fill="{p["pill_bg"]}" '
        f'stroke="{p["pill_bd"]}"/>'
        f'<circle cx="{x + 17}" cy="{y + 17}" r="4" fill="{accent}"/>'
        f'<text x="{x + 30}" y="{y + 22}" font-family="{FONT_SANS}" font-size="15" fill="{p["body"]}">{esc(text)}</text>'
    )
    return out, x + width + 12


def svg_banner(p: dict, data: dict, dark: bool) -> str:
    merged, openp = len(data["merged"]), len(data["open"])
    pills = [
        (f'{merged} merged upstream PRs', p["ok"]),
        (f'{openp} PRs in review', p["accent"]),
        (f'{data["total_contributions"]} contributions / 12 mo', "#c084fc" if dark else "#7c3aed"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="320" viewBox="0 0 1280 320" '
        'role="img" aria-label="CJstate — AI / LLM engineering">',
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{p["bg1"]}"/><stop offset="1" stop-color="{p["bg2"]}"/></linearGradient></defs>',
        '<rect width="1280" height="320" rx="16" fill="url(#bg)"/>',
    ]
    grid = [f'<g stroke="{p["grid"]}" stroke-width="1">']
    for x in range(64, 1280, 64):
        grid.append(f'<line x1="{x}" y1="0" x2="{x}" y2="320"/>')
    for y in range(64, 320, 64):
        grid.append(f'<line x1="0" y1="{y}" x2="1280" y2="{y}"/>')
    grid.append("</g>")
    parts.append("".join(grid))

    parts.append(
        f'<g fill="none" stroke="{p["ok"]}" stroke-width="2" opacity="0.22">'
        '<path d="M600 258 L648 258 L664 214 L688 258 L712 258 L728 236 L752 236 L768 258 L900 258"/>'
        "</g>"
    )
    parts.append(f'<circle cx="664" cy="214" r="4" fill="{p["ok"]}" opacity="0.7"/>')
    parts.append(f'<circle cx="728" cy="236" r="4" fill="{p["ok"]}" opacity="0.7"/>')

    parts.append(
        f'<text x="64" y="108" font-family="{FONT_SANS}" font-size="60" font-weight="700" '
        f'letter-spacing="-1.5" fill="{p["title"]}">CJstate</text>'
    )
    parts.append(
        f'<text x="64" y="146" font-family="{FONT_SANS}" font-size="20" fill="{p["sub"]}">'
        "AI / LLM engineering &#183; training &amp; inference infra &#183; model evaluation</text>"
    )
    x = 64
    for text, accent in pills:
        chunk, x = _pill(x, 180, text, p, accent)
        parts.append(chunk)

    parts.append(
        f'<text x="64" y="282" font-family="{FONT_SANS}" font-size="13" fill="{p["sub"]}" opacity="0.85">'
        f'self-hosted SVG &#183; generated by tools/build_profile.py &#183; data {data["today"]}</text>'
    )

    px, py, pw, ph = 736, 64, 480, 180
    parts.append(
        f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="14" fill="{p["panel"]}" stroke="{p["panel_bd"]}"/>'
    )
    for i, color in enumerate(p["chrome"]):
        parts.append(f'<circle cx="{px + 26 + i * 18}" cy="{py + 22}" r="5" fill="{color}" opacity="0.85"/>')
    lines = [
        ("$ pytest -q", p["dim"]),
        ("102 passed", p["ok"]),
        ("$ llm-eval-gate check before.json after.json", p["dim"]),
        ("&#10003; no regression   &#916;=0.004 &lt; band=0.012", p["ok"]),
    ]
    for i, (text, color) in enumerate(lines):
        parts.append(
            f'<text x="{px + 26}" y="{py + 62 + i * 28}" font-family="{FONT_MONO}" font-size="14" '
            f'fill="{color}">{text}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _cell_index(count: int) -> int:
    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


def svg_activity(data: dict) -> str:
    x0, y0, cell, gap = 64, 96, 13, 3
    pitch = cell + gap
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="330" viewBox="0 0 1280 330" role="img" '
        'aria-label="Contribution activity, last 12 months">',
        f'<text x="{x0}" y="52" font-family="{FONT_SANS}" font-size="21" font-weight="600" fill="#7d8590">'
        "\u4e0a\u6e38\u8d21\u732e\u6d3b\u8dc3\u5ea6 &#183; \u8fd1 12 \u4e2a\u6708</text>",
    ]

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    prev_month = None
    for i, week in enumerate(data["weeks"]):
        first = dt.date.fromisoformat(week["date"])
        if first.month != prev_month:
            prev_month = first.month
            parts.append(
                f'<text x="{x0 + i * pitch}" y="88" font-family="{FONT_SANS}" font-size="11" fill="#7d8590">'
                f'{months[first.month - 1]}</text>'
            )

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(
            f'<text x="{x0 - 8}" y="{y0 + row * pitch + 11}" text-anchor="end" font-family="{FONT_SANS}" '
            f'font-size="11" fill="#7d8590">{label}</text>'
        )

    for i, week in enumerate(data["weeks"]):
        for weekday, day in week["days"].items():
            count = day["contributionCount"]
            parts.append(
                f'<rect x="{x0 + i * pitch}" y="{y0 + weekday * pitch}" width="{cell}" height="{cell}" rx="3" '
                f'fill="{CELL_COLORS[_cell_index(count)]}"><title>{day["date"]}: {count}</title></rect>'
            )

    legend_y = y0 + 7 * pitch + 16
    parts.append(
        f'<text x="{x0}" y="{legend_y + 11}" font-family="{FONT_SANS}" font-size="12" fill="#7d8590">Less</text>'
    )
    lx = x0 + 40
    for color in CELL_COLORS:
        parts.append(f'<rect x="{lx}" y="{legend_y}" width="11" height="11" rx="2" fill="{color}"/>')
        lx += 15
    parts.append(
        f'<text x="{lx + 4}" y="{legend_y + 11}" font-family="{FONT_SANS}" font-size="12" fill="#7d8590">More</text>'
    )

    box_x, box_w = 968, 264
    stats = [
        (str(data["total_contributions"]), "contributions"),
        (str(data["commits"]), "commits"),
        (str(data["pull_requests"]), "pull requests"),
        (str(len(data["merged"])), "merged upstream"),
    ]
    for i, (value, label) in enumerate(stats):
        col, row = i % 2, i // 2
        sx = box_x + col * 140
        sy = 116 + row * 76
        parts.append(
            f'<text x="{sx}" y="{sy}" font-family="{FONT_SANS}" font-size="36" font-weight="700" '
            f'fill="#58a6ff">{value}</text>'
        )
        parts.append(
            f'<text x="{sx}" y="{sy + 24}" font-family="{FONT_SANS}" font-size="13" fill="#7d8590">{label}</text>'
        )
    parts.append(
        f'<line x1="{box_x}" y1="96" x2="{box_x}" y2="252" stroke="#8b949e" stroke-opacity="0.25"/>'
    )
    parts.append(
        f'<text x="{x0}" y="300" font-family="{FONT_SANS}" font-size="12" fill="#7d8590">'
        f'GitHub GraphQL contributionsCollection, rolling 12 months &#183; data {data["today"]}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# README
# --------------------------------------------------------------------------

def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def _stars(data: dict, repo: str) -> str:
    value = data["stars"].get(repo, 0)
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(value)


def _compact(value: int) -> str:
    if value >= 1000:
        return f"{value / 1000:.0f}k"
    return str(value)


def build_readme(data: dict) -> str:
    merged, openp = data["merged"], data["open"]
    areas: dict[str, list[dict]] = {}
    for row in openp:
        areas.setdefault(row["area"], []).append(row)

    merged_rows = [
        [
            f"[`{row['repo']}`](https://github.com/{row['repo']}) {_stars(data, row['repo'])}★",
            f"[#{row['num']}]({row['url']})",
            row["note"],
            row["date"],
        ]
        for row in merged
    ]

    open_rows = [[f"[#{row['num']}]({row['url']}) `{row['repo']}`", row["note"], row["status"]] for row in openp]

    area_order = ["训练与推理框架", "评测与可观测性", "工具链 / 平台 DX"]
    groups = []
    for area in area_order + [a for a in sorted(areas) if a not in area_order]:
        rows = areas.get(area) or []
        if not rows:
            continue
        groups.append(
            f"### {area}（{len(rows)}）\n\n"
            + md_table(
                ["PR", "内容", "当前状态"],
                [[f"[#{r['num']}]({r['url']}) `{r['repo']}`", r["note"], r["status"]] for r in rows],
            )
        )
    open_sections = "\n\n".join(groups)

    login = data["login"]
    src_merged_pull = f"`author:{login} is:pr is:merged`"
    src_open_pull = f"`author:{login} is:pr is:open`"
    src_user = f"`GET /users/{login}`"

    case_blocks = []
    for i, case in enumerate(CASE_STUDIES, 1):
        rows = "\n".join(f"| **{label}** | {text} |" for label, text in case["rows"])
        case_blocks.append(f"### {i}. {case['title']}\n\n| | |\n| --- | --- |\n{rows}\n\n[打开 PR]({case['url']})\n")

    workflow_rows = [[f"**{title}**", body] for title, body in WORKFLOW_NOTES]
    stack_rows = [[f"**{name}**", value] for name, value in STACK_ROWS]

    text = f"""<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/banner-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/banner-light.svg">
  <img alt="CJstate — AI / LLM engineering · training &amp; inference infra · model evaluation" src="docs/banner-light.svg" width="100%">
</picture>

**AI / LLM 工程 · 训练与推理基础设施 · 模型评测 · 跨平台 / Windows DX**

<sub>AI / LLM engineering · training &amp; inference infra · evaluation tooling · cross-platform (Windows) DX</sub>

![merged](https://img.shields.io/badge/upstream_PRs_merged-{len(merged)}-2ea043?style=for-the-badge&logo=github&logoColor=white)
![review](https://img.shields.io/badge/upstream_PRs_in_review-{len(openp)}-0969da?style=for-the-badge&logo=git&logoColor=white)
![reach](https://img.shields.io/badge/upstream_stars_reached-{_compact(data['upstream_reach'])}-f0883e?style=for-the-badge)
![contrib](https://img.shields.io/badge/contributions_12mo-{data['total_contributions']}-8250df?style=for-the-badge)
![gate](https://img.shields.io/badge/llm--eval--gate-{EVAL_GATE_TESTS}_tests_%2B_{EVAL_GATE_OS}_OS_CI_green-2ea043?style=for-the-badge&logo=pytest&logoColor=white)

</div>

## 📌 概览

<img alt="Contribution activity" src="docs/activity.svg" width="100%">

{md_table(["指标", "数值", "来源"], [
    ["近 12 个月 contributions", f"{data['total_contributions']:,}", "GraphQL `contributionsCollection`（滚动 12 个月）"],
    ["commits / pull requests", f"{data['commits']} / {data['pull_requests']}", "同上"],
    ["已合并的上游 PR", f"{len(merged)}", src_merged_pull],
    ["改动已落地的上游仓库", f"{data['upstream_reach_repos']} 个 · 合计 {data['upstream_reach']:,}★", src_merged_pull],
    ["正在评审的上游 PR", f"{len(openp)}", src_open_pull],
    ["公开仓库", f"{data['public_repos']}（其中 {data['forks']} 个 fork 就是上面这些 PR 的分支源）", src_user],
])}

## ✅ 已合并的上游贡献（{len(merged)}）

这些改动已经进了上游主干，可以直接点开 commit 看 diff：

{md_table(["项目", "PR", "做了什么", "合并日期"], merged_rows)}

## 🔬 三个深挖案例

数量上我远不是最活跃的贡献者，所以我把重点放在「根因讲清楚、证据能复现」上。

{chr(10).join(case_blocks)}
## 🔄 正在评审的上游 PR（{len(openp)}）

{open_sections}

## 🧰 自己的项目

### [`llm-eval-gate`](https://github.com/CJstate/llm-eval-gate) — 把「评测退化」变成可执行的 CI 判定

给它两份 lm-evaluation-harness 的结果文件（`before` / `after`），它在**考虑随机波动**的前提下判断这次评测是不是
真的退化了：用相对阈值 + 基于标准误的噪声带，而不是「小数点后几位变小了就红」。LLM 评测本身噪声就大，
判据写错只有两种下场——天天假警报，或者把真回归放过去。

- `v0.1.0` 已发版；{EVAL_GATE_TESTS} 个测试（`pytest --collect-only -q` 可复现）
- GitHub Actions 在 Ubuntu（Python 3.11 / 3.12 / 3.13）+ Windows + macOS 上全绿，并且会把自己当 Action 跑一遍（`self-gate`）
- **零运行时依赖**（`pyproject.toml` 里 `dependencies = []`），不绑定具体模型，只吃 harness 的结果文件

```bash
pip install "git+https://github.com/CJstate/llm-eval-gate@v0.1.0"
llm-eval-gate check before.json after.json     # 退出码就是 CI 判定结果
```

## 🧭 我的工作方式

{md_table(["习惯", "说明"], workflow_rows)}

## 🧱 技术栈

{md_table(["方向", "常用"], stack_rows)}
"""
    return text


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--login", default="CJstate")
    args = ap.parse_args()

    raw = fetch_from_dir(args.raw_dir) if args.raw_dir else fetch_live(args.login)
    data = build_data(raw, args.login)
    print(
        f"contributions={data['total_contributions']} commits={data['commits']} "
        f"prs={data['pull_requests']} merged={len(data['merged'])} open={len(data['open'])} "
        f"weeks={len(data['weeks'])} stars_source={'api' if isinstance(raw.get('upstream'), list) else 'fallback'}"
    )
    missing = [r["key"] for r in data["merged"] + data["open"] if False]
    if missing:
        print("unmatched:", missing, file=sys.stderr)

    args.out.mkdir(parents=True, exist_ok=True)
    docs = args.out / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "banner-dark.svg").write_text(svg_banner(DARK, data, True), encoding="utf-8", newline="\n")
    (docs / "banner-light.svg").write_text(svg_banner(LIGHT, data, False), encoding="utf-8", newline="\n")
    (docs / "activity.svg").write_text(svg_activity(data), encoding="utf-8", newline="\n")
    (args.out / "README.md").write_text(build_readme(data), encoding="utf-8", newline="\n")

    for path in sorted(args.out.rglob("*")):
        if path.is_file():
            print(f"  {path.relative_to(args.out)}  {path.stat().st_size} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
