'''Tests for IviumsoftInstanceManager.

The DLL is replaced by the in-memory fake from test_instance_scoping, and the
OS layer (process spawn, window close, process queries) by a FakeWorld, so the
full lifecycle state machine runs without IviumSoft or hardware.'''
import threading
import warnings
from datetime import datetime

import pytest

from pyvium import Pyvium, instance_manager
from pyvium.core.core_base import CoreBase
from pyvium.errors import DeviceBusyError
from pyvium.instance_manager import (MEASURING_DIALOG_BUTTONS,
                                     IviumsoftInstanceManager)
from pyvium.util import windows_process

MEASURING_DIALOG_CAPTIONS = tuple(MEASURING_DIALOG_BUTTONS.values())


class FakeIviumLib:
    '''Mimics the DLL: per-instance status derived from two sets.'''

    def __init__(self, active_instances=(1,)):
        self.active_instances = set(active_instances)
        self.busy_instances = set()
        self.selected = 1
        self.host_handles = {}

    def IV_selectdevice(self, instance_number_ptr):
        self.selected = instance_number_ptr[0]

    def IV_getdevicestatus(self):
        if self.selected not in self.active_instances:
            return -1
        return 2 if self.selected in self.busy_instances else 1

    def IV_HostHandle(self):
        # 0 means the scan has no handle to check, so nothing is filtered out
        # on the host-window check unless a test says otherwise.
        return self.host_handles.get(self.selected, 0)


class FakeProcess:
    '''Stands in for subprocess.Popen.'''
    _pid_counter = 5000

    def __init__(self, world):
        type(self)._pid_counter += 1
        self.pid = type(self)._pid_counter
        self.returncode = None
        self.instance_number = None
        self._world = world

    def poll(self):
        return self.returncode

    def terminate(self):
        self._world.exit_pid(self.pid, exit_code=-1, deregister=False)

    def kill(self):
        self._world.exit_pid(self.pid, exit_code=-9, deregister=False)


