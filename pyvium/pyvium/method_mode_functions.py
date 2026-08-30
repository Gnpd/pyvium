from ..core import Core
from ..pyvium_verifiers import PyviumVerifiers


class MethodModeFunctions():
    @staticmethod
    def load_method(method_file_path: str):
        '''Loads method procedure previously saved to a file.
            method_file_path represents the full path to the file.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        result_code, _ = Core.IV_readmethod(method_file_path)

        if result_code in (1, 2):
            raise FileNotFoundError(
                f"Method file not found or inaccessible: '{method_file_path}'. "
                "Verify the path is absolute, the file exists, and has a .imf extension."
            )

    @staticmethod
    def save_method(method_file_path: str):
        '''Saves currently loaded method procedure to a file.
            method_file_path represents the full path to the new file.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        result_code, _ = Core.IV_savemethod(method_file_path)
        PyviumVerifiers.verify_result_code(result_code, "save_method")

    @staticmethod
    def start_method(method_file_path=''):
        '''Starts a method procedure.
            If method_file_path is an empty string then the presently loaded procedure is started.
            If the full path to a previously saved method is provided
            then the procedure is loaded from the file and started.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        PyviumVerifiers.verify_device_is_available()

        result_code, _ = Core.IV_startmethod(method_file_path)

        if result_code in (1, 2):
            raise FileNotFoundError(
                f"Method file not found or inaccessible: '{method_file_path}'. "
                "Verify the path is absolute, the file exists, and has a .imf extension."
            )

    @staticmethod
    def abort_method():
        '''Requests an abort of the ongoing method procedure.

            The abort is not instantaneous: the measurement stops at the next
            data point. At slow sampling rates (e.g. 60 s/point in low-frequency
            EIS) the device can stay busy for the full remaining interval. Poll
            get_device_status() and wait for status 1 (idle) before starting a
            new method, otherwise the next start raises DeviceBusyError.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        result_code = Core.IV_abort()
        PyviumVerifiers.verify_result_code(result_code, "abort_method")

    @staticmethod
    def save_data(data_file_path: str):
        '''Saves the results of the last method execution into a file.
            data_file_path represents the full path to the new file.
           IMPORTANT: If the path provided is not valid,
           it will close the selected iviumsoft instance.
        '''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        result_code, _ = Core.IV_savedata(data_file_path)
        PyviumVerifiers.verify_result_code(result_code, "save_data")

    @staticmethod
    def set_method_parameter(parameter_name: str, parameter_value: str):
        '''Allows updating the parameter values for the currently loaded method procedrue.
            It only works for text based parameters and dropdowns (multiple option selectors).'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        result_code = Core.IV_setmethodparameter(parameter_name, parameter_value)
        PyviumVerifiers.verify_result_code(result_code, "set_method_parameter")

    @staticmethod
    def get_available_data_points_number():
        '''Returns actual available number of datapoints: indicates the progress
            during a run.

            The count is also the highest valid index for get_data_point and
            get_data_point_from_scan, both of which are 1-based.

            One value it cannot vouch for: an instance whose IviumSoft was
            terminated rather than closed stays registered with the driver, and
            such a slot answers this call with result code 0 and the count from
            the previous read on a live instance rather than one of its own.
            Nothing in the result code gives that away.
            get_active_iviumsoft_instances() does not report those slots, so
            scoping to an instance it does return avoids the trap.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        result_code, available_data_points_number = Core.IV_Ndatapoints()
        PyviumVerifiers.verify_result_code(
            result_code, "get_available_data_points_number")

        return available_data_points_number

    @staticmethod
    def get_data_point(data_point_index: int):
        '''Get the data from a datapoint with index int, returns 3 values that depend on
            the used technique. For example LSV/CV methods return (E/I/0) Transient methods
            return (time/I,E/0), Impedance methods return (Z1,Z2,freq) etc.

            data_point_index is 1-based: the first recorded point is 1, and the last
            valid index is the value get_available_data_points_number() returns. Index 0
            is a DLL sentinel that reports success and hands back a (1e-12, 1e-12, 1e-12)
            placeholder even when no measurement has run, so it is rejected here.

            Raises IndexError when the index is past the end of the recorded data. The
            DLL leaves its output buffers untouched on a failed read, so without this
            check the call would return the previously read point verbatim and a polling
            loop would silently duplicate points instead of failing.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        if data_point_index < 1:
            raise ValueError(
                "data_point_index is 1-based; the first recorded point is 1 "
                f"(got {data_point_index})"
            )

        result_code, value1, value2, value3 = Core.IV_getdata(
            data_point_index)
        MethodModeFunctions._verify_data_point_result_code(
            result_code, "get_data_point", data_point_index)

        return value1, value2, value3

    @staticmethod
    def get_db_file_name() -> str:
        '''Returns the path and filename of the last created SQL database file'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        _, file_name = Core.IV_getDbFileName()
        return file_name

    @staticmethod
    def update_temperature(value: float):
        '''Updates the shared temperature for all channels (beta).
            value in degrees Celsius'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        result_code, _ = Core.IV_UpdateTemperature(value)
        PyviumVerifiers.verify_result_code(result_code, "update_temperature")

    @staticmethod
    def save_dataset(file_path: str):
        '''Saves all result data in the measurement list to disk.
            file_path represents the full path to the new file.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        result_code, _ = Core.IV_savedataset(file_path)
        PyviumVerifiers.verify_result_code(result_code, "save_dataset")

    @staticmethod
    def get_data_point_from_scan(data_point_index: int, scan_index: int):
        '''Same as get_data_point, but with the additional scan_index parameter.
            This function will allow reading data from non-selected (previous) scans.

            Both indices are 1-based: the first point of the first scan is (1, 1).

            scan_index below 1 is rejected before the call reaches the DLL, because those
            values are not merely invalid, they are destructive: scan_index 0 reports
            success and then terminates the IviumSoft process, and scan_index -1 never
            returns while IviumSoft allocates memory without bound.'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        if scan_index < 1:
            raise ValueError(
                "scan_index is 1-based; the first scan is 1. Values below 1 crash or "
                f"hang IviumSoft and are refused here (got {scan_index})"
            )
        if data_point_index < 1:
            raise ValueError(
                "data_point_index is 1-based; the first recorded point is 1 "
                f"(got {data_point_index})"
            )

        result_code, value1, value2, value3 = Core.IV_getdatafromline(
            data_point_index, scan_index)
        MethodModeFunctions._verify_data_point_result_code(
            result_code, "get_data_point_from_scan", data_point_index, scan_index)

        return value1, value2, value3

    # DLL result code for a data read whose index is past the end of the recorded
    # data. It is 0xFFFF, a 16-bit -1, and it is not one of the codes
    # PyviumVerifiers.verify_result_code documents; routing it through there would
    # collide with -1 (no device), so the data getters map it themselves.
    _INDEX_OUT_OF_RANGE_RESULT_CODE = 65535

    @staticmethod
    def _verify_data_point_result_code(result_code: int, context: str,
                                       data_point_index: int,
                                       scan_index: int | None = None):
        '''Raise on a failed data read instead of returning the untouched buffers.'''
        if result_code == MethodModeFunctions._INDEX_OUT_OF_RANGE_RESULT_CODE:
            location = f"data point {data_point_index}"
            if scan_index is not None:
                location += f" of scan {scan_index}"
            raise IndexError(
                f"{location} is out of range: {context}. Call "
                "get_available_data_points_number() for the number of points recorded "
                "so far"
            )
        PyviumVerifiers.verify_result_code(result_code, context)
