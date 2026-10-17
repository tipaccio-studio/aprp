using System.ComponentModel;
using System.Globalization;
using Microsoft.Win32;

namespace Aprp;

/// <summary>
/// UI strings in six languages, switchable at runtime.
/// XAML: Text="{Binding [Play], Source={x:Static local:Loc.Instance}}"
/// Code: Loc.Get("Summary", total, installed)
///
/// The language is read from HKCU (then HKLM) \Software\aprp\Language, which the
/// installer writes from the language chosen during setup; otherwise the Windows UI language.
/// </summary>
public sealed class Loc : INotifyPropertyChanged
{
    // Lazy: static initializers run in source order, and the constructor needs Languages/Strings below.
    private static readonly Lazy<Loc> _instance = new(() => new Loc());
    public static Loc Instance => _instance.Value;

    public static IReadOnlyList<LanguageOption> Languages { get; } = new[]
    {
        new LanguageOption("it", "Italiano"),
        new LanguageOption("en", "English"),
        new LanguageOption("es", "Español"),
        new LanguageOption("fr", "Français"),
        new LanguageOption("de", "Deutsch"),
        new LanguageOption("pt", "Português"),
    };

    private const string RegistryKey = @"Software\aprp";
    private string _language = "en";

    private Loc() => _language = Detect();

    public event PropertyChangedEventHandler? PropertyChanged;

    public string Language => _language;
    public string LanguageName => Languages.First(l => l.Code == _language).Name;

    public string this[string key] =>
        Strings.TryGetValue(key, out var row) && row.TryGetValue(_language, out var text) ? text
        : Strings.TryGetValue(key, out row) && row.TryGetValue("en", out text) ? text
        : key;

    public static string Get(string key, params object[] args) =>
        args.Length == 0 ? Instance[key] : string.Format(Instance[key], args);

