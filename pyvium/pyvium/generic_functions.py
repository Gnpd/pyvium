import warnings
from contextlib import contextmanager
from dataclasses import dataclass

from ..core import Core
from ..errors import (DeviceNotConnectedToIviumSoftError,
                      IviumSoftNotRunningError)
from ..pyvium_verifiers import PyviumVerifiers

_STATUS_LABELS = {
    -1: 'no IviumSoft',
    0: 'not connected',
    1: 'available_idle',
    2: 'available_busy',
    3: 'no device available',
}
# Status codes for which IV_readSN cannot return a meaningful serial number
# (no device behind the channel), so the scan skips the read for them.
_NO_SERIAL_STATUS = (-1, 0, 3)


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
            command still verifies IviumSoft on its own.'''
        if Core.is_driver_open():
            warnings.warn(
                "open_driver() called but driver is already open, closing and reopening",
                UserWarning,
                stacklevel=2,
            )
            Core.IV_close()
        Core.IV_open()
        if not verify_iviumsoft:
            return
        try:
            PyviumVerifiers.verify_iviumsoft_is_running()
        except:
            Core.IV_close()
            raise

    @staticmethod
    def close_driver():
        '''Closes the iviumSoft driver'''
        if not Core.is_driver_open():
            return
        Core.IV_close()

    @staticmethod
    def get_max_device_number():
        '''Returns the maximum number of devices that can be managed by IviumSoft'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_MaxDevices()

    @staticmethod
    def get_device_status() -> tuple[int, str]:
        '''It returns -1 (no IviumSoft), 0 (not connected), 1 (available_idle), 2 (available_busy),
            3 (no device available)'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        result_code = Core.IV_getdevicestatus()
        return result_code, _STATUS_LABELS[result_code]

    @staticmethod
    def is_iviumsoft_running() -> bool:
        '''It returns true if the selected instance of IviumSoft is running'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_getdevicestatus() != -1

    @staticmethod
    def get_active_iviumsoft_instances():
        '''Returns a list of active(open) IviumSoft instances.

            The scan changes the selected instance while it runs, so it holds
            the driver lock and restores the previous selection afterwards.'''
        PyviumVerifiers.verify_driver_is_open()
        active_instances = []
        with Core.get_lock():
            previous_instance = Core.get_selected_instance()
            try:
                for instance_number in range(1, 33):
                    Core.IV_selectdevice(instance_number)

                    if Core.IV_getdevicestatus() != -1:
                        active_instances.append(instance_number)
            finally:
                Core.IV_selectdevice(previous_instance)
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

            This is a bare selection: to drive several channels safely from
            several threads, use on_channel / Pyvium.device(n).channel(m), which
            hold the driver lock across the selection and the commands that
            follow it.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        # IV_SelectChannel's return is not routed through verify_result_code: it
        # is unconfirmed whether it follows the setter-code convention or returns
        # the channel number. Left as-is pending hardware verification.
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
            Pyvium.device(n).channel(m), which does both):

                with Pyvium.on_instance(2):
                    with Pyvium.on_channel(3):
                        ...

            The lock serializes this process's threads only. It cannot stop a
            manual channel change in the IviumSoft UI (a separate process), so
            the restored channel is the last value we selected, not the live UI
            state. For robust connection targeting that does not depend on the
            active channel, prefer select_serial_number / connect_device_to_channel.'''
        PyviumVerifiers.verify_driver_is_open()
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
            that have a device behind them; it is empty otherwise.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
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
                        status_label=_STATUS_LABELS[status_code],
                    ))
            finally:
                Core.IV_SelectChannel(previous_channel)
        return statuses

    @staticmethod
    def connect_device_to_channel(serial_number: str, channel: int) -> None:
        '''Connects a specific device (by serial number) to a specific channel.

            Selects the channel, disconnects any idle device already on it,
            then selects the requested device and connects it. The whole
            sequence runs under the driver lock so no other thread can change
            the selection mid-way.

            Unlike on_channel, this leaves the target channel active on return:
            connecting is a deliberate state change toward that channel, so
            restoring a previous channel would only flip the focused tab away
            (the connection itself persists regardless of the active tab).

            Raises DeviceNotConnectedToIviumSoftError if the serial number is
            not in the available device list.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        with Core.get_lock():
            Core.IV_SelectChannel(channel)
            if Core.IV_getdevicestatus() == 1:  # idle, a device is connected
                GenericFunctions.disconnect_device()
            GenericFunctions.select_serial_number(serial_number)
            GenericFunctions.connect_device()
