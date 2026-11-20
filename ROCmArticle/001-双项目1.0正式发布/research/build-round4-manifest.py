"""Inventory current files and preserved local duplicate exports; never rewrite old manifests."""
import datetime as dt,hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];repo=root.parents[1];out=root/'research/validation/round4'
def sha(data):return hashlib.sha256(data).hexdigest()
def entry(p):return {'path':Path(os.path.relpath(p,root)).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def save(f,v):f.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
if '--verify' in sys.argv or '--verify-index' in sys.argv:
    data=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    for item in data['files']:
        path=(root/item['path']).resolve();assert entry(path)==item,item['path']
        if '--verify-index' in sys.argv:
            b=subprocess.check_output(['git','show',':'+path.relative_to(repo).as_posix()],cwd=repo)
            assert len(b)==item['bytes'] and sha(b)==item['sha256'],item['path']
    print('Verified',len(data['files']),'current article and public-data evidence hashes.')
else:
    candidates=sorted(p for p in out.rglob('*') if p.is_file())
    names=b'\0'.join(p.relative_to(repo).as_posix().encode('utf-8') for p in candidates)+b'\0'
    ignored=subprocess.run(['git','check-ignore','--no-index','-z','--stdin'],input=names,cwd=repo,capture_output=True)
    if ignored.returncode not in [0,1]:raise RuntimeError(ignored.stderr)
    localnames=set(ignored.stdout.decode('utf-8').rstrip('\0').split('\0'))
    local=[p for p in candidates if p.relative_to(repo).as_posix() in localnames]
    save(out/'local-only-files.json',{'scope':'Exact redundant raw SurfaceLab ZIP/workspace/export files retained locally, not re-uploaded. Complete 12 inputs/masks and numeric outputs have portable tracked copies.',
     'files':[entry(p) for p in local if p.name!='writer.lock']})
    extras=[root/f for f in ['01-事实与来源.md','02-配图方案.md','03-正文.md','03-正文预览.html','04-编辑记录.md','05-上手与验证.md',
      'research/真实开源数据案例与截图.md','research/build-preview.py','research/issue-2-截图与四应用复跑.md',
      'research/run-round4-real-data.py','research/build-round4-document-evidence.py','research/build-round4-evidence.py','research/check-round4.py','research/build-round4-manifest.py']]
    extras.append(root.parent/'README.md')
    public=[p for p in out.rglob('*') if p.is_file() and p.relative_to(repo).as_posix() not in localnames and p!=out/'manifest.json']
    save(out/'manifest.json',{'createdAt':dt.datetime.now().astimezone().isoformat(),'revision':'v7','baselineCommit':'a4f73e4',
      'applicationSourceCommit':'2f70b96267484b441fa726a3d496b8cc55d47219','screenshots':'screenshots/manifest.json',
      'scope':'Public real inputs, actual current HIP/signal/video runs and clearly dated historical HierText GPU outputs. Current surface model and OCR Compile failures retained.',
      'historicalManifests':'round2 raw unchanged; old article at a5aeb7d. round3 raw unchanged; old article at a4f73e4.',
      'productionAcceptance':False,'files':[entry(p) for p in sorted(set(public+extras))]})
    print('Inventoried',len(public+extras),'public files and',len(local),'local duplicate raw files.')
