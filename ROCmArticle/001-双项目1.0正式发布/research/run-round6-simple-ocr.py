"""Use two preselected large printed lines from a real public sign, then run C# GPU OCR."""
import argparse,datetime as dt,gzip,hashlib,html,json,math,os,subprocess
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','run','report']);a=p.parse_args()
root=Path(__file__).resolve().parents[1];out=root/'research/validation/round6';assets=Path('E:/GitSpace/ROCm-CSharp-Projects/assets')
data=assets/'document-evidence/hiertext-test-small-v1';model=assets/'document-evidence/en-ppocrv3-ctc-v2/model.json'
source=root.parent/'.tools/apps-round3-source';app=root.parent/'.tools/apps-round3-build/bin/Documents.App/Release/net10.0/Documents.App.dll'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):
    Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
if a.stage=='prepare':
    out.mkdir(exist_ok=False)
    original=data/'originals/b533107ff30932da.jpg';annotation=data/'test.jsonl.gz'
    assert sha(original)=='abf91176e175122c44f913e7109d017b819877df53194d37183527410f877d2c'
    assert sha(annotation)=='8a8f6cb6dd706b457b822634e9f19b7f51cc9813729d57401a3bb6ea45abd438'
    labels=json.loads(gzip.decompress(annotation.read_bytes()));page=next(p for p in labels['annotations'] if p['image_id']=='b533107ff30932da')
    chosen=[(2,0,'APPLE'),(2,1,'SODA')];samples=[]
    with Image.open(original) as photo:
        photo=photo.convert('RGB')
        # This actual sign crop is only for display; OCR uses each official line rectangle below.
        display_bounds=[1210,382,1375,510]
        (out/'inputs').mkdir(exist_ok=True);photo.crop(display_bounds).save(out/'inputs/apple-soda-sign.png')
        for pi,li,text in chosen:
            line=page['paragraphs'][pi]['lines'][li];assert line['text']==text and line['legible'] and not line['handwritten']
            v=line['vertices'];bounds=[math.floor(min(p[0] for p in v)),math.floor(min(p[1] for p in v)),math.ceil(max(p[0] for p in v)),math.ceil(max(p[1] for p in v))]
            ident=f'b533107ff30932da-p{pi:03d}-l{li:03d}';path=out/'inputs'/(ident+'.bmp')
            photo.crop(bounds).save(path)
            samples.append({'id':ident,'paragraphIndex':pi,'lineIndex':li,'text':text,'vertices':v,'bounds':bounds,'image':'inputs/'+path.name,'imageSha256':sha(path)})
    protocol={'declaredAt':dt.datetime.now().astimezone().isoformat(),'selection':'User requested a simpler illustration. Preselected APPLE and SODA from the second real HierText photo by visual legibility, before this round inference; demonstration, not random evaluation.',
      'dataset':'HierText official test image b533107ff30932da','license':'CC BY-SA 4.0','revision':'70b6620b2b112597d8219e11eee9773a1403827c',
      'sourceUrl':'https://github.com/google-research-datasets/hiertext','originalImageSha256':sha(original),'officialAnnotationSha256':sha(annotation),
      'originalImage':'../round4/document-history/data/originals/b533107ff30932da.jpg','displayBounds':display_bounds,'displaySha256':sha(out/'inputs/apple-soda-sign.png'),
      'cropRule':'Axis-aligned floor/ceil bounds of official line vertices; RGB BMP; no replacement text, rotation, whitening, generative editing or contrast changes.',
      'modelManifestSha256':sha(model),'graphSha256':read(model)['sha256'],'dictionarySha256':read(model)['dictionarySha256'],
      'applicationFiles':{str(f):sha(f) for f in [app,app.parent/'Documents.Core.dll']},'samples':samples,
      'scope':'Two easy selected real sign lines for illustration only. Official line geometry supplied; no detector, document field evaluation or accuracy benchmark. No new CPU tensor comparison.'}
    save(out/'protocol.json',protocol)
    save(out/'lines.json',{'schemaVersion':1,'source':'HierText / Open Images; Long et al., Google Research; CC BY-SA 4.0',
      'scope':protocol['scope'],'lines':[{k:s[k] for k in ['id','image','imageSha256']} for s in samples]})
    print('Frozen two official lines before OCR:',[s['text'] for s in samples],flush=True)
