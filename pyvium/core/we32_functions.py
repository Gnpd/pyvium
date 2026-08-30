from .constants import DOUBLE_PTR, LONG_PTR
from .core_base import CoreBase, ffi

ffi.cdef("""
    long __stdcall IV_we32setchannel(long *index);
    long __stdcall IV_we32setoffset(long *index, double *value);
    long __stdcall IV_we32setoffsets(long *nval, double *values);
    long __stdcall IV_we32getoffsets(long *nval, double *values);
    long __stdcall IV_we32readcurrents(double *values);
    long __stdcall IV_selectdevice_we32setchannel(long *devnr, long *index);
    long __stdcall IV_selectdevice_we32setoffset(long *devnr, long *index, double *value);
    long __stdcall IV_selectdevice_we32setoffsets(long *devnr, long *nval, double *values);
    long __stdcall IV_selectdevice_we32getoffsets(long *devnr, long *nval, double *values);
    long __stdcall IV_selectdevice_we32readcurrents(long *devnr, double *values);
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
    def IV_we32getoffsets(number_of_channels: int) -> tuple[int, list]:
        '''Returns actual WE32 offset values (Nchan, values),
            with Nchan the number of channels (1..32)'''
        number_of_channels_ptr = ffi.new(LONG_PTR, number_of_channels)
        values_arr = ffi.new(f"double[{number_of_channels}]")
        result_code = CoreBase.get_lib().IV_we32getoffsets(
            number_of_channels_ptr, values_arr)
        return result_code, list(values_arr)

    @staticmethod
    def IV_we32readcurrents() -> tuple[int, list]:
        '''Returns array with 32 WE32 current values measured simultaneously.'''
        current_values_arr = ffi.new("double[32]")
        result_code = CoreBase.get_lib().IV_we32readcurrents(current_values_arr)
        return result_code, list(current_values_arr)

    # --- selectdevice variants (scoped to an IviumSoft instance) ----------
    # One-call forms taking a leading IviumSoft instance number. Like all
    # selectdevice variants these are IV_selectdevice + the base call fused:
    # they leave the global selection parked on that instance and do NOT
    # restore it (see IV_selectdevice_getdevicestatus).

    @staticmethod
    def IV_selectdevice_we32setchannel(instance: int, channel_index: int) -> int:
        '''Scoped IV_we32setchannel for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        channel_index_ptr = ffi.new(LONG_PTR, channel_index)
        return CoreBase.get_lib().IV_selectdevice_we32setchannel(
            instance_ptr, channel_index_ptr)

    @staticmethod
    def IV_selectdevice_we32setoffset(instance: int, channel_index: int, value: float) -> int:
        '''Scoped IV_we32setoffset for the given IviumSoft instance.
            value -2 to +2V; use chan=0 to apply the same offset to all channels.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        channel_index_ptr = ffi.new(LONG_PTR, channel_index)
        value_ptr = ffi.new(DOUBLE_PTR, value)
        return CoreBase.get_lib().IV_selectdevice_we32setoffset(
            instance_ptr, channel_index_ptr, value_ptr)

    @staticmethod
    def IV_selectdevice_we32setoffsets(instance: int, number_of_channels: int, values: list) -> int:
        '''Scoped IV_we32setoffsets for the given IviumSoft instance.
            number_of_channels 1..32.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        number_of_channels_ptr = ffi.new(LONG_PTR, number_of_channels)
        values_arr = ffi.new(f"double[{len(values)}]", values)
        return CoreBase.get_lib().IV_selectdevice_we32setoffsets(
            instance_ptr, number_of_channels_ptr, values_arr)

    @staticmethod
    def IV_selectdevice_we32getoffsets(instance: int, number_of_channels: int) -> tuple[int, list]:
        '''Scoped IV_we32getoffsets for the given IviumSoft instance.
            number_of_channels 1..32.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        number_of_channels_ptr = ffi.new(LONG_PTR, number_of_channels)
        values_arr = ffi.new(f"double[{number_of_channels}]")
        result_code = CoreBase.get_lib().IV_selectdevice_we32getoffsets(
            instance_ptr, number_of_channels_ptr, values_arr)
        return result_code, list(values_arr)

    @staticmethod
    def IV_selectdevice_we32readcurrents(instance: int) -> tuple[int, list]:
        '''Scoped IV_we32readcurrents for the given IviumSoft instance.
            Returns 32 WE32 current values measured simultaneously.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        current_values_arr = ffi.new("double[32]")
        result_code = CoreBase.get_lib().IV_selectdevice_we32readcurrents(
            instance_ptr, current_values_arr)
        return result_code, list(current_values_arr)
