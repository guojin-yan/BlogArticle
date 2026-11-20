"""Validate every randomized sample and summarize all five runs, without selection."""
from pathlib import Path
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent.parent
R2 = ROOT / 'research/validation/round2'
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

runs = [read(R2 / f'results/benchmark-{i}.json') for i in range(1, 6)]
paths = ['ortCpu', 'hostNew', 'hostFixedInputReuse', 'deviceCpuOps', 'fullHip']
for run in runs:
    assert run['warmups'] == 10 and run['repetitions'] == 30
    assert len(run['executionOrder']) == 30
    assert all(set(order) == set(paths) for order in run['executionOrder'])
    for key in paths:
        values = run['measurements'][key]
        samples = values['samplesMs']
        assert len(samples) == 30 and all(math.isfinite(x) and x > 0 for x in samples)
        assert sorted(samples)[14] == values['p50Ms'] and sorted(samples)[28] == values['p95Ms']
        assert run['ablationErrors'][key]['passed']
        assert run['ablationErrors'][key]['failedElements'] == run['ablationErrors'][key]['nonFiniteElements'] == 0
    for key in ['rawHostError', 'rawDeviceError', 'hostError', 'deviceError', 'finalHostError', 'finalDeviceError']:
        assert run[key]['passed'] and run[key]['failedElements'] == run[key]['nonFiniteElements'] == 0
for key in ['modelSha256', 'rawInputSha256', 'modelInputSha256']:
    assert len({run[key] for run in runs}) == 1

summary = {'date': '2026-11-20', 'rounds': 5, 'samplesPerPathPerRound': 30, 'paths': {},
    'environment': 'environment.json', 'scope': runs[0]['benchmarkScope'], 'cacheCold': 'NOT TESTED',
    'hostReuseLimitation': runs[0]['hostReuseLimitation'],
    'inputHashes': {key: runs[0][key] for key in ['modelSha256', 'rawInputSha256', 'modelInputSha256']}}
for key in paths:
    p50s = [run['measurements'][key]['p50Ms'] for run in runs]
    p95s = [run['measurements'][key]['p95Ms'] for run in runs]
    summary['paths'][key] = {'p50PerRoundMs': p50s, 'p95PerRoundMs': p95s,
        'medianOfRoundP50Ms': statistics.median(p50s), 'minRoundP50Ms': min(p50s), 'maxRoundP50Ms': max(p50s)}
summary['startup'] = {key: {'perRoundMs': [run[key] for run in runs], 'medianMs': statistics.median(run[key] for run in runs)}
    for key in ['cpuSessionMs', 'hostCompileMs', 'deviceCompileMs', 'hipCompileMs']}
summary['firstRunMs'] = {key: [run['firstRunMs'][key] for run in runs] for key in ['cpu', 'gpu', 'joint']}
summary['numerical'] = {'failedElements': 0, 'nonFiniteElements': 0,
    'maxRawAbsoluteError': max(run[key]['maxAbs'] for run in runs for key in ['rawHostError','rawDeviceError']),
    'maxRelative': max(run[key]['maxRelative'] for run in runs for key in ['rawHostError','rawDeviceError']),
    'relativeDenominatorFloor': 1e-12, 'atol': .001, 'rtol': .001,
    'explanation': 'Relative error divides by max(1e-12,abs(reference)); tiny reference values can yield a large ratio while satisfying the elementwise atol+rtol*abs(reference) criterion.'}
(R2 / 'round2-benchmark.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