class FakeWorld:
    '''Simulates the OS: spawning, window-close messages, process liveness.'''

    def __init__(self, lib):
        self.lib = lib
        self.alive_pids = set()
        self.launched = []
        self.close_requests = []
        self.terminated_pids = []
        self.creation_times = {}         # pid -> datetime
        self.image_paths = {}            # pid -> exe path, when not the default
        self.default_image_path = 'fake-iviumsoft.exe'
        self.window_titles = {}          # pid -> str
        self.external_instances = {}     # external pid -> instance number
        self.register_on_launch = True   # instance registers instantly
        self.registration_delay = None   # seconds; None = never (if not instant)
        self.exit_code_on_launch = None  # process dies right away with this code
        self.honour_close = True         # WM_CLOSE makes the process exit

        # --- the confirmation a measuring instance answers a close with ---
        self.measuring_pids = set()      # these raise dialogs instead of exiting
        self.dialogs_per_close = 2       # IviumSoft raises one per window closed
        self.dialog_class = 'TfrmIviumWifiDisconnect'
        self.dialog_captions = MEASURING_DIALOG_CAPTIONS
        self.ignore_clicks = False       # BM_CLICK does nothing; Enter still works
        self.dialogs = {}                # dialog hwnd -> (pid, WindowInfo)
        self.control_owner = {}          # control hwnd -> (dialog hwnd, caption)
        self.clicked = []                # (pid, caption) in click order
        self.live_window_handles = set()  # handles is_window() accepts
        self.raise_on_describe = None     # exception to throw mid-close
        self._next_hwnd = 9000

    def launch_process(self, _exe_path):
        process = FakeProcess(self)
        self.launched.append(process)
        self.alive_pids.add(process.pid)
        self.creation_times[process.pid] = datetime.now()
        if self.exit_code_on_launch is not None:
            self.exit_pid(process.pid, self.exit_code_on_launch)
        elif self.register_on_launch:
            self.register_process(process)
        elif self.registration_delay is not None:
            threading.Timer(self.registration_delay,
                            self.register_process, [process]).start()
        return process

    def register_process(self, process):
        process.instance_number = max(self.lib.active_instances, default=0) + 1
        self.lib.active_instances.add(process.instance_number)

    def spawn_external(self, pid, instance_number=None, title=None,
                       started_at=None, image_path=None):
        '''An IviumSoft process this manager never launched (an orphan).

            image_path stands in for a pid Windows recycled for some other
            program: anything but the manager's exe must never be touched.'''
        self.alive_pids.add(pid)
        self.creation_times[pid] = started_at or datetime.now()
        if image_path is not None:
            self.image_paths[pid] = image_path
        if title is not None:
            self.window_titles[pid] = title
        if instance_number is not None:
            self.lib.active_instances.add(instance_number)
            self.external_instances[pid] = instance_number

    def exit_pid(self, pid, exit_code, deregister=True):
        '''Ends a process. deregister=False models a hard terminate: the
            process never gets to tell the driver it is going, so its instance
            number stays active with nothing behind it, which is the leak the
            dialog handling exists to avoid.'''
        self.alive_pids.discard(pid)
        for process in self.launched:
            if process.pid == pid:
                process.returncode = exit_code
                if deregister and process.instance_number is not None:
                    self.lib.active_instances.discard(process.instance_number)
        external_instance = self.external_instances.pop(pid, None)
        if deregister and external_instance is not None:
            self.lib.active_instances.discard(external_instance)

    # --- the measuring confirmation dialog ---

    def _raise_dialog(self, pid):
        '''Creates one confirmation dialog owned by pid, as IviumSoft does
            when asked to close while its device is measuring.'''
        self._next_hwnd += 1
        dialog_hwnd = self._next_hwnd
        controls = []
        for caption in self.dialog_captions:
            self._next_hwnd += 1
            controls.append(windows_process.WindowControl(
                hwnd=self._next_hwnd,
                class_name='TButton',
                text=caption,
                is_default_button=caption == 'Disconnect and Continue',
            ))
            self.control_owner[self._next_hwnd] = (dialog_hwnd, caption)
        self.dialogs[dialog_hwnd] = (pid, windows_process.WindowInfo(
            hwnd=dialog_hwnd,
            class_name=self.dialog_class,
            title='Confirm',
            controls=tuple(controls),
        ))

    def _answer(self, dialog_hwnd, caption):
        pid, _info = self.dialogs.pop(dialog_hwnd)
        self.clicked.append((pid, caption))
        if caption == 'Cancel':
            # The close was refused: no further dialogs, the process lives on.
            self.measuring_pids.discard(pid)
            return
        if not any(owner == pid for owner, _ in self.dialogs.values()):
            self.exit_pid(pid, exit_code=0)

    # --- windows_process replacements ---

    def close_main_windows(self, pid):
        self.close_requests.append(pid)
        if pid in self.measuring_pids:
            for _ in range(self.dialogs_per_close):
                self._raise_dialog(pid)
            return self.dialogs_per_close
        if self.honour_close:
            self.exit_pid(pid, exit_code=0)
            return 1
        return 0

    def list_visible_windows(self, pid):
        return [hwnd for hwnd, (owner, _) in self.dialogs.items()
                if owner == pid]

    def describe_window(self, hwnd):
        if self.raise_on_describe is not None:
            raise self.raise_on_describe
        return self.dialogs[hwnd][1]

    def click_button(self, hwnd):
        dialog_hwnd, caption = self.control_owner[hwnd]
        if self.ignore_clicks:
            self.clicked.append((self.dialogs[dialog_hwnd][0],
                                 f'ignored:{caption}'))
            return
        self._answer(dialog_hwnd, caption)

    def press_enter(self, hwnd):
        _pid, info = self.dialogs[hwnd]
        for control in info.controls:
            if control.is_default_button:
                self._answer(hwnd, control.text)
                return

    def is_window(self, hwnd):
        return hwnd in self.live_window_handles

    def is_process_running(self, pid):
        return pid in self.alive_pids

    def terminate_process(self, pid):
        self.terminated_pids.append(pid)
        self.exit_pid(pid, exit_code=1, deregister=False)
        return True

    def find_pids_by_exe(self, _exe_path):
        return sorted(self.alive_pids)

    def get_process_creation_time(self, pid):
        return self.creation_times.get(pid)

    def get_main_window_title(self, pid):
        return self.window_titles.get(pid)

    def get_process_image_path(self, pid):
        if pid in self.image_paths:
            return self.image_paths[pid]
        return self.default_image_path if pid in self.alive_pids else None


