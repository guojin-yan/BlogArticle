# 文章 001 的可运行示例

先阅读[正文](../03-正文.md)和[环境与验证说明](../05-上手与验证.md)。安装兼容驱动、VC++ x64 运行库、完整的 ROCm 10.1 系统依赖，以及 .NET 10 或可编译 net10.0 的更新 SDK；包装器需要 PowerShell 7。

Windows 示例只消费固定版本的正式 NuGet 包。首次还原需要 NuGet 网络；MigraphxCompute 另使用 ONNX Runtime CPU 1.23.2 作数值参考。没有自动 CPU 回退来掩盖 GPU 路径失败。

在准备存放源码的目录打开 PowerShell 7。首次使用先克隆仓库；已有副本时直接进入其根目录，跳过前两行：

```powershell
git clone https://github.com/guojin-yan/BlogArticle.git
Set-Location './BlogArticle'
$articleDir = (Resolve-Path './ROCmArticle/001-双项目1.0正式发布').Path
pwsh -File "$articleDir/examples/run-windows.ps1" -Architecture gfx1100
```

仓库可放在任意盘符和目录。脚本默认读取 `HIP_PATH`；未配置时，按提示输入自己的 ROCm 10.1 HIP 安装目录（包含 `bin`、`lib`）。可通过 `-HipRoot` 显式传入其他安装目录。`gfx1100` 为本文设备基线，其他架构需先核对引擎支持范围。

依次检查设备、HIP VectorAdd、Identity 和 `max(0,x*0.5+0.25)` 的 ONNX 计算。最后一个例子比较 4,096 个 float32 输出，核对 ONNX Runtime CPU、独立 C# 公式、MIGraphX 主机 I/O 和 HIP 设备 I/O。模型经过 HIP 设备缓冲区、Stream、前后处理 Kernel，并记录模型路径的 HIP event 完成间隔。

| 示例 | 目的 |
| --- | --- |
| HipHello | 版本与设备枚举 |
| HipVectorAdd | HIPRTC、自定义 Kernel、同步与 CPU 数值比较 |
| MigraphxHello | Identity 的加载/API/模型执行冒烟检查 |
| MigraphxCompute | 非平凡模型验证、执行跟踪、真实 ONNX 模型的三路径测量 |

## 查看实际执行的 GPU 算子

在上面的终端继续运行：

```powershell
pwsh -File "$articleDir/examples/run-windows.ps1" -Mode trace
```

输出编译后的 GPU 图及 RunTrace 记录。随文固定模型的执行记录含 `mul_add_relu_kernel`。RunTrace 提供执行元数据；HIP event 区间还包含所需 D2D 输出复制，不能拿它当逐 Kernel Profiler 时间线或纯 Kernel 性能。完整说明见正文的证据解释。

## 重做 YOLOX Nano 性能实验

以下脚本下载约 3.7 MB 的模型，并核对 SHA-256。第二轮证据目录另保留实测模型及上游 Apache-2.0 许可。模型来自 Megvii YOLOX `0.1.1rc0`。性能输入是固定的合成 RGB float 像素，不是检测精度数据集。

```powershell
$articleDir = (Resolve-Path './ROCmArticle/001-双项目1.0正式发布').Path
$modelDir = "$articleDir/.validation/models"
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
$modelPath = "$modelDir/yolox_nano.onnx"
Invoke-WebRequest 'https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx' -OutFile $modelPath
if ((Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d') { throw 'Model hash mismatch' }
pwsh -File "$articleDir/examples/run-windows.ps1" -Mode benchmark -ModelPath $modelPath -OutputPath "$articleDir/.validation/yolox-benchmark.json"
```

上面的 `benchmark` 保留首轮三路径实验。第二轮使用 `ablation` 的五路对照，每路先预热 10 次，再交错随机测量 30 次；分位数采用 nearest rank，不删除离群值。比较端到端时间：从已解码主机 HWC floats 到后处理后的主机输出，包含本路径的数据传输和同步。图像解码、NMS、模型编译、一次性缓冲区分配不计入端到端循环；解析、编译与本进程首次执行另列。`warmModelApi` 的不同 I/O 边界写在 JSON 中，不作为纯 Kernel 加速比。

```powershell
# 默认 5 个独立进程；每路 10 次预热、30 个逐次样本。
pwsh -File "$articleDir/examples/run-round2.ps1" -Rounds 5
```

输出默认在 `$articleDir/.validation/round2`。Host 复用组只能重放固定输入，不能代表连续新帧；Device+CPU 组保留 H2D/D2H/D2D，前后处理改由 CPU 完成。五组代码、执行顺序、全部逐次数据与解释见[第二轮修订说明](../research/issue-2-修订说明.md)。

联合路径绑定编译后全部参数，包括 `main:#output_0` 等引擎生成的输出参数，不能只按原始 ONNX 的输入名分配。输出还会做一次 D2D 复制到调用者缓冲区，随后 HIP clamp，再 D2H。

