"""Independently verify current executions, source/cache isolation, links and old bytes."""
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from PIL import Image

root = Path(__file__).resolve().parents[1]
repo = root.parents[1]
out = root / 'research/validation/round7'
clone = root.parent / '.tools/round7-reader'
reader = clone / root.relative_to(repo)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def git(*args, cwd=repo):
    return subprocess.check_output(['git', *args], cwd=cwd)


for path in out.glob('*.command.json'):
    command = read(path)
    expected = 1 if path.stem.removesuffix('.command') in ['doctor-positive', 'doctor-missing-sdk', 'doctor-wrong-arch', 'doctor-version-conflict'] else 0
    assert command['exitCode'] == expected and sha(out / command['log']) == command['logSha256'], path
    if 'sourceFilesUnchangedDuringRun' in command:
        assert command['sourceFilesUnchangedDuringRun']
        for p, digest in command['sourceFilesAtStart'].items():
            assert sha(root / p) == digest

positive = read(out / 'reader-doctor.json')
checks = {c['name']: c for c in positive['checks']}
assert positive['status'] == 'PASS_WITH_UNCHECKED_ITEMS' and not any(c['status'] == 'FAIL' for c in positive['checks'])
for name in ['Actual GPU gfx', 'Native static dependency closure', 'Native candidate identity scan', 'Driver/PowerShell/SDK inventory']:
    assert checks[name]['status'] == 'PASS'
assert checks['Native candidate compatibility']['status'] == checks['All model/solver ABI compatibility']['status'] == 'NOT CHECKED'
hardware = read(out / 'reader-doctor.json.hardware.json')
assert hardware['architectures'] == ['gfx1100'] and hardware['exitCode'] == 0 and sha(hardware['tool']) == hardware['toolSha256']
deps = read(out / 'reader-doctor.json.dependencies.json')
assert len(deps['files']) == 34 and len(deps['edges']) == 174 and not deps['missing'] and not deps['unreadable']
assert len(deps['conflicts']) == 4 and deps['versionConflicts'] == 0
for item in deps['files']:
    assert sha(item['path']) == item['sha256']
for item in deps['conflicts']:
    assert not item['differentVersions']
    for copy in item['copies']:
        assert sha(copy['path']) == copy['sha256']
for name, failed in [('doctor-missing-sdk', 'HIP_PATH'), ('doctor-wrong-arch', 'Actual GPU gfx'), ('doctor-version-conflict', 'Native candidate compatibility')]:
    report = read(out / (name + '.json'))
    assert report['status'] == 'FAIL' and any(c['name'] == failed and c['status'] == 'FAIL' for c in report['checks'])
assert read(out / 'doctor-positive.json')['status'] == 'FAIL'  # Prototype's over-strict byte rule retained.

commit = git('rev-parse', 'HEAD', cwd=clone).decode().strip()
assert commit == '73569f724920982aee6767cf7800635edb280c77'
assert git('status', '--porcelain', cwd=clone) == b''
sources = []
for path in sorted((reader / 'examples').rglob('*')):
    if path.suffix not in ['.cs', '.csproj', '.ps1'] or {'bin', 'obj'}.intersection(path.parts):
        continue
    relative = path.relative_to(clone).as_posix()
    raw = git('show', commit + ':' + relative)
    assert raw == path.read_bytes(), path
    assert raw.replace(b'\r\n', b'\n') == (repo / relative).read_bytes().replace(b'\r\n', b'\n'), path
    sources.append({'path': relative, 'sha256': sha(path), 'authorWorkingTreeSha256': sha(repo / relative),
                    'comparison': 'Clone bytes equal public Git blob; author checkout compared with CRLF/LF normalization only.'})
initial = read(out / 'reader-isolation-before.json')
assert len(initial['paths']) == 3 and set(initial['paths'].values()) == {0}
assert initial['samePhysicalHost'] and not initial['newOs'] and not initial['independentHumanReader']
assert not initial['oldNugetPackageAndHttpCacheReused'] and not initial['sourceOverlay']
packages = read(out / 'reader-restored-packages.json')
assert len(packages['restoredPackages']) == 10
assert {p['source'] for p in packages['restoredPackages']} == {'https://api.nuget.org/v3/index.json'}
fresh = (root.parent / '.tools/round7-fresh-nuget').resolve()
projects = list((reader / 'examples').glob('*/obj/project.assets.json'))
assert len(projects) == 5
for project in projects:
    assert {Path(p).resolve() for p in read(project)['packageFolders']} == {fresh}, project
identities = [reader / 'examples/ValidationWorkbench/bin/Release/net10.0-windows/ValidationWorkbench.exe',
              reader / 'examples/ValidationWorkbench/bin/Release/net10.0-windows/ValidationWorkbench.dll',
              reader / 'examples/MigraphxCompute/bin/Release/net10.0/MigraphxCompute.dll']
