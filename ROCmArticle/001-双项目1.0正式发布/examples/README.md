# 文章 001 的可运行示例

先阅读[正文](../03-正文.md)和[环境与验证说明](../05-上手与验证.md)。安装兼容驱动、VC++ x64 运行库、完整的 ROCm 10.1 系统依赖，以及 .NET 10 或可编译 net10.0 的更新 SDK；包装器需要 PowerShell 7。

Windows 示例只消费固定版本的正式 NuGet 包。首次还原需要 NuGet 网络；MigraphxCompute 另使用 ONNX Runtime CPU 1.23.2 作数值参考。没有自动 CPU 回退来掩盖 GPU 路径失败。

从 BlogArticle 根目录执行，替换自己的 SDK 路径与实际 GPU 架构：

```powershell
pwsh -File './ROCmArticle/001-双项目1.0正式发布/examples/run-windows.ps1' -HipRoot 'D:/AMD/ROCm/10.1.0/HIP' -Architecture gfx1100
```

依次检查设备、HIP VectorAdd、Identity 和 `max(0,x*0.5+0.25)` 的 ONNX 计算。最后一个例子比较 4,096 个 float32 输出，核对 ONNX Runtime CPU、独立 C# 公式、MIGraphX 主机 I/O 和 HIP 设备 I/O。模型经过 HIP 设备缓冲区、Stream、前后处理 Kernel，并记录模型路径的 HIP event 完成间隔。

| 示例 | 目的 |
| --- | --- |
| HipHello | 版本与设备枚举 |
| HipVectorAdd | HIPRTC、自定义 Kernel、同步与 CPU 数值比较 |
| MigraphxHello | Identity 的加载/API/模型执行冒烟检查 |
| MigraphxCompute | 非平凡模型验证、执行跟踪、真实 ONNX 模型的三路径测量 |

## 查看实际执行的 GPU 算子

```powershell
pwsh -File './ROCmArticle/001-双项目1.0正式发布/examples/run-windows.ps1' -HipRoot 'D:/AMD/ROCm/10.1.0/HIP' -Mode trace
```

输出编译后的 GPU 图及 RunTrace 记录。随文固定模型的执行记录含 `mul_add_relu_kernel`。RunTrace 提供执行元数据；HIP event 区间还包含所需 D2D 输出复制，不能拿它当逐 Kernel Profiler 时间线或纯 Kernel 性能。完整说明见正文的证据解释。

## 重做 YOLOX Nano 性能实验

以下脚本只下载约 3.7 MB 的模型，并核对 SHA-256；模型不随本文重新分发。模型属于 Megvii YOLOX 项目，按上游许可使用。本篇输入是固定的合成 RGB float 像素，不是检测精度数据集。

```powershell
$articleDir = (Resolve-Path './ROCmArticle/001-双项目1.0正式发布').Path
$modelDir = "$articleDir/.validation/models"
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
$modelPath = "$modelDir/yolox_nano.onnx"
Invoke-WebRequest 'https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx' -OutFile $modelPath
if ((Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d') { throw 'Model hash mismatch' }
pwsh -File "$articleDir/examples/run-windows.ps1" -HipRoot 'D:/AMD/ROCm/10.1.0/HIP' -Mode benchmark -ModelPath $modelPath -OutputPath "$articleDir/.validation/yolox-benchmark.json"
```

每条路径先预热 10 次，再逐项记录 30 次；分位数采用 nearest rank，不删除离群值。比较端到端时间：从已解码主机 HWC floats 到后处理后的主机输出，包含本路径的数据传输和同步。图像解码、模型编译、一次性缓冲区分配不计入端到端循环；解析、编译与本进程首次执行另列。`warmModelApi` 的不同 I/O 边界写在 JSON 中，不作为纯 Kernel 加速比。

联合路径绑定编译后全部参数，包括 `main:#output_0` 等引擎生成的输出参数，不能只按原始 ONNX 的输入名分配。输出还会做一次 D2D 复制到调用者缓冲区，随后 HIP clamp，再 D2H。

`hipMemGetInfo` 记录全设备显存快照，包含其他进程，不是单进程峰值。桌面环境未锁定 GPU 时钟/功耗，数值只用于当前单机 PoC。任一路径出错或输出超出 `0.001 + 0.001*abs(CPU)` 容差即返回非零，不生成成功结果。除后处理输出外，程序还比较未做 clamp 的原始模型张量与计时完成后的末次输出，避免后处理隐藏原始数值错误；全部比较通过才写成功 JSON。

## 模型生成与已知失败复现

两个小型 ONNX 模型可以由 `MigraphxCompute/generate-model.py` 使用 Python 标准库重新生成。默认使用已经验证的 `affine-relu.onnx`。单独指定 `matmul-relu.onnx` 可以复现本轮 Windows 原生编译失败；该文件是故障夹具，不作为快速开始的成功案例。原始失败日志与版本记录保留在 `../research/validation/`。
