# 简单 OCR 演示：真实招牌上的 APPLE / SODA

2026-11-21，作者要求将正文复杂街景 OCR 改为更简单直观的图片。选取另一张 HierText / Open Images 真实照片中的白底招牌局部，仅展示 **APPLE / SODA** 两行。选图、官方行框与原文在本轮推理前冻结，未根据新预测替换样本；这是有意选择的简单演示，不代表 OCR 总体准确率。

- [简洁展示页](evidence.html)：真实招牌裁剪与两行实际 GPU 输出。
- [原始 C# 批次输出](recognized/batch-evidence.json)、[完整日志](gpu.log)、[运行命令](command.json)、[结果摘要](summary.json)。
- [选图、官方原文、几何及哈希](protocol.json)、[完整来源照片](../round4/document-history/data/originals/b533107ff30932da.jpg)、[原始截图清单](screenshots/manifest.json)。

本次使用原有 PaddleOCR en-v3 模型、正式 C# 应用快照与 MIGraphX GPU，在 W7900 上实际运行：1 个模型实例、1 次编译、2 行输出均与官方原文逐字一致。模型、字典、前处理和阈值没有修改。识别采用官方行框的外接矩形裁剪，保留原始像素，不含自动文字检测；本次没有新增 CPU 概率张量对照或独立精度评测。

两行数据取自官方 `b533107ff30932da` 的第 2 个零基段落、第 0/1 行，分别为 APPLE 和 SODA。大图仅裁出招牌局部供展示，OCR 实际读取 `inputs/` 中两个官方行框 BMP。原图和官方压缩标注 SHA256 核验通过；没有生成图片、重写文字、调对比度、补字或修改预测。之前复杂街景的完整结果与失败行仍保留在 round4 / round5。

输入为 HierText / Open Images，作者 Long、Qin、Panteleev、Bissacco、Fujii、Raptis，Google Research，**CC BY-SA 4.0**。本次修改为裁剪真实招牌/文字行，在报告与截图中加入模型输出；包含图像及裁剪的派生展示保留相同许可与署名。许可原文见 [上游 LICENSE](../round4/document-history/data/upstream-LICENSE)。PaddleOCR 模型上游 Apache-2.0，本轮不重新分发权重。

```text
来源
https://github.com/google-research-datasets/hiertext
固定上游版本
https://github.com/google-research-datasets/hiertext/tree/70b6620b2b112597d8219e11eee9773a1403827c
图片归档
https://open-images-dataset.s3.amazonaws.com/ocr/test.tgz
许可
https://creativecommons.org/licenses/by-sa/4.0/
```

截图由浏览器直接打开实际展示页、回读 URL 后保存原始 JPEG 字节，没有手工编辑。它是实际 GPU 输出的简洁证据报告，不是文档审批页面或终端截图。首次调用因 manifest 使用 Git 目录路径被应用拒绝，日志与命令另存 `gpu-path-rejected*`；随后输入 manifest 和输出目录均通过临时盘符别名访问相同物理文件，成功运行。没有修改应用的路径防护或业务源码，别名用后解除。

正文、预览、索引与说明更新为 v9，其余三个案例继续使用第五轮真实运行截图。本轮原始资料单独放 round6；旧 round2/3/4/5 资料与清单不覆盖，旧可变文档分别按 `a5aeb7d` / `a4f73e4` / `9727a7d` / `1b33655` 核对。文件哈希见 `manifest.json`，核验结果见 `final-checks.json`。没有修改三个正式源码仓库或发送 Issue #2 评论。
