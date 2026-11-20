"""Check current public-data claims and preserve prior immutable evidence."""
import datetime as dt,hashlib,json,re,subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
from PIL import Image
root=Path(__file__).resolve().parents[1];out=root/'research/validation/round4';repo=root.parents[1]
def read(f):return json.loads(Path(f).read_text(encoding='utf-8-sig'))
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
for record in (out/'commands').glob('*.json'):
    r=read(record);assert sha(out/r['log'])==r['logSha256']
for name in ['signal-uci-cpu','signal-uci-hip','video-prepare-r2','video-nasa-gpu']:
    assert read(out/'commands'/(name+'.json'))['exitCode']==0
assert read(out/'commands/surface-dinov2-patchcore-verify.json')['exitCode']==3221225477
assert read(out/'commands/video-prepare.json')['exitCode']!=0
for f in ['logs/surface-dinov2-patchcore-verify.log','document-gpu/cli.log']:
    log=(out/f).read_text(encoding='utf-8-sig');assert '0xC0000005' in log and 'ProgramCompile' in log
assert read(out/'document-attempt.json')['status']=='failed'
assert not (out/'document-gpu/evaluation.json').exists()
for r in read(out/'source-binary-identities.json'):
    assert Path(r['path']).stat().st_size==r['bytes'] and sha(r['path'])==r['sha256']

c,g=[read(out/('surface-'+b+'-batch.json')) for b in ['cpu','hip']]
source=read(out/'inputs/visa-manifest.json')
for sample,x,y,check in zip(source['samples'],c['items'],g['items'],read(out/'surface-public-evidence/mask-comparison.json'),strict=True):
    assert g['synthetic'] is False and y['measurement']['backend']=='HIP'
    folder=out/'surface-public-evidence'/sample['id']
    assert sha(folder/'original.jpg')==x['sourceHash']==y['sourceHash']==check['inputSha256']
    assert sha(folder/'cpu-mask.png')==sha(folder/'hip-mask.png')==check['cpuMaskSha256']==check['hipMaskSha256']
    assert x['defectPixels']==y['defectPixels'] and y['machineDecision']=='Defect'
assert len(g['items'])==12 and sum(not s['anomaly'] for s in source['samples'])==6

summaries=[read(out/('signal-'+b+'-summary.json')) for b in ['cpu','hip']]
sigdirs=[out/('signal-'+b)/s['id'] for b,s in zip(['cpu','hip'],summaries)]
cpu,hip=[read(d/'result.json') for d in sigdirs]
assert cpu['inputSha256']==hip['inputSha256']==sha(sigdirs[0]/'input.csv')==sha(sigdirs[1]/'input.csv')
assert cpu['configSha256']==hip['configSha256']
assert len(cpu['frames'])==len(hip['frames'])==45
assert summaries[0]['needsReview']==summaries[1]['needsReview']==1 and summaries[1]['omittedTailSamples']==112
errors=[]
for x,y in zip(cpu['frames'],hip['frames'],strict=True):
    assert x['decision']==y['decision']
    for v,w in zip(x['spectrum']['psd'],y['spectrum']['psd'],strict=True):
        assert abs(w-v)<=1e-5+1e-4*abs(v);errors.append(abs(w-v))
assert len(errors)==5805 and max(errors)==read(out/'signal-comparison.json')['maxAbs']
inputaudit=read(out/'inputs/real-input-audit.json')['results']
assert inputaudit['uci']['all6000OriginalValueStringsIdentical'] and inputaudit['visa']['all12InputsByteIdenticalToOfficialArchive']

doc=read(out/'document-history/evaluation.json');batch=read(out/'document-history/recognized/batch-evidence.json')
assert doc['exactLines']==5 and doc['lineCount']==24 and len(doc['failures'])==19
assert doc['characterEdits']==78 and doc['referenceCharacters']==137
assert len({r['pageId'] for r in doc['records']})==1
assert any(r['predicted']=='' for r in doc['records'])
for r,actual in zip(doc['records'],batch['lines'],strict=True):
    assert sha(out/'document-history/data'/r['image'])==r['imageSha256']==actual['recognition']['inputSha256']
    assert r['predicted']==actual['recognition']['text']

