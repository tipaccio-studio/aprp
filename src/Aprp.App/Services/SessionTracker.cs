using System.Diagnostics;
using Aprp.Models;

namespace Aprp.Services;

/// <summary>
/// Measures a play session using the native monitor: wait for a process to
/// appear in the game's install folder, then wait until none is left.
/// </summary>
public sealed class SessionTracker
{
    private static readonly TimeSpan StartupWindow = TimeSpan.FromMinutes(3);  // launcher may patch first
    private static readonly TimeSpan HandOffWindow = TimeSpan.FromSeconds(10); // bootstrapper -> real game
    private static readonly TimeSpan PollInterval = TimeSpan.FromSeconds(2);

    public bool IsAvailable => NativeMethods.IsAvailable;

    /// <returns>Session length, or null if the game never started or tracking is unavailable.</returns>
    public async Task<TimeSpan?> TrackAsync(Game game, CancellationToken ct = default)
    {
        if (!IsAvailable || string.IsNullOrEmpty(game.InstallDir))
            return null;

        uint pid = await WaitForProcessAsync(game.InstallDir, StartupWindow, ct);
        if (pid == 0)
            return null;

        var clock = Stopwatch.StartNew();
        game.IsRunning = true;
        try
        {
            while (pid != 0)
            {
                await Task.Run(() => WaitForExit(pid, ct), ct);
                pid = await WaitForProcessAsync(game.InstallDir, HandOffWindow, ct);
            }
        }
        finally
        {
            game.IsRunning = false;
        }
        return clock.Elapsed;
    }

    private static async Task<uint> WaitForProcessAsync(string dir, TimeSpan window, CancellationToken ct)
    {
        var deadline = DateTime.UtcNow + window;
        while (DateTime.UtcNow < deadline)
        {
            if (NativeMethods.aprp_find_process_in_dir(dir, out uint pid) == NativeMethods.Ok)
                return pid;
            await Task.Delay(PollInterval, ct);
        }
        return 0;
    }

    private static void WaitForExit(uint pid, CancellationToken ct)
    {
        // Short native waits keep the loop cancellable without a dedicated wait handle.
        while (NativeMethods.aprp_wait_for_exit(pid, 1000) == NativeMethods.Timeout)
            ct.ThrowIfCancellationRequested();
    }
}
