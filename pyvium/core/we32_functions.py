from .constants import DOUBLE_PTR, LONG_PTR
from .core_base import CoreBase, ffi

ffi.cdef("""
    long __stdcall IV_we32setchannel(long *index);
    long __stdcall IV_we32setoffset(long *index, double *value);
    long __stdcall IV_we32setoffsets(long *nval, double *values);
    long __stdcall IV_we32getoffsets(long *nval, double *values);
    long __stdcall IV_we32readcurrents(double *values);
""")


class We32Functions(CoreBase):
    @staticmethod
    def IV_we32setchannel(channel_index: int) -> int:
        '''Select active WE32 channel (chan)'''
        channel_index_ptr = ffi.new(LONG_PTR, channel_index)
        result_code = CoreBase.get_lib().IV_we32setchannel(channel_index_ptr)
        return result_code

    @staticmethod
    def IV_we32setoffset(channel_index: int, value: float) -> int:
        '''Set WE32 offset (chan,value), value -2 to +2V.
            Use chan=0 to apply the same offset to all channels.'''
        channel_index_ptr = ffi.new(LONG_PTR, channel_index)
        value_ptr = ffi.new(DOUBLE_PTR, value)
        result_code = CoreBase.get_lib().IV_we32setoffset(channel_index_ptr, value_ptr)
        return result_code

    @staticmethod
    def IV_we32setoffsets(number_of_channels: int, values: list) -> int:
        '''Set WE32 offset values for multiple channels (Nchan, values),
            with Nchan the number of channels (1..32)'''
        number_of_channels_ptr = ffi.new(LONG_PTR, number_of_channels)
        values_arr = ffi.new(f"double[{len(values)}]", values)
        result_code = CoreBase.get_lib().IV_we32setoffsets(
            number_of_channels_ptr, values_arr)
        return result_code

    @staticmethod
    def IV_we32getoffsets(number_of_channels: int) -> tuple[int, float]:
        '''REVISE! Returns actual WE32 offset values (Nchan,values),
            with Nchan the number of channels (1..32)'''
        number_of_channels_index_ptr = ffi.new(LONG_PTR, number_of_channels)
        values_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_we32getoffsets(
            number_of_channels_index_ptr, values_ptr)
        return result_code, values_ptr[0]

    @staticmethod
    def IV_we32readcurrents() -> tuple[int, float]:
        '''REVISE! Returns array with 32 WE32 current values,
            that are measured simultaneously'''
        current_values_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_we32readcurrents(current_values_ptr)
        return result_code, current_values_ptr[0]
