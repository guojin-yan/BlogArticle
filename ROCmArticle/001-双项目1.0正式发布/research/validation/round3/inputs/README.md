# 本轮输入与展示来源

| 素材 | 来源、许可与使用范围 | 本轮用途 |
| --- | --- | --- |
| SurfaceLab 六图、Signal 双频 CSV、文档 demo 位图/文字 | 应用源码提交 `2f70b962` 自带的作者夹具，代码 Apache-2.0；明确为 authored/synthetic | 规则检测、数值对照和核验流程；不当成真实业务精度数据 |
| SurfaceLab 模型与 VisA pcb1 12 图 | Amazon Science VisA / spot-diff，数据 CC-BY-4.0；原声明见 `surface-data-manifest.json`，模型 ResNet18/patchbank 来源见 `surface-model.json` | 模型 Compile 失败，输入保留；不展示为成功热图或准确率结果 |
| 文档 PP-OCRv3 英文模型 | PaddleOCR Apache-2.0；原模型、字典与转换记录见 `document-model.json`、`document-model-preparation.json` | 实际 GPU 编译尝试失败，未输出识别结果。冻结七行是作者排版/指定矩形，非真实票据 |
| NASA SpaceX Demo-2 Walkout 预览 | NASA 官方素材，见 `video-downloads.json`、`video-nasa-metadata.json`。按 NASA 媒体指南用于事实性技术测试，署名 NASA，不暗示认可；标志、肖像不作为商业推广许可 | 冻结 20 帧和 PTS 的实际 GPU 复跑；原视频未再次分发。截图保留错误预测，无事件质量结论 |
| YOLOX 照片截图 | 上轮 NASA / Eileen Collins，via scikit-image；许可及原图见第二轮 `inputs/README.md` | 本轮仅截图上一轮实际报告，不冒充本轮推理 |

模型 SHA256：Surface patchbank `4d4c55d7b7eb7b5600e9da057df26d117fa99aacec012a0dc2059b0c7c408ac5`；OCR ONNX `f700f92dd1754c7e2e7f6aa8d1624ae056ef88889cca61724f5352238b8e1bb3`；视频 YOLOX `c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d`。输入/字典/协议及原视频的完整指纹均保留在相应 JSON。

```text
VisA / spot-diff
https://github.com/amazon-science/spot-diff

PaddleOCR
https://github.com/PaddlePaddle/PaddleOCR

NASA 官方视频
https://images.nasa.gov/details/KSC-20200530-MH-AJW02-0003-SpaceX_Demo-2_Walkout_Hallway_and_C7_Exit_4K

NASA 媒体指南
https://www.nasa.gov/nasa-brand-center/images-and-media/
```
