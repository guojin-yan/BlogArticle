"""Bind public input bytes, complete actual outputs and unedited browser captures."""
import argparse,csv,datetime as dt,hashlib,html,json,shutil,tarfile,zipfile
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--assets',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];out=root/'research/validation/round4';assets=Path(a.assets)
def sha(f):
    with Path(f).open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
def read(f):return json.loads(Path(f).read_text(encoding='utf-8-sig'))
def save(f,v):
    f=Path(f);f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
inputs=out/'inputs';inputs.mkdir(exist_ok=True)
signal=assets/'signals/uci447-ps1-cycle1-v2';sm=read(signal/'source-manifest.json')
archive=assets/'downloads/uci447-hydraulic.zip';assert sha(archive)==sm['archiveSha256']
with zipfile.ZipFile(archive) as z:
    with z.open('PS1.txt') as s:raw=s.readline()
    values=raw.decode('ascii').strip().split('\t')
    assert hashlib.sha256(raw).hexdigest()==sm['sourceRowSha256']
with (signal/'signal.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
assert len(rows)==len(values)==6000 and [r['value'] for r in rows]==values
assert all(float(r['time_s'])==i/100 for i,r in enumerate(rows))
for name in ['source-manifest.json','config.json','ATTRIBUTION.txt','official-metadata.json','official-source.html']:
    target=inputs/'uci';target.mkdir(exist_ok=True);shutil.copyfile(signal/name,target/name)
audit={'uci':{'archiveSha256':sm['archiveSha256'],'sourceRowSha256':sm['sourceRowSha256'],'all6000OriginalValueStringsIdentical':True,
 'samplingHz':100,'unit':'bar','inputSha256':sha(signal/'signal.csv')}}
visa=assets/'visa/pcb1-smoke';vm=read(visa/'manifest.json')
va=assets/'downloads/VisA_20220922.tar';assert sha(va)==vm['archiveSha256']
wanted={s['image']:sha(visa/s['image']) for s in vm['samples']};found={}
with tarfile.open(va,'r|') as tar:
    for member in tar:
        name=member.name.removeprefix('./')
        if name in wanted:
            found[name]=hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest()
assert found==wanted and len(found)==12
shutil.copyfile(visa/'manifest.json',inputs/'visa-manifest.json')
audit['visa']={'archiveSha256':vm['archiveSha256'],'all12InputsByteIdenticalToOfficialArchive':True,'samples':wanted}
portable=out/'surface-public-evidence';portable.mkdir(exist_ok=True)
c,g=[read(out/('surface-'+b+'-batch.json')) for b in ['cpu','hip']]
e=lambda s:html.escape(str(s),quote=True)
table=[];maskchecks=[]
for sample,x,y in zip(vm['samples'],c['items'],g['items'],strict=True):
    folder=portable/sample['id'];folder.mkdir(exist_ok=True)
    original=visa/sample['image'];assert sha(original)==x['sourceHash']==y['sourceHash']
    shutil.copyfile(original,folder/'original.jpg')
    masks=[]
    for backend,item in [('cpu',x),('hip',y)]:
        mask=out/('surface-'+backend+'-report/evidence')/item['id']/'mask.png'
        shutil.copyfile(mask,folder/(backend+'-mask.png'));masks.append(sha(mask))
    assert masks[0]==masks[1] and x['defectPixels']==y['defectPixels']
    maskchecks.append({'id':sample['id'],'inputSha256':sha(original),'cpuMaskSha256':masks[0],'hipMaskSha256':masks[1],'officialAnomaly':sample['anomaly'],
      'machineDecision':y['machineDecision'],'defectPixels':y['defectPixels']})
    sid=e(sample['id'])
    table.append(f'<tr><td>{sid}</td><td>{"异常" if sample["anomaly"] else "正常"}</td><td><img width="180" src="{sid}/original.jpg"></td><td>{e(y["machineDecision"])}</td><td>{y["defectPixels"]}</td><td><a href="{sid}/hip-mask.png">HIP</a> / <a href="{sid}/cpu-mask.png">CPU</a></td></tr>')
save(portable/'mask-comparison.json',maskchecks)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>SurfaceLab · VisA 实际输入与规则结果</title>
<style>body{{font:16px system-ui;margin:32px;color:#18253a}}p{{line-height:1.6}}table{{border-collapse:collapse}}td,th{{padding:10px;border:1px solid #ccd4de}}img{{display:block}}</style>
<h1>SurfaceLab · VisA pcb1 真实数据</h1><p>2026-11-21 · 12 张原始 JPG · 6 正常 / 6 异常 · 固定 HIP 灰度规则，与 CPU 掩码逐字节一致。</p>
<p>这是实际导入与计算结果。默认均匀表面规则把全部 12 图判为缺陷（包括 6 张正常图），不适合据此声称 PCB 检测精度；未调阈值。DINOv2/PatchCore 本轮 Compile 失败，截图展示 HIP 规则路径。</p>
<p>数据：VisA，Amazon Science / Yang Zou 等，CC BY 4.0。原图字节未修改；掩码来自实际程序，未手工绘制。<br>来源：https://github.com/amazon-science/spot-diff · 许可：https://creativecommons.org/licenses/by/4.0/</p>
<p><a href="../surface-hip-batch.json">完整 HIP 批次</a> · <a href="../surface-cpu-batch.json">完整 CPU 批次</a> · <a href="mask-comparison.json">输入及掩码逐图哈希</a></p>
<table><tr><th>样本</th><th>官方标签</th><th>真实原图</th><th>机器结果</th><th>规则像素数</th><th>实际掩码</th></tr>{''.join(table)}</table></html>'''
(portable/'report.html').write_text(page,encoding='utf-8',newline='\n')
audit['surfaceMasks']={'all12ByteIdentical':True,'normalImagesFlaggedDefect':sum(not s['anomaly'] for s in vm['samples']),
 'recipeUnchanged':read(out/'surface-recipe.json')}
nasa=assets/'video-event-search/nasa-walkout-v1'
for name in ['downloads.json','collection.json','metadata.json','nasa-media-guidelines.html']:
    target=inputs/'nasa';target.mkdir(exist_ok=True);shutil.copyfile(nasa/name,target/name)
assert sha(nasa/'walkout-preview.mp4')==read(out/'video-protocol.json')['sourceSha256']
audit['nasa']={'sourceSha256':sha(nasa/'walkout-preview.mp4'),'intervalOriginalFrames':[900,1200],
 'selection':'Fixed before inference from original 30s preview; includes all 25 samples, no prediction-based filtering.'}
audit['hiertext']=read(out/'document-history/audit.json')
save(inputs/'real-input-audit.json',{'checkedAt':dt.datetime.now().astimezone().isoformat(),'scope':'Public archive byte identity and official annotations; no publisher digital signature or business acceptance implied.','results':audit})
signalSummary=read(out/'signal-hip-summary.json');signalReport=Path(signalSummary['report']).relative_to(out).as_posix()
shots=[
 ('01-surface-visa-hip.jpg','http://127.0.0.1:5086/','SurfaceLab real VisA input, HIP rule; first official normal image, false positive retained',['surface-hip-batch.json','surface-public-evidence/report.html','surface-comparison.json']),
 ('02-signal-uci-ps1.jpg','http://127.0.0.1:8766/research/validation/round4/'+signalReport,'UCI PS1 first real pressure cycle, current HIP run',[signalReport,'signal-comparison.json']),
 ('03-document-hiertext-history.jpg','http://127.0.0.1:8766/research/validation/round4/document-history/evidence.html','Historical 2026-11-18 actual GPU outputs; 2026-11-21 official-label audit and screenshot; current Compile failed',['document-history/evidence.html','document-history/evaluation.json','document-history/audit.json','document-gpu/cli.log']),
 ('04-video-nasa-original-frame.jpg','http://127.0.0.1:8766/research/validation/round4/video-gpu/analysis/report.html#frame-0','Original NASA 30s frame with boxes drawn by actual application from current predictions',['video-gpu/analysis/report.html','video-gpu/analysis/result.json']),
 ('05-video-nasa-timeline.jpg','http://127.0.0.1:8766/research/validation/round4/video-gpu/analysis/report.html','Actual unreviewed candidate timeline from same current run',['video-gpu/workflow-run.json','video-gpu/analysis/result.json'])]
records=[]
for name,url,scope,evidence in shots:
    file=out/'screenshots/raw'/name
    with Image.open(file) as im:width,height=im.size;assert im.format=='JPEG'
    records.append({'file':'screenshots/raw/'+name,'url':url,'scope':scope,'evidence':evidence,'width':width,'height':height,
      'capturedAtFromFileMtime':dt.datetime.fromtimestamp(file.stat().st_mtime).astimezone().isoformat(),'sha256':sha(file),'bytes':file.stat().st_size,
      'format':'JPEG','captureApi':'cua_repl Tab.getScreenshot()','edited':False,'status':'VALID'})
save(out/'screenshots/manifest.json',{'captureScope':'Actual browser viewport; no desktop/window chrome or terminal screenshot; raw JPEG unedited.',
 'date':'2026-11-21','sourceCommit':'2f70b96267484b441fa726a3d496b8cc55d47219','licensing':'../THIRD_PARTY.md','files':records})
print('Verified real archive inputs, 12 mask pairs, 24 official OCR lines and five raw screenshots.')
