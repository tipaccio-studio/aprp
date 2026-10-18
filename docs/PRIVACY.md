# Privacy policy

aprp is a desktop app. It has no account, no telemetry, no analytics and no server of its own. Nothing you do in aprp is sent to Tipaccio Studio.

## What stays on your computer

aprp reads the local data of Steam, the Epic Games Launcher, the Microsoft Store/Xbox app and the Modrinth App to find your games and their playtime. Nothing from the Modrinth App is sent anywhere. It saves its library, metadata cache and settings under `%LOCALAPPDATA%\aprp` and in `HKCU\Software\aprp`. The uninstaller removes these if you ask it to.

## What is sent over the network

To show descriptions and artwork, aprp makes requests to these public services when it starts and when you press **Refresh library**:

| Service | Sent | Purpose |
|---|---|---|
| Steam store (`store.steampowered.com`) | Steam app ids, game titles (for Epic games), your language | Descriptions, developer names |
| Microsoft Store catalog (`displaycatalog.mp.microsoft.com`) | Package names of your Xbox/Store games, your language | Descriptions, banners |
| Wikipedia (`*.wikipedia.org`) | Game titles, your language | Descriptions when a store has none |
| Image servers of Steam, Epic Games and Microsoft | Image addresses | Cover and banner images |

Like any web request, these services can see your IP address. They don't receive your account names, store credentials or any other personal data from aprp. Their own privacy policies apply: [Valve](https://store.steampowered.com/privacy_agreement/), [Microsoft](https://privacy.microsoft.com/privacystatement), [Wikimedia Foundation](https://foundation.wikimedia.org/wiki/Policy:Privacy_policy), [Epic Games](https://www.epicgames.com/site/privacypolicy).

When you press **Play** or **Install**, aprp only opens the game's own store client (Steam, Epic Games Launcher or Xbox app), and that client's privacy policy applies.

## Downloads

Release files are hosted on GitHub ([GitHub privacy statement](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement)) and signed through SignPath ([code signing policy](CODE_SIGNING.md)).
