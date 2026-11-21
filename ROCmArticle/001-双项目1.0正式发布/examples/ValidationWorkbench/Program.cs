using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;

namespace ValidationWorkbench;

static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        if (args.Length != 4)
        {
            MessageBox.Show("Arguments: ARTICLE_DIRECTORY HIP_ROOT ARCHITECTURE NEW_OUTPUT_DIRECTORY");
            return;
        }
        Application.Run(new Workbench(args[0], args[1], args[2], args[3]));
    }
}

sealed class Workbench : Form
{
    readonly string article, hip, arch, output;
    readonly Label heading = new() { Dock = DockStyle.Top, Height = 72, Padding = new Padding(24, 18, 0, 0), Font = new Font("Segoe UI", 19, FontStyle.Bold), Text = "C# · AMD GPU validation" };
    readonly Label device = new() { Dock = DockStyle.Top, Height = 60, Padding = new Padding(24, 0, 0, 0), Text = "Reading hardware and executing the published-package examples…" };
    readonly ListView results = new() { Dock = DockStyle.Fill, View = View.Details, FullRowSelect = true, GridLines = true };
    readonly Label footer = new() { Dock = DockStyle.Bottom, Height = 95, Padding = new Padding(24, 15, 20, 0), Text = "Actual child-process execution; original stdout, stderr, commands and JSON retained.\nThis window reports checks for the selected models; it is not a performance benchmark or certification." };

    public Workbench(string article, string hip, string arch, string output)
    {
        this.article = Path.GetFullPath(article); this.hip = Path.GetFullPath(hip); this.arch = arch; this.output = Path.GetFullPath(output);
        Text = "ROCm C# · Live validation workbench";
        ClientSize = new Size(1140, 650); StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Segoe UI", 11); BackColor = Color.White;
        results.Columns.Add("Actual check", 270); results.Columns.Add("Status", 155); results.Columns.Add("Observed result", 650);
        Controls.Add(results); Controls.Add(footer); Controls.Add(device); Controls.Add(heading);
        Shown += async (_, _) => await Execute();
    }

    void Add(string check, string status, string detail)
    {
        var row = new ListViewItem(new[] { check, status, detail });
        row.ForeColor = status == "PASS" ? Color.DarkGreen : status == "FAIL" ? Color.Firebrick : Color.DimGray;
        results.Items.Add(row);
    }