save(out / 'reader-source-identity.json', {'sourceCommit': commit, 'sourceOverlay': False, 'gitTrackedChanges': [],
    'sourceFiles': sources, 'projectAssetsSha256': {p.relative_to(reader).as_posix(): sha(p) for p in projects},
    'binaryFiles': [{'path': str(p), 'sha256': sha(p)} for p in identities],
    'scope': 'Fresh remote clone; no source edits. New package, HTTP and CLI folders; system driver, SDK and framework packs reused.'})

workspace = out / 'reader-workbench'
workbench = read(workspace / 'workbench.json')
assert workbench['completed'] and not workbench['allDisplayedChecksPassed']
assert len(workbench['rows']) == 9 and sum(r['status'] == 'NOT CHECKED' for r in workbench['rows']) == 1
assert all(r['status'] in ['PASS', 'NOT CHECKED'] for r in workbench['rows'])
for path in workspace.glob('*.command.json'):
    command = read(path)
    assert command['exitCode'] == 0
    name = path.stem.removesuffix('.command')
    assert sha(workspace / (name + '.stdout.log')) == command['stdoutSha256']
    assert sha(workspace / (name + '.stderr.log')) == command['stderrSha256']
for path in [workspace / 'verify.json', workspace / 'matmul.json', out / 'reader-trace.json']:
    result = read(path)
    assert result['outputElements'] == 4096
    for key in ['hostError', 'deviceError', 'rawHostError', 'rawDeviceError', 'finalHostError', 'finalDeviceError']:
        error = result[key]
        assert error['passed'] and error['failedElements'] == error['nonFiniteElements'] == 0 and error['maxAbs'] == 0
stdout = (workspace / 'verify.stdout.log').read_text(encoding='utf-8-sig')
assert 'PASS: length=65539; repetitions=3; max_abs_error=0' in stdout and '1, 2, 3, 4' in stdout
assert 'symbol_name=mul_add_relu_kernel' in (out / 'reader-trace.log').read_text(encoding='utf-8-sig')
photo = read(out / 'reader-photo/photo.json')
assert photo['modelSha256'] == sha(reader / 'research/validation/round2/inputs/yolox_nano.onnx')
assert photo['imageSha256'] == sha(out / 'reader-photo/input-photo.png') == sha(root / 'research/validation/round2/inputs/astronaut.png')
assert photo['resultImageSha256'] == sha(out / 'reader-photo/yolox-detections.png') == sha(root / 'research/validation/round2/results/yolox-detections.png')
assert photo['rawCompared'] == 301665 and photo['failedElements'] == photo['nonFiniteElements'] == 0
assert len(photo['detections']) == 1 and photo['detections'][0]['Label'] == 'person' and abs(photo['detections'][0]['Score'] - 0.92588) < 1e-6

shot = out / 'screenshots/01-native-validation.jpg'
capture = read(out / 'screenshots/capture.json')
assert capture['edited'] is False and capture['window']['title'] == 'ROCm C# · Live validation workbench'
assert Path(capture['window']['app'].removeprefix('process:')).resolve() == identities[0].resolve()
with Image.open(shot) as image:
    assert image.format == 'JPEG'
    width, height = image.size
save(out / 'screenshots/manifest.json', {'captureScope': 'Actual native C# application window including title bar; original unedited JPEG.',
    'gpu': 'AMD Radeon PRO W7900', 'gfx': 'gfx1100', 'os': 'Windows 11 build 26300', 'runtime': '.NET 10.0.15',
    'sourceCommit': commit, 'environment': '../reader-workbench/doctor.json.inventory.json', 'files': [{
        'file': shot.relative_to(out).as_posix(), 'api': capture['api'], 'date': capture['date'], 'width': width, 'height': height,
        'format': 'JPEG', 'sha256': sha(shot), 'bytes': shot.stat().st_size, 'edited': False,
        'evidence': ['reader-source-identity.json', 'reader-workbench/workbench.json', 'reader-workbench/doctor.json',
                     'reader-workbench/verify.json', 'reader-workbench/matmul.json', 'reader-workbench.command.json']} ]})


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        self.paths.extend(v for k, v in attrs if k in ['href', 'src'])


for path in [root / '03-正文预览.html', out / 'reader-photo/detection-report.html']:
    parser = Links()
    parser.feed(path.read_text(encoding='utf-8-sig'))
    for link in parser.paths:
        u = urlsplit(link)
        if not u.scheme and u.path:
            assert (path.parent / unquote(u.path)).is_file(), (path, link)
docs = [root / name for name in ['01-事实与来源.md', '02-配图方案.md', '03-正文.md', '04-编辑记录.md', '05-上手与验证.md',
    'examples/README.md', 'examples/ValidationWorkbench/README.md', 'research/issue-2-当前验收对照.md',
    'research/issue-2-修订说明.md', 'research/issue-2-截图与四应用复跑.md', 'research/真实开源数据案例与截图.md']]
