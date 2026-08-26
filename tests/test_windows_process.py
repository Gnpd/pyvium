'''Tests for the Win32 process helpers, run against the real OS.

The instance-manager tests replace this whole layer with a fake, so the ctypes
calls themselves are only exercised here. PYVIUM is Windows-only (the package
loads the driver DLL at import), so these need no platform guard.
'''
# pylint: disable=missing-function-docstring
import os
import subprocess
import sys

import pytest

from pyvium.util import windows_process


@pytest.fixture
def sleeping_child():
    '''A real child process, killed and reaped at the end of the test.'''
    process = subprocess.Popen(  # pylint: disable=consider-using-with
        [sys.executable, '-c', 'import time; time.sleep(30)'],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    yield process
    if process.poll() is None:
        process.kill()
    process.wait()


def test_is_process_running_sees_this_process():
    assert windows_process.is_process_running(os.getpid())


def test_is_process_running_sees_a_child_and_its_exit(sleeping_child):
    assert windows_process.is_process_running(sleeping_child.pid)

    sleeping_child.kill()
    sleeping_child.wait()

    assert not windows_process.is_process_running(sleeping_child.pid)


def test_is_process_running_is_false_for_an_unused_pid():
    # Above the default Windows pid range and not a multiple of 4, so it cannot
    # be a live pid.
    assert not windows_process.is_process_running(999_999)


def test_is_process_running_does_not_trust_exit_code_259():
    '''259 is STILL_ACTIVE, the value GetExitCodeProcess returns for a running
        process, so a process exiting with it used to read as still running.'''
    process = subprocess.Popen(  # pylint: disable=consider-using-with
        [sys.executable, '-c', 'raise SystemExit(259)'],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert process.wait() == 259

    assert not windows_process.is_process_running(process.pid)


def test_get_process_image_path_matches_the_running_executable(sleeping_child):
    image_path = windows_process.get_process_image_path(sleeping_child.pid)

    assert image_path is not None
    assert windows_process.same_image_path(image_path, sys.executable)


def test_get_process_image_path_is_none_for_an_unused_pid():
    assert windows_process.get_process_image_path(999_999) is None


def test_same_image_path_ignores_case_and_separators():
    forward = 'C:/IviumStat/IviumSoft.exe'
    backward = forward.replace('/', os.sep)

    assert windows_process.same_image_path(forward, backward)
    assert windows_process.same_image_path(forward, forward.upper())
    assert not windows_process.same_image_path(
        forward, 'C:/IviumStat/Other.exe')


def test_get_process_creation_time_reads_a_live_process(sleeping_child):
    started_at = windows_process.get_process_creation_time(sleeping_child.pid)

    assert started_at is not None
    assert windows_process.get_process_creation_time(999_999) is None


def test_creation_time_is_stable_across_reads(sleeping_child):
    '''The identity pin is only useful if repeated reads agree.'''
    first = windows_process.get_process_creation_time(sleeping_child.pid)
    second = windows_process.get_process_creation_time(sleeping_child.pid)

    assert first == second


def test_two_processes_have_different_creation_times(sleeping_child):
    '''What lets the manager tell one IviumSoft from another after a pid reuse.'''
    other = subprocess.Popen(  # pylint: disable=consider-using-with
        [sys.executable, '-c', 'import time; time.sleep(30)'],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert (windows_process.get_process_creation_time(sleeping_child.pid)
                != windows_process.get_process_creation_time(other.pid))
    finally:
        other.kill()
        other.wait()
