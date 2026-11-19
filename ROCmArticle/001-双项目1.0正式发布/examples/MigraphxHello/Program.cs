using JYPPX.ROCm.MIGraphXSharp;

var environment = MIGraphXEnvironment.ProbeSystem();
if (!environment.ObjectsExecuted)
    throw new InvalidOperationException(string.Join("; ",
        environment.Diagnostics.Select(d => d.Message)));
string native = environment.LoadedPath!;

using var options = new MIGraphXOnnxOptions(native);
using var program = MIGraphXProgram.ParseOnnxBuffer(
    File.ReadAllBytes("identity.onnx"), options);
using var target = new MIGraphXTarget(native, "gpu");
using var compileOptions = new MIGraphXCompileOptions(native, offloadCopy: true);
program.Compile(target, compileOptions);

var shape = program.GetParameterShapes()["input"];
using var input = MIGraphXArgument.Create(native, shape, new[] { 1f, 2f, 3f, 4f });
using var parameters = new MIGraphXParameterMap(native);
parameters.Add("input", input);

using var outputs = program.Run(parameters);
Console.WriteLine(string.Join(", ", outputs[0].ToArray<float>()));
