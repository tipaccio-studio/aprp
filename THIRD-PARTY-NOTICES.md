# Third-party notices

aprp's own code is under the [MIT License](LICENSE). It also contains or uses the following.

## Bundled in the release builds

| Component | Used for | License |
|---|---|---|
| [.NET runtime and WPF](https://github.com/dotnet/runtime) | Bundled in the self-contained `aprp.exe` | MIT |
| [Python](https://www.python.org/) runtime | Bundled in the frozen scanner | PSF License |
| [PyInstaller](https://pyinstaller.org/) bootloader | Freezing the scanner | GPL-2.0 with the bootloader exception, which allows distributing the frozen program under any license |
| [Simple Icons](https://simpleicons.org/) | Steam, Epic Games, Xbox and Modrinth logo paths (`src/Aprp.App/Assets/PlatformLogos.xaml`) | CC0-1.0 |

## Build tools (not redistributed)

[Inno Setup](https://jrsoftware.org/isinfo.php) (installer), [Pillow](https://python-pillow.org/) (asset generation), CMake and MSVC.

## Online data

When metadata is enabled, aprp downloads game descriptions and artwork at runtime from the Steam store, the Microsoft Store catalog and Wikipedia. That content belongs to its respective owners and is not part of this repository. Wikipedia text is available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

## Trademarks

Steam is a trademark of Valve Corporation. Epic Games is a trademark of Epic Games, Inc. Xbox and Minecraft are trademarks of Microsoft Corporation. Modrinth is a trademark of Rinth, Inc. aprp is an independent project and is not affiliated with or endorsed by any of them. Their logos are used only to show which store a game comes from.
