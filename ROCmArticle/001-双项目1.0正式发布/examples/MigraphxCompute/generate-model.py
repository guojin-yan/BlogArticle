"""Generate a fixed ONNX MatMul + ReLU fixture using only Python's stdlib."""
from pathlib import Path
import hashlib
import json
import struct


def varint(value):
    output = bytearray()
    while value >= 128:
        output.append((value & 127) | 128)
        value >>= 7
    output.append(value)
    return bytes(output)


def integer(field, value):
    return varint(field << 3) + varint(value)


def blob(field, value):
    if isinstance(value, str):
        value = value.encode('utf-8')
    return varint((field << 3) | 2) + varint(len(value)) + value


def info(name, shape):
    dimensions = b''.join(blob(1, integer(1, n)) for n in shape)
    tensor_type = integer(1, 1) + blob(2, dimensions)
    return blob(1, name) + blob(2, blob(1, tensor_type))


def node(op, inputs, output):
    return b''.join(blob(1, name) for name in inputs) + blob(2, output) + blob(4, op)


root = Path(__file__).resolve().parent
size = 64
weights = [((i * 7 + j * 3) % 19 - 9) / 32 for i in range(size) for j in range(size)]
raw_weights = struct.pack('<' + 'f' * len(weights), *weights)
tensor = integer(1, size) + integer(1, size) + integer(2, 1) + blob(8, 'weights') + blob(9, raw_weights)
graph = (blob(1, node('MatMul', ['input', 'weights'], 'product'))
         + blob(1, node('Relu', ['product'], 'output'))
         + blob(2, 'article_matmul_relu_64') + blob(5, tensor)
         + blob(11, info('input', [64, 64])) + blob(12, info('output', [64, 64])))
model = integer(1, 8) + blob(2, 'BlogArticle fixed numerical fixture') + blob(7, graph) + blob(8, integer(2, 13))
path = root / 'matmul-relu.onnx'
path.write_bytes(model)
print(json.dumps({'model': str(path), 'sha256': hashlib.sha256(model).hexdigest(),
                  'shape': [64, 64], 'opset': 13, 'kind': 'authored numerical fixture; not a trained business model'}))

# A pointwise computation avoids relying on the platform GEMM compiler for the
# first numerical check. Keep MatMul as a separately reproducible failing case.
def scalar(name, value):
    return integer(1, 1) + integer(2, 1) + blob(8, name) + blob(9, struct.pack('<f', value))


graph = (blob(1, node('Mul', ['input', 'scale'], 'scaled'))
         + blob(1, node('Add', ['scaled', 'bias'], 'shifted'))
         + blob(1, node('Relu', ['shifted'], 'output'))
         + blob(2, 'article_affine_relu_64')
         + blob(5, scalar('scale', 0.5)) + blob(5, scalar('bias', 0.25))
         + blob(11, info('input', [64, 64])) + blob(12, info('output', [64, 64])))
model = integer(1, 8) + blob(2, 'BlogArticle fixed numerical fixture') + blob(7, graph) + blob(8, integer(2, 13))
path = root / 'affine-relu.onnx'
path.write_bytes(model)
print(json.dumps({'model': str(path), 'sha256': hashlib.sha256(model).hexdigest(),
                  'shape': [64, 64], 'formula': 'max(0, input*0.5+0.25)', 'opset': 13}))
