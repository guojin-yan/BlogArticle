# Issue #2：第二轮修订与真实运行记录

日期：2026-11-20（Asia/Shanghai）。审阅基线 commit：`b3d5a4a88b23e9c00faf1eed750200fa163f80cf`；本轮在候选工作区运行，源码身份见[证据清单](validation/round2/manifest.json)。保留原标题、七章、七个正式 NuGet 包、全部既有图片和首轮证据。正文为 v5，未替代项目自身的发布验证。

## 修改对照

| 修改了什么 | 为什么 | 实际证据 | 读者可以完成什么 |
| --- | --- | --- | --- |
| 五路消融、五个独立进程、随机交错顺序 | 分清对象复用、传输、前后处理，解释波动 | [五轮汇总](validation/round2/round2-benchmark.json)、`results/benchmark-1..5.json` 与同名日志 | 按相同口径比较自己的管线 |
| 正文呈现编译、首次调用与热态三种成本 | 低频应用需要判断启动成本 | 同一组 JSON 的 `*CompileMs`、`firstRunMs` | 选择长驻复用或低频调用策略 |
| 实跑缓存未命中/命中、保存/加载和新进程 | 缓存命中不自动免编译 | `cache-parsed-*`、所有失败日志 | 复现 Rebuilt/Hit，并识别失败分支 |
| 真实照片完整 YOLOX 流程 | 从张量正确走到可观察的业务结果 | [实际 PNG](validation/round2/results/yolox-detections.png)、[JSON](validation/round2/results/photo.json) | 换自己的图片，检查框、分数和坐标 |
| MatMul 经 C# 和直接原生 C API 复跑 | 缩小故障边界，保留 FAIL | `matmul-csharp/native/native-fast.log`、`affine-native.log` | 提供有界复现，而非猜测上游根因 |
| `-CheckOnly` 与隔离检出的 Quickstart | 降低环境排错成本 | `quickstart-doctor*`、`quickstart-verify*`、`clone-ssh.log` | 预检→四示例→自己的模型 |
| 三个 Start Here 同时提供点击与代码地址 | 兼顾博客复制和移动端访问 | 正文第七节 | 直接到源码或运行说明 |
| 概念图统一标 AIGC/非实测 | 区分视觉说明与运行证据 | 保留原六图，新增真实结果图 | 判断每张图能证明什么 |

## 五轮性能与消融范围

Windows 11 build 26300、AMD 驱动 `32.0.21030.2001`、W7900/gfx1100、Ryzen 9 5900XT（16C/32T）、ROCm 10.1、MIGraphX 2.18、.NET SDK 11.0.100（目标 net10.0）、PowerShell 7.6.9；ORT CPU 1.23.2、默认线程数、顺序执行图。gfx 来自已有同机验证和请求的编译目标，本轮 doctor 未独立读取硬件 gfx。后台桌面应用未隔离，未锁时钟/功耗；每轮有进程快照，不能据此声称运行期间 GPU 空闲。

五个独立 dotnet 进程，随机种子 `20261121..20261125`。每组 10 次预热、30 次测量，每个样本随机执行五条路径；执行顺序、全部样本、P50/P95均在 JSON。分位数 nearest rank，不剔除离群值。表中为每轮 P50，单位 ms：

| 路径 | 第1轮 | 第2轮 | 第3轮 | 第4轮 | 第5轮 | 五轮中位数 |
| --- | --- | --- | --- | --- | --- | --- |
| ORT CPU | 14.8610 | 14.4241 | 14.6336 | 15.0216 | 14.7732 | 14.7732 |
| Host 逐次新建 | 20.6362 | 20.5645 | 19.8358 | 21.4784 | 20.5638 | 20.5645 |
| Host 固定输入复用 | 19.0545 | 19.2487 | 17.7459 | 19.4519 | 19.2635 | 19.2487 |
| Device + CPU 前后处理 | 6.9672 | 6.8525 | 7.3855 | 7.3633 | 7.2323 | 7.2323 |
| 完整 HIP 联合路径 | 5.2017 | 5.0531 | 5.2284 | 5.3971 | 5.2865 | 5.2284 |

输入为固定合成 HWC RGB float，batch=1、CHW `1×3×416×416`，模型和两种输入哈希五轮一致。**计时从已解码主机 HWC float 到主机 clamp 后输出**，包含传输、布局、同步；排除解码、NMS、图编译和可复用缓冲区分配。它不是完整检测时间，不评估检测精度。

