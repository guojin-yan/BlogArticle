# 第二轮真实运行证据

2026-11-20（Asia/Shanghai），对应 BlogArticle Issue #2。结论和未完成项见[修订对照](../../issue-2-修订说明.md)。这里保留原始日志、全部样本和实际失败，不把运行证据写成全部验收通过。

| 路径 | 内容 |
| --- | --- |
| `manifest.json` | 环境、基线、源码阶段、素材/证据 SHA256 和未测范围 |
| `environment.json`、`results/*inventory.json` | Windows build、驱动、CPU、SDK、PowerShell、后台/时钟/缓存条件 |
| `commands.txt` | 初次原始命令，cache 当时默认 compiled；后续上下文见 `execution-context.json` |
| `round2-benchmark.json` | 所有五轮的 P50/P95、启动与首次调用汇总 |
| `results/benchmark-1..5.json` | 五轮全部逐次样本、随机顺序、误差、模型/输入 hash |
| `logs/benchmark-1..5.log` | 各轮完整原生日志，保留 MIOpen 诊断 |
| `inputs/` | 实测原图、模型、来源与第三方许可说明 |
| `results/photo.json`、`yolox-detections.png`、`detection-report.html` | 初次完整照片演示，保留原文件；PNG 是程序输出，不是截图 |
| `results/photo-final/`、`logs/photo-final.log` | 最终报告导出复验：输入副本、真实设备名、自包含 HTML；不覆盖初次证据 |
| `logs/cache*.log`、`results/cache*-exit.json` | 全部缓存尝试，包括测试代码错误与实际失败 |
| `logs/matmul-*.log`、`logs/affine-native.log` | C# 和直接原生 C API 对照，MatMul FAIL / root cause unknown |
| `logs/clone-*`、`results/clone-https-attempt.json` | SSH clone 成功，HTTPS clone 未完成 |
| `results/quickstart-*`、对应日志 | 隔离检出上的预检与四示例；同一物理机/驱动/SDK/NuGet缓存，非新OS/独立读者 |
| `doctor-missing-sdk*`、`doctor-fixed-positive*` 日志/JSON | 缺失SDK预检初次丢失JSON的失败、修复后的结构化FAIL及正常环境回归 |
| `sources/` | 实验阶段代码快照；benchmark 主文件与当时记录的 SHA256 完全相符 |
| `screenshots/raw/README.md` | 桌面截图 BLOCKED / NOT CAPTURED 原因 |

## 重现

从仓库根目录按 `examples/README.md` 配置 HIP 环境。性能运行：

```powershell
$articleDir = (Resolve-Path './ROCmArticle/001-双项目1.0正式发布').Path
pwsh -File "$articleDir/examples/run-round2.ps1" -Rounds 5
```

默认输出 `$articleDir/.validation/round2`，不要把 `-OutputRoot` 指向本归档。doctor/照片/parsed 与 compiled 缓存/trace/MatMul 的组合入口：

```powershell
$sdkRoot = Read-Host '输入自己的 ROCm 10.1 HIP 安装目录'
$cacheRoot = Read-Host '输入新的 ASCII 缓存目录'
pwsh -File "$articleDir/research/run-round2-evidence.ps1" -HipRoot $sdkRoot -CacheRoot $cacheRoot
```

该脚本输出到新目录 `.validation/evidence-new`，已有目录会拒绝覆盖。MatMul/compiled 缓存预期有 FAIL，脚本保留日志而非包装为成功。它是当前候选代码的复现入口，不声称重建了历史中每个旧测试程序错误。

## 核验

```powershell
python "$articleDir/research/summarize-round2.py"
python "$articleDir/research/check-issue1.py"
python "$articleDir/research/check-round2.py"
python "$articleDir/research/build-round2-manifest.py"
python "$articleDir/research/build-round2-manifest.py" --verify
```

预览先按生成器要求准备 Python Markdown 模块并运行 `build-preview.py`。本轮 v5 仅检查生成 HTML/源码、图像文件与实际数值；桌面控制被停止，没有完成新的桌面/手机布局视觉验收。

历史日志含实测绝对路径，保留用于追溯，不是读者需要复制的路径。缓存 payload 位于忽略目录、未打包；可按相同模型、native hash 和命令重建，不能把缺少 payload 解释成冷缓存测试。

本目录 `.gitattributes` 禁止换行自动转换，保留原始字节及 SHA256。提交前还可运行 `build-round2-manifest.py --verify-index`，核对 Git 暂存内容与清单完全一致。
