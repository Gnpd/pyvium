'''Win32 process helpers used by the IviumSoft instance manager.

All functions take plain values (a PID or an exe path), use only stdlib
ctypes (no extra dependencies), and resolve the Win32 APIs at call time so
importing this module is harmless on any platform.'''
import ctypes
import ntpath
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime

WM_CLOSE = 0x0010
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
BM_CLICK = 0x00F5
VK_RETURN = 0x0D
GWL_STYLE = -16
BS_DEFPUSHBUTTON = 0x0001
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SYNCHRONIZE = 0x00100000
WAIT_TIMEOUT = 0x102
ERROR_ACCESS_DENIED = 5
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


@dataclass(frozen=True)
class WindowControl:
    '''One child control of a window: enough to recognise it and click it.'''
    hwnd: int
    class_name: str
    text: str
    is_default_button: bool


@dataclass(frozen=True)
class WindowInfo:
    '''A window and its child controls, as read from another process.'''
    hwnd: int
    class_name: str
    title: str
    controls: tuple[WindowControl, ...]


def list_visible_windows(pid: int) -> list[int]:
    '''Returns the handles of every visible top-level window of the process.

        The building block the close, title and dialog helpers share. A window
        appearing here that was not here a moment ago is how a modal raised in
        response to WM_CLOSE is spotted.'''
    user32 = ctypes.windll.user32
    handles = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def report_window(window_handle, _lparam):
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window_handle, ctypes.byref(window_pid))
        if window_pid.value == pid and user32.IsWindowVisible(window_handle):
            handles.append(window_handle)
        return True  # keep enumerating

    user32.EnumWindows(report_window, 0)
    return handles


def _window_class(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value


def _window_text(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(512)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def describe_window(hwnd: int) -> WindowInfo:
    '''Reads a window's class, title and child controls.

        Every child is reported rather than only the buttons, because what
        counts as a button is a caller's judgement: is_default_button flags the
        one Enter would activate (BS_DEFPUSHBUTTON), which is meaningful only
        for buttons and is False for everything else.'''
    user32 = ctypes.windll.user32
    controls = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def report_child(child_handle, _lparam):
        style = user32.GetWindowLongW(child_handle, GWL_STYLE)
        controls.append(WindowControl(
            hwnd=child_handle,
            class_name=_window_class(child_handle),
            text=_window_text(child_handle),
            is_default_button=bool(style & BS_DEFPUSHBUTTON),
        ))
        return True

    user32.EnumChildWindows(hwnd, report_child, 0)
    return WindowInfo(
        hwnd=hwnd,
        class_name=_window_class(hwnd),
        title=_window_text(hwnd),
        controls=tuple(controls),
    )


def is_window(hwnd: int) -> bool:
    '''True when the handle still names a window that exists.

        The handle a dead process registered outlives it as a plain number, so
        this is what tells a stale handle from a live one.'''
    return bool(ctypes.windll.user32.IsWindow(hwnd))


def click_button(hwnd: int) -> None:
    '''Posts BM_CLICK to a button control, as if it had been clicked.'''
    ctypes.windll.user32.PostMessageW(hwnd, BM_CLICK, 0, 0)


def press_enter(hwnd: int) -> None:
    '''Posts Enter to a window, activating its default button.

        The fallback for a dialog that did not answer a BM_CLICK on the button
        itself.'''
    user32 = ctypes.windll.user32
    user32.PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0)
    user32.PostMessageW(hwnd, WM_KEYUP, VK_RETURN, 0)


def close_main_windows(pid: int) -> int:
    '''Posts WM_CLOSE to every visible top-level window of the process.

        Equivalent to the user clicking the window close button: IviumSoft
        shuts down gracefully and updates the driver bookkeeping, unlike a
        process kill. Returns the number of windows messaged (0 means the
        process has no visible window, possibly still starting up).

        A graceful close is a request, not a guarantee: an application may
        answer it with a modal confirmation, which the caller has to handle.'''
    user32 = ctypes.windll.user32
    handles = list_visible_windows(pid)
    for window_handle in handles:
        user32.PostMessageW(window_handle, WM_CLOSE, 0, 0)
    return len(handles)


def is_process_running(pid: int) -> bool:
    '''Returns True if the process exists and has not exited.

        Liveness comes from waiting on the process handle with a zero timeout
        rather than from GetExitCodeProcess: that call reports STILL_ACTIVE
        (259) for a running process, which a process exiting with code 259 of
        its own is indistinguishable from.'''
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    process_handle = kernel32.OpenProcess(
        SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not process_handle:
        # Denied means the process is there but this caller cannot query it;
        # any other failure means it is genuinely gone.
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        return kernel32.WaitForSingleObject(process_handle, 0) == WAIT_TIMEOUT
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
                image_path = get_process_image_path(entry.th32ProcessID)
                if image_path is None or same_image_path(image_path, exe_path):
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
    for window_handle in list_visible_windows(pid):
        return _window_text(window_handle)
    return None


def same_image_path(image_path: str, exe_path: str) -> bool:
    '''True when two executable paths name the same file, comparing them
        case-insensitively and with separators normalised.'''
    return ntpath.normpath(image_path).lower() == ntpath.normpath(exe_path).lower()


def get_process_image_path(pid: int) -> str | None:
    '''Returns the full image path of the process, or None if it is gone or
        the path cannot be read.'''
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
