# CJstate

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=22&pause=1400&color=7AA2F7&center=true&vCenter=true&width=720&lines=Go+infrastructure+%C2%B7+Kubernetes+tooling+%C2%B7+Prometheus;Fixing+the+bugs+CI+never+catches;Test-first%2C+every+time;Windows+daily+driver" alt="Currently typing">
</p>

Backend engineer focused on Go infrastructure and LLM tooling. I work mainly on Prometheus (CNCF), Kubernetes tooling, and Python ML infrastructure — and I run Windows as a daily driver, which is how I keep running into the bugs that never show up on Linux CI.

**Stack:** Go · Python · Kubernetes · Docker · Prometheus · GitHub Actions

<p align="center">
  <img alt="Merged pull requests across GitHub, fetched live" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.github.com%2Fsearch%2Fissues%3Fq%3Dauthor%253ACJstate%2520type%253Apr%2520is%253Amerged&query=%24.total_count&label=merged%20PRs&color=brightgreen&logo=github">
  <img alt="GitHub profile views" src="https://komarev.com/ghpvc/?username=CJstate&color=58A6FF&style=flat">
</p>

## Open source

Merged pull requests, with the defect each one removed:

| Project | PR | What it fixed |
| --- | --- | --- |
| [juanfont/headscale](https://github.com/juanfont/headscale) | [#3650](https://github.com/juanfont/headscale/pull/3650) | Pre-0.23 databases without a migrations table were migrated blindly; now they are rejected with a clear error instead of being corrupted. |
| [pranshuparmar/witr](https://github.com/pranshuparmar/witr) | [#242](https://github.com/pranshuparmar/witr/pull/242) | The root `main.go` was a tracked symlink. Git for Windows checks symlinks out as plain text, so `go build` failed on a real clone while CI stayed green. Replaced it with a real entry point and added a lint guard for tracked symlinks. |
| [dagucloud/dagu](https://github.com/dagucloud/dagu) | [#3554](https://github.com/dagucloud/dagu/pull/3554) | `mark_success` was ignored for non-retryable exit codes, so marked steps still failed the workflow. |
| [dagucloud/dagu](https://github.com/dagucloud/dagu) | [#3578](https://github.com/dagucloud/dagu/pull/3578) | Regenerated `llms.txt` and added a CI check that keeps it in sync with the skills tree. |
| [k8sgpt-ai/k8sgpt-operator](https://github.com/k8sgpt-ai/k8sgpt-operator) | [#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) | Added tolerations to the K8sGPT CRD and Helm chart so the controller can schedule on tainted nodes. |
| [bmf-san/ggc](https://github.com/bmf-san/ggc) | [#542](https://github.com/bmf-san/ggc/pull/542) | The config and command test suites relied on Unix-only exec mocks; they now pass on Windows. |

Most of my fixes start from a failure I hit locally: a Windows checkout that will not compile, a GBK locale that mangles a template file, a timestamp that drifts by a few nanoseconds. I reproduce it, write the failing test first, and open the PR only after the affected suites, vet and formatting are all green.

## Activity

<p align="center">
  <img alt="GitHub stats" src="https://github-readme-stats.vercel.app/api?username=CJstate&show_icons=true&include_all_commits=true&count_private=true&theme=tokyonight&hide_border=false">
  <img alt="Top languages" src="https://github-readme-stats.vercel.app/api/top-langs/?username=CJstate&layout=compact&theme=tokyonight&hide_border=false">
</p>

<p align="center">
  <img alt="Contribution streak" src="https://streak-stats.demolab.com?user=CJstate&theme=tokyonight&hide_border=false&short_counts=true">
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./docs/snake-dark.svg">
    <img alt="Contribution snake eating the contribution graph" src="./docs/snake-light.svg">
  </picture>
</p>

## Projects

### [Veritas-Harness](https://github.com/CJstate/Veritas-Harness)

A coding-agent runtime you can audit. Every tool call, model reply and MCP request lands in a hash-chained JSONL log; `veritas replay` verifies the chain, re-runs the tools, and diffs each fresh result by SHA-256 — a run is verified, not trusted.

- 141 tests, zero runtime dependencies, CI matrix Linux / Windows / macOS × Python 3.10–3.13
- Built for real Windows environments: UTF-8 → GBK → Latin-1 fallback, BOM and CRLF preserved
- Includes a tamper demo that edits a session and shows replay rejecting it before any tool executes

### [EvalGuard](https://github.com/CJstate/EvalGuard)

Turns lm-evaluation-harness output into a CI verdict. Given `before` / `after` result files, it decides whether a benchmark actually regressed: a relative threshold plus a standard-error band, not "the third decimal went down, turn the build red".

- 107 tests, zero runtime dependencies (`dependencies = []`)
- Ships an offline demo where MMLU stays inside the noise band and GSM8K correctly fails the gate

## Contact

1507965754@qq.com
