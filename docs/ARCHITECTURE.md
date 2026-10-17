# aprp: architecture & developer guide

How aprp is built and how to work on it. For what the app does, see the [README](../README.md).

## 1. Architecture

```
┌──────────────────────────── aprp.exe (C# / WPF, .NET) ─────────────────────────────┐
│  MainWindow.xaml ── MainViewModel ──┬── ScannerService ──spawn──► Python sidecar   │
│                                     │      (stdout JSON)          aprp_scanner     │
│                                     ├── LauncherService ──ShellExecute──► steam:// │
│                                     │                         com.epicgames...://  │
│                                     │                         shell:AppsFolder\…   │
│                                     └── SessionTracker ──P/Invoke──► aprp_native.dll│
│                                                                     (C++, Win32)   │
└────────────────────────────────────────────────────────────────────────────────────┘
          %LOCALAPPDATA%\aprp\library.json  ← last scan, shown instantly at startup
```

| Layer | Language | Why this language | Talks to the host via |
|---|---|---|---|
| UI, orchestration, launching | **C#** (WPF) | Native Windows UI, data binding, easy `ShellExecute` | n/a (it's the host) |
| Game detection & metadata | **Python** | Fast to iterate on file formats (VDF, JSON, XML), easy to add stores/APIs | Child process, **JSON on stdout** |
| Process tracking | **C++** | Direct Win32: ToolHelp snapshots, `QueryFullProcessImageNameW`, waitable process handles | **C ABI DLL + P/Invoke** |

Design decisions:

- **Process + JSON for Python, not embedding.** The scanner is a plain CLI (`python -m aprp_scanner scan`). It's crash-isolated (a bad manifest can't take down the UI), testable on its own, and ships as a single `aprp-scanner.exe` via PyInstaller. Each platform scans independently, and failures come back in `errors[]` instead of aborting.
- **The scanner owns the launch URI.** Each game record carries a ready-to-use `launch_uri`, so the C# side has no store-specific logic. Adding a store (GOG, EA, Ubisoft) is a Python-only change.
- **C ABI for C++, not C++/CLI.** Plain `extern "C"` functions work with `DllImport`, need no mixed-mode assembly, and the DLL is statically linked (no VC++ redistributable needed). If the DLL is missing, the app still runs with playtime tracking disabled.
- **Launch through the store, never the .exe.** Store protocols keep DRM, updates, cloud saves and overlays working. Xbox executables are ACL-protected, so running them directly fails anyway.
- **Why C++ is needed at all:** every store URI returns immediately and hands off to another launcher, so there's no child process to wait on. The native monitor finds whichever process is running *from the game's install folder*, picks the largest one by working set (so it skips crash reporters and anti-cheat helpers), and blocks on its handle. `SessionTracker` keeps watching for a short window after exit to handle bootstrapper → game hand-offs.

### Data contract (`scanner/aprp_scanner/models.py` ⇄ `src/Aprp.App/Models/Game.cs`)

```json
{
  "games": [{
    "id": "steam:3241660", "platform": "steam", "title": "R.E.P.O.",
    "install_dir": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\REPO",
    "launch_uri": "steam://rungameid/3241660",
    "cover": "C:\\...\\librarycache\\3241660\\library_600x900.jpg",
    "size_bytes": 1234567890
  }],
  "errors": [{ "platform": "epic", "message": "..." }]
}
```

## 2. Detection & launch logic

| Store | Where installed games are found | Launch |
|---|---|---|
| **Steam** ([steam.py](../scanner/aprp_scanner/steam.py)) | Registry `HKCU\Software\Valve\Steam\SteamPath` → `steamapps\libraryfolders.vdf` (all library drives) → each `appmanifest_<appid>.acf`. Installed when `StateFlags & 4`. | `steam://rungameid/<appid>` |
| **Epic** ([epic.py](../scanner/aprp_scanner/epic.py)) | `HKLM\SOFTWARE\WOW6432Node\Epic Games\EpicGamesLauncher\AppDataPath` (fallback `%ProgramData%\Epic\EpicGamesLauncher\Data\Manifests`) → `*.item` JSON. Skips incomplete installs, DLC, and non-game items such as Unreal Engine. | `com.epicgames.launcher://apps/<ns>%3A<catalogId>%3A<appName>?action=launch&silent=true` |
| **Xbox** ([xbox.py](../scanner/aprp_scanner/xbox.py)) | `Get-AppxPackage`, keeping only packages whose install folder has `MicrosoftGame.config` (GDK games). Title and logo come from `<ShellVisuals>`, the AppId from the package manifest. | `explorer.exe shell:AppsFolder\<PackageFamilyName>!<AppId>` |