@pytest.fixture
def world(monkeypatch):
    lib = FakeIviumLib(active_instances=(1,))
    fake_world = FakeWorld(lib)

    monkeypatch.setattr(CoreBase, 'get_lib', staticmethod(lambda: lib))
    CoreBase.set_driver_open(True)
    CoreBase.set_selected_instance(1)
    CoreBase.invalidate_active_instances_cache()

    monkeypatch.setattr(instance_manager, '_launch_process',
                        fake_world.launch_process)
    monkeypatch.setattr(windows_process, 'close_main_windows',
                        fake_world.close_main_windows)
    monkeypatch.setattr(windows_process, 'is_process_running',
                        fake_world.is_process_running)
    monkeypatch.setattr(windows_process, 'terminate_process',
                        fake_world.terminate_process)
    monkeypatch.setattr(windows_process, 'find_pids_by_exe',
                        fake_world.find_pids_by_exe)
    monkeypatch.setattr(windows_process, 'get_process_creation_time',
                        fake_world.get_process_creation_time)
    monkeypatch.setattr(windows_process, 'get_main_window_title',
                        fake_world.get_main_window_title)
    monkeypatch.setattr(windows_process, 'get_process_image_path',
                        fake_world.get_process_image_path)
    monkeypatch.setattr(windows_process, 'list_visible_windows',
                        fake_world.list_visible_windows)
    monkeypatch.setattr(windows_process, 'describe_window',
                        fake_world.describe_window)
    monkeypatch.setattr(windows_process, 'click_button',
                        fake_world.click_button)
    monkeypatch.setattr(windows_process, 'press_enter',
                        fake_world.press_enter)
    monkeypatch.setattr(windows_process, 'is_window', fake_world.is_window)

    yield fake_world

    CoreBase.set_driver_open(False)
    CoreBase.set_selected_instance(1)


def make_manager(**overrides):
    settings = {'exe_path': 'fake-iviumsoft.exe', 'launch_timeout': 2.0,
                'close_timeout': 0.05, 'poll_interval': 0.01}
    settings.update(overrides)
    return IviumsoftInstanceManager(**settings)


def test_launch_attributes_new_instance_number(world):
    manager = make_manager()

    record = manager.launch()

    assert record.instance_number == 2  # instance 1 already existed
    assert record.pid == world.launched[0].pid
    assert record.managed is True
    assert record.launched_at is not None


def test_launch_cold_start_with_no_running_instances(world):
    world.lib.active_instances.clear()  # nothing running yet
    manager = make_manager()

    record = manager.launch()

    assert record.instance_number == 1
    assert record.managed is True


def test_launch_waits_for_delayed_registration(world):
    world.register_on_launch = False
    world.registration_delay = 0.1
    manager = make_manager()

    record = manager.launch()

    assert record.instance_number == 2


def test_launch_times_out_and_terminates_the_process(world):
    world.register_on_launch = False  # never registers
    manager = make_manager(launch_timeout=0.05)

    with pytest.raises(TimeoutError):
        manager.launch()

    process = world.launched[0]
    assert process.returncode is not None, 'orphan GUI process left behind'


def test_launch_detects_startup_crash(world):
    world.exit_code_on_launch = 3
    manager = make_manager()

    with pytest.raises(RuntimeError, match='exited with code 3'):
        manager.launch()


def test_close_sends_window_close_and_forgets_the_instance(world):
    manager = make_manager()
    record = manager.launch()

    manager.close(record.instance_number)

    assert world.close_requests == [record.pid]
    assert record.instance_number not in world.lib.active_instances
    assert world.terminated_pids == []  # no escalation needed
    with pytest.raises(ValueError):
        manager.close(record.instance_number)  # record is gone


def test_close_closes_a_measuring_instance_and_only_cancel_refuses(world):
    '''force no longer gates this: on_measuring does, through the dialog.'''
    manager = make_manager()
    record = manager.launch()
    world.lib.busy_instances.add(record.instance_number)
    world.measuring_pids.add(record.pid)

    with pytest.raises(DeviceBusyError, match="on_measuring is 'cancel'"):
        manager.close(record.instance_number, on_measuring='cancel')
    assert world.close_requests == []  # refused before anything was messaged

    manager.close(record.instance_number)  # the default closes it
    assert world.close_requests == [record.pid]
    assert world.clicked == [(record.pid, 'Disconnect and Continue')] * 2
    assert world.terminated_pids == []