    public void SetLanguage(string code)
    {
        if (Languages.All(l => l.Code != code) || code == _language) return;
        _language = code;
        try
        {
            using var key = Registry.CurrentUser.CreateSubKey(RegistryKey);
            key.SetValue("Language", code);
        }
        catch (Exception)
        {
            // Not persisting the choice is fine; it still applies for this session.
        }
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs("Item[]"));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(Language)));
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(LanguageName)));
    }

    private static string Detect()
    {
        foreach (var hive in new[] { Registry.CurrentUser, Registry.LocalMachine })
        {
            try
            {
                using var key = hive.OpenSubKey(RegistryKey);
                if (key?.GetValue("Language") is string saved && Languages.Any(l => l.Code == saved))
                    return saved;
            }
            catch (Exception)
            {
                // Unreadable key: fall through to the next source.
            }
        }
        var ui = CultureInfo.CurrentUICulture.TwoLetterISOLanguageName;
        return Languages.Any(l => l.Code == ui) ? ui : "en";
    }

    //                                   it, en, es, fr, de, pt
    private static Dictionary<string, string> Row(string it, string en, string es, string fr, string de, string pt) =>
        new() { ["it"] = it, ["en"] = en, ["es"] = es, ["fr"] = fr, ["de"] = de, ["pt"] = pt };

    private static readonly Dictionary<string, Dictionary<string, string>> Strings = new()
    {
        ["Tagline"] = Row("Tutti i tuoi giochi", "All your games", "Todos tus juegos", "Tous vos jeux", "Alle deine Spiele", "Todos os seus jogos"),
        ["Library"] = Row("LIBRERIA", "LIBRARY", "BIBLIOTECA", "BIBLIOTHÈQUE", "BIBLIOTHEK", "BIBLIOTECA"),
        ["AllGames"] = Row("Tutti i giochi", "All games", "Todos los juegos", "Tous les jeux", "Alle Spiele", "Todos os jogos"),
        ["InstalledOnly"] = Row("Solo installati", "Installed only", "Solo instalados", "Installés uniquement", "Nur installierte", "Apenas instalados"),
        ["Refresh"] = Row("Aggiorna libreria", "Refresh library", "Actualizar biblioteca", "Actualiser", "Aktualisieren", "Atualizar biblioteca"),
        ["YourLibrary"] = Row("La tua libreria", "Your library", "Tu biblioteca", "Votre bibliothèque", "Deine Bibliothek", "Sua biblioteca"),
        ["Search"] = Row("Cerca un gioco…", "Search games…", "Buscar un juego…", "Rechercher un jeu…", "Spiel suchen…", "Buscar um jogo…"),
        ["Play"] = Row("Gioca", "Play", "Jugar", "Jouer", "Spielen", "Jogar"),
        ["Install"] = Row("Installa", "Install", "Instalar", "Installer", "Installieren", "Instalar"),
        ["OpenFolder"] = Row("Apri cartella", "Open folder", "Abrir carpeta", "Ouvrir le dossier", "Ordner öffnen", "Abrir pasta"),
        ["Installed"] = Row("Installato", "Installed", "Instalado", "Installé", "Installiert", "Instalado"),
        ["NotInstalled"] = Row("Non installato", "Not installed", "No instalado", "Non installé", "Nicht installiert", "Não instalado"),
        ["Playing"] = Row("In gioco", "Playing", "Jugando", "En jeu", "Läuft", "Jogando"),
        ["PlayingBadge"] = Row("IN GIOCO", "PLAYING", "JUGANDO", "EN JEU", "LÄUFT", "JOGANDO"),
        ["Language"] = Row("Lingua", "Language", "Idioma", "Langue", "Sprache", "Idioma"),
        ["Scanning"] = Row("Cerco i tuoi giochi…", "Looking for your games…", "Buscando tus juegos…", "Recherche de vos jeux…", "Suche nach deinen Spielen…", "Procurando seus jogos…"),
        ["Metadata"] = Row("Aggiorno descrizioni e immagini…", "Updating descriptions and artwork…", "Actualizando descripciones e imágenes…", "Mise à jour des descriptions et images…", "Beschreibungen und Bilder werden geladen…", "Atualizando descrições e imagens…"),
        ["Summary"] = Row("{0} giochi · {1} installati", "{0} games · {1} installed", "{0} juegos · {1} instalados", "{0} jeux · {1} installés", "{0} Spiele · {1} installiert", "{0} jogos · {1} instalados"),
        ["Problems"] = Row("Problemi", "Problems", "Problemas", "Problèmes", "Probleme", "Problemas"),
        ["ScanFailed"] = Row("Scansione non riuscita: {0}", "Scan failed: {0}", "Error al buscar juegos: {0}", "Échec de l'analyse : {0}", "Suche fehlgeschlagen: {0}", "Falha na busca: {0}"),
        ["Launching"] = Row("Avvio {0}…", "Launching {0}…", "Iniciando {0}…", "Lancement de {0}…", "{0} wird gestartet…", "Iniciando {0}…"),
        ["Installing"] = Row("Apro {0} per installare {1}. Premi Aggiorna quando ha finito.",
                             "Opening {0} to install {1}. Press Refresh when it's done.",
                             "Abriendo {0} para instalar {1}. Pulsa Actualizar cuando termine.",
                             "Ouverture de {0} pour installer {1}. Cliquez sur Actualiser une fois terminé.",
                             "{0} wird geöffnet, um {1} zu installieren. Danach auf Aktualisieren klicken.",
                             "Abrindo {0} para instalar {1}. Clique em Atualizar quando terminar."),
        ["Played"] = Row("Hai giocato a {0} per {1} h {2} min.", "You played {0} for {1} h {2} min.", "Jugaste a {0} durante {1} h {2} min.",
                         "Vous avez joué à {0} pendant {1} h {2} min.", "Du hast {0} {1} Std. {2} Min. gespielt.", "Você jogou {0} por {1} h {2} min."),
        ["LaunchFailed"] = Row("Impossibile avviare {0}: {1}", "Couldn't launch {0}: {1}", "No se pudo iniciar {0}: {1}",
                               "Impossible de lancer {0} : {1}", "{0} konnte nicht gestartet werden: {1}", "Não foi possível iniciar {0}: {1}"),
        ["NoNative"] = Row("aprp_native.dll mancante: tempo di gioco non registrato.", "aprp_native.dll missing: playtime isn't tracked.",
                           "Falta aprp_native.dll: no se registra el tiempo de juego.", "aprp_native.dll manquant : temps de jeu non enregistré.",
                           "aprp_native.dll fehlt: Spielzeit wird nicht erfasst.", "aprp_native.dll ausente: o tempo de jogo não é registrado."),
    };
}

public sealed record LanguageOption(string Code, string Name);