**Owned but not installed** games are listed too (dimmed, with an Install button), read from local caches without network access or an API key:

- **Steam:** app ids from `appcache\librarycache\` + `userdata\*\config\localconfig.vdf`, with names and types from the binary `appcache\appinfo.vdf` ([steam_appinfo.py](../scanner/aprp_scanner/steam_appinfo.py), v28/v29 format). Only `type == game` is kept. Install: `steam://install/<appid>`.
- **Epic:** `Data\Catalog\catcache.bin` (base64 JSON), keeping items in the `games` category that aren't add-ons or DLC. Box art comes from `keyImages`. Install: the same launcher URI with `action=install`.

Both caches are filled by the store client, so a game bought on another device shows up after that client has synced once.

Covers: Steam's local `appcache\librarycache` (old and 2024+ layouts), falling back to the Steam CDN. Xbox uses the package logo. Epic has no local art, so the UI shows a placeholder.

Security: `LauncherService` only shell-executes the three URI prefixes above. `library.json` is user-writable, so arbitrary strings from it are never executed.

## 3. UI layout

```
┌─────────────┬─────────────────────────────────────────────────────┐
│ aprp        │ [ Search games…              ]                      │
│             │                                                     │
│ LIBRARY     │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│ All games 8 │ │cover │ │cover │ │cover │ │cover │ │cover │  ← 2:3 │
│ Steam     4 │ │ ▶Play│ │      │ │RUNNING│ │      │ │      │  cards │
│ Epic      0 │ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘        │
│ Xbox      4 │  Title    Title    Title    Title    Title           │
│             │  Steam    Xbox     Epic     ...                      │
│             │                                                     │
│ [⟳ Rescan]  ├─────────────────────────────────────────────────────┤
│             │ Played R.E.P.O. for 1h 12m.            (status bar) │
└─────────────┴─────────────────────────────────────────────────────┘
```

- **Sidebar:** platform filter with counts, and Rescan at the bottom.
- **Grid:** cover cards. Hovering shows a Play button and an accent border. Double-click also launches. A green **RUNNING** badge appears while the native monitor sees the game.
- **Status bar:** scan results, per-platform errors, and the last session's length.

Files: [MainWindow.xaml](../src/Aprp.App/MainWindow.xaml), [App.xaml](../src/Aprp.App/App.xaml) (palette + styles), [MainViewModel.cs](../src/Aprp.App/ViewModels/MainViewModel.cs).

## 4. Setup & run

### Prerequisites

1. **.NET SDK 10** (LTS): `winget install Microsoft.DotNet.SDK.10`
2. **Python 3.10+** on `PATH` (stdlib only, no `pip install` needed). Set `APRP_PYTHON` to use a specific interpreter.
3. **Visual Studio 2022 Build Tools** with the *Desktop development with C++* workload, plus **CMake 3.20+**.

### Build & run

```powershell
# 1) Native DLL  -> native\bin\aprp_native.dll
cmake -S native -B native\build -A x64
cmake --build native\build --config Release

# 2) Check the scanner on its own
cd scanner; python -m aprp_scanner scan --pretty; cd ..

# 3) Run the app (copies the scanner + DLL next to aprp.exe)
dotnet run --project src\Aprp.App
```

> **Path length:** MSBuild fails if the project lives in a very deep folder (260-character limit). Keep the repo somewhere short like `C:\dev\aprp`.

### Tests

```powershell
cd scanner; python -m pytest tests     # or: pip install pytest first
```

### Shipping: one `aprp.exe`

```powershell
.\build.ps1
```

[build.ps1](../build.ps1) builds the C++ DLL, freezes the scanner with PyInstaller, and publishes `dist\aprp.exe` (about 72 MB). That single file contains the .NET runtime, the native DLL and the frozen scanner, which is extracted once to `%LOCALAPPDATA%\aprp\bin`. Users don't need Python or .NET installed.

### Installer

