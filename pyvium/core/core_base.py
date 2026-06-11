'''The module provides base class for shared state and methods related to Ivium driver.'''
import threading
from typing import Any

from cffi import FFI

from ..util import get_ivium_dll_path

ffi = FFI()


class CoreBase:
    """
    Base class for providing shared state and methods related to Ivium driver.
    """
    __is_driver_open = False
    __lib = ffi.dlopen(get_ivium_dll_path())
    # The DLL keeps the selected instance as global state and has no getter,
    # so the last value passed to IV_selectdevice is tracked here. The driver
    # defaults to instance 1 after IV_open.
    __selected_instance = 1
    # Re-entrant so nested locked sections (high-level methods calling other
    # high-level methods on the same thread) do not deadlock.
    __lock = threading.RLock()

    @staticmethod
    def get_lock() -> threading.RLock:
        """
        Returns the process-wide lock that serializes DLL access.

        Hold this lock for any sequence of calls that must not be interleaved
        with another thread, e.g. select instance + run command.
        """
        return CoreBase.__lock

    @staticmethod
    def get_selected_instance() -> int:
        """
        Returns the IviumSoft instance number last selected via IV_selectdevice.
        """
        return CoreBase.__selected_instance

    @staticmethod
    def set_selected_instance(instance_number: int) -> None:
        """
        Records the IviumSoft instance number passed to IV_selectdevice.

        :param instance_number: Instance number as an integer.
        """
        CoreBase.__selected_instance = instance_number

    @staticmethod
    def get_lib() -> Any:
        """
        Returns the library instance.
        """
        return CoreBase.__lib

    @staticmethod
    def is_driver_open() -> bool:
        """
        Returns the driver open status.
        """
        return CoreBase.__is_driver_open

    @staticmethod
    def set_driver_open(status: bool) -> None:
        """
        Sets the driver open status.

        :param status: Driver open status as a boolean.
        """
        CoreBase.__is_driver_open = status
