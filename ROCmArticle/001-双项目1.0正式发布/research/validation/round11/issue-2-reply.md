谢谢这份详细反馈。我已按 Issue 的 **27 条修改任务和 9 条最小验收门槛**逐项核对，更新正文至 v14，并将每条原始要求、落实情况、证据入口及未测范围整理进对照表。

本次核对结果是 **25 项已落实、7 项落实但保留验证范围、3 项条件不适用、1 项按作者最新排版要求调整**，没有将所有项目统写成 PASS。修改与证据已推送仓库，保留原标题、七章、两个项目的能力介绍、七个 NuGet 包和原有成果。

**性能与成本（P0-A、P0-B）**：已完成 W7900 上 5 个独立进程、每路径 10 次预热/30 次测量的五路比较，保留全部 750 个逐次样本、随机执行顺序与 P50/P95。正文同时列出计时边界、编译/首次执行/热态成本；本轮从原始 JSON 重新核对全部分位数与汇总。Host 参数复用仅是固定输入重放，不能代表更新帧；端到端差值不能全归因于纯 GPU 算子或零拷贝。近零值的相对误差及逐元素容差、缓存命中后仍需编译、保存/加载失败均保留，`cache-cold NOT TESTED`。

**真实检测与 MatMul（P1-A、P1-B）**：NASA 公有领域照片已完成实际 C# 解码、预处理、GPU 推理、YOLOX 解码、NMS、原图坐标与结果导出；第七轮得到 1 个 person、分数约 0.9259，301,665 个原始输出与 CPU 对照无超差，人工检查框对应人物，只作功能演示。MatMul 的 C# 与原生入口失败记录均保留；单变量对照定位到本机 hipBLASLt 设备库路径分隔符触发条件，规范化反斜杠后实际数值验证通过。原生内部源码级根因仍未知，不扩大成上游问题全部修复。

**首次运行与真实截图（P1-C、P1-D）**：doctor 包含实际 gfx、普通/延迟导入依赖闭包及版本/哈希检查，保留 3 个反向失败场景。第七轮从公开提交新 clone、以初始为空的 NuGet/HTTP/CLI 目录运行，未覆盖源码；仍是同一物理 Windows/W7900，复用系统驱动与 SDK，没有独立人类读者或新 OS 验收。正文核心图已换成第八轮实际运行的 PowerShell 终端原图，附 PID、命令、时间、日志/transcript 与 SHA256；日志阅读页和原生 C# 应用图按各自类型归档。本轮再次核对原字节与记录，没有重新生成终端文字或截图。

四个应用的截图均使用公开真实输入：VisA、UCI PS1、HierText、NASA 视频，保留 PCB 的 3 张异常漏检、复杂 OCR 的 19 行失败和视频 12 个待复核候选。按作者要求另展示简单 APPLE/SODA 两行 OCR，不替代复杂样本结果，也不代表总体精度。六张原概念图明确标为 AIGC/非实测。

**表达与入口（P2）**：保留产品特色与关键解释，四案例简短展示，结尾按 VectorAdd → ONNX/CPU 对照 → 自己的数据组织。P2-3 原建议同时提供点击链接；作者最新明确要求所有网站使用代码展示，因此三个入口保留完整可复制地址、移除点击跳转。对照表单列 `AUTHOR_OVERRIDE`，不把这一项说成按原文完成。正文、当前配套资料和 HTML 预览均已检查，不含外部网站跳转。

逐项表与正文：

```text
https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/research/issue-2-当前验收对照.md
https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/03-正文.md
https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/05-上手与验证.md
```

本轮核对、原始性能、终端与首次运行证据：

```text
https://github.com/guojin-yan/BlogArticle/tree/main/ROCmArticle/001-双项目1.0正式发布/research/validation/round11
https://github.com/guojin-yan/BlogArticle/tree/main/ROCmArticle/001-双项目1.0正式发布/research/validation/round2
https://github.com/guojin-yan/BlogArticle/tree/main/ROCmArticle/001-双项目1.0正式发布/research/validation/round8
https://github.com/guojin-yan/BlogArticle/tree/main/ROCmArticle/001-双项目1.0正式发布/research/validation/round7
https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/research/真实开源数据案例与截图.md
```

本轮仅修改排版并复核既有证据，未新增 GPU 运行、性能测量或截图。性能是第二轮、264 项测试是第三轮、四应用和简单 OCR 分别是第五/六轮，未复制历史 PASS 当成本轮 PASS。第二至第八轮共 1,160 个 manifest 文件记录已核对哈希，第二至第十轮证据目录未改。

仍未验证冷缓存、独立逐 Kernel Profiler、进程峰值显存、其他 GPU/原生 Linux及小 INT8 本轮复验；四组同名 DLL 字节差异和动态求解器/全模型兼容性仍为 `NOT CHECKED`。当前状态为**可带明确边界进入审阅**，不等同全部硬件/模型或生产验收通过。Issue 保持开放，供继续审阅。