- Host API 创建参数时深拷贝，公开接口没有更新已创建参数的操作。复用组仅重放同一输入，不能代表新帧，也不能据此承诺移除所有分配成本。
- Device+CPU 组保留 H2D/D2H/D2D，CPU 做布局与 clamp；完整组再替换为 HIP Kernel。相同最终语义和容差均通过，但差值仍含调用、复用与同步，不能解释为纯 Kernel 加速或零拷贝。
- 五组最终输出及 Host/联合的原始模型输出均无超差/非有限值。最大原始绝对误差 `2.3692846298217773e-5`，最大相对误差 `5381.316725561192`，分母取 `max(1e-12,abs(reference))`。近零参考使比例放大，实际判据是 `abs(actual-reference) <= 0.001 + 0.001*abs(reference)`，不是最大相对误差单项阈值。
- 首轮和照片运行出现 MIOpen `Invalid elapsed time` solver 诊断，完整保留；不能把数值通过写成原生日志完全无异常。没有独立逐 Kernel Profiler 或进程峰值显存数据。

旧两轮记录及其数值继续保留在 `validation/issue1-yolox-benchmark*.json`，不选择最快一轮作新结论。汇总脚本为 `summarize-round2.py`；重跑入口为 `examples/run-round2.ps1`。

## 启动、首次执行与缓存

五轮中位数：CPU Session **99.9408 ms**、Host 图编译 **25,127.6276 ms**、Device 图编译 **19,414.7566 ms**、HIP 编译 **63.2087 ms**。CPU/Host/联合首次调用范围分别为 **26.8430–161.3284 / 38.1329–44.1841 / 20.2910–21.4772 ms**。这些是本进程首次调用，`cache-cold NOT TESTED`；没有清驱动、磁盘缓存，也不做摊平请求数的实测声明。

缓存按时间保留全部尝试，不能只看最终 PASS：

| 尝试 | 状态与解释 | 日志/结果前缀 |
| --- | --- | --- |
| 中文路径，已编译图保存 | FAIL：原生路径字符映射，save status 4 | `cache-miss`、`cache-hit-process2/3` |
| ASCII 路径，保存/加载已编译图后直接 Run | **测试代码错误**：遗漏公开契约要求的 Compile；不是库缺陷证据 | `cache-ascii-*` |
| ASCII 路径，已编译图 Load 后 Compile | FAIL：`auto_contiguous` / `Input shapes have changed`，status 4 | `cache-v2-*` |
| ASCII 路径，未编译图 Save/Load 后 Compile | PASS：Rebuilt/Hit/Hit，三个独立 PID，CPU 对照通过 | `cache-parsed-*` |

最初 parsed 三进程组精确值如下，时间单位 ms：

| 进程 | 结果 | builder 次数 | 查询/构建+保存+加载 | 加载后 Compile | 首次 Run |
| --- | --- | --- | --- | --- | --- |
| 24244 | Rebuilt，之前 Miss | 1 | 169.1431 | 26686.6222 | 42.5975 |
| 69892 | Hit | 0 | 71.3113 | 29079.2163 | 32.1499 |
| 29288 | Hit | 0 | 69.6850 | 27245.4361 | 31.4344 |

最终日志字段修正后又以独立 PID 70888 复验一次 Hit：查询100.2720 ms、Compile31574.2016 ms、首次Run34.8859 ms，数值通过。合计三次Hit的Compile范围约27–32秒；不选择最快命中作承诺。最终照片导出复验的编译为39556.4858 ms（初次26772.5027 ms），两次带框PNG哈希一致；这些是另存的功能复验，不并入五轮性能表。

因此这里只确认显式模型缓存和 msgpack 保存/加载在 ASCII 路径可用，**没有确认 compiled 程序重载免编译**。每份 parsed JSON 含 30 个热态样本，固定输入重放，不并入五轮表。历史 `startupThroughReferenceMs` 字段误在热循环后取值，包含热循环，**不得当启动时间使用**；最终源码已把采样位置移至 CPU 对照完成、热循环开始前，历史 JSON 不改。

最初 `commands.txt` 中 cache 未显式写 kind，当时默认 compiled。当前默认 parsed；历史脚本快照保留在 `sources/`，现在的复现脚本显式指定 kind 并写入新的输出目录，不能用新默认值冒充历史运行。

## 授权真实照片与人工核对

