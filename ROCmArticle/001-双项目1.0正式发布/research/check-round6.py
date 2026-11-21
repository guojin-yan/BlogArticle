"""Audit the simple real-photo OCR demonstration and freeze its evidence index."""
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image

root = Path(__file__).resolve().parents[1]
repo = root.parents[1]
out = root / 'research/validation/round6'
assets = Path('E:/GitSpace/ROCm-CSharp-Projects/assets')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                          encoding='utf-8', newline='\n')


protocol = read(out / 'protocol.json')
batch = read(out / 'recognized/batch-evidence.json')
summary = read(out / 'summary.json')
command = read(out / 'command.json')
assert dt.datetime.fromisoformat(protocol['declaredAt']) < dt.datetime.fromisoformat(command['started'])
original = (out / protocol['originalImage']).resolve()
annotation = assets / 'document-evidence/hiertext-test-small-v1/test.jsonl.gz'
assert sha(original) == protocol['originalImageSha256'] == 'abf91176e175122c44f913e7109d017b819877df53194d37183527410f877d2c'
assert sha(annotation) == protocol['officialAnnotationSha256'] == '8a8f6cb6dd706b457b822634e9f19b7f51cc9813729d57401a3bb6ea45abd438'
labels = json.loads(gzip.decompress(annotation.read_bytes()))
page = next(p for p in labels['annotations'] if p['image_id'] == 'b533107ff30932da')
assert batch['manifestSha256'] == sha(out / 'lines.json')
assert batch['modelInstances'] == batch['recognizer']['programCompilations'] == 1
assert batch['recognizer'] == summary['backend']
assert len(protocol['samples']) == len(batch['lines']) == len(summary['records']) == 2
assert summary['exactLines'] == 2 and summary['allPredictionsRetained']
with Image.open(original) as source:
    source = source.convert('RGB')
    display = out / 'inputs/apple-soda-sign.png'
    assert sha(display) == protocol['displaySha256']
    with Image.open(display) as image:
        expected = source.crop(protocol['displayBounds'])
        assert image.mode == expected.mode and image.size == expected.size and image.tobytes() == expected.tobytes()
    for n, (sample, line, result) in enumerate(zip(protocol['samples'], batch['lines'], summary['records'], strict=True), 1):
        official = page['paragraphs'][sample['paragraphIndex']]['lines'][sample['lineIndex']]
        assert official['legible'] and not official['handwritten']
        assert official['text'] == sample['text'] == result['expected']
        assert official['vertices'] == sample['vertices']
        vertices = official['vertices']
        bounds = [math.floor(min(v[0] for v in vertices)), math.floor(min(v[1] for v in vertices)),
                  math.ceil(max(v[0] for v in vertices)), math.ceil(max(v[1] for v in vertices))]
        assert sample['bounds'] == bounds
        path = out / sample['image']
        with Image.open(path) as image:
            expected = source.crop(bounds)
            assert image.mode == expected.mode and image.size == expected.size and image.tobytes() == expected.tobytes()
        rec = line['recognition']
        assert rec == read(out / f'recognized/line-{n:03d}.json')
        assert sample['id'] == line['id'] == result['id']
        assert rec['inputSha256'] == sample['imageSha256'] == sha(path)
        assert rec['text'] == result['actual'] == sample['text'] and result['exactMatch']
        assert rec['confidence'] == result['confidence'] and rec['reference'] is None
        assert rec['backend'].startswith('MIGraphX GPU') and rec['device'] == 'AMD Radeon PRO W7900'
        for key in ['modelManifestSha256', 'graphSha256', 'dictionarySha256']:
            assert rec[key] == protocol[key] == batch['recognizer'][key]

for name, code, log in [('command.json', 0, 'gpu.log'), ('gpu-path-rejected-command.json', 1, 'gpu-path-rejected.log')]:
    run = read(out / name)
    assert run['exitCode'] == code and run['logSha256'] == sha(out / log)
    for path, digest in run['frozenFiles'].items():
        assert sha(path) == digest
assert 'Generated resources must stay outside the source checkout.' in (out / 'gpu-path-rejected.log').read_text(encoding='utf-8-sig')
assert 'hipErrorInvalidKernelFile' in (out / 'gpu.log').read_text(encoding='utf-8-sig')

shot = out / 'screenshots/03-document-simple-sign.jpg'
with Image.open(shot) as image:
    assert image.format == 'JPEG'
    width, height = image.size
save(out / 'screenshots/manifest.json', {
    'captureScope': 'Actual browser viewport; unedited original JPEG bytes.',
    'files': [{'file': shot.relative_to(out).as_posix(),
               'url': 'http://127.0.0.1:8766/research/validation/round6/evidence.html',
               'evidence': ['evidence.html', 'recognized/batch-evidence.json', 'summary.json', 'protocol.json'],
               'width': width, 'height': height, 'format': 'JPEG', 'bytes': shot.stat().st_size,
               'sha256': sha(shot), 'capturedAtFromFileMtime': dt.datetime.fromtimestamp(shot.stat().st_mtime).astimezone().isoformat(),
               'captureApi': 'cua_repl Tab.getScreenshot()', 'edited': False, 'status': 'VALID'}]})


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        self.paths.extend(v for k, v in attrs if k in ['href', 'src'])


