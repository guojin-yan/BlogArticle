"""Independently audit actual outputs, official labels, old bytes and reader links."""
import datetime as dt,hashlib,importlib.util,json,re,subprocess,sys,zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
from PIL import Image
root=Path(__file__).resolve().parents[1];repo=root.parents[1];out=root/'research/validation/round5';old=root/'research/validation/round4'
assets=Path('E:/GitSpace/ROCm-CSharp-Projects/assets');snapshot=root.parent/'.tools/apps-round3-source'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
for name in ['native-matmul-base','native-backslash-repeat','native-forward-rocblas','surface-native-path','hiertext-native-path']:
    assert read(out/'commands'/(name+'.json'))['exitCode']==0,name
for name in ['native-forward-blas','native-forward-hipblaslt','native-mixed-hipblaslt']:
    c=read(out/'commands'/(name+'.json'));assert c['exitCode']==1
    assert 'access violation reading 0x0000000000000080' in (out/c['log']).read_text(encoding='utf-8-sig')
for command in (out/'commands').glob('*.json'):
    c=read(command);log=out/'logs'/(command.stem+'.log');assert sha(log)==c['logSha256'],command
for name in ['matmul-forward','matmul-backslash']:
    c=read(out/(name+'.json'));assert c['outputElements']==4096
    for key in ['hostError','deviceError','rawHostError','rawDeviceError','finalHostError','finalDeviceError']:
        assert c[key]['passed'] is True and c[key]['failedElements']==c[key]['nonFiniteElements']==0
        assert c[key]['maxAbs']==0
    assert sha(c['nativeLibrary'])=='8e4ac30ebd51808ba0210d1a9292221d74041b1edb7fa576fa9d22909bb18aab'
    assert read(out/'commands'/(name+'.json'))['exitCode']==0

inputs=read(old/'inputs/real-input-audit.json')['results'];manifest=read(assets/'visa/pcb1-smoke/manifest.json')
assert sha(assets/'visa/pcb1-smoke/manifest.json')==sha(old/'inputs/visa-manifest.json')
batch=read(out/'surface-model-batch.json');summary=read(out/'surface-model-summary.json')
assert batch==read(out/'surface-model-report/result.json') and len(batch['items'])==12 and not batch['synthetic']
assert batch['backend']=='MigraphX' and batch['recipe']['modelFingerprint']=='c084320331df667f77dcb1228e25bd0a56246fc3a7353003d8c42cf2d37cbdf5'
confusion={'normalPass':0,'normalDefect':0,'anomalyDefect':0,'anomalyPass':0}
for s,i,c in zip(manifest['samples'],batch['items'],summary['checks'],strict=True):
    assert sha(assets/'visa/pcb1-smoke'/s['image'])==i['sourceHash']==inputs['visa']['samples'][s['image']]==c['sourceSha256']
    assert i['status']=='Completed' and i['finalDecision']=='NeedsReview' and i['reviews']==[]
    assert i['measurement']['backend'].startswith('MIGraphX GPU')
    a=i['anomaly'];assert a['modelSha256']=='885e22beaeecf14fdda2576bdd2ac0d5a03dd84290964c00e43367e5d51839c7'
    assert a['imageThreshold']==0.6117777228355408 and a['pixelThreshold']==0.4964463412761688
    assert i['machineDecision']==('Defect' if a['score']>a['imageThreshold'] else 'Pass')
    confusion[('anomaly' if s['anomaly'] else 'normal')+i['machineDecision']]+=1
assert confusion=={'normalPass':6,'normalDefect':0,'anomalyDefect':3,'anomalyPass':3}
assert len(list((out/'surface-model-report/evidence').rglob('*.png')))==48
with zipfile.ZipFile(out/'surface-model.zip') as z:
    assert z.testzip() is None
    for name in z.namelist():assert z.read(name)==(out/'surface-model-report'/name).read_bytes()
