import warnings

from ..core import Core
from ..errors import (DeviceNotConnectedToIviumSoftError,
                      IviumSoftNotRunningError)
from ..pyvium_verifiers import PyviumVerifiers


class GenericFunctions():
    @staticmethod
    def open_driver():
        '''Open the driver to manipulate the Ivium software'''
        if Core.is_driver_open():
            warnings.warn(
                "open_driver() called but driver is already open — closing and reopening",
                UserWarning,
                stacklevel=2,
            )
            Core.IV_close()
        Core.IV_open()
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
        status_labels = {
            '-1': 'no IviumSoft',
            '0': 'not connected',
            '1': 'available_idle',
            '2': 'available_busy',
            '3': 'no device available'
        }
        result_code = Core.IV_getdevicestatus()
        return result_code, status_labels[str(result_code)]

    @staticmethod
    def is_iviumsoft_running() -> bool:
        '''It returns true if the selected instance of IviumSoft is running'''
        PyviumVerifiers.verify_driver_is_open()
        return Core.IV_getdevicestatus() != -1

    @staticmethod
    def get_active_iviumsoft_instances():
        '''Returns a list of active(open) IviumSoft instances'''
        PyviumVerifiers.verify_driver_is_open()
        active_instances = []
        first_active_instance_number = 0
        for instance_number in range(1, 33):
            Core.IV_selectdevice(instance_number)

            if Core.IV_getdevicestatus() != -1:
                active_instances.append(instance_number)

                if first_active_instance_number == 0:
                    first_active_instance_number = instance_number

        if first_active_instance_number == 0:
            first_active_instance_number = 1

        Core.IV_selectdevice(first_active_instance_number)
        return active_instances

    @staticmethod
    def select_iviumsoft_instance(iviumsoft_instance_number: int):
        '''It allows to select one instance of the currently running IviumSoft instances'''

        PyviumVerifiers.verify_driver_is_open()
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
                "connect_device() called but device is already connected — skipping",
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
            controlled.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        Core.IV_SelectChannel(channel_number)

    @staticmethod
    def select_serial_number(serial_number: str) -> int | None:
        '''Selects a device by serial number, making it ready to connect.
            Returns the position index in the dropdown list (0-based), or None if
            the device is already connected and no reselection was needed.
            Warns if the requested device is already connected — skips reselection.
            Raises DeviceNotConnectedToIviumSoftError if the serial number is not
            found in the device list, or if a different device is already connected.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        if Core.IV_getdevicestatus() in (1, 2):
            _, connected_serial = Core.IV_readSN()
            if connected_serial == serial_number:
                warnings.warn(
                    f"select_serial_number('{serial_number}') called but this device "
                    "is already connected — skipping.",
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
