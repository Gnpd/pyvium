from .constants import CHAR_ARRAY, DOUBLE_PTR, LONG_PTR, UTF_ENCODING
from .core_base import CoreBase, ffi

ffi.cdef("""
    long __stdcall IV_readmethod(char *fname);
    long __stdcall IV_savemethod(char *fname);
    long __stdcall IV_startmethod(char *fname);
    long __stdcall IV_abort();
    long __stdcall IV_savedata(char *fname);
    long __stdcall IV_savedataset(char *fname);
    long __stdcall IV_setmethodparameter(char *parname, char *parvalue);
    long __stdcall IV_Ndatapoints(long *value);
    long __stdcall IV_getdata(long *pointnr, double *x, double *y, double *z);
    long __stdcall IV_getdatafromline(long *pointnr, long *scannr, double *x, double *y, double *z);
    long __stdcall IV_UpdateTemperature(double *value);
    long __stdcall IV_getDbFileName(char *fname);
    long __stdcall IV_selectdevice_readmethod(long *devnr, char *fname);
    long __stdcall IV_selectdevice_savemethod(long *devnr, char *fname);
    long __stdcall IV_selectdevice_startmethod(long *devnr, char *fname);
    long __stdcall IV_selectdevice_abort(long *devnr);
    long __stdcall IV_selectdevice_savedata(long *devnr, char *fname);
    long __stdcall IV_selectdevice_savedataset(long *devnr, char *fname);
    long __stdcall IV_selectdevice_setmethodparameter(long *devnr, char *parname, char *parvalue);
    long __stdcall IV_selectdevice_Ndatapoints(long *devnr, long *value);
    long __stdcall IV_selectdevice_getdata(long *devnr, long *pointnr, double *x, double *y, double *z);
""")


