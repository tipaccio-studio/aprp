using System.Diagnostics;
using Aprp.Models;

namespace Aprp.Services;

/// <summary>
/// Launches games through their store's own protocol so DRM, updates,
/// cloud saves and overlays keep working.
/// </summary>
public sealed class LauncherService
{
    // Only URIs the scanner produces are allowed; library.json is user-writable,
    // so never shell-execute arbitrary strings from it.
    private static readonly string[] AllowedPrefixes =
    {
        "steam://rungameid/",
        "steam://install/",
        "com.epicgames.launcher://apps/",
        @"shell:AppsFolder\",
    };

    public void Launch(Game game)
    {
        var uri = game.LaunchUri;
        if (!AllowedPrefixes.Any(p => uri.StartsWith(p, StringComparison.OrdinalIgnoreCase)))
            throw new InvalidOperationException($"Refusing to launch unrecognised URI: {uri}");

        var psi = uri.StartsWith("shell:", StringComparison.OrdinalIgnoreCase)
            ? new ProcessStartInfo("explorer.exe") { ArgumentList = { uri } }  // Xbox / MS Store (MSIX)
            : new ProcessStartInfo(uri) { UseShellExecute = true };             // registered protocol handler

        Process.Start(psi);
    }
}