video=read(out/'video-gpu/workflow-run.json');result=read(out/'video-gpu/analysis/result.json')
assert video['framesProcessed']==25 and video['observations']==len(result['observations'])==109
assert video['unreviewedEventPredictions']==len(result['events'])==12
assert all(ev['reviewStatus']=='NeedsReview' for ev in result['events'])
assert video['eventQualityMeasured'] is False and video['metrics'] is None
assert 'hipErrorInvalidKernelFile' in (out/'video-gpu/infer.stderr.txt').read_text(encoding='utf-8-sig')
prepared=read(out/'video-prepared/media/frames.json');assert len(prepared['frames'])==25
assert [f['pts'] for f in prepared['frames']]==[460800+6144*i for i in range(25)]
for frame in prepared['frames']:assert sha(out/'video-prepared/media'/frame['image'])==frame['sha256']
assert sha(out/'video-prepared/original-media.mp4')==video['sourceSha256']

screens=read(out/'screenshots/manifest.json')['files'];assert len(screens)==5
for shot in screens:
    f=out/shot['file'];assert sha(f)==shot['sha256'] and shot['edited'] is False and shot['status']=='VALID'
    with Image.open(f) as im:assert im.size==(shot['width'],shot['height']) and im.format=='JPEG'
    for ev in shot['evidence']:assert (out/ev).is_file()

class Links(HTMLParser):
    def __init__(self):super().__init__();self.paths=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ['href','src']:self.paths.append(value)
pages=[root/'03-正文预览.html',out/'surface-public-evidence/report.html',out/'document-history/evidence.html',
       out/'video-gpu/analysis/report.html',*[d/'report.html' for d in sigdirs]]
for page in pages:
    parser=Links();parser.feed(page.read_text(encoding='utf-8-sig'))
    for link in parser.paths:
        parsed=urlsplit(link)
        if not parsed.scheme and parsed.path:assert (page.parent/unquote(parsed.path)).is_file(),(page,link)
article=(root/'03-正文.md').read_text(encoding='utf-8')
assert len(re.findall(r'^## ',article,re.M))==7
assert len(re.findall(r'(?<!!)\[[^\]]+\]\([^)]+\)',article))==3
assert len(re.findall(r'!\[[^\]]+\]\(research/validation/round4/',article))==4
for image in ['01-cover-v2.png','02-api-architecture-v3.png','03-surfacelab-v3.png','04-signal-diagnostics-v3.png','05-document-evidence-v3.png','06-video-event-search-v3.png']:
    assert '(assets/'+image+')' in article
for token in ['VisA','UCI','HierText','NASA','历史','2026-11-18','Compile 失败','CC BY-SA 4.0']:
    assert token in article
docs=[root/'03-正文.md',root/'05-上手与验证.md',root/'research/真实开源数据案例与截图.md',out/'README.md',out/'THIRD_PARTY.md']
for path in docs:
    content=path.read_text(encoding='utf-8');assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)',content),path
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',content):
        parsed=urlsplit(link)
        if not parsed.scheme and parsed.path:assert (path.parent/unquote(parsed.path)).exists(),(path,link)

historical={}
for roundname,commit in [('round2','a5aeb7d'),('round3','a4f73e4')]:
    manifest=read(root/'research/validation'/roundname/'manifest.json')
    for item in manifest['files']:
        path=root/item['path']
        if item['path'].startswith('research/validation/'+roundname+'/'):
            assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],path
        else:
            raw=subprocess.check_output(['git','show',commit+':'+path.relative_to(repo).as_posix()],cwd=repo)
            assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],path
    historical[roundname]=len(manifest['files'])
summary={'checkedAt':dt.datetime.now().astimezone().isoformat(),'publicDataCaseScreenshots':4,'rawBrowserScreenshots':5,
 'surfaceRealImages':12,'signalPsdValues':len(errors),'hiertextHistoricalLinesRescored':24,'videoRealFrames':25,
 'videoDetections':109,'videoUnreviewedEvents':12,'nativeCompileFailuresRetained':2,'historicalHashesVerified':historical,
 'readerPathsPortable':True,'originalSixConceptImagesRetained':True,'newBuildOr264TestsRerun':False,'productionAcceptance':False}
(out/'final-checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(summary,ensure_ascii=False))