class MethodModeFunctions(CoreBase):
    @staticmethod
    def IV_readmethod(method_file_path: str) -> tuple[int, str]:
        '''Loads method procedure previously saved to a file.
            method_file_path represents the full path to the file.'''
        method_file_path_ptr = ffi.new(
            CHAR_ARRAY, method_file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_readmethod(method_file_path_ptr)
        return result_code, ffi.string(method_file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_savemethod(method_file_path: str) -> tuple[int, str]:
        '''Saves currently loaded method procedure to a file.
            method_file_path represents the full path to the new file.'''
        method_file_path_ptr = ffi.new(
            CHAR_ARRAY, method_file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_savemethod(method_file_path_ptr)
        return result_code, ffi.string(method_file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_startmethod(method_file_path='') -> tuple[int, str]:
        '''Starts a method procedure.
            If method_file_path is an empty string then the presently loaded procedure is started.
            If the full path to a previously saved method is provided
            then the procedure is loaded from the file and started.'''
        method_file_path_ptr = ffi.new(
            CHAR_ARRAY, method_file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_startmethod(method_file_path_ptr)
        return result_code, ffi.string(method_file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_abort() -> int:
        '''Aborts the ongoing method procedure'''
        return CoreBase.get_lib().IV_abort()

    @staticmethod
    def IV_savedata(method_data_file_path: str) -> tuple[int, str]:
        '''Saves the results of the last method execution into a file.
            method_file_path represents the full path to the new file.'''
        method_data_file_path_ptr = ffi.new(
            CHAR_ARRAY, method_data_file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_savedata(method_data_file_path_ptr)
        return result_code, ffi.string(method_data_file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_setmethodparameter(parameter_name: str, parameter_value: str) -> int:
        '''Allows updating the parameter values for the currently loaded method procedrue.
            It only works for text based parameters and dropdowns (multiple option selectors).'''
        parameter_name_ptr = ffi.new(
            CHAR_ARRAY, parameter_name.encode(UTF_ENCODING))
        parameter_value_ptr = ffi.new(
            CHAR_ARRAY, parameter_value.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_setmethodparameter(
            parameter_name_ptr, parameter_value_ptr)
        return result_code

    @staticmethod
    def IV_Ndatapoints() -> tuple[int, int]:
        '''Returns actual available number of datapoints: indicates the progress during a run'''
        data_point_ptr = ffi.new(LONG_PTR)
        result_code = CoreBase.get_lib().IV_Ndatapoints(data_point_ptr)
        return result_code, data_point_ptr[0]

    @staticmethod
    def IV_getdata(data_point_index: int) -> tuple[int, float, float, float]:
        '''Get the data from a datapoint with index int, returns 3 values that depend on
            the used technique. For example LSV/CV methods return (E/I/0) Transient methods
            return (time/I,E/0), Impedance methods return (Z1,Z2,freq) etc.

            data_point_index is 1-based. Index 0 is a DLL sentinel that returns result
            code 0 and a (1e-12, 1e-12, 1e-12) placeholder even with no data recorded.
            An index past the end returns result code 65535 (0xFFFF) and leaves the
            output buffers untouched, so the returned values are whatever the previous
            read left in the reused allocation; check the result code before using them.'''
        selected_data_point_index_ptr = ffi.new(LONG_PTR, data_point_index)
        measured_value1_ptr = ffi.new(DOUBLE_PTR)
        measured_value2_ptr = ffi.new(DOUBLE_PTR)
        measured_value3_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getdata(
            selected_data_point_index_ptr, measured_value1_ptr, measured_value2_ptr, measured_value3_ptr)
        return result_code, measured_value1_ptr[0], measured_value2_ptr[0], measured_value3_ptr[0]

    @staticmethod
    def IV_getDbFileName() -> tuple[int, str]:
        '''Returns the path and filename of the last created SQL database file.'''
        db_path_ptr = ffi.new(CHAR_ARRAY, 260)
        result_code = CoreBase.get_lib().IV_getDbFileName(db_path_ptr)
        return result_code, ffi.string(db_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_savedataset(file_path: str) -> tuple[int, str]:
        '''Saves all result data in the measurement list to disk at the given path.'''
        file_path_ptr = ffi.new(CHAR_ARRAY, file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_savedataset(file_path_ptr)
        return result_code, ffi.string(file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_UpdateTemperature(temperature: float) -> tuple[int, float]:
        '''Updates the shared temperature for all channels (beta).'''
        temperature_ptr = ffi.new(DOUBLE_PTR, temperature)
        result_code = CoreBase.get_lib().IV_UpdateTemperature(temperature_ptr)
        return result_code, temperature_ptr[0]

    @staticmethod
    def IV_getdatafromline(data_point_index: int, scan_index: int) -> tuple[int, float, float, float]:
        '''Same as get_data_point, but with the additional scan_index parameter.
            This function will allow reading data from non-selected (previous) scans.

            WARNING: do not pass scan_index below 1. Both indices are 1-based, and on
            IviumSoft 4.1247 a scan_index of 0 returns result code 0 and then terminates
            the IviumSoft process, while a scan_index of -1 never returns and leaves
            IviumSoft allocating memory without bound. Use Pyvium.get_data_point_from_scan,
            which refuses those values before the call reaches the DLL.

            As with IV_getdata, an out-of-range index returns result code 65535 (0xFFFF)
            and leaves the output buffers untouched.'''
        selected_data_point_index_ptr = ffi.new(LONG_PTR, data_point_index)
        selected_line_index_ptr = ffi.new(LONG_PTR, scan_index)
        measured_value1_ptr = ffi.new(DOUBLE_PTR)
        measured_value2_ptr = ffi.new(DOUBLE_PTR)
        measured_value3_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getdatafromline(
            selected_data_point_index_ptr,
            selected_line_index_ptr,
            measured_value1_ptr,
            measured_value2_ptr,
            measured_value3_ptr)
        return result_code, measured_value1_ptr[0], measured_value2_ptr[0], measured_value3_ptr[0]

    # --- selectdevice variants (scoped to an IviumSoft instance) ----------
    # One-call forms taking a leading IviumSoft instance number. Like all
    # selectdevice variants these are IV_selectdevice + the base call fused:
    # they leave the global selection parked on that instance and do NOT
    # restore it (see IV_selectdevice_getdevicestatus). The DLL exposes no
    # scoped IV_getdatafromline, so that one has no selectdevice variant.

    @staticmethod
    def IV_selectdevice_readmethod(instance: int, method_file_path: str) -> tuple[int, str]:
        '''Scoped IV_readmethod for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        method_file_path_ptr = ffi.new(
            CHAR_ARRAY, method_file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_selectdevice_readmethod(
            instance_ptr, method_file_path_ptr)
        return result_code, ffi.string(method_file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_selectdevice_savemethod(instance: int, method_file_path: str) -> tuple[int, str]:
        '''Scoped IV_savemethod for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        method_file_path_ptr = ffi.new(
            CHAR_ARRAY, method_file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_selectdevice_savemethod(
            instance_ptr, method_file_path_ptr)
        return result_code, ffi.string(method_file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_selectdevice_startmethod(instance: int, method_file_path: str = '') -> tuple[int, str]:
        '''Scoped IV_startmethod for the given IviumSoft instance.
            An empty path starts the presently loaded procedure.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        method_file_path_ptr = ffi.new(
            CHAR_ARRAY, method_file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_selectdevice_startmethod(
            instance_ptr, method_file_path_ptr)
        return result_code, ffi.string(method_file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_selectdevice_abort(instance: int) -> int:
        '''Scoped IV_abort for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        return CoreBase.get_lib().IV_selectdevice_abort(instance_ptr)

    @staticmethod
    def IV_selectdevice_savedata(instance: int, method_data_file_path: str) -> tuple[int, str]:
        '''Scoped IV_savedata for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        method_data_file_path_ptr = ffi.new(
            CHAR_ARRAY, method_data_file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_selectdevice_savedata(
            instance_ptr, method_data_file_path_ptr)
        return result_code, ffi.string(method_data_file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_selectdevice_savedataset(instance: int, file_path: str) -> tuple[int, str]:
        '''Scoped IV_savedataset for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        file_path_ptr = ffi.new(CHAR_ARRAY, file_path.encode(UTF_ENCODING))
        result_code = CoreBase.get_lib().IV_selectdevice_savedataset(
            instance_ptr, file_path_ptr)
        return result_code, ffi.string(file_path_ptr).decode(UTF_ENCODING)

    @staticmethod
    def IV_selectdevice_setmethodparameter(
        instance: int, parameter_name: str, parameter_value: str
    ) -> int:
        '''Scoped IV_setmethodparameter for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        parameter_name_ptr = ffi.new(
            CHAR_ARRAY, parameter_name.encode(UTF_ENCODING))
        parameter_value_ptr = ffi.new(
            CHAR_ARRAY, parameter_value.encode(UTF_ENCODING))
        return CoreBase.get_lib().IV_selectdevice_setmethodparameter(
            instance_ptr, parameter_name_ptr, parameter_value_ptr)

    @staticmethod
    def IV_selectdevice_Ndatapoints(instance: int) -> tuple[int, int]:
        '''Scoped IV_Ndatapoints for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        data_point_ptr = ffi.new(LONG_PTR)
        result_code = CoreBase.get_lib().IV_selectdevice_Ndatapoints(
            instance_ptr, data_point_ptr)
        return result_code, data_point_ptr[0]

    @staticmethod
    def IV_selectdevice_getdata(instance: int, data_point_index: int) -> tuple[int, float, float, float]:
        '''Scoped IV_getdata for the given IviumSoft instance.'''
        instance_ptr = ffi.new(LONG_PTR, instance)
        selected_data_point_index_ptr = ffi.new(LONG_PTR, data_point_index)
        measured_value1_ptr = ffi.new(DOUBLE_PTR)
        measured_value2_ptr = ffi.new(DOUBLE_PTR)
        measured_value3_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_selectdevice_getdata(
            instance_ptr,
            selected_data_point_index_ptr,
            measured_value1_ptr,
            measured_value2_ptr,
            measured_value3_ptr)
        return result_code, measured_value1_ptr[0], measured_value2_ptr[0], measured_value3_ptr[0]
