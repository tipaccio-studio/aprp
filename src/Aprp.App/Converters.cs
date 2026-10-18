using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Aprp;

/// <summary>Image path/URL -> downscaled bitmap; null (placeholder shows) when missing or broken.</summary>
/// <remarks>ConverterParameter = decode width in pixels (default 320).</remarks>
public sealed class ImageConverter : IValueConverter
{
    public object? Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is not string s || s.Length == 0) return null;
        try
        {
            var img = new BitmapImage();
            img.BeginInit();
            img.UriSource = new Uri(s, UriKind.Absolute);
            img.DecodePixelWidth = int.TryParse(parameter as string, out var w) ? w : 320; // keep memory low
            img.CacheOption = BitmapCacheOption.OnLoad; // don't hold Steam's cache files open
            img.EndInit();
            return img;
        }
        catch (Exception)
        {
            return null;
        }
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}

/// <summary>Platform id ("steam") -> Logo geometry | Name | Brush, chosen by ConverterParameter.</summary>
public sealed class PlatformConverter : IValueConverter
{
    private static readonly Dictionary<string, (string Name, string Resource, string Color)> Platforms = new()
    {
        ["steam"] = ("Steam", "SteamLogo", "#1B2838"),
        ["epic"] = ("Epic Games", "EpicLogo", "#2F2F2F"),
        ["xbox"] = ("Xbox", "XboxLogo", "#107C10"),
        ["all"] = ("Tutti i giochi", "AllLogo", "#7C5CFF"),
    };

    public object? Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is not string id || !Platforms.TryGetValue(id, out var p)) return null;
        return (parameter as string) switch
        {
            "Logo" => Application.Current.TryFindResource(p.Resource),
            "Brush" => new SolidColorBrush((Color)ColorConverter.ConvertFromString(p.Color)),
            _ => p.Name,
        };
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}

/// <summary>
/// RadioButton.IsChecked &lt;-&gt; a string property: checked when value == ConverterParameter,
/// and checking it sets the property. Works for mouse, keyboard (arrow keys) and UI Automation alike.
/// </summary>
public sealed class EqualsConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture) =>
        Equals(value as string, parameter as string);

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        value is true ? parameter : Binding.DoNothing;
}

public sealed class BytesConverter : IValueConverter
{
    public object? Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is not long bytes || bytes <= 0) return null;
        string[] units = { "B", "KB", "MB", "GB", "TB" };
        double size = bytes;
        var unit = 0;
        while (size >= 1024 && unit < units.Length - 1) { size /= 1024; unit++; }
        return $"{size:0.#} {units[unit]}";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}

/// <summary>Visible for non-empty strings / true / non-null; ConverterParameter="Invert" flips it.</summary>
public sealed class VisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        var visible = value switch
        {
            null => false,
            bool b => b,
            string s => s.Length > 0,
            int i => i != 0,
            _ => true,
        };
        if (parameter as string == "Invert") visible = !visible;
        return visible ? Visibility.Visible : Visibility.Collapsed;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) =>
        throw new NotSupportedException();
}
