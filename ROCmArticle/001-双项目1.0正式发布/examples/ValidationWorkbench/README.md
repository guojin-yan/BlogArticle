# 原生 C# 验证窗口（Windows）

这个 WinForms 小工具实际启动随文示例，依次执行预检、HIP VectorAdd、Identity、Affine/ReLU 和 MatMul/ReLU，再从真实日志与 JSON 显示检查结果。它用于观察固定示例的运行情况，原始输出始终另存，不提供性能或生产认证。

安装条件与[示例总说明](../README.md)相同，另需 .NET 10 Windows Desktop Runtime。使用固定 NuGet 包的仍是随文计算示例；窗口自身只使用 .NET WinForms。

在文章仓库根目录的 PowerShell 7 中执行：

```powershell
$articleDir = (Resolve-Path './ROCmArticle/001-双项目1.0正式发布').Path
$hipRoot = Read-Host '输入自己的 ROCm 10.1 HIP 目录'
# 每次选一个尚不存在的结果目录，防止覆盖原始证据。
$resultDir = "$articleDir/.validation/workbench-1"
dotnet run --project "$articleDir/examples/ValidationWorkbench" -c Release -- "$articleDir" "$hipRoot" 'gfx1100' "$resultDir"
```

`gfx1100` 为本文 W7900 基线。预检使用 SDK 的 `hipInfo.exe` 读取实际 gfx 并核对；多架构设备需要先处理显式设备选择。

窗口打开后自动执行，各步骤完成后才填入对应结果。成功时可以看到 VectorAdd 的 65,539 元素、3 次比较，以及两个 ONNX 模型的 4,096 元素 CPU/GPU 检查。出现 `FAIL` 时按结果目录日志排查；`NOT CHECKED` 会继续保留，不转成通过。

结果包含 `*.command.json`、标准输出/错误、预检与依赖检查、数值结果和 `workbench.json`。窗口原生截图与这些文件对应；窗口不是终端模拟器，也不读取一张预制的成功图片。
