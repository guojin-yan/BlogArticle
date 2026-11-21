# Issue #2：当前逐项修改与验收对照

对应正文 **v10，2026-11-21**。本表以保存的 Issue 原文逐条映射，共 **27 条修改任务 + 9 条最小门槛**；旧第二/三轮说明保留为历史记录。状态为 **可带明确边界进入审阅**，不是全部硬件、模型或生产验收通过，也未关闭 GitHub Issue。

- “已落实”表示要求的修改或取证动作已有证据。
- “已落实，保留范围”表示按 Issue 要求明确披露实测边界与未执行条件，不将其写成 PASS。
- “条件不适用”只用于未作摊销估算、后处理已经运行、没有性能曲线这三项条件。

## 27 条修改任务

| 条目 | 状态 | 落实内容与边界 | 证据 |
| --- | --- | --- | --- |
| P0-A-1 性能计时边界 | 已落实 | 正文第六节写明已解码 HWC 到主机后处理，纳入传输/布局/同步/clamp，排除解码/NMS/编译/可复用分配；合成数据不评精度。 | [03-正文.md](../03-正文.md)、[round2-benchmark.json](../research/validation/round2/round2-benchmark.json) |
| P0-A-2 五路公平消融 | 已落实，保留范围 | CPU、Host新建、Host固定输入重放、Device+CPU、HIP联合；API不能更新已有Host参数，明确重放组不代表新帧。 | [Round2Tools.cs](../examples/MigraphxCompute/Round2Tools.cs)、[issue-2-修订说明.md](../research/issue-2-修订说明.md) |
| P0-A-3 五轮真实复测 | 已落实 | 五个独立进程，每路10次预热/30样本，随机交错；保留全部750个计时样本、P50/P95及旧两轮，不择优。 | [round2-benchmark.json](../research/validation/round2/round2-benchmark.json)、[run-round2.ps1](../examples/run-round2.ps1) |
| P0-A-4 完整环境与负载口径 | 已落实 | 记录Windows/驱动/CPU/ROCm/引擎/包/.NET、ORT默认线程策略、后台进程、未锁时钟功耗；第七轮另直接读取gfx，不追改历史。 | [environment.json](../research/validation/round2/environment.json)、[reader-doctor.json.hardware.json](../research/validation/round7/reader-doctor.json.hardware.json) |
| P0-A-5 误差与近零值 | 已落实 | 原数值保留；解释分母近零导致大比例，按atol+rtol*abs(reference)逐元素比较并记录失败/非有限值。 | [issue-2-修订说明.md](../research/issue-2-修订说明.md)、[benchmark-1.json](../research/validation/round2/results/benchmark-1.json) |
| P0-B-1 启动、首次与热态 | 已落实 | 正文同时呈现Session/图/HIP编译成本、首次调用范围和五轮热态表，排除项写在表旁。 | [03-正文.md](../03-正文.md) |
| P0-B-2 缓存与进程重启 | 已落实，保留范围 | 实际Rebuilt/Hit与独立PID测试；中文路径和compiled重编译FAIL保留。缓存命中仍需编译；cache-cold NOT TESTED。 | [issue-2-修订说明.md](../research/issue-2-修订说明.md)、[README.md](../examples/README.md) |
| P0-B-3 摊销公式条件项 | 条件不适用 | 文章未计算摊平请求数，未将估算称实测；仍区分长驻复用和低频启动成本。 | [03-正文.md](../03-正文.md) |
| P1-A-1 真实照片完整检测 | 已落实 | NASA公有领域照片、固定模型/图像哈希，C#完成解码、预处理、GPU、后处理、NMS、原坐标导出；第七轮新检出再跑。 | [photo.json](../research/validation/round7/reader-photo/photo.json)、[README.md](../research/validation/round2/inputs/README.md) |
| P1-A-2 保留实际结果与来源 | 已落实 | 原图、程序产生的带框PNG、类别/置信度/坐标、命令、日志、模型及许可全部有对应文件，未生成假框。 | [reader-photo.command.json](../research/validation/round7/reader-photo.command.json)、[yolox-detections.png](../research/validation/round7/reader-photo/yolox-detections.png)、[README.md](../research/validation/round2/inputs/README.md) |
| P1-A-3 人工看框与精度边界 | 已落实 | 第七轮再次查看PNG，框对应人物；301,665原始值CPU/GPU无超差，不报告mAP或业务精度。 | [README.md](../research/validation/round7/README.md)、[photo.json](../research/validation/round7/reader-photo/photo.json) |
| P1-A-4 后处理未实现时的条件项 | 条件不适用 | 完整后处理已实际运行，无须用NOT IMPLEMENTED替代结果；其他未验证范围仍明示。 | [PhotoDetection.cs](../examples/MigraphxCompute/PhotoDetection.cs)、[photo.json](../research/validation/round7/reader-photo/photo.json) |
| P1-B-1 MatMul故障复现 | 已落实 | C#与原生失败码、Compile阶段、编译选项、最小模型和DLL身份保留；未取得独立原生调试堆栈也已说明。 | [issue-2-修订说明.md](../research/issue-2-修订说明.md)、[matmul-native.log](../research/validation/round2/logs/matmul-native.log) |
| P1-B-2 封装/原生与路径对照 | 已落实 | C#、原生入口、Affine对照、fastMath及路径单变量测试；第五轮定位本机hipBLASLt路径触发条件，第七轮MatMul数值复验。 | [README.md](../research/validation/round5/README.md)、[matmul.json](../research/validation/round7/reader-workbench/matmul.json) |
| P1-B-3 根因、FAIL与上游边界 | 已落实，保留范围 | 旧失败保留；本机触发条件与有效修正有证据，原生内部源码级根因仍未定位。未擅自向上游发消息或宣称全部引擎问题已修复。 | [README.md](../research/validation/round5/README.md)、[README.md](../research/validation/round7/README.md) |
| P1-C-1 非破坏性doctor | 已落实，保留范围 | SDK/驱动/.NET/PS/RID/gfx/模型/模块及普通-延迟导入、同名版本哈希扫描；三项反向检查失败。动态求解器和同版本副本兼容性保留NOT CHECKED。 | [NativePreflight.cs](../examples/MigraphxCompute/NativePreflight.cs)、[reader-doctor.json](../research/validation/round7/reader-doctor.json)、[doctor-version-conflict.json](../research/validation/round7/doctor-version-conflict.json) |
| P1-C-2 从clone开始首次运行 | 已落实，保留范围 | 公开73569f7新克隆，无源码覆盖，空NuGet/HTTP/CLI目录；10包从官方源还原并实际计算、跟踪、检测和原生窗口截图。同物理机/驱动/SDK，没有新OS或独立读者，独立人类试用为条件性未执行项。 | [reader-source-identity.json](../research/validation/round7/reader-source-identity.json)、[reader-isolation-before.json](../research/validation/round7/reader-isolation-before.json)、[workbench.json](../research/validation/round7/reader-workbench/workbench.json) |
| P1-C-3 不改全局设置及排错路径 | 已落实 | 脚本只配置当前子进程；不改全局PATH/驱动、不安装未知系统依赖。正文按命令、预期输出、故障表组织，深入诊断在配套说明。 | [run-windows.ps1](../examples/run-windows.ps1)、[03-正文.md](../03-正文.md)、[05-上手与验证.md](../05-上手与验证.md) |
| P1-D-1 截图来自实际程序 | 已落实 | 核心新增实际WinForms验证窗口；四应用使用真实公开数据工作台/报告截图。全部结果由真实程序产生，未用AI制作UI、框、热图或终端。 | [manifest.json](../research/validation/round7/screenshots/manifest.json)、[真实开源数据案例与截图.md](../research/真实开源数据案例与截图.md) |
| P1-D-2 原图、哈希与来源映射 | 已落实 | 各轮原始截图保留，清单记录日期/哈希/尺寸/环境/源码与输出映射；第七轮另留原生窗口身份与采集API。素材许可按对应输入说明。 | [manifest.json](../research/validation/round3/screenshots/manifest.json)、[manifest.json](../research/validation/round5/screenshots/manifest.json)、[manifest.json](../research/validation/round6/screenshots/manifest.json)、[manifest.json](../research/validation/round7/screenshots/manifest.json) |
| P1-D-3 性能绘图条件项 | 条件不适用 | 正文使用由原始JSON汇总的数值表，没有新增性能曲线图。汇总代码与五轮数据公开，未用AIGC绘制测量结果。 | [summarize-round2.py](../research/summarize-round2.py)、[round2-benchmark.json](../research/validation/round2/round2-benchmark.json) |
| P1-D-4 概念图与真实证据分清 | 已落实 | 依作者要求保留原六图，全部标AIGC概念/非实测，核心和业务另有实际输出。最新简单OCR仅作两行演示，不替代旧失败记录。 | [03-正文.md](../03-正文.md)、[README.md](../research/validation/round6/README.md) |
| P1-D-5 矛盾与异常回到实跑 | 已落实 | URL不明旧工具停止；使用可核对的浏览器接口和本轮原生窗口。无效排版截图、模型/路径失败和错误预测保留，未修图改结果。 | [issue-2-截图与四应用复跑.md](../research/issue-2-截图与四应用复跑.md)、[README.md](../research/validation/round5/README.md)、[README.md](../research/validation/round7/README.md) |
| P2-1 前言具体化 | 已落实 | 保留原标题，前言聚焦原生依赖、设备缓冲区、模型与业务接入，首节只说明实际能力与收益。 | [03-正文.md](../03-正文.md) |
| P2-2 避免把模型耗时当检测耗时 | 已落实 | 表旁明确不含解码、NMS和编译；五轮数据替代旧单轮最低值，真实检测流程单列。 | [03-正文.md](../03-正文.md) |
| P2-3 三个Start Here入口 | 已落实 | 第七节三个重要入口同时有命名点击链接和代码URL，其他正文URL按博客要求代码展示。 | [03-正文.md](../03-正文.md) |
| P2-4 围绕读者的操作顺序 | 已落实 | VectorAdd→ONNX/CPU对照→真实照片/自己的数据，每项提供预期结果、示例命令与故障反馈入口。 | [03-正文.md](../03-正文.md)、[README.md](../examples/README.md) |

