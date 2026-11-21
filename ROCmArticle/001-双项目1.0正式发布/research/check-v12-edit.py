"""Check editorial invariants and existing capture provenance; never run GPU work."""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parents[1]
repo = root.parents[1]
out = root / 'research/validation/round9'
baseline = '008d03afa4ef0bd351318196c27491a4d68cdef7'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def previous(path):
    return subprocess.check_output(['git', 'show', baseline + ':' + path.relative_to(repo).as_posix()], cwd=repo)


def han_count(text):
    return len(re.findall(r'[\u4e00-\u9fff]', re.sub(r'```.*?```', '', text, flags=re.S)))


article_path = root / '03-正文.md'
old = previous(article_path).decode('utf-8-sig')
article = article_path.read_text(encoding='utf-8-sig')
assert old.splitlines()[0] == article.splitlines()[0]
assert re.findall(r'^## .*$', old, re.M) == re.findall(r'^## .*$', article, re.M)
images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', article)
assert images == re.findall(r'!\[[^\]]*\]\(([^)]+)\)', old) and len(images) == 14
assert re.findall(r'```powershell\n(.*?)```', article, re.S) == re.findall(r'```powershell\n(.*?)```', old, re.S)
assert re.findall(r'^\|.*$', article, re.M) == re.findall(r'^\|.*$', old, re.M)
assert len(re.findall(r'(?<!!)\[[^\]]+\]\([^)]+\)', article)) == 3
assert len(re.findall(r'^\| `JYPPX\.', article, re.M)) == 7
assert len(re.findall(r'^## ', article, re.M)) == 7
assert 'log-view.jpg' not in article
assert not re.search(r'(?i)(\b[a-z]:[\\/]|file://|/home/|/mnt/[a-z]/|/Users/)', article)
for link in images:
    assert (root / link).is_file(), link
for path in re.findall(r'https://github.com/guojin-yan/BlogArticle/blob/main/([^\s`)]+)', article):
    assert (repo / unquote(path)).is_file(), path

captures = []
evidence = root / 'research/validation/round8'
for mode in ['verify', 'trace']:
    command = read(evidence / mode / 'command.json')
    identity = read(evidence / mode / 'window-identity.json')
    capture = read(evidence / 'screenshots' / (mode + '-capture.json'))
    assert command['exitCode'] == 0 and command['hostName'] == 'ConsoleHost'
    assert command['processId'] == identity['Id'] == capture['processId']
    assert identity['ProcessName'] == 'pwsh' and identity['MainWindowTitle'] == capture['windowTitle']
    assert digest((root / 'research/run-round8-terminal.ps1').read_bytes()) == command['runnerSha256']
    for filename, key in [('stdout-stderr.txt', 'logSha256'), ('transcript.txt', 'transcriptSha256')]:
        assert digest((evidence / mode / filename).read_bytes()) == command[key]
    assert digest((evidence / capture['file']).read_bytes()) == capture['sha256']
    assert not capture['edited'] and not capture['terminalInputAutomated']
    assert dt.datetime.fromisoformat(capture['capturedAt']) > dt.datetime.fromisoformat(command['finished'])
    result = read(evidence / mode / 'result.json')
    assert result['outputElements'] == 4096
    for key in ['hostError', 'deviceError', 'rawHostError', 'rawDeviceError', 'finalHostError', 'finalDeviceError']:
        error = result[key]
        assert error['passed'] and error['maxAbs'] == error['failedElements'] == error['nonFiniteElements'] == 0
    text = (evidence / mode / 'stdout-stderr.txt').read_text(encoding='utf-8-sig')
    if mode == 'verify':
        assert 'PASS: length=65539; repetitions=3; max_abs_error=0' in text and '1, 2, 3, 4' in text
    else:
        assert 'symbol_name=mul_add_relu_kernel' in text and 'BEGIN_MODEL_EXECUTION' in text and 'END_MODEL_EXECUTION' in text
    captures.append({key: capture[key] for key in ['file', 'api', 'processId', 'capturedAt', 'sha256']})

# Historical evidence must remain untouched. Mutable article files are read at the old commit.
manifest = read(evidence / 'manifest.json')
for item in manifest['files']:
    path = (root / item['path']).resolve()
    raw = path.read_bytes() if path.is_relative_to(evidence) else previous(path)
    assert len(raw) == item['bytes'] and digest(raw) == item['sha256'], item['path']
historical_dirs = [root / ('research/validation/round' + str(i)) for i in range(2, 9)]
changed = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', *[str(p) for p in historical_dirs]], cwd=repo).decode().strip()
assert not changed, changed


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(v for k, v in attrs if k in ['href', 'src'])


preview = root / '03-正文预览.html'
page = preview.read_text(encoding='utf-8-sig')
assert 'v12' in page and 'log-view.jpg' not in page
parser = Links()
parser.feed(page)
for link in parser.links:
    url = urlsplit(link)
    if not url.scheme and url.path:
        assert (preview.parent / unquote(url.path)).is_file(), link
for path in [root.parent / 'README.md', out / 'README.md', root / 'research/issue-2-当前验收对照.md']:
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
        url = urlsplit(link)
        if not url.scheme and url.path and url.path != 'editorial-checks.json':
            assert (path.parent / unquote(url.path)).exists(), (path.name, link)
requirements = read(out / 'issue-2-requirements.json')
assert requirements['revision'] == 'v12' and len(requirements['records']) == 36

report = {'checkedAt': dt.datetime.now().astimezone().isoformat(), 'revision': 'v12', 'baselineCommit': baseline,
    'scope': 'Editorial revision and verification of existing round8 evidence; no new GPU run or screenshot.',
    'newGpuExecutions': 0, 'newScreenshots': 0,
    'chineseCharactersOutsideFencedCode': {'before': han_count(old), 'after': han_count(article),
        'reductionPercent': round((1 - han_count(article) / han_count(old)) * 100, 1)},
    'preserved': {'title': True, 'chapterHeadings': 7, 'nugetRows': 7, 'imageReferencesInOrder': 14,
        'powershellBlocksUnchanged': True, 'tableRowsUnchanged': True, 'namedStartHereLinks': 3},
    'captureProvenanceVerified': captures, 'round8ManifestFilesVerified': len(manifest['files']),
    'round2Through8TrackedEvidenceChanged': False, 'readerLinksAndPaths': 'PASS', 'previewLinks': 'PASS',
    'issue2Requirements': 36}
(out / 'editorial-checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
