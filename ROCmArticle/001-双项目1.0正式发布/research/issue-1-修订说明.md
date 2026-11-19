# Issue #1 修订对照（v4）

日期：2026-11-19。对应 [BlogArticle Issue #1](https://github.com/guojin-yan/BlogArticle/issues/1)。本文替代 v3 的处理说明：作者已确认继续落实七章结构、正文限制、实际模型测量与 Issue 回复，不再沿用 v3 的五章宣发取舍。链接展示另按作者最新要求调整：博客正文不使用文字超链接，地址用代码展示，供读者复制。

主交付：[正文](../03-正文.md)、[上手与验证](../05-上手与验证.md)、[可运行示例](../examples/README.md)。原定标题、六张原配图及引用保留，三张实际证据图放在配套验证资料；新材料均位于 ROCmArticle，三个源码仓库只读。按作者后续反馈，正文案例只作简要展示，详细复现和数值记录由配套资料承接。

按作者最新反馈，第六、七章进一步压缩：正文保留平台简表、端到端性能与测量条件、三条关键边界、三条上手路线和项目入口；完整来源、Warm API 计时、编译/首次执行/显存、诊断日志及反馈模板保留在配套说明。以下完成项按正文与配套资料共同核对。

## P0：工程可信度

| 建议 | 完成内容与证据 | 保留边界 |
| --- | --- | --- |
| 七章逻辑与读者结果 | 正文按七章重写；按作者最新要求，首章只介绍GPU批量计算、ONNX推理和联合流程三类效果，上手命令统一放第四章 | 不承诺首次安装全部依赖只需 5 分钟 |
| P0-A 平台/框架范围 | 正文第六章简表区分 Windows、WSL2、原生 Linux/KFD 与能力跳过；完整包版本、PASS/SKIP/NOT TESTED/KNOWN FAIL 和固定来源在配套矩阵 | 本轮新增运行只在 Windows；历史驱动版本不填造 |
| P0-B 来源和依赖 | 正文第三章列七包与版本关系、Windows 源码构建及补丁、Ubuntu 二进制来源、ROCm 系统库/驱动/VC++ 前提、manifest 和第三方许可 | 社区封装与 AMD 上游归属分开，不称官方认证 |
| P0-C Identity 定位 | Identity 仅作 Loader/API/执行链路冒烟检查；新增固定 Affine/ReLU、独立 C# 与 ORT CPU 对照、实际 RunTrace、设备 I/O 与 HIP event | [trace](validation/issue1-affine-trace.log)和[JSON](validation/issue1-affine-result.json)不是独立逐 Kernel 硬件 Profiler 时间线 |
| P0-C 数值计算 | [VectorAdd](../examples/HipVectorAdd/Program.cs)：65,539 元素×3轮，maxAbs=0；[Affine/ReLU](../examples/MigraphxCompute/README.md)：4,096 元素，多参考结果一致 | 核验固定输入/模型；不代表任意 ONNX 或 GPU 兼容 |
| P0-D 已知问题 | 正文写入 Windows 2×2 INT8、缺 TensorFlow importer、Interop 数据复制与应用质量边界；新增本轮 64×64 float MatMul 编译 0xC0000005 夹具和日志 | 原生失败原因未定位，不把大矩阵成功解释为小矩阵修复 |

## P1：复现、性能与应用

| 建议 | 完成内容与证据 | 保留边界 |
| --- | --- | --- |
| P1-A 三条上手路径 | 正文第四、七章：HIP / ONNX / 联合路线，包依赖、预检、命令、预期输出、错误定位；[Windows 包装器](../examples/run-windows.ps1)实际运行通过 | 当前工程目标 net10.0、PowerShell 7；Ubuntu 需按固定部署指南替换 Runtime 与环境 |
| P1-B 实际模型测量 | 上游 YOLOX Nano，模型/输入哈希、固定合成 RGB、batch1/float32；CPU ORT 1.23.2、MIGraphX 主机 I/O、HIP 联合路径；每路径10次预热、30次原始计时、P50/P95/吞吐、编译/首次执行及全设备显存快照 | 未清缓存，首次执行不是干净冷启动；无单进程峰值显存、时钟/功耗隔离；不含解码/NMS/检测精度；warm API 的 I/O 边界不同 |
| P1-B 结果与解释 | [最终 benchmark](validation/issue1-yolox-benchmark.json)：E2E P50 CPU15.053ms、主机19.770ms、联合4.155ms；原始模型张量、后处理及测量后结果全部通过容差，maxAbs约2.19047e-5 | 不隐藏主机 GPU 路径更慢；[首轮](validation/issue1-yolox-benchmark-round1.json)与日志也保留，显示波动及曾出现的 MIOpen solver 诊断 |
| P1-C Signal 案例 | 正文第五章用输入/处理/输出简述并附源码；完整命令、8s/4096Hz作者信号、CPU/HIP125窗、15待复核、64,125 PSD值比较和12组FFT检查见配套说明第六节 | 演示信号验证数值和流程，不是现场设备诊断准确率或性能基准 |
| P1-C SurfaceLab | 正文一句用途说明与源码；配套保留实际VisA输入/热图、FN样例、12图统计及pcb2召回73%/正常误报6%与失败样例 | 未达到99%/10%质量目标，不是新独立工业验收；保留人工复核 |
| P1-C DocumentEvidence | 正文简述OCR与文档核验并附源码；配套区分导入/指定行/自动检测，保留历史7条作者英文行、6条精确和前导空格失败记录 | 不扩大为整页检测、字段精度或真实单据验收 |
| P1-C VideoEventSearch | 正文简述候选事件回看并附源码；实际演示帧、PTS800/1200、timebase1/1000、zone-enter候选与NeedsReview移至配套说明 | 无独立真实视频事件标签，不给事件准确率 |

## P2：引用与贡献

| 建议 | 完成内容与证据 |
| --- | --- |
| 链接与博客排版 | 按作者最新要求，正文的七个NuGet、仓库、指南、源码和证据地址使用代码块/行内代码，替代Issue建议的文字超链接；相对资料地址展开为公开GitHub完整地址。仓库配套文档仍可点击；宽表横向滚动 |
| 稳定来源 | HIP文档固定提交、MIGraphX v1.0.0、应用固定提交；[来源核对](validation/issue1-source-checks.json)保留公开blob与本地一致的记录 |
| Start Here / 反馈 | 文末提供 HIP / ONNX / 联合流水线三条路线与统一示例入口、反馈要点及贡献入口；完整环境/复现/日志模板在配套说明 |
| 归属与许可 | 明确 C# 封装、AMD 上游和第三方归属；Apache-2.0 不覆盖全部原生组件、模型、数据、文章和图片；[新增图片来源](../assets/evidence/README.md)逐项说明 |

## 验收解释

文章内容、可运行示例、固定模型执行/数值证据、实际模型三路径测量和应用结果材料均已补齐。P0 的披露与可复现要求已落实，P1/P2 增强内容也已纳入正文及配套资料。此结论不表示所有运行环境和工程风险均被验证完毕。

尚未取得的独立硬件 Profiler 时间线、干净冷启动、单进程峰值显存、原生 Linux/KFD/其他GPU新增测试、长期运行与独立工业数据验收，在正文和反馈中明确列出。不能把这些项标成实验通过。Issue 保持打开，由作者/提出者决定是否接受本轮修订。