## 9 条最小验收门槛

| 条目 | 状态 | 落实内容与边界 | 证据 |
| --- | --- | --- | --- |
| DOD-1 保留七章与第一轮成果 | 已落实 | 原标题、七章、七包、原六图及第一轮真实成果保留。 | [03-正文.md](../03-正文.md) |
| DOD-2 性能口径与启动成本 | 已落实 | 正文已呈现并明确整体实现差异不能全归因纯GPU算子。 | [03-正文.md](../03-正文.md) |
| DOD-3 至少三轮与原始证据 | 已落实 | 五轮750逐次样本、随机顺序、环境与误差留存；Host复用限制公开，旧两轮不覆盖。 | [round2-benchmark.json](../research/validation/round2/round2-benchmark.json)、[issue-2-修订说明.md](../research/issue-2-修订说明.md) |
| DOD-4 授权真实照片YOLOX | 已落实 | 完整流程已完成，第七轮再次实际执行与人工看框。 | [photo.json](../research/validation/round7/reader-photo/photo.json)、[README.md](../research/validation/round2/inputs/README.md) |
| DOD-5 MatMul失败归档 | 已落实 | 最小失败、原生入口与有效路径修正均有证据，不要求凭文章宣称修好全部原生引擎。 | [README.md](../research/validation/round5/README.md)、[issue-2-修订说明.md](../research/issue-2-修订说明.md) |
| DOD-6 实际Quickstart与诊断 | 已落实，保留范围 | 新远端clone、独立包缓存、固定公开源码与原生窗口已完成；物理机/系统依赖复用和无人类独立试用明确。 | [README.md](../research/validation/round7/README.md)、[reader-source-identity.json](../research/validation/round7/reader-source-identity.json) |
| DOD-7 核心与业务真实截图 | 已落实 | 新增核心原生C#运行截图；四案例公开真实输入及实际截图已齐，概念图有明确标识。 | [manifest.json](../research/validation/round7/screenshots/manifest.json)、[真实开源数据案例与截图.md](../research/真实开源数据案例与截图.md) |
| DOD-8 存疑实跑与日期边界 | 已落实，保留范围 | 本轮预检反例、空包缓存、小图、trace、照片实际运行；五轮性能、264测试、四案例按原日期引用，冷缓存/其他硬件/动态兼容性未验项明示。 | [README.md](../research/validation/round7/README.md)、[05-上手与验证.md](../05-上手与验证.md) |
| DOD-9 保留FAIL/SKIP与全部样本 | 已落实 | 历史原始证据逐项核验；Surface漏检、24行OCR失败、视频诊断、初版预检和新反向失败全部保留。简单OCR是推理前冻结的演示，不合并评分。 | [final-checks.json](../research/validation/round7/final-checks.json)、[README.md](../research/validation/round5/README.md)、[README.md](../research/validation/round6/README.md) |

