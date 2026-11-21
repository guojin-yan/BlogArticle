"""Run the unchanged official-label evaluator, preserving the SUBST output alias."""
import argparse, importlib.util, sys
from pathlib import Path
p=argparse.ArgumentParser()
for name in ['evaluator','model','manifest','app','output']:p.add_argument('--'+name,required=True)
a=p.parse_args();evaluator=Path(a.evaluator)
sys.path.insert(0,str(evaluator.parent))
spec=importlib.util.spec_from_file_location('hiertext',evaluator)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=evaluator.parent.parent.resolve()
def external(path):
    logical=Path(path).absolute();physical=logical.resolve()
    if physical==source or source in physical.parents:raise ValueError('Output inside application source')
    return logical
module.external=external
module.evaluate(argparse.Namespace(model=a.model,manifest=a.manifest,app=a.app,output=a.output,dotnet='dotnet',audit_only=False))
