# 第七轮：Issue #2 预检、首次运行与当前验收

2026-11-21，基于 v9 / `4096421` 继续逐项落实 Issue #2。当前任务要求以[保存的 Issue 原文](issue-2-source.json)为准；27 条修改任务和 9 条最小门槛的对应关系见[当前验收对照](../../issue-2-当前验收对照.md)。

## 本轮完成

| 修改 | 原因 | 实际证据 | 读者可完成的任务 |
| --- | --- | --- | --- |
| `hipInfo` 硬件 gfx 核对 | 区分真实硬件与请求的编译参数 | [硬件原文](reader-doctor.json.hardware.json)、[预检](reader-doctor.json) | 发现架构配置错误 |
| 原生 PE 普通/延迟导入与候选副本检查 | 从目录存在推进到依赖解析与加载身份 | [34 文件、174 导入边](reader-doctor.json.dependencies.json) | 查找缺失依赖、不同版本及实际加载路径 |
| 预检三个反向场景 | 核对错误环境能否得到失败与下一步建议 | `doctor-missing-sdk*`、`doctor-wrong-arch*`、`doctor-version-conflict*` | 对照自己的错误报告排查 |
| 新检出与独立包缓存 | 增强首次运行证据，去掉旧源码覆盖和包缓存复用 | [初始隔离状态](reader-isolation-before.json)、[还原包](reader-restored-packages.json)、[源码与构建身份](reader-source-identity.json) | 从公开提交还原正式包并运行示例 |
| 原生 C# 验证窗口 | 直接观察程序实际执行及保留项 | [截图](screenshots/01-native-validation.jpg)、[结果](reader-workbench/workbench.json)、[完整命令](reader-workbench.command.json) | 观察每项检查，打开对应 JSON 与原始日志 |
| 再跑跟踪与真实照片 | 核对新检出里的完整模型路径 | [trace](reader-trace.log)、[照片结果](reader-photo/photo.json)、[带框 PNG](reader-photo/yolox-detections.png) | 读取 GPU 执行记录及真实检测结果 |

源码改动只在文章的消费示例中：新增 `NativePreflight.cs`、调整 `run-windows.ps1`，新增 `ValidationWorkbench`。三个正式项目仓库只读。示例先在 `73569f724920982aee6767cf7800635edb280c77` 公开，然后从远端完整浅克隆该提交；没有用候选文件覆盖克隆源码。

## 预检结果与保留的差异

本机实际硬件报告为 **AMD Radeon PRO W7900 / gfx1100**。静态检查递归读取非系统 PE 的普通/延迟导入，记录已加载模块和候选路径；系统 DLL 在 System32 停止递归，API set 交给操作系统。当前 34 个文件、174 条导入边无缺失或解析失败。该检查不模拟 Windows 加载器的全部策略，也不证明所有动态插件、数学库求解器或 ONNX 模型兼容。

包内与 SDK 的 `hiprtc0716.dll`、`amdhip64_7.dll`、`rocm_kpack.dll`、`amd_comgr.dll` 有不同哈希副本。可读取的版本号相同，`rocm_kpack.dll` 无版本号；兼容性保持 `NOT CHECKED`，实际加载路径及全部副本哈希保留。新扫描只在发现明确的不同版本时返回冲突失败；相同版本的字节差异不能单独证明 ABI 不兼容。

初版扫描把任何哈希差异直接判为 FAIL，结果原样留在 `doctor-positive*`；修正判据后的结果为 `doctor-positive-v2*` 和本轮新检出的 `reader-doctor*`。这是诊断判据修正，不是删除实际模型错误。窗口初次构建出现局部变量重名的编译错误，修正命名后构建通过；正式构建日志为 `workbench-build.log`，未把初次构建声称为成功。

三个反向场景均实际返回非零并保存结构化 JSON：不存在的 SDK、请求 `gfx1030` 而硬件为 `gfx1100`、搜索目录中加入不同版本候选。最后一项在本地隔离目录放置重命名的系统 DLL，仅作为诊断负例，不改 SDK、包、业务输入或任何模型；详细候选身份在失败报告中。

## 首次运行的隔离范围

NuGet 包目录、HTTP 缓存、CLI 配置目录在运行前均为空。10 个包实际从 `https://api.nuget.org/v3/index.json` 还原；项目 assets 中包目录均指向新的专用目录，未使用旧全局包缓存或手工覆盖源码。设置只作用于本轮子进程，不修改用户全局 PATH、驱动或 SDK。

原生窗口实际启动随文 PowerShell 包装器，依次做预检、设备枚举、VectorAdd（65,539 元素、3 次、最大误差 0）、Identity（1,2,3,4）、Affine/ReLU 与 MatMul/ReLU（各 4,096 元素、CPU/Host GPU/联合 GPU 对照）。每步结束后才读取日志与 JSON 填入列表，原始 stdout、stderr、命令及其哈希均单独保存。兼容性未确认行保留，因此 `allDisplayedChecksPassed` 为 false，没有制造全部通过。

另一个独立进程完成 [RunTrace](reader-trace.log)，含 `mul_add_relu_kernel`。真实 NASA 照片再次完成 C# 解码、预处理、GPU 推理、YOLOX 解码、NMS、坐标映射与导出，301,665 个原始值与 CPU 对照无超差，maxAbs `3.743171691894531e-5`；1 个 person，分数 `0.92588`。已人工查看框对应人物，结果 PNG 与第二轮哈希一致。原图、模型哈希及许可沿用[第二轮素材](../round2/inputs/README.md)；图片为公有领域，不报告 mAP。

这是**同一物理 Windows/W7900 的源码、包与 CLI 目录隔离**，复用已有驱动、SDK 和 .NET 框架包；没有新 OS 或独立人类读者。没有清驱动/磁盘缓存，`cache-cold NOT TESTED`。未重新做五轮性能、264 项自动测试或四应用复跑；这些仍按第二、三、五、六轮日期引用。没有新增原生调试符号堆栈、逐 Kernel Profiler 或进程峰值显存数据。

## 截图与历史保存

截图来自实际 WinForms 程序窗口，含原生标题栏，由 `@oai/sky get_window_state` 保存原始 JPEG，未裁切、补字或改变结果。窗口身份与采集记录见 [capture.json](screenshots/capture.json)，日期、SHA256、环境和输出映射见[截图清单](screenshots/manifest.json)。它是本次实际运行的 C# 应用截图；原浏览器报告与日志阅读页继续按原类型标注。

第二至第六轮原始证据及 manifest 不覆盖。旧可变文稿按 `a5aeb7d` / `a4f73e4` / `9727a7d` / `1b33655` / `4096421` 核验。本轮文件清单为 [manifest.json](manifest.json)，独立检查为 [final-checks.json](final-checks.json)。当前状态供逐项审阅，不代表业务精度、全平台认证或生产验收；未发送 Issue #2 评论或关闭 Issue。
