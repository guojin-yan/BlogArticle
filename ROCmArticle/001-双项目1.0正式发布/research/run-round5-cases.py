"""Rerun fixed public inputs with Windows-native device-library paths."""
import argparse,datetime as dt,hashlib,io,json,os,shutil,subprocess,sys,time,urllib.request,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('stage',choices=['surface-server','surface-run','signal','video','matmul-forward','matmul-backslash']);p.add_argument('--label',default='')
a=p.parse_args();root=Path(__file__).resolve().parents[1];out=root/'research/validation/round5'
source=root.parent/'.tools/apps-round3-source';build=root.parent/'.tools/apps-round3-build/bin'
assets=Path('E:/GitSpace/ROCm-CSharp-Projects/assets');hip=Path('D:/AMD/ROCm/10.1.0/HIP');native=Path('D:/AMD/ROCm/10.1.0/MIGraphX/bin/migraphx_c.dll')
env=dict(os.environ,HIP_PATH=str(hip),ROCM_PATH=str(hip),HIP_DEVICE_LIB_PATH=str(hip/'lib/llvm/amdgcn/bitcode'),
 ROCBLAS_TENSILE_LIBPATH=str(hip/'bin/rocblas/library'),HIPBLASLT_TENSILE_LIBPATH=str(hip/'bin/hipblaslt/library/gfx1100'),
 MIGRAPHX_NATIVE_PATH=str(native),INSPECTION_GPU_ARCH='gfx1100',SIGNAL_GPU_ARCH='gfx1100',INSPECTION_URL='http://127.0.0.1:5086',
 INSPECTION_DATA_ROOT=str(out/'surface-workspace'),INSPECTION_MODEL_ROOT=str(assets/'models'),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
env['PATH']=str(native.parent)+';'+str(hip/'bin')+';'+str(hip/'lib/llvm/bin')+';'+env['PATH']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):
    Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def app(n):return build/n/'Release/net10.0'/(n+'.dll')
def run(label,cmd,cwd=source):
    log=out/'logs'/(label+'.log');start=dt.datetime.now().astimezone().isoformat()
    with log.open('xb') as f:code=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=None if label=='surface-server' else 900).returncode
    save(out/'commands'/(label+'.json'),{'command':list(map(str,cmd)),'started':start,'finished':dt.datetime.now().astimezone().isoformat(),
     'exitCode':code,'deviceLibraryEnvironment':{k:env[k] for k in ['ROCBLAS_TENSILE_LIBPATH','HIPBLASLT_TENSILE_LIBPATH']},'logSha256':sha(log)})
    print(label,code,flush=True)
    if code:raise RuntimeError(log)
