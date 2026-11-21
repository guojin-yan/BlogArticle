# ROCm 系列文章

本目录用于椒颜皮皮虾（Guojin Yan）的 ROCm / C# 系列文章。文章、规划、事实资料和配图全部在本目录内维护。

## 文章索引

| 顺序 | 文章 | 状态 | 资料 |
| --- | --- | --- | --- |
| 001 | C# 也能玩转 AMD GPU：从自定义计算到 AI 推理，让你的项目也加速起来 | 草稿 v12：复核真实终端截图来源，精简重复文字，突出能力、操作与结果 | [正文](001-双项目1.0正式发布/03-正文.md) · [排版预览](001-双项目1.0正式发布/03-正文预览.html) · [本轮精简与核对](001-双项目1.0正式发布/research/validation/round9/README.md) · [上手与验证](001-双项目1.0正式发布/05-上手与验证.md) · [真实数据与截图](001-双项目1.0正式发布/research/真实开源数据案例与截图.md) · [当前验收对照](001-双项目1.0正式发布/research/issue-2-当前验收对照.md) · [真实终端截图](001-双项目1.0正式发布/research/validation/round8/README.md) · [第七轮记录](001-双项目1.0正式发布/research/validation/round7/README.md) · [简单 OCR 演示](001-双项目1.0正式发布/research/validation/round6/README.md) · [第五轮记录](001-双项目1.0正式发布/research/validation/round5/README.md) · [事实与来源](001-双项目1.0正式发布/01-事实与来源.md) · [配图方案](001-双项目1.0正式发布/02-配图方案.md) |

## 排序与文件约定

- 每篇文章一个目录，使用三位递增编号：`001-主题`、`002-主题`。文章新增时分配新编号，已经使用的编号保持稳定。
- 阅读顺序调整优先更新索引表，不为调整顺序批量改名。尚未开始的选题只列在下面，不提前占号。
- 单篇目录内使用 `00-文章规划.md`、`01-事实与来源.md`、`02-配图方案.md`；开始写作后新增 `03-正文.md`，后续修改直接迭代该正文。
- 图片放在该篇的 `assets/`；可核验的查询快照、必要的素材说明放在 `research/`。不复制整个源码、数据集或开发记录。
- 状态按“规划 → 草稿 → 待核对 → 可发布 → 已发布”更新；已发布时补外部地址、日期和正文版本。

## 后续选题池（建议，尚未定稿）

1. Windows / Ubuntu 24.04 的安装、原生依赖与第一次 GPU 运行。
2. HIP CSharp API 实战：从 HIPRTC 到一个能核验结果的 Kernel。
3. MIGraphX CSharp API 实战：ONNX 解析、GPU 编译、张量与程序复用。
4. HIP 与 MIGraphX 联合使用：Stream、设备输入输出和资源生命周期。
5. YOLO26、PaddleOCR、CLIP、PP-Structure 的专题实战，按实际内容分别成篇。
6. SurfaceLab、SignalDiagnostics、DocumentEvidence、VideoEventSearch 的应用专题，按成熟度与实际验证进度安排。

首篇负责建立项目认知、正式版入口和使用兴趣；安装细节、接口原理及完整业务案例在后续文章展开。

## 写作参考

- 风格库：`JYPPX-Skills` 仓库。
- 首要样本：`references/technical-writing/2026-08-19-hip-csharp-api-0.10.0.md`。
- 仓库系列、编号与资料维护方式见[目录规范](../docs/repository-structure.md)。

资料核对日期：2026-11-21（Asia/Shanghai）。
