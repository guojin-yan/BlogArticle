"""Direct ctypes calls to the MIGraphX C API; no C# wrapper. Run in a child process."""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import time

p = argparse.ArgumentParser()
p.add_argument('--native', required=True)
p.add_argument('--model', required=True)
p.add_argument('--hip-root', default=os.environ.get('HIP_PATH'))
p.add_argument('--fast-math', type=int, default=0)
a = p.parse_args()
native, model = Path(a.native).resolve(), Path(a.model).resolve()
handles = [os.add_dll_directory(str(native.parent)), os.add_dll_directory(str(Path(a.hip_root) / 'bin'))]
os.environ['HIP_PATH'] = a.hip_root
os.environ['ROCM_PATH'] = a.hip_root
os.environ['PATH'] = str(native.parent) + os.pathsep + str(Path(a.hip_root) / 'bin') + os.pathsep + os.environ['PATH']
lib = C.CDLL(str(native))
P = C.c_void_p
def call(name, types, *values):
    f = getattr(lib, name)
    f.restype, f.argtypes = C.c_int, types
    print('CALL', name, flush=True)
    result = f(*values)
    print('RETURN', name, result, flush=True)
    if result:
        raise RuntimeError((name, result))

print(json.dumps({'nativeSha256': hashlib.sha256(native.read_bytes()).hexdigest(),
    'modelSha256': hashlib.sha256(model.read_bytes()).hexdigest(), 'fastMath': bool(a.fast_math),
    'offloadCopy': True, 'exhaustiveTune': False, 'entry': 'ctypes direct C ABI; no managed wrapper'}), flush=True)
options, program, target, compile = P(), P(), P(), P()
call('migraphx_onnx_options_create', [C.POINTER(P)], C.byref(options))
data = model.read_bytes()
buffer = C.create_string_buffer(data)
call('migraphx_parse_onnx_buffer', [C.POINTER(P), P, C.c_size_t, P], C.byref(program), buffer, len(data), options)
call('migraphx_target_create', [C.POINTER(P), C.c_char_p], C.byref(target), b'gpu')
call('migraphx_compile_options_create', [C.POINTER(P)], C.byref(compile))
for name, value in [('offload_copy', 1), ('fast_math', a.fast_math), ('exhaustive_tune_flag', 0)]:
    call('migraphx_compile_options_set_' + name, [P, C.c_bool], compile, bool(value))
start = time.perf_counter()
call('migraphx_program_compile', [P, P, P], program, target, compile)
print('COMPILE PASS', time.perf_counter() - start, flush=True)
for name, handle in [('program', program), ('compile_options', compile), ('target', target), ('onnx_options', options)]:
    call('migraphx_' + name + '_destroy', [P], handle)
