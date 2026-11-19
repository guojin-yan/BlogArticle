using System.Globalization;
using System.Text.RegularExpressions;
using JYPPX.ROCm.HipSharp;
using JYPPX.ROCm.HipSharp.Modules;
using JYPPX.ROCm.HipSharp.Rtc;

// Based on the project's Apache-2.0 HipRtcVectorAdd tutorial; this consumer
// references the published packages and adds a fixed CPU comparison.
if (args.Length != 2 || args[0] != "--arch" ||
    !Regex.IsMatch(args[1], "^gfx[0-9a-f]+$", RegexOptions.CultureInvariant))
{
    Console.Error.WriteLine("Usage: dotnet run -c Release -- --arch gfx1100");
    return 2;
}

const int length = 65_539; // Deliberately not a multiple of the block size.
const int repetitions = 3;
const double absoluteTolerance = 1e-6;
const uint blockSize = 256;
const string source = """
    extern "C" __global__ void VectorAdd(const float* a, const float* b,
                                         float* c, int length)
    {
        int i = (int)(blockIdx.x * blockDim.x + threadIdx.x);
        if (i < length) c[i] = a[i] + b[i];
    }
    """;

try
{
    using var runtime = new HipRuntime();
    runtime.Initialize();
    Console.WriteLine("Device: " + runtime.GetDevices().First());
    Console.WriteLine("HIP Runtime: " + runtime.GetVersionInfo().RuntimeVersion);

    var rtc = new HipRtc();
    using var program = rtc.CreateProgram(source, "article-vector-add.hip");
    var compilation = program.Compile(new[] { "--offload-arch=" + args[1], "-O2" });
    using var module = runtime.LoadModule(compilation.GetCodeObject());
    var kernel = module.GetKernel("VectorAdd");

    var a = new float[length];
    var b = new float[length];
    var sentinel = new float[length];
    Array.Fill(sentinel, float.NaN);
    for (int i = 0; i < length; i++)
    {
        a[i] = (i % 97 - 48) * 0.25f;
        b[i] = (i % 31 - 15) * 0.5f;
    }

    static byte[] Bytes(float[] values)
    {
        var bytes = new byte[checked(values.Length * sizeof(float))];
        Buffer.BlockCopy(values, 0, bytes, 0, bytes.Length);
        return bytes;
    }

    ulong byteLength = checked((ulong)length * sizeof(float));
    using var deviceA = runtime.Allocate(byteLength);
    using var deviceB = runtime.Allocate(byteLength);
    using var deviceC = runtime.Allocate(byteLength);
    deviceA.CopyFrom(Bytes(a));
    deviceB.CopyFrom(Bytes(b));
    var outputBytes = new byte[checked(length * sizeof(float))];
    var actual = new float[length];
    uint gridSize = checked((uint)((length + (long)blockSize - 1) / blockSize));
    var arguments = new List<HipKernelArgument>
    {
        HipKernelArgument.DevicePointer(deviceA),
        HipKernelArgument.DevicePointer(deviceB),
        HipKernelArgument.DevicePointer(deviceC),
        HipKernelArgument.Scalar32(length),
    };

    double maxAbsoluteError = 0;
    for (int repeat = 0; repeat < repetitions; repeat++)
    {
        // A missing write must fail the comparison, including on repeat runs.
        deviceC.CopyFrom(Bytes(sentinel));
        kernel.Launch(new HipLaunchDimensions(gridSize),
            new HipLaunchDimensions(blockSize), arguments);
        runtime.Synchronize();
        deviceC.CopyTo(outputBytes);
        Buffer.BlockCopy(outputBytes, 0, actual, 0, outputBytes.Length);
        for (int i = 0; i < length; i++)
        {
            float expected = a[i] + b[i];
            double error = Math.Abs((double)actual[i] - expected);
            if (!float.IsFinite(actual[i]) || error > absoluteTolerance)
                throw new InvalidOperationException(
                    $"Mismatch: repeat={repeat}; index={i}; expected={expected}; actual={actual[i]}");
            maxAbsoluteError = Math.Max(maxAbsoluteError, error);
        }
    }

    Console.WriteLine($"Kernel: VectorAdd; arch={args[1]}; blocks={gridSize}; threads={blockSize}");
    Console.WriteLine("Code SHA-256: " + compilation.CodeSha256);
    Console.WriteLine($"PASS: length={length}; repetitions={repetitions}; " +
        "max_abs_error=" + maxAbsoluteError.ToString("G17", CultureInfo.InvariantCulture) +
        "; atol=" + absoluteTolerance.ToString("G", CultureInfo.InvariantCulture));
    Console.WriteLine("Evidence: HIPRTC compile, HIP kernel launch, device synchronization, D2H, CPU comparison.");
    Console.WriteLine("No profiler trace or performance comparison was collected.");
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine(error);
    return 1;
}
