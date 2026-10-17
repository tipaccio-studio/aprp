using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.Json;
using Aprp.Models;

namespace Aprp.Services;

/// <summary>
/// Runs the Python scanner as a child process and reads its JSON from stdout.
/// Looks for, in order: scanner\aprp-scanner.exe next to the app, the frozen
/// scanner embedded in aprp.exe (extracted once to %LOCALAPPDATA%), and
/// `python -m aprp_scanner` for development.
/// </summary>
public sealed class ScannerService
{
    private static readonly string AppData = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "aprp");
    private static readonly string ScannerDir = Path.Combine(AppContext.BaseDirectory, "scanner");
    private static readonly string CachePath = Path.Combine(AppData, "library.json");

    /// <param name="online">Also fetch missing descriptions and banners (slower; cached by the scanner).</param>
    public async Task<ScanResult> ScanAsync(bool online, CancellationToken ct = default)
    {
        var psi = CreateStartInfo();
        psi.ArgumentList.Add("scan");
        if (online) psi.ArgumentList.Add("--online");
        psi.UseShellExecute = false;
        psi.CreateNoWindow = true;
        psi.RedirectStandardOutput = true;
        psi.RedirectStandardError = true;
        psi.StandardOutputEncoding = Encoding.UTF8;
        psi.Environment["PYTHONIOENCODING"] = "utf-8";
        psi.Environment["APRP_LANG"] = Loc.Instance.Language; // descriptions in the app's language

        using var process = Process.Start(psi)
            ?? throw new InvalidOperationException("Impossibile avviare lo scanner dei giochi.");
        var stdout = process.StandardOutput.ReadToEndAsync();
        var stderr = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync(ct);

        if (process.ExitCode != 0)
            throw new InvalidOperationException($"Scanner terminato con errore ({process.ExitCode}): {await stderr}");

        var result = JsonSerializer.Deserialize<ScanResult>(await stdout) ?? new ScanResult();
        SaveCache(result);
        return result;
    }

    /// <summary>Last successful scan, so the library shows instantly on startup.</summary>
    public ScanResult? LoadCache()
    {
        try
        {
            return File.Exists(CachePath)
                ? JsonSerializer.Deserialize<ScanResult>(File.ReadAllText(CachePath))
                : null;
        }
        catch (Exception ex) when (ex is IOException or JsonException)
        {
            return null;
        }
    }

    private static void SaveCache(ScanResult result)
    {
        try
        {
            Directory.CreateDirectory(AppData);
            File.WriteAllText(CachePath, JsonSerializer.Serialize(result));
        }
        catch (IOException)
        {
            // Cache is an optimisation only.
        }
    }

    private static ProcessStartInfo CreateStartInfo()
    {
        var beside = Path.Combine(ScannerDir, "aprp-scanner.exe");
        if (File.Exists(beside))
            return new ProcessStartInfo(beside);

        if (ExtractEmbeddedScanner() is { } extracted)
            return new ProcessStartInfo(extracted);

        var python = Environment.GetEnvironmentVariable("APRP_PYTHON") ?? "python";
        return new ProcessStartInfo(python)
        {
            ArgumentList = { "-m", "aprp_scanner" },
            WorkingDirectory = ScannerDir,
        };
    }

    private static string? ExtractEmbeddedScanner()
    {
        var asm = Assembly.GetExecutingAssembly();
        using var resource = asm.GetManifestResourceStream("aprp-scanner.exe");
        if (resource is null)
            return null;

        // Versioned name: a new aprp.exe never runs a stale scanner.
        var version = asm.GetName().Version?.ToString() ?? "0";
        var target = Path.Combine(AppData, "bin", $"aprp-scanner-{version}-{resource.Length}.exe");
        if (!File.Exists(target))
        {
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            var temp = target + ".tmp";
            using (var file = File.Create(temp))
                resource.CopyTo(file);
            File.Move(temp, target, overwrite: true);
        }
        return target;
    }
}