def test_close_escalates_to_terminate_only_with_force(world):
    world.honour_close = False  # e.g. a confirmation dialog blocks WM_CLOSE
    manager = make_manager()
    record = manager.launch()

    with pytest.raises(TimeoutError, match='did not close'):
        manager.close(record.instance_number)

    assert world.launched[0].returncode is None  # still running
    assert world.terminated_pids == []

    # The record survived, so the close can be escalated rather than repeated
    # from scratch. Without it this second call would raise ValueError.
    with pytest.warns(UserWarning, match='terminating'):
        manager.close(record.instance_number, force=True)

    assert world.launched[0].returncode == -9  # killed via the Popen handle


def test_close_requires_a_known_pid(world):
    manager = make_manager()

    with pytest.raises(ValueError, match='adopt'):
        manager.close(1)  # active, but never launched or adopted here


def test_adopt_then_close(world):
    world.spawn_external(7777, instance_number=5)
    manager = make_manager()

    record = manager.adopt(5, 7777)
    assert record.managed is False
    assert record.pid == 7777

    manager.close(5)
    assert world.close_requests == [7777]


def test_adopt_validates_instance_and_pid(world):
    manager = make_manager()

    with pytest.raises(ValueError, match='not active'):
        manager.adopt(9, 7777)

    with pytest.raises(ValueError, match='not running'):
        manager.adopt(1, 4242)  # instance exists, pid does not


def test_close_refuses_a_pid_recycled_by_another_program(world):
    """A pid Windows handed to another program must never be closed or killed."""
    world.lib.active_instances.add(5)
    world.spawn_external(7777, started_at=datetime(2026, 1, 1, 10, 0))
    manager = make_manager()
    manager.adopt(5, 7777)

    # The IviumSoft process dies and Windows recycles its pid for an editor.
    world.exit_pid(7777, exit_code=0)
    world.lib.active_instances.add(5)
    world.spawn_external(7777, started_at=datetime(2026, 1, 1, 11, 0),
                         image_path='C:/Windows/notepad.exe')

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        manager.close(5)

    assert world.close_requests == []
    assert world.terminated_pids == []
    assert 7777 in world.alive_pids  # the editor is untouched
    assert any('no longer' in str(warning.message) for warning in caught)
    assert 5 not in {item.instance_number for item in manager.list_instances()
                     if item.pid is not None}


def test_close_refuses_a_pid_recycled_by_another_iviumsoft(world):
    """The case an exe-path check alone cannot catch: same program, same pid.

        The manager launches and closes IviumSoft repeatedly, so a recycled pid
        is far more likely to be another IviumSoft than an unrelated program."""
    world.lib.active_instances.add(5)
    world.spawn_external(7777, started_at=datetime(2026, 1, 1, 10, 0))
    manager = make_manager()
    manager.adopt(5, 7777)

    world.exit_pid(7777, exit_code=0)
    world.lib.active_instances.add(5)
    world.spawn_external(7777, started_at=datetime(2026, 1, 1, 11, 0))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        manager.close(5)

    assert world.close_requests == []
    assert world.terminated_pids == []
    assert 7777 in world.alive_pids
    assert any('no longer' in str(warning.message) for warning in caught)


def test_close_terminates_when_the_pid_is_still_ours(world):
    """The guard must not refuse the ordinary escalation path."""
    world.lib.active_instances.add(5)
    world.spawn_external(7777, started_at=datetime(2026, 1, 1, 10, 0))
    world.honour_close = False
    manager = make_manager()
    manager.adopt(5, 7777)

    with pytest.warns(UserWarning, match='did not close'):
        manager.close(5, force=True)

    assert world.close_requests == [7777]
    assert world.terminated_pids == [7777]


def test_close_orphans_skips_a_recycled_pid(world):
    world.spawn_external(8001, instance_number=6)
    world.spawn_external(8002, instance_number=7,
                         image_path='C:/Windows/notepad.exe')
    manager = make_manager()

    manager.close_orphans()

    assert world.close_requests == [8001]
    assert 8002 in world.alive_pids


def test_adopt_rejects_a_pid_that_is_not_iviumsoft(world):
    world.lib.active_instances.add(5)
    world.spawn_external(7777, image_path='C:/Windows/notepad.exe')
    manager = make_manager()

    with pytest.raises(ValueError, match='not .*IviumSoft|image path'):
        manager.adopt(5, 7777)


