#include "aprp_native.h"

#include <windows.h>
#include <psapi.h>
#include <tlhelp32.h>

#include <string>
#include <vector>

namespace {

struct Handle {
    HANDLE h;
    explicit Handle(HANDLE handle) : h(handle) {}
    ~Handle() { if (h && h != INVALID_HANDLE_VALUE) CloseHandle(h); }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
    explicit operator bool() const { return h && h != INVALID_HANDLE_VALUE; }
};

// Absolute path, backslashes, trailing separator so "C:\Games\Foo" doesn't match "C:\Games\FooBar".
std::wstring NormalizeDir(const wchar_t* dir) {
    std::wstring out(dir);
    DWORD needed = GetFullPathNameW(dir, 0, nullptr, nullptr);
    if (needed > 0) {
        std::vector<wchar_t> buf(needed);
        DWORD n = GetFullPathNameW(dir, needed, buf.data(), nullptr);
        if (n > 0 && n < needed) out.assign(buf.data(), n);
    }
    for (auto& c : out) if (c == L'/') c = L'\\';
    if (!out.empty() && out.back() != L'\\') out.push_back(L'\\');
    return out;
}

bool StartsWithNoCase(const std::wstring& s, const std::wstring& prefix) {
    return s.size() >= prefix.size() &&
           CompareStringOrdinal(s.c_str(), static_cast<int>(prefix.size()),
                                prefix.c_str(), static_cast<int>(prefix.size()), TRUE) == CSTR_EQUAL;
}

}  // namespace

extern "C" APRP_API int32_t aprp_find_process_in_dir(const wchar_t* install_dir, uint32_t* pid_out) {
    if (!install_dir || !*install_dir || !pid_out) return APRP_ERROR;
    const std::wstring prefix = NormalizeDir(install_dir);

    Handle snap(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0));
    if (!snap) return APRP_ERROR;

    PROCESSENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    std::vector<wchar_t> path(32768);  // max extended-length path; reused for every process
    DWORD self = GetCurrentProcessId();
    DWORD best_pid = 0;
    SIZE_T best_ws = 0;

    for (BOOL ok = Process32FirstW(snap.h, &entry); ok; ok = Process32NextW(snap.h, &entry)) {
        if (entry.th32ProcessID == 0 || entry.th32ProcessID == self) continue;

        // LIMITED_INFORMATION works for most processes without elevation,
        // including games running under anti-cheat.
        Handle proc(OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, entry.th32ProcessID));
        if (!proc) continue;

        DWORD size = static_cast<DWORD>(path.size());
        if (!QueryFullProcessImageNameW(proc.h, 0, path.data(), &size)) continue;
        if (!StartsWithNoCase(std::wstring(path.data(), size), prefix)) continue;

        PROCESS_MEMORY_COUNTERS pmc{};
        SIZE_T ws = GetProcessMemoryInfo(proc.h, &pmc, sizeof(pmc)) ? pmc.WorkingSetSize : 0;
        if (best_pid == 0 || ws > best_ws) {
            best_pid = entry.th32ProcessID;
            best_ws = ws;
        }
    }

    if (best_pid == 0) return APRP_NOT_FOUND;
    *pid_out = best_pid;
    return APRP_OK;
}

extern "C" APRP_API int32_t aprp_wait_for_exit(uint32_t pid, uint32_t timeout_ms) {
    Handle proc(OpenProcess(SYNCHRONIZE, FALSE, pid));
    if (!proc) {
        return GetLastError() == ERROR_INVALID_PARAMETER ? APRP_NOT_FOUND : APRP_ERROR;
    }
    switch (WaitForSingleObject(proc.h, timeout_ms)) {
        case WAIT_OBJECT_0: return APRP_OK;
        case WAIT_TIMEOUT:  return APRP_TIMEOUT;
        default:            return APRP_ERROR;
    }
}

extern "C" APRP_API int32_t aprp_get_working_set(uint32_t pid, uint64_t* bytes_out) {
    if (!bytes_out) return APRP_ERROR;
    Handle proc(OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
    if (!proc) return APRP_NOT_FOUND;
    PROCESS_MEMORY_COUNTERS pmc{};
    if (!GetProcessMemoryInfo(proc.h, &pmc, sizeof(pmc))) return APRP_ERROR;
    *bytes_out = pmc.WorkingSetSize;
    return APRP_OK;
}
