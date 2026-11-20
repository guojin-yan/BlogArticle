"""Check claims against archived raw data, including failures and scope limits."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
import re
import statistics

ROOT = Path(__file__).resolve().parent.parent
R2 = ROOT / 'research/validation/round2'
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def rounded_ms(value):
    return str(Decimal(str(value)).quantize(Decimal('.001'), rounding=ROUND_HALF_UP))

article = (ROOT / '03-正文.md').read_text(encoding='utf-8')
summary = read(R2 / 'round2-benchmark.json')
model_hash = 'c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d'
image_hash = '88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5'
assert sha(R2 / 'inputs/yolox_nano.onnx') == model_hash
assert sha(R2 / 'inputs/astronaut.png') == image_hash
runs = [read(R2 / f'results/benchmark-{i}.json') for i in range(1, 6)]
paths = list(summary['paths'])
assert len(paths) == 5
for i, run in enumerate(runs, 1):
    assert run['mode'] == 'ablation' and int(run['seed']) == 20261120 + i
    assert run['modelSha256'] == model_hash
    assert run['warmups'] == 10 and run['repetitions'] == 30
    assert read(R2 / f'results/exit-{i}.json')['exitCode'] == 0
    assert len(run['executionOrder']) == 30
    assert all(len(order) == 5 and set(order) == set(paths) for order in run['executionOrder'])
    for key in paths:
        values = run['measurements'][key]
        samples = values['samplesMs']
        assert len(samples) == 30 and all(math.isfinite(x) and x > 0 for x in samples)
        assert sorted(samples)[14] == values['p50Ms'] and sorted(samples)[28] == values['p95Ms']
        assert math.isclose(30000 / sum(samples), values['serializedItemsPerSecond'])
        error = run['ablationErrors'][key]
        assert error['passed'] and error['failedElements'] == error['nonFiniteElements'] == 0
        assert error['compared'] == 301665
for key in ['rawInputSha256', 'modelInputSha256']:
    assert len({run[key] for run in runs}) == 1
for key, values in summary['paths'].items():
    p50s = [run['measurements'][key]['p50Ms'] for run in runs]
    assert values['p50PerRoundMs'] == p50s
    assert values['medianOfRoundP50Ms'] == statistics.median(p50s)
    assert rounded_ms(statistics.median(p50s)) in article, key
    assert f"{rounded_ms(min(p50s))}–{rounded_ms(max(p50s))}" in article, key
for key in ['cpuSessionMs', 'hostCompileMs', 'deviceCompileMs', 'hipCompileMs']:
    assert summary['startup'][key]['medianMs'] == statistics.median(run[key] for run in runs)
for run in runs:
    for key in ['hostError', 'deviceError', 'rawHostError', 'rawDeviceError', 'finalHostError', 'finalDeviceError']:
        assert run[key]['passed'] and run[key]['compared'] == 301665
        assert run[key]['failedElements'] == run[key]['nonFiniteElements'] == 0

for folder in [R2 / 'results', R2 / 'results/photo-final']:
    photo = read(folder / 'photo.json')
    assert photo['modelSha256'] == model_hash and photo['imageSha256'] == image_hash
    assert photo['rawCompared'] == 301665 and photo['failedElements'] == photo['nonFiniteElements'] == 0
    assert photo['resultImageSha256'] == sha(folder / 'yolox-detections.png')
    assert len(photo['detections']) == 1
    assert photo['detections'][0]['Label'] == 'person'
    assert math.isclose(photo['detections'][0]['Score'], .9258799, abs_tol=1e-7)
assert sha(R2 / 'results/photo-final/input-photo.png') == image_hash
assert sha(R2 / 'results/photo-final/yolox-detections.png') == sha(R2 / 'results/yolox-detections.png')

cache = [read(R2 / f'results/cache-parsed-{name}.json') for name in ['miss', 'hit-process2', 'hit-process3']]
assert [c['cacheKind'] for c in cache] == ['Rebuilt', 'Hit', 'Hit']
assert [c['builderCalls'] for c in cache] == [1, 0, 0]
assert len({c['pid'] for c in cache}) == 3
for c in cache + [read(R2 / 'results/cache-parsed-final-hit.json')]:
    assert c['cachePayloadKind'] == 'parsed' and c['modelSha256'] == model_hash
    assert c['passed'] and c['failedElements'] == c['nonFiniteElements'] == 0
    assert len(c['hotSamplesMs']) == 30 and c['loadedCompileMs'] > 0
    assert c['cacheCold'].startswith('NOT TESTED')
for name in ['miss', 'hit-process2', 'hit-process3']:
    assert read(R2 / f'results/cache-parsed-{name}-exit.json')['exitCode'] == 0
    assert read(R2 / f'results/cache-v2-{name}-exit.json')['exitCode'] != 0
assert read(R2 / 'results/cache-parsed-final-hit-exit.json')['exitCode'] == 0
exits = {item['name']: item['exitCode'] for item in read(R2 / 'results/evidence-exits.json')}
assert exits['matmul-csharp'] == -1073741819 and exits['affine-native'] == 0
assert exits['matmul-native'] != 0 and exits['matmul-native-fast'] != 0
for name in ['matmul-native', 'matmul-native-fast']:
    log = (R2 / f'logs/{name}.log').read_text(encoding='utf-8-sig', errors='replace')
    assert 'CALL migraphx_program_compile' in log and 'access violation reading' in log
assert 'Input shapes have changed' in (R2 / 'logs/cache-v2-hit-process2.log').read_text(encoding='utf-8-sig')
for prefix in ['quickstart', 'quickstart-final']:
    doctor = read(R2 / f'results/{prefix}-doctor.json')
    assert doctor['status'] == 'PASS_WITH_UNCHECKED_ITEMS'
    assert any(c['status'] == 'NOT CHECKED' for c in doctor['checks'])
    assert not any(c['status'] == 'FAIL' for c in doctor['checks'])
    result = read(R2 / f'results/{prefix}-verify.json')
    assert result['outputElements'] == 4096 and result['hostError']['passed'] and result['deviceError']['passed']
    log = (R2 / f'logs/{prefix}-verify.log').read_text(encoding='utf-8-sig')
    assert 'max_abs_error=0' in log and '1, 2, 3, 4' in log
scope = read(R2 / 'results/quickstart-scope.json')
assert scope['samePhysicalHost'] and not scope['newOs'] and not scope['independentHumanReader']
assert read(R2 / 'results/doctor-missing-sdk-exit.json')['exitCode'] != 0
negative = read(R2 / 'results/doctor-missing-sdk-fixed.json')
assert negative['status'] == 'FAIL'
assert read(R2 / 'results/doctor-missing-sdk-fixed-exit.json')['exitCode'] != 0
assert any(c['status'] == 'FAIL' and c['next'] for c in negative['checks'])
assert any(c['name'] == 'MIGraphX object probe' and c['status'] == 'FAIL' for c in negative['checks'])
assert read(R2 / 'results/doctor-fixed-positive.json')['status'] == 'PASS_WITH_UNCHECKED_ITEMS'
recorded_hash = read(R2 / 'results/source-native-hashes.json')[0]['Hash'].lower()
assert sha(R2 / 'sources/Program-benchmark.cs') == recorded_hash
current = (ROOT / 'examples/MigraphxCompute/Program.cs').read_bytes().decode('utf-8')
recovered = current.replace(', "--cache-kind"', '').replace('arguments["--cache"], arguments.GetValueOrDefault("--cache-kind", "parsed")', 'arguments["--cache"]')
assert hashlib.sha256(recovered.encode()).hexdigest() == recorded_hash

docs = [ROOT / p for p in ['03-正文.md', '05-上手与验证.md', 'examples/README.md',
    'examples/MigraphxCompute/README.md', 'research/issue-2-修订说明.md', 'research/validation/round2/README.md',
    'research/validation/round2/inputs/README.md']]
for document in docs:
    text = document.read_text(encoding='utf-8')
    assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)', text), document
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        parsed = urlsplit(target)
        if not parsed.scheme and parsed.path:
            assert (document.parent / unquote(parsed.path)).exists(), (document, target)
class ImageCheck(HTMLParser):
    def __init__(self, base):
        super().__init__(); self.base = base; self.count = 0
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.count += 1
            src = dict(attrs)['src']
            assert urlsplit(src).scheme or (self.base / unquote(src)).is_file(), src
for page in [ROOT / '03-正文预览.html', R2 / 'results/detection-report.html', R2 / 'results/photo-final/detection-report.html']:
    parser = ImageCheck(page.parent); parser.feed(page.read_text(encoding='utf-8'))
    assert parser.count == (7 if page.name == '03-正文预览.html' else 2)
assert not list((R2 / 'screenshots/raw').glob('*.png'))
assert 'NOT CAPTURED' in (R2 / 'screenshots/raw/README.md').read_text(encoding='utf-8')
assert 'ROOT CAUSE UNKNOWN' in article and 'cache-cold NOT TESTED' in article
result = {'date': '2026-11-20', 'revision': 'v5', 'fiveIndependentBenchmarkRounds': True,
    'timedSamples': 750, 'randomOrderAndQuantilesChecked': True, 'photoInputsAndActualPngHashesMatch': True,
    'parsedCacheMissAndTwoProcessHits': True, 'cacheFailuresRetained': True, 'matmulFailureRetained': True,
    'quickstartInitialAndFinalNumericalChecks': True, 'doctorMissingSdkWritesStructuredFailure': True,
    'benchmarkSourceHashMatchesRecordedRun': True,
    'linksAndHtmlImagesResolve': True, 'readerPathsPortable': True,
    'screenshots': 'BLOCKED / NOT CAPTURED', 'fourApplications': 'NOT RE-RUN', 'allIssue2AcceptanceMet': False}
(R2 / 'final-checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
