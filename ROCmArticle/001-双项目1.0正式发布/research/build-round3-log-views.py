"""Present actual core stdout verbatim in explicitly labelled browser reading pages."""
from pathlib import Path
import html

root = Path(__file__).resolve().parent / 'validation/round3'
for name, title in [('verify', 'HIP 与 ONNX 数值校验'), ('trace', 'MIGraphX 执行跟踪')]:
    log = root / f'logs/core-{name}.log'
    body = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>{title} · 原始日志查看</title><style>body{{font:16px/1.7 "Segoe UI","Microsoft YaHei",sans-serif;margin:32px;color:#19293b}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.65 Consolas,monospace;background:#f3f6f9;padding:20px}}h1{{font-size:26px}}</style><h1>{title} · 本轮实跑记录</h1><p>浏览器日志查看页：逐字呈现实际程序标准输出，不是终端截图。W7900 / gfx1100 · Windows 11 · ROCm 10.1 · MIGraphX 2.18。</p><p>来源：<code>logs/core-{name}.log</code>；命令、时间与退出码见 <code>commands.json</code>。</p><pre>{html.escape(log.read_text(encoding='utf-8-sig'))}</pre></html>'''
    (root / f'results/core-{name}-log-view.html').write_text(body, encoding='utf-8', newline='\n')
