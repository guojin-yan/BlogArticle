# 实际结果配图来源

这些图片由 `research/build-evidence.py` 从保留的真实运行产物生成，和正文原有的六张流程概念图分开标注。

| 文件 | 来源与处理 | 适用范围 |
| --- | --- | --- |
| surfacelab-real-result.png | Amazon Science VisA / spot-diff（`https://github.com/amazon-science/spot-diff`），CC BY 4.0（`https://creativecommons.org/licenses/by/4.0/`）；保留输入与应用热图，缩放并列、添加标签 | 已复用的 12 图历史流程检查，选图为漏检 FN；不是独立质量验收 |
| signal-cpu-hip.png | 作者编写的确定性信号；2026-11-19 实际 CPU/HIP 输出的 PSD 与窗口决策，使用 matplotlib 绘制 | 数值和软件流程检查，不是设备故障准确率 |
| video-pts-evidence.png | 作者编写的演示帧及历史应用产物；放大显示原帧并添加原始 PTS 标签 | 候选事件回看，不是真实视频事件准确率 |

对应输入与产物哈希、统计和数据边界见 `../../research/validation/issue1-*-evidence.json`、`issue1-signal-comparison.json`。历史完整输入、报告及第三方数据集未随文章重新分发，读者可按固定源码与命令重跑；图像合成脚本里的本机路径仅用于记录生成来源。

项目源码许可证不自动覆盖上述第三方数据、文章与图片。VisA 图片保留原作者归属和 CC BY 4.0 要求；其余作者产物按仓库对文章、配图的授权约定处理。
