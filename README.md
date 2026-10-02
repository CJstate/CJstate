<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/CJstate/CJstate@main/docs/banner-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://cdn.jsdelivr.net/gh/CJstate/CJstate@main/docs/banner-light.svg" />
  <img src="https://cdn.jsdelivr.net/gh/CJstate/CJstate@main/docs/banner-dark.svg" alt="CJstate" width="100%" />
</picture>

**AI / LLM 工程 · Python · 分布式训练 · 模型评测**

<a href="https://github.com/CJstate"><img src="https://img.shields.io/badge/GitHub-CJstate-181717?style=flat-square&logo=github&logoColor=white" /></a>
<img src="https://img.shields.io/badge/Focus-AI%20%2F%20LLM%20Engineering-22D3EE?style=flat-square" />
<img src="https://img.shields.io/github/followers/CJstate?label=Followers&style=flat-square&color=ec4899&logo=github" />

</div>

---

### 关于 · About

- **方向**：大模型训练与推理基础设施、模型评测、可观测性
- **日常**：读上游 issue → 本地复现 → 写最小修复 + 回归测试 → 提 PR，跟进 review
- **偏好**：改动可验证、能被上游接受；不堆砌无法验证的技能清单

---

### 上游贡献 · Upstream Contributions

#### 协作中 · In Review

| 项目 | PR | 内容 |
|------|----|------|
| huggingface/accelerate | [#4360](https://github.com/huggingface/accelerate/pull/4360) | `debug_launcher` Windows 支持（fork / 临时文件 / gloo 网卡名） |
| Lightning-AI/pytorch-lightning | [#21975](https://github.com/Lightning-AI/pytorch-lightning/pull/21975) | 新增 `enable_device_summary` 开关 |
| huggingface/datasets | [#8693](https://github.com/huggingface/datasets/pull/8693) | `PathLike` 类型注解 `List` → `Sequence` |
| anthropics/skills | [#1720](https://github.com/anthropics/skills/pull/1720) | 评估报告按 UTF-8 写出（Windows cp1252 下崩溃） |
| pranshuparmar/witr | [#239](https://github.com/pranshuparmar/witr/pull/239) | 无亮色 ANSI 支持的终端保留颜色 |
| EleutherAI/lm-evaluation-harness | [#4216](https://github.com/EleutherAI/lm-evaluation-harness/pull/4216) | `make_table` 重复共享子任务修复 |
| EleutherAI/lm-evaluation-harness | [#4114](https://github.com/EleutherAI/lm-evaluation-harness/pull/4114) | `simple_evaluate()` 输入校验回归测试 |
| traceloop/openllmetry | [#4484](https://github.com/traceloop/openllmetry/pull/4484) | Groq 流式：`usage` 被空 `choices` 早退丢弃 |
| mlflow/mlflow | [#26206](https://github.com/mlflow/mlflow/pull/26206) | artifact 图片缩放修复 |
| Lightning-AI/pytorch-lightning | [#21939](https://github.com/Lightning-AI/pytorch-lightning/pull/21939) | Windows 无符号链接权限时跳过测试 |
| browser-use/jev-ultrafast | [#114](https://github.com/browser-use/jev-ultrafast/pull/114) | no-progress guard 需考虑未观测结果 |

#### 已合并 · Merged

| 项目 | PR | 内容 |
|------|----|------|
| nvm-sh/nvm | [#3915](https://github.com/nvm-sh/nvm/pull/3915) | `nvm --help` 颜色图例渲染 |
| DependencyTrack/dependency-track | [#7096](https://github.com/DependencyTrack/dependency-track/pull/7096) | README CI 徽章指向 main 分支 |

完整列表见 [Pull Requests](https://github.com/CJstate?tab=pull-requests)。

---

### 自己的项目 · Own Projects

| 项目 | 说明 | 技术 |
|------|------|------|
| [**llm-eval-gate**](https://github.com/CJstate/llm-eval-gate) | 比较两次 `lm-evaluation-harness` 结果，用相对阈值 + stderr 显著性噪声带判定评测回归，让 CI 在真正变差时失败、在噪声范围内放行 | Python 标准库 · GitHub Action · 102 测试 · MIT |
| [**fold-blur-demo**](https://github.com/CJstate/fold-blur-demo) | 折叠屏雾化 / 磨砂玻璃效果演示 | 纯 CSS `backdrop-filter` |

---

### 技术栈 · Stack

`Python` · `PyTorch` · `Transformers` · `vLLM` · `Lightning` · `Hugging Face Datasets / Accelerate` · `pytest` · `GitHub Actions` · `Linux`

---

<div align="center">

<img src="https://streak-stats.demolab.com?user=CJstate&theme=tokyonight&hide_border=true&fire=ec4899&ring=22d3ee" alt="GitHub Streak" />

<sub>这个主页只写能点开验证的东西。</sub>

</div>
