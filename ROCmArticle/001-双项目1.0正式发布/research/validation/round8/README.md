# 第八轮：实际 PowerShell 终端截图

2026-11-21，作者指出正文中的日志网页截图不等于实际运行终端截图。第七轮新增的原生 C# 验证窗口属于应用截图，也不能替代终端。本轮将正文核心计算与跟踪的两处展示换为**本轮真实 PowerShell 7 / ConsoleHost 运行窗口**。

| 展示 | 本轮实际执行 | 原始资料 |
| --- | --- | --- |
| [设备、VectorAdd、Identity 与 Affine/ReLU](screenshots/01-powershell-verify-frame.png) | W7900/gfx1100；65,539 元素、3轮、最大绝对误差0；Identity输出1,2,3,4；4,096元素CPU/Host GPU/联合GPU数值比较通过 | [命令与日志哈希](verify/command.json)、[原始输出](verify/stdout-stderr.txt)、[PowerShell transcript](verify/transcript.txt)、[数值JSON](verify/result.json) |
| [MIGraphX 编译图与 RunTrace](screenshots/02-powershell-trace-frame.png) | 本轮实际执行trace，包含 `mul_add_relu_kernel`、设备复制/同步与数值校验 | [命令与日志哈希](trace/command.json)、[原始输出](trace/stdout-stderr.txt)、[PowerShell transcript](trace/transcript.txt)、[数值JSON](trace/result.json) |

两个窗口由命令工具启动 `conhost.exe` 与 PowerShell，脚本真实调用随文 `run-windows.ps1`，将本次程序标准输出同时写到控制台和原始文件；不是读取之前的日志打印出来。命令开始/结束时间、退出码、PowerShell PID、窗口身份、脚本和输出哈希全部对应保存。源脚本为 `research/run-round8-terminal.ps1`，采集脚本为 `research/capture-round8-window.py`。

截图使用 Win32 `PrintWindow` 只读采集指定 HWND 的完整窗口位图，保存原始 PNG。采集前重新核对 PID、标题与本轮命令记录，包含真实标题栏、命令、输出、提示符，没有截取其他应用或全桌面，也没有向终端模拟键鼠输入。没有日志网页、终端重绘、拼字、裁切、打码或修改结果。截图原始元数据见 [verify-capture.json](screenshots/verify-capture.json)、[trace-capture.json](screenshots/trace-capture.json)与[清单](screenshots/manifest.json)。

最初的启动命令使用了不存在的 PowerShell 安装位置，没有模型运行；改为本机已安装的实际可执行文件后完成验证。一次重复启动因结果目录已存在而停止，没有覆盖第一次输出。浏览器/电脑控制接口没有列出控制台窗口，系统截图工具的浮层亦未可靠绑定，因此没有把这些尝试写成有效截图。随后采用不注入输入的窗口只读位图采集。早期 Pillow 客户区和完整窗口探测 PNG 均原样保留，正文使用最终带元数据的 `*-frame.png`；完整窗口探测曾在保存图像后的句柄释放阶段报错，正式脚本已声明完整句柄类型，最终两次采集退出0。

本轮复用已有 Windows 11 / W7900 / ROCm10.1 / MIGraphX2.18 和包缓存，只重新执行核心 `verify`、`trace`。它不是新环境、性能、264项测试、四应用或生产验收。第四节原生日志中的路径字符编码保持原样，没有为截图改写路径输出；读者可复制命令仍使用正文相对路径。

原生 C# 应用图、浏览器报告和旧日志阅读页按原类型保留在之前各轮；正文不再将日志阅读页用于核心运行截图。第二至第七轮原始文件和 manifest 不覆盖，可变文稿按各轮提交读取：`a5aeb7d` / `a4f73e4` / `9727a7d` / `1b33655` / `4096421` / `3126902`。

本轮[逐项对照](../../issue-2-当前验收对照.md)、[检查结果](final-checks.json)与[文件清单](manifest.json)单独保存。没有发送 Issue #2 评论或关闭问题。
