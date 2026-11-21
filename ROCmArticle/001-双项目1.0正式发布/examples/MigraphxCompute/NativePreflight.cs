using System.Diagnostics;
using System.Reflection.PortableExecutable;
using System.Text.Json;
using System.Text.RegularExpressions;

// Consumer-side diagnostics, without changing the published API or system settings.
static class NativePreflight
{
    public static void Hardware(string hipRoot, string architecture, string output, Action<string, string, string, string> add)
    {
        string tool = Path.Combine(hipRoot, "bin", "hipInfo.exe");
        if (!File.Exists(tool))
        {
            add("Actual GPU gfx", "NOT CHECKED", "hipInfo.exe is absent; requested target is " + architecture, "Install the matching HIP diagnostic tools, then rerun.");
            return;
        }
        try
        {
            using var process = Process.Start(new ProcessStartInfo(tool) { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true })!;
            var stdout = process.StandardOutput.ReadToEndAsync();
            var stderr = process.StandardError.ReadToEndAsync();
            if (!process.WaitForExit(30000)) { process.Kill(true); throw new TimeoutException("hipInfo exceeded 30 seconds"); }
            string text = stdout.GetAwaiter().GetResult();
            string errors = stderr.GetAwaiter().GetResult();
            var detected = Regex.Matches(text, @"gcnArchName:\s*(gfx[0-9a-f]+)").Select(m => m.Groups[1].Value).Distinct().ToArray();
            Round2Tools.Write(output + ".hardware.json", new { tool, toolSha256 = Round2Tools.Hash(tool), exitCode = process.ExitCode, stdout = text, stderr = errors, architectures = detected, requested = architecture });
            // A multi-GPU host requires an explicit device selection, which these examples do not provide.
            bool matches = process.ExitCode == 0 && detected.Length == 1 && detected[0] == architecture;
            add("Actual GPU gfx", matches ? "PASS" : "FAIL", "hipInfo hardware report: " + string.Join(", ", detected) + "; requested=" + architecture,
                "Match --arch to hipInfo. Multiple architectures require explicit device selection before using this example.");
        }
        catch (Exception error) { add("Actual GPU gfx", "FAIL", error.Message, "Run hipInfo from the selected HIP installation and inspect driver errors."); }
    }

    public static void Inventory(Action<string, string, string, string> add)
    {
        string? path = Environment.GetEnvironmentVariable("ARTICLE_DOCTOR_INVENTORY");
        if (path is null || !File.Exists(path))
        {
            add("Driver/PowerShell/SDK inventory", "NOT CHECKED", "No launcher inventory supplied", "Use run-windows.ps1 -CheckOnly.");
            return;
        }
        using var json = JsonDocument.Parse(File.ReadAllText(path).TrimStart('\uFEFF'));
        var data = json.RootElement;
        bool present = data.GetProperty("gpuDriver").GetArrayLength() > 0 && data.GetProperty("sdks").GetArrayLength() > 0;
        add("Driver/PowerShell/SDK inventory", present ? "PASS" : "FAIL", "Collected by launcher: " + Path.GetFileName(path), "Inspect inventory.json; collection does not certify driver compatibility.");
    }