verify=json.loads((out/'logs/surface-native-path.log').read_text(encoding='utf-8-sig').split('\n',1)[1])
assert verify['passed'] and verify['pixels']==153664 and verify['maxAbsoluteError']==9.149313e-6

sigdirs=[]
for b in ['cpu','hip']:
    s=read(out/('signal-native-'+b+'-summary.json'));d=out/('signal-native-'+b)/s['id'];sigdirs.append(d)
    assert sha(d/'input.csv')==inputs['uci']['inputSha256'] and s['frames']==45 and s['needsReview']==1 and s['omittedTailSamples']==112
cpu,gpu=[read(d/'result.json') for d in sigdirs];errors=[]
assert cpu['configSha256']==gpu['configSha256'] and cpu['inputSha256']==gpu['inputSha256']
for x,y in zip(cpu['frames'],gpu['frames'],strict=True):
    assert x['decision']==y['decision']
    for v,w in zip(x['spectrum']['psd'],y['spectrum']['psd'],strict=True):
        assert abs(w-v)<=1e-5+1e-4*abs(v);errors.append(abs(w-v))
assert len(errors)==5805 and max(errors)==read(out/'signal-comparison.json')['maxAbs']
assert read(out/'commands/signal-uci-hip.json')['exitCode']==1
assert 'SIGNAL_GPU_ARCH' in (out/'logs/signal-uci-hip.log').read_text()

evaluator=snapshot/'eng/document-evaluate-hiertext.py';sys.path.insert(0,str(evaluator.parent))
spec=importlib.util.spec_from_file_location('hiertext_audit',evaluator);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
protocol,lines,files,distance=module.validate(assets/'document-evidence/en-ppocrv3-ctc-v2/model.json',assets/'document-evidence/hiertext-test-small-v1/lines.json')
doc=read(out/'document-hiertext-native-path/evaluation.json');db=read(out/'document-hiertext-native-path/recognized/batch-evidence.json')
assert doc['lineCount']==len(doc['records'])==len(db['lines'])==24 and doc['exactLines']==5 and len(doc['failures'])==19
assert db['modelInstances']==db['recognizer']['programCompilations']==1 and db['recognizer']['backend'].startswith('MIGraphX GPU')
for official,record,actual in zip(protocol['samples'],doc['records'],db['lines'],strict=True):
    assert record['id']==actual['id']==official['id'] and record['text']==official['text']
    assert record['predicted']==actual['recognition']['text'] and record['editDistance']==distance(official['text'],record['predicted'])
    assert record['exactMatch']==(record['text']==record['predicted']) and record['reference']['passed'] is True
    assert record['imageSha256']==sha(old/'document-history/data'/record['image'])
assert sum(r['reference']['values'] for r in doc['records'])==93120
assert sum(r['editDistance'] for r in doc['records'])==doc['characterEdits']==78
assert sum(len(r['text']) for r in doc['records'])==doc['referenceCharacters']==137
assert len({r['pageId'] for r in doc['records']})==1 and any(r['predicted']=='' for r in doc['records'])
assert doc['maxAbsoluteReferenceError']==max(r['reference']['maxAbsoluteError'] for r in doc['records'])==1.5556812e-5
for p,h in doc['frozenFiles'].items():assert sha(p)==h

video=read(out/'video-gpu/workflow-run.json');result=read(out/'video-gpu/analysis/result.json')
assert video['status']=='completed-awaiting-independent-human-labels' and result['status']=='completed'
assert video['framesProcessed']==25 and len(result['observations'])==video['observations']==109
assert len(result['events'])==video['unreviewedEventPredictions']==12 and video['eventQualityMeasured'] is False and video['metrics'] is None
assert video['preparedWorkflowSha256']==sha(old/'video-prepared/workflow.json')
for ev in result['events']:assert ev['reviewStatus']=='NeedsReview'
for p in (out/'video-gpu/analysis/frames').glob('*'):assert sha(p)==sha(old/'video-gpu/analysis/frames'/p.name)
assert 'hipErrorInvalidKernelFile' in (out/'video-gpu/infer.stderr.txt').read_text(encoding='utf-8-sig')
for i in read(old/'source-binary-identities.json'):assert sha(i['path'])==i['sha256']
for i in read(out/'binary-identities.json')['files']:assert sha(i['path'])==i['sha256']

