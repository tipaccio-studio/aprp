using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;

namespace Aprp.Services;

public sealed record UpdateInfo(Version Version, string PageUrl, string? SetupUrl, string? SumsUrl, string? SetupName);

/// <summary>
/// Checks the latest GitHub release and installs it: downloads the installer,
/// checks its SHA-256 against the release's SHA256SUMS.txt, then runs it.
/// </summary>
public sealed class UpdateService
{
    private static readonly HttpClient Http = CreateClient();

    private static HttpClient CreateClient()
    {
        var c = new HttpClient { Timeout = TimeSpan.FromMinutes(10) };
        c.DefaultRequestHeaders.UserAgent.ParseAdd($"aprp/{AppInfo.VersionText} (+{AppInfo.RepositoryUrl})");
        c.DefaultRequestHeaders.Accept.ParseAdd("application/vnd.github+json");
        return c;
    }

    /// <summary>The latest release if it's newer than this app, otherwise null.</summary>
    public async Task<UpdateInfo?> CheckAsync(CancellationToken ct = default)
    {
        using var resp = await Http.GetAsync($"https://api.github.com/repos/{AppInfo.Repository}/releases/latest", ct);
        resp.EnsureSuccessStatusCode();
        using var doc = JsonDocument.Parse(await resp.Content.ReadAsStringAsync(ct));
        var root = doc.RootElement;
        var latest = AppInfo.ParseVersion(root.GetProperty("tag_name").GetString() ?? "");
        if (latest is null || latest <= AppInfo.Version) return null;

        string? setup = null, setupName = null, sums = null;
        foreach (var asset in root.GetProperty("assets").EnumerateArray())
        {
            var name = asset.GetProperty("name").GetString() ?? "";
            var url = asset.GetProperty("browser_download_url").GetString();
            if (name.StartsWith("aprp-setup-", StringComparison.OrdinalIgnoreCase) && name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                (setup, setupName) = (url, name);
            else if (name.Equals("SHA256SUMS.txt", StringComparison.OrdinalIgnoreCase))
                sums = url;
        }
        return new UpdateInfo(latest, root.GetProperty("html_url").GetString() ?? AppInfo.ReleasesUrl, setup, sums, setupName);
    }

    /// <summary>Download, verify and start the installer. The caller should then close aprp.</summary>
    public async Task DownloadAndRunAsync(UpdateInfo update, IProgress<int> progress, CancellationToken ct = default)
    {
        if (update.SetupUrl is null || update.SumsUrl is null || update.SetupName is null)
            throw new InvalidOperationException("The release has no installer or checksums.");
        if (!IsOurDownload(update.SetupUrl) || !IsOurDownload(update.SumsUrl))
            throw new InvalidOperationException("Unexpected download location.");

        var sums = await Http.GetStringAsync(update.SumsUrl, ct);
        var expected = sums.Split('\n')
            .Select(l => l.Trim().Split(' ', 2, StringSplitOptions.RemoveEmptyEntries))
            .FirstOrDefault(p => p.Length == 2 && p[1].Trim().Equals(update.SetupName, StringComparison.OrdinalIgnoreCase))?[0];
        if (expected is null) throw new InvalidOperationException("No checksum for the installer.");

        var dir = Path.Combine(Path.GetTempPath(), "aprp-update");
        Directory.CreateDirectory(dir);
        var file = Path.Combine(dir, update.SetupName);

        using (var resp = await Http.GetAsync(update.SetupUrl, HttpCompletionOption.ResponseHeadersRead, ct))
        {
            resp.EnsureSuccessStatusCode();
            var total = resp.Content.Headers.ContentLength ?? 0;
            await using var src = await resp.Content.ReadAsStreamAsync(ct);
            await using var dst = File.Create(file);
            var buffer = new byte[1 << 16];
            long done = 0;
            int read;
            while ((read = await src.ReadAsync(buffer, ct)) > 0)
            {
                await dst.WriteAsync(buffer.AsMemory(0, read), ct);
                done += read;
                if (total > 0) progress.Report((int)(done * 100 / total));
            }
        }

        string actual;
        await using (var fs = File.OpenRead(file))
            actual = Convert.ToHexString(await SHA256.HashDataAsync(fs, ct));
        if (!actual.Equals(expected, StringComparison.OrdinalIgnoreCase))
        {
            File.Delete(file);
            throw new InvalidOperationException("The download is corrupted (checksum mismatch).");
        }

        // The installer closes the running aprp (CloseApplications) and upgrades it in place.
        Process.Start(new ProcessStartInfo(file) { UseShellExecute = true, Arguments = "/SP-" });
    }

    private static bool IsOurDownload(string url) =>
        url.StartsWith($"https://github.com/{AppInfo.Repository}/releases/download/", StringComparison.OrdinalIgnoreCase);
}
