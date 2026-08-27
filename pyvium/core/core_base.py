'''The module provides base class for shared state and methods related to Ivium driver.'''
import threading
from typing import Any

from cffi import FFI

from ..util import get_ivium_dll_path

ffi = FFI()

# The driver resets its selected instance to 1 on IV_open; channel tabs likewise
# start at 1. Both selection shadows are initialised and reset to these values.
DEFAULT_INSTANCE = 1
DEFAULT_CHANNEL = 1


class CoreBase:
    """
    Base class for providing shared state and methods related to Ivium driver.
    """
    __is_driver_open = False
    __lib = ffi.dlopen(get_ivium_dll_path())
    # The DLL keeps the selected instance as global state and has no getter,
    # so the last value passed to IV_selectdevice is tracked here. The driver
    # defaults to instance 1 after IV_open, so IV_open/IV_close reset this
    # shadow (see reset_selection_shadows); otherwise a value left over from
    # before a close would outlive the selection it describes.
    __selected_instance = DEFAULT_INSTANCE
    # The active multichannel channel is likewise global with no getter, so the
    # last value passed to IV_SelectChannel is tracked here. This is a restore
    # hint, not a source of truth: it reflects what we last selected, not the
    # live IviumSoft UI (a manual tab change is not observable). Channels default
    # to 1 and are reset alongside the instance. See get_selected_channel for
    # the caveats.
    __selected_channel = DEFAULT_CHANNEL
    # Re-entrant so nested locked sections (high-level methods calling other
    # high-level methods on the same thread) do not deadlock.
    __lock = threading.RLock()
    # Cache of the last full active-instance scan (each scan costs 32 DLL calls).
    # None means "unknown, must rescan". Invalidated by open/close_driver and by
    # the instance manager when it launches/closes/adopts an instance. It cannot
    # see instances that appear or close outside this process, so a periodic full
    # rescan is still needed; this only spares the hot status-poll path.
    # Every mutation is serialised on the driver lock, and the scan holds that
    # lock across both the probe and the write, so a scan already in flight can
    # never write its stale list over an invalidation issued meanwhile.
    __active_instances_cache: list | None = None

    @staticmethod
    def get_active_instances_cache() -> list | None:
        """
        Returns the cached active-instance list, or None if it must be rescanned.

        Deliberately not locked: this is the hot path the cache exists to make
        cheap, and reading a list that is about to be invalidated is ordinary
        cache staleness, which the scan already documents.
        """
        return CoreBase.__active_instances_cache

    @staticmethod
    def set_active_instances_cache(instances) -> None:
        """
        Stores the result of a full active-instance scan.

        Serialised on the driver lock. The scan already holds it across the
        probe and this write (the lock is re-entrant), so the pair cannot be
        split by an invalidation.

        :param instances: Iterable of active instance numbers.
        """
        with CoreBase.__lock:
            CoreBase.__active_instances_cache = list(instances)

    @staticmethod
    def invalidate_active_instances_cache() -> None:
        """
        Drops the cached active-instance list so the next read does a full scan.

        Takes the driver lock, so it can block behind an in-flight scan. That
        wait is the point: an invalidation must land after the scan it overlaps,
        never be overwritten by it.
        """
        with CoreBase.__lock:
            CoreBase.__active_instances_cache = None

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
    def get_selected_channel() -> int:
        """
        Returns the multichannel channel last selected via IV_SelectChannel.

        This is a best-effort shadow of global DLL state that has no getter. It
        is the last value this process selected; it does not track manual
        channel changes made in the IviumSoft UI (a separate process the lock
        cannot serialize). Scoped helpers use it as a restore target only, and
        always re-select the channel explicitly before acting on it.
        """
        return CoreBase.__selected_channel

    @staticmethod
    def set_selected_channel(channel_number: int) -> None:
        """
        Records the channel number passed to IV_SelectChannel.

        :param channel_number: Channel number as an integer.
        """
        CoreBase.__selected_channel = channel_number

    @staticmethod
    def reset_selection_shadows() -> None:
        """
        Resets both selection shadows to the values the driver starts from.

        Called by IV_open/IV_close: the DLL resets its selected instance to 1
        on IV_open, so a shadow surviving from before the close would make the
        next scoped block restore a selection the driver no longer has, moving
        the caller's working instance without any command saying so.
        """
        CoreBase.__selected_instance = DEFAULT_INSTANCE
        CoreBase.__selected_channel = DEFAULT_CHANNEL

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
