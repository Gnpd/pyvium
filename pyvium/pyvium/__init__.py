from .batch_mode_functions import BatchModeFunctions
from .direct_mode_functions import DirectModeFunctions
from .generic_functions import (ChannelStatus, DEVICE_STATUS_LABELS,
                                GenericFunctions, device_status_label)
from .instance import PyviumChannel, PyviumInstance
from .method_mode_functions import MethodModeFunctions


class Pyvium(BatchModeFunctions, DirectModeFunctions, GenericFunctions, MethodModeFunctions):
    @staticmethod
    def instance(instance_number: int) -> PyviumInstance:
        '''Returns a handle bound to one IviumSoft instance.

            Every method called on the handle runs atomically on that instance
            (see Pyvium.on_instance), making it safe to drive several
            instances from several threads.'''
        return PyviumInstance(instance_number)
