"""Audit and present historical real HierText predictions; never perform/fake inference."""
import argparse, base64, datetime as dt, hashlib, html, importlib.util, json, shutil, sys
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--assets',required=True);p.add_argument('--history',required=True)
a=p.parse_args()
article=Path(__file__).resolve().parents[1];out=article/'research/validation/round4'
source=article.parent/'.tools/apps-round3-source'
assets,history=Path(a.assets),Path(a.history)
data=assets/'document-evidence/hiertext-test-small-v1';model=assets/'document-evidence/en-ppocrv3-ctc-v2/model.json'
def read(f):return json.loads(Path(f).read_text(encoding='utf-8-sig'))
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def save(f,v):Path(f).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
sys.path.insert(0,str(source/'eng'))
spec=importlib.util.spec_from_file_location('hiertext',source/'eng/document-evaluate-hiertext.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
protocol,manifest,files,distance=m.validate(model,data/'lines.json')
result=read(history/'evaluation.json');batch=read(history/'recognized/batch-evidence.json')
assert batch['manifestSha256']==sha(data/'lines.json') and batch['modelInstances']==1 and batch['recognizer']['programCompilations']==1
assert result['manifestSha256']==batch['manifestSha256'] and result['modelManifestSha256']==sha(model)
assert len(result['records'])==len(batch['lines'])==len(protocol['samples'])==24
for official,line,actual,record in zip(protocol['samples'],manifest['lines'],batch['lines'],result['records'],strict=True):
    recognition=actual['recognition'];ref=recognition['reference']
    assert actual['id']==official['id']==record['id']
    assert recognition['inputSha256']==official['imageSha256']==record['imageSha256']
    assert recognition['modelManifestSha256']==sha(model) and ref['referenceSha256']==line['referenceSha256'] and ref['passed'] is True
    assert record['text']==official['text'] and record['predicted']==recognition['text']
    assert record['editDistance']==distance(official['text'],recognition['text']) and record['exactMatch']==(official['text']==recognition['text'])
assert sum(r['exactMatch'] for r in result['records'])==result['exactLines']==5
assert sum(r['editDistance'] for r in result['records'])==result['characterEdits']==78
assert sum(len(r['text']) for r in result['records'])==result['referenceCharacters']==137
assert len({r['pageId'] for r in result['records']})==1
snapshot=out/'document-history';snapshot.mkdir()
for name in ['evaluation.json','before-scoring.json','cli.log']:
    shutil.copyfile(history/name,snapshot/name)
shutil.copytree(history/'recognized',snapshot/'recognized')
localdata=snapshot/'data';localdata.mkdir()
for name in ['protocol.json','selection-plan.json','lines.json','preparation.json','upstream-LICENSE','upstream-README.md']:
    shutil.copyfile(data/name,localdata/name)
shutil.copytree(data/'originals',localdata/'originals');shutil.copytree(data/'crops',localdata/'crops')
audit={'auditedAt':dt.datetime.now().astimezone().isoformat(),'historicalInferenceStartedUtc':result['startedAtUtc'],
 'mode':'Independent official annotation re-import, crop/model hash audit and historical raw prediction rescoring; no new inference or probability recomputation.',
 'officialDataFilesChecked':len(files),'sourceSnapshotHashes':{str(f):h for f,h in files.items()},
 'historicalEvaluationSha256':sha(history/'evaluation.json'),'historicalBatchSha256':sha(history/'recognized/batch-evidence.json'),
 'lineCount':24,'scoredOriginalImages':1,'exactLines':5,'referenceCharacters':137,'characterEdits':78,'characterErrorRate':78/137,
 'historicalReportedProbabilityValues':sum(r['reference']['values'] for r in result['records']),
 'historicalReportedMaxAbs':result['maxAbsoluteReferenceError'],
 'currentGpuAttempt':'failed in native Compile, 0xC0000005; see ../document-gpu/cli.log',
 'passed':True}
save(snapshot/'audit.json',audit)
e=lambda s:html.escape(str(s),quote=True)
rows=[]
for i,r in enumerate(result['records']):
    rows.append(f'<tr><td>{i+1:02d}</td><td><img class="crop" src="data/{e(r["image"])}" alt="原图行裁剪"></td><td><pre>{e(r["text"])}</pre></td><td><pre>{e(r["predicted"]) if r["predicted"] else "（空结果）"}</pre></td><td>{"匹配" if r["exactMatch"] else "不匹配"}</td></tr>')
content=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>DocumentEvidence · HierText 真实数据证据</title>
<style>body{{font:16px "Segoe UI","Microsoft YaHei",sans-serif;margin:28px;color:#17243a;background:#f5f7fa}}h1{{margin:0 0 12px;font-size:28px}}p{{line-height:1.6;margin:10px 0}}.badge{{padding:12px 16px;background:#fff2d9;border:1px solid #d9ac53}}.grid{{display:grid;grid-template-columns:44% 1fr;gap:24px;margin-top:20px}}.photo{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;background:#fff}}td,th{{padding:9px;border:1px solid #ccd5de;text-align:left}}th{{background:#e9eff5}}pre{{margin:0;white-space:pre-wrap;font:15px Consolas,monospace}}.crop{{max-width:105px;max-height:34px;image-rendering:auto}}code{{overflow-wrap:anywhere}}small{{line-height:1.6}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>DocumentEvidence · HierText 真实场景文字</h1>
<p class="badge"><b>历史 GPU 执行：2026-11-18 · 本轮核验与截图：2026-11-21</b><br>本轮 GPU OCR 在 Compile 阶段失败；以下展示历史真实输出，24 行全部保留。</p>
<p>MIGraphX GPU · Radeon PRO W7900 · PaddleOCR en-v3 · 官方行框 → 识别 → 与官方原文逐字比较</p>
<p><b>严格匹配 5 / 24 行 · 字符错误率 56.93%（78 / 137）</b>。24 行来自同一张照片；使用官方行框，不包含文字检测或票据字段验收。</p>
<div class="grid"><section><img class="photo" src="data/originals/417cfad1483563c3.jpg" alt="HierText 原始街景照片 417cfad1483563c3">
<p>原图 ID：417cfad1483563c3<br>HierText / Open Images · Long 等，Google Research</p>
<small>照片、官方标注及其裁剪：CC BY-SA 4.0。修改：按官方行框裁剪，加入模型输出和对照。未更改标注、空格、大小写或失败结果。<br>来源：https://github.com/google-research-datasets/hiertext<br>许可：https://creativecommons.org/licenses/by-sa/4.0/</small>
<p><a href="evaluation.json">原始评估 JSON</a> · <a href="recognized/batch-evidence.json">历史批次输出</a> · <a href="audit.json">本轮核验记录</a></p></section>
<section><table><thead><tr><th>行</th><th>真实裁剪</th><th>官方原文</th><th>实际输出</th><th>对照</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section></div>
<p><small>这是读取真实数据与既有执行结果生成的证据报告，不是文档业务审批界面。本轮只重新核验和排版；历史记录中的 GPU/CPU 概率比较未重新计算。</small></p></html>'''
(snapshot/'evidence.html').write_text(content,encoding='utf-8',newline='\n')
print(json.dumps({k:audit[k] for k in ['passed','lineCount','exactLines','characterEdits','referenceCharacters','officialDataFilesChecked']},ensure_ascii=False))
