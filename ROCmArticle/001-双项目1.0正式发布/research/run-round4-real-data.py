"""Run public-data cases without modifying application source or test labels."""
import argparse, datetime as dt, hashlib, importlib.util, io, json, os, shutil, subprocess, sys, time, urllib.request, zipfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('stage', choices=['signal', 'surface-model', 'surface-hip', 'document', 'video-prepare', 'video-run'])
p.add_argument('--assets', required=True)
p.add_argument('--hip-root', required=True)
p.add_argument('--native', required=True)
p.add_argument('--output', required=True)
a = p.parse_args()
article = Path(__file__).resolve().parents[1]
source = article.parent/'.tools/apps-round3-source'
build = article.parent/'.tools/apps-round3-build/bin'
assets, out = Path(a.assets), Path(a.output).absolute()
out.mkdir(parents=True, exist_ok=True)
(out/'logs').mkdir(exist_ok=True)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', HIP_PATH=a.hip_root, ROCM_PATH=a.hip_root,
 HIP_DEVICE_LIB_PATH=a.hip_root+'/lib/llvm/amdgcn/bitcode', ROCBLAS_TENSILE_LIBPATH=a.hip_root+'/bin/rocblas/library',
 HIPBLASLT_TENSILE_LIBPATH=a.hip_root+'/bin/hipblaslt/library/gfx1100', SIGNAL_GPU_ARCH='gfx1100', INSPECTION_GPU_ARCH='gfx1100',
 MIGRAPHX_NATIVE_PATH=a.native, INSPECTION_DATA_ROOT=str(out/'surface-workspace'), INSPECTION_MODEL_ROOT=str(assets/'models'))
env['PATH'] = a.hip_root+'/bin;'+a.hip_root+'/lib/llvm/bin;'+env['PATH']
os.environ.update(env)
def sha(f): return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def read(f): return json.loads(Path(f).read_text(encoding='utf-8-sig'))
def save(f,v):
    f=Path(f);f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def app(n): return build/n/'Release/net10.0'/(n+'.dll')
