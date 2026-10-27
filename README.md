<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/hero-light.svg">
  <img src="docs/hero-dark.svg" width="100%" alt="Jinhui Chen — I fix the bugs CI cannot see">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/metrics-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/metrics-light.svg">
  <img src="docs/metrics-dark.svg" width="100%" alt="Every merged pull request, one row each">
</picture>

</div>

<br>

I write Python and Go, and I care about the seam between a green build and a
user filing a bug. The failures I keep finding are structural: a symlink Git
for Windows never checks out, a locale encoding that eats the file you just
wrote, ANSI colour a terminal silently drops, a mock that replaces the command
under test. None of them can fail in CI, because CI is the machine that has the
thing the user does not.

Every number on this page is fetched from the GitHub API at render time by
[`tools/render_profile.py`](tools/render_profile.py) — 557 lines of stdlib
Python, no third-party cards, no badge services. If a service goes down, nothing
here breaks, because nothing here is hosted anywhere else.

## What I built

**[hui-harness](https://github.com/CJstate/hui-harness)** — a replayable coding
agent in pure stdlib Python. Hash-chained session logs so a run can be verified
rather than trusted, eight built-in tools, policy-gated command execution,
OpenAI and Anthropic providers behind one interface.

**[llm-eval-gate](https://github.com/CJstate/llm-eval-gate)** — a CI gate that
fails a build only when an LLM evaluation *actually* regressed. Relative
thresholds plus stderr-aware noise bands over `lm-evaluation-harness` results,
so a two-point wobble inside the error bar does not page anyone.

## What I landed upstream

Twelve pull requests merged into projects I do not own. The ones I would want
reviewed first:

| Pull request | What it fixes |
| --- | --- |
| [witr#242](https://github.com/pranshuparmar/witr/pull/242) | The root `main.go` was a version-controlled symlink. Git for Windows checks it out as a 16-byte text file and `go build` fails for every user — while CI stays green, because `actions/checkout` does create the symlink. Replaced with a real entry point plus a lint guard. |
| [nvm#3915](https://github.com/nvm-sh/nvm/pull/3915) | `nvm --help` documented a colour legend it never rendered in colour. |
| [k8sgpt-operator#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) | Tolerations support across the operator's CRD, controller and manifests. |
| [ggc#542](https://github.com/bmf-san/ggc/pull/542) | Config and command tests that only passed on Unix. |
| [agent-access-review#19](https://github.com/Mihirajmera/agent-access-review/pull/19) | `--format json` for machine-readable scan findings. |
| [witr#239](https://github.com/pranshuparmar/witr/pull/239) | Colour output died on terminals without bright-ANSI support. |

## How this page works

```bash
python tools/render_profile.py --out docs          # fetch live, render
python tools/render_profile.py --out docs --static # no animation, for review
```

`render_profile.py` calls `gh api` for the merged and open pull requests, walks
the contribution calendar, and emits four SVGs plus a JSON payload. A scheduled
workflow runs it daily and commits whatever changed, so the boards cannot drift
away from the account they describe.

The animation is CSS, layered on top of a complete static drawing: every element
carries its final geometry and colour as its base state. A renderer that ignores
keyframes — a screenshot tool, a sanitizer, a mail client — still gets the whole
picture. Elements whose only purpose is motion are the only ones that start
invisible, and they all respect `prefers-reduced-motion`.

## Elsewhere

[hui-harness](https://github.com/CJstate/hui-harness) ·
[llm-eval-gate](https://github.com/CJstate/llm-eval-gate) ·
[all merged pull requests](https://github.com/CJstate?tab=pull-requests&q=is%3Apr+is%3Amerged)
