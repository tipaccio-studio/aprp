# Advanced Installer (MSI): in preparation

The official installer is still the Inno Setup one ([../aprp.iss](../aprp.iss)). This folder prepares a Windows Installer (MSI) package built with [Advanced Installer](https://www.advancedinstaller.com/). It will ship next to the Inno Setup installer, or replace it, once the free open-source licence is active.

- [make-msi.ps1](make-msi.ps1) generates the project from a command file (`/newproject` + `/execute`) and builds `dist\aprp-<version>.msi` from `dist\aprp.exe`. Nothing binary is kept in git.
- Dialog art comes from `tools/make_assets.py`: `installer/art/msi-dialog.bmp` (493×312) and `msi-banner.bmp` (493×58).
- Languages: English plus Italian (1040), Spanish (3082), French (1036), German (1031) and Portuguese (BR) (1046).

**Why a licence is needed:** custom banners and images, multilingual packages and command-line project editing are not in the free edition. Caphyon offers free licences to open-source projects.

## Still to do once the licence arrives

1. Install Advanced Installer (`winget install Caphyon.AdvancedInstaller`) and run `AdvancedInstaller.com /register <licence id>`.
2. Run `.\build.ps1 -Stage app`, then `.\installer\advinst\make-msi.ps1`, and test the MSI. The script hasn't been run yet because it needs the licence.
3. In the generated project, check the settings that the command line doesn't cover: per-user install, "Launch aprp" at the end, and the `Language` registry value.
4. Add the MSI to `.github/workflows/release.yml` (a step that registers the licence from a secret) and to SignPath (a `msi-file` artifact configuration).

## Licence request email

To **support@advancedinstaller.com**, subject *Open-source licence request: aprp*:

> Hello,
>
> I'm the maintainer of **aprp**, a free and open-source (MIT) Windows game launcher that brings together Steam, Epic Games, Xbox and Modrinth games in one library.
>
> - Repository: https://github.com/tipaccio-studio/aprp
> - Releases: https://github.com/tipaccio-studio/aprp/releases
> - Licence: MIT
>
> We would like to ship an MSI installer built with Advanced Installer, with our own dialog artwork and six languages (EN, IT, ES, FR, DE, PT-BR), built in GitHub Actions. Would you be able to provide a free licence for this open-source project? We'd be happy to credit Advanced Installer in the README and on the releases page.
>
> Thank you,
> Tipaccio Studio
