// aprp_native: low-level process tracking for the aprp launcher.
//
// Launch URIs (steam://, com.epicgames.launcher://, shell:AppsFolder) return
// immediately and hand off to another launcher, so we can't just wait on the
// process we started. Instead we look for whichever process is running out of
// the game's install directory, then block on its handle.
//
// Plain C ABI so C# can P/Invoke it without C++/CLI.
#pragma once

#include <stdint.h>

#ifdef APRP_NATIVE_EXPORTS
#define APRP_API __declspec(dllexport)
#else
#define APRP_API __declspec(dllimport)
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum {
    APRP_OK = 0,
    APRP_NOT_FOUND = 1,
    APRP_TIMEOUT = 2,
    APRP_ERROR = -1,
};

// Finds a running process whose executable lives under `install_dir`.
// When several match (game + crash handler + anti-cheat), the one with the
// largest working set wins, which is almost always the game itself.
APRP_API int32_t aprp_find_process_in_dir(const wchar_t* install_dir, uint32_t* pid_out);

// Blocks until `pid` exits or `timeout_ms` elapses (0xFFFFFFFF = forever).
// Returns APRP_OK on exit, APRP_TIMEOUT, or APRP_NOT_FOUND if it already exited.
APRP_API int32_t aprp_wait_for_exit(uint32_t pid, uint32_t timeout_ms);

// Current working set of `pid`, in bytes (for the "now playing" panel).
APRP_API int32_t aprp_get_working_set(uint32_t pid, uint64_t* bytes_out);

#ifdef __cplusplus
}
#endif
