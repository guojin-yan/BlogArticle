using JYPPX.ROCm.HipSharp;

using var runtime = new HipRuntime();
runtime.Initialize();

var versions = runtime.GetVersionInfo();
Console.WriteLine($"HIP Runtime: {versions.RuntimeVersion}");
Console.WriteLine($"HIP Driver:  {versions.DriverVersion}");

foreach (var device in runtime.GetDevices())
{
    Console.WriteLine(device);
}