def test_adopt_accepts_a_manually_launched_instance(world):
    """The ordinary orphan-recovery flow: discover, pair by hand, adopt, close."""
    world.spawn_external(7777, instance_number=5, title='IviumSoft - manual')
    manager = make_manager()

    report = manager.discover()
    assert 5 in report.orphan_instance_numbers  # instance 1 is an orphan too
    assert 7777 in [process.pid for process in report.untracked_processes]

    record = manager.adopt(5, 7777)
    assert record.managed is False
    assert record.started_at == world.creation_times[7777]

    manager.close(5)
    assert world.close_requests == [7777]


def test_list_instances_prunes_a_record_whose_process_was_replaced(world):
    world.lib.active_instances.add(5)
    world.spawn_external(7777, started_at=datetime(2026, 1, 1, 10, 0))
    manager = make_manager()
    manager.adopt(5, 7777)

    world.exit_pid(7777, exit_code=0)
    world.lib.active_instances.add(5)
    world.spawn_external(7777, started_at=datetime(2026, 1, 1, 11, 0))

    listed = {item.instance_number: item for item in manager.list_instances()}

    # Instance 5 is still active, but our record no longer points at its process.
    assert listed[5].pid is None


def _deregister(world, instance_number):
    """IviumSoft leaves the driver but its process lives on.

        Distinct from world.exit_pid, which does both: this is the window where
        the driver answers -1 while the process is still winding down, crashed
        without exiting, or hung."""
    world.lib.active_instances.discard(instance_number)


def test_close_closes_a_deregistered_instance_whose_process_lives(world):
    """The busy check cannot run, but the process still needs cleaning up."""
    manager = make_manager()
    record = manager.launch()
    _deregister(world, record.instance_number)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        manager.close(record.instance_number)

    assert world.close_requests == [record.pid]
    assert record.pid not in world.alive_pids
    assert any('deregistered' in str(warning.message) for warning in caught)


def test_close_terminates_a_hung_deregistered_instance(world):
    """The case the fix exists for: deregistered, alive, and ignoring WM_CLOSE."""
    world.honour_close = False
    manager = make_manager()
    record = manager.launch()
    _deregister(world, record.instance_number)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        manager.close(record.instance_number, force=True)

    assert world.close_requests == [record.pid]
    assert world.launched[0].returncode == -9  # killed via the Popen handle
    assert any('did not close' in str(warning.message) for warning in caught)


def test_list_instances_keeps_a_deregistered_record_whose_process_lives(world):
    """Pruning on the registration rather than the process stranded the pid."""
    manager = make_manager()
    record = manager.launch()
    _deregister(world, record.instance_number)

    listed = manager.list_instances()
    assert record.instance_number not in [item.instance_number for item in listed]

    # The record survives, so the leftover process is still closable.
    with warnings.catch_warnings(record=True):
        warnings.simplefilter('always')
        manager.close(record.instance_number)

    assert world.close_requests == [record.pid]


def test_discover_reports_a_deregistered_process_as_untracked(world):
    manager = make_manager()
    record = manager.launch()
    _deregister(world, record.instance_number)

    report = manager.discover()

    # Reported on both sides on purpose: the manager still holds the record,
    # and the OS shows a process no active instance claims. That mismatch is
    # the signal, and it makes the process sweepable by close_orphans().
    assert record.instance_number in [item.instance_number for item in report.tracked]
    assert record.pid in [process.pid for process in report.untracked_processes]


def test_list_instances_merges_managed_and_orphans(world):
    manager = make_manager()
    record = manager.launch()        # instance 2, managed
    world.lib.active_instances.add(4)  # orphan, unknown pid

    listed = {item.instance_number: item for item in manager.list_instances()}

    assert sorted(listed) == [1, 2, 4]
    assert listed[1].pid is None and listed[1].managed is False
    assert listed[2].pid == record.pid and listed[2].managed is True
    assert listed[4].pid is None and listed[4].managed is False


def test_list_instances_prunes_dead_records(world):
    manager = make_manager()
    record = manager.launch()

    world.exit_pid(record.pid, exit_code=0)  # crashed / closed externally

    numbers = [item.instance_number for item in manager.list_instances()]
    assert numbers == [1]


def test_discover_groups_tracked_orphans_and_untracked(world):
    manager = make_manager()
    record = manager.launch()  # instance 2, tracked
    world.spawn_external(9001, instance_number=4, title='IviumSoft')

    report = manager.discover()

    assert [item.instance_number for item in report.tracked] == [2]
    assert report.tracked[0].pid == record.pid
    assert report.orphan_instance_numbers == [1, 4]
    assert [process.pid for process in report.untracked_processes] == [9001]
    untracked = report.untracked_processes[0]
    assert untracked.window_title == 'IviumSoft'
    assert untracked.started_at is not None


