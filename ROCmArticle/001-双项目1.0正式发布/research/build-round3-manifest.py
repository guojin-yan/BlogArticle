"""Inventory current article and round3 evidence without rewriting historical data."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'research/validation/round3'
DEST = OUT / 'manifest.json'
REPO = ROOT.parents[1]

def entry(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

if '--verify' in sys.argv or '--verify-index' in sys.argv:
    data = json.loads(DEST.read_text(encoding='utf-8'))
    for item in data['files']:
        path = ROOT / item['path']
        assert entry(path) == item, item['path']
        if '--verify-index' in sys.argv:
            staged = subprocess.check_output(['git', 'show', ':'+path.relative_to(REPO).as_posix()], cwd=REPO)
            assert len(staged) == item['bytes'] and hashlib.sha256(staged).hexdigest() == item['sha256'], item['path']
    print(f"Verified {len(data['files'])} current evidence and article hashes; two GPU Compile failures remain.")
else:
    extras = [ROOT / name for name in ['03-正文.md', '03-正文预览.html', '04-编辑记录.md', '05-上手与验证.md',
        'research/issue-2-修订说明.md', 'research/issue-2-截图与四应用复跑.md',
        'research/run-round3-apps.py', 'research/run-round3-document-page.py',
        'research/build-round3-log-views.py', 'research/build-round3-manifest.py',
        'research/check-round3.py', 'research/check-round2.py', 'research/check-issue1.py', 'research/build-preview.py']]
    files = sorted({p for p in OUT.rglob('*') if p.is_file() and p != DEST and '__pycache__' not in p.parts} | set(extras))
    data = {'createdAt': datetime.datetime.now().astimezone().isoformat(), 'revision': 'v6',
        'baselineCommit': 'a5aeb7d', 'applicationSourceCommit': '2f70b96267484b441fa726a3d496b8cc55d47219',
        'environment': 'research/validation/round3/environment.json',
        'commands': 'research/validation/round3/commands.json',
        'screenshots': 'research/validation/round3/screenshots/manifest.json',
        'scope': 'Actual browser viewport captures, four applications executed. Surface patchbank and Document OCR Compile failed. Authored document CPU workflow separately completed.',
        'historicalRound2Manifest': 'Preserved unchanged; its article/source hashes are verified at a5aeb7d, round2 raw evidence against the current checkout.',
        'productionAcceptance': False, 'allIssue2AcceptanceMet': False, 'files': [entry(p) for p in files]}
    DEST.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(f"Wrote {len(files)} hashes; original failures and round2 evidence preserved.")
