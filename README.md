# CJstate

Backend Engineer | Cloud Native | Data Infra — I fix correctness defects that only surface in real environments, with a failing regression test before every patch.

**Go** · **Python** · **K8s** · **Docker** · **Prometheus**

## Selected contributions

Merged upstream pull requests, each with the defect it removed:

- [juanfont/headscale#3650](https://github.com/juanfont/headscale/pull/3650) — Reject pre-0.23 databases that lack a migrations table instead of migrating them blindly.
- [pranshuparmar/witr#242](https://github.com/pranshuparmar/witr/pull/242) — Replaced a symlinked root `main.go` that Git for Windows checks out as a 16-byte text file, so `go build` failed on a real clone while CI stayed green; added a lint guard.
- [dagucloud/dagu#3554](https://github.com/dagucloud/dagu/pull/3554) — Honour `mark_success` for non-retryable exit codes.
- [dagucloud/dagu#3578](https://github.com/dagucloud/dagu/pull/3578) — Regenerate `llms.txt` and add a CI check that keeps it in sync with the skills tree.
- [k8sgpt-ai/k8sgpt-operator#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) — Add tolerations to the K8sGPT CRD and chart so the controller can run on tainted nodes.
- [bmf-san/ggc#542](https://github.com/bmf-san/ggc/pull/542) — Make the config and command tests pass on Windows.

## Open source

I strictly follow TDD and ensure all CI checks pass before submitting a PR. No spam, no low-value commits.
