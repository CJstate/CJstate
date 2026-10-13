<div align="center">

<img src="docs/banner-light.svg" width="92%" alt="CJstate · AI/LLM engineering">

[5 个 PR 已合并](#已合并) · [25 个在评](#在评) · [llm-eval-gate](https://github.com/CJstate/llm-eval-gate) · [hui-harness](https://github.com/CJstate/hui-harness)

</div>

你好，我是 CJstate。

过去一年主要在做一件事：给上游开源项目修 Windows 和编码相关的 bug。这类问题有几个特点——复现需要特定的系统 locale、特定的文件系统行为，或者一次真实的 `git clone`；报错离根因往往隔了好几层；维护者大多在 Linux/macOS 上开发，很难亲手踩到。所以这类 issue 常常挂着没人动，而修起来其实不难，难的是找到它。

目前已合并 5 个 PR（witr×2、nvm、k8sgpt-operator、dependency-track），在评 25 个，分布在 pytorch-lightning、accelerate、datasets、mlflow、llm 这些项目里。下面这些全部是真实链接，点开就是 PR 本体。

## 已合并

| 项目 | PR | 干了什么 | 合并日期 |
| --- | --- | --- | --- |
| [witr](https://github.com/pranshuparmar/witr) 22.6k★ | [#242](https://github.com/pranshuparmar/witr/pull/242) | 根目录的 `main.go` 是个符号链接。Git for Windows 默认 `core.symlinks=false`，clone 下来变成一个 16 字节的文本文件，`go build` 直接废掉。CI 是绿的，因为 `actions/checkout` 会真的建符号链接——CI 掩盖了用户真实环境。改成真实入口 + lint 守卫。 | 10-04 |
| [witr](https://github.com/pranshuparmar/witr) 22.6k★ | [#239](https://github.com/pranshuparmar/witr/pull/239) | 不支持亮色 ANSI 的终端上 `--help` 配色图例悄悄失效。按终端能力逐级回退。 | 10-03 |
| [nvm](https://github.com/nvm-sh/nvm) 95.3k★ | [#3915](https://github.com/nvm-sh/nvm/pull/3915) | `nvm --help` 的 set-colors 图例输出成纯文本。在 help 分支里用上同一套颜色变量。 | 09-03 |
| [k8sgpt-operator](https://github.com/k8sgpt-ai/k8sgpt-operator) | [#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) | 给 K8sGPT 的 CRD 和 chart 加 tolerations，控制器能调度到被打 taint 的节点。 | 10-10 |
| [dependency-track](https://github.com/DependencyTrack/dependency-track) | [#7096](https://github.com/DependencyTrack/dependency-track/pull/7096) | README 的 CI 徽章指向废弃分支，点了 404。 | 08-24 |

## 两个印象深的 case

<details>
<summary><b>simonw/llm#1737：写文件用 UTF-8，读回来却用系统编码</b></summary>

在 cp936 的 Windows 上，`llm -t 模板` 直接抛 `UnicodeDecodeError: 'gbk' codec can't decode`。查下来很好笑：`llm templates edit` 新建模板时用 `write_text(..., "utf-8")` 写的，几行之后 `load_template()` 用 `read_text()` 读——没有指定编码，吃了 locale 默认值。同一个函数族三处入口都这样。

修法是加一个 `_read_text_file()`：先按 UTF-8 读，文件确实不是合法 UTF-8 才回退 locale，这样老的 GBK 文件不会坏。仓库里 `embed-multi --files` 本来就有类似回退，算是顺着既有约定。三个回归测试先红后绿。

[PR](https://github.com/simonw/llm/pull/1737) · 等维护者批准 workflow
</details>

<details>
<summary><b>accelerate#4360：debug_launcher 起不来，三处 Unix 假设</b></summary>

`accelerate debug_launcher script.py` 在 Windows 上先是 `cannot find context for 'fork'`——代码写死了 `start_method="fork"`。绕过这个之后是 `PermissionError`：rendezvous 文件用 `NamedTemporaryFile` 建的，句柄还攥在父进程手里，spawn 出来的子进程当然打不开。再往后还有一处，`gloo_socket_ifname="lo"`，Windows 的回环口不叫 lo。

三个点各修各的：按平台能力选启动方式；临时文件换成 `TemporaryDirectory` 只传路径；探测到 `lo` 存在才设环境变量。修完本机能正常起多进程调试了。

[PR](https://github.com/huggingface/accelerate/pull/4360) · 等批准 workflow
</details>

## 在评（25）

<details open>
<summary><b>训练 / 推理（6）</b></summary>

| PR | 内容 |
| --- | --- |
| [accelerate#4361](https://github.com/huggingface/accelerate/pull/4361) | checkpoint 随机状态恢复失败时按 rank 告警一次，别静默跳过 |
| [accelerate#4360](https://github.com/huggingface/accelerate/pull/4360) | 上面那个 debug_launcher |
| [pytorch-lightning#21975](https://github.com/Lightning-AI/pytorch-lightning/pull/21975) | `enable_device_summary` 与既有参数组合时不一致，补开关和文档 |
| [datasets#8693](https://github.com/huggingface/datasets/pull/8693) | 类型注解认 `List[...]` 不认 `Sequence[...]` |
| [pytorch-lightning#21974](https://github.com/Lightning-AI/pytorch-lightning/pull/21974) | 文档 `:emphasize-lines:` 行号按渲染后的行算 |
| [pytorch-lightning#21939](https://github.com/Lightning-AI/pytorch-lightning/pull/21939) | 没符号链接权限时 skip 并说明原因，而不是 fail |

</details>

<details open>
<summary><b>评测 / 可观测（4）</b></summary>

| PR | 内容 |
| --- | --- |
| [mlflow#26206](https://github.com/mlflow/mlflow/pull/26206) | artifact 图片被强制缩放，小图放大糊掉；改成按容器宽度 |
| [lm-eval-harness#4216](https://github.com/EleutherAI/lm-evaluation-harness/pull/4216) | `make_table` 把共享子任务算了两遍 |
| [openllmetry#4484](https://github.com/traceloop/openllmetry/pull/4484) | Groq 流式响应的 usage 丢了；补统计和回归测试 |
| [lm-eval-harness#4114](https://github.com/EleutherAI/lm-evaluation-harness/pull/4114) | `simple_evaluate` 非法输入静默给空结果 |

</details>

<details open>
<summary><b>工具链 / DX（15）</b></summary>

| PR | 内容 |
| --- | --- |
| [pinact#1779](https://github.com/suzuki-shunsuke/pinact/pull/1779) | debug 日志完全看不到 `uses` 行上发生了什么；每行补日志 |
| [pinact#1780](https://github.com/suzuki-shunsuke/pinact/pull/1780) | 仓库只打 tag 不发 release 时版本解析会短路 |
| [pinact#1781](https://github.com/suzuki-shunsuke/pinact/pull/1781) | `v4` 和 `v4.0.0` 明明是同一个版本，`-u` 却说要更新 |
| [posting#400](https://github.com/darrenburns/posting/pull/400) | 集合浏览器里高亮请求时顺带打开（可配置） |
| [posting#401](https://github.com/darrenburns/posting/pull/401) | 换个请求后 Response 区还挂着上一个的响应，加归属提示 |
| [ggc#540](https://github.com/bmf-san/ggc/pull/540) | config/interactive/history 测试在 Windows 全红 |
| [ggc#541](https://github.com/bmf-san/ggc/pull/541) | 101 处 `exec.Command("echo")` mock 被真 echo.exe 劫持 |
| [ggc#542](https://github.com/bmf-san/ggc/pull/542) | 编辑器桩和临时目录清理的 Windows 兼容 |
| [witr#245](https://github.com/pranshuparmar/witr/pull/245) | 测试被 temp 目录上层真实 git 仓库污染 |
| [hallmark#77](https://github.com/Nutlope/hallmark/pull/77) | 文档里 13 处相对链接装完就 404 |
| [llm#1737](https://github.com/simonw/llm/pull/1737) | 上面那个 UTF-8 case |
| [jev-ultrafast#114](https://github.com/browser-use/jev-ultrafast/pull/114) | no-progress guard 把「没观测到」当成「没进展」 |
| [skills#1720](https://github.com/anthropics/skills/pull/1720) | mcp-builder 评估报告输出乱码，显式写 UTF-8 |
| [public-apis#7217](https://github.com/public-apis/public-apis/pull/7217) | Pirate Weather 链接失效了 |
| [hallmark#72](https://github.com/Nutlope/hallmark/pull/72) | macrostructure 文档补全 |

</details>

## 自己的两个项目

<table>
<tr>
<td width="50%" valign="top">

#### [llm-eval-gate](https://github.com/CJstate/llm-eval-gate)

跑 LLM 评测的时候经常遇到一个烦人的问题：两次跑分差了 0.3 个点，到底是真退化还是随机波动？这个工具吃两份 lm-evaluation-harness 的结果文件，用相对阈值加标准误噪声带来判定，输出就是 CI 退出码。

<a href="https://github.com/CJstate/llm-eval-gate/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/CJstate/llm-eval-gate/ci.yml?branch=main&style=flat-square&label=CI&color=2ea043"></a>
<img src="https://img.shields.io/badge/tests-102-2ea043?style=flat-square">
<img src="https://img.shields.io/github/v/release/CJstate/llm-eval-gate?style=flat-square&label=release">
<img src="https://img.shields.io/badge/runtime_deps-0-2ea043?style=flat-square">

```bash
pip install "git+https://github.com/CJstate/llm-eval-gate@v0.1.0"
llm-eval-gate check before.json after.json
```

</td>
<td width="50%" valign="top">

#### [hui-harness](https://github.com/CJstate/hui-harness)

一个大概 3k 行的编程 Agent，纯标准库。工具调用循环、权限策略、会话日志这些基本功。比较较真的一个点：会话文件是哈希链，`hui replay` 会真的重跑一遍并逐条核对 sha256，链对不上直接失败。破坏性命令要显式授权。

<img src="https://img.shields.io/badge/tests-139-2ea043?style=flat-square">
<img src="https://img.shields.io/badge/runtime_deps-0-2ea043?style=flat-square">
<img src="https://img.shields.io/badge/python-3.10%E2%80%933.13-0969da?style=flat-square&logo=python&logoColor=white">

```bash
pip install -e . && hui demo
hui replay .sessions/session-*.jsonl
```

</td>
</tr>
</table>

## 怎么干活

修一个 bug 的流程固定：先在本机完整复现，把原始报错贴进 PR；改动只碰根因相关的行，不带格式化；能写测试的一定带一个先失败的测试。挑问题的时候专门找环境类的——编码、文件系统、CI 门禁这些，因为这类问题我有一台真实的 Windows 机器，而很多维护者没有。

技术栈：Python（3.9–3.13）、Go、TypeScript；训练推理侧 PyTorch / Transformers / Accelerate / vLLM；评测侧 Datasets / lm-evaluation-harness / MLflow。

---

<p align="center">
<sub>有需要可以邮件联系：1507965754@qq.com</sub>
</p>
