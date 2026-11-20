# 第三轮：截图与四应用执行证据

本轮从应用源码提交 `2f70b96267484b441fa726a3d496b8cc55d47219` 的只读归档构建，Core 使用已发布 1.0.0。所有生成物均在文章目录，原三个源码仓库只读。环境是 Windows 11 / W7900 / gfx1100 / ROCm 10.1 / MIGraphX 2.18，详细 SDK、驱动、Windows build 见 `environment.json`；SDK 11 构建的应用目标框架为 net10.0。

入口：[本轮说明](../../issue-2-截图与四应用复跑.md)、[截图清单](screenshots/manifest.json)、[执行命令](commands.json)、[源码与原生文件 hash](source-binary-hashes.json)。

- `logs/`：构建、测试、每次程序输出和失败。
- `results/`：完整 CPU/HIP 数据、导出报告、视频逐帧结果、文档夹具流程与 OCR 失败现场。
- `inputs/`：模型/数据声明、来源与许可。大模型和原视频不重复分发，用固定 SHA256 标识。
- `screenshots/raw/`：未经改图的浏览器视口截图；两张无效 fullPage 图片也保留。
- `test-results/`：264 项测试的四份 TRX。测试通过不等于全部 GPU 模型通过。

复跑脚本 `../../run-round3-apps.py` 分阶段执行，每次写新日志并立即记录退出码，已存在日志会拒绝覆盖。它要求用户准备指定提交的应用源码快照、已构建 DLL、冻结模型/素材和兼容环境；资产准备方式见应用仓库文档。本轮具体参数在命令清单，读者须替换为自己的资源位置。文档输出别名适配的原因、实际改动与失败事实见本轮说明。

`manifest.json` 在采集结束、服务停止后生成，包含本轮证据和当前文稿 SHA256；`final-checks.json` 核对数值、截图引用、来源、失败保留和第二轮历史数据。它不宣称 Issue #2 全部验收通过。
