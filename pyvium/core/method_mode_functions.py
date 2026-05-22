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
            return (time/I,E/0), Impedance methods return (Z1,Z2,freq) etc.'''
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
            This function will allow reading data from non-selected (previous) scans.'''
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