    public static void Dependencies(string nativeDir, string hipRoot, string output, Action<string, string, string, string> add)
    {
        var loaded = Process.GetCurrentProcess().Modules.Cast<ProcessModule>()
            .GroupBy(m => m.ModuleName, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(g => g.Key, g => g.First().FileName, StringComparer.OrdinalIgnoreCase);
        string system = Environment.GetFolderPath(Environment.SpecialFolder.System);
        var directories = new[] { nativeDir, AppContext.BaseDirectory, Path.Combine(AppContext.BaseDirectory, "runtimes", "win-x64", "native"), Path.Combine(hipRoot, "bin"), system }
            .Concat((Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator))
            .Where(p => !string.IsNullOrWhiteSpace(p) && Path.IsPathFullyQualified(p) && Directory.Exists(p))
            .Select(Path.GetFullPath).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        var pending = new Queue<string>();
        foreach (string name in new[] { "migraphx_c.dll", "migraphx.dll", "migraphx_gpu.dll" }) pending.Enqueue(Path.Combine(nativeDir, name));
        foreach (var module in loaded.Where(m => Regex.IsMatch(m.Key, "hip|miopen|rocblas|comgr", RegexOptions.IgnoreCase))) pending.Enqueue(module.Value);
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var edges = new List<object>();
        var conflicts = new List<object>();
        int versionConflicts = 0;
        var missing = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var scannedNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var identities = new List<object>();
        var unreadable = new List<object>();
        while (pending.TryDequeue(out string? path))
        {
            if (!seen.Add(Path.GetFullPath(path))) continue;
            if (!File.Exists(path)) { missing.Add(path); continue; }
            identities.Add(new { path, sha256 = Round2Tools.Hash(path), version = FileVersionInfo.GetVersionInfo(path).FileVersion });
            if (path.StartsWith(system + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) continue;
            try
            {
                foreach (string name in Imports(path).Distinct(StringComparer.OrdinalIgnoreCase))
                {
                    if (name.StartsWith("api-ms-", StringComparison.OrdinalIgnoreCase) || name.StartsWith("ext-ms-", StringComparison.OrdinalIgnoreCase))
                    { edges.Add(new { importer = path, name, status = "OS_API_SET", resolved = (string?)null }); continue; }
                    var candidates = new[] { Path.GetDirectoryName(path)! }.Concat(directories)
                        .Select(dir => Path.Combine(dir, name)).Where(File.Exists).Select(Path.GetFullPath).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
                    string? resolved = loaded.GetValueOrDefault(name) ?? candidates.FirstOrDefault();
                    edges.Add(new { importer = path, name, status = resolved is null ? "MISSING" : loaded.ContainsKey(name) ? "LOADED" : "STATIC_CANDIDATE", resolved });
                    if (resolved is null) missing.Add(name);
                    else pending.Enqueue(resolved);
                    if (scannedNames.Add(name) && resolved is not null && !resolved.StartsWith(system + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                    {
                        var copies = candidates.Append(resolved).Distinct(StringComparer.OrdinalIgnoreCase)
                            .Select(p => new { path = p, sha256 = Round2Tools.Hash(p), version = FileVersionInfo.GetVersionInfo(p).FileVersion }).ToArray();
                        if (copies.Select(c => c.sha256).Distinct().Count() > 1)
                        {
                            bool differentVersions = copies.Where(c => !string.IsNullOrEmpty(c.version)).Select(c => c.version).Distinct().Count() > 1;
                            if (differentVersions) versionConflicts++;
                            conflicts.Add(new { name, copies, differentVersions, loaded = loaded.GetValueOrDefault(name) });
                        }
                    }
                }
            }
            catch (Exception error) { unreadable.Add(new { path, error = error.Message }); }
        }
        Round2Tools.Write(output + ".dependencies.json", new {
            scope = "Static PE import and delay-import closure of non-system native dependencies plus actually loaded modules. System DLL recursion stops at System32; API sets are OS-resolved. Dynamic plugin/solver loads and ABI compatibility are not certified. Candidate search is diagnostic, not an emulation of all Windows loader policies.",
            directories, files = identities, edges, missing, unreadable, conflicts, versionConflicts });
        add("Native static dependency closure", missing.Count == 0 && unreadable.Count == 0 ? "PASS" : "FAIL",
            $"{seen.Count} files; {edges.Count} import edges; {missing.Count} missing; {unreadable.Count} unreadable", "Inspect .dependencies.json; use one complete ROCm installation and matching VC++ runtime.");
        add("Native candidate identity scan", "PASS", $"{conflicts.Count} non-system DLL names have different reachable SHA256 values; {versionConflicts} also have different versions", "Inspect candidate copies and actual loaded paths in .dependencies.json.");
        add("Native candidate compatibility", versionConflicts > 0 ? "FAIL" : conflicts.Count > 0 ? "NOT CHECKED" : "PASS",
            "Different versions require resolution; same-version byte differences do not by themselves prove ABI incompatibility.", "Use one ROCm family and validate the selected models. Byte-different copies remain recorded even after numerical checks pass.");
    }

    static IEnumerable<string> Imports(string path)
    {
        byte[] bytes = File.ReadAllBytes(path);
        using var pe = new PEReader(new MemoryStream(bytes));
        var header = pe.PEHeaders.PEHeader ?? throw new InvalidDataException("Not a PE image");
        int Offset(int rva)
        {
            var section = pe.PEHeaders.SectionHeaders.FirstOrDefault(s => rva >= s.VirtualAddress && rva < s.VirtualAddress + Math.Max(s.VirtualSize, s.SizeOfRawData));
            if (section.Name is null) throw new InvalidDataException("Import RVA outside PE sections");
            return checked(section.PointerToRawData + rva - section.VirtualAddress);
        }
        string Name(int rva)
        {
            int start = Offset(rva), end = Array.IndexOf(bytes, (byte)0, start);
            if (end < 0) throw new InvalidDataException("Unterminated import name");
            return System.Text.Encoding.ASCII.GetString(bytes, start, end - start);
        }
        var names = new List<string>();
        if (header.ImportTableDirectory.RelativeVirtualAddress != 0)
        {
            int start = Offset(header.ImportTableDirectory.RelativeVirtualAddress);
            for (int p = start; p + 20 <= bytes.Length; p += 20)
            {
                int name = BitConverter.ToInt32(bytes, p + 12);
                if (name == 0) break;
                names.Add(Name(name));
            }
        }
        if (header.DelayImportTableDirectory.RelativeVirtualAddress != 0)
        {
            int start = Offset(header.DelayImportTableDirectory.RelativeVirtualAddress);
            for (int p = start; p + 32 <= bytes.Length; p += 32)
            {
                uint flags = BitConverter.ToUInt32(bytes, p), name = BitConverter.ToUInt32(bytes, p + 4);
                if (name == 0) break;
                if ((flags & 1) == 0) throw new NotSupportedException("Legacy VA delay imports require manual inspection");
                names.Add(Name(checked((int)name)));
            }
        }
        return names;
    }
}
