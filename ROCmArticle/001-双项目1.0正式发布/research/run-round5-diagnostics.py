"""Bounded native/C# compile diagnosis; official repositories remain read-only."""
import argparse,datetime as dt,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('stage',choices=['native-matmul','cli-matmul','cli-ocr','surface','document'])
p.add_argument('--label',required=True);p.add_argument('--override',action='append',default=[])
a=p.parse_args();root=Path(__file__).resolve().parents[1];out=root/'research/validation/round5';out.mkdir(exist_ok=True)
(out/'logs').mkdir(exist_ok=True);(out/'commands').mkdir(exist_ok=True)
hip=Path('D:/AMD/ROCm/10.1.0/HIP');native=Path('D:/AMD/ROCm/10.1.0/MIGraphX/bin/migraphx_c.dll')
assets=Path('E:/GitSpace/ROCm-CSharp-Projects/assets');snapshot=root.parent/'.tools/apps-round3-source';build=root.parent/'.tools/apps-round3-build/bin'
env=dict(os.environ,HIP_PATH=str(hip),ROCM_PATH=str(hip),HIP_DEVICE_LIB_PATH=str(hip/'lib/llvm/amdgcn/bitcode'),
 ROCBLAS_TENSILE_LIBPATH=str(hip/'bin/rocblas/library'),HIPBLASLT_TENSILE_LIBPATH=str(hip/'bin/hipblaslt/library/gfx1100'),
 MIGRAPHX_NATIVE_PATH=str(native),INSPECTION_GPU_ARCH='gfx1100',INSPECTION_DATA_ROOT=str(out/'surface-workspace'),INSPECTION_MODEL_ROOT=str(assets/'models'),
 PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
env['PATH']=str(native.parent)+';'+str(hip/'bin')+';'+str(hip/'lib/llvm/bin')+';'+env['PATH']
changes={}
for item in a.override:
    key,value=item.split('=',1);changes[key]=value
    if value=='<UNSET>':env.pop(key,None)
    else:env[key]=value
def app(n):return build/n/'Release/net10.0'/(n+'.dll')
model=root/'examples/MigraphxCompute/matmul-relu.onnx'
if a.stage=='native-matmul':
    cmd=[sys.executable,'-B',root/'examples/native-compile-probe.py','--model',model,'--native',native,'--hip-root',hip]
elif a.stage.startswith('cli-'):
    if a.stage=='cli-ocr':model=assets/'document-evidence/en-ppocrv3-ctc-v2/recognizer.onnx'
    cmd=[native.parent/'migraphx-driver.exe','compile',model,'--onnx','--gpu','--disable-fast-math','--enable-offload-copy','--brief']
elif a.stage=='surface':cmd=['dotnet',app('Inspection.App'),'verify-model','visa-pcb1-dinov2-patchcore-v1']
else:
    # R: temporarily maps round5; preserves existing app's Git ancestor output guard.
    cmd=[sys.executable,'-B',root/'research/run-round5-document.py','--evaluator',snapshot/'eng/document-evaluate-hiertext.py',
       '--model',assets/'document-evidence/en-ppocrv3-ctc-v2/model.json','--manifest',assets/'document-evidence/hiertext-test-small-v1/lines.json',
       '--app',app('Documents.App'),'--output','R:/document-'+a.label]
log=out/'logs'/(a.label+'.log');start=dt.datetime.now().astimezone().isoformat()
with log.open('xb') as f:
    try:code=subprocess.run(list(map(str,cmd)),env=env,cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300).returncode
    except subprocess.TimeoutExpired:code='TIMEOUT'
record={'command':list(map(str,cmd)),'stage':a.stage,'started':start,'finished':dt.datetime.now().astimezone().isoformat(),
 'exitCode':code,'environmentOverrides':changes,'deviceLibraryEnvironment':{k:env.get(k) for k in ['HIP_PATH','HIP_DEVICE_LIB_PATH','ROCBLAS_TENSILE_LIBPATH','HIPBLASLT_TENSILE_LIBPATH']},'native':str(native),'nativeSha256':hashlib.sha256(native.read_bytes()).hexdigest(),
 'log':'logs/'+log.name,'logSha256':hashlib.sha256(log.read_bytes()).hexdigest()}
(out/'commands'/(a.label+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'label':a.label,'exitCode':code,'logBytes':log.stat().st_size}),flush=True)