`hipMemGetInfo` 记录全设备显存快照，包含其他进程，不是单进程峰值。桌面环境未锁定 GPU 时钟/功耗，数值只用于当前单机 PoC。任一路径出错或输出超出 `0.001 + 0.001*abs(CPU)` 容差即返回非零，不生成成功结果。除后处理输出外，程序还比较未做 clamp 的原始模型张量与计时完成后的末次输出，避免后处理隐藏原始数值错误；全部比较通过才写成功 JSON。

## 模型生成与已知失败复现

两个小型 ONNX 模型可以由 `MigraphxCompute/generate-model.py` 使用 Python 标准库重新生成。默认使用已经验证的 `affine-relu.onnx`。单独指定 `matmul-relu.onnx` 可以复现本轮 Windows 原生编译失败；该文件是故障夹具，不作为快速开始的成功案例。原始失败日志与版本记录保留在 `../research/validation/`。

## 只检查环境，不改系统设置

```powershell
pwsh -File "$articleDir/examples/run-windows.ps1" -CheckOnly -OutputPath "$articleDir/.validation/doctor.json"
```

输出 `PASS / FAIL / SKIP / NOT CHECKED` 和排错建议；JSON 记录实际加载模块的路径、版本和 SHA256，旁边的 `*.inventory.json` 记录 PowerShell、SDK、Windows、GPU 和驱动。HIPRTC 会做一次小型编译，MIGraphX 会探测对象。目录/DLL 存在只代表文件检查，不代表全部数学库和模型可用；完整依赖链、版本冲突认证、硬件 gfx 自动识别标为 `NOT CHECKED`。不修改全局 PATH，不安装依赖；后续仍需运行四个示例及自己的模型。

## 真实照片：从输入到检测结果

在仓库根目录的 PowerShell 7 继续执行：

```powershell
$photoRoot = "$articleDir/.validation/photo"
New-Item -ItemType Directory -Force -Path "$photoRoot/inputs", "$photoRoot/results" | Out-Null
$photoPath = "$photoRoot/inputs/astronaut.png"
$modelPath = "$photoRoot/inputs/yolox_nano.onnx"
Invoke-WebRequest 'https://raw.githubusercontent.com/scikit-image/scikit-image/v0.19.3/skimage/data/astronaut.png' -OutFile $photoPath
Invoke-WebRequest 'https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx' -OutFile $modelPath
if ((Get-FileHash -LiteralPath $photoPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne '88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5') { throw 'Image hash mismatch' }
if ((Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d') { throw 'Model hash mismatch' }
pwsh -File "$articleDir/examples/run-windows.ps1" -Mode detect -ModelPath $modelPath -ImagePath $photoPath -OutputPath "$photoRoot/results/photo.json"
```

成功时显示 `1 detections; raw GPU/CPU failures=0`，`person` 分数约 0.9259。结果目录导出输入副本、带框 PNG、框/分数 JSON 及可直接打开的 `detection-report.html`。换图时只替换 `-ImagePath`，并自行确认素材使用权限；报告不自动推断你自己的图片来源。

流程是 STB 解码、双线性缩放（整数舍入）、左上补 114、BGR `[0,255]`、CHW 416 → GPU 模型 → YOLOX grid/stride 解码 → objectness×class → 阈值 0.30 → 类内 greedy NMS（IoU 0.45）→ 原图坐标。前后处理在 CPU；这个完整功能演示与 HIP 合成输入 benchmark 分开。没有独立标注，不计算 mAP。

示例照片为 NASA 宇航员 Eileen Collins，scikit-image 源码说明公有领域/无已知限制，来源及许可快照见[素材说明](../research/validation/round2/inputs/README.md)。新增 `StbImageSharp 2.30.15`（上游声明 Public Domain or MIT）及 `StbImageWriteSharp 1.16.7`（Public Domain）；保留对应上游 README 与包元数据，不把项目 Apache-2.0 代替第三方许可。

## 缓存与进程重启

选择一个**新的、仅含 ASCII 字符**的缓存目录；不要照搬作者的安装路径。每条包装命令启动独立进程：

```powershell
$cacheRoot = Read-Host '输入新的 ASCII 缓存目录（路径不要含中文）'
if ($cacheRoot -match '[^\x00-\x7F]') { throw '本轮引擎中文缓存路径保存失败，请用 ASCII 路径' }
if (Test-Path -LiteralPath $cacheRoot) { throw '请选一个尚不存在的目录，以验证首次未命中' }
foreach ($round in 1..3) {
    pwsh -File "$articleDir/examples/run-windows.ps1" -Mode cache -ModelPath $modelPath -CacheKind parsed -CachePath $cacheRoot -OutputPath "$articleDir/.validation/cache-$round.json"
}
```

预期为 `Rebuilt`、`Hit`、`Hit`，全部输出须通过 CPU 数值对照。**命中后仍需 Compile**：本轮实测约 27–32 秒，并未免编译。`compiled` 是保留的故障复现选项，当前 YOLOX 在加载后再次 Compile 失败；不要当成成功路径。没有清理驱动或磁盘缓存，`cache-cold NOT TESTED`。所有历史失败和修正过程见第二轮资料。