    async Task Execute()
    {
        try
        {
            if (Directory.Exists(output)) throw new IOException("Select a new output directory; previous evidence is never overwritten.");
            Directory.CreateDirectory(output);
            int doctorExit = await Run("doctor", "-CheckOnly");
            using (var report = JsonDocument.Parse(File.ReadAllText(Path.Combine(output, "doctor.json"))))
            {
                var checks = report.RootElement.GetProperty("checks").EnumerateArray().ToArray();
                foreach (string name in new[] { "Actual GPU gfx", "Native static dependency closure", "Native candidate identity scan", "Native candidate compatibility" })
                {
                    var check = checks.Single(c => c.GetProperty("name").GetString() == name);
                    Add(name, check.GetProperty("status").GetString()!, check.GetProperty("detail").GetString()!);
                }
                using var hardware = JsonDocument.Parse(File.ReadAllText(Path.Combine(output, "doctor.json.hardware.json")));
                string stdout = hardware.RootElement.GetProperty("stdout").GetString()!;
                string deviceName = stdout.Split('\n').FirstOrDefault(l => l.StartsWith("Name:"))?.Split(':', 2)[1].Trim() ?? "See hardware report";
                device.Text = $"{deviceName} / {arch} · Windows {Environment.OSVersion.Version} · {System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription}\nHIP / MIGraphX supplied by the fixed NuGet references; SDK and native hashes are saved beside these results.";
            }
            Add("Preflight execution", doctorExit == 0 ? "PASS" : "FAIL", "Original checks and unresolved scope retained in doctor.json");
            if (doctorExit != 0) throw new InvalidOperationException("Preflight failed; inspect raw evidence before running models.");
            int verifyExit = await Run("verify");
            string verifyLog = File.ReadAllText(Path.Combine(output, "verify.stdout.log"));
            Add("HIP VectorAdd", verifyExit == 0 && verifyLog.Contains("PASS: length=65539; repetitions=3; max_abs_error=0") ? "PASS" : "FAIL", "65,539 elements · 3 repetitions · original stdout retained");
            Add("ONNX Identity", verifyExit == 0 && verifyLog.Contains("1, 2, 3, 4") ? "PASS" : "FAIL", "Model output: 1, 2, 3, 4 (API smoke test)");
            if (verifyExit != 0) throw new InvalidOperationException("Verification command failed; no successful model claim.");
            using (var report = JsonDocument.Parse(File.ReadAllText(Path.Combine(output, "verify.json"))))
            {
                var data = report.RootElement;
                bool passed = new[] { "hostError", "deviceError", "finalHostError", "finalDeviceError" }.All(k => data.GetProperty(k).GetProperty("passed").GetBoolean());
                int elements = data.GetProperty("outputElements").GetInt32();
                Add("Affine/ReLU CPU vs GPU", passed ? "PASS" : "FAIL", $"{elements:N0} outputs · CPU / host GPU / joint GPU numerical comparison");
            }
            int matmulExit = await Run("matmul", "-ModelPath", Path.Combine(article, "examples/MigraphxCompute/matmul-relu.onnx"));
            if (matmulExit != 0) throw new InvalidOperationException("MatMul failed; inspect raw log.");
            using (var report = JsonDocument.Parse(File.ReadAllText(Path.Combine(output, "matmul.json"))))
            {
                var data = report.RootElement;
                bool passed = new[] { "hostError", "deviceError", "finalHostError", "finalDeviceError" }.All(k => data.GetProperty(k).GetProperty("passed").GetBoolean());
                Add("MatMul + ReLU CPU vs GPU", passed ? "PASS" : "FAIL", $"{data.GetProperty("outputElements").GetInt32():N0} outputs · fixed Windows library paths");
            }
            heading.Text = "C# · AMD GPU checks completed";
            File.WriteAllText(Path.Combine(output, "workbench.json"), JsonSerializer.Serialize(new {
                date = DateTimeOffset.Now, completed = true, sourceArticle = article, requestedArchitecture = arch,
                rows = results.Items.Cast<ListViewItem>().Select(r => new { check = r.Text, status = r.SubItems[1].Text, detail = r.SubItems[2].Text }),
                allDisplayedChecksPassed = results.Items.Cast<ListViewItem>().All(r => r.SubItems[1].Text == "PASS"),
                scope = "Actual command execution in this session; static checks do not certify all models or drivers. No benchmark, cold-cache or production claim."
            }, new JsonSerializerOptions { WriteIndented = true }));
        }
        catch (Exception error)
        {
            heading.Text = "Validation stopped · inspect evidence";
            Add("Execution", "FAIL", error.Message);
            if (Directory.Exists(output)) File.WriteAllText(Path.Combine(output, "workbench-error.txt"), error.ToString());
        }
    }

    async Task<int> Run(string name, params string[] extra)
    {
        footer.Text = $"Executing {name} now…\nOriginal stdout / stderr and command identity are saved; no result is inserted before the command finishes.";
        var start = new ProcessStartInfo("pwsh") { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, WorkingDirectory = article };
        foreach (string arg in new[] { "-NoProfile", "-File", Path.Combine(article, "examples/run-windows.ps1"), "-HipRoot", hip, "-Architecture", arch,
                                      "-OutputPath", Path.Combine(output, name + ".json") }.Concat(extra)) start.ArgumentList.Add(arg);
        var started = DateTimeOffset.Now;
        using var process = Process.Start(start)!;
        var stdout = process.StandardOutput.ReadToEndAsync(); var stderr = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromMinutes(15));
        try { await process.WaitForExitAsync(timeout.Token); }
        catch { process.Kill(true); throw; }
        await File.WriteAllTextAsync(Path.Combine(output, name + ".stdout.log"), await stdout);
        await File.WriteAllTextAsync(Path.Combine(output, name + ".stderr.log"), await stderr);
        await File.WriteAllTextAsync(Path.Combine(output, name + ".command.json"), JsonSerializer.Serialize(new {
            started, finished = DateTimeOffset.Now, processId = process.Id, command = new[] { start.FileName }.Concat(start.ArgumentList), exitCode = process.ExitCode,
            stdoutSha256 = Hash(Path.Combine(output, name + ".stdout.log")), stderrSha256 = Hash(Path.Combine(output, name + ".stderr.log"))
        }, new JsonSerializerOptions { WriteIndented = true }));
        footer.Text = "Actual child-process execution; original stdout, stderr, commands and JSON retained.\nSelected fixed-model checks only; no benchmark or universal compatibility claim.";
        return process.ExitCode;
    }

    static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
}
