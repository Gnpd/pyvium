from ..core import Core
from ..pyvium_verifiers import PyviumVerifiers


class DirectModeFunctions():

    @staticmethod
    def get_cell_status() -> list:
        '''Returns cell status labels
            ["I_ovl", "Anin1_ovl","E_ovl", "CellOff_button pressed", "Cell on"]'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        _, cell_status_bits = Core.IV_getcellstatus()
        cell_status_labels = []

        labels = ["I_ovl", "", "Anin1_ovl", "E_ovl",
                  "", "CellOff_button pressed", "Cell on"]
        for i, label in enumerate(labels, 2):
            if cell_status_bits & (1 << i) and label:
                cell_status_labels.append(label)
        if len(cell_status_labels) == 0:
            cell_status_labels = ['Cell off']
        return cell_status_labels

    @staticmethod
    def set_connection_mode(connection_mode_number: int):
        ''' Select the connection mode for the currently connected device.
            The available modes depend on the connected device.
            These are all the supported connection modes: 0=off; 1=EStat4EL(default), 2=EStat2EL,
            3=EstatDummy1,4=EStatDummy2,5=EstatDummy3,6=EstatDummy4
            7=Istat4EL, 8=Istat2EL, 9=IstatDummy, 10=BiStat4EL, 11=BiStat2EL'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setconnectionmode(connection_mode_number)

    @staticmethod
    def set_cell_on():
        '''Set cell on '''
        if 'Cell off' in DirectModeFunctions.get_cell_status():
            Core.IV_setcellon(1)

    @staticmethod
    def set_cell_off():
        '''Set cell off '''
        if 'Cell on' in DirectModeFunctions.get_cell_status():
            Core.IV_setcellon(0)

    @staticmethod
    def set_potential(potential_value: float):
        '''Set cell potential'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setpotential(potential_value)

    @staticmethod
    def set_we2_potential(potential_we2_value: float):
        '''Set BiStat offset potential'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setpotentialWE2(potential_we2_value)

    @staticmethod
    def set_current(current_value: float):
        '''Set cell current (galvanostatic mode)'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setcurrent(current_value)

    @staticmethod
    def get_potential() -> float:
        '''Returns measured potential'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        _, potential_value = Core.IV_getpotential()
        return potential_value

    @staticmethod
    def set_current_range(current_range_number: int):
        '''Set current range, 0=10A, 1=1A, etc,'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setcurrentrange(current_range_number)

    @staticmethod
    def set_we2_current_range(current_range_number: int):
        '''Set current range for BiStat, 0=10mA, 1=1mA, etc,'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setcurrentrangeWE2(current_range_number)

    @staticmethod
    def get_current() -> float:
        '''Returns measured current'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        _, current_value = Core.IV_getcurrent()
        return current_value

    @staticmethod
    def get_we2_current() -> float:
        '''Returns measured current from WE2 (bipotentiostat)'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        _, current_value = Core.IV_getcurrentWE2()
        return current_value

    @staticmethod
    def set_filter(filter_number: int):
        '''Set filter, for int :0=1MHz, 1=100kHz, 2=10kHz, 3=1kHz, 4=10Hz'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setfilter(filter_number)

    @staticmethod
    def set_stability(stability_number: int):
        '''Set stability, for int 0=HighSpeed, 1=Standard, 2=HighStability'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setstability(stability_number)

    @staticmethod
    def set_bistat_mode(value: int):
        '''REVISE! --> IV_bistat_mode(int) in documentation
            Select mode for BiStat, for int 0=standard, 1=scanning
            This bistat_mode function also can be used to control
            the Automatic E-ranging function of the instrument;
            0=AutoEranging off; 1=AutoEranging on'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setbistatmode(value)

    @staticmethod
    def set_dac(channel_number: int, value: float):
        '''Set dac on external port, int=0 for dac1, int=1 for dac2'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setdac(channel_number, value)

    @staticmethod
    def get_adc(channel_number: int) -> float:
        '''REVISE! Returns measured voltage on external ADC port, int=channelnr. 0-7'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        _, measured_voltage = Core.IV_getadc(channel_number)
        return measured_voltage

    @staticmethod
    def set_mux_channel(channel_number: int = 0):
        '''Set channel of multiplexer, int=channelnr. starting from 0(default)'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_setmuxchannel(channel_number)

    @staticmethod
    def get_current_trace(points_quantity: int, interval_rate: float):
        '''Returns a sequence of measured currents at defined samplingrate.
            npoints<=256, interval: 10us to 20ms'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        return Core.IV_getcurrenttrace(points_quantity, interval_rate)

    @staticmethod
    def get_current_we2_trace(points_quantity: int, interval_rate: float):
        '''Returns a sequence of measured WE2 currents at defined samplingrate.
            npoints<=256, interval: 10us to 20ms'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        return Core.IV_getcurrentWE2trace(points_quantity, interval_rate)

    @staticmethod
    def get_potential_trace(points_quantity: int, interval_rate: float):
        '''Returns a sequence of measured potentials at defined samplingrate.
            npoints<=256, interval: 10us to 20ms'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        return Core.IV_getpotentialtrace(points_quantity, interval_rate)

    @staticmethod
    def set_we32_offsets(number_of_channels: int, values: list):
        '''Set WE32 offset values for multiple channels.
            number_of_channels: 1..32; values: list of offsets in Volts (-2 to +2V)'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        Core.IV_we32setoffsets(number_of_channels, values)

    @staticmethod
    def set_device_current(instance: int, value: float):
        '''Set current on a selected device instance (galvanostatic mode).
            instance: IviumSoft instance number; value in Ampere'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        Core.IV_selectdevicesetvalue(instance, 0, value)

    @staticmethod
    def set_device_potential(instance: int, value: float):
        '''Set potential on a selected device instance.
            instance: IviumSoft instance number; value in Volt'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()
        Core.IV_selectdevicesetvalue(instance, 1, value)

    @staticmethod
    def set_ac_amplitude(ac_amplitude: float):
        '''Set the value of the ac amplitude in Volts'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        Core.IV_setamplitude(ac_amplitude)

    @staticmethod
    def set_ac_frequency(ac_frequency: float):
        '''Set the value of the ac frequency in Hz'''
        PyviumVerifiers.verify_driver_is_open()
        PyviumVerifiers.verify_iviumsoft_is_running()

        Core.IV_setfrequency(ac_frequency)