`build.ps1` also produces `dist\aprp-setup-<version>.exe` with [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`). The script is [installer/aprp.iss](../installer/aprp.iss).

![installer](installer.png)

- **Languages:** Italian, English, Spanish, French, German and Portuguese (BR). The setup language is detected from Windows and can be changed in the language dialog. It is saved to `HKCU\Software\aprp\Language`, so the app opens in the same language.
- **Artwork:** the aprp banner on the welcome and finish pages, and the logo in the page headers and on the setup and uninstall icons. All of it comes from `tools/make_assets.py` (`installer/art/*.bmp` at 100/150/200% DPI).
- **Install mode:** per-user by default (`%LOCALAPPDATA%\Programs\aprp`, no admin prompt), or for all users.
- **Options:** Start menu shortcut, optional desktop icon, optional *start with Windows*, and *launch aprp* at the end. Setup closes a running aprp before upgrading.
- **Uninstall:** removes the app and the extracted scanner, then asks whether to also delete the library cache and settings. The default is to keep them.
- Silent install: `aprp-setup-0.2.0.exe /VERYSILENT /CURRENTUSER /LANG=en`.

### Code signing

The build signs every executable when a certificate is configured: `aprp-scanner.exe` before it's embedded, `aprp.exe`, the installer and the uninstaller inside it. Signatures use SHA-256 with an RFC 3161 timestamp, so they stay valid after the certificate expires. Signing is done by [tools/sign.ps1](../tools/sign.ps1) (signtool from the Windows SDK), configured with environment variables:

```powershell
# A certificate in the Windows store (Certum SimplySign, USB token, any OV/EV cert):
$env:APRP_SIGN_THUMBPRINT = "<SHA-1 thumbprint>"
# ...or Azure Artifact Signing:
$env:APRP_SIGN_AZURE_JSON = "C:\path\metadata.json"; $env:APRP_SIGN_AZURE_DLIB = "C:\path\Azure.CodeSigning.Dlib.dll"

.\build.ps1 -RequireSign     # fails instead of producing an unsigned release
```

Without a certificate the build still works, but the output is unsigned (with a warning). The whole chain has been tested with a throwaway self-signed certificate.

**Getting a certificate.** It has to come from a CA that Windows trusts and be issued to you or your organisation after an identity check. A self-signed certificate doesn't help with SmartScreen. Options to compare (check current prices and eligibility):

| Option | Notes |
|---|---|
| [SignPath Foundation](https://signpath.org/) | Free for open-source projects. You apply, and releases are built and signed in CI (GitHub Actions). The publisher shown is "SignPath Foundation". |
| [Certum Open Source Code Signing](https://www.certum.eu/) | Low-cost certificate for individual open-source developers. The cloud key (SimplySign) appears in the Windows certificate store, so set `APRP_SIGN_THUMBPRINT`. The publisher is your name. |
| [Azure Artifact Signing](https://learn.microsoft.com/azure/trusted-signing/) | Microsoft's managed signing, billed monthly, with restrictions on which countries and entity types qualify. Set `APRP_SIGN_AZURE_*`. |
| OV/EV certificate (DigiCert, Sectigo, …) | The classic route. More expensive, and the key lives on a hardware token or HSM. |

**What signing does and doesn't do.** A valid signature replaces "Unknown publisher" with your name and lets SmartScreen build **reputation** for your certificate. The warning fades as people download and run signed releases, but it isn't removed instantly, not even with EV certificates. Submitting new releases to [Microsoft's file submission portal](https://www.microsoft.com/wdsi/filesubmission) as a software developer can speed this up, and it also helps with antivirus false positives, which PyInstaller-built executables sometimes trigger.

### App languages

The UI is available in the same six languages ([Loc.cs](../src/Aprp.App/Loc.cs)) and switches live from the picker at the bottom of the sidebar. Game descriptions follow the chosen language: the scanner receives it as `APRP_LANG` and refetches metadata in that language. To add a language, add a column to `Loc.cs` and a `[Languages]` line to the .iss.

### Metadata & assets

- `scan --online` fills in descriptions, banners and developers from [metadata.py](../scanner/aprp_scanner/metadata.py) and caches them in `%LOCALAPPDATA%\aprp\metadata.json`. Sources: the Steam store, the Microsoft Store catalog, Steam store search for Epic titles, and Wikipedia as a fallback, all in the Windows user language. The app first shows the offline scan, then merges the online results in place.
- `python tools/make_assets.py` regenerates the app icon ([Assets/aprp.ico](../src/Aprp.App/Assets/aprp.ico)) and the Steam, Epic and Xbox vector logos ([PlatformLogos.xaml](../src/Aprp.App/Assets/PlatformLogos.xaml), from Simple Icons, CC0).

## Next steps

- **Persistent playtime:** store `SessionTracker` results in `library.json`.
- **Metadata:** Epic/Xbox box art through SteamGridDB (needs an API key) as a `metadata.py` stage in the scanner.
- **Filter non-games:** Steam lists tools like Wallpaper Engine. Use the Steam store API `type` field or a user "hide" toggle.
- **Large libraries:** swap `WrapPanel` for a virtualizing wrap panel once you're past a few hundred games.
- **More stores:** GOG (`HKLM\SOFTWARE\WOW6432Node\GOG.com\Games`), EA app, Ubisoft Connect. Each is one new Python module.
