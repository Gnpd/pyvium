'''Instance-scoped and channel-scoped proxies over the Pyvium API.'''
import functools


class PyviumInstance:
    '''Handle bound to one IviumSoft instance.

        An "instance" is one running IviumSoft window/process, selected through
        IV_selectdevice. Despite that DLL name, it selects an IviumSoft instance,
        not a hardware device (see docs/terminology.md); the device methods on
        this handle act on whatever instrument is connected inside the instance.

        Exposes the full Pyvium API; every method call runs inside
        Pyvium.on_instance(instance_number), so the right instance is selected
        and the driver lock is held for the duration of the call:

            instance = Pyvium.instance(3)
            instance.connect_device()       # always targets instance 3
            instance.start_method('cv.imf')

        For multichannel (Ivium-n-Soft) instances, instance.channel(m) returns a
        handle that also scopes the channel tab (see PyviumChannel).

        Handles are cheap to create and hold no driver resources; the driver
        itself is still opened/closed globally via Pyvium.open_driver().'''

    def __init__(self, instance_number: int):
        self._instance_number = instance_number

    @property
    def instance_number(self) -> int:
        '''The IviumSoft instance this handle is bound to.'''
        return self._instance_number

    def channel(self, channel_number: int) -> "PyviumChannel":
        '''Returns a handle bound to one channel tab of this instance.

            Defined explicitly (not routed through __getattr__) because it
            returns a handle rather than running a scoped Pyvium call.'''
        return PyviumChannel(self._instance_number, channel_number)

    def __getattr__(self, name: str):
        # Imported lazily: this module is imported by pyvium.pyvium.__init__,
        # so a top-level import of Pyvium would be circular.
        from . import Pyvium  # pylint: disable=import-outside-toplevel

        attribute = getattr(Pyvium, name)
        if not callable(attribute):
            return attribute

        @functools.wraps(attribute)
        def scoped(*args, **kwargs):
            with Pyvium.on_instance(self._instance_number):
                return attribute(*args, **kwargs)

        return scoped

    def __dir__(self):
        from . import Pyvium  # pylint: disable=import-outside-toplevel
        return sorted(set(super().__dir__()) | set(dir(Pyvium)))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(instance_number={self._instance_number})"


class PyviumChannel:
    '''Handle bound to one channel tab of one IviumSoft instance.

        "Channel" here is the Multichannel-control tab (IV_SelectChannel,
        Ivium-n-Soft), not a WE32 channel, a multiplexer channel, or necessarily
        the physical channel number of the hardware (the tab number need not
        match the instrument's physical channel). See docs/terminology.md.

        Exposes the full Pyvium API; every method call runs inside both
        Pyvium.on_instance(instance_number) and Pyvium.on_channel(channel_number),
        so the right instance and channel are selected and the driver lock is
        held for the duration of the call:

            channel = Pyvium.instance(1).channel(3)
            channel.connect_device()      # always targets instance 1, channel 3
            channel.start_method('cv.imf')

        Both selections are asserted on every call, so the handle is correct
        even if the instance or channel was changed elsewhere between calls.'''

    def __init__(self, instance_number: int, channel_number: int):
        self._instance_number = instance_number
        self._channel_number = channel_number

    @property
    def instance_number(self) -> int:
        '''The IviumSoft instance this handle is bound to.'''
        return self._instance_number

    @property
    def channel_number(self) -> int:
        '''The channel this handle is bound to.'''
        return self._channel_number

    def __getattr__(self, name: str):
        from . import Pyvium  # pylint: disable=import-outside-toplevel

        attribute = getattr(Pyvium, name)
        if not callable(attribute):
            return attribute

        @functools.wraps(attribute)
        def scoped(*args, **kwargs):
            with Pyvium.on_instance(self._instance_number):
                with Pyvium.on_channel(self._channel_number):
                    return attribute(*args, **kwargs)

        return scoped

    def __dir__(self):
        from . import Pyvium  # pylint: disable=import-outside-toplevel
        return sorted(set(super().__dir__()) | set(dir(Pyvium)))

    def __repr__(self) -> str:
        return (f"{type(self).__name__}(instance_number={self._instance_number}, "
                f"channel_number={self._channel_number})")
