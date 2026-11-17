# CJstate

Backend engineer. I work on Go infrastructure, cloud-native tooling, and the unglamorous edges of I/O where errors get lost and state goes stale.

**Stack:** Go · Python · Rust · Kubernetes · Prometheus · Docker · GitHub Actions

I start from a reproducible failure, write the test that exposes it, and ship the smallest change that makes the suite green. Most of the bugs below were found on a Windows machine running a real clone — the ones Linux CI never sees.

## Selected open source work

Merged pull requests only. A few representative fixes across 19 upstream projects:

### Go / systems

- **[valyala/fasthttp](https://github.com/valyala/fasthttp/pulls?q=is%3Apr+author%3ACJstate+is%3Amerged)** — `WriteTo` implementations in five exported types returned the raw result of one `w.Write`, silently accepting short writes. Now report `io.ErrShortWrite` so callers can detect partial output ([#2541](https://github.com/valyala/fasthttp/pull/2541), with follow-ups in [#2542](https://github.com/valyala/fasthttp/pull/2542), [#2543](https://github.com/valyala/fasthttp/pull/2543)). Also fixed `Accept-Encoding` parsing that stopped scanning after a `q=0` member ([#2590](https://github.com/valyala/fasthttp/pull/2590)).

- **[klauspost/compress](https://github.com/klauspost/compress/pulls?q=is%3Apr+author%3ACJstate+is%3Amerged)** — `gzip.Reader.WriteTo` reused `z.err` as both the write-error slot and the end-of-stream marker, so a failed destination write was mistaken for a clean finish and the CRC check was skipped. Writer errors are now wrapped and kept distinct from `io.EOF` ([#1302](https://github.com/klauspost/compress/pull/1302)). Related fixes cover short writes in flate and s2 ([#1303](https://github.com/klauspost/compress/pull/1303), [#1304](https://github.com/klauspost/compress/pull/1304), [#1316](https://github.com/klauspost/compress/pull/1316)).

- **[juanfont/headscale](https://github.com/juanfont/headscale/pull/3650)** — pre-0.23 databases without a migrations table were migrated blindly and could be corrupted. They are now rejected with a clear error.

- **[bmf-san/ggc](https://github.com/bmf-san/ggc/pull/542)** — config and command test suites used Unix-only process mocks, so `go test` failed on Windows even though CI stayed green. Reworked the mocks and added a guard against tracked symlinks in [witr](https://github.com/pranshuparmar/witr/pull/242), another Windows build breakage.

### Cloud native / observability

- **[k8sgpt-ai/k8sgpt](https://github.com/k8sgpt-ai/k8sgpt/pull/1845)** — added an `exclusions` config key so operators can mute known findings by content hash with an expiry, applied consistently in CLI and server mode with the muted count reported.

- **[k8sgpt-ai/k8sgpt-operator](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855)** — exposed tolerations through the CRD and Helm chart so the controller can schedule on tainted nodes.

- **[prometheus/prometheus](https://github.com/prometheus/prometheus/pull/20352)** — `MetricFamiliesToWriteRequest` looked up gauge-histogram metadata with the `dto` enum name (`GAUGE_HISTOGRAM`) against a map keyed by the `prompb` name (`GAUGEHISTOGRAM`), dropping the type. Fixed the mapping so remote-write metadata survives.

- **[cybozu-go/moco](https://github.com/cybozu-go/moco/pull/966)** — added `podLabels` and `podAnnotations` to the Helm chart so controller pods can carry custom metadata.

### Workflow / tooling

- **[dagucloud/dagu](https://github.com/dagucloud/dagu/pulls?q=is%3Apr+author%3ACJstate+is%3Amerged)** — a series of fixes across the workflow engine: unknown-key validation for eight executors, `repeat_policy.on_limit: fail` for exhausted `until` loops, inheriting a `foreach` parent's environment in body steps, and step-output references in `working_dir`.

- **[Lynpoint/CyberVerse](https://github.com/Lynpoint/CyberVerse/pulls?q=is%3Apr+author%3ACJstate+is%3Amerged)** — RAG fixes: explicit zero-valued config fields no longer fall back to defaults, Milvus delete expressions escape backslashes and quotes, plugin shutdown continues after a startup failure, and YAML `${VAR}` expansion treats env values as data rather than re-parsing them as YAML.

## Projects

### [Veritas-Harness](https://github.com/CJstate/Veritas-Harness)

An audit-friendly runtime for coding agents. Every tool call, model reply, and MCP request is appended to a hash-chained JSONL log; `veritas replay` verifies the chain, re-runs the tools, and diffs each result by SHA-256. A run is verified, not trusted.

- 141 tests, no runtime dependencies; CI green on Linux / Windows / macOS × Python 3.10–3.13
- Built for real Windows environments: UTF-8 → GBK → Latin-1 fallback with BOM and CRLF preserved
- Includes a tamper demo where replay rejects an edited session before any tool runs

### [EvalGuard](https://github.com/CJstate/EvalGuard)

A CI gate for LLM evaluations. Given `before` and `after` result files, it decides whether a benchmark genuinely regressed using a relative threshold plus a standard-error band — not a red build over a third-decimal wobble.

- 107 tests, no runtime dependencies; CI green
- Offline demo where MMLU stays inside the noise band and GSM8K correctly fails the gate

## Activity

<p align="center">
  <img src="https://cdn.jsdelivr.net/gh/CJstate/CJstate@main/docs/profile-stats.svg" alt="GitHub stats" />
</p>

<p align="center">
  <img src="https://cdn.jsdelivr.net/gh/CJstate/CJstate@main/docs/profile-streak.svg" alt="Contribution streak" />
</p>

## Contact

1507965754@qq.com · [github.com/CJstate](https://github.com/CJstate)
