using System.Runtime.InteropServices;

namespace Aprp.Services;

/// <summary>P/Invoke surface of native/include/aprp_native.h.</summary>
internal static class NativeMethods
{
    private const string Dll = "aprp_native.dll";

    public const int Ok = 0;
    public const int NotFound = 1;
    public const int Timeout = 2;

    [DllImport(Dll, CharSet = CharSet.Unicode, CallingConvention = CallingConvention.Cdecl)]
    public static extern int aprp_find_process_in_dir(string installDir, out uint pid);

    [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)]
    public static extern int aprp_wait_for_exit(uint pid, uint timeoutMs);

    [DllImport(Dll, CallingConvention = CallingConvention.Cdecl)]
    public static extern int aprp_get_working_set(uint pid, out ulong bytes);

    private static readonly Lazy<bool> _isAvailable = new(() =>
    {
        try
        {
            aprp_get_working_set(0, out _);
            return true;
        }
        catch (Exception ex) when (ex is DllNotFoundException or EntryPointNotFoundException or BadImageFormatException)
        {
            return false;
        }
    });

    public static bool IsAvailable => _isAvailable.Value;
}
