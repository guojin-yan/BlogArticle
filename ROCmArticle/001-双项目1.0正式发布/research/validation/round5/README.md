# 第五轮：Windows 路径修正与四案例真实数据复跑

2026-11-21，基于文章 v7 / `9727a7d` 继续排查。三个正式源码仓库保持只读；应用仍为提交 `2f70b96267484b441fa726a3d496b8cc55d47219` 的既有快照和 DLL。本轮修改的是文章运行包装脚本与证据编排，没有替换引擎、模型、官方标签或阈值。

## 编译故障的定位与修正

在同一 Windows 11 / W7900 gfx1100 / ROCm 10.1 / MIGraphX 2.18 环境，以同一 MatMul 模型直接调用原生 C API，仅改变设备库路径变量：

| 对照 | hipBLASLt 路径 | rocBLAS 路径 | 结果 |
| --- | --- | --- | --- |
| `native-matmul-base` | Windows 反斜杠 | 反斜杠 | Compile 通过；该次启用 trace |
| `native-backslash-repeat` | 反斜杠 | 反斜杠 | 不启用 trace，重复通过 |
| `native-forward-blas` | 正斜杠 | 正斜杠 | 访问冲突，读取地址 `0x80` |
| `native-forward-hipblaslt` | 仅此项改正斜杠 | 反斜杠 | 同样访问冲突 |
| `native-forward-rocblas` | 反斜杠 | 仅此项改正斜杠 | Compile 通过 |
| `native-mixed-hipblaslt` | 根目录反斜杠、后缀正斜杠，复现旧脚本拼接 | 反斜杠 | 同样访问冲突 |

证据见 [commands](commands/) 和 [原始日志](logs/)。这确定了**本机这套原生二进制的 hipBLASLt 路径触发条件及有效修正**；没有调试符号或上游源码级堆栈，不能进一步声称已查明原生库内部哪一行存在缺陷，也不外推到所有 Windows/ROCm 版本。

`examples/run-windows.ps1` 对 SDK 根目录做完整路径解析，再用 `Join-Path` 生成 Windows 环境变量。读者输入正、反斜杠的两次 C# 实跑都完成 MatMul 编译、执行与 4,096 元素的 CPU/Host GPU/联合 GPU 对照，三个输出比较的最大绝对误差均为 0。见 [正斜杠输入](matmul-forward.json)、[反斜杠输入](matmul-backslash.json)。旧失败记录保留为历史事实。

## 四个案例的本轮结果

| 案例 | 固定真实输入 | 本轮实际执行与边界 |
| --- | --- | --- |
| SurfaceLab | VisA pcb1 原有 12 张测试原图，6 正常 / 6 异常 | DINOv2/PatchCore 成功编译；153,664 像素参考张量对照 maxAbs `9.149313e-6`，容差不变。完整 12 图跑完，6 正常判合格、3 异常检出、3 异常漏检。12 项均 `NeedsReview`，未调阈值。 |
| SignalDiagnostics | UCI 447 PS1 第 1 周期，6,000 原始值，100 Hz、bar | CPU 与 HIP 重跑，45 窗 / 5,805 PSD 值通过既定容差，maxAbs `2.0453294865774296e-5`；1 窗触发示例规则，112 尾点未分析，不是设备故障诊断。 |
| DocumentEvidence | HierText 同一真实照片的固定 24 行，官方行框、原文不变 | 一次模型实例 / Compile，24 行串行 GPU OCR；93,120 概率值与 CPU 参考对照通过，maxAbs `1.5556812e-5`。严格匹配 5 行，78/137 字符编辑，CER 56.9343%，19 行失败全部保留。不是文字检测或票据字段验收。 |
| VideoEventSearch | 第四轮已冻结的 NASA 原帧 [900,1200)，每 12 帧取 1，25 帧 | 同一准备包、模型、区域和阈值重新 GPU 推理，109 检测、12 待复核候选事件。MIOpen/rocBLAS `hipErrorInvalidKernelFile` 诊断仍存在；本轮路径修正没有解决该独立现象。无独立事件真值，不报告精确率/召回率。 |

SurfaceLab 的参考张量检查只验证一份 held-out 校准张量，不等于对 12 张图逐像素做 CPU 模型对照；12 张测试集也不代表完整 VisA 精度。编译耗时和运行记录保留，但本轮没有重新做性能基准、264 项自动测试或生产验收。

信号首次调用遗漏 `SIGNAL_GPU_ARCH`，CPU 完成、HIP 被参数检查拒绝；保留 `signal-uci-*` 日志，不计作 GPU 通过。补齐架构后以 `signal-native-*` 新目录重跑两条路径，没有覆盖初次失败。OCR 仅通过编排适配器保留临时目录别名，原 evaluator 的官方标注校验、模型调用、参考比较与评分未改。

## 结果与截图入口

- SurfaceLab：[完整原始导出报告](surface-model-report/report.html)、[逐图输出](surface-model-batch.json)、[官方标签与预测对照](surface-model-summary.json)、[模型验证日志](logs/surface-native-path.log)。
- Signal：[本轮实际报告](signal-native-hip/c2e341f30b9049bf9aa67d78b380fb8d/report.html)、[逐窗数值核验](signal-comparison.json)。
- OCR：[原图与全部 24 行报告](document-hiertext-native-path/evidence.html)、[本轮原始评估](document-hiertext-native-path/evaluation.json)、[C# 批次输出](document-hiertext-native-path/recognized/batch-evidence.json)。报告是从实际输入和输出生成的证据阅读页。
- Video：[实际报告](video-gpu/analysis/report.html)、[本轮运行摘要](video-gpu/workflow-run.json)、[原始 stderr](video-gpu/infer.stderr.txt)。
- [截图与 SHA256 清单](screenshots/manifest.json)、[第三方数据与模型署名](THIRD_PARTY.md)。四张均为 `cua_repl Tab.getScreenshot()` 的原始浏览器视口 JPEG，不是全桌面或终端截图，未补框、重画 UI 或修改结果。

真实输入与官方归档的字节核验沿用 [第四轮记录](../round4/inputs/real-input-audit.json)，本轮再核对实际上传/运行数据与该记录的哈希；HierText evaluator 重新读取官方标注并检查选择协议。输入图像通过相对路径复用既有入库副本，不复制整套数据集。

## 保存范围

全部新资料在 round5。原始 SurfaceLab ZIP 与工作空间在本地完整保留并列入 `local-only-files.json`；ZIP 展开的完整报告、48 张实际 PNG、CSV/JSON 全部入库。四案例原始输出、失败日志和截图均保留，不以当前成功覆盖旧失败。

旧 round2 / round3 / round4 原始文件及 manifest 不改；清单涉及的旧正文等可变文档分别按 `a5aeb7d` / `a4f73e4` / `9727a7d` 核验。本轮完整文件清单为 `manifest.json`，独立核验结果为 `final-checks.json`。没有向 Issue #2 发评论，也没有关闭问题。
