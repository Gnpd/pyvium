'''Class with methods to validated the current status of the IviumSoft environment'''
from .core import Core
from .errors import DriverNotOpenError, \
    IllegalCommandError, \
    InvalidStateError, \
    IviumSoftNotRunningError, \
    DeviceNotConnectedToIviumSoftError, \
    DeviceBusyError, \
    NoDeviceDetectedError, \
    CellOffError


class PyviumVerifiers:
    '''Encapsulates methods to validated the current status of the IviumSoft environment'''

    @staticmethod
    def verify_driver_is_open():
        '''Raise exception if the driver is not open'''
        if not Core.is_driver_open():
            raise DriverNotOpenError

    @staticmethod
    def verify_iviumsoft_is_running():
        '''Raise exception if IviumSoft is not running'''
        device_status = Core.IV_getdevicestatus()

        if device_status == -1:
            raise IviumSoftNotRunningError

    @staticmethod
    def verify_device_is_connected_to_iviumsoft():
        '''Raise exception if a device is not connected through the IviumSoft app'''
        device_status = Core.IV_getdevicestatus()
        if device_status < 1 or device_status == 3:
            raise DeviceNotConnectedToIviumSoftError

    @staticmethod
    def verify_device_is_connected_to_computer():
        '''Raise exception if no device is connected to your computer through usb'''
        device_status = Core.IV_getdevicestatus()

        if device_status == 3:
            raise NoDeviceDetectedError

    @staticmethod
    def verify_device_is_available():
        '''Raise exception if the connected device/s are not available at the moment'''
        device_status = Core.IV_getdevicestatus()
        if device_status == 2:
            raise DeviceBusyError

    @staticmethod
    def verify_cell_is_on():
        '''Raise exception if the cell is off'''
        _, device_status = Core.IV_getcellstatus()
        if not device_status:
            raise CellOffError

    @staticmethod
    def verify_result_code(result_code: int, context: str = ""):
        '''Raise a typed exception when a DLL setter returns a non-zero result code.

        DLL result code semantics for setter functions:
          0  = success (no exception raised)
         -1  = no device: IviumSoft lost contact with the hardware
          1  = illegal command: the command is not valid for this device
          2  = argument out of range: a parameter value was rejected by the firmware
          3  = invalid state: the command is valid but cannot run in the device's
               current operating state (e.g. method already running)
        '''
        suffix = f": {context}" if context else ""
        if result_code == -1:
            raise NoDeviceDetectedError(
                f"No device available during command{suffix}"
            )
        if result_code == 1:
            raise IllegalCommandError(
                f"The command is not available in the current device state{suffix}"
            )
        if result_code == 2:
            raise ValueError(
                f"Argument out of range{suffix}"
            )
        if result_code == 3:
            raise InvalidStateError(
                f"The device is in an invalid state for this command{suffix}"
            )
