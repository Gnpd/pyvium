from .constants import LONG_PTR
from .core_base import CoreBase, ffi

ffi.cdef("""
    long __stdcall IV_StatusParSet(long *value);
    long __stdcall IV_StatusParGet(long *value);
""")


class BatchModeFunctions(CoreBase):
    @staticmethod
    def IV_StatusParSet(value: int) -> tuple[int, int]:
        '''Sets the global Statuspar variable, can be used for synchronisation.'''
        value_ptr = ffi.new(LONG_PTR, value)
        result_code = CoreBase.get_lib().IV_StatusParSet(value_ptr)
        return result_code, value_ptr[0]

    @staticmethod
    def IV_StatusParGet() -> tuple[int, int]:
        '''Reads the global Statuspar variable, can be used for synchronisation.'''
        value_ptr = ffi.new(LONG_PTR)
        result_code = CoreBase.get_lib().IV_StatusParGet(value_ptr)
        return result_code, value_ptr[0]