输入为 NASA Eileen Collins 照片（512×512），scikit-image v0.19.3 源码标 public domain/no known restrictions。原图、来源快照、YOLOX 0.1.1rc0 模型及 Apache-2.0 许可均保留，SHA256 见[素材说明](validation/round2/inputs/README.md)。

实际 C# 流程：解码→双线性缩放整数舍入→左上补114/BGR/CHW416→MIGraphX GPU→grid/stride/exp 解码→objectness×class→0.30阈值→类内 greedy NMS（IoU0.45）→原图坐标。前后处理在 CPU，与性能表中的 HIP 管线不同。

结果：**1 person，0.9258799，xyxy `[11.440047,20.257587,368.83075,507.20425]`**。301,665 原始输出与 ORT CPU 比较，0 超差/非有限值，maxAbs `5.936622619628906e-5`。已人工查看 PNG，框对应人物，没有移动或补画预测。没有独立标注，不报告 mAP/业务准确率。PNG 是程序真实输出，HTML 仅呈现该结果，均非桌面截图。

最终报告导出增加任意输入副本和实际设备名称，避免把用户照片错标为 NASA；复验另存 `photo-final`，初次文件与数值不覆盖。

## MatMul、doctor 与 Quickstart

`64×64 float32 MatMul+ReLU` 夹具哈希固定。C# 在 Compile 阶段复现 fatal `0xC0000005`（进程退出 `-1073741819`）。Python ctypes 直接调用 `migraphx_c` C API，绕过 C#，同样在 Compile 访问冲突读地址 `0x80`；fastMath false/true 均失败，直接原生 Affine 对照成功。原生入口每次 CALL/RETURN、编译选项、模型/DLL SHA 都在日志。未取得独立 native debugger stack（没有可用 cdb），仅保留 managed stack 与直接 C 入口异常。**ROOT CAUSE UNKNOWN**：不能确定是 AMD 上游、Windows 构建补丁、依赖或其他原因；未向其他仓库擅自提报。

doctor 实跑完成设备、HIPRTC 编译、对象探测、模块路径/版本/hash、插件与设备数据检查；完整数学库依赖链、所有版本冲突认证、硬件 gfx 自动识别为 NOT CHECKED，Linux/其他GPU为 SKIP。不能用文件存在或总体 `PASS_WITH_UNCHECKED_ITEMS` 代替模型可用性结论。

补测不存在的 SDK 路径，发现初版 doctor 在 ProbeSystem 抛出异常后没有写 JSON。已只在随文示例中增加捕获，将异常、FAIL 和下一步建议写入报告；保留 `doctor-missing-sdk.log` 初次失败。修正后 `doctor-missing-sdk-fixed.json` 返回 FAIL/非零并保留完整检查项，正常环境的 `doctor-fixed-positive.json` 仍为 PASS_WITH_UNCHECKED_ITEMS。这是预检排错能力的正反向复验，不把缺依赖写成模型通过。

Quickstart 从新的 shallow sparse SSH clone 开始（HTTPS 整库 clone 超时，保留 `NOT COMPLETED` 记录），覆盖候选示例后新建 bin/obj，执行 CheckOnly 和四示例成功：VectorAdd 65,539 元素、3轮、误差0；Identity `1,2,3,4`；Affine/ReLU 4,096 元素与 CPU 对照通过。**同一物理 Windows 主机、同一已安装驱动/SDK、复用全局 NuGet 缓存，无新 OS，无独立人类读者**。它证明隔离检出可运行，不能称干净机器安装验收。最终轻量复验另存日志，保留初次记录。

## 尚未完成的范围

- **桌面截图：BLOCKED / NOT CAPTURED。** 电脑控制工具无法可靠识别浏览器 URL 而停止，要求停止应用输入；已停止 UI 操作，没有用其他截图方式绕过，也没有制造终端图片。原始目录含状态说明。
- **四个应用：NOT RE-RUN。** 保留既有真实数值与原六张概念图，统一 AIGC/非实测标识；本轮未完成四应用界面截图、业务精度或生产验收。
- 小 INT8、其他 GPU/平台、原生 Linux/KFD、冷缓存、独立 Profiler、进程峰值显存均未本轮复验。

因此 Issue #2 的真机截图门槛尚未全部满足，不能标“全部验收通过”或据此关闭。本文没有向 Issue #2 发送评论；可以用本修订表作为后续回复依据。
