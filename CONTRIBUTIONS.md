# 开源贡献记录

流水账：已合并的和还在评的全部在这里，链接都是 PR 本体。

## 已合并（5）

| PR | 干了什么 | 合并日期 |
| --- | --- | --- |
| [witr#242](https://github.com/pranshuparmar/witr/pull/242) | 根目录 main.go 是符号链接，Git for Windows 默认不 clone 符号链接，clone 下来变成 16 字节文本文件，go build 直接废。CI 是绿的，因为 actions/checkout 会真的建符号链接——CI 掩盖了用户真实环境。改成真实入口 + lint 守卫 | 10-04 |
| [witr#239](https://github.com/pranshuparmar/witr/pull/239) | 不支持亮色 ANSI 的终端上 --help 配色图例悄悄失效，按终端能力逐级回退 | 10-03 |
| [nvm#3915](https://github.com/nvm-sh/nvm/pull/3915) | nvm --help 的 set-colors 图例输出成纯文本，在 help 分支里用上同一套颜色变量 | 09-03 |
| [k8sgpt-operator#855](https://github.com/k8sgpt-ai/k8sgpt-operator/pull/855) | 给 CRD 和 chart 加 tolerations，控制器能调度到被打 taint 的节点 | 10-10 |
| [dependency-track#7096](https://github.com/DependencyTrack/dependency-track/pull/7096) | README 的 CI 徽章指向废弃分支，点了 404 | 08-24 |

## 在评（25）

### 训练 / 推理（6）

| PR | 内容 | 状态 |
| --- | --- | --- |
| [accelerate#4361](https://github.com/huggingface/accelerate/pull/4361) | checkpoint 随机状态恢复失败时按 rank 告警一次，别静默跳过 | 等 review |
| [accelerate#4360](https://github.com/huggingface/accelerate/pull/4360) | debug_launcher 在 Windows 起不来：写死的 fork、临时文件句柄、回环口 lo 三处 Unix 假设 | 等 review |
| [pytorch-lightning#21975](https://github.com/Lightning-AI/pytorch-lightning/pull/21975) | enable_device_summary 与既有参数组合时不一致，补开关和文档 | 等 review |
| [datasets#8693](https://github.com/huggingface/datasets/pull/8693) | 类型注解认 List[...] 不认 Sequence[...] | 等 review |
| [pytorch-lightning#21974](https://github.com/Lightning-AI/pytorch-lightning/pull/21974) | 文档 :emphasize-lines: 行号按渲染后的行算 | 等 review |
| [pytorch-lightning#21939](https://github.com/Lightning-AI/pytorch-lightning/pull/21939) | 没符号链接权限时 skip 并说明原因，而不是 fail | 等 review |

### 评测 / 可观测（4）

| PR | 内容 | 状态 |
| --- | --- | --- |
| [mlflow#26206](https://github.com/mlflow/mlflow/pull/26206) | artifact 图片被强制缩放，小图放大糊掉；改成按容器宽度 | 有一个检查失败，待查 |
| [lm-eval-harness#4216](https://github.com/EleutherAI/lm-evaluation-harness/pull/4216) | make_table 把共享子任务算了两遍 | 等 review |
| [openllmetry#4484](https://github.com/traceloop/openllmetry/pull/4484) | Groq 流式响应的 usage 丢了；补统计和回归测试 | 等 review |
| [lm-eval-harness#4114](https://github.com/EleutherAI/lm-evaluation-harness/pull/4114) | simple_evaluate 非法输入静默给空结果 | 等 review |

### 工具链 / DX（15）

| PR | 内容 | 状态 |
| --- | --- | --- |
| [pinact#1779](https://github.com/suzuki-shunsuke/pinact/pull/1779) | debug 日志完全看不到 uses 行上发生了什么；每行补日志 | CI 绿，等 review |
| [pinact#1780](https://github.com/suzuki-shunsuke/pinact/pull/1780) | 仓库只打 tag 不发 release 时版本解析会短路 | CI 绿，等 review |
| [pinact#1781](https://github.com/suzuki-shunsuke/pinact/pull/1781) | v4 和 v4.0.0 明明是同一个版本，-u 却说要更新 | CI 绿，等 review |
| [posting#400](https://github.com/darrenburns/posting/pull/400) | 集合浏览器里高亮请求时顺带打开（可配置） | 与主干冲突，待 rebase |
| [posting#401](https://github.com/darrenburns/posting/pull/401) | 换个请求后 Response 区还挂着上一个的响应，加归属提示 | 等 review |
| [ggc#540](https://github.com/bmf-san/ggc/pull/540) | config/interactive/history 测试在 Windows 全红 | CI 绿，等 review |
| [ggc#541](https://github.com/bmf-san/ggc/pull/541) | 101 处 exec.Command("echo") mock 被真 echo.exe 劫持 | CI 绿，等 review |
| [ggc#542](https://github.com/bmf-san/ggc/pull/542) | 编辑器桩和临时目录清理的 Windows 兼容 | CI 绿，等 review |
| [witr#245](https://github.com/pranshuparmar/witr/pull/245) | 测试被 temp 目录上层真实 git 仓库污染 | 按维护者意见修改中 |
| [hallmark#77](https://github.com/Nutlope/hallmark/pull/77) | 文档里 13 处相对链接装完就 404 | 等 review |
| [llm#1737](https://github.com/simonw/llm/pull/1737) | 模板写入用 UTF-8、读取吃系统 locale，cp936 机器上直接抛 UnicodeDecodeError | 等 review |
| [jev-ultrafast#114](https://github.com/browser-use/jev-ultrafast/pull/114) | no-progress guard 把「没观测到」当成「没进展」 | CI 绿，等 review |
| [skills#1720](https://github.com/anthropics/skills/pull/1720) | mcp-builder 评估报告输出乱码，显式写 UTF-8 | 等 review |
| [public-apis#7217](https://github.com/public-apis/public-apis/pull/7217) | Pirate Weather 链接失效了 | 等 review |
| [hallmark#72](https://github.com/Nutlope/hallmark/pull/72) | macrostructure 文档补全 | 等 review |
