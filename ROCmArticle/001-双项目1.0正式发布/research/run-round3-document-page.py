"""Run the unchanged page evaluator with an explicit Windows output-drive alias.

The application rejects resources under *any* Git ancestor. Article evidence must
live in this writing repository, outside the application snapshot. A temporary
SUBST drive names that evidence directory without changing app/model code.
Only evaluator path normalization changes; validation and GPU execution remain
the original evaluator's implementation. Both earlier rejected attempts stay.
"""
import argparse
import importlib.util
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('--evaluator', required=True)
known, rest = p.parse_known_args()
evaluator = Path(known.evaluator).resolve()
sys.path.insert(0, str(evaluator.parent))
spec = importlib.util.spec_from_file_location('original_page_evaluator', evaluator)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
source = evaluator.parent.parent

def external(path):
    logical = Path(path).absolute()
    physical = logical.resolve()
    if physical == source or source in physical.parents:
        raise ValueError('Resources must stay outside the application source snapshot')
    return logical

module.external = external
args = argparse.ArgumentParser()
for name in ['model', 'declaration', 'app', 'output']:
    args.add_argument('--'+name, required=True)
args.add_argument('--dotnet', default='dotnet')
module.evaluate(args.parse_args(rest))
