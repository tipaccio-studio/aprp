using System.Diagnostics;
using System.IO;
using System.Reflection;
using Microsoft.Win32;

namespace Aprp.Services;

/// <summary>Version, links and how this copy of aprp was installed.</summary>
public static class AppInfo
{
    public const string Repository = "tipaccio-studio/aprp";
    public const string RepositoryUrl = "https://github.com/" + Repository;
    public const string ReleasesUrl = RepositoryUrl + "/releases/latest";
    public const string StudioName = "Tipaccio Studio";
    public const string StudioUrl = "https://tipacciostudio.com/";
    public const string LicenseUrl = RepositoryUrl + "/blob/main/LICENSE";
    public const string PrivacyUrl = RepositoryUrl + "/blob/main/docs/PRIVACY.md";

    // Inno Setup AppId from installer/aprp.iss; its uninstall key is "<AppId>_is1".
    private const string UninstallKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\{6B1C2F2E-5A3D-4C8E-9F1A-A7B2C3D4E5F6}_is1";

    /// <summary>"1.0.0", from &lt;Version&gt; in the project. APRP_DEBUG_VERSION overrides it to test updates.</summary>
    public static Version Version { get; } = ReadVersion();
    public static string VersionText => $"{Version.Major}.{Version.Minor}.{Version.Build}";

    public static string ExecutableDir => AppContext.BaseDirectory.TrimEnd('\\');

    private static Version ReadVersion()
    {
        var text = Environment.GetEnvironmentVariable("APRP_DEBUG_VERSION")
                   ?? Assembly.GetExecutingAssembly().GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion
                   ?? "0.0.0";
        return ParseVersion(text) ?? new Version(0, 0, 0);
    }

    /// <summary>"v1.2.3" / "1.2.3+abc" -> 1.2.3; null if it isn't a version.</summary>
    public static Version? ParseVersion(string text)
    {
        var core = text.Trim().TrimStart('v', 'V').Split('+', '-')[0];
        return Version.TryParse(core, out var v) ? new Version(v.Major, v.Minor, Math.Max(0, v.Build)) : null;
    }

    /// <summary>The Inno Setup uninstaller for *this* copy, or null for a portable copy.</summary>
    public static string? FindUninstaller()
    {
        foreach (var hive in new[] { RegistryHive.CurrentUser, RegistryHive.LocalMachine })
        {
            try
            {
                using var root = RegistryKey.OpenBaseKey(hive, RegistryView.Registry64);
                using var key = root.OpenSubKey(UninstallKey);
                if (key?.GetValue("InstallLocation") is not string location) continue;
                if (!string.Equals(Path.GetFullPath(location).TrimEnd('\\'), ExecutableDir, StringComparison.OrdinalIgnoreCase))
                    continue; // another installation; this copy is portable
                var uninstaller = (key.GetValue("UninstallString") as string)?.Trim('"');
                if (uninstaller is not null && File.Exists(uninstaller)) return uninstaller;
            }
            catch (Exception ex) when (ex is UnauthorizedAccessException or IOException or System.Security.SecurityException)
            {
            }
        }
        return null;
    }

    public static void OpenUrl(string url)
    {
        // Only our own fixed links are opened (never URLs from scan results).
        if (url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
    }
}
