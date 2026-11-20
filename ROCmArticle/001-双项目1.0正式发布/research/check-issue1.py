"""Regress the first-round evidence and preserved assets after the v5 edits."""
from pathlib import Path
import gzip
import csv
import hashlib
import json
import math
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
VALIDATION = ROOT / 'research/validation'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


article = (ROOT / '03-正文.md').read_text(encoding='utf-8')
guide = (ROOT / '05-上手与验证.md').read_text(encoding='utf-8')
preview = (ROOT / '03-正文预览.html').read_text(encoding='utf-8')
before = read_json(VALIDATION / 'issue1-before.json')
assert article.splitlines()[0] == '# C# 也能玩转 AMD GPU：从自定义计算到 AI 推理，让你的项目也加速起来'
assert len(re.findall(r'^## ', article, re.M)) == 7
first_section = article.split('## 一、', 1)[1].split('## 二、', 1)[0]
assert '```' not in first_section
images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', article)
assert len(images) == 7
for asset in before['assets']:
    assert sha(ROOT / asset['path'].replace('\\', '/')).lower() == asset['sha256'].lower(), asset['path']
for tag in before['htmlImageTags']:
    assert tag in preview, tag
nuget = re.findall(r'https://www.nuget.org/packages/[^\s`|]+', article)
assert len(nuget) == len(set(nuget)) == 7
assert all(f'`{url}`' in article for url in nuget)
expected_start_here = [public_path for public_path in [
    'examples/HipVectorAdd/Program.cs', 'examples/MigraphxCompute/README.md', 'examples/README.md']]
links = re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', article)
assert links == ['https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/' + p for p in expected_start_here]
in_code_block = False
for line in article.splitlines():
    if line.startswith('```'):
        in_code_block = not in_code_block
    if not in_code_block:
        line = re.sub(r'(?<!!)\[[^\]]+\]\([^)]+\)', '', line)
        for url in re.findall(r'https://[^\s`|]+', line):
            assert f'`{url}`' in line, url

documents = [ROOT / name for name in ['03-正文.md', '05-上手与验证.md',
    'examples/README.md', 'examples/MigraphxCompute/README.md',
    'research/issue-1-修订说明.md', 'assets/evidence/README.md',
    'research/issue-2-修订说明.md', 'research/validation/round2/README.md']]
for document in documents[:4] + [ROOT / '03-正文预览.html', ROOT / 'examples/run-windows.ps1']:
    assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)',
        document.read_text(encoding='utf-8')), f'{document.name}: machine-specific path'
local_links = []
public_article_base = 'https://github.com/guojin-yan/BlogArticle/blob/main/ROCmArticle/001-双项目1.0正式发布/'
for target in re.findall(r'https://[^\s`|]+', article):
    if target.startswith(public_article_base):
        relative = unquote(target.removeprefix(public_article_base)).rstrip(')。.,')
        assert (ROOT / relative).exists(), target
        local_links.append(relative)
for document in documents:
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
        parsed = urlsplit(target)
        if parsed.scheme or not parsed.path:
            continue
        path = document.parent / unquote(parsed.path)
        assert path.exists(), f'{document.name}: {target}'
        local_links.append(target)

models = {'affine-relu.onnx': 'a576429543db2891d85d3ef11403feee445e51dfe540e8700029151e11a0357a',
    'matmul-relu.onnx': '9f001078ffbada6510b0c4e16300b7c448b8fd85e9bab5bb23696399daef9bf9'}
for name, expected in models.items():
    assert sha(ROOT / 'examples/MigraphxCompute' / name) == expected
affine = read_json(VALIDATION / 'issue1-affine-result.json')
assert any('mul_add_relu_kernel' in operation for operation in affine['traceOperations'])
benchmark = read_json(VALIDATION / 'issue1-yolox-benchmark.json')
assert benchmark['modelSha256'] == 'c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d'
assert benchmark['warmups'] == 10 and benchmark['repetitions'] == 30
for result in [affine, benchmark]:
    for key in ['hostError', 'deviceError', 'rawHostError', 'rawDeviceError', 'finalHostError', 'finalDeviceError']:
        assert result[key]['passed'] and result[key]['compared'] == result['outputElements']
for path, measurement in benchmark['measurements'].items():
    for boundary, values in measurement.items():
        samples = values['samplesMs']
        assert len(samples) == 30 and all(math.isfinite(x) and x > 0 for x in samples)
        ordered = sorted(samples)
        assert values['p50Ms'] == ordered[14] and values['p95Ms'] == ordered[28]
        assert math.isclose(values['serializedItemsPerSecond'], 30000 / sum(samples))
        measurement_text = guide  # historical table remains in the companion guide
        for metric in ['p50Ms', 'p95Ms']:
            assert f"{values[metric]:.3f}" in measurement_text, (path, boundary, metric)
    assert f"{measurement['endToEnd']['serializedItemsPerSecond']:.2f}" in guide
assert 'max_abs_error=0' in (VALIDATION / 'issue1-vectoradd-run.log').read_text(encoding='utf-8-sig')
signal = read_json(VALIDATION / 'issue1-signal-comparison.json')
assert signal['frames'] == 125 and signal['psdBinsCompared'] == 64125 and signal['allFrameDecisionsMatch']
assert signal['needsReview'] == {'cpu': 15, 'hip': 15}
pair_file = VALIDATION / 'issue1-signal-psd.csv.gz'
if pair_file.exists():
    with gzip.open(pair_file, 'rt', encoding='utf-8', newline='') as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 64125
    max_error = 0
    for row in rows:
        cpu, hip = float(row['cpuPsd']), float(row['hipPsd'])
        error = abs(cpu - hip)
        assert error <= 1e-5 + 1e-4 * abs(cpu)
        max_error = max(max_error, error)
    assert max_error == signal['maxPsdAbsoluteError']

result = {'date': '2026-11-20', 'revision': 'v5', 'titlePreserved': True,
    'mainSections': 7, 'nugetPackages': 7, 'originalHtmlImageTagsPreserved': 6,
    'originalAssetsUnchanged': len(before['assets']), 'articleImages': len(images),
    'checkedLocalLinks': len(local_links), 'localLinksResolve': True,
    'articleUrlsUseCodeExceptThreeStartHere': True, 'articleTextHyperlinks': 3, 'firstSectionHasNoCommands': True,
    'readerInstructionsHaveNoMachineSpecificPaths': True,
    'fixedModelHashesMatch': True, 'affineExecutionAndNumericalEvidence': True,
    'benchmarkRawSamplesAndTableMatch': True, 'benchmarkRawAndFinalOutputsPass': True,
    'signalNumericalPairs': len(rows) if pair_file.exists() else None,
    'visualReview': 'v5 generated HTML/source checks only. UI screenshot collection blocked by computer-use URL policy; earlier v4 review is historical.',
    'limits': 'No independent kernel profiler, clean cold start, process peak VRAM, other-platform rerun or industrial acceptance'}
(VALIDATION / 'round2/issue1-regression-checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(result, ensure_ascii=False))
