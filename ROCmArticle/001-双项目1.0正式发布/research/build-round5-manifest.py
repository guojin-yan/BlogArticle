"""Freeze current evidence and reader files; preserve every earlier round manifest."""
import datetime as dt,hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];repo=root.parents[1];out=root/'research/validation/round5'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def entry(p):return {'path':Path(os.path.relpath(p,root)).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
if '--verify' in sys.argv or '--verify-index' in sys.argv:
    data=read(out/'manifest.json')
    for item in data['files']:
        p=(root/item['path']).resolve();assert entry(p)==item,item['path']
        if '--verify-index' in sys.argv:
            raw=subprocess.check_output(['git','show',':'+p.relative_to(repo).as_posix()],cwd=repo)
            assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],item['path']
    print('Verified',len(data['files']),'current evidence and reader-file hashes.')
else:
    candidates=sorted(p for p in out.rglob('*') if p.is_file())
    names=b'\0'.join(p.relative_to(repo).as_posix().encode() for p in candidates)+b'\0'
    check=subprocess.run(['git','check-ignore','--no-index','-z','--stdin'],input=names,cwd=repo,capture_output=True)
    assert check.returncode in [0,1],check.stderr
    ignored=set(check.stdout.decode().rstrip('\0').split('\0'))
    local=[p for p in candidates if p.relative_to(repo).as_posix() in ignored and p.name!='writer.lock']
    save(out/'local-only-files.json',{'scope':'Exact redundant SurfaceLab workspace and ZIP retained locally; complete extracted report, 48 actual PNGs, CSV and JSON are tracked.',
       'files':[entry(p) for p in local]})
    extras=[root/f for f in ['01-事实与来源.md','02-配图方案.md','03-正文.md','03-正文预览.html','04-编辑记录.md','05-上手与验证.md',
      'examples/run-windows.ps1','examples/README.md','examples/MigraphxCompute/README.md','research/真实开源数据案例与截图.md',
      'research/build-preview.py','research/issue-2-截图与四应用复跑.md']]
    extras.extend(root/'research'/name for name in ['run-round5-diagnostics.py','run-round5-cases.py','run-round5-document.py','build-round5-evidence.py','check-round5.py','build-round5-manifest.py'])
    extras.append(root.parent/'README.md')
    public=[p for p in out.rglob('*') if p.is_file() and p.relative_to(repo).as_posix() not in ignored and p!=out/'manifest.json']
    save(out/'manifest.json',{'createdAt':dt.datetime.now().astimezone().isoformat(),'revision':'v8','baselineCommit':'9727a7d',
      'applicationSourceCommit':'2f70b96267484b441fa726a3d496b8cc55d47219','screenshots':'screenshots/manifest.json',
      'scope':'Windows native path A/B diagnosis, fixed reader wrapper, four current public-data executions, raw actual screenshots and preserved failures.',
      'historicalManifests':'round2/3/4 raw unchanged; old mutable files at a5aeb7d/a4f73e4/9727a7d.',
      'productionAcceptance':False,'files':[entry(p) for p in sorted(set(public+extras))]})
    print('Inventoried',len(set(public+extras)),'public files;',len(local),'redundant local files retained.')
