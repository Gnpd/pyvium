from ..core import Core
from ..pyvium_verifiers import PyviumVerifiers


class BatchModeFunctions():
    @staticmethod
    def set_status_par(value: int):
        '''Sets the global Statuspar variable, can be used for synchronisation.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        Core.IV_StatusParSet(value)

    @staticmethod
    def get_status_par() -> int:
        '''Reads the global Statuspar variable, can be used for synchronisation.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        _, value = Core.IV_StatusParGet()
        return value
