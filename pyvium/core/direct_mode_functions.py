from .constants import DOUBLE_PTR, LONG_PTR
from .core_base import CoreBase, ffi

ffi.cdef(
    """
    long __stdcall IV_getcellstatus(long *devcellstatus);
    long __stdcall IV_setconnectionmode(long *value);
    long __stdcall IV_setcellon(long *cellon);
    long __stdcall IV_setpotential(double *value);
    long __stdcall IV_setpotentialWE2(double *value);
    long __stdcall IV_setcurrent(double *value);
    long __stdcall IV_getpotential(double *value);
    long __stdcall IV_setcurrentrange(long *value);
    long __stdcall IV_setcurrentrangeWE2(long *value);
    long __stdcall IV_getcurrent(double *value);
    long __stdcall IV_getcurrentWE2(double *value);
    long __stdcall IV_setfilter(long *value);
    long __stdcall IV_setstability(long *value);
    long __stdcall IV_setbistatmode(long *value);
    long __stdcall IV_setdac(long *channr, double *value);
    long __stdcall IV_getadc(long *channr, double *value);
    long __stdcall IV_setmuxchannel(long *value);
    long __stdcall IV_setdigout(long *value);
    long __stdcall IV_getdigin(long *value);
    long __stdcall IV_setfrequency(double *value);
    long __stdcall IV_setamplitude(double *value);
    long __stdcall IV_getcurrenttrace(long* npoints, double *rate, double *values);
    long __stdcall IV_getcurrentWE2trace(long* npoints, double *rate, double *values);
    long __stdcall IV_getpotentialtrace(long* npoints, double *rate, double *values);
    long __stdcall IV_selectdevicesetvalue(long *devnr, long *valuetype, double *value);
"""
)


