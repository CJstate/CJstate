<div align="center">

<img src="docs/hero.svg" width="100%" alt="Jinhui Chen — the bugs CI cannot see"/>

<img src="docs/metrics-dark.svg" width="100%" alt="upstream activity metrics"/>

</div>

上面的数据板——四个数字和那排会生长的月度柱——不是第三方卡片服务画的，是这个仓库里 [render_profile.py](tools/render_profile.py) 每天从 GitHub API 拉真实数据渲染的 SVG。没有一枚徽章来自外部服务，也就没有一枚会加载失败。

写 Python 和 Go，喜欢把工具做到**零依赖**，把测试做到**任何一台机器上都能复现**。上游修 bug 专挑 CI 结构上抓不到的：符号链接、locale 编码、测试污染、被 mock 劫持的命令。**绿灯和用户报错之间那道缝，就是我在找的东西。**

## 💼 三个能说明问题的 case

<details>
<summary><b>witr#242（已合并）</b> — CI 掩盖了用户的真实环境</summary>

根目录的 `main.go` 是受版本控制的符号链接。Git for Windows 默认不检出符号链接，用户 clone 下来是一个 16 字节的文本文件，`go build` 全废——而 CI 一直是绿的，因为 `actions/checkout` 会真的建出符号链接。改成真实入口 + lint 守卫，让 CI 不再依赖 checkout 的副作用。[PR](https://github.com/pranshuparmar/witr/pull/242)

</details>

<details>
<summary><b>simonw/llm#1737</b> — 写用 UTF-8，读却吃系统编码</summary>

cp936 的 Windows 上 `llm -t 模板` 直接抛 `UnicodeDecodeError`：`templates edit` 用 `write_text(..., "utf-8")` 写，几行之后 `load_template()` 用没指定编码的 `read_text()` 读。修法是先按 UTF-8 读、确认不是合法 UTF-8 才回退 locale，老的 GBK 模板不受影响。这个页面自己的生成器，写完第一天就在 cp936 上踩了同一个坑——同一个 bug 类隔天出现在自己身上，修 bug 的人先被同一个 bug 咬了一口。[PR](https://github.com/simonw/llm/pull/1737)

</details>

<details>
<summary><b>huggingface/accelerate#4360</b> — debug_launcher 的三处 Unix 假设</summary>

`start_method` 写死 `"fork"`；rendezvous 文件用 `NamedTemporaryFile` 建、句柄攥在父进程手里，spawn 的子进程打不开；回环网卡名写死 `lo`。三处各自独立，分别修，修完本机多进程调试恢复正常。[PR](https://github.com/huggingface/accelerate/pull/4360)

</details>

<details>
<summary><b>其余已合并</b> 与完整在评清单</summary>

- [witr#239](https://github.com/pranshuparmar/witr/pull/239) — 不支持高亮 ANSI 的终端上 `--help` 配色图例静默降级（已合并）
- [nvm#3915](https://github.com/nvm-sh/nvm/pull/3915) — `nvm --help` 的 set-colors 图例输出为未着色文本（已合并）
- [k8sgpt-operator#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) — 为 CRD 与 chart 增加 tolerations（已合并）
- [dependency-track#7096](https://github.com/DependencyTrack/dependency-track/pull/7096) — README 的 CI 徽章指向已废弃分支（已合并）
- 在评 PR 的完整清单与逐条状态：[CONTRIBUTIONS.md](CONTRIBUTIONS.md)

</details>

## 🛠️ 用什么

`Python 3.9–3.13` · `Go` · `PyTorch / Transformers / Accelerate` · `pytest` · `GitHub Actions` · `Docker / Kubernetes` · 一台 cp936 的 Windows，和承受它的耐心。

---

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake.svg" />
  <img alt="contribution snake" src="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake-dark.svg" width="100%"/>
</picture>
</div>
