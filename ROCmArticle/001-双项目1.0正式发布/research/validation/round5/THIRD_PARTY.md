# 本轮真实数据、模型与截图署名

四张截图与报告继续适用[第四轮完整第三方来源、许可及处理说明](../round4/THIRD_PARTY.md)。该说明中的第四轮 Compile 失败是历史状态；本轮结果以 [README](README.md) 为准。

- **VisA pcb1**：Yang Zou 等 / Amazon Science，CC BY 4.0。12 张原 JPG 不变，本轮加入 DINOv2/PatchCore 实际 GPU 掩码、热图、叠加图及工作台截图。模型 ONNX SHA256 `885e22beaeecf14fdda2576bdd2ac0d5a03dd84290964c00e43367e5d51839c7`；不重新分发权重。DINOv2 vits14 上游为 Meta / facebookresearch，Apache-2.0；模型输出不代表上游质量背书。
- **UCI Condition monitoring of hydraulic systems**：Nikolai Helwig、Eliseo Pignanelli、Andreas Schütze，2015，DOI `10.24432/C5CW21`，CC BY 4.0。PS1 第一周期原始压力值不缩放、不重采样；相对时间、CSV 表头及分析输出为处理结果。
- **HierText / Open Images**：Shangbang Long、Siyang Qin、Dmitry Panteleev、Alessandro Bissacco、Yasuhisa Fujii、Michalis Raptis，Google Research，CC BY-SA 4.0。原图 `417cfad1483563c3` 及官方标注不变；按官方框裁剪，报告与截图加入本轮识别和原文对照。包含这些图像/裁剪的派生展示继续按 CC BY-SA 4.0 保留署名；许可原文见 [上游 LICENSE](../round4/document-history/data/upstream-LICENSE)。PaddleOCR en-v3 模型上游 Apache-2.0，不重新分发权重。
- **NASA Demo-2 Walkout**：NASA Image and Video Library，2020-05-30。沿用冻结原视频与 25 个原帧，按 NASA 媒体使用指南作事实性技术分析；保留署名，不暗示 NASA 认可、合作或商业代言。人物、标志与第三方权利按该指南。YOLOX Nano 上游 Megvii，Apache-2.0，不重新分发权重。

```text
VisA
https://github.com/amazon-science/spot-diff
DINOv2
https://github.com/facebookresearch/dinov2
UCI / DOI
https://doi.org/10.24432/C5CW21
HierText
https://github.com/google-research-datasets/hiertext
NASA 素材与使用指南
https://images.nasa.gov/details/KSC-20200530-MH-AJW02-0003-SpaceX_Demo-2_Walkout_Hallway_and_C7_Exit_4K
https://www.nasa.gov/nasa-brand-center/images-and-media/
CC BY 4.0
https://creativecommons.org/licenses/by/4.0/
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
```

浏览器原始截图没有编辑。SurfaceLab 是实际工作台，Signal / Video 是应用原始 HTML，OCR 是从本轮真实 GPU 批次生成并标明用途的证据报告。没有手画检测框、替换预测或修改官方标签。
