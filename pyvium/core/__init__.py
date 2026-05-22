from .batch_mode_functions import BatchModeFunctions
from .direct_mode_functions import DirectModeFunctions
from .generic_functions import GenericFunctions
from .method_mode_functions import MethodModeFunctions
from .we32_functions import We32Functions


class Core(BatchModeFunctions, DirectModeFunctions, GenericFunctions, MethodModeFunctions, We32Functions):
    pass
