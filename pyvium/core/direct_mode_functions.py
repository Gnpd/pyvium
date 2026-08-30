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
    long __stdcall IV_selectdevice_getcellstatus(long *devnr, long *devcellstatus);
    long __stdcall IV_selectdevice_setconnectionmode(long *devnr, long *value);
    long __stdcall IV_selectdevice_setcellon(long *devnr, long *cellon);
    long __stdcall IV_selectdevice_setpotential(long *devnr, double *value);
    long __stdcall IV_selectdevice_setpotentialWE2(long *devnr, double *value);
    long __stdcall IV_selectdevice_setcurrent(long *devnr, double *value);
    long __stdcall IV_selectdevice_getpotential(long *devnr, double *value);
    long __stdcall IV_selectdevice_setcurrentrange(long *devnr, long *value);
    long __stdcall IV_selectdevice_setcurrentrangeWE2(long *devnr, long *value);
    long __stdcall IV_selectdevice_getcurrent(long *devnr, double *value);
    long __stdcall IV_selectdevice_getcurrentWE2(long *devnr, double *value);
    long __stdcall IV_selectdevice_setfilter(long *devnr, long *value);
    long __stdcall IV_selectdevice_setstability(long *devnr, long *value);
    long __stdcall IV_selectdevice_setbistatmode(long *devnr, long *value);
    long __stdcall IV_selectdevice_setdac(long *devnr, long *channr, double *value);
    long __stdcall IV_selectdevice_getadc(long *devnr, long *channr, double *value);
    long __stdcall IV_selectdevice_setmuxchannel(long *devnr, long *value);
    long __stdcall IV_selectdevice_setdigout(long *devnr, long *value);
    long __stdcall IV_selectdevice_getdigin(long *devnr, long *value);
    long __stdcall IV_selectdevice_setfrequency(long *devnr, double *value);
    long __stdcall IV_selectdevice_setamplitude(long *devnr, double *value);
    long __stdcall IV_selectdevice_getcurrenttrace(long *devnr, long* npoints, double *rate, double *values);
    long __stdcall IV_selectdevice_getcurrentWE2trace(long *devnr, long* npoints, double *rate, double *values);
    long __stdcall IV_selectdevice_getpotentialtrace(long *devnr, long* npoints, double *rate, double *values);
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
    ) -> tuple[int, list]:
        """Returns a sequence of measured currents at defined samplingrate.
        npoints<=256, interval: 10us to 20ms"""
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        values_arr = ffi.new(f"double[{points_quantity}]")
        result_code = CoreBase.get_lib().IV_getcurrenttrace(
            points_quantity_ptr, interval_rate_ptr, values_arr
        )
        return result_code, list(values_arr)

    @staticmethod
    def IV_getcurrentWE2trace(
        points_quantity: int, interval_rate: float
    ) -> tuple[int, list]:
        """Returns a sequence of measured WE2 currents at defined samplingrate.
        npoints<=256, interval: 10us to 20ms"""
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        values_arr = ffi.new(f"double[{points_quantity}]")
        result_code = CoreBase.get_lib().IV_getcurrentWE2trace(
            points_quantity_ptr, interval_rate_ptr, values_arr
        )
        return result_code, list(values_arr)

    @staticmethod
    def IV_getpotentialtrace(
        points_quantity: int, interval_rate: float
    ) -> tuple[int, list]:
        """Returns a sequence of measured potentials at defined samplingrate.
        npoints<=256, interval: 10us to 20ms"""
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        values_arr = ffi.new(f"double[{points_quantity}]")
        result_code = CoreBase.get_lib().IV_getpotentialtrace(
            points_quantity_ptr, interval_rate_ptr, values_arr
        )
        return result_code, list(values_arr)

    # --- selectdevice variants (scoped to an IviumSoft instance) ----------
    # One-call forms of the direct-mode functions, each taking a leading
    # IviumSoft instance number. Hardware-confirmed these are IV_selectdevice +
    # the base call fused: they leave the global selection parked on that
    # instance and do NOT restore it (see IV_selectdevice_getdevicestatus).
    # Thin 1:1 bindings like the rest of Core: raw result codes, no restore.

    @staticmethod
    def IV_selectdevice_getcellstatus(instance: int) -> tuple[int, int]:
        """Scoped IV_getcellstatus for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        cell_status_ptr = ffi.new(LONG_PTR)
        result_code = CoreBase.get_lib().IV_selectdevice_getcellstatus(
            instance_ptr, cell_status_ptr)
        return result_code, cell_status_ptr[0]

    @staticmethod
    def IV_selectdevice_setconnectionmode(instance: int, connection_mode_number: int) -> int:
        """Scoped IV_setconnectionmode for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        connection_mode_number_ptr = ffi.new(LONG_PTR, connection_mode_number)
        return CoreBase.get_lib().IV_selectdevice_setconnectionmode(
            instance_ptr, connection_mode_number_ptr)

    @staticmethod
    def IV_selectdevice_setcellon(instance: int, cell_on_mode_number: int) -> int:
        """Scoped IV_setcellon for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        cell_on_mode_number_ptr = ffi.new(LONG_PTR, cell_on_mode_number)
        return CoreBase.get_lib().IV_selectdevice_setcellon(
            instance_ptr, cell_on_mode_number_ptr)

    @staticmethod
    def IV_selectdevice_setpotential(instance: int, value: float) -> int:
        """Scoped IV_setpotential (cell potential) for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(DOUBLE_PTR, value)
        return CoreBase.get_lib().IV_selectdevice_setpotential(instance_ptr, value_ptr)

    @staticmethod
    def IV_selectdevice_setpotentialWE2(instance: int, value: float) -> int:
        """Scoped IV_setpotentialWE2 (BiStat offset potential) for the given instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(DOUBLE_PTR, value)
        return CoreBase.get_lib().IV_selectdevice_setpotentialWE2(instance_ptr, value_ptr)

    @staticmethod
    def IV_selectdevice_setcurrent(instance: int, value: float) -> int:
        """Scoped IV_setcurrent (galvanostatic mode) for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(DOUBLE_PTR, value)
        return CoreBase.get_lib().IV_selectdevice_setcurrent(instance_ptr, value_ptr)

    @staticmethod
    def IV_selectdevice_getpotential(instance: int) -> tuple[int, float]:
        """Scoped IV_getpotential for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_selectdevice_getpotential(
            instance_ptr, value_ptr)
        return result_code, value_ptr[0]

    @staticmethod
    def IV_selectdevice_setcurrentrange(instance: int, current_range_number: int) -> int:
        """Scoped IV_setcurrentrange for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        current_range_number_ptr = ffi.new(LONG_PTR, current_range_number)
        return CoreBase.get_lib().IV_selectdevice_setcurrentrange(
            instance_ptr, current_range_number_ptr)

    @staticmethod
    def IV_selectdevice_setcurrentrangeWE2(instance: int, current_range_number: int) -> int:
        """Scoped IV_setcurrentrangeWE2 for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        current_range_number_ptr = ffi.new(LONG_PTR, current_range_number)
        return CoreBase.get_lib().IV_selectdevice_setcurrentrangeWE2(
            instance_ptr, current_range_number_ptr)

    @staticmethod
    def IV_selectdevice_getcurrent(instance: int) -> tuple[int, float]:
        """Scoped IV_getcurrent for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_selectdevice_getcurrent(
            instance_ptr, value_ptr)
        return result_code, value_ptr[0]

    @staticmethod
    def IV_selectdevice_getcurrentWE2(instance: int) -> tuple[int, float]:
        """Scoped IV_getcurrentWE2 (bipotentiostat) for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_selectdevice_getcurrentWE2(
            instance_ptr, value_ptr)
        return result_code, value_ptr[0]

    @staticmethod
    def IV_selectdevice_setfilter(instance: int, filter_number: int) -> int:
        """Scoped IV_setfilter for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        filter_number_ptr = ffi.new(LONG_PTR, filter_number)
        return CoreBase.get_lib().IV_selectdevice_setfilter(
            instance_ptr, filter_number_ptr)

    @staticmethod
    def IV_selectdevice_setstability(instance: int, stability_number: int) -> int:
        """Scoped IV_setstability for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        stability_number_ptr = ffi.new(LONG_PTR, stability_number)
        return CoreBase.get_lib().IV_selectdevice_setstability(
            instance_ptr, stability_number_ptr)

    @staticmethod
    def IV_selectdevice_setbistatmode(instance: int, value: int) -> int:
        """Scoped IV_setbistatmode for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(LONG_PTR, value)
        return CoreBase.get_lib().IV_selectdevice_setbistatmode(instance_ptr, value_ptr)

    @staticmethod
    def IV_selectdevice_setdac(instance: int, channel_number: int, value: float) -> int:
        """Scoped IV_setdac for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        channel_number_ptr = ffi.new(LONG_PTR, channel_number)
        value_ptr = ffi.new(DOUBLE_PTR, value)
        return CoreBase.get_lib().IV_selectdevice_setdac(
            instance_ptr, channel_number_ptr, value_ptr)

    @staticmethod
    def IV_selectdevice_getadc(instance: int, channel_number: int) -> tuple[int, float]:
        """Scoped IV_getadc for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        channel_number_ptr = ffi.new(LONG_PTR, channel_number)
        measured_voltage_ptr = ffi.new(DOUBLE_PTR)
        result_code = CoreBase.get_lib().IV_selectdevice_getadc(
            instance_ptr, channel_number_ptr, measured_voltage_ptr)
        return result_code, measured_voltage_ptr[0]

    @staticmethod
    def IV_selectdevice_setmuxchannel(instance: int, channel_number: int = 0) -> int:
        """Scoped IV_setmuxchannel for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        channel_number_ptr = ffi.new(LONG_PTR, channel_number)
        return CoreBase.get_lib().IV_selectdevice_setmuxchannel(
            instance_ptr, channel_number_ptr)

    @staticmethod
    def IV_selectdevice_setdigout(instance: int, value: int) -> int:
        """Scoped IV_setdigout for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(LONG_PTR, value)
        return CoreBase.get_lib().IV_selectdevice_setdigout(instance_ptr, value_ptr)

    @staticmethod
    def IV_selectdevice_getdigin(instance: int) -> tuple[int, int]:
        """Scoped IV_getdigin for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        value_ptr = ffi.new(LONG_PTR)
        result_code = CoreBase.get_lib().IV_selectdevice_getdigin(
            instance_ptr, value_ptr)
        return result_code, value_ptr[0]

    @staticmethod
    def IV_selectdevice_setfrequency(instance: int, frequency: float) -> int:
        """Scoped IV_setfrequency for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        frequency_ptr = ffi.new(DOUBLE_PTR, frequency)
        return CoreBase.get_lib().IV_selectdevice_setfrequency(
            instance_ptr, frequency_ptr)

    @staticmethod
    def IV_selectdevice_setamplitude(instance: int, amplitude: float) -> int:
        """Scoped IV_setamplitude for the given IviumSoft instance."""
        instance_ptr = ffi.new(LONG_PTR, instance)
        amplitude_ptr = ffi.new(DOUBLE_PTR, amplitude)
        return CoreBase.get_lib().IV_selectdevice_setamplitude(
            instance_ptr, amplitude_ptr)

    @staticmethod
    def IV_selectdevice_getcurrenttrace(
        instance: int, points_quantity: int, interval_rate: float
    ) -> tuple[int, list]:
        """Scoped IV_getcurrenttrace for the given IviumSoft instance.
        npoints<=256, interval: 10us to 20ms"""
        instance_ptr = ffi.new(LONG_PTR, instance)
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        values_arr = ffi.new(f"double[{points_quantity}]")
        result_code = CoreBase.get_lib().IV_selectdevice_getcurrenttrace(
            instance_ptr, points_quantity_ptr, interval_rate_ptr, values_arr)
        return result_code, list(values_arr)

    @staticmethod
    def IV_selectdevice_getcurrentWE2trace(
        instance: int, points_quantity: int, interval_rate: float
    ) -> tuple[int, list]:
        """Scoped IV_getcurrentWE2trace for the given IviumSoft instance.
        npoints<=256, interval: 10us to 20ms"""
        instance_ptr = ffi.new(LONG_PTR, instance)
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        values_arr = ffi.new(f"double[{points_quantity}]")
        result_code = CoreBase.get_lib().IV_selectdevice_getcurrentWE2trace(
            instance_ptr, points_quantity_ptr, interval_rate_ptr, values_arr)
        return result_code, list(values_arr)

    @staticmethod
    def IV_selectdevice_getpotentialtrace(
        instance: int, points_quantity: int, interval_rate: float
    ) -> tuple[int, list]:
        """Scoped IV_getpotentialtrace for the given IviumSoft instance.
        npoints<=256, interval: 10us to 20ms"""
        instance_ptr = ffi.new(LONG_PTR, instance)
        points_quantity_ptr = ffi.new(LONG_PTR, points_quantity)
        interval_rate_ptr = ffi.new(DOUBLE_PTR, interval_rate)
        values_arr = ffi.new(f"double[{points_quantity}]")
        result_code = CoreBase.get_lib().IV_selectdevice_getpotentialtrace(
            instance_ptr, points_quantity_ptr, interval_rate_ptr, values_arr)
        return result_code, list(values_arr)
