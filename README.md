<div align="center">

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&pause=1200&color=6EA8FE&center=true&vCenter=true&random=false&width=640&lines=%E6%8A%8A%E5%B7%A5%E5%85%B7%E5%81%9A%E5%88%B0%E9%9B%B6%E4%BE%9D%E8%B5%96%EF%BC%8C%E6%8A%8A%E6%B5%8B%E8%AF%95%E5%81%9A%E5%88%B0%E4%BB%BB%E4%BD%95%E6%9C%BA%E5%99%A8%E4%B8%8A%E9%83%BD%E8%83%BD%E5%A4%8D%E7%8E%B0;Fixing+the+bugs+CI+cannot+see)](https://github.com/CJstate)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/coding.gif" />
  <source media="(prefers-color-scheme: light)" srcset="docs/jobs.png" height="225px" />
  <img src="docs/coding.gif" />
</picture>

<div>&nbsp;</div>

<div>
  <img src="https://komarev.com/ghpvc/?username=CJstate&label=Views&color=orange&style=flat" alt="访问量统计" />
</div>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake.svg" />
  <img alt="github-snake" src="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake-dark.svg" />
</picture>

</div>

<img width="100%" src="docs/hr.gif" />

# 🙋 Hello

<table>
<tr><td>

### 🤺 About Me

<img align="right" width="88" src="docs/jobs.png" />

<p>&emsp;&emsp;嗨，我是 Jinhui Chen。写 Python 和 Go，喜欢把工具做到<strong>零依赖</strong>，把测试做到<strong>任何一台机器上都能复现</strong>。</p>
<p>&emsp;&emsp;自己写了两个小而硬的东西：一个纯标准库的编程 agent harness，一个给 LLM 评测判「真退化还是噪声」的统计门禁。</p>
<p>&emsp;&emsp;上游那边修 bug 的口味偏刁：专挑 CI 结构上抓不到的问题——符号链接、locale 编码、测试污染、被 mock 劫持的命令。<strong>绿灯和用户报错之间那道缝，就是我在找的东西。</strong></p>
<p>&emsp;&emsp;<strong>Small tools, zero dependencies, and the bugs CI cannot see.</strong></p>

</td></tr>
</table>

<img width="100%" src="docs/hr.gif" />

# 🚀 自己写的两个东西

<table>
<tr>
<td width="50%" valign="top">

#### [llm-eval-gate](https://github.com/CJstate/llm-eval-gate)

LLM 评测最烦的问题：两次跑分差了 0.3 个点，是真退化还是随机波动？吃两份 lm-evaluation-harness 结果，按每个任务自己的标准误算噪声带，只有跌幅既超相对阈值、又落在噪声带外才让 CI 挂。

纯标准库，零运行时依赖，102 个测试。

![CI](https://img.shields.io/github/actions/workflow/status/CJstate/llm-eval-gate/ci.yml?branch=main&style=flat-square&label=CI)

```bash
pip install "git+https://github.com/CJstate/llm-eval-gate@v0.1.0"
llm-eval-gate check before.json after.json
```

</td>
<td width="50%" valign="top">

#### [hui-harness](https://github.com/CJstate/hui-harness)

约 2.6k 行纯标准库的编程 agent：工具循环、权限策略、上下文压缩、多 provider SSE。最较真的设计是会话日志——哈希链追加，`hui replay` 会真的重放并逐条核对每个工具结果的 sha256，对不上直接失败。

3.10–3.13 × Linux/Windows/macOS 矩阵，140 个测试。

![CI](https://img.shields.io/github/actions/workflow/status/CJstate/hui-harness/ci.yml?branch=main&style=flat-square&label=CI)

```bash
pip install -e . && hui demo
hui replay .sessions/session-*.jsonl
```

</td>
</tr>
</table>

# 💼 上游贡献

<table>
<tr><td>

<p><strong>已合并 5 个</strong>，在评 25 个（完整清单见 <a href="CONTRIBUTIONS.md">CONTRIBUTIONS.md</a>）。挑两个能说明「CI 为什么抓不到它们」的：</p>

<details>
<summary><b>witr#242</b> — CI 掩盖了用户的真实环境</summary>

根目录的 `main.go` 是受版本控制的符号链接。Git for Windows 默认不检出符号链接，用户 clone 下来是一个 16 字节的文本文件，`go build` 全废——而 CI 一直是绿的，因为 `actions/checkout` 会真的建出符号链接。改成真实入口 + lint 守卫，让 CI 不再依赖 checkout 的副作用。[PR](https://github.com/pranshuparmar/witr/pull/242)（已合并）

</details>

<details>
<summary><b>simonw/llm#1737</b> — 写用 UTF-8，读却吃系统编码</summary>

cp936 的 Windows 上 `llm -t 模板` 直接抛 `UnicodeDecodeError`：`templates edit` 用 `write_text(..., "utf-8")` 写，几行之后 `load_template()` 用没指定编码的 `read_text()` 读。修法是先按 UTF-8 读、确认不是合法 UTF-8 才回退 locale，老的 GBK 模板不受影响，三个回归测试先红后绿。[PR](https://github.com/simonw/llm/pull/1737)

</details>

<details>
<summary><b>huggingface/accelerate#4360</b> — debug_launcher 的三处 Unix 假设</summary>

`start_method` 写死 `"fork"`；rendezvous 文件用 `NamedTemporaryFile` 建、句柄攥在父进程手里，spawn 的子进程打不开；回环网卡名写死 `lo`。三处各自独立，分别修，修完本机多进程调试恢复正常。[PR](https://github.com/huggingface/accelerate/pull/4360)

</details>

<details>
<summary><b>其余已合并</b></summary>

- [witr#239](https://github.com/pranshuparmar/witr/pull/239) — 不支持高亮 ANSI 的终端上 `--help` 配色图例静默降级，按终端能力逐级回退
- [nvm#3915](https://github.com/nvm-sh/nvm/pull/3915) — `nvm --help` 的 set-colors 图例输出为未着色文本
- [k8sgpt-operator#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) — 为 CRD 与 chart 增加 tolerations，控制器可调度到被 taint 的节点
- [dependency-track#7096](https://github.com/DependencyTrack/dependency-track/pull/7096) — README 的 CI 徽章指向已废弃分支，点开 404

</details>

</td></tr>
</table>

<img width="100%" src="docs/hr.gif" />

# 📊 Activity Overview

<div align="center">

<img align="left" width="130" src="docs/left.png" />
<img align="right" width="130" src="docs/right.png" />

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api?username=CJstate&show_icons=true&hide_border=true&bg_color=00000000&title_color=6ea8fe&icon_color=3fb6a8&text_color=aebdda&include_all_commits=true" />
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-stats.vercel.app/api?username=CJstate&show_icons=true&hide_border=true&bg_color=00000000&title_color=0969da&icon_color=1f883d&text_color=1f2328&include_all_commits=true" />
  <img src="https://github-readme-stats.vercel.app/api?username=CJstate&show_icons=true&hide_border=true&bg_color=00000000&include_all_commits=true" />
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-streak-stats.herokuapp.com?user=CJstate&hide_border=true&background=00000000&stroke=24306a&ring=6ea8fe&fire=3fb6a8&currStreakLabel=6ea8fe" />
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-streak-stats.herokuapp.com?user=CJstate&hide_border=true&background=00000000&stroke=d0d7de&ring=0969da&fire=1f883d&currStreakLabel=0969da" />
  <img src="https://github-readme-streak-stats.herokuapp.com?user=CJstate&hide_border=true" />
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-activity-graph.vercel.app/graph?username=CJstate&theme=react-dark&bg_color=1B222D&hide_border=true" />
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-activity-graph.vercel.app/graph?username=CJstate&theme=xcode&hide_border=true" />
  <img src="https://github-readme-activity-graph.vercel.app/graph?username=CJstate&theme=react-dark&hide_border=true" />
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="profile-3d-contrib/profile-night-rainbow.svg" />
  <source media="(prefers-color-scheme: light)" srcset="profile-3d-contrib/profile-gitblock.svg" />
  <img src="profile-3d-contrib/profile-night-rainbow.svg" />
</picture>

</div>

<img width="100%" src="docs/hr.gif" />

# 🛠️ Tech Stack

<div align="center">

![Python Badge](https://img.shields.io/badge/Python-3.9%E2%80%933.13-3776AB?logo=python&logoColor=fff&style=flat)
![PyTorch Badge](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=fff&style=flat)
![Transformers Badge](https://img.shields.io/badge/Transformers-FFD21E?logo=huggingface&logoColor=000&style=flat)
![Go Badge](https://img.shields.io/badge/Go-00ADD8?logo=go&logoColor=fff&style=flat)
![Docker Badge](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff&style=flat)
![Kubernetes Badge](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=fff&style=flat)
![GitHub Actions Badge](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=fff&style=flat)
![Linux Badge](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=000&style=flat)
![Windows Badge](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=fff&style=flat)

<img src="https://skillicons.dev/icons?i=python,pytorch,go,docker,kubernetes,linux,git,github&perline=8" />

</div>

---