def run(label,args,timeout=600):
    log=out/'logs'/(label+'.log'); started=dt.datetime.now().astimezone().isoformat()
    print(label,flush=True)
    with log.open('xb') as f:
        try: code=subprocess.run(list(map(str,args)),cwd=source,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired: code='TIMEOUT'
    save(out/'commands'/(label+'.json'),{'label':label,'command':list(map(str,args)),'started':started,
      'finished':dt.datetime.now().astimezone().isoformat(),'exitCode':code,'log':log.relative_to(out).as_posix(),'logSha256':sha(log)})
    print(label,code,flush=True)
    return code,log

if a.stage=='signal':
    data=assets/'signals/uci447-ps1-cycle1-v2'
    for backend in ['cpu','hip']:
        code,log=run('signal-uci-'+backend,['dotnet',app('Signal.App'),'analyze',data/'signal.csv','--config',data/'config.json',
          '--source-manifest',data/'source-manifest.json',*(['--hip'] if backend=='hip' else []),'--output',out/('signal-'+backend)])
        if code: raise RuntimeError(log)
        save(out/('signal-'+backend+'-summary.json'),read(log))
    c,g=[read(read(out/('signal-'+b+'-summary.json'))['output']+'/result.json') for b in ['cpu','hip']]
    assert c['inputSha256']==g['inputSha256'] and c['configSha256']==g['configSha256']
    errors=[]
    for x,y in zip(c['frames'],g['frames'],strict=True):
        assert x['decision']==y['decision']
        for v,w in zip(x['spectrum']['psd'],y['spectrum']['psd'],strict=True):
            assert abs(w-v)<=1e-5+1e-4*abs(v);errors.append(abs(w-v))
    save(out/'signal-comparison.json',{'passed':True,'windows':len(c['frames']),'psdValues':len(errors),'maxAbs':max(errors),
     'scope':'Unmodified real UCI PS1 cycle 1, 100 Hz, bar; illustrative rule, not fault diagnosis acceptance.'})

if a.stage=='surface-model':
    run('surface-dinov2-patchcore-verify',['dotnet',app('Inspection.App'),'verify-model','visa-pcb1-dinov2-patchcore-v1'])

if a.stage=='surface-hip':
    # Upload the frozen complete 12-image real subset; no demo endpoint or generated pixels.
    manifest=assets/'visa/pcb1-smoke/manifest.json'; data=read(manifest)
    recipe=read(source/'projects/IndustrialInspection/config/uniform-surface.json')
    save(out/'surface-recipe.json',recipe)
    def request(path,body=None):
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:5086'+path,data=body,
          headers={'Content-Type':'multipart/form-data; boundary=round4-real-visa'} if body else {}),timeout=30) as r:return r.read()
    for backend in ['Cpu','Hip']:
        fields={'name':'VisA pcb1 · 12 real images · '+backend+' fixed grayscale rule','backend':backend,'recipe':json.dumps(recipe)}
        parts=[f'--round4-real-visa\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k,v in fields.items()]
        identity=[]
        for sample in data['samples']:
            image=manifest.parent/sample['image']; name=sample['id']+image.suffix
            parts.append(f'--round4-real-visa\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+image.read_bytes()+b'\r\n')
            identity.append({**sample,'uploadName':name,'sha256':sha(image)})
        parts.append(b'--round4-real-visa--\r\n')
        start=dt.datetime.now().astimezone().isoformat(); batch=json.loads(request('/api/batches',b''.join(parts)))
        for _ in range(600):
            batch=json.loads(request('/api/batches/'+batch['id']))
            if batch['status'] not in ['Queued','Running']:break
            time.sleep(.2)
        save(out/('surface-'+backend.lower()+'-batch.json'),batch)
        save(out/('surface-'+backend.lower()+'-inputs.json'),{'started':start,'sourceManifestSha256':sha(manifest),'samples':identity})
        archive=request('/api/batches/'+batch['id']+'/export/zip')
        (out/('surface-'+backend.lower()+'.zip')).write_bytes(archive)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:z.extractall(out/('surface-'+backend.lower()+'-report'))
        assert len(batch['items'])==12 and all(i['status']=='Completed' for i in batch['items'])
    c,g=[read(out/('surface-'+b+'-batch.json')) for b in ['cpu','hip']]
    for x,y in zip(c['items'],g['items'],strict=True):
        assert x['fileName']==y['fileName'] and x['defectPixels']==y['defectPixels']
        assert request('/api/batches/'+c['id']+'/items/'+x['id']+'/mask.png')==request('/api/batches/'+g['id']+'/items/'+y['id']+'/mask.png')
    save(out/'surface-comparison.json',{'passed':True,'images':12,'byteIdenticalMasks':True,'scope':'Real VisA images, fixed grayscale rule, no anomaly-model or defect-quality claim.'})

if a.stage=='document':
    # Preserve the temporary SUBST drive name for app output only. Evaluator validation/scoring unchanged.
    evaluator=source/'eng/document-evaluate-hiertext.py'
    sys.path.insert(0,str(evaluator.parent))
    spec=importlib.util.spec_from_file_location('hiertext',evaluator);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def external(path):
        logical=Path(path).absolute();physical=logical.resolve()
        if physical==source or source in physical.parents:raise ValueError('Output inside application source')
        return logical
    module.external=external
    args=argparse.Namespace(model=str(assets/'document-evidence/en-ppocrv3-ctc-v2/model.json'),
      manifest=str(assets/'document-evidence/hiertext-test-small-v1/lines.json'),app=str(app('Documents.App')),
      output=str(out/'document-gpu'),dotnet='dotnet',audit_only=False)
    started=dt.datetime.now().astimezone().isoformat()
    try:module.evaluate(args);status='completed'
    except Exception as error:status='failed';save(out/'document-attempt-error.json',{'error':str(error)})
    save(out/'document-attempt.json',{'started':started,'finished':dt.datetime.now().astimezone().isoformat(),'status':status,
      'evaluatorSha256':sha(evaluator),'adapter':'Only external path normalization preserves SUBST output alias; original validation, inference and scoring unchanged.'})

if a.stage.startswith('video-'):
    script=source/'eng/video-run-workflow.py'
    if a.stage=='video-prepare':
        run('video-prepare-r2',[sys.executable,'-B',script,'prepare','--input',assets/'video-event-search/nasa-walkout-v1/walkout-preview.mp4',
          '--protocol',out/'video-protocol.json','--model',assets/'video-event-search/yolox-nano-coco-first3-v1/detector.json',
          '--ffmpeg',assets/'video-event-search/tools/ffmpeg-9.0.2/bin/ffmpeg.exe','--ffprobe',assets/'video-event-search/tools/ffmpeg-9.0.2/bin/ffprobe.exe',
          '--output',out/'video-prepared'])
    else:
        run('video-nasa-gpu',[sys.executable,'-B',script,'run','--prepared',out/'video-prepared','--app',app('VideoEvents.App'),
          '--dotnet',shutil.which('dotnet'),'--output',out/'video-gpu'])
