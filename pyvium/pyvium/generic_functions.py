import time
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType

from ..core import Core
from ..errors import (DeviceNotConnectedToIviumSoftError,
                      IviumSoftNotRunningError)
from ..pyvium_verifiers import PyviumVerifiers
from ..util import windows_process

# Only the codes the DLL documents. Never index this directly with a code that
# came back from the DLL: go through device_status_label, which falls back
# instead of raising if a future release reports something new.
_STATUS_LABELS = {
    -1: 'no IviumSoft',
    0: 'not connected',
    1: 'available_idle',
    2: 'available_busy',
    3: 'no device available',
}

# Public, read-only view of the device-status code -> label map, so consumers do
# not have to reach into this private module. Read-only so callers cannot mutate
# the shared mapping.
DEVICE_STATUS_LABELS = MappingProxyType(_STATUS_LABELS)


def device_status_label(status_code: int) -> str:
    '''Human-readable label for a device status code (as returned by
        get_device_status / IV_getdevicestatus): -1..3. Falls back to a readable
        "unknown (code)" string instead of raising on an unexpected code.'''
    return _STATUS_LABELS.get(status_code, f"unknown ({status_code})")
# Status codes for which IV_readSN cannot return a meaningful serial number
# (no device behind the channel), so the scan skips the read for them.
_NO_SERIAL_STATUS = (-1, 0, 3)

# Multichannel control supports up to 32 channels/tabs (IviumSoft manual,
# "Multichannel control"). IV_SelectChannel does NOT bounds-check its argument:
# it treats the integer as the NUMBER OF TABS to open and always returns 0, so an
# out-of-range value (e.g. 999) silently makes IviumSoft open that many tabs. The
# high-level API guards against that with _verify_channel_number.
MAX_CHANNELS = 32


# IV_connect completes asynchronously: the status goes 0 -> 1 over a short window
# after the call returns. Anything that needs to know WHICH device landed has to
# wait for that window and read the serial back. The connect itself comes up
# sub-second once it starts, so a short poll is enough.
_CONNECT_SETTLE_TIMEOUT_S = 3.0
_CONNECT_POLL_INTERVAL_S = 0.2


def _await_connected_serial(timeout: float | None = None) -> str:
    '''Polls the currently selected instance/channel until a device is connected
        and returns its serial number.

        Returns the connected serial once the status reaches 1/2, or '' if the
        connection never landed within the timeout (the slot stayed free). The
        caller must hold the driver lock for the whole poll, otherwise another
        thread could change the selection and this would read a different
        channel's device.

        timeout defaults to _CONNECT_SETTLE_TIMEOUT_S, read at call time so the
        module constant stays adjustable.'''
    deadline = time.monotonic() + (
        _CONNECT_SETTLE_TIMEOUT_S if timeout is None else timeout)
    while True:
        if Core.IV_getdevicestatus() in (1, 2):
            return Core.IV_readSN()[1]
        if time.monotonic() >= deadline:
            return ''
        time.sleep(_CONNECT_POLL_INTERVAL_S)


def _verify_channel_number(channel_number: int) -> None:
    '''Raise ValueError unless channel_number is a valid 1..MAX_CHANNELS channel.

        IV_SelectChannel opens [channel_number] tabs without validating the value,
        so a typo or out-of-range number would make IviumSoft open that many tabs.
        This keeps the bare DLL behaviour from leaking through the high-level API.'''
    if not 1 <= channel_number <= MAX_CHANNELS:
        raise ValueError(
            f"channel number {channel_number} is out of range (1..{MAX_CHANNELS}); "
            "IV_SelectChannel treats the value as a tab count and would open that "
            "many tabs")


def _scan_restore_target(previous_instance: int, active_instances: list) -> int:
    '''Returns the instance a completed scan should leave selected.

        The previous selection when it is still running, so a scan has no side
        effect. When that instance has gone and another is running, the lowest
        active one instead: reporting which instances are alive and then parking
        the caller on a dead one makes the next command fail for no reason. When
        nothing at all is running there is no better target, so the previous
        selection stands.'''
    if previous_instance in active_instances or not active_instances:
        return previous_instance
    return active_instances[0]


