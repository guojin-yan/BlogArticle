using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using JYPPX.ROCm.HipSharp;
using JYPPX.ROCm.HipSharp.Rtc;
using JYPPX.ROCm.MIGraphXSharp;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;

static class Round2Tools
{
    public static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
    public static void Write(string path, object value)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        File.WriteAllText(path, JsonSerializer.Serialize(value, new JsonSerializerOptions { WriteIndented = true }));
    }
    public static int Doctor(string output, string architecture)
    {
        var checks = new List<object>();
        int failures = 0;
        void Add(string name, string status, string detail, string next = "")
        {
            checks.Add(new { name, status, detail, next });
            if (status == "FAIL") failures++;
            Console.WriteLine($"{status,-12} {name}: {detail}");
        }
        void Check(string name, Action action, string next)
        {
            try { action(); Add(name, "PASS", "check completed"); }
            catch (Exception error) { Add(name, "FAIL", error.Message, next); }
        }
        Add("Process/RID", Environment.Is64BitProcess && OperatingSystem.IsWindows() ? "PASS" : "FAIL", RuntimeInformation.RuntimeIdentifier);
        Add(".NET", "PASS", RuntimeInformation.FrameworkDescription);
        var root = Environment.GetEnvironmentVariable("HIP_PATH");
        Add("HIP_PATH", Directory.Exists(root) ? "PASS" : "FAIL", root ?? "unset", "Use the ROCm 10.1 HIP root, containing bin and lib.");
        foreach (var file in new[] { "amdhip64*.dll", "hiprtc[0-9]*.dll", "amd_comgr.dll", "MIOpen.dll", "rocblas.dll", "libhipblaslt.dll" })
        {
            string bin = Path.Combine(root ?? "", "bin");
            string pattern = file.Replace("[0-9]", "");
            string[] matches = Directory.Exists(bin) ? Directory.GetFiles(bin, pattern).Where(p => !Path.GetFileName(p).Contains("builtins")).ToArray() : Array.Empty<string>();
            Add("File " + file, matches.Length > 0 ? "PASS" : "FAIL", "File presence only: " + string.Join("; ", matches), "Verify the complete matching ROCm installation; do not copy individual DLLs.");
        }
        foreach (var relative in new[] { "lib/llvm/amdgcn/bitcode", "bin/rocblas/library", "bin/hipblaslt/library/" + architecture })
            Add("Device data", Directory.Exists(Path.Combine(root ?? "", relative)) ? "PASS" : "FAIL", relative, "Check GPU architecture and matching device data.");
        Check("HIP device/runtime", () => { using var hip = new HipRuntime(); hip.Initialize(); Console.WriteLine(string.Join("; ", hip.GetDevices())); Console.WriteLine(hip.GetVersionInfo().RuntimeVersion); }, "Check driver, amdhip64 and HIP load diagnostics.");
        Check("HIPRTC compile", () => { var rtc = new HipRtc(); using var p = rtc.CreateProgram("extern \"C\" __global__ void Probe(float* x){if(threadIdx.x==0)x[0]=1;}", "doctor.hip"); _ = p.Compile(new[] { "--offload-arch=" + architecture, "-O2" }).GetCodeObject(); }, "Check hiprtc, COMGR, bitcode and actual gfx architecture.");
        string nativeDir = AppContext.BaseDirectory;
        try
        {
            var probe = MIGraphXEnvironment.ProbeSystem();
            Add("MIGraphX object probe", probe.ObjectsExecuted ? "PASS" : "FAIL", probe.LoadedPath ?? string.Join("; ", probe.Diagnostics.Select(d => d.Message)), "Inspect ProbeSystem diagnostics and plugin dependencies.");
            nativeDir = Path.GetDirectoryName(probe.LoadedPath ?? "") ?? AppContext.BaseDirectory;
        }
        catch (Exception error)
        {
            Add("MIGraphX object probe", "FAIL", error.ToString(), "Check the matching ROCm installation, native loader and plugin dependencies; then rerun the precheck.");
        }
        foreach (string file in new[] { "migraphx_c.dll", "migraphx.dll", "migraphx_gpu.dll" })
            Add("Plugin " + file, File.Exists(Path.Combine(nativeDir, file)) ? "PASS" : "FAIL", Path.Combine(nativeDir, file));
        foreach (string model in new[] { "affine-relu.onnx", "matmul-relu.onnx" })
            Add("Model " + model, File.Exists(Path.Combine(AppContext.BaseDirectory, model)) ? "PASS" : "FAIL", "Fixed fixture in application output directory");
        var modules = Process.GetCurrentProcess().Modules.Cast<ProcessModule>()
            .Where(m => new[] { "hip", "migraphx", "miopen", "rocblas", "comgr", "vcruntime" }.Any(s => m.ModuleName.Contains(s, StringComparison.OrdinalIgnoreCase)))
            .Select(m => new { m.ModuleName, m.FileName, version = m.FileVersionInfo.FileVersion, sha256 = Hash(m.FileName) }).ToArray();
        Add("Loaded native modules", "PASS", $"Recorded {modules.Length} modules with actual paths and SHA256; presence is not a full dependency proof.");
        NativePreflight.Hardware(root ?? "", architecture, output, Add);
        Check("Native dependency audit execution", () => NativePreflight.Dependencies(nativeDir, root ?? "", output, Add), "Inspect native import tables and matching ROCm installation.");
        NativePreflight.Inventory(Add);
        Add("All model/solver ABI compatibility", "NOT CHECKED", "Static dependencies and loaded-file hashes do not exercise every dynamic solver or certify every ONNX model.", "Run the fixed model and your own ONNX; retain native errors.");
        Add("Linux/other GPU", "SKIP", "Windows host only");
        Write(output, new { date = DateTimeOffset.Now, status = failures == 0 ? "PASS_WITH_UNCHECKED_ITEMS" : "FAIL", checks, modules, globalSettingsChanged = false });
        return failures == 0 ? 0 : 1;
    }
    public static int Cache(string modelPath, string output, string cacheRoot, string cacheKind)
    {
        if (cacheKind is not ("parsed" or "compiled")) throw new ArgumentException("cache-kind must be parsed or compiled");
        var startup = Stopwatch.StartNew();
        byte[] bytes = File.ReadAllBytes(modelPath);
        var probe = MIGraphXEnvironment.ProbeSystem();
        if (!probe.ObjectsExecuted) throw new InvalidOperationException("MIGraphX probe failed");
        string native = probe.LoadedPath!;
        using var hip = new HipRuntime(); hip.Initialize();
        using var options = new MIGraphXOnnxOptions(native);
        using var target = new MIGraphXTarget(native, "gpu");
        using var compile = new MIGraphXCompileOptions(native, offloadCopy: true, fastMath: false, exhaustiveTune: false);
        using var files = new MIGraphXFileOptions(native);
        var cache = new MIGraphXModelCache(Path.GetFullPath(cacheRoot));
        var metadata = new MIGraphXCacheMetadata(Hash(modelPath), "gpu", cacheKind + ";offloadCopy=true;fastMath=false;exhaustiveTune=false;gfx1100", "msgpack", Hash(native),
            apiIdentity: "MIGraphX/2.18/ROCm10.1;win-x64;gfx1100");
        double buildMs = 0;
        int builds = 0;
        MIGraphXProgram Build()
        {
            builds++; var timer = Stopwatch.StartNew();
            var program = MIGraphXProgram.ParseOnnxBuffer(bytes, options);
            try { if (cacheKind == "compiled") program.Compile(target, compile); buildMs = timer.Elapsed.TotalMilliseconds; return program; }
            catch { program.Dispose(); throw; }
        }
        var clock = Stopwatch.StartNew();
        using var result = cache.GetOrBuild(metadata, files, Build);
        double lookupMs = clock.Elapsed.TotalMilliseconds;
        // The public Load/GetOrBuild contract requires Compile before Run,
        // even when the serialized native graph was already compiled.
        clock.Restart();
        result.Program.Compile(target, compile);
        double loadedCompileMs = clock.Elapsed.TotalMilliseconds;
        var shape = result.Program.GetParameterShapes().Single();
        int[] dims = shape.Value.Lengths.Select(x => (int)x).ToArray();
        float[] data = Enumerable.Range(0, (int)shape.Value.ElementCount).Select(i => (float)((i * 13) % 256)).ToArray();
        using var arg = MIGraphXArgument.Create(native, shape.Value, data);
        using var map = new MIGraphXParameterMap(native); map.Add(shape.Key, arg);
        clock.Restart();
        using var values = result.Program.Run(map); hip.Synchronize();
        var actual = values[0].ToArray<float>();
        double firstMs = clock.Elapsed.TotalMilliseconds;
        using var cpu = new InferenceSession(bytes);
        var cpuInputs = new[] { NamedOnnxValue.CreateFromTensor(shape.Key, new DenseTensor<float>(data, dims)) };
        using var cpuValues = cpu.Run(cpuInputs);
        float[] expected = cpuValues.Single().AsTensor<float>().ToArray();
        if (expected.Length != actual.Length) throw new InvalidOperationException("GPU/CPU output lengths differ");
        int failures = expected.Zip(actual).Count(p => !float.IsFinite(p.First) || !float.IsFinite(p.Second) || Math.Abs(p.First - p.Second) > .001 + .001 * Math.Abs(p.First));
        double startupThroughReferenceMs = startup.Elapsed.TotalMilliseconds;
        var hot = new List<double>();
        for (int i = 0; i < 10; i++) { using var warm = result.Program.Run(map); hip.Synchronize(); }
        for (int i = 0; i < 30; i++) { clock.Restart(); using var warm = result.Program.Run(map); hip.Synchronize(); _ = warm[0].ToArray<float>(); hot.Add(clock.Elapsed.TotalMilliseconds); }
        Write(output, new { date = DateTimeOffset.Now, pid = Environment.ProcessId, modelSha256 = Hash(modelPath), nativeSha256 = Hash(native),
            cachePayloadKind = cacheKind, cacheKind = result.Kind.ToString(), previousLookup = result.PreviousLookup?.ToString(), builderCalls = builds, buildMs, lookupMs, loadedCompileMs,
            firstRunMs = firstMs, startupThroughReferenceMs, hotSamplesMs = hot,
            failedElements = failures, nonFiniteElements = actual.Count(x => !float.IsFinite(x)), passed = failures == 0,
            cacheCold = "NOT TESTED: no driver/disk cache clearing", scope = "Explicit model cache miss/hit and msgpack save/load; each invocation is a new process; host I/O immutable input." });
        Console.WriteLine($"CACHE {result.Kind}; payload={cacheKind}; builder={builds}; lookup={lookupMs:F3} ms; build={buildMs:F3} ms; loaded Compile={loadedCompileMs:F3} ms; first={firstMs:F3} ms; failures={failures}");
        return failures == 0 ? 0 : 1;
    }
}