def test_discover_sorts_untracked_by_start_time(world):
    manager = make_manager()
    world.spawn_external(9002, started_at=datetime(2026, 1, 1, 10, 5))
    world.spawn_external(9001, started_at=datetime(2026, 1, 1, 10, 0))

    report = manager.discover()

    assert [process.pid for process in report.untracked_processes] == [9001, 9002]


def test_discover_is_read_only(world):
    manager = make_manager()
    record = manager.launch()
    world.exit_pid(record.pid, exit_code=0)  # died externally

    report = manager.discover()

    assert [item.instance_number for item in report.tracked] == [2]
    # list_instances, by contrast, prunes the dead record
    assert record.instance_number not in [
        item.instance_number for item in manager.list_instances()]


def test_close_orphans_closes_only_untracked(world):
    manager = make_manager()
    record = manager.launch()
    world.spawn_external(9001, instance_number=4)

    closed = manager.close_orphans()

    assert closed == [9001]
    assert world.close_requests == [9001]
    assert record.pid in world.alive_pids  # managed instance untouched
    assert 4 not in world.lib.active_instances


def test_close_orphans_refuses_a_busy_orphan_only_with_cancel(world):
    '''Orphan pids cannot be paired with instance numbers, so a 'cancel' sweep
        is all-or-nothing.'''
    manager = make_manager()
    world.spawn_external(9001, instance_number=4)
    world.lib.busy_instances.add(4)

    with pytest.raises(DeviceBusyError):
        manager.close_orphans(on_measuring='cancel')
    assert world.close_requests == []  # nothing closed

    closed = manager.close_orphans()
    assert closed == [9001]


def test_close_orphans_escalates_only_with_force(world):
    world.honour_close = False
    manager = make_manager()
    world.spawn_external(9001, instance_number=4)

    with pytest.warns(UserWarning, match='not reported as closed'):
        closed = manager.close_orphans()

    assert closed == []  # it never closed, so it is not reported as closed
    assert world.terminated_pids == []
    assert world.is_process_running(9001)

    with pytest.warns(UserWarning, match='terminating'):
        closed = manager.close_orphans(force=True)

    assert closed == [9001]
    assert world.terminated_pids == [9001]


def test_close_orphans_with_nothing_untracked(world):
    manager = make_manager()
    manager.launch()

    # instance 1 is an orphan number, but no untracked process is visible
    assert manager.close_orphans() == []


def test_launch_and_close_invalidate_the_active_instance_cache(world):
    manager = make_manager()

    Pyvium.get_active_iviumsoft_instances()  # populate the cache
    assert CoreBase.get_active_instances_cache() is not None

    record = manager.launch()
    assert CoreBase.get_active_instances_cache() is None  # launch invalidated it

    Pyvium.get_active_iviumsoft_instances()  # repopulate
    manager.close(record.instance_number)
    assert CoreBase.get_active_instances_cache() is None  # close invalidated it


# --- the measuring confirmation dialog -------------------------------------
#
# A measuring instance answers a close with a modal confirmation instead of
# closing. Left unanswered it holds the process open until the close times out
# and terminates it, and a terminated IviumSoft cannot deregister, which is how
# the instance number leaks. IviumSoft raises one dialog per window messaged,
# so a close gets two of them back.


def measuring_instance(world, pid=7777, instance_number=5):
    '''An adopted instance whose device is measuring.'''
    world.spawn_external(pid, instance_number=instance_number)
    world.lib.busy_instances.add(instance_number)
    world.measuring_pids.add(pid)
    manager = make_manager()
    manager.adopt(instance_number, pid)
    return manager


def test_close_answers_the_measuring_dialog_instead_of_terminating(world):
    manager = measuring_instance(world)

    with warnings.catch_warnings():
        warnings.simplefilter('error')  # no timeout and no leak warning
        manager.close(5, force=True)

    assert world.clicked == [(7777, 'Disconnect and Continue')] * 2
    assert world.terminated_pids == []
    assert 5 not in world.lib.active_instances


def test_close_with_abort_clicks_the_abort_button(world):
    manager = measuring_instance(world)

    manager.close(5, force=True, on_measuring='abort')

    assert world.clicked == [(7777, 'Disconnect and Abort')] * 2
    assert world.terminated_pids == []


