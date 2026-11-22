"""Reconcile Issue #2 with current prose and existing raw evidence; no GPU execution."""
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parents[1]
repo = root.parents[1]
out = root / 'research/validation/round11'
baseline = 'b96f454'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path.relative_to(repo).as_posix()], cwd=repo)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.outside_code_urls = []
        self.code_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('pre', 'code'):
            self.code_depth += 1
        self.links.extend((tag, k, v) for k, v in attrs if k in ('href', 'src'))

    def handle_endtag(self, tag):
        if tag in ('pre', 'code'):
            self.code_depth -= 1

    def handle_data(self, data):
        if not self.code_depth:
            self.outside_code_urls.extend(re.findall(r'https?://\S+', data))


# Preserve the author's v13 explanation and all executable/visual content.
article = (root / '03-正文.md').read_text(encoding='utf-8-sig')
old = blob(baseline, root / '03-正文.md').decode('utf-8-sig')
expected = re.sub(r'\[(?:源码入口|运行说明|完整示例)\]\(https://[^)]+\)。', '', old)
assert article == expected, 'Only the three external Start Here anchors should change in the article.'
assert len(re.findall(r'^## ', article, re.M)) == 7
assert len(re.findall(r'^\| `JYPPX\.', article, re.M)) == 7
images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', article)
assert len(images) == 14 and all((root / p).is_file() for p in images)
assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)', article)
assert 'log-view.jpg' not in article

# Markdown render verifies named links, autolinks and naked website text together.
import sys
sys.path.insert(0, str(repo / 'ROCmArticle/.tools/python'))
import markdown

current_docs = list(root.glob('*.md')) + [root / 'assets/evidence/README.md']
current_docs += list((root / 'examples').rglob('README.md'))
current_docs += [root / 'research/真实开源数据案例与截图.md', root / 'research/issue-2-当前验收对照.md']
url_counts = {}
for path in current_docs:
    source = path.read_text(encoding='utf-8-sig')
    parser = Page()
    parser.feed(markdown.markdown(source, extensions=['tables', 'fenced_code']))
    assert not parser.outside_code_urls, (path, parser.outside_code_urls)
    assert not [(t, k, v) for t, k, v in parser.links if k == 'href' and urlsplit(v).scheme in ('http', 'https')], path
    url_counts[path.relative_to(root).as_posix()] = len(re.findall(r'https?://', source))
preview = root / '03-正文预览.html'
parser = Page()
page = preview.read_text(encoding='utf-8-sig')
parser.feed(page)
assert 'v14，网站地址代码展示' in page and not parser.outside_code_urls
assert not [(t, k, v) for t, k, v in parser.links if k == 'href' and urlsplit(v).scheme in ('http', 'https')]
for tag, key, value in parser.links:
    url = urlsplit(value)
    if not url.scheme and url.path:
        assert (preview.parent / unquote(url.path)).is_file(), value

# Compare every original checkbox and fingerprint its concrete evidence references.
source = read(out / 'issue-2-source.json')
requirements = read(out / 'issue-2-requirements.json')
original = [line[6:].strip() for line in source['body'].splitlines() if line.startswith('- [ ]')]
records = requirements['records']
assert len(records) == len(original) == 36 and requirements['revision'] == 'v14'
assert original == [r['originalRequirement'] for r in records]
assert sum(r['id'].startswith('DOD-') for r in records) == 9
assert next(r for r in records if r['id'] == 'P2-3')['status'] == 'AUTHOR_OVERRIDE'
evidence = []
for record in records:
    files = []
    for rel in record['evidence']:
        path = root / rel
        assert path.is_file(), (record['id'], rel)
        files.append({'path': rel, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())})
    evidence.append({'id': record['id'], 'originalCompared': True, 'declaredStatus': record['status'], 'files': files})

