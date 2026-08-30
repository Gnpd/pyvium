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
from .errors import DeviceBusyError, IviumSoftNotRunningError
from .pyvium import Pyvium
from .util import windows_process

DEFAULT_IVIUMSOFT_EXE = r"C:\IviumStat\IviumSoft.exe"
DEVICE_STATUS_BUSY = 2

# Closing a measuring instance does not close IviumSoft: it raises a modal
# confirmation, and one per window messaged, so a close posts WM_CLOSE to the
# main form and the TApplication window and gets two of these back. Left
# unanswered they hold the process open until the close times out and
# terminates it, and a terminated process cannot deregister its instance
# number, which is how the number leaks.
#
# Recognition is by the button captions rather than the form class, because the
# captions are the part that has to stay stable for a user to understand the
# dialog. The class is carried only so a warning can name it. Verified on
# IviumSoft 4.1247: class TfrmIviumWifiDisconnect, title 'Confirm', with a
# TPanel reading 'IviumSoft Device: <serial> is measuring'.
MEASURING_DIALOG_CLASS = 'TfrmIviumWifiDisconnect'
MEASURING_DIALOG_BUTTONS = {
    'continue': 'Disconnect and Continue',   # BS_DEFPUSHBUTTON
    'abort': 'Disconnect and Abort',
    'cancel': 'Cancel',
}


