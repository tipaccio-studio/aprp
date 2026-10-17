using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Windows.Data;
using System.Windows.Input;
using Aprp.Models;
using Aprp.Services;

namespace Aprp.ViewModels;

public sealed class MainViewModel : ObservableObject
{
    private readonly ScannerService _scanner = new();
    private readonly LauncherService _launcher = new();
    private readonly SessionTracker _tracker = new();

    public ObservableCollection<Game> Games { get; } = new();
    public ICollectionView GamesView { get; }

    public ICommand RescanCommand { get; }
    public ICommand LaunchCommand { get; }
    public ICommand OpenFolderCommand { get; }
    public ICommand SelectPlatformCommand { get; }

    public MainViewModel()
    {
        GamesView = CollectionViewSource.GetDefaultView(Games);
        GamesView.Filter = o => o is Game g && Matches(g);
        // Installed games first, then A–Z.
        GamesView.SortDescriptions.Add(new SortDescription(nameof(Game.Installed), ListSortDirection.Descending));
        GamesView.SortDescriptions.Add(new SortDescription(nameof(Game.Title), ListSortDirection.Ascending));

        RescanCommand = new RelayCommand(async _ => await RescanAsync(online: true), _ => !IsScanning);
        LaunchCommand = new RelayCommand(p => { if ((p as Game ?? SelectedGame) is { } g) _ = LaunchAsync(g); });
        OpenFolderCommand = new RelayCommand(
            _ => Process.Start(new ProcessStartInfo("explorer.exe") { ArgumentList = { SelectedGame!.InstallDir } }),
            _ => SelectedGame is { Installed: true } g && Directory.Exists(g.InstallDir));
        SelectPlatformCommand = new RelayCommand(p => Platform = p as string ?? "all");
        SetLanguageCommand = new RelayCommand(async p =>
        {
            IsLanguageMenuOpen = false;
            if (p is not string code || code == Loc.Instance.Language) return;
            Loc.Instance.SetLanguage(code);
            await RescanAsync(online: true); // descriptions in the new language
        });
    }

    public ICommand SetLanguageCommand { get; }
    public IReadOnlyList<LanguageOption> Languages => Loc.Languages;

    private bool _isLanguageMenuOpen;
    public bool IsLanguageMenuOpen
    {
        get => _isLanguageMenuOpen;
        set => SetField(ref _isLanguageMenuOpen, value);
    }

    private string _platform = "all";
    public string Platform
    {
        get => _platform;
        set { if (SetField(ref _platform, value)) RefreshView(); }
    }

    private string _searchText = "";
    public string SearchText
    {
        get => _searchText;
        set { if (SetField(ref _searchText, value)) RefreshView(); }
    }

    private bool _installedOnly;
    public bool InstalledOnly
    {
        get => _installedOnly;
        set { if (SetField(ref _installedOnly, value)) RefreshView(); }
    }

    private Game? _selectedGame;
    public Game? SelectedGame
    {
        get => _selectedGame;
        set
        {
            if (SetField(ref _selectedGame, value)) CommandManager.InvalidateRequerySuggested();
        }
    }

    private bool _isScanning;
    public bool IsScanning
    {
        get => _isScanning;
        private set
        {
            // Async completion doesn't trigger WPF's CanExecute re-query on its own.
            if (SetField(ref _isScanning, value)) CommandManager.InvalidateRequerySuggested();
        }
    }

    private string _status = "";
    public string Status
    {
        get => _status;
        private set => SetField(ref _status, value);
    }

    public int AllCount => Games.Count;
    public int SteamCount => Games.Count(g => g.Platform == "steam");
    public int EpicCount => Games.Count(g => g.Platform == "epic");
    public int XboxCount => Games.Count(g => g.Platform == "xbox");
    public int VisibleCount => GamesView.Cast<object>().Count();

    public async Task InitializeAsync()
    {
        if (_scanner.LoadCache() is { } cached)
            MergeGames(cached.Games);
        await RescanAsync(online: false); // fast: local files + cached metadata
        await RescanAsync(online: true);  // fills in new descriptions/banners in the background
        if (!_tracker.IsAvailable)
            Status = Loc.Get("NoNative");
    }

    private bool Matches(Game g) =>
        (Platform == "all" || g.Platform == Platform) &&
        (!InstalledOnly || g.Installed) &&
        (SearchText.Length == 0 || g.Title.Contains(SearchText, StringComparison.OrdinalIgnoreCase));

    private void RefreshView()
    {
        GamesView.Refresh();
        OnPropertyChanged(nameof(VisibleCount));
        if (SelectedGame is null || !Matches(SelectedGame))
            SelectedGame = GamesView.Cast<Game>().FirstOrDefault();
    }

    private async Task RescanAsync(bool online)
    {
        if (IsScanning) return;
        IsScanning = true;
        Status = Loc.Get(online ? "Metadata" : "Scanning");
        try
        {
            var result = await _scanner.ScanAsync(online);
            MergeGames(result.Games);
            var summary = Loc.Get("Summary", Games.Count, Games.Count(g => g.Installed));
            Status = result.Errors.Count == 0
                ? summary
                : $"{summary}. {Loc.Get("Problems")}: " + string.Join("; ", result.Errors.Select(e => $"{e.Platform}: {e.Message}"));
        }
        catch (Exception ex)
        {
            Status = Loc.Get("ScanFailed", ex.Message);
        }
        finally
        {
            IsScanning = false;
        }
    }

    /// <summary>Update existing games in place (keeps selection, scroll and running state), add new ones, drop removed ones.</summary>
    private void MergeGames(IEnumerable<Game> fresh)
    {
        var incoming = fresh.GroupBy(g => g.Id).ToDictionary(g => g.Key, g => g.First());
        foreach (var gone in Games.Where(g => !incoming.ContainsKey(g.Id)).ToList())
            Games.Remove(gone);

        var existing = Games.ToDictionary(g => g.Id);
        foreach (var game in incoming.Values)
        {
            if (!existing.TryGetValue(game.Id, out var current))
                Games.Add(game);
            else if (current.Installed != game.Installed || current.LaunchUri != game.LaunchUri)
                Games[Games.IndexOf(current)] = game; // install state changed: replace
            else
                current.UpdateFrom(game);
        }

        OnPropertyChanged(nameof(AllCount));
        OnPropertyChanged(nameof(SteamCount));
        OnPropertyChanged(nameof(EpicCount));
        OnPropertyChanged(nameof(XboxCount));
        RefreshView();
    }

    private async Task LaunchAsync(Game game)
    {
        try
        {
            _launcher.Launch(game);
            if (!game.Installed)
            {
                var store = game.Platform == "epic" ? "Epic Games" : "Steam";
                Status = Loc.Get("Installing", store, game.Title);
                return;
            }
            Status = Loc.Get("Launching", game.Title);
            var played = await _tracker.TrackAsync(game);
            if (played is { } t)
                Status = Loc.Get("Played", game.Title, (int)t.TotalHours, t.Minutes);
        }
        catch (Exception ex)
        {
            Status = Loc.Get("LaunchFailed", game.Title, ex.Message);
        }
    }
}
