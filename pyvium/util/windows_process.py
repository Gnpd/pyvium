'''Win32 process helpers used by the IviumSoft instance manager.

All functions take plain values (a PID or an exe path), use only stdlib
ctypes (no extra dependencies), and resolve the Win32 APIs at call time so
importing this module is harmless on any platform.'''
import ctypes
import ntpath
from ctypes import wintypes
from datetime import datetime

WM_CLOSE = 0x0010
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
TH32CS_SNAPPROCESS = 0x00000002

# Seconds between the Windows FILETIME epoch (1601) and the Unix epoch (1970).
_EPOCH_OFFSET_SECONDS = 11_644_473_600


class _PROCESSENTRY32W(ctypes.Structure):  # pylint: disable=too-few-public-methods
    _fields_ = (
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.c_size_t),
        ('th32ModuleID', wintypes.DWORD),
        ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD),
        ('pcPriClassBase', wintypes.LONG),
        ('dwFlags', wintypes.DWORD),
        ('szExeFile', wintypes.WCHAR * 260),
    )


def close_main_windows(pid: int) -> int:
    '''Posts WM_CLOSE to every visible top-level window of the process.

        Equivalent to the user clicking the window close button: IviumSoft
        shuts down gracefully and updates the driver bookkeeping, unlike a
        process kill. Returns the number of windows messaged (0 means the
        process has no visible window, possibly still starting up).'''
    user32 = ctypes.windll.user32
    closed_count = 0

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def report_window(window_handle, _lparam):
        nonlocal closed_count
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window_handle, ctypes.byref(window_pid))
        if window_pid.value == pid and user32.IsWindowVisible(window_handle):
            user32.PostMessageW(window_handle, WM_CLOSE, 0, 0)
            closed_count += 1
        return True  # keep enumerating

    user32.EnumWindows(report_window, 0)
    return closed_count


def is_process_running(pid: int) -> bool:
    '''Returns True if the process exists and has not exited.'''
    kernel32 = ctypes.windll.kernel32
    process_handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not process_handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code))
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(process_handle)


def find_pids_by_exe(exe_path: str) -> list[int]:
    '''Returns the pids of every running process started from exe_path.

        Matches by file name in the system process snapshot, then confirms
        the full image path where it can be read; a process whose path is
        readable and different (a same-named exe elsewhere) is excluded,
        one whose path cannot be read is kept on the name match alone.'''
    kernel32 = ctypes.windll.kernel32
    exe_name = ntpath.basename(exe_path).lower()
    normalized_path = ntpath.normpath(exe_path).lower()

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (0, -1):
        return []
    pids = []
    try:
        entry = _PROCESSENTRY32W()
        # pylint: disable-next=invalid-name,attribute-defined-outside-init
        entry.dwSize = ctypes.sizeof(entry)
        has_entry = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while has_entry:
            if entry.szExeFile.lower() == exe_name:
                image_path = _get_process_image_path(entry.th32ProcessID)
                if image_path is None or ntpath.normpath(image_path).lower() == normalized_path:
                    pids.append(entry.th32ProcessID)
            has_entry = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return pids


def get_process_creation_time(pid: int) -> datetime | None:
    '''Returns the process start time as a naive local datetime, or None
        if the process is gone or its times cannot be read.'''
    kernel32 = ctypes.windll.kernel32
    process_handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not process_handle:
        return None
    try:
        creation_time = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(
                process_handle,
                ctypes.byref(creation_time), ctypes.byref(exit_time),
                ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return None
    finally:
        kernel32.CloseHandle(process_handle)
    ticks = (creation_time.dwHighDateTime << 32) | creation_time.dwLowDateTime
    return datetime.fromtimestamp(ticks / 10_000_000 - _EPOCH_OFFSET_SECONDS)


def get_main_window_title(pid: int) -> str | None:
    '''Returns the title of the first visible top-level window owned by
        the process, or None if it has no visible window.'''
    user32 = ctypes.windll.user32
    title_found = None

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def report_window(window_handle, _lparam):
        nonlocal title_found
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window_handle, ctypes.byref(window_pid))
        if window_pid.value == pid and user32.IsWindowVisible(window_handle):
            buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(window_handle, buffer, len(buffer))
            title_found = buffer.value
            return False  # stop enumerating
        return True

    user32.EnumWindows(report_window, 0)
    return title_found


def _get_process_image_path(pid: int) -> str | None:
    kernel32 = ctypes.windll.kernel32
    process_handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not process_handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buffer))
        if kernel32.QueryFullProcessImageNameW(
                process_handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return None
    finally:
        kernel32.CloseHandle(process_handle)


def terminate_process(pid: int) -> bool:
    '''Forcefully terminates the process. Last resort: IviumSoft gets no
        chance to disconnect devices or update driver state. Returns True
        if the termination call succeeded.'''
    kernel32 = ctypes.windll.kernel32
    process_handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not process_handle:
        return False
    try:
        return bool(kernel32.TerminateProcess(process_handle, 1))
    finally:
        kernel32.CloseHandle(process_handle)
