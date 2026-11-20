# MigraphxCompute：固定 ONNX 的 MIGraphX 验证样例

这个样例消费正式版 C# 包，使用随文生成的 `affine-relu.onnx` 验证一条可复现的非平凡计算路径：

`float32[64,64] → max(0, x × 0.5 + 0.25)`

程序同时比较独立 C# 公式、ONNX Runtime CPU、MIGraphX 主机输入输出和 HIP 联合设备路径的 4,096 个输出。默认容差是 `0.001 + 0.001 × abs(CPU参考)`。先按[配套说明](../../05-上手与验证.md)配置当前终端的原生环境，再从本示例目录运行；模型生成器只使用 Python 标准库：

```powershell
python generate-model.py
dotnet run -c Release -- --mode verify
dotnet run -c Release -- --mode trace
dotnet run -c Release -- --mode doctor
```

从文章仓库根目录执行时，也可以使用：

```powershell
pwsh -File './ROCmArticle/001-双项目1.0正式发布/examples/run-windows.ps1' -Mode trace
```

包装脚本默认读取 `HIP_PATH`；未配置时会提示输入自己的 ROCm 10.1 HIP 安装目录，也可用 `-HipRoot` 显式指定。

`trace` 输出 MIGraphX 的执行记录和 HIP 同步信息；它用于确认固定模型走过 GPU 执行路径，不是独立硬件 Profiler 的逐 Kernel 时间线。`benchmark` 的计时边界包含程序运行、设备拷贝和同步，不能直接当成单个 Kernel 时间。

`matmul-relu.onnx` 是保留的失败复现夹具：同一环境下原生编译会触发 `0xC0000005`，因此没有把它算作通过，也没有据此推断 MIGraphX 的根因。详见上级 [示例说明](../README.md) 和文章的[已知限制](../../05-上手与验证.md)。

## 第二轮新增模式

| 模式 | 用途与参数 |
| --- | --- |
| `doctor` | 非破坏性预检；完整系统清单请使用上级包装脚本 `-CheckOnly` |
| `ablation` | `--model PATH --seed 20261121`；CPU、Host 新建、Host 固定输入复用、Device+CPU、完整 HIP 五路随机交错测量 |
| `detect` | `--model PATH --image PATH`；真实图片预处理、GPU、YOLOX 解码/NMS、PNG/JSON/HTML 导出 |
| `cache` | `--model PATH --cache ASCII_PATH --cache-kind parsed`；显式缓存、保存/加载、重新编译与 CPU 校验 |

所有模式均可传 `--output PATH`；输入/输出参数是键值对。`detect` 固定为 YOLOX Nano 416、COCO 80 类 raw 输出，不是任意 ONNX 检测器。Host 参数深拷贝且无原地更新接口，复用组仅固定输入重放。`cache-kind compiled` 当前是失败复现分支，默认 `parsed`。

可复制的照片下载/hash检查、缓存三进程命令、五轮入口和许可见[上级说明](../README.md)。结果与边界见[第二轮修订说明](../../research/issue-2-修订说明.md)。历史 `benchmark` 模式保留三条路径和 Warm API 计时，正文采用新五轮消融结果。