shots=read(out/'screenshots/manifest.json')['files'];assert len(shots)==4
for s in shots:
    p=out/s['file'];assert sha(p)==s['sha256'] and s['edited'] is False
    with Image.open(p) as im:assert im.format=='JPEG' and im.size==(s['width'],s['height'])
    for f in s['evidence']:assert (out/f).is_file()
class Links(HTMLParser):
    def __init__(self):super().__init__();self.paths=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ['href','src']:self.paths.append(v)
pages=[root/'03-正文预览.html',out/'surface-model-report/report.html',out/'document-hiertext-native-path/evidence.html',out/'video-gpu/analysis/report.html',*[d/'report.html' for d in sigdirs]]
for page in pages:
    parser=Links();parser.feed(page.read_text(encoding='utf-8-sig'))
    for link in parser.paths:
        u=urlsplit(link)
        if not u.scheme and u.path:assert (page.parent/unquote(u.path)).is_file(),(page,link)
article=(root/'03-正文.md').read_text(encoding='utf-8')
assert len(re.findall(r'^## ',article,re.M))==7 and len(re.findall(r'(?<!!)\[[^\]]+\]\([^)]+\)',article))==3
assert len(re.findall(r'!\[[^\]]+\]\(research/validation/round5/',article))==4
for name in ['01-cover-v2.png','02-api-architecture-v3.png','03-surfacelab-v3.png','04-signal-diagnostics-v3.png','05-document-evidence-v3.png','06-video-event-search-v3.png']:assert '(assets/'+name+')' in article
assert 'ROOT CAUSE UNKNOWN' not in article and '本轮 OCR Compile 失败' not in article
docs=[root/'03-正文.md',root/'05-上手与验证.md',root/'examples/README.md',root/'examples/MigraphxCompute/README.md',root/'research/真实开源数据案例与截图.md',out/'README.md',out/'THIRD_PARTY.md',root.parent/'README.md']
for path in docs:
    text=path.read_text(encoding='utf-8-sig');assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)',text),path
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
        u=urlsplit(link)
        if not u.scheme and u.path:assert (path.parent/unquote(u.path)).exists(),(path,link)
history={}
for r,commit in [('round2','a5aeb7d'),('round3','a4f73e4'),('round4','9727a7d')]:
    m=read(root/'research/validation'/r/'manifest.json')
    for item in m['files']:
        p=(root/item['path']).resolve()
        if item['path'].startswith('research/validation/'+r+'/'):
            assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],p
        else:
            raw=subprocess.check_output(['git','show',commit+':'+p.relative_to(repo).as_posix()],cwd=repo)
            assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],p
    history[r]=len(m['files'])
save(out/'final-checks.json',{'checkedAt':dt.datetime.now().astimezone().isoformat(),'nativePathContrasts':6,'matmulActualWrapperRuns':2,
 'surfaceImages':12,'surfaceConfusion':confusion,'surfaceAllNeedReview':True,'signalPsdValues':len(errors),'ocrCurrentGpuLines':24,'ocrProbabilityValues':93120,
 'officialOcrDataModelFilesRevalidated':len(files),'videoFrames':25,'videoDetections':109,'videoUnreviewedCandidates':12,'videoStderrRetained':True,
 'rawCurrentScreenshots':4,'historicalHashesVerified':history,'readerPathsPortable':True,'new264TestsOrPerformanceRerun':False,'productionAcceptance':False})
print('Passed current real outputs, official labels, screenshots, reader links and historical hashes:',history)
