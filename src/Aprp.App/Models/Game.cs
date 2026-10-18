using System.Text.Json.Serialization;
using Aprp.ViewModels;

namespace Aprp.Models;

/// <summary>One game. JSON shape matches scanner/aprp_scanner/models.py.</summary>
public sealed class Game : ObservableObject
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("platform")] public string Platform { get; set; } = "";
    [JsonPropertyName("source")] public string? Source { get; set; }
    [JsonPropertyName("title")] public string Title { get; set; } = "";
    [JsonPropertyName("install_dir")] public string InstallDir { get; set; } = "";
    [JsonPropertyName("launch_uri")] public string LaunchUri { get; set; } = "";
    [JsonPropertyName("size_bytes")] public long? SizeBytes { get; set; }
    [JsonPropertyName("installed")] public bool Installed { get; set; } = true;
    [JsonPropertyName("logo")] public string? Logo { get; set; }

    // Filled in later by the online metadata pass, so they notify.
    private string? _cover, _banner, _description, _developer;
    [JsonPropertyName("cover")] public string? Cover { get => _cover; set => SetField(ref _cover, value); }
    [JsonPropertyName("banner")] public string? Banner { get => _banner; set => SetField(ref _banner, value); }
    [JsonPropertyName("description")] public string? Description { get => _description; set => SetField(ref _description, value); }
    [JsonPropertyName("developer")] public string? Developer { get => _developer; set => SetField(ref _developer, value); }

    // ── playtime ──────────────────────────────────────────────────────────
    // Store-recorded values come from the scanner (Steam, Modrinth); for everything else
    // aprp records sessions itself (PlaytimeStore) and fills the Tracked* values.
    private int? _storeMinutes;
    private long? _storeLastPlayed;
    private int _trackedMinutes;
    private long? _trackedLastPlayed;

    [JsonPropertyName("playtime_minutes")]
    public int? StorePlaytimeMinutes { get => _storeMinutes; set { _storeMinutes = value; NotifyPlaytime(); } }

    [JsonPropertyName("last_played")]
    public long? StoreLastPlayed { get => _storeLastPlayed; set { _storeLastPlayed = value; NotifyPlaytime(); } }

    [JsonIgnore] public bool StoreTracksPlaytime => StorePlaytimeMinutes.HasValue;
    [JsonIgnore] public int TrackedMinutes { get => _trackedMinutes; set { _trackedMinutes = value; NotifyPlaytime(); } }
    [JsonIgnore] public long? TrackedLastPlayed { get => _trackedLastPlayed; set { _trackedLastPlayed = value; NotifyPlaytime(); } }

    [JsonIgnore] public int PlaytimeMinutes => StorePlaytimeMinutes ?? TrackedMinutes;
    [JsonIgnore] public long LastPlayed => Math.Max(StoreLastPlayed ?? 0, TrackedLastPlayed ?? 0);
    [JsonIgnore] public bool HasPlaytime => PlaytimeMinutes > 0;
    [JsonIgnore] public bool HasLastPlayed => LastPlayed > 0;

    [JsonIgnore]
    public string PlaytimeText => PlaytimeMinutes >= 60
        ? Loc.Get("PlaytimeHours", PlaytimeMinutes / 60, PlaytimeMinutes % 60)
        : Loc.Get("PlaytimeMinutes", PlaytimeMinutes);

    [JsonIgnore]
    public string LastPlayedText
    {
        get
        {
            if (LastPlayed <= 0) return "";
            var when = DateTimeOffset.FromUnixTimeSeconds(LastPlayed).LocalDateTime.Date;
            var days = (DateTime.Today - when).Days;
            var ago = days <= 0 ? Loc.Get("Today")
                : days == 1 ? Loc.Get("Yesterday")
                : days < 31 ? Loc.Get("DaysAgo", days)
                : days < 60 ? Loc.Get("MonthAgo")
                : days < 365 ? Loc.Get("MonthsAgo", days / 30)
                : days < 730 ? Loc.Get("YearAgo")
                : Loc.Get("YearsAgo", days / 365);
            return Loc.Get("LastPlayed", ago);
        }
    }

    /// <summary>A session that aprp just measured. Store-tracked games get it from the store on the next scan too.</summary>
    public void AddSession(TimeSpan played)
    {
        var minutes = (int)Math.Round(played.TotalMinutes);
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        if (StoreTracksPlaytime)
            StorePlaytimeMinutes += minutes;   // shown right away; the next scan brings the store's own number
        else
            TrackedMinutes += minutes;
        TrackedLastPlayed = now;
    }

    /// <summary>Re-raise the computed texts (after a language change too).</summary>
    public void NotifyPlaytime()
    {
        OnPropertyChanged(nameof(PlaytimeMinutes));
        OnPropertyChanged(nameof(LastPlayed));
        OnPropertyChanged(nameof(HasPlaytime));
        OnPropertyChanged(nameof(HasLastPlayed));
        OnPropertyChanged(nameof(PlaytimeText));
        OnPropertyChanged(nameof(LastPlayedText));
    }

    [JsonIgnore]
    public string Initial => string.IsNullOrEmpty(Title) ? "?" : Title.Substring(0, 1).ToUpperInvariant();

    private bool _isRunning;
    [JsonIgnore]
    public bool IsRunning
    {
        get => _isRunning;
        set => SetField(ref _isRunning, value);
    }

    /// <summary>Copy data from a newer scan of the same game, keeping this instance (and the UI's selection).</summary>
    public void UpdateFrom(Game other)
    {
        Cover = other.Cover ?? Cover;
        Banner = other.Banner ?? Banner;
        Description = other.Description ?? Description;
        Developer = other.Developer ?? Developer;
        StorePlaytimeMinutes = other.StorePlaytimeMinutes ?? StorePlaytimeMinutes;
        StoreLastPlayed = other.StoreLastPlayed ?? StoreLastPlayed;
    }
}

public sealed class ScanResult
{
    [JsonPropertyName("games")] public List<Game> Games { get; set; } = new();
    [JsonPropertyName("errors")] public List<ScanError> Errors { get; set; } = new();
}

public sealed class ScanError
{
    [JsonPropertyName("platform")] public string Platform { get; set; } = "";
    [JsonPropertyName("message")] public string Message { get; set; } = "";
}
