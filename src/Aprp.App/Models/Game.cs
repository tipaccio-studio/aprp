using System.Text.Json.Serialization;
using Aprp.ViewModels;

namespace Aprp.Models;

/// <summary>One game. JSON shape matches scanner/aprp_scanner/models.py.</summary>
public sealed class Game : ObservableObject
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("platform")] public string Platform { get; set; } = "";
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

    [JsonIgnore]
    public string Initial => string.IsNullOrEmpty(Title) ? "?" : Title.Substring(0, 1).ToUpperInvariant();

    private bool _isRunning;
    [JsonIgnore]
    public bool IsRunning
    {
        get => _isRunning;
        set => SetField(ref _isRunning, value);
    }

    /// <summary>Copy metadata from a newer scan of the same game, keeping this instance (and the UI's selection).</summary>
    public void UpdateFrom(Game other)
    {
        Cover = other.Cover ?? Cover;
        Banner = other.Banner ?? Banner;
        Description = other.Description ?? Description;
        Developer = other.Developer ?? Developer;
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
