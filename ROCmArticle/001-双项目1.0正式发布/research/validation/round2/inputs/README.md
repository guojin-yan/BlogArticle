# 本轮输入与第三方来源

所有 SHA256 由 `../manifest.json` 核对，保留文件用于重现。下载日期：2026-11-20。

| 文件 | 来源/版本 | 许可与使用范围 |
| --- | --- | --- |
| `astronaut.png` | scikit-image v0.19.3；NASA Eileen Collins，原出处 `https://flic.kr/p/r9qvLn` | 上游 `_fetchers.py` 的 astronaut docstring 标 Public domain / no known copyright restrictions；保留 `skimage-fetchers.py`、`photo-source.json` 和源码 BSD 许可 `scikit-image-LICENSE.txt`，不暗示 NASA 背书 |
| `yolox_nano.onnx` | Megvii-BaseDetection/YOLOX release `0.1.1rc0`，tag commit `e1052df71842031413f6030723c3607b839c80ce` | YOLOX 上游 Apache-2.0，原文见 `YOLOX-LICENSE.txt`；模型未经修改，仅作功能/数值/性能演示，无业务准确率承诺 |
| `StbImageSharp-README.md` | 上游 commit `274a325dafc7dd1ddb715c36b32a23fd18b2d9ab` | 上游声明 Public Domain or MIT；本例消费 NuGet 2.30.15，不声称 README 快照就是该包源码 commit |
| `StbImageWriteSharp-README.md` | 上游 commit `82d11ce531bfc33c758d85ff6ee5e864fb2d7242` | 上游声明 Public Domain；本例消费 NuGet 1.16.7，包元数据另保留 |

模型 SHA256：`c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d`。

照片 SHA256：`88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5`。

```text
https://raw.githubusercontent.com/scikit-image/scikit-image/v0.19.3/skimage/data/astronaut.png
https://github.com/scikit-image/scikit-image/blob/v0.19.3/skimage/data/_fetchers.py
https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx
https://github.com/Megvii-BaseDetection/YOLOX/blob/0.1.1rc0/LICENSE
https://github.com/StbSharp/StbImageSharp
https://github.com/StbSharp/StbImageWriteSharp
```

检测 PNG 只在该照片上依据实际 GPU 输出添加红框；没有生成/改写图片主体或修改预测。结果 HTML 为软件导出，不是实机截图。自己的图片由读者自行提供来源与展示权限。
