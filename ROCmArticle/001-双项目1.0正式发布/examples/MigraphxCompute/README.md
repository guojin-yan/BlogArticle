# MigraphxCompute：固定 ONNX 的 MIGraphX 验证样例

这个样例消费正式版 C# 包，使用随文生成的 `affine-relu.onnx` 验证一条可复现的非平凡计算路径：

`float32[64,64] → max(0, x × 0.5 + 0.25)`

程序同时比较独立 C# 公式、ONNX Runtime CPU、MIGraphX 主机输入输出和 HIP 联合设备路径的 4,096 个输出。默认容差是 `0.001 + 0.001 × abs(CPU参考)`。先按[配套说明](../../05-上手与验证.md)配置当前终端的原生环境，再从本示例目录运行；模型生成器只使用 Python 标准库：

```powershell
python generate-model.py
dotnet run -c Release -- --mode verify
dotnet run -c Release -- --mode trace
dotnet run -c Release -- --mode benchmark
```

从文章仓库根目录执行时，也可以使用：

```powershell
pwsh -File './ROCmArticle/001-双项目1.0正式发布/examples/run-windows.ps1' -Mode trace
```

包装脚本默认读取 `HIP_PATH`；未配置时会提示输入自己的 ROCm 10.1 HIP 安装目录，也可用 `-HipRoot` 显式指定。

`trace` 输出 MIGraphX 的执行记录和 HIP 同步信息；它用于确认固定模型走过 GPU 执行路径，不是独立硬件 Profiler 的逐 Kernel 时间线。`benchmark` 的计时边界包含程序运行、设备拷贝和同步，不能直接当成单个 Kernel 时间。

`matmul-relu.onnx` 是保留的失败复现夹具：同一环境下原生编译会触发 `0xC0000005`，因此没有把它算作通过，也没有据此推断 MIGraphX 的根因。详见上级 [示例说明](../README.md) 和文章的[已知限制](../../05-上手与验证.md)。
