"""Build/verify the evidence inventory; do not alter raw logs or measurements."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
R2 = ROOT / 'research/validation/round2'
DEST = R2 / 'manifest.json'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def entry(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}
if '--verify' in sys.argv or '--verify-index' in sys.argv:
    manifest = read(DEST)
    for item in manifest['files']:
        path = ROOT / item['path']
        assert path.is_file() and path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], item['path']
        if '--verify-index' in sys.argv:
            git_path = path.relative_to(ROOT.parents[1]).as_posix()
            staged = subprocess.check_output(['git', 'show', ':' + git_path], cwd=ROOT.parents[1])
            assert hashlib.sha256(staged).hexdigest() == item['sha256'], 'staged bytes: ' + git_path
    print(f"Verified {len(manifest['files'])} SHA256 entries; acceptance remains partial.")
else:
    extras = [ROOT / p for p in ['03-正文.md', '03-正文预览.html', '05-上手与验证.md',
        'examples/README.md', 'examples/run-windows.ps1', 'examples/run-round2.ps1',
        'examples/native-compile-probe.py', 'examples/MigraphxCompute/Program.cs',
        'examples/MigraphxCompute/PhotoDetection.cs', 'examples/MigraphxCompute/Round2Tools.cs',
        'examples/MigraphxCompute/MigraphxCompute.csproj', 'examples/MigraphxCompute/README.md',
        'research/issue-2-修订说明.md', 'research/run-round2-evidence.ps1',
        'research/summarize-round2.py', 'research/check-issue1.py', 'research/check-round2.py',
        'research/build-round2-manifest.py', 'research/build-preview.py']]
    files = sorted({p for p in R2.rglob('*') if p.is_file() and p != DEST and '__pycache__' not in p.parts} | set(extras))
    manifest = {'date': '2026-11-20', 'timezone': 'Asia/Shanghai', 'articleRevision': 'v5',
        'issue': 'https://github.com/guojin-yan/BlogArticle/issues/2',
        'baselineCommit': (R2 / 'baseline-commit.txt').read_text(encoding='utf-8-sig').strip(),
        'worktree': 'Experiments used uncommitted candidate sources on this baseline. This manifest hashes final files; it does not invent a pre-existing final commit.',
        'environment': read(R2 / 'environment.json'),
        'nuget': 'research/validation/round2/results/nuget-lock.txt',
        'sourceStages': {
            'benchmark': {'main': 'research/validation/round2/sources/Program-benchmark.cs',
                'sha256': read(R2 / 'results/source-native-hashes.json')[0]['Hash'].lower(),
                'scope': 'Byte-for-byte recovered using the recorded hash. Final Program differs only in cache-kind option/dispatch; timed methods unchanged. Helper cache revisions were not snapshotted for each early failed attempt.'},
            'photoInitial': 'research/validation/round2/sources/PhotoDetection-before-final.cs',
            'cacheParsedThreeProcesses': 'research/validation/round2/sources/Round2Tools-before-final.cs',
            'cacheFinalHit': 'research/validation/round2/sources/Round2Tools-cache-final.cs',
            'finalChanges': 'Photo report input-copy/device metadata and output-length guards; cache startup-field sampling moved before hot loop. Final source build, photo, doctor, verify and cache hit rechecked separately. Later doctor-only exception guard fixed missing-SDK report loss, with positive/negative prechecks rerun.'},
        'inputs': {'modelSha256': sha(R2 / 'inputs/yolox_nano.onnx'), 'imageSha256': sha(R2 / 'inputs/astronaut.png'),
            'licenseAndSources': 'research/validation/round2/inputs/README.md'},
        'screenshotStatus': {'status': 'BLOCKED / NOT CAPTURED',
            'reason': 'Computer-use stopped because current browser URL could not be determined confidently enough to enforce policy. No alternate screenshot route used.',
            'actualResultImage': 'research/validation/round2/results/yolox-detections.png', 'resultImageIsDesktopScreenshot': False},
        'limits': ['cache-cold NOT TESTED', 'MatMul ROOT CAUSE UNKNOWN', 'four applications NOT RE-RUN',
            'same physical Windows host and existing system/NuGet dependencies; no independent human reader',
            'no independent per-kernel profiler or process peak VRAM', 'other GPU/platform and small INT8 NOT RE-RUN',
            'v5 HTML/source checked; new desktop/mobile visual QA NOT COMPLETED'],
        'allIssue2AcceptanceMet': False, 'files': [entry(p) for p in files]}
    DEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Wrote manifest with {len(files)} files; no raw evidence changed.")