for path in [root / '03-正文预览.html', out / 'evidence.html']:
    parser = Links()
    parser.feed(path.read_text(encoding='utf-8-sig'))
    for link in parser.paths:
        url = urlsplit(link)
        if not url.scheme and url.path:
            assert (path.parent / unquote(url.path)).is_file(), (path, link)

article = (root / '03-正文.md').read_text(encoding='utf-8-sig')
assert len(re.findall(r'^## ', article, re.M)) == 7
assert len(re.findall(r'(?<!!)\[[^\]]+\]\([^)]+\)', article)) == 3
assert len(re.findall(r'!\[[^\]]+\]\(research/validation/round5/', article)) == 3
assert len(re.findall(r'!\[[^\]]+\]\(research/validation/round6/', article)) == 1
for name in ['01-cover-v2.png', '02-api-architecture-v3.png', '03-surfacelab-v3.png',
             '04-signal-diagnostics-v3.png', '05-document-evidence-v3.png', '06-video-event-search-v3.png']:
    assert '(assets/' + name + ')' in article
preview = (root / '03-正文预览.html').read_text(encoding='utf-8-sig')
assert 'v9，简单真实招牌 OCR 演示' in preview and 'round6/screenshots/03-document-simple-sign.jpg' in preview
docs = [root / '03-正文.md', root / '05-上手与验证.md', root / 'examples/README.md',
        root / 'examples/MigraphxCompute/README.md', root / 'research/真实开源数据案例与截图.md',
        out / 'README.md', root.parent / 'README.md']
for path in docs:
    text = path.read_text(encoding='utf-8-sig')
    assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)', text), path
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        url = urlsplit(link)
        if not url.scheme and url.path:
            assert (path.parent / unquote(url.path)).exists(), (path, link)

history = {}
for round_name, commit in [('round2', 'a5aeb7d'), ('round3', 'a4f73e4'), ('round4', '9727a7d'), ('round5', '1b33655')]:
    manifest = read(root / 'research/validation' / round_name / 'manifest.json')
    for item in manifest['files']:
        path = (root / item['path']).resolve()
        if item['path'].startswith('research/validation/' + round_name + '/'):
            raw = path.read_bytes()
        else:
            raw = subprocess.check_output(['git', 'show', commit + ':' + path.relative_to(repo).as_posix()], cwd=repo)
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], path
    history[round_name] = len(manifest['files'])

save(out / 'final-checks.json', {
    'checkedAt': dt.datetime.now().astimezone().isoformat(), 'officialLinesAndPixelCropsVerified': 2,
    'actualCurrentGpuLines': 2, 'exactLines': 2, 'modelInstances': 1, 'programCompilations': 1,
    'selectionFrozenBeforeInference': True, 'allPredictionsRetained': True, 'newCpuTensorComparison': False,
    'nativeCandidateStderrRetained': True, 'initialPathRejectionRetained': True, 'rawBrowserScreenshots': 1,
    'historicalHashesVerified': history, 'readerPathsPortable': True, 'articleLinksAndStructure': 'PASS',
    'otherThreeCasesOr264TestsOrPerformanceRerun': False, 'productionAcceptance': False})

files = {p for p in out.rglob('*') if p.is_file() and p != out / 'manifest.json'}
files.update(root / name for name in ['01-事实与来源.md', '02-配图方案.md', '03-正文.md', '03-正文预览.html',
    '04-编辑记录.md', '05-上手与验证.md', 'research/真实开源数据案例与截图.md', 'research/build-preview.py',
    'research/run-round6-simple-ocr.py', 'research/check-round6.py'])
files.add(root.parent / 'README.md')
save(out / 'manifest.json', {
    'createdAt': dt.datetime.now().astimezone().isoformat(), 'revision': 'v9', 'baselineCommit': '1b33655',
    'applicationSourceCommit': '2f70b96267484b441fa726a3d496b8cc55d47219',
    'scope': 'Simple real sign illustration; two supplied official line crops, current C# MIGraphX GPU output and raw screenshot.',
    'screenshots': 'screenshots/manifest.json',
    'historicalManifests': 'round2/3/4/5 raw unchanged; old mutable files checked at a5aeb7d/a4f73e4/9727a7d/1b33655.',
    'files': [{'path': Path(os.path.relpath(p, root)).as_posix(), 'bytes': p.stat().st_size,
               'sha256': sha(p)} for p in sorted(files)]})
print('PASS: two official photo crops, actual GPU outputs, screenshot, reader links and historical hashes:', history)
