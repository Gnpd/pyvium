'''Lifecycle management for IviumSoft application instances.

Opens, tracks, adopts and gracefully closes IviumSoft processes, mapping
each one to the driver instance number it registered with. The driver must
already be open for any operation that talks to it; on a cold start with
no IviumSoft running yet, use Pyvium.open_driver(verify_iviumsoft=False).
'''
import subprocess
import threading
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime

from .core import Core
from .errors import DeviceBusyError
from .pyvium import Pyvium
from .util import windows_process

DEFAULT_IVIUMSOFT_EXE = r"C:\IviumStat\IviumSoft.exe"
DEVICE_STATUS_BUSY = 2


def _launch_process(exe_path: str) -> subprocess.Popen:
    '''Starts IviumSoft detached from our stdio.
        Module-level so tests can replace it with a fake.'''
    return subprocess.Popen(  # pylint: disable=consider-using-with
        [exe_path],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


@dataclass
class ManagedInstance:
    '''One IviumSoft process as seen by the manager.

        managed is True only for instances launched by this manager (a Popen
        handle is held). Adopted instances have a known pid but no handle;
        discovered orphans have neither (pid is None) and can only be
        observed, not closed.'''
    instance_number: int
    pid: int | None
    launched_at: datetime | None
    managed: bool
    process: subprocess.Popen | None = field(default=None, repr=False)
    # OS process start time, read at launch/adopt. Windows reuses pids, so this
    # is what tells our process apart from a later one wearing the same pid;
    # launched_at is this manager's own clock and is set only for launches.
    started_at: datetime | None = None


@dataclass
class UntrackedProcess:
    '''An IviumSoft process found on the machine that no manager record
        covers. started_at and window_title are best-effort aids for pairing
        it with an orphan driver instance number by hand: launch order
        matches the driver's sequential numbering.'''
    pid: int
    started_at: datetime | None
    window_title: str | None


@dataclass
class DiscoveryReport:
    '''Snapshot pairing the driver's view of IviumSoft with the OS's view.

        tracked instances connect both views (instance number and pid);
        orphan_instance_numbers (driver side) and untracked_processes (OS
        side) are the two halves the manager cannot pair automatically. In
        a healthy state their counts match; a mismatch usually means a
        process still starting up or one that died without deregistering.'''
    tracked: list[ManagedInstance]
    orphan_instance_numbers: list[int]
    untracked_processes: list[UntrackedProcess]


class IviumsoftInstanceManager:
    '''Opens and closes IviumSoft instances and maps them to driver
        instance numbers.

        launch() attributes the new driver instance number to the spawned
        process by diffing the active-instance list before and after, so
        launches are serialized: one manager lock covers launch and close.

        The driver instance numbering after an instance closes is stable for
        the remaining instances: closing one leaves a gap rather than
        renumbering the survivors (verified against real IviumSoft hardware).'''

    def __init__(self, exe_path: str = DEFAULT_IVIUMSOFT_EXE,
                 launch_timeout: float = 30.0,
                 close_timeout: float = 10.0,
                 poll_interval: float = 0.5):
        self._exe_path = exe_path
        self._launch_timeout = launch_timeout
        self._close_timeout = close_timeout
        self._poll_interval = poll_interval
        self._records: dict[int, ManagedInstance] = {}
        self._lock = threading.RLock()

    def launch(self) -> ManagedInstance:
        '''Starts one IviumSoft process and waits until it registers with
            the driver. Returns its ManagedInstance record.

            Raises RuntimeError if the process exits during startup, or
            TimeoutError (after terminating the process) if it never
            registers within launch_timeout.'''
        with self._lock:
            instances_before = set(Pyvium.get_active_iviumsoft_instances())
            process = _launch_process(self._exe_path)
            deadline = time.monotonic() + self._launch_timeout

            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"IviumSoft (pid {process.pid}) exited with code "
                        f"{process.returncode} during startup")

                new_instances = set(
                    Pyvium.get_active_iviumsoft_instances()) - instances_before
                if new_instances:
                    instance_number = min(new_instances)
                    record = ManagedInstance(
                        instance_number=instance_number,
                        pid=process.pid,
                        launched_at=datetime.now(),
                        managed=True,
                        process=process,
                        started_at=windows_process.get_process_creation_time(
                            process.pid),
                    )
                    self._records[instance_number] = record
                    Core.invalidate_active_instances_cache()
                    return record

                time.sleep(self._poll_interval)

            process.terminate()
            raise TimeoutError(
                f"IviumSoft (pid {process.pid}) did not register with the "
                f"driver within {self._launch_timeout}s")

    def close(self, instance_number: int, force: bool = False) -> None:
        '''Gracefully closes an instance (window-close message), escalating
            to a hard terminate if the process does not exit in time.

            Refuses to close a measuring instance unless force=True.
            Raises ValueError for instances without a known pid; adopt()
            them first.'''
        with self._lock:
            record = self._records.get(instance_number)
            if record is None or record.pid is None:
                raise ValueError(
                    f"Instance {instance_number} has no known pid in this "
                    "manager. Launch it here or adopt(instance_number, pid) "
                    "before closing.")

            if not self._is_our_process(record.pid, record.started_at):
                warnings.warn(
                    f"Instance {instance_number} (pid {record.pid}) is no longer "
                    "the process this manager recorded: it exited and the pid "
                    "was reused. Dropping the record without closing anything.",
                    UserWarning,
                    stacklevel=2,
                )
                self._records.pop(instance_number, None)
                Core.invalidate_active_instances_cache()
                return

            if not force:
                self._verify_not_busy(instance_number)

            windows_process.close_main_windows(record.pid)

            deadline = time.monotonic() + self._close_timeout
            while time.monotonic() < deadline:
                if not self._is_running(record):
                    break
                time.sleep(self._poll_interval)
            else:
                warnings.warn(
                    f"IviumSoft instance {instance_number} (pid {record.pid}) "
                    f"did not close within {self._close_timeout}s, "
                    "terminating the process",
                    UserWarning,
                    stacklevel=2,
                )
                self._terminate(record)

            self._records.pop(instance_number, None)
            Core.invalidate_active_instances_cache()

    def adopt(self, instance_number: int, pid: int) -> ManagedInstance:
        '''Re-attaches to an instance launched outside this manager (e.g.
            found after a process restart). The pid must come from an
            external source that recorded it: the driver cannot map instance
            numbers to pids.'''
        with self._lock:
            active_instances = Pyvium.get_active_iviumsoft_instances()
            if instance_number not in active_instances:
                raise ValueError(
                    f"Instance {instance_number} is not active "
                    f"(active instances: {active_instances})")
            if not windows_process.is_process_running(pid):
                raise ValueError(f"Process {pid} is not running")

            image_path = windows_process.get_process_image_path(pid)
            if image_path is None or not windows_process.same_image_path(
                    image_path, self._exe_path):
                raise ValueError(
                    f"Process {pid} is not this manager's IviumSoft: its image "
                    f"path is {image_path!r}, expected {self._exe_path!r}. "
                    "Adopting it would let close() message and terminate a "
                    "process that is not IviumSoft; construct the manager with "
                    "exe_path set to that install to manage it.")

            record = ManagedInstance(
                instance_number=instance_number,
                pid=pid,
                launched_at=None,
                managed=False,
                started_at=windows_process.get_process_creation_time(pid),
            )
            self._records[instance_number] = record
            return record

    def discover(self) -> DiscoveryReport:
        '''Read-only diagnostic: never launches, closes, prunes or adopts.

            Reports the records this manager holds (tracked), active driver
            instance numbers with no record (orphans), and IviumSoft
            processes (matched by the manager's exe path) that no record
            points at (untracked, sorted by start time). The recommended
            recovery flow is discover(), then adopt() each untracked
            process you can pair with an orphan number, then close_orphans()
            for whatever remains.'''
        with self._lock:
            active_instances = Pyvium.get_active_iviumsoft_instances()
            tracked = [self._records[number] for number in sorted(self._records)]
            known_pids = {record.pid for record in tracked
                          if record.pid is not None}

            untracked = [
                UntrackedProcess(
                    pid=pid,
                    started_at=windows_process.get_process_creation_time(pid),
                    window_title=windows_process.get_main_window_title(pid),
                )
                for pid in windows_process.find_pids_by_exe(self._exe_path)
                if pid not in known_pids
            ]
            untracked.sort(key=lambda process: (
                process.started_at is None,
                process.started_at or datetime.min,
                process.pid,
            ))

            return DiscoveryReport(
                tracked=tracked,
                orphan_instance_numbers=sorted(
                    number for number in active_instances
                    if number not in self._records),
                untracked_processes=untracked,
            )

    def close_orphans(self, force: bool = False) -> list[int]:
        '''Gracefully closes every untracked IviumSoft process (the
            untracked_processes of discover()), escalating to a hard
            terminate per process if it does not exit in time. Returns the
            pids that were closed.

            Orphan pids cannot be paired with driver instance numbers, so
            the busy check is all-or-nothing: if any orphan instance is
            measuring, nothing is closed unless force=True. For instances
            that are still in use, prefer discover() + adopt() over
            sweeping them away here.'''
        with self._lock:
            report = self.discover()
            if not force:
                for instance_number in report.orphan_instance_numbers:
                    if self._is_busy(instance_number):
                        raise DeviceBusyError(
                            f"Orphan instance {instance_number} is measuring "
                            "and cannot be paired with a specific process; "
                            "nothing was closed. Adopt and close it "
                            "individually, or use close_orphans(force=True) "
                            "to override.")

            # The whole sweep works from UntrackedProcess records rather than
            # bare pids: discover() already read each start time, and the loop
            # below can take close_timeout seconds, which is ample for a pid to
            # be recycled underneath it.
            pending = [process for process in report.untracked_processes
                       if self._is_our_process(process.pid, process.started_at)]
            closed_pids = [process.pid for process in pending]
            for process in pending:
                windows_process.close_main_windows(process.pid)

            deadline = time.monotonic() + self._close_timeout
            while pending:
                pending = [
                    process for process in pending
                    if windows_process.is_process_running(process.pid)
                    and self._is_our_process(process.pid, process.started_at)]
                if not pending or time.monotonic() >= deadline:
                    break
                time.sleep(self._poll_interval)

            for process in pending:
                warnings.warn(
                    f"Orphan IviumSoft process (pid {process.pid}) did not "
                    f"close within {self._close_timeout}s, terminating the "
                    "process",
                    UserWarning,
                    stacklevel=2,
                )
                if self._is_our_process(process.pid, process.started_at):
                    windows_process.terminate_process(process.pid)

            Core.invalidate_active_instances_cache()
            return closed_pids

    def list_instances(self) -> list[ManagedInstance]:
        '''Returns one record per active driver instance: launched and
            adopted ones carry their pid; unknown orphans have pid None.
            Stale records (instance or process gone) are pruned.'''
        with self._lock:
            active_instances = Pyvium.get_active_iviumsoft_instances()

            for instance_number in list(self._records):
                record = self._records[instance_number]
                if instance_number not in active_instances or not self._is_running(record):
                    del self._records[instance_number]

            return [
                self._records.get(instance_number) or ManagedInstance(
                    instance_number=instance_number,
                    pid=None,
                    launched_at=None,
                    managed=False,
                )
                for instance_number in active_instances
            ]

    def _is_busy(self, instance_number: int) -> bool:
        status_code, _ = Pyvium.instance(instance_number).get_device_status()
        return status_code == DEVICE_STATUS_BUSY

    def _verify_not_busy(self, instance_number: int) -> None:
        if self._is_busy(instance_number):
            raise DeviceBusyError(
                f"Instance {instance_number} is measuring, aborting the "
                "method first, or use close(force=True) to override")

    def _is_our_process(self, pid: int | None,
                        started_at: datetime | None) -> bool:
        '''True when pid is still the IviumSoft process the manager recorded.

            Two independent checks, because they catch different substitutions.
            The image path must still be this manager's exe, so a pid Windows
            handed to an unrelated program is never messaged or killed. The
            start time must match the one recorded, which is the only thing that
            tells one IviumSoft from another after a pid reuse. A start time
            that could not be read falls back to the exe check alone.'''
        if pid is None:
            return False
        image_path = windows_process.get_process_image_path(pid)
        if image_path is None or not windows_process.same_image_path(
                image_path, self._exe_path):
            return False
        if started_at is None:
            return True
        return windows_process.get_process_creation_time(pid) == started_at

    def _is_running(self, record: ManagedInstance) -> bool:
        if record.process is not None:
            # A held Popen handle stops Windows reusing the pid, so the poll
            # alone is conclusive for instances this manager launched.
            return record.process.poll() is None
        return (windows_process.is_process_running(record.pid)
                and self._is_our_process(record.pid, record.started_at))

    def _terminate(self, record: ManagedInstance) -> None:
        if record.process is not None:
            record.process.kill()
        elif self._is_our_process(record.pid, record.started_at):
            windows_process.terminate_process(record.pid)