def test_close_with_cancel_refuses_before_messaging_anything(world):
    '''The cheap path: one status read, no WM_CLOSE and no dialog raised.'''
    manager = measuring_instance(world)

    with pytest.raises(DeviceBusyError, match="on_measuring is 'cancel'"):
        manager.close(5, on_measuring='cancel')

    assert world.close_requests == []
    assert world.clicked == []
    assert world.terminated_pids == []
    assert world.is_process_running(7777)
    assert 5 in world.lib.active_instances


def test_close_with_cancel_backs_out_at_the_dialog_in_the_race(world):
    '''The instance reads idle at the pre-check and raises the dialog anyway,
        which is what a device going busy in between looks like. No status read
        can prevent that, so the Cancel click is the backstop.'''
    world.spawn_external(7777, instance_number=5)
    world.measuring_pids.add(7777)   # the dialog appears...
    # ...but busy_instances stays empty, so the pre-check sees an idle device.
    manager = make_manager()
    manager.adopt(5, 7777)

    with pytest.raises(DeviceBusyError, match='cancelled at its confirmation'):
        manager.close(5, on_measuring='cancel')

    # Both dialogs are answered: leaving one open would strand IviumSoft on a
    # modal nobody is going to close.
    assert world.clicked == [(7777, 'Cancel')] * 2
    assert world.terminated_pids == []
    assert world.is_process_running(7777)
    assert 5 in world.lib.active_instances


def test_close_with_cancel_never_terminates_even_with_force(world):
    '''A deliberate refusal must not be escalated into a kill.'''
    world.spawn_external(7777, instance_number=5)
    world.measuring_pids.add(7777)
    manager = make_manager()
    manager.adopt(5, 7777)

    with pytest.raises(DeviceBusyError):
        manager.close(5, force=True, on_measuring='cancel')

    assert world.terminated_pids == []
    assert world.is_process_running(7777)


def test_close_falls_back_to_enter_when_the_click_is_ignored(world):
    manager = measuring_instance(world)
    world.ignore_clicks = True

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        manager.close(5, force=True, on_measuring='continue')

    assert world.clicked == ([(7777, 'ignored:Disconnect and Continue')] * 2
                             + [(7777, 'Disconnect and Continue')] * 2)
    assert world.terminated_pids == []


def test_close_without_dialog_handling_terminates_and_leaks(world):
    '''The behaviour before this fix, still reachable with on_measuring=None.'''
    manager = measuring_instance(world)

    with pytest.warns(UserWarning) as caught:
        manager.close(5, force=True, on_measuring=None)

    messages = [str(warning.message) for warning in caught]
    assert any('did not close' in message for message in messages)
    assert any('still registered with the driver' in message
               for message in messages)
    assert world.clicked == []
    assert world.terminated_pids == [7777]
    assert 5 in world.lib.active_instances  # the ghost


def test_close_warns_about_an_unrecognised_dialog_and_leaves_it_alone(world):
    manager = measuring_instance(world)
    world.dialog_class = 'TfrmSomethingElse'
    world.dialog_captions = ('Yes', 'No')

    with pytest.warns(UserWarning, match='does not recognise'):
        manager.close(5, force=True)

    assert world.clicked == []          # never guess at an unknown default
    assert world.terminated_pids == [7777]


def test_close_rejects_an_unknown_on_measuring(world):
    manager = measuring_instance(world)

    with pytest.raises(ValueError, match='on_measuring must be None'):
        manager.close(5, force=True, on_measuring='disconnect')

    assert world.close_requests == []   # rejected before anything was messaged


def test_close_orphans_answers_the_dialog(world):
    world.spawn_external(8001, instance_number=6)
    world.lib.busy_instances.add(6)
    world.measuring_pids.add(8001)
    manager = make_manager()

    closed = manager.close_orphans(force=True)

    assert closed == [8001]
    assert world.clicked == [(8001, 'Disconnect and Continue')] * 2
    assert world.terminated_pids == []
    assert 6 not in world.lib.active_instances


