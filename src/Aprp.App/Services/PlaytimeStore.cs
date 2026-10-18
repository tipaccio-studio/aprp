using System.IO;
using System.Text.Json;
using Aprp.Models;

namespace Aprp.Services;

/// <summary>
/// Playtime that aprp measured itself, for games whose store doesn't record it
/// (Epic, Xbox). Saved in %LOCALAPPDATA%\aprp\playtime.json.
/// </summary>
public sealed class PlaytimeStore
{
    private sealed class Entry
    {
        public int Minutes { get; set; }
        public long LastPlayed { get; set; }
    }

    private static readonly string FilePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "aprp", "playtime.json");

    private readonly Dictionary<string, Entry> _entries;

    public PlaytimeStore()
    {
        try
        {
            _entries = File.Exists(FilePath)
                ? JsonSerializer.Deserialize<Dictionary<string, Entry>>(File.ReadAllText(FilePath)) ?? new()
                : new();
        }
        catch (Exception ex) when (ex is IOException or JsonException)
        {
            _entries = new();
        }
    }

    /// <summary>Put the saved numbers on a game freshly loaded from a scan.</summary>
    public void Apply(Game game)
    {
        if (_entries.TryGetValue(game.Id, out var e))
        {
            game.TrackedMinutes = e.Minutes;
            game.TrackedLastPlayed = e.LastPlayed > 0 ? e.LastPlayed : null;
        }
    }

    /// <summary>Record a finished session and update the game on screen.</summary>
    public void Record(Game game, TimeSpan played)
    {
        game.AddSession(played);
        if (!_entries.TryGetValue(game.Id, out var e))
            _entries[game.Id] = e = new Entry();
        e.Minutes = game.TrackedMinutes;
        e.LastPlayed = game.TrackedLastPlayed ?? 0;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(FilePath)!);
            var temp = FilePath + ".tmp";
            File.WriteAllText(temp, JsonSerializer.Serialize(_entries));
            File.Move(temp, FilePath, overwrite: true);
        }
        catch (IOException)
        {
            // Losing one session's minutes is better than crashing the app.
        }
    }
}