def _host_window_is_gone() -> bool:
    '''True when the selected instance's host window provably no longer exists.

        IV_HostHandle answers with the window the currently selected IviumSoft
        registered with the driver. A process that was terminated rather than
        closed leaves that handle behind pointing at nothing, which is the one
        reliable mark of a leaked slot: the device status is unchanged. Only a
        non-zero handle that IsWindow rejects counts, so a slot is never hidden
        on missing evidence.'''
    handle = Core.IV_HostHandle()
    return bool(handle) and not windows_process.is_window(handle)


@dataclass
class ChannelStatus:
    '''One multichannel channel as seen during a get_channel_statuses scan.

        serial_number is empty when no device sits behind the channel
        (status_code in -1/0/3). status_label is the human-readable form of
        status_code, matching get_device_status.'''
    channel: int
    serial_number: str
    status_code: int
    status_label: str


class GenericFunctions():  # pylint: disable=too-many-public-methods
    @staticmethod
    def open_driver(verify_iviumsoft: bool = True):
        '''Open the driver to manipulate the Ivium software.

            verify_iviumsoft=False skips the check that an IviumSoft instance
            is running, allowing a cold start where instances are launched
            afterwards (e.g. via IviumsoftInstanceManager). Every subsequent
            command still verifies IviumSoft on its own.

            The driver starts on instance 1, so opening it resets the selected
            instance and channel to 1: a selection made before a close does not
            carry over into the reopened driver.'''
        if Core.is_driver_open():
            warnings.warn(
                "open_driver() called but driver is already open, closing and reopening",
                UserWarning,
                stacklevel=2,
            )
            Core.IV_close()
        Core.IV_open()
        Core.invalidate_active_instances_cache()  # instance set is now unknown
        if not verify_iviumsoft:
            return
        try:
            PyviumVerifiers.verify_iviumsoft_is_running()
        except:
            Core.IV_close()
            raise

    @staticmethod
    def close_driver():
        '''Closes the iviumSoft driver.

            Also resets the selected instance and channel to 1, so a stale
            selection cannot outlive the driver that held it.'''
        if not Core.is_driver_open():
            # Nothing to close, and nothing to reset: whatever closed the
            # driver already reset the selection.
            return
        Core.IV_close()
        Core.invalidate_active_instances_cache()

    @staticmethod
    def get_max_device_number():
        '''Returns the maximum number of devices that can be managed by IviumSoft.

            Per the DLL reference this is the maximum number of simultaneous
            IviumSoft instances (32), not a count of hardware devices; "device"
            here follows the DLL naming. See docs/terminology.md. Pending
            hardware confirmation.'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_MaxDevices()

    @staticmethod
    def get_device_status() -> tuple[int, str]:
        '''It returns -1 (no IviumSoft), 0 (not connected), 1 (available_idle), 2 (available_busy),
            3 (no device available)

            A code outside that set is returned as-is, labelled
            "unknown (code)"; a status query does not raise over one.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        result_code = Core.IV_getdevicestatus()
        return result_code, device_status_label(result_code)

    @staticmethod
    def is_iviumsoft_running() -> bool:
        '''It returns true if the selected instance of IviumSoft is running'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_getdevicestatus() != -1

    @staticmethod
    def get_active_iviumsoft_instances(use_cache: bool = False,
                                       verify_host_window: bool = True):
        '''Returns a list of active (open) IviumSoft instances.

            A full scan probes all 32 possible instance slots (32
            IV_getdevicestatus calls); it changes the selected instance while it
            runs, so it holds the driver lock and restores the previous selection
            afterwards. The slot count is fixed at 32.

            verify_host_window drops a slot whose IviumSoft process is provably
            gone. An IviumSoft that was terminated rather than closed cannot
            deregister, so the driver keeps reporting its slot as active with no
            process behind it, and the slot never heals: not on a rescan, not on
            close_driver() + open_driver(), only in a new process. Such a slot
            still answers IV_HostHandle with the window handle it registered,
            which is now a handle to nothing, so a slot is dropped only on
            positive proof, a non-zero handle that IsWindow rejects. A handle of
            zero or one that cannot be read is left alone: reporting a leaked
            slot is a much smaller problem than hiding a live instance. Pass
            False for the raw driver view.

            One exception to that restore: if the previously selected instance is
            no longer running and another one is, the scan leaves the selection on
            the lowest-numbered running instance instead. Reporting which
            instances are alive and then parking the caller on a dead one would
            make the next command raise IviumSoftNotRunningError for no reason.
            With nothing running at all the previous selection stands.

            use_cache=True returns the list from the last full scan without
            touching the DLL, when one is available. The cache is kept fresh by
            open_driver/close_driver and the instance manager, but it cannot see
            instances that appeared or closed outside this process, so a periodic
            use_cache=False rescan is still needed. A status poller should iterate
            the known set (one get_device_status per instance) and only rescan
            occasionally to pick up topology changes.'''
        PyviumVerifiers.verify_driver_is_open()
        if use_cache:
            cached = Core.get_active_instances_cache()
            if cached is not None:
                return list(cached)
        active_instances = []
        scan_completed = False
        with Core.get_lock():
            previous_instance = Core.get_selected_instance()
            try:
                for instance_number in range(1, 33):
                    Core.IV_selectdevice(instance_number)

                    if Core.IV_getdevicestatus() == -1:
                        continue
                    if verify_host_window and _host_window_is_gone():
                        continue
                    active_instances.append(instance_number)
                scan_completed = True
            finally:
                # A scan that died partway holds a partial list, which says
                # nothing about the instances it never reached, so restore
                # blindly in that case.
                Core.IV_selectdevice(
                    _scan_restore_target(previous_instance, active_instances)
                    if scan_completed else previous_instance)
            Core.set_active_instances_cache(active_instances)
        return active_instances

    @staticmethod
    @contextmanager
    def on_instance(iviumsoft_instance_number: int):
        '''Context manager that runs a block of commands on a given IviumSoft
            instance atomically.

            Acquires the process-wide driver lock, selects the instance, runs
            the block, and restores the previously selected instance, even if
            the block raises. While the block runs, no other thread can issue
            DLL commands, so the selection cannot change underneath it:

                with Pyvium.on_instance(3):
                    Pyvium.connect_device()
                    Pyvium.start_method('cv.imf')

            Note: this does not verify the instance is running (that scan is
            expensive); commands inside the block raise IviumSoftNotRunningError
            through the verifiers if it is not.'''
        PyviumVerifiers.verify_driver_is_open()
        with Core.get_lock():
            previous_instance = Core.get_selected_instance()
            Core.IV_selectdevice(iviumsoft_instance_number)
            try:
                yield
            finally:
                Core.IV_selectdevice(previous_instance)

    @staticmethod
    def select_iviumsoft_instance(iviumsoft_instance_number: int):
        '''It allows to select one instance of the currently running IviumSoft instances'''

        PyviumVerifiers.verify_driver_is_open()
        with Core.get_lock():
            active_instances = GenericFunctions.get_active_iviumsoft_instances()
            if iviumsoft_instance_number not in active_instances:
                error_msg = 'No IviumSoft on instance number {}, actual active instances list = {}'
                raise IviumSoftNotRunningError(error_msg.format(
                    iviumsoft_instance_number, active_instances))
            Core.IV_selectdevice(iviumsoft_instance_number)

    @staticmethod
    def get_device_serial_number():
        '''Returns the serial number of the currently selected device if available'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_computer()
        _, serial_number = Core.IV_readSN()
        if serial_number == '':
            raise DeviceNotConnectedToIviumSoftError(
                'This device needs to be connected to get its serial number')
        return serial_number

    @staticmethod
    def connect_device():
        '''It connects the currently selected device'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_computer()
        if Core.IV_getdevicestatus() in (1, 2):
            warnings.warn(
                "connect_device() called but device is already connected, skipping",
                UserWarning,
                stacklevel=2,
            )
            return
        result_code, _ = Core.IV_connect(1)
        PyviumVerifiers.verify_result_code(result_code, context="connect_device")

    @staticmethod
    def disconnect_device():
        '''It disconnects the currently selected device'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_computer()
        result_code, _ = Core.IV_connect(0)
        PyviumVerifiers.verify_result_code(result_code, context="disconnect_device")

    @staticmethod
    def get_dll_version() -> int:
        '''Returns the version of the IviumSoft dll'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_VersionDll()

    @staticmethod
    def get_iviumsoft_version() -> str:
        '''Returns the version of the IviumSoft that match with this pyvium version'''
        PyviumVerifiers.verify_driver_is_open()
        version = str(Core.IV_VersionDllFile())[:5]
        return version[:1] + '.' + version[1:]

    @staticmethod
    def get_version_host() -> int:
        '''Returns the required DLL version for the active IviumSoft version'''
        PyviumVerifiers.verify_driver_is_open()
        _, version = Core.IV_VersionHost(0)
        return version

    @staticmethod
    def check_dll_version() -> bool:
        '''Returns True if the DLL version matches the IviumSoft requirement'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_VersionCheck() == 1

    @staticmethod
    def get_host_handle() -> int:
        '''Returns the host handle'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_HostHandle()

    @staticmethod
    def get_dll_version_string() -> str:
        '''Returns the DLL version as a formatted string (e.g. "4.123910334").'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_VersionDllFileStr()

    @staticmethod
    def select_channel(channel_number: int):
        '''Sending the integer value communicates with Multichannel control:
            if not yet active,
            the [int] number of tabs is automatically opened and the [int] tab becomes active;
            if Ivium-n-Soft is active already, the [int] tab becomes active.
            Now the channel/instrument that is connected to this tab can be controlled.
            If no instrument is connected,
            the next available instrument in the list can be connected (IV_connect) and
            controlled.

            channel_number must be in 1..MAX_CHANNELS (32); a larger value would
            make IviumSoft open that many tabs (see _verify_channel_number), so it
            raises ValueError instead.

            This is a bare selection: to drive several channels safely from
            several threads, use on_channel / Pyvium.instance(n).channel(m), which
            hold the driver lock across the selection and the commands that
            follow it.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        _verify_channel_number(channel_number)
        # IV_SelectChannel's return is not routed through verify_result_code:
        # hardware-confirmed it always returns 0 and carries no status (the int is
        # an unvalidated tab count, not a setter code), so there is nothing to route.
        Core.IV_SelectChannel(channel_number)

    @staticmethod
    def select_serial_number(serial_number: str) -> int | None:
        '''Selects a device by serial number, making it ready to connect.
            Returns the position index in the dropdown list (0-based), or None if
            the device is already connected and no reselection was needed.
            Warns if the requested device is already connected, skips reselection.
            Raises DeviceNotConnectedToIviumSoftError if the serial number is not
            found in the device list, or if a different device is already connected.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        if Core.IV_getdevicestatus() in (1, 2):
            _, connected_serial = Core.IV_readSN()
            if connected_serial == serial_number:
                warnings.warn(
                    f"select_serial_number('{serial_number}') called but this device "
                    "is already connected, skipping.",
                    UserWarning,
                    stacklevel=2,
                )
                return None  # device already active, no selection performed
            raise DeviceNotConnectedToIviumSoftError(
                f"Cannot select '{serial_number}': device '{connected_serial}' is already "
                "connected. Call disconnect_device() first."
            )

        device_index = Core.IV_SelectSn(serial_number)
        if device_index == -1:
            raise DeviceNotConnectedToIviumSoftError(
                f"Serial number '{serial_number}' not found in the available device list."
            )
        return device_index

    @staticmethod
    @contextmanager
    def on_channel(channel_number: int):
        '''Context manager that runs a block of commands on a given
            multichannel channel atomically.

            The twin of on_instance, one level down: acquires the process-wide
            driver lock, selects the channel, runs the block, and restores the
            previously selected channel even if the block raises:

                with Pyvium.on_channel(3):
                    Pyvium.connect_device()
                    Pyvium.start_method('cv.imf')

            A channel only means something within the selected IviumSoft
            instance, so nest this inside on_instance (or use
            Pyvium.instance(n).channel(m), which does both):

                with Pyvium.on_instance(2):
                    with Pyvium.on_channel(3):
                        ...

            The lock serializes this process's threads only. It cannot stop a
            manual channel change in the IviumSoft UI (a separate process), so
            the restored channel is the last value we selected, not the live UI
            state. For robust connection targeting that does not depend on the
            active channel, prefer select_serial_number / connect_device_to_channel.

            channel_number must be in 1..MAX_CHANNELS (32), else ValueError.'''
        PyviumVerifiers.verify_driver_is_open()
        _verify_channel_number(channel_number)
        with Core.get_lock():
            previous_channel = Core.get_selected_channel()
            Core.IV_SelectChannel(channel_number)
            try:
                yield
            finally:
                Core.IV_SelectChannel(previous_channel)

    @staticmethod
    def get_channel_statuses(number_of_channels: int) -> list[ChannelStatus]:
        '''Scans channels 1..number_of_channels and returns one ChannelStatus
            per channel (channel, serial number, status code, status label).

            The whole scan runs under the driver lock and restores the
            previously selected channel afterwards, so it does not interleave
            with other threads. The serial number is read only for channels
            that have a device behind them; it is empty otherwise.

            number_of_channels must be in 1..MAX_CHANNELS (32); the scan calls
            IV_SelectChannel up to that value, which would open that many tabs.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        _verify_channel_number(number_of_channels)
        statuses = []
        with Core.get_lock():
            previous_channel = Core.get_selected_channel()
            try:
                for channel in range(1, number_of_channels + 1):
                    Core.IV_SelectChannel(channel)
                    status_code = Core.IV_getdevicestatus()
                    serial_number = (
                        Core.IV_readSN()[1]
                        if status_code not in _NO_SERIAL_STATUS else '')
                    statuses.append(ChannelStatus(
                        channel=channel,
                        serial_number=serial_number,
                        status_code=status_code,
                        status_label=device_status_label(status_code),
                    ))
            finally:
                Core.IV_SelectChannel(previous_channel)
        return statuses

    @staticmethod
    def connect_device_to_channel(serial_number: str, channel: int,
                                  alias: str | None = None) -> None:
        '''Connects a specific device to a specific Multichannel-control tab.

            Selects the channel, disconnects any idle device already on it,
            then selects the requested device and connects it. The whole
            sequence runs under the driver lock so no other thread can change
            the selection mid-way.

            Two identifiers are involved and they are not always the same value
            (see docs/terminology.md):

              serial_number  the device identity, what IV_readSN reports. This
                             is what the connection is verified against.
              alias          the IviumSoft dropdown selection token IV_SelectSn
                             takes. On a single-channel device it equals the
                             serial, so it can be omitted. On multichannel
                             hardware each channel has its own token (e.g.
                             "Oc-0-3") distinct from its per-channel serial, and
                             the serial will not select anything. This is the
                             selection token, not a human display name.

            Resolving a serial to its alias is left to the caller: the mapping
            comes from the hardware configuration and is not discoverable
            through the DLL.

            Unlike on_channel, this leaves the target channel active on return:
            connecting is a deliberate state change toward that channel, so
            restoring a previous channel would only flip the focused tab away
            (the connection itself persists regardless of the active tab).

            IV_connect is asynchronous and connects the first available device,
            which IV_SelectSn steers by putting the requested device at the top
            of the list. A second connect issued before the first has settled can
            therefore land on the wrong device, so the driver lock is held until
            the connection has come up and the serial has been read back. A
            connection that lands on a different device is disconnected again
            (freeing it) and reported as a failure rather than a false success.

            channel must be in 1..MAX_CHANNELS (32), else ValueError.

            Raises DeviceNotConnectedToIviumSoftError if the device is not in
            the available device list, if the connection does not come up within
            the settle timeout, or if it lands on a different device.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        _verify_channel_number(channel)
        with Core.get_lock():
            Core.IV_SelectChannel(channel)
            if Core.IV_getdevicestatus() == 1:  # idle, a device is connected
                GenericFunctions.disconnect_device()
            GenericFunctions.select_serial_number(alias or serial_number)
            GenericFunctions.connect_device()

            connected_serial = _await_connected_serial()
            if connected_serial == serial_number:
                return
            if not connected_serial:
                raise DeviceNotConnectedToIviumSoftError(
                    f"Connecting '{serial_number}' on channel {channel} did not "
                    f"complete within {_CONNECT_SETTLE_TIMEOUT_S}s; the channel "
                    "is still free.")
            # Mis-grab: the connect took a different device than the one that was
            # selected. Free it so it can be connected through its own channel.
            disconnect_error = ''
            try:
                GenericFunctions.disconnect_device()
            except Exception as error:  # pylint: disable=broad-except
                disconnect_error = f"; disconnecting it failed: {error}"
            raise DeviceNotConnectedToIviumSoftError(
                f"Connecting '{serial_number}' on channel {channel} grabbed "
                f"'{connected_serial}' instead{disconnect_error}.")
