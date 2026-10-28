<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/intro-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/intro-light.svg">
  <img src="docs/intro-dark.svg" width="100%" alt="Jinhui Chen — I look for the failures that leave no trace">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/work-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/work-light.svg">
  <img src="docs/work-dark.svg" width="100%" alt="hui-harness and llm-eval-gate">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/upstream-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/upstream-light.svg">
  <img src="docs/upstream-dark.svg" width="100%" alt="Every merged pull request, one row each">
</picture>

</div>

## Upstream, and what each one was actually about

| Pull request | The bug |
| --- | --- |
| [witr#242](https://github.com/pranshuparmar/witr/pull/242) | The root `main.go` was a version-controlled symlink. Git for Windows checks it out as a 16-byte text file, so `go build` fails for every Windows user — while CI stays green, because `actions/checkout` does create the symlink. |
| [k8sgpt#1841](https://github.com/k8sgpt-ai/k8sgpt/pull/1841) | The server-mode analyze handler had no test that could tell a dropped request from an empty result. |
| [nvm#3915](https://github.com/nvm-sh/nvm/pull/3915) | `nvm --help` documented a colour legend it never rendered in colour. |
| [k8sgpt-operator#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) | Tolerations support across the operator's CRD, controller and manifests. |
| [ggc#542](https://github.com/bmf-san/ggc/pull/542) | Config and command tests that only passed on Unix. |

[All merged pull requests](https://github.com/CJstate?tab=pull-requests&q=is%3Apr+is%3Amerged) ·
[hui-harness](https://github.com/CJstate/hui-harness) ·
[llm-eval-gate](https://github.com/CJstate/llm-eval-gate)
