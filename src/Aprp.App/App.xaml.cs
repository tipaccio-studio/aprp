using System.IO;
using System.Windows;
using System.Windows.Threading;

namespace Aprp;

public partial class App : Application
{
    private static readonly string CrashLog = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "aprp", "crash.log");

    public App()
    {
        // Never vanish silently: log the error and tell the user where the details are.
        DispatcherUnhandledException += (_, e) =>
        {
            Report(e.Exception);
            e.Handled = true;
            Shutdown(1);
        };
        AppDomain.CurrentDomain.UnhandledException += (_, e) => Report(e.ExceptionObject as Exception);
    }

    private static void Report(Exception? ex)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(CrashLog)!);
            File.AppendAllText(CrashLog, $"[{DateTime.Now:u}] {ex}\n\n");
        }
        catch (IOException)
        {
        }
        MessageBox.Show($"aprp: {ex?.GetBaseException().Message}\n\n{CrashLog}", "aprp",
                        MessageBoxButton.OK, MessageBoxImage.Error);
    }
}
