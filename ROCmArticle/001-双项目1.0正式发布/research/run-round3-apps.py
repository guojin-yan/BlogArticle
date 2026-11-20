"""Rerun four real applications from a read-only source snapshot; save every exit/log."""
import argparse
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
import zipfile
import io

p = argparse.ArgumentParser()
p.add_argument('--attempt',default='')
p.add_argument('--stage', choices=['surface','signal','document','document-demo','video'], required=True)
p.add_argument('--surface-model', action='store_true')
p.add_argument('--source', required=True)
p.add_argument('--build', required=True)
p.add_argument('--assets', required=True)
p.add_argument('--prepared-video', required=True)
p.add_argument('--hip-root', required=True)
p.add_argument('--native', required=True)
p.add_argument('--output', required=True)
p.add_argument('--surface-url', default='http://127.0.0.1:5086')
a = p.parse_args()
source, build, assets = map(lambda x: Path(x).resolve(), [a.source, a.build, a.assets])
out = Path(a.output).absolute()  # Preserve the documented temporary output-drive alias.
out.mkdir(parents=True, exist_ok=True)
commands = json.loads((out/"commands.json").read_text(encoding="utf-8")) if (out/"commands.json").exists() else []
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', HIP_PATH=a.hip_root, ROCM_PATH=a.hip_root,
    HIP_DEVICE_LIB_PATH=a.hip_root+'/lib/llvm/amdgcn/bitcode', ROCBLAS_TENSILE_LIBPATH=a.hip_root+'/bin/rocblas/library',
    HIPBLASLT_TENSILE_LIBPATH=a.hip_root+'/bin/hipblaslt/library/gfx1100', SIGNAL_GPU_ARCH='gfx1100', MIGRAPHX_NATIVE_PATH=a.native)
env['PATH'] = a.hip_root+'/bin;'+a.hip_root+'/lib/llvm/bin;'+env['PATH']
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def app(name): return str(build/'bin'/name/'Release/net10.0'/(name+'.dll'))
def run(label, args, expected=0):
    label += ('-'+a.attempt) if a.attempt else ''
    print(label, flush=True)
    log = out/'logs'/(label+'.log')
    started = dt.datetime.now().astimezone().isoformat()
    with log.open('xb') as f:
        result = subprocess.run(list(map(str,args)), cwd=source, env=env, stdout=f, stderr=subprocess.STDOUT)
    record = {'label':label,'command':list(map(str,args)),'started':started,'finished':dt.datetime.now().astimezone().isoformat(),
        'exitCode':result.returncode,'expectedExit':expected,'log':log.relative_to(out).as_posix(),'logSha256':sha(log)}
    # Keep one immutable record per execution before refreshing the summary.
    # Independent stages can finish in a different order from their starts.
    record_path = out/'command-records'/(label+'.json')
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(record, f, ensure_ascii=False, indent=2); f.write('\n')
    current = read(out/'commands.json') if (out/'commands.json').exists() else []
    current.append(record)
    write(out/'commands.json', current)
    if result.returncode != expected: raise RuntimeError(f'{label}: {result.returncode}, expected {expected}; see {log}')
    return log

if a.stage == 'surface':
    # Real local service, CPU/HIP equality, review history, broken input retention, model workflow.
    surface_name='surface-smoke-model-retry' if a.surface_model else 'surface-smoke-hip'
    run(surface_name, [sys.executable,'-B',source/'eng/smoke-inspection.py','--url',a.surface_url,'--gpu','--report',out/f'results/{surface_name}.json'] + (['--model','visa-pcb1-patchbank-v1','--manifest',assets/'visa/pcb1-smoke/manifest.json'] if a.surface_model else []))
    surface = read(out/f'results/{surface_name}.json')
    for label,key in [('cpu','cpuBatch'),('hip','gpuBatch'),('model','modelBatch')]:
        if not surface[key]: continue
        url = a.surface_url+'/api/batches/'+surface[key]
        with urllib.request.urlopen(url) as response: data=response.read()
        (out/f'results/surface-{label}-batch.json').write_bytes(data)
        with urllib.request.urlopen(url+'/export/zip') as response: package=response.read()
        (out/f'results/surface-{label}-report.zip').write_bytes(package)
        with zipfile.ZipFile(io.BytesIO(package)) as z: z.extractall(out/f'results/surface-{label}-report')

