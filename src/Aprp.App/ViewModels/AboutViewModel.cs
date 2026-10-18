using System.Diagnostics;
using System.Windows;
using System.Windows.Input;
using Aprp.Services;

namespace Aprp.ViewModels;

/// <summary>The "About" panel: version, studio, updates and uninstall.</summary>
public sealed class AboutViewModel : ObservableObject
{
    private readonly UpdateService _updates = new();
    private UpdateInfo? _available;

    public AboutViewModel()
    {
        OpenCommand = new RelayCommand(_ => IsOpen = true);
        CloseCommand = new RelayCommand(_ => { IsOpen = false; IsConfirmingUninstall = false; });
        OpenUrlCommand = new RelayCommand(p => { if (p is string url) AppInfo.OpenUrl(url); });
        CheckCommand = new RelayCommand(async _ => await CheckAsync(userAsked: true), _ => !IsBusy);
        InstallUpdateCommand = new RelayCommand(async _ => await InstallUpdateAsync(), _ => !IsBusy && _available is not null);
        UninstallCommand = new RelayCommand(_ => Uninstall(), _ => Uninstaller is not null && !IsBusy);
        AskUninstallCommand = new RelayCommand(_ => IsConfirmingUninstall = true, _ => IsInstalled);
        CancelUninstallCommand = new RelayCommand(_ => IsConfirmingUninstall = false);
        Uninstaller = AppInfo.FindUninstaller();
    }

    public ICommand OpenCommand { get; }
    public ICommand CloseCommand { get; }
    public ICommand OpenUrlCommand { get; }
    public ICommand CheckCommand { get; }
    public ICommand InstallUpdateCommand { get; }
    public ICommand UninstallCommand { get; }

    public string Version => Loc.Get("VersionLabel", AppInfo.VersionText);
    public string StudioUrl => AppInfo.StudioUrl;
    public string RepositoryUrl => AppInfo.RepositoryUrl;
    public string LicenseUrl => AppInfo.LicenseUrl;
    public string PrivacyUrl => AppInfo.PrivacyUrl;

    /// <summary>Path of the Inno Setup uninstaller, or null for a portable copy.</summary>
    public string? Uninstaller { get; }
    public bool IsInstalled => Uninstaller is not null;

    private bool _isOpen;
    public bool IsOpen { get => _isOpen; set => SetField(ref _isOpen, value); }

    private bool _isBusy;
    public bool IsBusy
    {
        get => _isBusy;
        private set { if (SetField(ref _isBusy, value)) CommandManager.InvalidateRequerySuggested(); }
    }

    private bool _isUpdateAvailable;
    public bool IsUpdateAvailable { get => _isUpdateAvailable; private set => SetField(ref _isUpdateAvailable, value); }

    private string _updateStatus = "";
    public string UpdateStatus { get => _updateStatus; private set => SetField(ref _updateStatus, value); }

    private bool _isConfirmingUninstall;
    public bool IsConfirmingUninstall { get => _isConfirmingUninstall; set => SetField(ref _isConfirmingUninstall, value); }

    public ICommand AskUninstallCommand { get; }
    public ICommand CancelUninstallCommand { get; }

    /// <summary>Re-read texts after a language change.</summary>
    public void Refresh()
    {
        OnPropertyChanged(nameof(Version));
        if (_available is not null) UpdateStatus = Loc.Get("UpdateAvailable", Short(_available.Version));
    }

    /// <summary>Silent at startup (no message unless there's an update); verbose when the user asks.</summary>
    public async Task CheckAsync(bool userAsked)
    {
        if (IsBusy) return;
        IsBusy = true;
        if (userAsked) UpdateStatus = Loc.Get("Checking");
        try
        {
            _available = await _updates.CheckAsync();
            IsUpdateAvailable = _available is not null;
            UpdateStatus = _available is not null ? Loc.Get("UpdateAvailable", Short(_available.Version))
                         : userAsked ? Loc.Get("UpToDate") : "";
        }
        catch (Exception ex)
        {
            if (userAsked) UpdateStatus = Loc.Get("UpdateFailed", ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task InstallUpdateAsync()
    {
        if (_available is null) return;
        if (!IsInstalled || _available.SetupUrl is null)
        {
            // Portable copy: the new version is a new file, so send people to the release page.
            AppInfo.OpenUrl(_available.PageUrl);
            return;
        }
        IsBusy = true;
        try
        {
            await _updates.DownloadAndRunAsync(_available, new Progress<int>(p => UpdateStatus = Loc.Get("Downloading", p)));
            Application.Current.Shutdown();   // the installer upgrades aprp in place
        }
        catch (Exception ex)
        {
            UpdateStatus = Loc.Get("UpdateFailed", ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }

    private void Uninstall()
    {
        if (Uninstaller is null) return;
        // /SILENT: progress only (we already asked). The uninstaller still asks whether to keep
        // the library and settings, and requests admin rights itself for all-users installs.
        Process.Start(new ProcessStartInfo(Uninstaller) { UseShellExecute = true, Arguments = "/SILENT" });
        Application.Current.Shutdown();
    }

    private static string Short(Version v) => $"{v.Major}.{v.Minor}.{v.Build}";
}
