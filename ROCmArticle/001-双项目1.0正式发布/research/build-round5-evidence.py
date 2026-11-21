"""Build a plainly labelled report from current raw OCR output; never change predictions."""
import datetime as dt,hashlib,html,json
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1];out=root/'research/validation/round5';doc=out/'document-hiertext-native-path'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
evaluation=read(doc/'evaluation.json');batch=read(doc/'recognized/batch-evidence.json')
assert evaluation['lineCount']==len(batch['lines'])==24
assert batch['modelInstances']==batch['recognizer']['programCompilations']==1
e=lambda s:html.escape(str(s),quote=True)
data='../../round4/document-history/data/'
rows=[]
for n,(r,line) in enumerate(zip(evaluation['records'],batch['lines'],strict=True),1):
    assert r['predicted']==line['recognition']['text'] and r['reference']['passed'] is True
    assert sha(doc.parent.parent/'round4/document-history/data'/r['image'])==r['imageSha256']
    rows.append(f'<tr><td>{n:02d}</td><td><img class="crop" src="{data+e(r["image"])}"></td><td><pre>{e(r["text"])}</pre></td><td><pre>{e(r["predicted"]) if r["predicted"] else "（空结果）"}</pre></td><td>{"匹配" if r["exactMatch"] else "不匹配"}</td></tr>')
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>DocumentEvidence · 本轮 HierText GPU 结果</title>
<style>body{{font:16px "Segoe UI","Microsoft YaHei",sans-serif;margin:28px;color:#17243a;background:#f5f7fa}}h1{{margin:0 0 12px;font-size:28px}}p{{line-height:1.6;margin:10px 0}}.badge{{padding:12px 16px;background:#e6f4ed;border:1px solid #8ebba3}}.grid{{display:grid;grid-template-columns:44% 1fr;gap:24px;margin-top:20px}}.photo{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;background:#fff}}td,th{{padding:9px;border:1px solid #ccd5de;text-align:left}}th{{background:#e9eff5}}pre{{margin:0;white-space:pre-wrap;font:15px Consolas,monospace}}.crop{{max-width:105px;max-height:34px}}small{{line-height:1.6}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>DocumentEvidence · HierText 真实场景文字</h1>
<p class="badge"><b>2026-11-21 本轮 GPU 推理完成 · 24 行全部保留</b><br>MIGraphX GPU · Radeon PRO W7900 · PaddleOCR en-v3 · 一次编译、串行识别。</p>
<p>官方行框 → GPU 识别 → 与官方原文逐字比较。GPU/CPU 概率张量对照通过，最大绝对误差 {evaluation['maxAbsoluteReferenceError']:.8g}。</p>
<p><b>严格匹配 {evaluation['exactLines']} / 24 行 · 字符错误率 {evaluation['characterErrorRate']:.2%}（{evaluation['characterEdits']} / {evaluation['referenceCharacters']}）</b>。24 行来自同一照片；不包含文字检测或票据字段验收。</p>
<div class="grid"><section><img class="photo" src="{data}originals/417cfad1483563c3.jpg" alt="HierText 原始街景照片">
<p>原图 ID：417cfad1483563c3<br>HierText / Open Images · Long 等，Google Research</p>
<small>照片、官方标注及其裁剪：CC BY-SA 4.0。修改：按官方行框裁剪，加入本轮模型输出与对照。保留大小写、空格、错字与空结果。<br>来源：https://github.com/google-research-datasets/hiertext<br>许可：https://creativecommons.org/licenses/by-sa/4.0/</small>
<p><a href="evaluation.json">本轮原始评估</a> · <a href="recognized/batch-evidence.json">本轮批次输出</a> · <a href="cli.log">原始运行日志</a></p></section>
<section><table><thead><tr><th>行</th><th>真实裁剪</th><th>官方原文</th><th>实际输出</th><th>对照</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section></div>
<p><small>本页由真实输入与本轮原始输出生成，是证据报告；模型输出未经修改。完整选择协议、输入哈希、评分和失败行保存在评估 JSON。</small></p></html>'''
(doc/'evidence.html').write_text(page,encoding='utf-8',newline='\n')
summary={'builtAt':dt.datetime.now().astimezone().isoformat(),'inferenceStartedUtc':evaluation['startedAtUtc'],'lineCount':24,
 'exactLines':evaluation['exactLines'],'characterEdits':evaluation['characterEdits'],'referenceCharacters':evaluation['referenceCharacters'],
 'characterErrorRate':evaluation['characterErrorRate'],'maxAbsoluteReferenceError':evaluation['maxAbsoluteReferenceError'],
 'modelInstances':1,'programCompilations':1,'evaluationSha256':sha(doc/'evaluation.json'),'batchSha256':sha(doc/'recognized/batch-evidence.json'),
 'scope':'Current real GPU OCR, independent official-label scoring, all failures retained; not production acceptance.'}
(out/'document-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(summary,ensure_ascii=False))

old=out.parent/'round4'
identities=read(old/'source-binary-identities.json')
for item in identities:
    assert sha(item['path'])==item['sha256'] and Path(item['path']).stat().st_size==item['bytes']
additional=[Path('D:/AMD/ROCm/10.1.0/MIGraphX/bin')/name for name in ['migraphx.dll','migraphx_gpu.dll']]
additional.extend(Path('D:/AMD/ROCm/10.1.0/HIP/bin')/name for name in ['rocblas.dll','libhipblaslt.dll'])
additional.append(Path(read(out/'matmul-forward.json')['nativeLibrary']))
for p in additional:identities.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
(out/'binary-identities.json').write_text(json.dumps({'checkedAt':dt.datetime.now().astimezone().isoformat(),
 'applicationSourceCommit':'2f70b96267484b441fa726a3d496b8cc55d47219','allRound4IdentitiesUnchanged':True,'files':identities},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
signal=Path(read(out/'signal-native-hip-summary.json')['report']).relative_to(out).as_posix()
entries=[
 ('01-surface-visa-model.jpg','http://127.0.0.1:5086/','Current real VisA DINOv2/PatchCore GPU workspace, first original-order normal image; all 12 unreviewed.',
  ['surface-model-batch.json','surface-model-summary.json','surface-model-report/report.html','logs/surface-native-path.log']),
 ('02-signal-uci-ps1.jpg','http://127.0.0.1:8766/research/validation/round5/'+signal,'Current UCI PS1 cycle 1 actual HIP report.',[signal,'signal-comparison.json']),
 ('03-document-hiertext-gpu.jpg','http://127.0.0.1:8766/research/validation/round5/document-hiertext-native-path/evidence.html',
  'Current GPU OCR with official labels; all predictions retained in report, not a business approval UI.',
  ['document-hiertext-native-path/evidence.html','document-hiertext-native-path/evaluation.json','document-hiertext-native-path/recognized/batch-evidence.json']),
 ('04-video-nasa-original-frame.jpg','http://127.0.0.1:8766/research/validation/round5/video-gpu/analysis/report.html#frame-0',
  'Current NASA GPU report, first frozen frame at original PTS 460800 / 30 seconds; actual program-drawn boxes.',
  ['video-gpu/analysis/report.html','video-gpu/analysis/result.json','video-gpu/workflow-run.json'])]
shots=[]
for name,url,scope,evidence in entries:
    p=out/'screenshots/raw'/name
    with Image.open(p) as im:
        assert im.format=='JPEG';width,height=im.size
    shots.append({'file':'screenshots/raw/'+name,'url':url,'scope':scope,'evidence':evidence,
     'width':width,'height':height,'capturedAtFromFileMtime':dt.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(),
     'sha256':sha(p),'bytes':p.stat().st_size,'format':'JPEG','captureApi':'cua_repl Tab.getScreenshot()',
     'edited':False,'status':'VALID'})
(out/'screenshots/manifest.json').write_text(json.dumps({'captureScope':'Actual browser viewport, no desktop or terminal chrome; unedited original JPEG bytes.',
 'date':'2026-11-21','sourceCommit':'2f70b96267484b441fa726a3d496b8cc55d47219','licensing':'../THIRD_PARTY.md','files':shots},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