docs += [out / 'README.md', root.parent / 'README.md']
for path in docs:
    text = path.read_text(encoding='utf-8-sig')
    # Internal factual archives may quote historical paths; reader instructions must not depend on them.
    if path.name not in ['01-事实与来源.md', '04-编辑记录.md']:
        assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)', text), path
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        u = urlsplit(link)
        if not u.scheme and u.path:
            target = (path.parent / unquote(u.path)).resolve()
            if target not in {(out / 'manifest.json').resolve(), (out / 'final-checks.json').resolve()}:
                assert target.exists(), (path, link)
article = (root / '03-正文.md').read_text(encoding='utf-8-sig')
assert len(re.findall(r'^## ', article, re.M)) == 7 and len(re.findall(r'(?<!!)\[[^\]]+\]\([^)]+\)', article)) == 3
assert len(re.findall(r'!\[[^\]]+\]\(research/validation/round5/', article)) == 3
assert len(re.findall(r'!\[[^\]]+\]\(research/validation/round6/', article)) == 1
for name in ['01-cover-v2.png', '02-api-architecture-v3.png', '03-surfacelab-v3.png', '04-signal-diagnostics-v3.png', '05-document-evidence-v3.png', '06-video-event-search-v3.png']:
    assert '(assets/' + name + ')' in article
assert 'v10，Issue #2' in (root / '03-正文预览.html').read_text(encoding='utf-8-sig')
requirements = read(out / 'issue-2-requirements.json')
assert len(requirements['records']) == 36 and sum(r['id'].startswith('DOD-') for r in requirements['records']) == 9
for record in requirements['records']:
    for evidence in record['evidence']:
        if evidence != 'research/validation/round7/final-checks.json':
            assert (root / evidence).exists(), evidence
for script in ['research/capture-round7.py', 'research/build-issue2-audit.py', 'research/check-round7.py', 'research/build-preview.py']:
    ast.parse((root / script).read_text(encoding='utf-8-sig'))

history = {}
for name, old_commit in [('round2', 'a5aeb7d'), ('round3', 'a4f73e4'), ('round4', '9727a7d'), ('round5', '1b33655'), ('round6', '4096421')]:
    manifest = read(root / 'research/validation' / name / 'manifest.json')
    for item in manifest['files']:
        path = (root / item['path']).resolve()
        raw = path.read_bytes() if item['path'].startswith('research/validation/' + name + '/') else git('show', old_commit + ':' + path.relative_to(repo).as_posix())
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], path
    history[name] = len(manifest['files'])
save(out / 'final-checks.json', {'checkedAt': dt.datetime.now().astimezone().isoformat(), 'preflightPositiveAndThreeNegativeCases': True,
    'hardwareGfx': 'gfx1100', 'staticNativeFiles': 34, 'nativeImportEdges': 174, 'byteDifferentNativeNames': 4,
    'sameVersionCandidateCompatibility': 'NOT CHECKED', 'freshRemoteClone': commit, 'sourceOverlay': False,
    'freshOfficialNugetPackages': 10, 'newOs': False, 'independentHumanReader': False,
    'vectorAddElements': 65539, 'vectorAddRepetitions': 3, 'affineAndMatmulEachElements': 4096,
    'actualNewTrace': True, 'actualNewPhotoRawValues': 301665, 'photoMaxAbs': photo['maxAbs'], 'photoManualInspection': True,
    'rawNativeApplicationScreenshots': 1, 'modificationTasksMapped': 27, 'minimumAcceptanceItemsMapped': 9,
    'historicalHashesVerified': history, 'readerPathsAndRelativeLinks': 'PASS', 'newPerformanceOr264TestsOrFourCaseReruns': False,
    'reviewStatus': 'READY_FOR_REVIEW_WITH_DECLARED_LIMITS', 'externalIssueClosed': False, 'productionAcceptance': False})

files = {p for p in out.rglob('*') if p.is_file() and p != out / 'manifest.json'}
files.update(docs)
files.update(root / name for name in ['03-正文预览.html', 'research/build-preview.py', 'research/build-issue2-audit.py',
    'research/capture-round7.py', 'research/check-round7.py', 'examples/MigraphxCompute/NativePreflight.cs',
    'examples/MigraphxCompute/Round2Tools.cs', 'examples/run-windows.ps1', 'examples/ValidationWorkbench/Program.cs',
    'examples/ValidationWorkbench/ValidationWorkbench.csproj'])
save(out / 'manifest.json', {'createdAt': dt.datetime.now().astimezone().isoformat(), 'revision': 'v10', 'baselineCommit': '4096421',
    'verifiedPublicExampleCommit': commit, 'screenshots': 'screenshots/manifest.json', 'acceptance': 'issue-2-requirements.json',
    'scope': 'Preflight and negative cases; fresh clone/package caches; actual C# window, core checks, trace and real-photo detection. Previous rounds preserved.',
    'files': [{'path': Path(os.path.relpath(p, root)).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(files)]})
assert (out / 'manifest.json').is_file() and (out / 'final-checks.json').is_file()
print('PASS: new executions, source/cache isolation, native screenshot, 36 requirement mappings, links and historical hashes:', history)
