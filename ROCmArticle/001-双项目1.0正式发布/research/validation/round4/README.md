# 第四轮：公开真实数据案例

本目录保存 2026-11-21 的真实数据执行与五张浏览器视口截图。详见[修订与结果](../../真实开源数据案例与截图.md)。

- `inputs/real-input-audit.json`：UCI 官方 ZIP 的原始 6,000 数值、VisA TAR 的 12 张原图逐字节核验，以及 NASA / HierText 身份。
- `surface-public-evidence/report.html`：全部 12 张真实原图、官方标签、实际 CPU/HIP 掩码。`surface-*-batch.json` 是完整未改的执行输出。默认规则误报正常图仍保留，不作 PCB 精度结论。
- `signal-cpu/`、`signal-hip/`：同一 UCI 真实周期的完整报告、输入、配置、频谱与逐窗结果。
- `document-gpu/`：本次 OCR Compile 失败原始记录。`document-history/`：11 月 18 日历史真实 GPU 输出的逐字副本、真实照片/裁剪、全部 24 行核验报告；截图标明执行日期与本次失败。
- `video-protocol.json`：推理前固定的约 30–40 秒连续区间；`video-prepared/`：原视频、抽帧、PTS、FFmpeg/ffprobe 日志；`video-gpu/`：25 帧实际推理、109 检测、12 未复核候选和完整输出。无独立事件真值，未评估精确率/召回率。
- `commands/`、`logs/`：各次实际命令和退出。首次视频准备时误指向不存在的模型目录，失败保留；第二次改用协议原已绑定的 YOLOX Nano detector manifest，成功准备和运行。未更换模型或协议参数。
- `screenshots/manifest.json`：五张原始 JPEG 的 URL、尺寸、时间、哈希及证据对应关系；没有全桌面或终端截图。
- `manifest.json`：入库文件身份；`local-only-files.json`：不重复入库的 SurfaceLab 完整原始 ZIP、工作空间和导出报告身份。这些原始文件仍在本目录本地保留；全部 12 张输入/掩码、CPU/HIP 完整数值和截图都有入库副本。

文章侧脚本位于 `research/`：`run-round4-real-data.py`、`build-round4-document-evidence.py`、`build-round4-evidence.py`、`check-round4.py`。这些脚本使用既有固定源码与构建，仅接受读者自己的资产/SDK/native 路径；数据准备方法见对应开源应用的真实数据文档。执行脚本不能代替首次准备公开数据与模型。

`.gitattributes` 将本目录所有资料按原字节入库，避免行尾转换破坏原始记录。历史 round2 / round3 保持原样，旧正文哈希按相应交付提交验证。本轮没有重新构建/运行 264 项测试，也没有重做性能测量或其他平台验证。

SurfaceLab 模型和 OCR 的原生 Compile 故障根因仍未知。不能把截图替换完成写成四个模型都成功或生产验收完成。