# Independently recompute all per-round quantiles, aggregates, startup and first calls.
r2 = root / 'research/validation/round2'
summary = read(r2 / 'round2-benchmark.json')
runs = [read(r2 / f'results/benchmark-{i}.json') for i in range(1, 6)]
paths = set(summary['paths'])
assert len(paths) == 5 and summary['rounds'] == 5
for run in runs:
    assert run['warmups'] == 10 and run['repetitions'] == 30
    assert len(run['executionOrder']) == 30 and all(set(order) == paths and len(order) == 5 for order in run['executionOrder'])
    assert len({tuple(order) for order in run['executionOrder']}) > 1
    for key, value in summary['inputHashes'].items():
        assert run[key] == value
    for error in list(run['ablationErrors'].values()) + [run[k] for k in ('rawHostError', 'rawDeviceError')]:
        assert error['passed'] and error['failedElements'] == error['nonFiniteElements'] == 0
        assert error['atol'] == error['rtol'] == .001 and error['compared'] == 301665
for key, value in summary['paths'].items():
    p50, p95 = [], []
    for run in runs:
        measurement = run['measurements'][key]
        samples = sorted(measurement['samplesMs'])
        assert len(samples) == 30 and all(math.isfinite(s) and s > 0 for s in samples)
        assert measurement['p50Ms'] == samples[14] and measurement['p95Ms'] == samples[28]
        p50.append(samples[14]); p95.append(samples[28])
    assert p50 == value['p50PerRoundMs'] and p95 == value['p95PerRoundMs']
    assert statistics.median(p50) == value['medianOfRoundP50Ms']
    assert min(p50) == value['minRoundP50Ms'] and max(p50) == value['maxRoundP50Ms']
    rounded = Decimal(str(statistics.median(p50))).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    assert str(rounded) in article
for key, value in summary['startup'].items():
    samples = [run[key] for run in runs]
    assert samples == value['perRoundMs'] and statistics.median(samples) == value['medianMs']
for key, values in summary['firstRunMs'].items():
    assert [run['firstRunMs'][key] for run in runs] == values
assert summary['cacheCold'] == 'NOT TESTED'
assert 'immutable input' in summary['hostReuseLimitation'] and summary['numerical']['maxRelative'] > 5000
environment = read(r2 / 'environment.json')
assert all(k in environment for k in ('windows', 'driver', 'cpu', 'architecture', 'cpuOrt', 'background', 'clockPower', 'dotnet'))

# Verify actual terminal identity, timing, original bytes and numerical output.
r8 = root / 'research/validation/round8'
captures = []
for mode in ('verify', 'trace'):
    command = read(r8 / mode / 'command.json')
    identity = read(r8 / mode / 'window-identity.json')
    capture = read(r8 / 'screenshots' / (mode + '-capture.json'))
    assert command['exitCode'] == 0 and command['hostName'] == 'ConsoleHost'
    assert command['processId'] == identity['Id'] == capture['processId']
    assert identity['ProcessName'] == 'pwsh' and identity['MainWindowTitle'] == capture['windowTitle']
    assert sha((root / 'research/run-round8-terminal.ps1').read_bytes()) == command['runnerSha256']
    for filename, key in [('stdout-stderr.txt', 'logSha256'), ('transcript.txt', 'transcriptSha256')]:
        assert sha((r8 / mode / filename).read_bytes()) == command[key]
    assert sha((r8 / capture['file']).read_bytes()) == capture['sha256']
    assert not capture['edited'] and not capture['terminalInputAutomated']
    assert dt.datetime.fromisoformat(capture['capturedAt']) > dt.datetime.fromisoformat(command['finished'])
    result = read(r8 / mode / 'result.json')
    assert result['outputElements'] == 4096
    for key in ('hostError', 'deviceError', 'rawHostError', 'rawDeviceError', 'finalHostError', 'finalDeviceError'):
        assert result[key]['passed'] and result[key]['maxAbs'] == result[key]['failedElements'] == result[key]['nonFiniteElements'] == 0
    log = (r8 / mode / 'stdout-stderr.txt').read_text(encoding='utf-8-sig')
    assert ('PASS: length=65539; repetitions=3; max_abs_error=0' in log and '1, 2, 3, 4' in log) if mode == 'verify' else ('symbol_name=mul_add_relu_kernel' in log and 'BEGIN_MODEL_EXECUTION' in log)
    captures.append({k: capture[k] for k in ('file', 'api', 'processId', 'capturedAt', 'sha256')})