## 仍然明确保留的边界

首次运行复验使用同一物理 Windows/W7900，复用系统驱动、SDK 和框架包；源码、NuGet 包、HTTP 缓存及 CLI 目录独立，初始为空。没有新 OS 或独立人类读者；Issue 中“条件允许时的独立读者”未执行。

四组同名 DLL 字节差异及动态求解器/全模型兼容性仍未认证。实际模型数值通过不能替代这些范围。冷缓存、逐 Kernel Profiler、进程峰值显存、其他 GPU/原生 Linux、小 INT8 没有本轮复验；原生内部源码级根因未定位。

本轮新增的是预检、原生 C# 验证窗口、独立包缓存首次运行、执行跟踪与真实照片检测。五轮性能仍是第二轮数据，264项测试仍是第三轮，四案例与简单OCR分别是第五/六轮；没有把历史PASS改写成本轮PASS。原六张概念图按作者要求保留并标识，最新OCR按作者要求保持简单两行，不代表字段核验或总体精度。

原始数据和失败不覆盖；新旧可变文稿按对应提交核验。完整新证据见[第七轮目录](validation/round7/README.md)，逐项原始要求见[结构化对照](validation/round7/issue-2-requirements.json)，公开 Issue 的本轮只读快照见[来源](validation/round7/issue-2-source.json)。没有向 Issue #2 发送评论或关闭它。