if a.stage == 'signal':
    # Keep raw stdout and actual spectral tensors rather than only a PASS summary.
    run('signal-gpu-verify',['dotnet',app('Signal.App'),'verify-gpu'])
    cpu_log=run('signal-cpu-demo',['dotnet',app('Signal.App'),'demo','--output',out/'results/signal-cpu'])
    cpu_summary=read(cpu_log); cpu_dir=Path(cpu_summary['output'])
    hip_log=run('signal-hip-analyze',['dotnet',app('Signal.App'),'analyze',cpu_dir/'input.csv','--config',cpu_dir/'config.json','--hip','--output',out/'results/signal-hip'])
    hip_summary=read(hip_log); hip_dir=Path(hip_summary['output'])
    cpu,hip=read(cpu_dir/'result.json'),read(hip_dir/'result.json')
    assert cpu['inputSha256']==hip['inputSha256'] and cpu['configSha256']==hip['configSha256']
    errors=[]
    for c,g in zip(cpu['frames'],hip['frames'],strict=True):
        assert c['decision']==g['decision']
        for expected,actual in zip(c['spectrum']['psd'],g['spectrum']['psd'],strict=True):
            error=abs(actual-expected); assert error <= 1e-5+1e-4*abs(expected); errors.append(error)
    write(out/'results/signal-comparison.json',{'frames':len(cpu['frames']),'psdValues':len(errors),'maxAbs':max(errors),
        'cpuNeedsReview':cpu_summary['needsReview'],'hipNeedsReview':hip_summary['needsReview'],'passed':True,
        'cpuReport':(cpu_dir/'report.html').relative_to(out).as_posix(),'hipReport':(hip_dir/'report.html').relative_to(out).as_posix(),
        'scope':'Authored 4096 Hz two-frequency fixture; GPU numerical/software integration, no device diagnosis accuracy.'})

if a.stage == 'document':
    # One GPU OCR session, frozen seven-line authored page and CPU tensor comparisons.
    doc=out/('results/document-gpu'+('-'+a.attempt if a.attempt else ''))
    run('document-page-gpu',[sys.executable,'-B',Path(__file__).with_name('run-round3-document-page.py'), '--evaluator', source/'eng/document-evaluate-page.py',
        '--model',assets/'document-evidence/en-ppocrv3-ctc-v2/model.json',
        '--declaration',assets/'document-evidence/authored-page-v1/page-lines.json','--app',app('Documents.App'),'--output',doc])
    case=out/'results/document-case'; template=assets/'document-evidence/authored-page-v1/template.json'
    run('document-import',['dotnet',app('Documents.App'),'import',doc/'recognized/ocr-evidence.json',template,case],expected=2)
    run('document-export-initial',['dotnet',app('Documents.App'),'export',case,out/'results/document-initial-report'])
    run('document-approve-rejected',['dotnet',app('Documents.App'),'approve',case,'0','article-fixture-reviewer','Expected rejection for missing subtotal'],expected=1)
    run('document-explicit-fixture-correction',['dotnet',app('Documents.App'),'correct',case,'0','article-fixture-reviewer','Authored fixture transcription of visible amount; not independent business review','subtotal','20.00'])
    run('document-approve-fixture',['dotnet',app('Documents.App'),'approve',case,'1','article-fixture-reviewer','Authored demonstration only; checked original page'])
    run('document-export-final',['dotnet',app('Documents.App'),'export',case,out/'results/document-final-report'])

if a.stage == 'document-demo':
    run('document-cpu-workflow-demo', ['dotnet', app('Documents.App'), 'demo', out/'results/document-cpu-demo'])

if a.stage == 'video':
    # Frozen real-media preparation, actual GPU execution, all sampled frames and PTS.
    run('video-real-media-gpu',[sys.executable,'-B',source/'eng/video-run-workflow.py','run','--prepared',a.prepared_video,
        '--app',app('VideoEvents.App'),'--dotnet',str(Path(subprocess.check_output(['where.exe','dotnet'],text=True).splitlines()[0])),
        '--output',out/'results/video-gpu'])

print(f'{a.stage} stage completed; inspect raw evidence and scope.',flush=True)
