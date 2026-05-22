'''Class with methods to validated the current status of the IviumSoft environment'''
from .core import Core
from .errors import DriverNotOpenError, \
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
        '''Raise exception if the is off'''
        _, device_status = Core.IV_getcellstatus()
        if not device_status:
            raise CellOffError
