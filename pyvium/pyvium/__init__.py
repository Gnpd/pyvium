from .batch_mode_functions import BatchModeFunctions
from .device import PyviumDevice
from .direct_mode_functions import DirectModeFunctions
from .generic_functions import GenericFunctions
from .method_mode_functions import MethodModeFunctions


class Pyvium(BatchModeFunctions, DirectModeFunctions, GenericFunctions, MethodModeFunctions):
    @staticmethod
    def device(instance_number: int) -> PyviumDevice:
        '''Returns a handle bound to one IviumSoft instance.

            Every method called on the handle runs atomically on that instance
            (see Pyvium.on_instance), making it safe to drive several
            instances from several threads.'''
        return PyviumDevice(instance_number)
