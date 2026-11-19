# 椒颜皮皮虾的技术文章

这里收录我围绕 C# / .NET、GPU 计算、AI 模型部署和开源项目编写的系列文章，以及配套的图片、示例代码和写作资料。

文章按主题分系列，每篇文章独立维护。后续会继续加入更多项目的介绍、实战教程和开发经验。

## 系列导航

| 系列 | 内容 | 入口 |
| --- | --- | --- |
| ROCm / C# | HIP、MIGraphX、AMD GPU 计算与应用案例 | [ROCm 系列](ROCmArticle/README.md) |

## 文章索引

| 系列 | 编号 | 文章 |
| --- | --- | --- |
| ROCm / C# | 001 | [C# 也能玩转 AMD GPU：从自定义计算到 AI 推理，让你的项目也加速起来](ROCmArticle/001-双项目1.0正式发布/03-正文.md) |

点击文章标题即可在 GitHub 阅读 Markdown 正文。每篇文章目录还保留配图与示例；HTML 预览可克隆或下载仓库后在本地打开。

## 目录组织

```text
BlogArticle/
├── README.md                     # 总导航与跨系列文章索引
├── docs/
│   └── repository-structure.md   # 系列、编号、资料与状态约定
├── templates/
│   └── article/README.md         # 新文章目录与起稿模板
└── ROCmArticle/                  # ROCm 系列，保持现有路径
    ├── README.md                 # 本系列索引与后续选题
    └── 001-双项目1.0正式发布/
        ├── 03-正文.md            # 阅读与编辑主文件
        ├── 03-正文预览.html      # 本地排版预览
        ├── assets/              # 配图与必要的小型模型
        ├── examples/            # 配套代码
        ├── research/            # 来源快照、提示词和验证资料
        └── *.md                 # 规划、事实、配图方案与编辑记录
```

新主题可以增加与 `ROCmArticle` 并列的系列目录。系列内独立编号，已分配的编号和文章路径保持稳定，排序通过索引调整。具体约定见[目录规范](docs/repository-structure.md)，新文章可参考[文章模板](templates/article/README.md)。

## 相关开源项目

| 项目 | 地址 |
| --- | --- |
| HIP CSharp API | https://github.com/guojin-yan/HIP-CSharp-API |
| MIGraphX CSharp API | https://github.com/guojin-yan/MIGraphX-CSharp-API |
| ROCm C# 应用集合 | https://github.com/guojin-yan/ROCm-CSharp-Projects |

## 使用与反馈

欢迎通过 Issue 交流文章勘误、运行体验和希望继续展开的选题。反馈代码问题时，可以同时附上文章编号、包版本和运行环境。

文章与配图的使用授权以各自说明或作者授权为准；引用的第三方代码、模型及素材遵循其原有许可。相关项目的开源许可不自动覆盖本仓库文章。

作者：Guojin Yan / 椒颜皮皮虾。
