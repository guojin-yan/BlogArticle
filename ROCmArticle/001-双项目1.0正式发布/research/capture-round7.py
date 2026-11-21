"""Capture one real command without overwriting previous attempts."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('name')
p.add_argument('--isolated', action='store_true')
p.add_argument('command', nargs=argparse.REMAINDER)
a = p.parse_args()
command = a.command[1:] if a.command[:1] == ['--'] else a.command
root = Path(__file__).resolve().parents[1]
out = root / 'research/validation/round7'
env = dict(os.environ)
env['NUGET_PACKAGES'] = str(root.parent / '.tools' / ('round7-fresh-nuget' if a.isolated else 'nuget'))
if a.isolated:
    env.update(DOTNET_CLI_HOME=str(root.parent / '.tools/round7-cli-home'),
               NUGET_HTTP_CACHE_PATH=str(root.parent / '.tools/round7-http-cache'),
               DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
start = dt.datetime.now().astimezone().isoformat()
source_files = [p for p in (root / 'examples').rglob('*') if p.suffix in ['.cs', '.csproj', '.ps1'] and not {'bin', 'obj'}.intersection(p.parts)]
source_hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
log = out / (a.name + '.log')
with log.open('xb') as stream:
    result = subprocess.run(command, env=env, cwd=root.parents[1], stdout=stream, stderr=subprocess.STDOUT, timeout=1800)
metadata = {'started': start, 'finished': dt.datetime.now().astimezone().isoformat(),
            'command': command, 'exitCode': result.returncode, 'cwd': str(root.parents[1]),
            'environment': {k: env[k] for k in ['NUGET_PACKAGES', 'DOTNET_CLI_HOME', 'NUGET_HTTP_CACHE_PATH'] if k in env},
            'log': log.name, 'logSha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'sourceFilesAtStart': source_hashes,
            'sourceFilesUnchangedDuringRun': all(hashlib.sha256((root / p).read_bytes()).hexdigest() == h for p, h in source_hashes.items())}
with (out / (a.name + '.command.json')).open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(metadata, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'name': a.name, 'exitCode': result.returncode, 'log': str(log)}, ensure_ascii=False))
raise SystemExit(result.returncode)
