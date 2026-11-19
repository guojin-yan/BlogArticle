感谢这份具体的建议。已按七章逻辑完成 v4 修订，保留原标题与六张原配图，并把上一轮遗漏的验证矩阵、非平凡模型证据、性能与已知限制放回正文。

- [修订正文](https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/03-正文.md)
- [P0/P1/P2 逐项处理对照](https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/research/issue-1-修订说明.md)
- [运行、模型下载与复现命令](https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/examples/README.md)

本轮具体完成：

1. 正文区分 HIP / MIGraphX / HIP.Interop，列全七个包和版本关系，说明 Windows MIGraphX 源码构建与补丁来源、ROCm 系统依赖及第三方许可。平台矩阵区分 Windows、WSL2、原生 Linux/KFD，分别记录 PASS、SKIP、NOT TESTED 与已知失败，TFM 只表述为目标框架/包构建范围。
2. Identity 明确为冒烟检查。新增 HIP VectorAdd（65,539 元素×3轮、maxAbs=0）与固定 Affine/ReLU ONNX（4,096 输出，对照独立 C# 公式、ORT CPU、MIGraphX 主机与设备路径）。公开实际 `mul_add_relu_kernel` 执行跟踪、同步设备结果与 HIP event 区间，且明确这些记录不是独立逐 Kernel 硬件 Profiler。
3. 新增 YOLOX Nano 三路径实测：W7900/gfx1100、Windows 11、ROCm10.1/MIGraphX2.18；相同合成RGB输入、batch1、float32、10次预热和30次原始计时。端到端P50/P95为 CPU **15.053/17.147 ms**、MIGraphX主机I/O **19.770/20.796 ms**、HIP联合 **4.155/4.404 ms**。原始模型张量、后处理与计时后输出均通过统一容差，maxAbs约2.19047e-5。没有隐藏主机GPU路径比CPU慢的结果。[完整计时与边界](https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/research/validation/issue1-yolox-benchmark.json)及首轮结果均保留。
4. 深入展示 SignalDiagnostics 的输入、命令、报告、数值检查和复用方法：CPU/HIP 125窗、15待复核，64,125个PSD值比较通过，并公开全部数值对。其余三应用增加实际材料与失败记录，包括 SurfaceLab 漏检/质量未达标、OCR前导空格失败、视频PTS与NeedsReview候选，明确不等于工业精度验收。
5. 文末补三条 Start Here、排错和反馈模板；重要来源固定到tag/commit。原图哈希保持不变，另加三张实际证据图并注明来源。按作者最新博客排版要求，首章集中介绍三类实际效果，命令统一放第四章；正文使用代码块/行内代码展示完整可复制地址，替代文字超链接，仓库配套文档仍保留可点击入口。桌面与手机排版已检查。

剩余边界也已写进正文：没有独立硬件Profiler时间线、清缓存冷启动或单进程峰值显存；显存只有全设备快照，桌面测量未锁时钟/功耗，输入不是检测精度数据集，端到端不含解码/NMS。没有新增其他GPU、原生Linux/KFD完整运行或工业/长期验收。Windows小INT8访问冲突、缺TensorFlow importer，以及本轮发现的64×64 float MatMul/ReLU原生编译0xC0000005均保留说明、夹具或来源，没有当作已修复。

文章和可复现材料的修订已完成；上述未测项不标为实验通过。Issue先保持打开，方便继续核对及补充验证。
