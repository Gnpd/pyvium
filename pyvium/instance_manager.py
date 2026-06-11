'''Lifecycle management for IviumSoft application instances.

Opens, tracks, adopts and gracefully closes IviumSoft processes, mapping
each one to the driver instance number it registered with. The driver must
already be open (Pyvium.open_driver()) for any operation that talks to it.
'''
import subprocess
import threading
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime

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


class IviumsoftInstanceManager:
    '''Opens and closes IviumSoft instances and maps them to driver
        instance numbers.

        launch() attributes the new driver instance number to the spawned
        process by diffing the active-instance list before and after, so
        launches are serialized: one manager lock covers launch and close.

        The driver instance numbering after an instance closes is assumed
        stable for the remaining instances (pending confirmation from Ivium,
        see INTEGRATION_PLAN §7.1).'''

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
                    )
                    self._records[instance_number] = record
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
            Raises ValueError for instances without a known pid — adopt()
            them first.'''
        with self._lock:
            record = self._records.get(instance_number)
            if record is None or record.pid is None:
                raise ValueError(
                    f"Instance {instance_number} has no known pid in this "
                    "manager. Launch it here or adopt(instance_number, pid) "
                    "before closing.")

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
                    f"did not close within {self._close_timeout}s — "
                    "terminating the process",
                    UserWarning,
                    stacklevel=2,
                )
                self._terminate(record)

            self._records.pop(instance_number, None)

    def adopt(self, instance_number: int, pid: int) -> ManagedInstance:
        '''Re-attaches to an instance launched outside this manager (e.g.
            found after an API-server restart). The pid must come from an
            external source such as a session registry: the driver cannot
            map instance numbers to pids.'''
        with self._lock:
            active_instances = Pyvium.get_active_iviumsoft_instances()
            if instance_number not in active_instances:
                raise ValueError(
                    f"Instance {instance_number} is not active "
                    f"(active instances: {active_instances})")
            if not windows_process.is_process_running(pid):
                raise ValueError(f"Process {pid} is not running")

            record = ManagedInstance(
                instance_number=instance_number,
                pid=pid,
                launched_at=None,
                managed=False,
            )
            self._records[instance_number] = record
            return record

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

    def _verify_not_busy(self, instance_number: int) -> None:
        status_code, _ = Pyvium.device(instance_number).get_device_status()
        if status_code == DEVICE_STATUS_BUSY:
            raise DeviceBusyError(
                f"Instance {instance_number} is measuring — aborting the "
                "method first, or use close(force=True) to override")

    @staticmethod
    def _is_running(record: ManagedInstance) -> bool:
        if record.process is not None:
            return record.process.poll() is None
        return windows_process.is_process_running(record.pid)

    @staticmethod
    def _terminate(record: ManagedInstance) -> None:
        if record.process is not None:
            record.process.kill()
        else:
            windows_process.terminate_process(record.pid)
