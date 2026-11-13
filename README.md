<div align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=28&pause=1000&color=36BCF7&center=true&vCenter=true&width=600&lines=Backend+Engineer;Cloud+Native+Developer;Data+Infrastructure+Enthusiast;TDD+Advocate" alt="Typing SVG" />
</div>

<div align="center">
  <img src="https://komarev.com/ghpvc/?username=CJstate&style=for-the-badge&color=blue" alt="Profile Views" />
  <img src="https://img.shields.io/github/followers/CJstate?style=for-the-badge&color=blue" alt="Followers" />
</div>

---

### Hi, I'm CJstate 👋

Backend engineer working on **Go infrastructure, cloud-native tooling, and reliable data paths**. I reproduce a defect locally, write the failing test first, and open a PR only after the affected suites, vet, and formatting are green. Most fixes start with a failure I actually hit: a writer that accepts only part of a buffer, a reader that mistakes a write error for a clean end of stream, an inherited environment scope that quietly widens.

#### 💻 Stack

<div align="center">

![Go](https://img.shields.io/badge/Go-00ADD8?style=for-the-badge&logo=go&logoColor=white) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![Rust](https://img.shields.io/badge/Rust-000000?style=for-the-badge&logo=rust&logoColor=white)

![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black) ![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)

</div>

#### 🚀 Featured Open Source Contributions

> Merged pull requests only. Still-open and withdrawn PRs are deliberately omitted - I would rather show the fixes that actually shipped.

- 🛠️ **[klauspost/compress - #1302](https://github.com/klauspost/compress/pull/1302)**: `gzip.Reader.WriteTo` stored a destination write error in `z.err`, which doubles as the end-of-stream marker. A failed write was therefore mistaken for a clean end of stream and the CRC/trailer check was silently skipped. Writer errors are now wrapped with `%w` so they stay distinct from `io.EOF`. Merged by the author.

- ⚡ **[k8sgpt-ai/k8sgpt - #1845](https://github.com/k8sgpt-ai/k8sgpt/pull/1845)**: Findings already known to an operator had no way to be silenced, so every analysis re-reported them. Added an `exclusions` config key with a content hash and expiry, applied before analysis and in server mode, with the muted count reported so a mute cannot silently swallow findings.

- 🐳 **[dagucloud/dagu](https://github.com/dagucloud/dagu/pulls?q=is%3Apr+author%3ACJstate+is%3Amerged)**: A run of merged fixes across the workflow engine - unknown-key validation for the `jq`, `http`, `archive`, `s3`, `redis`, `postgres`, `sqlite`, and `mail` executors ([#3558](https://github.com/dagucloud/dagu/pull/3558), [#3559](https://github.com/dagucloud/dagu/pull/3559), [#3570](https://github.com/dagucloud/dagu/pull/3570)-[#3574](https://github.com/dagucloud/dagu/pull/3574)), `repeat_policy.on_limit: fail` for exhausted `until` loops ([#3651](https://github.com/dagucloud/dagu/pull/3651)), and inheriting a `foreach` parent's env scope in body steps ([#3657](https://github.com/dagucloud/dagu/pull/3657)).

- 🗄️ **[cybozu-go/moco - #966](https://github.com/cybozu-go/moco/pull/966)**: The Helm chart gave controller pods no way to carry custom metadata. Added support for custom labels and annotations on controller pods.

- 📦 **[klauspost/compress - #1303](https://github.com/klauspost/compress/pull/1303)**: Kept `ErrCorrupt` instead of losing the failure when `s2.Skip` rejects an oversized chunk, so a corrupt stream cannot be reported as a clean skip. Its sibling [flate fix - #1304](https://github.com/klauspost/compress/pull/1304) keeps the reader failed after a short write inside `WriteTo`.

---

#### 📊 Activity

<div align="center">
  <img src="https://cdn.jsdelivr.net/gh/CJstate/CJstate@main/docs/profile-stats.svg" alt="GitHub Stats" />
  <img src="https://cdn.jsdelivr.net/gh/CJstate/CJstate@main/docs/profile-streak.svg" alt="Contribution Streak" />
</div>

<div align="center">
  <img src="https://cdn.jsdelivr.net/gh/CJstate/CJstate@main/docs/profile-langs.svg" alt="Top Languages" />
</div>

---

#### 🐍 Contribution Graph

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./docs/snake-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./docs/snake-light.svg">
    <img src="./docs/snake-dark.svg" alt="Contribution snake eating the real contribution graph" width="900">
  </picture>
</div>

---

<br/>

### 🤝 Connect with me

<div align="center">

Bug reports, reproducible failures, and patches for upstream Go projects are always welcome.
The fastest way to reach me is email; the profile above stays the source of truth for my work.

</div>

<div align="center">
  <a href="mailto:1507965754@qq.com">
    <img src="https://img.shields.io/badge/Email-1507965754%40qq.com-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email" />
  </a>
  <a href="https://github.com/CJstate">
    <img src="https://img.shields.io/badge/GitHub-CJstate-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" />
  </a>
</div>

<br/>

<div align="center">

*"Reproduce it. Write the failing test. Ship the smallest fix that makes it green."*

</div>
