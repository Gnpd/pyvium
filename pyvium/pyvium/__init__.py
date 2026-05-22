from .batch_mode_functions import BatchModeFunctions
from .direct_mode_functions import DirectModeFunctions
from .generic_functions import GenericFunctions
from .method_mode_functions import MethodModeFunctions


class Pyvium(BatchModeFunctions, DirectModeFunctions, GenericFunctions, MethodModeFunctions):
    pass
