using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using JYPPX.ROCm.HipSharp;
using JYPPX.ROCm.HipSharp.Modules;
using JYPPX.ROCm.HipSharp.Memory;
using JYPPX.ROCm.HipSharp.Streams;
using JYPPX.ROCm.HipSharp.Rtc;
using JYPPX.ROCm.MIGraphXSharp;
using JYPPX.ROCm.MIGraphX.CSharp.API.HIP.Interop;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;

// A reproducible numerical check and serialized batch=1 pipeline benchmark.
// The CPU baseline is ONNX Runtime CPU, not a hand-written slow matrix loop.
try
{
    var started = Stopwatch.StartNew();
    var arguments = new Dictionary<string, string>();
    for (int i = 0; i < args.Length; i += 2)
    {
        if (i + 1 == args.Length || !args[i].StartsWith("--") || !arguments.TryAdd(args[i], args[i + 1]))
            throw new ArgumentException("Use --model PATH --output PATH --mode verify|benchmark|trace --arch gfx1100");
    }
    var allowed = new[] { "--model", "--output", "--mode", "--arch" };
    if (arguments.Keys.Any(key => !allowed.Contains(key))) throw new ArgumentException("Unknown option");
    string modelPath = Path.GetFullPath(arguments.GetValueOrDefault("--model", Path.Combine(AppContext.BaseDirectory, "affine-relu.onnx")));
    string resultPath = Path.GetFullPath(arguments.GetValueOrDefault("--output", "compute-result.json"));
    string mode = arguments.GetValueOrDefault("--mode", "verify");
    if (mode is not ("verify" or "benchmark" or "trace")) throw new ArgumentException("Unknown mode");
    string arch = arguments.GetValueOrDefault("--arch", "gfx1100");
    byte[] modelBytes = File.ReadAllBytes(modelPath);
    var probe = MIGraphXEnvironment.ProbeSystem();
    if (!probe.ObjectsExecuted) throw new InvalidOperationException(string.Join("; ", probe.Diagnostics.Select(d => d.Message)));
    string native = probe.LoadedPath!;
    using var hip = new HipRuntime();
    hip.Initialize();
    var before = hip.GetMemoryInfo();
    var clock = Stopwatch.StartNew();
    using var onnxOptions = new MIGraphXOnnxOptions(native);
    using var hostProgram = MIGraphXProgram.ParseOnnxBuffer(modelBytes, onnxOptions);
    double parseMs = clock.Elapsed.TotalMilliseconds;
    var shapes = hostProgram.GetParameterShapes();
    if (shapes.Count != 1) throw new NotSupportedException("This example requires one static float32 input.");
    string name = shapes.Keys.Single();
    var shape = shapes[name];
    int count = checked((int)shape.ElementCount);
    int[] dimensions = shape.Lengths.Select(n => checked((int)n)).ToArray();
    int channels = dimensions.Length == 4 ? dimensions[1] : 1;
    int spatial = count / channels;
    var raw = Enumerable.Range(0, count).Select(i => channels == 3 ? (float)((i * 13) % 256) : ((i * 13) % 101 - 50) / 64f).ToArray();
    var normalized = new float[count];
    void Preprocess()
    {
        for (int i = 0; i < count; i++) normalized[i] = raw[(i % spatial) * channels + i / spatial];
    }
    static void Postprocess(float[] values)
    {
        for (int i = 0; i < values.Length; i++) values[i] = Math.Max(0, values[i]);
    }
    Preprocess();
    byte[] rawBytes = Bytes(raw);
    clock.Restart();
    using var cpuOptions = new SessionOptions(); // CPU EP only; default ORT thread policy.
    using var cpu = new InferenceSession(modelBytes, cpuOptions);
    double cpuSessionMs = clock.Elapsed.TotalMilliseconds;
    var tensor = new DenseTensor<float>(normalized, dimensions);
    var cpuInputs = new[] { NamedOnnxValue.CreateFromTensor(name, tensor) };
    float[] CpuModel()
    {
        using var outputs = cpu.Run(cpuInputs);
        return outputs.Single().AsTensor<float>().ToArray();
    }
    float[] CpuEndToEnd()
    {
        Preprocess();
        var output = CpuModel();
        Postprocess(output);
        return output;
    }
    clock.Restart();
    var reference = CpuEndToEnd();
    double cpuFirstMs = clock.Elapsed.TotalMilliseconds;

    using var target = new MIGraphXTarget(native, "gpu");
    using var compileHost = new MIGraphXCompileOptions(native, offloadCopy: true, fastMath: false, exhaustiveTune: false);
    clock.Restart();
    hostProgram.Compile(target, compileHost);
    double hostCompileMs = clock.Elapsed.TotalMilliseconds;
    float[] HostModel()
    {
        using var input = MIGraphXArgument.Create(native, shape, normalized);
        using var parameters = new MIGraphXParameterMap(native);
        parameters.Add(name, input);
        using var output = hostProgram.Run(parameters);
        hip.Synchronize();
        return output[0].ToArray<float>();
    }
    float[] HostEndToEnd()
    {
        Preprocess();
        var output = HostModel();
        Postprocess(output);
        return output;
    }
    clock.Restart();
    var hostResult = HostEndToEnd();
    double hostFirstMs = clock.Elapsed.TotalMilliseconds;
    var hostError = Compare(reference, hostResult);
    double startupToFirstGpuMs = started.Elapsed.TotalMilliseconds;

    var traceNames = new List<string>();
    if (mode == "trace")
    {
        Console.WriteLine("BEGIN_COMPILED_GPU_PROGRAM");
        hostProgram.Print();
        using var input = MIGraphXArgument.Create(native, shape, normalized);
        using var parameters = new MIGraphXParameterMap(native);
        parameters.Add(name, input);
        Console.WriteLine("BEGIN_MODEL_EXECUTION");
        Console.Out.Flush();
        using var output = hostProgram.RunTrace(parameters, info => traceNames.Add(info.Name));
        hip.Synchronize();
        Console.WriteLine("END_MODEL_EXECUTION");
        Console.WriteLine("Trace operations: " + string.Join(", ", traceNames.Distinct()));
    }

    // Same ONNX, compiled for device inputs. Model weights remain initializers.
    clock.Restart();
    using var deviceProgram = MIGraphXProgram.ParseOnnxBuffer(modelBytes, onnxOptions);
    using var compileDevice = new MIGraphXCompileOptions(native, offloadCopy: false, fastMath: false, exhaustiveTune: false);
    deviceProgram.Compile(target, compileDevice);
    double deviceCompileMs = clock.Elapsed.TotalMilliseconds;
    if (deviceProgram.GetOutputShapes().Count != 1) throw new NotSupportedException("Expected one output");
    int outputCount = checked((int)deviceProgram.GetOutputShapes()[0].ElementCount);
    using var stream = hip.CreateStream();
    using var rawDevice = hip.Allocate((ulong)rawBytes.Length);
    using var inputDevice = hip.Allocate((ulong)rawBytes.Length);
    using var modelOutput = hip.Allocate(checked((ulong)outputCount * sizeof(float)));
    using var postOutput = hip.Allocate(checked((ulong)outputCount * sizeof(float)));
    var outputBytes = new byte[checked(outputCount * sizeof(float))];
    var rtc = new HipRtc();
    const string kernelSource = """
        extern "C" __global__ void Layout(const float* x,float* y,int n,int channels,int spatial)
        { int i=blockIdx.x*blockDim.x+threadIdx.x; if(i<n) y[i]=x[(i%spatial)*channels+i/spatial]; }
        extern "C" __global__ void Clamp(const float* x,float* y,int n)
        { int i=blockIdx.x*blockDim.x+threadIdx.x; if(i<n) y[i]=x[i]>0?x[i]:0; }
        """;
    using var rtcProgram = rtc.CreateProgram(kernelSource, "article-pipeline.hip");
    clock.Restart();
    var compilation = rtcProgram.Compile(new[] { "--offload-arch=" + arch, "-O2" });
    using var module = hip.LoadModule(compilation.GetCodeObject());
    double hipCompileMs = clock.Elapsed.TotalMilliseconds;
    var pre = module.GetKernel("Layout");
    var post = module.GetKernel("Clamp");
    var preArguments = new[] { HipKernelArgument.DevicePointer(rawDevice), HipKernelArgument.DevicePointer(inputDevice),
        HipKernelArgument.Scalar32(count), HipKernelArgument.Scalar32(channels), HipKernelArgument.Scalar32(spatial) };
    var postArguments = new[] { HipKernelArgument.DevicePointer(modelOutput), HipKernelArgument.DevicePointer(postOutput), HipKernelArgument.Scalar32(outputCount) };
    using var bindings = new DeviceBindings();
    var deviceInputs = new List<MIGraphXHipDeviceInput> { new(name, shape, inputDevice) };
    // offloadCopy=false may expose compiler-created output parameters as well.
    foreach (var parameter in deviceProgram.GetParameterShapes())
        if (parameter.Key != name)
        {
            var memory = hip.Allocate(checked((ulong)parameter.Value.ByteCount));
            bindings.Own(memory);
            deviceInputs.Add(new MIGraphXHipDeviceInput(parameter.Key, parameter.Value, memory));
        }
    var deviceOutputs = new[] { modelOutput };
    void DeviceModel()
    {
        using var run = deviceProgram.RunDeviceIntoAsync(deviceInputs, deviceOutputs, stream);
        run.Synchronize();
    }
    float[] DeviceEndToEnd()
    {
        rawDevice.CopyFromAsync(rawBytes, stream);
        pre.Launch(stream, new HipLaunchDimensions((uint)((count + 255L) / 256)), new HipLaunchDimensions(256), preArguments);
        using var run = deviceProgram.RunDeviceIntoAsync(deviceInputs, deviceOutputs, stream);
        post.Launch(stream, new HipLaunchDimensions((uint)((outputCount + 255L) / 256)), new HipLaunchDimensions(256), postArguments);
        postOutput.CopyToAsync(outputBytes, stream);
        run.Synchronize(); // includes postprocessing and D2H queued on the same stream
        var output = new float[outputCount];
        Buffer.BlockCopy(outputBytes, 0, output, 0, outputBytes.Length);
        return output;
    }
    clock.Restart();
    var deviceResult = DeviceEndToEnd();
    double deviceFirstMs = clock.Elapsed.TotalMilliseconds;
    var deviceError = Compare(reference, deviceResult);
    // A separate stream event interval surrounds only the compiled model path
    // and its required D2D output copies. No HIP layout/clamp kernels are inside.
    using var modelStart = hip.CreateEvent();
    using var modelEnd = hip.CreateEvent();
    modelStart.Record(stream);
    using (var activityRun = deviceProgram.RunDeviceIntoAsync(deviceInputs, deviceOutputs, stream))
    {
        modelEnd.Record(stream);
        activityRun.Synchronize();
        modelEnd.Synchronize();
    }
    float modelDeviceEventMs = HipEvent.ElapsedTime(modelStart, modelEnd);
    // The fixture additionally has a reference independent of either ONNX engine.
    object? fixtureReference = null;
    if (Path.GetFileName(modelPath) == "matmul-relu.onnx")
    {
        var expected = new float[64 * 64];
        for (int row = 0; row < 64; row++)
            for (int col = 0; col < 64; col++)
            {
                double value = 0;
                for (int k = 0; k < 64; k++) value += (double)normalized[row * 64 + k] * (((k * 7 + col * 3) % 19 - 9) / 32f);
                expected[row * 64 + col] = Math.Max(0, (float)value);
            }
        fixtureReference = new { cpu = Compare(expected, reference), gpu = Compare(expected, hostResult), joint = Compare(expected, deviceResult) };
    }
    else if (Path.GetFileName(modelPath) == "affine-relu.onnx")
    {
        var expected = normalized.Select(value => Math.Max(0, value * .5f + .25f)).ToArray();
        fixtureReference = new { cpu = Compare(expected, reference), gpu = Compare(expected, hostResult), joint = Compare(expected, deviceResult) };
    }
    int warmups = mode == "benchmark" ? 10 : 0;
    int repetitions = mode == "benchmark" ? 30 : 1;
    var measurements = new Dictionary<string, object>();
    if (mode == "benchmark")
    {
        measurements["ortCpu"] = new { endToEnd = Measure(() => { _ = CpuEndToEnd(); }, warmups, repetitions), warmModelApi = Measure(() => { _ = CpuModel(); }, warmups, repetitions) };
        measurements["migraphxHostIo"] = new { endToEnd = Measure(() => { _ = HostEndToEnd(); }, warmups, repetitions), warmModelApi = Measure(() => { _ = HostModel(); }, warmups, repetitions) };
        measurements["hipMigraphxDeviceIo"] = new { endToEnd = Measure(() => { _ = DeviceEndToEnd(); }, warmups, repetitions), warmModelApi = Measure(DeviceModel, warmups, repetitions) };
    }
    // Check unclamped model tensors too, so shared postprocessing cannot hide
    // errors in negative or near-zero model outputs. Keep this outside timing.
    Preprocess();
    var rawReference = CpuModel();
    var rawHostError = Compare(rawReference, HostModel());
    DeviceModel();
    var rawDeviceBytes = new byte[outputBytes.Length];
    modelOutput.CopyTo(rawDeviceBytes);
    var rawDeviceValues = new float[outputCount];
    Buffer.BlockCopy(rawDeviceBytes, 0, rawDeviceValues, 0, rawDeviceBytes.Length);
    var rawDeviceError = Compare(rawReference, rawDeviceValues);
    var finalHostError = Compare(reference, HostEndToEnd());
    var finalDeviceError = Compare(reference, DeviceEndToEnd());
    var after = hip.GetMemoryInfo();
    var result = new
    {
        date = DateTimeOffset.Now.ToString("O"), mode, model = Path.GetFileName(modelPath),
        modelSha256 = Hash(modelBytes), rawInputSha256 = Hash(rawBytes), modelInputSha256 = Hash(Bytes(normalized)),
        inputName = name, inputShape = dimensions, outputElements = outputCount,
        inputKind = channels == 3 ? "Deterministic synthetic HWC RGB float pixels in [0,255]; not an accuracy dataset" : "Fixed authored float matrix",
        preprocessing = "HWC to CHW layout; channels=1 is a copy", postprocessing = "elementwise max(value,0)",
        device = hip.GetDevices().First().ToString(), runtime = hip.GetVersionInfo().RuntimeVersion.ToString(), nativeLibrary = native,
        os = Environment.OSVersion.ToString(), logicalProcessors = Environment.ProcessorCount,
        cpuReference = "ONNX Runtime CPU 1.23.2; default CPU thread policy; sequential graph; no GPU provider",
        precision = "float32; MIGraphX fastMath=false, exhaustiveTune=false", batch = 1,
        parseMs, cpuSessionMs, hostCompileMs, deviceCompileMs, hipCompileMs, startupToFirstGpuMs,
        firstRunMs = new { cpu = cpuFirstMs, gpu = hostFirstMs, joint = deviceFirstMs },
        firstRunScope = "First run of each path in this process; disk/driver caches were not cleared; startupToFirstGpu also includes CPU setup/reference",
        tolerance = "abs(actual-reference)<=0.001+0.001*abs(reference), every finite element",
        hostError, deviceError, rawHostError, rawDeviceError, finalHostError, finalDeviceError, fixtureReference, referenceFirst16 = reference.Take(16), gpuFirst16 = hostResult.Take(16), jointFirst16 = deviceResult.Take(16),
        warmups, repetitions, measurements, traceOperations = traceNames,
        modelDeviceEventMs, gpuEvidenceScope = "Compiled GPU instruction trace plus device-only bindings, synchronized device output matching independent CPU, and a HIP stream event interval around the model+D2D copies; not an independent per-kernel profiler timeline",
        nativeEnvironment = new { disableMlir = Environment.GetEnvironmentVariable("MIGRAPHX_DISABLE_MLIR") },
        compiledDeviceParameters = deviceInputs.Select(value => new { value.Name, shape = value.Shape.Lengths }),
        memory = new { beforeFreeBytes = before.FreeBytes, afterFreeBytes = after.FreeBytes, totalBytes = after.TotalBytes,
            scope = "hipMemGetInfo whole-device snapshots, includes other processes; not per-process peak VRAM" },
        benchmarkScope = "Serialized batch=1. E2E begins with decoded host HWC floats and ends with postprocessed host float output. Decode, model parse/compile and reusable buffer allocation excluded. Joint includes H2D, HIP layout, model, D2D output copy, HIP clamp, D2H and stream sync. Host API includes its managed/native copies. warmModelApi has different I/O boundaries across paths and must not be used as a pure-kernel speedup comparison. No GPU clock/power isolation."
    };
    Directory.CreateDirectory(Path.GetDirectoryName(resultPath)!);
    File.WriteAllText(resultPath, JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine($"PASS: {Path.GetFileName(modelPath)}; outputElements={outputCount}; host and joint match CPU");
    Console.WriteLine("Evidence: " + resultPath);
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine(error);
    return 1;
}

static byte[] Bytes(float[] input)
{
    var bytes = new byte[checked(input.Length * sizeof(float))];
    Buffer.BlockCopy(input, 0, bytes, 0, bytes.Length);
    return bytes;
}
static string Hash(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
static object Compare(float[] expected, float[] actual)
{
    if (expected.Length != actual.Length) throw new InvalidOperationException("Output length mismatch");
    double maxAbs = 0, maxRelative = 0;
    for (int i = 0; i < expected.Length; i++)
    {
        double error = Math.Abs((double)actual[i] - expected[i]);
        if (!float.IsFinite(expected[i]) || !float.IsFinite(actual[i]) || error > .001 + .001 * Math.Abs(expected[i]))
            throw new InvalidOperationException($"Numerical mismatch at {i}: CPU={expected[i]}, actual={actual[i]}");
        maxAbs = Math.Max(maxAbs, error);
        maxRelative = Math.Max(maxRelative, error / Math.Max(1e-12, Math.Abs(expected[i])));
    }
    return new { compared = expected.Length, maxAbs, maxRelative, passed = true };
}
static object Measure(Action action, int warmups, int repetitions)
{
    for (int i = 0; i < warmups; i++) action();
    var samples = new double[repetitions];
    for (int i = 0; i < repetitions; i++)
    {
        var timer = Stopwatch.StartNew();
        action();
        samples[i] = timer.Elapsed.TotalMilliseconds;
    }
    var ordered = samples.Order().ToArray();
    return new { samplesMs = samples, p50Ms = ordered[(int)Math.Ceiling(.50 * repetitions) - 1],
        p95Ms = ordered[(int)Math.Ceiling(.95 * repetitions) - 1], serializedItemsPerSecond = 1000 * repetitions / samples.Sum(),
        quantileMethod = "nearest rank; repetitions=30; no outlier removal" };
}

sealed class DeviceBindings : IDisposable
{
    private readonly List<HipDeviceMemory> owned = new();
    public void Own(HipDeviceMemory memory) => owned.Add(memory);
    public void Dispose() { foreach (var memory in owned) memory.Dispose(); }
}
