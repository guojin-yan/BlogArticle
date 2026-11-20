# 真实数据、模型与截图署名

源码仓库的许可不自动覆盖以下数据、媒体、模型或它们的派生截图。

| 资料 | 来源与作者 | 许可与本目录处理 |
| --- | --- | --- |
| SurfaceLab PCB 原图 | VisA，Yang Zou 等 / Amazon Science，SPot-the-Difference 项目 | **CC BY 4.0**。固定 pcb1 测试子集 12 张原 JPG 字节不改；灰度掩码由实际程序产生，截图加入工作台界面。未手画异常位置。所有该图像及其派生展示应保留署名和许可。 |
| Signal 原始压力值 | Condition monitoring of hydraulic systems，Nikolai Helwig、Eliseo Pignanelli、Andreas Schütze，UCI，2015，DOI 10.24432/C5CW21 | **CC BY 4.0**。PS1 第 1 周期，不缩放、不重采样；添加相对时间和 CSV 表头。窗口/PSD/RMS/规则结果是程序计算，规则不是官方故障标注。 |
| OCR 原照片、标注及裁剪 | HierText，Shangbang Long、Siyang Qin、Dmitry Panteleev、Alessandro Bissacco、Yasuhisa Fujii、Michalis Raptis，Google Research；原图来自 Open Images | **CC BY-SA 4.0**，随附 `document-history/data/upstream-LICENSE` 与上游 README。修改：官方行多边形取轴对齐矩形并裁剪为 BMP；报告和截图加入真实预测及对照。原图/标签、派生裁剪和包含它们的展示按相同许可保留署名。24 行均出自 `417cfad1483563c3`，未改官方原文。 |
| 视频与原帧 | NASA Image and Video Library，SpaceX Demo-2 Walkout，2020-05-30；元数据及官方媒体指南在 `inputs/nasa/` | 按 **NASA images-and-media guidelines** 作事实性教育/技术分析并署名 NASA。不是 CC / Apache 数据集许可；标志、可识别人物和第三方权利另按官方指南，不能暗示 NASA 认可、合作或商业代言。原视频字节保留；抽帧、实际程序预测框及报告为派生技术证据。 |
| YOLOX Nano | Megvii YOLOX 上游发布，ONNX SHA256 `c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d` | 上游 Apache-2.0；本轮沿用冻结 detector manifest，仅记录身份，不重新分发模型权重。 |
| PaddleOCR en-v3 | PaddleOCR 上游，ONNX SHA256 `f700f92dd1754c7e2e7f6aa8d1624ae056ef88889cca61724f5352238b8e1bb3` | 上游 Apache-2.0；使用既有固定模型，未重新分发权重。本次 Compile 失败，截图的历史预测与本次核验明确分开。 |

```text
VisA 官方项目与原始归档
https://github.com/amazon-science/spot-diff
https://amazon-visual-anomaly.s3.us-west-2.amazonaws.com/VisA_20220922.tar

UCI 官方页与 DOI
https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems
https://doi.org/10.24432/C5CW21

HierText 官方项目（资料固定到 70b6620b2b112597d8219e11eee9773a1403827c）
https://github.com/google-research-datasets/hiertext

NASA 素材与使用指南
https://images.nasa.gov/details/KSC-20200530-MH-AJW02-0003-SpaceX_Demo-2_Walkout_Hallway_and_C7_Exit_4K
https://www.nasa.gov/nasa-brand-center/images-and-media/

CC BY 4.0
https://creativecommons.org/licenses/by/4.0/
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
```

截图是实际浏览器视口的原始 JPEG，不包含桌面或终端外壳。模型框来自实际执行的程序报告，没有手工补框、替换预测或修改官方标注。OCR 核验报告重新组织了真实原图、裁剪和历史输出的版式，未模拟业务审批界面。