def _validate_on_measuring(value: str | None) -> None:
    '''Rejects an unknown on_measuring before any window has been messaged.'''
    if value is not None and value not in MEASURING_DIALOG_BUTTONS:
        raise ValueError(
            "on_measuring must be None or one of "
            f"{sorted(MEASURING_DIALOG_BUTTONS)}, got {value!r}")


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
        process still starting up or one that died without deregistering.

        A record whose driver instance deregistered while its process is still
        alive appears on both sides: as a tracked record the manager still
        holds, and as an untracked process the OS still shows. That pairing is
        the mismatch, and it keeps the process visible and sweepable.'''
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

    def close(self, instance_number: int, force: bool = False,
              on_measuring: str | None = 'continue') -> None:
        '''Gracefully closes an instance with a window-close message.

            Raises ValueError for instances without a known pid; adopt() them
            first.

            The two parameters cover two separate questions.

            on_measuring answers the modal confirmation a measuring instance
            raises instead of closing:

              'continue'  (default) Disconnect and Continue. IviumSoft exits,
                          its instance number is released, and the measurement
                          carries on running on the device.
              'abort'     Disconnect and Abort. IviumSoft exits and the run
                          ends.
              'cancel'    Cancel. The close is refused and DeviceBusyError is
                          raised, leaving the process and the run alone. This
                          is how to say "never close a measuring instance"; it
                          is checked before anything is messaged and again at
                          the dialog, which covers an instance that goes busy
                          in between.
              None        Leave the dialog alone, so the close cannot complete.

            force says whether this may escalate to TerminateProcess, and
            nothing else. Without it a close that does not complete within
            close_timeout raises TimeoutError with the process still running
            and the record still held, so it can be retried or handed to
            terminate(). With it, the process is killed on that timeout and
            also if the close fails unexpectedly, and the original error is
            re-raised either way. A terminated IviumSoft cannot deregister, so
            its instance number is leaked for as long as any IviumSoft keeps
            running; force=True together with on_measuring=None is the only
            combination that leaks one.

            Closing an instance does not stop a measurement running on the
            device itself: on DataSecure hardware the run continues without any
            instance, and a later instance connecting to that device reloads it
            and carries the method on if it is still going. After a close answered
            with 'continue', a relaunched instance reconnects to a busy device,
            keeps counting points and aborts normally.'''
        _validate_on_measuring(on_measuring)
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

            self._check_before_close(instance_number, on_measuring)

            windows_before = set(
                windows_process.list_visible_windows(record.pid))
            windows_process.close_main_windows(record.pid)

            attempts: dict[int, int] = {}
            deadline = time.monotonic() + self._close_timeout
            # Whether the process is gone, and so whether the record and the
            # instance number should be given up. False on every path that
            # leaves IviumSoft running.
            finished = False
            try:
                while time.monotonic() < deadline:
                    if not self._is_running(record):
                        break
                    if self._answer_dialogs(record.pid, windows_before,
                                            attempts, on_measuring):
                        # A close raises one confirmation per window messaged,
                        # so give any sibling dialog a moment to appear and get
                        # its Cancel too; leaving one open would strand
                        # IviumSoft on a modal nobody is going to answer.
                        time.sleep(self._poll_interval)
                        self._answer_dialogs(record.pid, windows_before,
                                             attempts, on_measuring)
                        raise DeviceBusyError(
                            f"Instance {instance_number} is measuring and the "
                            "close was cancelled at its confirmation dialog; "
                            "IviumSoft is still running. Use "
                            "on_measuring='continue' to close it and leave the "
                            "measurement running, or 'abort' to end it.")
                    time.sleep(self._poll_interval)
                else:
                    if not force:
                        raise TimeoutError(
                            f"IviumSoft instance {instance_number} (pid "
                            f"{record.pid}) did not close within "
                            f"{self._close_timeout}s and is still running. "
                            "Retry, or call terminate() to kill it, which "
                            "leaks the instance number.")
                    warnings.warn(
                        f"IviumSoft instance {instance_number} (pid "
                        f"{record.pid}) did not close within "
                        f"{self._close_timeout}s, terminating the process",
                        UserWarning,
                        stacklevel=2,
                    )
                    self._terminate(record)
                finished = True
            except DeviceBusyError:
                # A Cancel is a deliberate refusal, never a reason to kill.
                raise
            except Exception:
                # force also covers a close that fails unexpectedly. Exception
                # and not BaseException on purpose: a Ctrl-C must not turn into
                # a killed instrument and a leaked instance number.
                if force:
                    warnings.warn(
                        f"IviumSoft instance {instance_number} (pid "
                        f"{record.pid}) failed to close cleanly, terminating "
                        "the process because force=True",
                        UserWarning,
                        stacklevel=2,
                    )
                    self._terminate(record)
                    finished = True
                raise
            finally:
                if finished:
                    self._records.pop(instance_number, None)
                    # The leak check rescans, which repopulates the cache, so
                    # the invalidation has to come after it: a close must
                    # always leave the cache empty for the next reader.
                    self._warn_if_leaked(instance_number)
                # Invalidated on every path, including the ones that raise: the
                # WM_CLOSE was posted and may still land.
                Core.invalidate_active_instances_cache()

    def terminate(self, instance_number: int) -> None:
        '''Kills an instance's process outright. The last resort.

            IviumSoft gets no chance to shut down, which means it never
            deregisters: the instance number stays in the driver's active list
            with nothing behind it, and a slot in that state answers every DLL
            call as though it were alive (its last device status, result code
            0, and data aliased from the previous read on a live instance).
            The number is spent for as long as any IviumSoft keeps running, and
            later launches get the next one up.

            close() avoids all of that, including on a measuring instance, so
            reach for this only when a close has already failed. The natural
            pairing is:

                try:
                    manager.close(n)
                except TimeoutError:
                    manager.terminate(n)

            Raises ValueError for instances without a known pid.'''
        with self._lock:
            record = self._records.get(instance_number)
            if record is None or record.pid is None:
                raise ValueError(
                    f"Instance {instance_number} has no known pid in this "
                    "manager. Launch it here or adopt(instance_number, pid) "
                    "before terminating.")

            if not self._is_our_process(record.pid, record.started_at):
                warnings.warn(
                    f"Instance {instance_number} (pid {record.pid}) is no "
                    "longer the process this manager recorded: it exited and "
                    "the pid was reused. Dropping the record without "
                    "terminating anything.",
                    UserWarning,
                    stacklevel=2,
                )
                self._records.pop(instance_number, None)
                Core.invalidate_active_instances_cache()
                return

            self._terminate(record)
            self._records.pop(instance_number, None)
            self._warn_if_leaked(instance_number)
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
            # Only a record whose instance is still active claims its pid. One
            # whose instance deregistered while its process lives is reported
            # on both sides, as a held record and as an untracked process:
            # that pairing mismatch is exactly what this report exists to show.
            known_pids = {record.pid for record in tracked
                          if record.pid is not None
                          and record.instance_number in active_instances}

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

    def close_orphans(self, force: bool = False,
                      on_measuring: str | None = 'continue') -> list[int]:
        '''Gracefully closes every untracked IviumSoft process (the
            untracked_processes of discover()). Returns the pids that closed.

            Both parameters mean what they mean in close(), and default the
            same way. For instances that are still in use, prefer discover() +
            adopt() over sweeping them away here.

            The sweep is batched, so nothing here raises for one process: a
            'cancel' refusal and, without force, a process that will not close
            are each reported through a warning and left out of the returned
            pids. One stubborn orphan is not a reason to abandon the rest.

            on_measuring='cancel' is the exception, because orphan pids cannot
            be paired with driver instance numbers: if any orphan instance is
            measuring, nothing is closed at all.'''
        _validate_on_measuring(on_measuring)
        with self._lock:
            report = self.discover()
            if on_measuring == 'cancel':
                for instance_number in report.orphan_instance_numbers:
                    if self._is_busy(instance_number):
                        raise DeviceBusyError(
                            f"Orphan instance {instance_number} is measuring "
                            "and cannot be paired with a specific process, so "
                            "nothing was closed. Adopt and close it "
                            "individually, or sweep with "
                            "on_measuring='continue' to close it and leave the "
                            "measurement running.")

            # The whole sweep works from UntrackedProcess records rather than
            # bare pids: discover() already read each start time, and the loop
            # below can take close_timeout seconds, which is ample for a pid to
            # be recycled underneath it.
            pending = [process for process in report.untracked_processes
                       if self._is_our_process(process.pid, process.started_at)]
            closed_pids = [process.pid for process in pending]
            windows_before = {
                process.pid: set(
                    windows_process.list_visible_windows(process.pid))
                for process in pending}
            attempts: dict[int, dict[int, int]] = {
                process.pid: {} for process in pending}
            cancelled_pids: set[int] = set()
            for process in pending:
                windows_process.close_main_windows(process.pid)

            deadline = time.monotonic() + self._close_timeout
            while pending:
                for process in pending:
                    if self._answer_dialogs(process.pid,
                                            windows_before[process.pid],
                                            attempts[process.pid],
                                            on_measuring):
                        cancelled_pids.add(process.pid)
                pending = [
                    process for process in pending
                    if process.pid not in cancelled_pids
                    and windows_process.is_process_running(process.pid)
                    and self._is_our_process(process.pid, process.started_at)]
                if not pending or time.monotonic() >= deadline:
                    break
                time.sleep(self._poll_interval)

            stuck_pids = {process.pid for process in pending}
            for process in pending:
                if force:
                    warnings.warn(
                        f"Orphan IviumSoft process (pid {process.pid}) did not "
                        f"close within {self._close_timeout}s, terminating the "
                        "process; its instance number is leaked",
                        UserWarning,
                        stacklevel=2,
                    )
                    if self._is_our_process(process.pid, process.started_at):
                        windows_process.terminate_process(process.pid)
                        stuck_pids.discard(process.pid)
                else:
                    warnings.warn(
                        f"Orphan IviumSoft process (pid {process.pid}) did not "
                        f"close within {self._close_timeout}s and is still "
                        "running; it is not reported as closed. Sweep with "
                        "force=True to terminate it, which leaks its instance "
                        "number.",
                        UserWarning,
                        stacklevel=2,
                    )

            closed_pids = [pid for pid in closed_pids
                           if pid not in cancelled_pids
                           and pid not in stuck_pids]

            Core.invalidate_active_instances_cache()
            return closed_pids

    def list_instances(self) -> list[ManagedInstance]:
        '''Returns one record per active driver instance: launched and
            adopted ones carry their pid; unknown orphans have pid None.
            Records whose process is gone are pruned. A record whose driver
            instance deregistered while its process is still alive is kept, so
            the leftover process stays closable through close(); it drops out
            of the returned list, which is keyed on the active instances.'''
        with self._lock:
            active_instances = Pyvium.get_active_iviumsoft_instances()

            for instance_number in list(self._records):
                record = self._records[instance_number]
                if not self._is_running(record):
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

    def _answer_dialogs(self, pid: int, windows_before: set[int],
                        attempts: dict[int, int],
                        on_measuring: str | None) -> bool:
        '''Answers the confirmations a close raised on this process.

            Any visible top-level window that was not there before the
            WM_CLOSE is a candidate. attempts carries state across polls, so a
            dialog is clicked once, retried once with Enter, then left alone.
            Returns True when a dialog was answered with Cancel, meaning the
            caller asked for the close to be refused.'''
        if on_measuring is None:
            return False

        wanted_caption = MEASURING_DIALOG_BUTTONS[on_measuring]
        expected_captions = set(MEASURING_DIALOG_BUTTONS.values())
        cancelled = False

        for hwnd in windows_process.list_visible_windows(pid):
            if hwnd in windows_before or attempts.get(hwnd, 0) >= 2:
                continue

            dialog = windows_process.describe_window(hwnd)
            buttons = {control.text: control for control in dialog.controls}

            if not expected_captions <= set(buttons):
                # Not the measuring confirmation. Enter on an unknown Delphi
                # form would activate whatever its default button happens to
                # be, so report it and leave it alone; the close falls through
                # to its timeout as before.
                captions = sorted(control.text for control in dialog.controls
                                  if control.text)
                warnings.warn(
                    f"IviumSoft (pid {pid}) raised a window this manager does "
                    f"not recognise while closing: class {dialog.class_name!r}"
                    f", title {dialog.title!r}, controls {captions}. It was "
                    "left alone, so the close will time out and terminate the "
                    "process.",
                    UserWarning,
                    stacklevel=2,
                )
                attempts[hwnd] = 2
                continue

            target = buttons[wanted_caption]
            if attempts.get(hwnd, 0) == 0:
                windows_process.click_button(target.hwnd)
            elif target.is_default_button:
                # The posted click did not take. Enter activates the default
                # button, which is the form's own answer to being dismissed.
                windows_process.press_enter(hwnd)
            attempts[hwnd] = attempts.get(hwnd, 0) + 1
            cancelled = cancelled or on_measuring == 'cancel'

        return cancelled

    def _warn_if_leaked(self, instance_number: int) -> None:
        '''Warns when a closed instance number is still registered.

            Reads the unfiltered scan on purpose: the host-window check hides a
            leaked number from callers, which is the point, but the DLL slot is
            still spent and the next launch gets the number above it. This is
            the moment a caller can still do something about it.'''
        if instance_number in Pyvium.get_active_iviumsoft_instances(
                verify_host_window=False):
            warnings.warn(
                f"Instance {instance_number} is still registered with the "
                "driver although its process is gone: a terminated IviumSoft "
                "cannot deregister. The number stays spent for the lifetime "
                "of this process and later launches get the next one up. "
                "Closing with on_measuring set (the default) avoids this.",
                UserWarning,
                stacklevel=2,
            )

    def _device_status(self, instance_number: int) -> int | None:
        '''Status code for one instance, or None when it is no longer
            registered with the driver (closed from its own window, crashed,
            or still winding down).

            None is not the same as idle: the instance cannot be asked whether
            its device is measuring.'''
        try:
            status_code, _ = Pyvium.instance(instance_number).get_device_status()
        except IviumSoftNotRunningError:
            return None
        return status_code

    def _is_busy(self, instance_number: int) -> bool:
        return self._device_status(instance_number) == DEVICE_STATUS_BUSY

    def _check_before_close(self, instance_number: int,
                            on_measuring: str | None) -> None:
        '''Reports what is known about the instance before anything is messaged.

            Only on_measuring='cancel' asks for a measuring instance to be left
            alone, and this is its cheap early exit: one status read, with no
            WM_CLOSE posted and no dialog raised. The Cancel click in the wait
            loop still backs out an instance that goes busy between this check
            and the close, which no status read can prevent.'''
        status_code = self._device_status(instance_number)
        if status_code is None:
            # The instance has already left the driver, so it is not running a
            # measurement through it and closing the leftover process cannot
            # make anything worse. Reported rather than raised: refusing here
            # would leave a hung process with no way to clean it up.
            warnings.warn(
                f"Instance {instance_number} had already deregistered from the "
                "driver (closed, crashed, or hung), so it could not be checked "
                "for a running measurement; cleaning up its leftover process",
                UserWarning,
                stacklevel=2,
            )
            return
        if status_code == DEVICE_STATUS_BUSY and on_measuring == 'cancel':
            raise DeviceBusyError(
                f"Instance {instance_number} is measuring and on_measuring is "
                "'cancel', so nothing was messaged. Use 'continue' to close it "
                "and leave the measurement running on the device, or 'abort' "
                "to end it.")

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