elif a.stage=='run':
    protocol=read(out/'protocol.json');assert sha(model)==protocol['modelManifestSha256']
    hip=Path('D:/AMD/ROCm/10.1.0/HIP');native=Path('D:/AMD/ROCm/10.1.0/MIGraphX/bin/migraphx_c.dll')
    env=dict(os.environ,HIP_PATH=str(hip),ROCM_PATH=str(hip),HIP_DEVICE_LIB_PATH=str(hip/'lib/llvm/amdgcn/bitcode'),
      ROCBLAS_TENSILE_LIBPATH=str(hip/'bin/rocblas/library'),HIPBLASLT_TENSILE_LIBPATH=str(hip/'bin/hipblaslt/library/gfx1100'),MIGRAPHX_NATIVE_PATH=str(native))
    env['PATH']=str(native.parent)+';'+str(hip/'bin')+';'+str(hip/'lib/llvm/bin')+';'+env['PATH']
    # Both input manifest and output use the temporary alias because the CLI rejects any Git ancestor.
    command=['dotnet',str(app),'recognize-lines',str(model),'R:/lines.json','R:/recognized']
    start=dt.datetime.now().astimezone().isoformat();frozen={str(p):sha(p) for p in [out/'protocol.json',out/'lines.json',model,app,app.parent/'Documents.Core.dll']}
    with (out/'gpu.log').open('xb') as log:
        code=subprocess.run(command,env=env,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=300).returncode
    save(out/'command.json',{'started':start,'finished':dt.datetime.now().astimezone().isoformat(),'command':command,'exitCode':code,
      'nativeSha256':sha(native),'logSha256':sha(out/'gpu.log'),'frozenFiles':frozen,'environment':{k:env[k] for k in ['HIP_PATH','ROCBLAS_TENSILE_LIBPATH','HIPBLASLT_TENSILE_LIBPATH']}})
    assert code==0
    for p,h in frozen.items():assert sha(p)==h
    batch=read(out/'recognized/batch-evidence.json');assert len(batch['lines'])==2 and batch['modelInstances']==batch['recognizer']['programCompilations']==1
    records=[]
    for sample,line in zip(protocol['samples'],batch['lines'],strict=True):
        rec=line['recognition'];assert line['id']==sample['id'] and rec['inputSha256']==sample['imageSha256']
        assert rec['modelManifestSha256']==protocol['modelManifestSha256'] and rec['backend'].startswith('MIGraphX GPU')
        records.append({'id':sample['id'],'expected':sample['text'],'actual':rec['text'],'exactMatch':sample['text']==rec['text'],'confidence':rec['confidence']})
    save(out/'summary.json',{'scope':protocol['scope'],'lines':2,'exactLines':sum(r['exactMatch'] for r in records),'records':records,
      'backend':batch['recognizer'],'inferenceStarted':start,'allPredictionsRetained':True})
    print(json.dumps(records,ensure_ascii=False),flush=True)
else:
    s=read(out/'summary.json');e=lambda v:html.escape(str(v),quote=True)
    rows=''.join(f'<tr><td>{e(r["expected"])}</td><td>{e(r["actual"]) or "（空结果）"}</td><td>{"一致" if r["exactMatch"] else "不一致"}</td></tr>' for r in s['records'])
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>DocumentEvidence · 简单招牌 OCR 演示</title>
<style>*{{box-sizing:border-box}}body{{font:18px "Segoe UI","Microsoft YaHei",sans-serif;background:#f3f6fa;color:#172941;margin:0;padding:34px}}main{{max-width:1130px;margin:auto}}h1{{font-size:30px;margin:0 0 12px}}.meta{{font-size:16px;color:#51647a;line-height:1.7;margin-bottom:26px}}.grid{{display:grid;grid-template-columns:42% 1fr;gap:26px}}section{{background:white;border:1px solid #d5dfe9;border-radius:14px;padding:26px}}h2{{font-size:19px;margin:0 0 22px}}.photo{{display:block;width:330px;max-width:100%;height:auto;margin:auto;image-rendering:auto}}table{{border-collapse:collapse;width:100%;font-size:24px}}th{{font-size:16px;background:#eef4f8}}td,th{{text-align:left;padding:18px 12px;border-bottom:1px solid #dce5ec}}.note{{font-size:15px;line-height:1.8;color:#506278;margin-top:24px}}.success{{color:#237252;font-weight:600}}footer{{font-size:13px;line-height:1.7;color:#536479;margin-top:22px}}a{{color:#376399}}</style>
<main><h1>DocumentEvidence · 读出招牌上的两行文字</h1><p class="meta">真实公开照片裁剪 → 指定两行区域 → MIGraphX GPU 识别<br>Radeon PRO W7900 · PaddleOCR en-v3 · 2026-11-21 本次实际运行</p>
<div class="grid"><section><h2>真实图片</h2><img class="photo" src="inputs/apple-soda-sign.png" alt="白底招牌上的 APPLE 和 SODA 两行文字"><p class="note">从公开照片裁剪招牌局部，保留原有像素。两行位置采用数据集官方标注。</p></section>
<section><h2>实际识别结果</h2><table><tr><th>图片原文</th><th>GPU 输出</th><th>对照</th></tr>{rows}</table><p class="note success">{s['exactLines']} / 2 行与官方原文一致</p><p class="note">这里只演示指定文字行识别。文字检测、票据字段核验及整体准确率需要另行验证。</p></section></div>
<footer>图片：HierText / Open Images，Long 等，Google Research · CC BY-SA 4.0。修改：裁剪招牌与文字行，加入实际输出展示。<br>来源：https://github.com/google-research-datasets/hiertext · 许可：https://creativecommons.org/licenses/by-sa/4.0/<br><a href="../round4/document-history/data/originals/b533107ff30932da.jpg">完整原照片</a> · <a href="protocol.json">取图与官方标注记录</a> · <a href="recognized/batch-evidence.json">原始 GPU 输出</a></footer></main></html>'''
    (out/'evidence.html').write_text(page,encoding='utf-8',newline='\n')
    print('Built simple real sign OCR evidence report.')
