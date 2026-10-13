<div align="center">

<img src="docs/header.svg" width="100%" alt="Jinhui Chen"/>

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=19&pause=1400&color=6EA8FE&center=true&vCenter=true&random=false&width=700&lines=Fixing+the+bugs+CI+cannot+see;Zero-dependency+tooling+in+pure+stdlib;Reading+a+codebase+until+it+makes+sense)](https://github.com/CJstate)

</div>

我做的东西通常很小，但要求能一口气读完：一个零依赖的编程 agent，一个给 LLM 评测判「真退化还是噪声」的统计门禁。小不是妥协——能在一个下午读完的东西，才谈得上被信任。

上游那边，我修的 bug 有一个共同点：**CI 结构上抓不到它们**。仓库入口是个符号链接，`actions/checkout` 会老老实实建出符号链接，用户机器上却只是一个 16 字节的文本文件；测试污染了共享单例，本地按文件名字母序跑恰好不炸，随机顺序下全线崩；mock 劫持了 `echo`，只有在没装 GNU coreutils 的机器上才现形。**绿灯和用户报错之间那道缝，就是我在找的东西**——这类问题不难修，难的是意识到它存在。

## 自己写的两个东西

<table>
<tr>
<td width="50%" valign="top">

#### [llm-eval-gate](https://github.com/CJstate/llm-eval-gate)

LLM 评测里最烦的一件事：两次跑分差了 0.3 个点，是真退化还是随机波动？这个工具吃两份 lm-evaluation-harness 结果，按每个任务自己的标准误算出噪声带，只有当跌幅既超过相对阈值、又落在噪声带外才让 CI 挂。

零运行时依赖，纯标准库，102 个测试。

![CI](https://img.shields.io/github/actions/workflow/status/CJstate/llm-eval-gate/ci.yml?branch=main&style=flat-square&label=CI)

```bash
pip install "git+https://github.com/CJstate/llm-eval-gate@v0.1.0"
llm-eval-gate check before.json after.json
```

</td>
<td width="50%" valign="top">

#### [hui-harness](https://github.com/CJstate/hui-harness)

约 3k 行纯标准库的编程 agent：工具循环、权限策略、上下文压缩、多provider SSE。最较真的一个设计是会话日志——哈希链追加，`hui replay` 会真的重放并逐条核对每个工具结果的 sha256，对不上就直接失败。可复现不是口号，是 CI 里跑的一条断言。

3.10–3.13 × Linux/Windows/macOS 矩阵，139 个测试。

![CI](https://img.shields.io/github/actions/workflow/status/CJstate/hui-harness/ci.yml?branch=main&style=flat-square&label=CI)

```bash
pip install -e . && hui demo
hui replay .sessions/session-*.jsonl
```

</td>
</tr>
</table>

## 上游修复

<details open>
<summary><b>已合并</b></summary>

- [witr#242](https://github.com/pranshuparmar/witr/pull/242) — 根 `main.go` 是受版本控制的符号链接，Git for Windows 默认不检出符号链接，clone 下来是个 16 字节文本文件，`go build` 全废。CI 一直是绿的，因为 `actions/checkout` 会真的建出符号链接——**CI 掩盖了用户真实环境**。改成真实入口 + lint 守卫。
- [witr#239](https://github.com/pranshuparmar/witr/pull/239) — 不支持高亮 ANSI 的终端上，`--help` 的配色图例静默降级；改为按终端能力逐级回退。
- [nvm#3915](https://github.com/nvm-sh/nvm/pull/3915) — `nvm --help` 里 set-colors 图例输出为未着色文本。
- [k8sgpt-operator#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) — 为 CRD 与 chart 增加 tolerations，控制器可调度到被 taint 的节点。
- [dependency-track#7096](https://github.com/DependencyTrack/dependency-track/pull/7096) — README 的 CI 徽章指向已废弃分支，点开 404。

</details>

<details>
<summary><b>两个花了比较久的 case</b></summary>

**simonw/llm#1737** — cp936 的 Windows 上 `llm -t 模板` 直接抛 `UnicodeDecodeError`。查下来是 `templates edit` 用 `write_text(..., "utf-8")` 写模板，几行之后 `load_template()` 用没指定编码的 `read_text()` 读——同一个函数族三处入口都这样。修法是加一层 `_read_text_file()`：先按 UTF-8 读，确认不是合法 UTF-8 才回退 locale，老的 GBK 模板不受影响。三个回归测试先红后绿。[PR](https://github.com/simonw/llm/pull/1737)

**huggingface/accelerate#4360** — `debug_launcher` 在 Windows 上起不来，三处 Unix 假设各自独立：`start_method` 写死 `"fork"`；rendezvous 文件用 `NamedTemporaryFile` 建，句柄还攥在父进程手里，spawn 出的子进程打不开；回环网卡名写死 `lo`。三处分别修，本机多进程调试恢复正常。[PR](https://github.com/huggingface/accelerate/pull/4360)

</details>

还没合并的清单在 [CONTRIBUTIONS.md](CONTRIBUTIONS.md)。

## 常用的

![Python](https://img.shields.io/badge/Python-3.9–3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![Transformers](https://img.shields.io/badge/Transformers-FFD21E?style=flat-square&logo=huggingface&logoColor=black)
![Go](https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake-dark.svg"/>
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake.svg"/>
  <img alt="contribution snake" src="https://raw.githubusercontent.com/CJstate/CJstate/output/github-contribution-grid-snake.svg"/>
</picture>
</div>

---

1507965754@qq.com
