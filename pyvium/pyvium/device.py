'''Instance-scoped proxy over the Pyvium API.'''
import functools


class PyviumDevice:
    '''Handle bound to one IviumSoft instance.

        Exposes the full Pyvium API; every method call runs inside
        Pyvium.on_instance(instance_number), so the right instance is selected
        and the driver lock is held for the duration of the call:

            device = Pyvium.device(3)
            device.connect_device()       # always targets instance 3
            device.start_method('cv.imf')

        Handles are cheap to create and hold no driver resources; the driver
        itself is still opened/closed globally via Pyvium.open_driver().'''

    def __init__(self, instance_number: int):
        self._instance_number = instance_number

    @property
    def instance_number(self) -> int:
        '''The IviumSoft instance this handle is bound to.'''
        return self._instance_number

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
