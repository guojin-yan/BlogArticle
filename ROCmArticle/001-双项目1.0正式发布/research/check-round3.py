"""Check current claims against all reruns, including failed attempts and raw captures."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import datetime
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'research/validation/round3'
REPO = ROOT.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

commands = read(OUT / 'commands.json')
by_name = {c['label']: c for c in commands}
assert len(by_name) == len(commands)
for command in commands:
    assert sha(OUT / command['log']) == command['logSha256']
for name in ['core-verify', 'core-trace', 'signal-gpu-verify', 'signal-cpu-demo',
             'signal-hip-analyze', 'surface-smoke-hip', 'document-cpu-workflow-demo', 'video-real-media-gpu']:
    assert by_name[name]['exitCode'] == by_name[name]['expectedExit'] == 0, name
for name in ['surface-smoke', 'surface-smoke-model-retry', 'document-page-gpu',
             'document-page-gpu-path-alias', 'document-page-gpu-alias-fixed']:
    assert by_name[name]['exitCode'] != 0, name
for path in ['logs/surface-server-retry.log', 'results/document-gpu-alias-fixed/cli.log']:
    log = (OUT / path).read_text(encoding='utf-8-sig')
    assert '0xC0000005' in log and 'ProgramCompile' in log
for path in ['results/document-gpu/cli.log', 'results/document-gpu-path-alias/cli.log']:
    assert 'outside the source checkout' in (OUT / path).read_text(encoding='utf-8-sig')

surface = read(OUT / 'results/surface-smoke-hip.json')
assert surface['passed'] and surface['modelBatch'] is None
cpu, hip = [read(OUT / f'results/surface-{b}-batch.json') for b in ['cpu', 'hip']]
assert len(cpu['items']) == len(hip['items']) == 6
assert [i['defectPixels'] for i in cpu['items']] == [0, 1295, 1400, 0, 2695, 0]
for c, g in zip(cpu['items'], hip['items'], strict=True):
    assert c['sourceHash'] == g['sourceHash'] and c['defectPixels'] == g['defectPixels']
    cp = OUT / 'results/surface-cpu-report/evidence' / c['id'] / 'mask.png'
    gp = OUT / 'results/surface-hip-report/evidence' / g['id'] / 'mask.png'
    assert cp.read_bytes() == gp.read_bytes()

comparison = read(OUT / 'results/signal-comparison.json')
assert comparison['frames'] == 125 and comparison['psdValues'] == 64125
assert comparison['cpuNeedsReview'] == comparison['hipNeedsReview'] == 15
cpu, hip = [read(OUT / Path(comparison[b+'Report']).parent / 'result.json') for b in ['cpu', 'hip']]
assert cpu['inputSha256'] == hip['inputSha256'] and cpu['configSha256'] == hip['configSha256']
errors = []
for c, g in zip(cpu['frames'], hip['frames'], strict=True):
    assert c['decision'] == g['decision']
    for expected, actual in zip(c['spectrum']['psd'], g['spectrum']['psd'], strict=True):
        error = abs(actual - expected)
        assert error <= 1e-5 + 1e-4 * abs(expected)
        errors.append(error)
assert len(errors) == 64125 and max(errors) == comparison['maxAbs']

video = read(OUT / 'results/video-gpu/workflow-run.json')
assert video['framesProcessed'] == 20 and video['observations'] == 2
assert video['unreviewedEventPredictions'] == 0 and video['backend'] == 'MIGraphX GPU'
assert video['eventQualityMeasured'] is False and video['metrics'] is None
actual = read(OUT / 'results/video-gpu/analysis/result.json')
assert all(o['class'] == 'train' and o['frameIndex'] in [18, 19] for o in actual['observations'])
assert [o['pts'] for o in actual['observations']] == [110592, 116736]
assert 'hipErrorInvalidKernelFile' in (OUT / 'results/video-gpu/infer.stderr.txt').read_text(encoding='utf-8-sig')
document = read(OUT / 'logs/document-cpu-workflow-demo.log')
assert len(document['initialFindings']) == 3 and document['version'] == 3
assert document['reviewStatus'] == 'ApprovedByHuman' and 'Authored' in document['scope']
assert not list((OUT / 'results/document-gpu-alias-fixed').glob('recognized/ocr-evidence.json'))

tests = []
for path in sorted((OUT / 'test-results').glob('*.trx')):
    counters = ET.parse(path).find('.//{*}Counters').attrib
    assert counters['total'] == counters['passed'] and counters['failed'] == '0'
    tests.append(int(counters['total']))
assert sorted(tests) == [47, 65, 73, 79] and sum(tests) == 264
assert 'max_abs_error=0' in (OUT / 'logs/core-verify.log').read_text(encoding='utf-8-sig')
assert 'mul_add_relu_kernel' in (OUT / 'logs/core-trace.log').read_text(encoding='utf-8-sig')
for name in ['verify', 'trace']:
    page = (OUT / f'results/core-{name}-log-view.html').read_text(encoding='utf-8')
    import html
    assert html.escape((OUT / f'logs/core-{name}.log').read_text(encoding='utf-8-sig')) in page

screens = read(OUT / 'screenshots/manifest.json')
assert len(screens['files']) == 10
assert sum(p['status'] == 'VALID' for p in screens['files']) == 8
for shot in screens['files']:
    assert sha(OUT / shot['file']) == shot['sha256'] and shot['edited'] is False
    assert shot['format'] == 'JPEG'
    for evidence in shot['evidence']:
        assert (ROOT / evidence).is_file()

docs = [ROOT / name for name in ['03-正文.md', '05-上手与验证.md',
    'research/issue-2-截图与四应用复跑.md', 'research/validation/round3/README.md',
    'research/validation/round3/inputs/README.md']]
for path in docs:
    content = path.read_text(encoding='utf-8')
    assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)', content), path
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', content):
        parsed = urlsplit(link)
        if not parsed.scheme and parsed.path:
            assert (path.parent / unquote(parsed.path)).exists(), (path, link)
article = docs[0].read_text(encoding='utf-8')
assert 'ROOT CAUSE UNKNOWN' in article and '访问冲突' in article
assert '本轮四应用均已执行' in article and '本轮未重跑该照片' in article

# Never refresh the round2 manifest to hide historical edits. Verify the original
# manifest against its delivery commit, and every round2 raw file in this checkout.
old = read(ROOT / 'research/validation/round2/manifest.json')
historical = 0
for item in old['files']:
    path = ROOT / item['path']
    if item['path'].startswith('research/validation/round2/'):
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], item['path']
    else:
        git_path = path.relative_to(REPO).as_posix()
        data = subprocess.check_output(['git', 'show', 'a5aeb7d:'+git_path], cwd=REPO)
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], git_path
    historical += 1
result = {'checkedAt': datetime.datetime.now().astimezone().isoformat(), 'revision': 'v6',
    'testsPassed': 264, 'fourApplicationsExecuted': True, 'gpuCompileFailuresRetained': 2,
    'validBrowserScreenshots': 8, 'invalidLayoutCapturesRetained': 2,
    'signalPsdValuesChecked': len(errors), 'videoIncorrectPredictionsRetained': True,
    'historicalRound2HashEntriesVerified': historical, 'readerPathsPortable': True,
    'productionAcceptance': False, 'allIssue2AcceptanceMet': False}
(OUT / 'final-checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