# First-run scope, negative doctor checks, dependency closure and actual photo output.
r7 = root / 'research/validation/round7'
doctor = read(r7 / 'reader-doctor.json')
deps = read(r7 / 'reader-doctor.json.dependencies.json')
assert doctor['status'] == 'PASS_WITH_UNCHECKED_ITEMS' and not doctor['globalSettingsChanged']
assert len(deps['files']) == 34 and len(deps['edges']) == 174 and not deps['missing'] and not deps['unreadable']
assert len(deps['conflicts']) == 4 and deps['versionConflicts'] == 0
for name in ('doctor-missing-sdk.json', 'doctor-wrong-arch.json', 'doctor-version-conflict.json'):
    assert read(r7 / name)['status'] == 'FAIL'
isolation = read(r7 / 'reader-isolation-before.json')
assert all(v == 0 for v in isolation['paths'].values())
assert isolation['samePhysicalHost'] and isolation['systemDriverAndSdkReused']
assert not isolation['newOs'] and not isolation['independentHumanReader'] and not isolation['sourceOverlay']
identity = read(r7 / 'reader-source-identity.json')
assert identity['sourceCommit'].startswith('73569f7') and not identity['sourceOverlay'] and not identity['gitTrackedChanges']
for item in identity['sourceFiles']:
    assert sha(blob(identity['sourceCommit'], repo / item['path'])) == item['sha256']
workbench = read(r7 / 'reader-workbench/workbench.json')
assert workbench['completed'] and not workbench['allDisplayedChecksPassed']
photo = read(r7 / 'reader-photo/photo.json')
assert photo['rawCompared'] == 301665 and photo['failedElements'] == photo['nonFiniteElements'] == 0
assert len(photo['detections']) == 1 and sha((r7 / 'reader-photo/yolox-detections.png').read_bytes()) == photo['resultImageSha256']

# Public-data demos: recompute defects rather than hide failures behind a PASS.
r5 = root / 'research/validation/round5'
surface = read(r5 / 'surface-model-summary.json')['checks']
tn = sum(not x['officialAnomaly'] and x['machineDecision'] == 'Pass' for x in surface)
tp = sum(x['officialAnomaly'] and x['machineDecision'] == 'Defect' for x in surface)
fn = sum(x['officialAnomaly'] and x['machineDecision'] == 'Pass' for x in surface)
assert len(surface) == 12 and (tn, tp, fn) == (6, 3, 3)
signal = read(r5 / 'signal-comparison.json')
assert signal['passed'] and signal['windows'] == 45 and signal['psdValues'] == 5805
document = read(r5 / 'document-summary.json')
assert document['lineCount'] == 24 and document['exactLines'] == 5
video = read(r5 / 'video-gpu/analysis/result.json')
assert video['framesProcessed'] == 25 and len(video['observations']) == 109 and len(video['events']) == 12
easy = read(root / 'research/validation/round6/summary.json')
assert easy['lines'] == easy['exactLines'] == 2 and [x['actual'] for x in easy['records']] == ['APPLE', 'SODA']
for name, succeeded in [('native-forward-hipblaslt', False), ('native-mixed-hipblaslt', False), ('native-backslash-repeat', True), ('native-forward-rocblas', True)]:
    command = read(r5 / f'commands/{name}.json')
    assert (command['exitCode'] == 0) == succeeded
    assert sha((r5 / command['log']).read_bytes()) == command['logSha256']
for name in ('matmul-forward.json', 'matmul-backslash.json'):
    result = read(r5 / name)
    assert result['outputElements'] == 4096 and result['rawHostError']['passed'] and result['rawDeviceError']['passed']