if a.stage=='surface-server':run('surface-server',['dotnet',app('Inspection.App')])
if a.stage=='surface-run':
    def request(path,body=None):
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:5086'+path,data=body,
          headers={'Content-Type':'multipart/form-data; boundary=round5-real-visa'} if body else {}),timeout=60) as r:return r.read()
    catalog=json.loads(request('/api/models'));model=next(m for m in catalog if m['id']=='visa-pcb1-dinov2-patchcore-v1' and m['available'])
    manifest=assets/'visa/pcb1-smoke/manifest.json';data=read(manifest)
    recipe={'modelId':model['id'],'modelFingerprint':model['fingerprint']};save(out/'surface-recipe.json',recipe)
    fields={'name':'VisA pcb1 · 12 real images · DINOv2/PatchCore GPU','backend':'MigraphX','recipe':json.dumps(recipe)}
    parts=[f'--round5-real-visa\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k,v in fields.items()]
    for s in data['samples']:
        image=manifest.parent/s['image'];name=s['id']+image.suffix
        parts.append(f'--round5-real-visa\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+image.read_bytes()+b'\r\n')
    parts.append(b'--round5-real-visa--\r\n');start=dt.datetime.now().astimezone().isoformat()
    batch=json.loads(request('/api/batches',b''.join(parts)))
    save(out/'surface-submission.json',{'started':start,'sourceManifestSha256':sha(manifest),'model':model,'id':batch['id']})
    for _ in range(1800):
        batch=json.loads(request('/api/batches/'+batch['id']))
        if batch['status'] not in ['Queued','Running']:break
        time.sleep(.2)
    save(out/'surface-model-batch.json',batch)
    assert len(batch['items'])==12 and all(i['status']=='Completed' and i['finalDecision']=='NeedsReview' for i in batch['items'])
    archive=request('/api/batches/'+batch['id']+'/export/zip');(out/'surface-model.zip').write_bytes(archive)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert z.testzip() is None;z.extractall(out/'surface-model-report')
    checks=[]
    for s,i in zip(data['samples'],batch['items'],strict=True):
        assert sha(manifest.parent/s['image'])==i['sourceHash']
        assert i['anomaly']['manifestSha256']==model['fingerprint'] and i['measurement']['backend'].startswith('MIGraphX GPU')
        checks.append({'id':s['id'],'officialAnomaly':s['anomaly'],'score':i['anomaly']['score'],'machineDecision':i['machineDecision'],'finalDecision':i['finalDecision'],'sourceSha256':i['sourceHash']})
    save(out/'surface-model-summary.json',{'images':12,'initializationMs':batch['initializationMs'],'checks':checks,
      'scope':'Same frozen 12-image subset and preset model thresholds; no production quality or independent benchmark claim.'})
    print(json.dumps({'id':batch['id'],'images':12}),flush=True)
if a.stage=='video':
    # Reuse the byte-frozen prepared frames, recipe and model; no reselection.
    run('video-nasa-gpu',[sys.executable,'-B',source/'eng/video-run-workflow.py','run',
      '--prepared',root/'research/validation/round4/video-prepared','--app',app('VideoEvents.App'),'--dotnet',shutil.which('dotnet'),'--output',out/'video-gpu'])
if a.stage=='signal':
    data=assets/'signals/uci447-ps1-cycle1-v2'
    prefix='signal'+('-'+a.label if a.label else '')
    for backend in ['cpu','hip']:
        label=prefix+'-uci-'+backend
        run(label,['dotnet',app('Signal.App'),'analyze',data/'signal.csv','--config',data/'config.json','--source-manifest',data/'source-manifest.json',
         *(['--hip'] if backend=='hip' else []),'--output',out/(prefix+'-'+backend)])
        save(out/(prefix+'-'+backend+'-summary.json'),read(out/'logs'/(label+'.log')))
    cpu,gpu=[read(Path(read(out/(prefix+'-'+b+'-summary.json'))['output'])/'result.json') for b in ['cpu','hip']]
    errors=[]
    assert cpu['inputSha256']==gpu['inputSha256'] and cpu['configSha256']==gpu['configSha256']
    for x,y in zip(cpu['frames'],gpu['frames'],strict=True):
        assert x['decision']==y['decision']
        for v,w in zip(x['spectrum']['psd'],y['spectrum']['psd'],strict=True):
            assert abs(w-v)<=1e-5+1e-4*abs(v);errors.append(abs(w-v))
    save(out/'signal-comparison.json',{'passed':True,'windows':len(cpu['frames']),'psdValues':len(errors),'maxAbs':max(errors),
      'scope':'Unmodified UCI PS1 cycle 1; illustrative rule, not fault diagnosis acceptance.'})
if a.stage.startswith('matmul-'):
    hiparg=hip.as_posix() if a.stage=='matmul-forward' else str(hip)
    run(a.stage,['pwsh','-NoProfile','-File',root/'examples/run-windows.ps1','-HipRoot',hiparg,'-Mode','verify',
      '-ModelPath',root/'examples/MigraphxCompute/matmul-relu.onnx','-OutputPath',out/(a.stage+'.json')],cwd=root)
