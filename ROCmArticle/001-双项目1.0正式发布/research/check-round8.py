"""Verify real console captures, command results, reader links and historical bytes."""
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
out = root / 'research/validation/round8'


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


captures = []
for mode in ['verify', 'trace']:
    command = read(out / mode / 'command.json')
    identity = read(out / mode / 'window-identity.json')
    capture = read(out / 'screenshots' / (mode + '-capture.json'))
    assert command['exitCode'] == 0 and command['hostName'] == 'ConsoleHost'
    assert command['processId'] == identity['Id'] == capture['processId']
    assert identity['ProcessName'] == 'pwsh' and identity['MainWindowTitle'] == capture['windowTitle']
    assert sha(root / 'research/run-round8-terminal.ps1') == command['runnerSha256']
    assert sha(out / mode / 'stdout-stderr.txt') == command['logSha256']
    assert sha(out / mode / 'transcript.txt') == command['transcriptSha256']
    assert sha(out / capture['file']) == capture['sha256'] and not capture['edited'] and not capture['terminalInputAutomated']
    assert dt.datetime.fromisoformat(capture['capturedAt']) > dt.datetime.fromisoformat(command['finished'])
    with Image.open(out / capture['file']) as im:
        assert im.format == 'PNG' and im.size == (capture['width'], capture['height'])
    result = read(out / mode / 'result.json')
    assert result['outputElements'] == 4096
    for key in ['hostError', 'deviceError', 'rawHostError', 'rawDeviceError', 'finalHostError', 'finalDeviceError']:
        error = result[key]
        assert error['passed'] and error['maxAbs'] == error['failedElements'] == error['nonFiniteElements'] == 0
    text = (out / mode / 'stdout-stderr.txt').read_text(encoding='utf-8-sig')
    if mode == 'verify':
        assert 'PASS: length=65539; repetitions=3; max_abs_error=0' in text and '1, 2, 3, 4' in text
    else:
        assert 'symbol_name=mul_add_relu_kernel' in text and 'BEGIN_MODEL_EXECUTION' in text and 'END_MODEL_EXECUTION' in text
    captures.append(capture)
save(out / 'screenshots/manifest.json', {'scope': 'Real PowerShell/ConsoleHost execution; read-only unedited full-window captures.',
    'gpu': 'AMD Radeon PRO W7900', 'gfx': 'gfx1100', 'os': 'Windows 11 build 26300', 'engine': 'MIGraphX2.18 / ROCm10.1',
    'sourceBaseline': '3126902', 'files': captures})


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(v for k, v in attrs if k in ['href', 'src'])


article = (root / '03-正文.md').read_text(encoding='utf-8-sig')
assert len(re.findall(r'^## ', article, re.M)) == 7 and len(re.findall(r'(?<!!)\[[^\]]+\]\([^)]+\)', article)) == 3
assert 'log-view.jpg' not in article and '日志查看页' not in article and '日志阅读页' not in article
for capture in captures:
    assert 'research/validation/round8/' + capture['file'] in article
for name in ['01-cover-v2.png', '02-api-architecture-v3.png', '03-surfacelab-v3.png', '04-signal-diagnostics-v3.png', '05-document-evidence-v3.png', '06-video-event-search-v3.png']:
    assert '(assets/' + name + ')' in article
docs = [root / name for name in ['03-正文.md', '05-上手与验证.md', 'research/issue-2-当前验收对照.md']]
docs += [out / 'README.md', root.parent / 'README.md']
for p in docs:
    text = p.read_text(encoding='utf-8-sig')
    assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)', text), p
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        u = urlsplit(link)
        if not u.scheme and u.path:
            target = (p.parent / unquote(u.path)).resolve()
            if target not in {(out / 'manifest.json').resolve(), (out / 'final-checks.json').resolve()}:
                assert target.exists(), (p, link)
preview = root / '03-正文预览.html'
parser = Links()
html = preview.read_text(encoding='utf-8-sig')
parser.feed(html)
assert 'v11，真实 PowerShell' in html and 'log-view.jpg' not in html
for link in parser.links:
    u = urlsplit(link)
    if not u.scheme and u.path:
        assert (preview.parent / unquote(u.path)).is_file(), link
requirements = read(out / 'issue-2-requirements.json')
assert len(requirements['records']) == 36 and requirements['revision'] == 'v11'

history = {}
for name, commit in [('round2', 'a5aeb7d'), ('round3', 'a4f73e4'), ('round4', '9727a7d'), ('round5', '1b33655'), ('round6', '4096421'), ('round7', '3126902')]:
    m = read(root / 'research/validation' / name / 'manifest.json')
    for item in m['files']:
        p = (root / item['path']).resolve()
        raw = p.read_bytes() if item['path'].startswith('research/validation/' + name + '/') else subprocess.check_output(['git', 'show', commit + ':' + p.relative_to(repo).as_posix()], cwd=repo)
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], p
    history[name] = len(m['files'])
save(out / 'final-checks.json', {'checkedAt': dt.datetime.now().astimezone().isoformat(), 'realConsoleHostRuns': 2,
    'rawFullWindowCaptures': 2, 'terminalKeyboardOrMouseInput': False, 'oldLogReplay': False, 'editedScreenshots': False,
    'vectorAddElements': 65539, 'vectorAddRepetitions': 3, 'affineComparedElementsPerRun': 4096, 'numericFailedElements': 0,
    'actualTraceKernel': 'mul_add_relu_kernel', 'articleContainsLogViewerScreenshot': False, 'readerLinksAndPaths': 'PASS',
    'historicalHashesVerified': history, 'newEnvironmentPerformance264OrFourCaseRerun': False})
files = {p for p in out.rglob('*') if p.is_file() and p != out / 'manifest.json'}
files.update(docs)
files.update(root / name for name in ['01-事实与来源.md', '02-配图方案.md', '04-编辑记录.md', '03-正文预览.html',
    'research/run-round8-terminal.ps1', 'research/capture-round8-window.py', 'research/check-round8.py',
    'research/build-preview.py', 'research/build-issue2-audit.py'])
save(out / 'manifest.json', {'createdAt': dt.datetime.now().astimezone().isoformat(), 'revision': 'v11', 'baselineCommit': '3126902',
    'scope': 'Actual PowerShell verification and trace window captures replacing article log-view screenshots.',
    'files': [{'path': Path(os.path.relpath(p, root)).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(files)]})
print('PASS: two actual terminal runs/captures, numerical checks, article links and historical hashes:', history)