# All historical manifest files stay byte-identical; mutable prose uses its old Git blob.
history = {}
for number, commit in [(2, 'a5aeb7d'), (3, 'a4f73e4'), (4, '9727a7d'), (5, '1b33655'), (6, '4096421'), (7, '3126902'), (8, '008d03a')]:
    directory = root / f'research/validation/round{number}'
    manifest = read(directory / 'manifest.json')
    for item in manifest['files']:
        path = (root / item['path']).resolve()
        raw = path.read_bytes() if path.is_relative_to(directory) else blob(commit, path)
        assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], (number, item['path'])
    history[f'round{number}'] = len(manifest['files'])
directories = [str(root / f'research/validation/round{i}') for i in range(2, 11)]
assert not subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', *directories], cwd=repo).strip()

report = {
    'checkedAt': dt.datetime.now().astimezone().isoformat(), 'revision': 'v14', 'baselineCommit': baseline,
    'status': 'EXISTING_EVIDENCE_CHECKS_PASS_WITH_DECLARED_LIMITS',
    'newGpuExecutions': 0, 'newScreenshots': 0,
    'currentWebsiteFormat': {'documentsChecked': url_counts, 'externalAnchors': 0, 'websiteTextOutsideCode': 0, 'previewExternalAnchors': 0},
    'preserved': {'v13ProductExplanations': True, 'chapters': 7, 'nugetPackages': 7, 'images': 14, 'commandsTablesUnchanged': True},
    'issue2': {'modificationTasks': 27, 'minimumAcceptanceItems': 9, 'states': {s: sum(r['status'] == s for r in records) for s in sorted({r['status'] for r in records})}, 'evidence': evidence},
    'benchmark': {'rounds': 5, 'paths': 5, 'samplesVerified': 750, 'allQuantilesAndStartupRecomputed': True, 'allNumericalChecksPassed': True, 'cacheCold': 'NOT TESTED'},
    'captureProvenance': captures,
    'readerValidation': {'dependencyFiles': 34, 'importEdges': 174, 'uncheckedCandidateGroups': 4, 'negativeChecksRetained': 3, 'emptyInitialCaches': True, 'publicCloneSourceHashes': len(identity['sourceFiles']), 'samePhysicalHost': True, 'independentHumanReader': False},
    'realDataCases': {'surfaceTN': tn, 'surfaceTP': tp, 'surfaceFN': fn, 'signalWindows': 45, 'psdValues': 5805, 'complexOcrExact': 5, 'complexOcrFailed': 19, 'easyOcr': ['APPLE', 'SODA'], 'videoFrames': 25, 'detections': 109, 'unreviewedCandidates': 12},
    'historicalManifestFilesVerified': history, 'round2Through10Changed': False,
    'limits': ['No new OS or independent human trial', 'Dynamic solver/all-model and byte-different DLL compatibility NOT CHECKED', 'No new cold-cache/profiler/process-peak/other-GPU/native-Linux/INT8 validation', 'Native internal root cause unknown; local path trigger and workaround evidenced', 'P2-3 clickable entry superseded by author code-only website requirement']
}
receipt_path = out / 'issue-2-reply-published.json'
if receipt_path.exists():
    receipt = read(receipt_path)
    assert sha((out / receipt['localBodyFile']).read_bytes()) == receipt['localBodyFileSha256']
    assert receipt['publishedBodyMatchesLocalAfterNewlineNormalization'] and receipt['issueStateAfterReply'] == 'open'
    report['publishedReply'] = {k: receipt[k] for k in ('commentId', 'commentUrl', 'createdAt', 'issueStateAfterReply', 'localBodyFileSha256')}
(out / 'final-checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print('PASS: code-only websites, 36 requirement mappings, 750 samples, capture provenance, first-run/case evidence and historical hashes.')
print(json.dumps({'states': report['issue2']['states'], 'historicalFiles': history}, ensure_ascii=False))
