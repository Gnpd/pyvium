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
from pyvium.instance_manager import IviumsoftInstanceManager
from pyvium.util import windows_process


class FakeIviumLib:
    '''Mimics the DLL: per-instance status derived from two sets.'''

    def __init__(self, active_instances=(1,)):
        self.active_instances = set(active_instances)
        self.busy_instances = set()
        self.selected = 1

    def IV_selectdevice(self, instance_number_ptr):
        self.selected = instance_number_ptr[0]

    def IV_getdevicestatus(self):
        if self.selected not in self.active_instances:
            return -1
        return 2 if self.selected in self.busy_instances else 1


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
        self._world.exit_pid(self.pid, exit_code=-1)

    def kill(self):
        self._world.exit_pid(self.pid, exit_code=-9)


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

    def exit_pid(self, pid, exit_code):
        self.alive_pids.discard(pid)
        for process in self.launched:
            if process.pid == pid:
                process.returncode = exit_code
                if process.instance_number is not None:
                    self.lib.active_instances.discard(process.instance_number)
        external_instance = self.external_instances.pop(pid, None)
        if external_instance is not None:
            self.lib.active_instances.discard(external_instance)

    # --- windows_process replacements ---

    def close_main_windows(self, pid):
        self.close_requests.append(pid)
        if self.honour_close:
            self.exit_pid(pid, exit_code=0)
            return 1
        return 0

    def is_process_running(self, pid):
        return pid in self.alive_pids

    def terminate_process(self, pid):
        self.terminated_pids.append(pid)
        self.exit_pid(pid, exit_code=1)
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


def test_close_refuses_while_measuring_unless_forced(world):
    manager = make_manager()
    record = manager.launch()
    world.lib.busy_instances.add(record.instance_number)

    with pytest.raises(DeviceBusyError):
        manager.close(record.instance_number)
    assert world.close_requests == []

    manager.close(record.instance_number, force=True)
    assert world.close_requests == [record.pid]


def test_close_escalates_to_terminate_when_window_close_is_ignored(world):
    world.honour_close = False  # e.g. a confirmation dialog blocks WM_CLOSE
    manager = make_manager()
    record = manager.launch()

    with pytest.warns(UserWarning, match='terminating'):
        manager.close(record.instance_number)

    assert world.launched[0].returncode == -9  # killed via the Popen handle


def test_close_requires_a_known_pid(world):
    manager = make_manager()

    with pytest.raises(ValueError, match='adopt'):
        manager.close(1)  # active, but never launched or adopted here


def test_adopt_then_close(world):
    world.lib.active_instances.add(5)
    world.alive_pids.add(7777)
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
        manager.close(5)

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
        manager.close(record.instance_number)

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


def test_close_orphans_refuses_when_any_orphan_is_busy(world):
    manager = make_manager()
    world.spawn_external(9001, instance_number=4)
    world.lib.busy_instances.add(4)

    with pytest.raises(DeviceBusyError):
        manager.close_orphans()
    assert world.close_requests == []  # all-or-nothing: nothing closed

    closed = manager.close_orphans(force=True)
    assert closed == [9001]


def test_close_orphans_escalates_when_close_is_ignored(world):
    world.honour_close = False
    manager = make_manager()
    world.spawn_external(9001, instance_number=4)

    with pytest.warns(UserWarning, match='terminating'):
        closed = manager.close_orphans()

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
