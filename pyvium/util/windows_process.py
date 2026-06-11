'''Win32 process helpers used by the IviumSoft instance manager.

All functions take a plain PID, use only stdlib ctypes (no extra
dependencies), and resolve the Win32 APIs at call time so importing this
module is harmless on any platform.'''
import ctypes
from ctypes import wintypes

WM_CLOSE = 0x0010
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259


def close_main_windows(pid: int) -> int:
    '''Posts WM_CLOSE to every visible top-level window of the process.

        Equivalent to the user clicking the window close button: IviumSoft
        shuts down gracefully and updates the driver bookkeeping, unlike a
        process kill. Returns the number of windows messaged (0 means the
        process has no visible window — possibly still starting up).'''
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