class DirectModeFunctions(CoreBase):
    """
    DirectModeFunctions class provides access to the direct mode functions of the IviumSoft library.
    """

    @staticmethod
    def IV_getcellstatus() -> tuple[int, int]:
        """Returns cell status labels
        ["I_ovl", "Anin1_ovl","E_ovl", "CellOff_button pressed", "Cell on"]"""
        cell_status_ptr = ffi.new(LONG_PTR)
        result_code = CoreBase.get_lib().IV_getcellstatus(cell_status_ptr)
        return result_code, cell_status_ptr[0]

    @staticmethod
    def IV_setconnectionmode(connection_mode_number: int) -> int:
        """Select the connection mode for the currently connected device.
        The available modes depend on the connected device.
        These are all the supported connection modes: 0=off; 1=EStat4EL(default), 2=EStat2EL,
        3=EstatDummy1,4=EStatDummy2,5=EstatDummy3,6=EstatDummy4
        7=Istat4EL, 8=Istat2EL, 9=IstatDummy, 10=BiStat4EL, 11=BiStat2EL"""
        connection_mode_number_ptr = ffi.new(LONG_PTR, connection_mode_number)
        result_code = CoreBase.get_lib().IV_setconnectionmode(
            connection_mode_number_ptr
        )
        return result_code

    @staticmethod
    def IV_setcellon(cell_on_mode_number: int) -> int:
        """Set cell on off to close cell relais (0=off;1=on)"""
        cell_on_mode_number_ptr = ffi.new(LONG_PTR, cell_on_mode_number)
        result_code = CoreBase.get_lib().IV_setcellon(cell_on_mode_number_ptr)
        return result_code

    @staticmethod
    def IV_setpotential(potential_value: float) -> int:
        """Set cell potential"""
        potential_value_ptr = ffi.new(DOUBLE_PTR, potential_value)
        result_code = CoreBase.get_lib().IV_setpotential(potential_value_ptr)
        return result_code

    @staticmethod
    def IV_setpotentialWE2(potential_we2_value: float) -> int:
        """Set BiStat offset potential"""
        potential_we2_value_ptr = ffi.new(DOUBLE_PTR, potential_we2_value)
        result_code = CoreBase.get_lib().IV_setpotentialWE2(potential_we2_value_ptr)
        return result_code

    @staticmethod
    def IV_setcurrent(current_value: float) -> int:
        """Set cell current (galvanostatic mode)"""
        current_value_ptr = ffi.new(DOUBLE_PTR, current_value)
        result_code = CoreBase.get_lib().IV_setcurrent(current_value_ptr)
        return result_code

    @staticmethod
    def IV_getpotential() -> tuple[int, float]:
        """Returns measured potential"""
        potential_value_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getpotential(potential_value_ptr)
        return result_code, potential_value_ptr[0]

    @staticmethod
    def IV_setcurrentrange(current_range_number: int) -> int:
        """Set current range, 0=10A, 1=1A, etc,"""
        current_range_number_ptr = ffi.new(LONG_PTR, current_range_number)
        result_code = CoreBase.get_lib().IV_setcurrentrange(current_range_number_ptr)
        return result_code

    @staticmethod
    def IV_setcurrentrangeWE2(current_range_number: int) -> int:
        """Set current range for BiStat, 0=10mA, 1=1mA, etc,"""
        current_range_number_ptr = ffi.new(LONG_PTR, current_range_number)
        result_code = CoreBase.get_lib().IV_setcurrentrangeWE2(current_range_number_ptr)
        return result_code

    @staticmethod
    def IV_getcurrent() -> tuple[int, float]:
        """Returns measured current"""
        current_value_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getcurrent(current_value_ptr)
        return result_code, current_value_ptr[0]

    @staticmethod
    def IV_getcurrentWE2() -> tuple[int, float]:
        """Returns measured current from WE2 (bipotentiostat)"""
        current_value_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getcurrentWE2(current_value_ptr)
        return result_code, current_value_ptr[0]

    @staticmethod
    def IV_setfilter(filter_number: int) -> int:
        """Set filter, for int :0=1MHz, 1=100kHz, 2=10kHz, 3=1kHz, 4=10Hz"""
        filter_number_ptr = ffi.new(LONG_PTR, filter_number)
        result_code = CoreBase.get_lib().IV_setfilter(filter_number_ptr)
        return result_code

    @staticmethod
    def IV_setstability(stability_number: int) -> int:
        """Set stability, for int 0=HighSpeed, 1=Standard, 2=HighStability"""
        stability_number_ptr = ffi.new(LONG_PTR, stability_number)
        result_code = CoreBase.get_lib().IV_setstability(stability_number_ptr)
        return result_code

    @staticmethod
    def IV_setbistatmode(value: int) -> int:
        """REVISE! --> IV_bistat_mode(int) in documentation
        Select mode for BiStat, for int 0=standard, 1=scanning
        This bistat_mode function also can be used to control the Automatic E-ranging function of the instrument;
        0=AutoEranging off; 1=AutoEranging on"""
        value_ptr = ffi.new(LONG_PTR, value)
        result_code = CoreBase.get_lib().IV_setbistatmode(value_ptr)
        return result_code

    @staticmethod
    def IV_setdac(channel_number: int, value: float) -> int:
        """Set dac on external port, int=0 for dac1, int=1 for dac2"""
        channel_number_ptr = ffi.new(LONG_PTR, channel_number)
        value_ptr = ffi.new(DOUBLE_PTR, value)
        result_code = CoreBase.get_lib().IV_setdac(channel_number_ptr, value_ptr)
        return result_code

    @staticmethod
    def IV_getadc(channel_number: int) -> tuple[int, float]:
        """REVISE! Returns measured voltage on external ADC port, int=channelnr. 0-7"""
        channel_number_ptr = ffi.new(LONG_PTR, channel_number)
        measured_voltage_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getadc(
            channel_number_ptr, measured_voltage_ptr
        )
        return result_code, measured_voltage_ptr[0]

    @staticmethod
    def IV_setmuxchannel(channel_number=0) -> int:
        """Set channel of multiplexer, int=channelnr. starting from 0(default)"""
        channel_number_ptr = ffi.new(LONG_PTR, channel_number)
        result_code = CoreBase.get_lib().IV_setmuxchannel(channel_number_ptr)
        return result_code

    @staticmethod
    def IV_setdigout(value: int) -> int:
        """REVISE! Set digital lines on external port, int is bitmask"""
        value_ptr = ffi.new(LONG_PTR, value)
        result_code = CoreBase.get_lib().IV_setdigout(value_ptr)
        return result_code

    @staticmethod
    def IV_getdigin() -> tuple[int, int]:
        """REVISE! Returns status of digital inputs from external port, int is bitmask"""
        value_ptr = ffi.new(LONG_PTR)
        result_code = CoreBase.get_lib().IV_getdigin(value_ptr)
        return result_code, value_ptr[0]

    @staticmethod
    def IV_setfrequency(frequency: float) -> int:
        frequency_ptr = ffi.new(DOUBLE_PTR, frequency)
        result_code: int = CoreBase.get_lib().IV_setfrequency(frequency_ptr)
        return result_code

    @staticmethod
    def IV_setamplitude(amplitude: float) -> int:
        amplitude_ptr = ffi.new(DOUBLE_PTR, amplitude)
        result_code: int = CoreBase.get_lib().IV_setamplitude(amplitude_ptr)
        return result_code

    @staticmethod
    def IV_getcurrenttrace(
        points_quantity: int, interval_rate: float
    ) -> tuple[int, float]:
        """Returns a sequence of measured currents at defined samplingrate
        (npoints, interval, array of double): npoints<=256, interval: 10us to 20ms"""
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        result_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getcurrenttrace(
            points_quantity_ptr, interval_rate_ptr, result_ptr
        )
        return result_code, result_ptr[0]

    @staticmethod
    def IV_getcurrentWE2trace(
        points_quantity: int, interval_rate: float
    ) -> tuple[int, float]:
        """Returns a sequence of measured WE2 currents at defined samplingrate
        (npoints, interval, array of double): npoints<=256, interval: 10us to 20ms"""
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        result_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getcurrentWE2trace(
            points_quantity_ptr, interval_rate_ptr, result_ptr
        )
        return result_code, result_ptr[0]

    @staticmethod
    def IV_getpotentialtrace(
        points_quantity: int, interval_rate: float
    ) -> tuple[int, float]:
        """Returns a sequence of measured potentials at defined samplingrate
        (npoints, interval, array of double): npoints<=256, interval: 10us to 20ms"""
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        result_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_getpotentialtrace(
            points_quantity_ptr, interval_rate_ptr, result_ptr
        )
        return result_code, result_ptr[0]

    @staticmethod
    def IV_selectdevicesetvalue(instance: int, value_type: int, value: float) -> int:
        """Set potential or current on a selected device instance.
        instance: IviumSoft instance number; value_type: 0=current, 1=potential"""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_type_ptr = ffi.new(LONG_PTR, value_type)
        value_ptr = ffi.new(DOUBLE_PTR, value)
        return CoreBase.get_lib().IV_selectdevicesetvalue(
            instance_ptr, value_type_ptr, value_ptr
        )