def test_close_orphans_with_cancel_skips_a_pid_without_raising(world):
    '''A busy orphan is caught by the all-or-nothing pre-check, but one that
        only raises the dialog is skipped, and the sweep carries on.'''
    world.spawn_external(8001, instance_number=6)
    world.measuring_pids.add(8001)   # dialog appears; the pre-check sees idle
    world.spawn_external(8002, instance_number=7)
    manager = make_manager()

    closed = manager.close_orphans(on_measuring='cancel')

    assert closed == [8002]          # the other orphan still closed
    assert world.is_process_running(8001)
    assert world.terminated_pids == []


def test_close_drops_the_ghost_from_the_reported_instances(world):
    '''A terminate leaks the number, but a slot whose host window is gone is
        no longer reported to callers.'''
    manager = measuring_instance(world)
    world.lib.host_handles[5] = 4242    # the window it registered
    world.live_window_handles.add(4242)

    with pytest.warns(UserWarning):
        manager.close(5, force=True, on_measuring=None)

    assert 5 in world.lib.active_instances       # the DLL still says so
    world.live_window_handles.discard(4242)      # the window died with it

    # Instance 1 is the fixture's healthy instance: it reports no handle, so it
    # is kept. Only the slot with positive proof of a dead window is dropped.
    assert Pyvium.get_active_iviumsoft_instances() == [1]
    assert Pyvium.get_active_iviumsoft_instances(
        verify_host_window=False) == [1, 5]      # raw driver view


# --- force gates the kill, and nothing else --------------------------------
#
# Closing a measuring instance is graceful and reversible now that the dialog
# is answered, so it needs no flag. TerminateProcess is the irreversible one:
# it leaks the instance number, so it is what force has to guard.


def test_close_timeout_leaves_the_process_and_the_record_alone(world):
    world.honour_close = False
    manager = make_manager()
    record = manager.launch()

    with pytest.raises(TimeoutError, match='did not close'):
        manager.close(record.instance_number)

    assert world.terminated_pids == []
    assert world.is_process_running(record.pid)
    assert record.instance_number in world.lib.active_instances
    # The record is intact, which is what makes terminate() the documented
    # recovery rather than a second close from scratch.
    manager.terminate(record.instance_number)
    assert world.launched[0].returncode == -9


def test_close_with_abort_needs_no_force(world):
    manager = measuring_instance(world)

    manager.close(5, on_measuring='abort')

    assert world.clicked == [(7777, 'Disconnect and Abort')] * 2
    assert world.terminated_pids == []
    assert 5 not in world.lib.active_instances


def test_close_terminates_after_an_unexpected_failure_only_with_force(world):
    '''force covers a close that fails unexpectedly, and the original error
        still reaches the caller.'''
    manager = measuring_instance(world)
    world.raise_on_describe = RuntimeError('window vanished mid-read')

    with pytest.raises(RuntimeError, match='vanished'):
        manager.close(5)
    assert world.terminated_pids == []
    assert world.is_process_running(7777)

    with pytest.warns(UserWarning, match='failed to close cleanly'):
        with pytest.raises(RuntimeError, match='vanished'):
            manager.close(5, force=True)
    assert world.terminated_pids == [7777]


def test_close_does_not_terminate_on_a_keyboard_interrupt(world):
    '''force escalates on errors, but a Ctrl-C must not kill an instrument and
        leak its slot.'''
    manager = measuring_instance(world)
    world.raise_on_describe = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        manager.close(5, force=True)

    assert world.terminated_pids == []
    assert world.is_process_running(7777)


def test_terminate_kills_warns_about_the_leak_and_drops_the_record(world):
    world.spawn_external(7777, instance_number=5)
    manager = make_manager()
    manager.adopt(5, 7777)

    with pytest.warns(UserWarning, match='still registered with the driver'):
        manager.terminate(5)

    assert world.terminated_pids == [7777]
    assert not world.is_process_running(7777)
    assert 5 in world.lib.active_instances  # leaked: it never deregistered
    with pytest.raises(ValueError):
        manager.terminate(5)                # the record is gone


def test_terminate_requires_a_known_pid(world):
    manager = make_manager()

    with pytest.raises(ValueError, match='no known pid'):
        manager.terminate(1)


def test_terminate_refuses_a_pid_recycled_by_another_program(world):
    world.spawn_external(7777, instance_number=5,
                         started_at=datetime(2026, 1, 1, 10, 0))
    manager = make_manager()
    manager.adopt(5, 7777)
    world.image_paths[7777] = 'C:/Windows/notepad.exe'

    with pytest.warns(UserWarning, match='pid was reused'):
        manager.terminate(5)

    assert world.terminated_pids == []
