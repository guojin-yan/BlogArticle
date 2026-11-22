# v14：网站地址代码展示与 Issue #2 逐项复核

日期：2026-11-22（Asia/Shanghai）。本轮修正排版并复核已有证据，没有新增 GPU 运行、性能测量或截图。保留 v13 的产品特色和关键步骤解释，以及原标题、七章、七包、14 张图与全部运行命令。

## 网站展示

正文最后三个 Start Here 点击入口已移除，名称及完整地址在代码块中保留。事实来源、上手说明和素材说明中的网站也使用代码展示；本地资料导航和图片引用保留。历史 Issue 原文、旧修订及原始输出保持原字节。

Issue P2-3 原本建议同时提供可点击入口，作者最新要求“网站都使用代码方式展示”覆盖该建议；[逐项对照](../../issue-2-当前验收对照.md)将其单列为 `AUTHOR_OVERRIDE`，不标为按原文完成。

## 核对范围与证据

- **逐项要求**：读取最新 GitHub Issue 原文，将 27 条任务及 9 条验收门槛逐一映射到具体文件，并核对文件存在、哈希与声明范围。原文见[只读快照](issue-2-source.json)，完整要求与状态见[结构化对照](issue-2-requirements.json)。
- **性能**：从第二轮五份原始 JSON 重算 750 样本的各轮 P50/P95、五轮中位数、启动/首次执行范围，核对随机交错顺序、输入哈希与数值容差；保留 Host 固定输入重放的不可比边界。
- **运行与截图**：复核第八轮两张 PowerShell 原图、PID/时间、命令、日志和 transcript 哈希；核对第七轮 doctor、新远端 clone、空包缓存、MatMul 与真实 NASA 照片结果。
- **四案例**：核对 VisA 12 图结果及 3 张异常漏检、UCI 45 窗/5,805 PSD 值、复杂 HierText 24 行及 19 行失败、NASA 25 帧/109 检测/12 候选；简单 OCR 的 APPLE/SODA 两行单独保留。
- **历史保留**：第二至第八轮按原 manifest 核验，可变文稿使用相应历史提交；第二至第十轮证据目录相对本轮基线未改。没有把历史 PASS 写成本轮运行。

复核脚本为[check-v14-issue2.py](../../check-v14-issue2.py)，结果见[final-checks.json](final-checks.json)。这是已有证据核对，不是新的 GPU 或生产验收。

## 未执行范围与回复

仍使用同一物理 Windows/W7900，系统驱动、SDK 复用；无新 OS 或独立人类读者。冷缓存、逐 Kernel Profiler、进程峰值显存、其他 GPU/原生 Linux、小 INT8 本轮未验；四组同名 DLL 字节差异及动态求解器/全模型兼容性仍 `NOT CHECKED`。MatMul 的本机路径触发条件和有效修正已有证据，原生内部源码级根因仍未知。

作者已授权核对后回复 Issue #2。发布正文见[回复文稿](issue-2-reply.md)，已发布并回读验证正文一致；[发布记录](issue-2-reply-published.json)保存评论 URL、ID、时间和正文哈希。内容提交为 `bea9ba5`，回复前已推送并确认 37 个证据入口存在。Issue 保持开放。

```text
https://github.com/guojin-yan/BlogArticle/issues/2#issuecomment-7081395459
```
