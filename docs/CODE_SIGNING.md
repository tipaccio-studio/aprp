# Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io), certificate by [SignPath Foundation](https://signpath.org)

## What is signed

Release binaries published on [GitHub Releases](https://github.com/tipaccio-studio/aprp/releases):

- `aprp-setup-<version>.exe`: the installer
- `aprp.exe`: the app, also available as a portable download and packaged inside the installer

Only binaries built from this repository's source code are signed. They are built by the [Build & release](../.github/workflows/release.yml) GitHub Actions workflow on GitHub-hosted runners, then submitted to SignPath, which verifies that they come from that workflow before signing. Third-party components (the .NET runtime, the Python runtime, the PyInstaller bootloader) are bundled unmodified and listed in [THIRD-PARTY-NOTICES](../THIRD-PARTY-NOTICES.md).

Every release is signed only after a project approver manually approves the signing request.

## Team roles

| Role | Members |
|---|---|
| Committers and reviewers | [@tipaccio-studio](https://github.com/tipaccio-studio) |
| Approvers | [@tipaccio-studio](https://github.com/tipaccio-studio) |

aprp is made by [Tipaccio Studio](https://tipacciostudio.com/).

Contributions from people outside this list are reviewed by a committer before they are merged. All team members use multi-factor authentication on GitHub and SignPath.

## Privacy policy

See [PRIVACY.md](PRIVACY.md). In short, aprp contacts public store and Wikipedia services to download game descriptions and artwork. It sends no personal data, account data or telemetry, and nothing is sent to Tipaccio Studio.
