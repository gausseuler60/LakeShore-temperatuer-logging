from Drivers.LakeShoreBase import *


class LakeShore335(LakeShoreBase):
    # Class constructor
    # Control channel: A or B
    # Heater channel: 1 or 2
    def __init__(self, device_num, control_channel, heater_channel, temp_0=None, max_temp=1.7, verbose=True, mode="active",
                 temp_step=0.1):
        input_letters = {'A', 'B'}
        if control_channel not in input_letters:
            raise ValueError('Please set a valid input channel: A or B')
        self._temp_channel = control_channel
        self._heater_channel = heater_channel

        super().__init__(device_num, control_channel, temp_0, max_temp, verbose, mode, temp_step)

    # Remember parameters of one of two inputs: A or B
    def _get_intype(self):
        chan = self._temp_channel
        read_data = self.GetString(f'INTYPE? {chan}')
        sensor_type, autorange, rng, compensation, units = [int(i) for i in read_data.split(',')]
        self._intype_input = chan
        self._intype_sensor_type = sensor_type
        self._intype_autorange = autorange
        self._intype_range = rng
        self._intype_compensation = compensation
        self._intype_units = units

    # device parameter setters
    def _set_pid(self, pid):
        chan = self._heater_channel
        self.device.write(f'PID {chan},{pid}')
        super()._set_pid(pid)

    def _set_heater_range(self, htrrng):
        chan = self._heater_channel
        self.device.write(f'RANGE {chan},{htrrng}')
        super()._set_heater_range(htrrng)

    def _set_excitation(self, excitation):
        chan = self._temp_channel
        self.device.write(f'INTYPE {chan},{self._intype_sensor_type},{self._intype_autorange},{excitation},{self._intype_compensation},{self._intype_units}')
        super()._set_excitation(excitation)

    def _set_channel(self, chan):
        super()._set_channel(chan)

    # Functions for updating LakeShore params depending on temperature
    # Updates thermometer excitation in dependence of temperature
    @staticmethod
    def _get_excitation_for_temperature(temp):
        # TODO: measure in different temperature ranges and find where '2' must be
        n_setting = 1
        return n_setting

    @staticmethod
    def _get_heater_range_from_temperature(temp):
        return 0  # TODO measure in different temperature ranges and set another values there

    def _get_pid_from_temperature(self, temp):
        return "5,2,0"  # TODO measure in different temperature ranges and set another values there

    def _remember_old_params(self):
        self._get_intype()
        self.__old_pid = self.GetString(f'PID? {self._heater_channel}')
        self._pid = self.__old_pid

    def _restore_old_params(self):
        self._set_excitation(self._intype_range)
        self._set_pid(self.__old_pid)

    # Prints current controller parameters
    def PrintParams(self):
        pass  # TODO: implement (if will be needed)

    # Measures a current temperature
    def _meas_temperature(self):
        return self.GetFloat(f'KRDG? {self._temp_channel}')

    # Changes a setpoint
    def _set_setpoint(self, setp):
        chan = self._heater_channel
        self.SendString(f'SETP {setp}')

    def _set_control_mode(self, mode: PIDLoopType):
        # in a device: 1 - closed loop, 3 - open loop, 4 = off
        class_to_device = {PIDLoopType.open_loop: 3,
                           PIDLoopType.close_loop: 1,
                           PIDLoopType.off: 4}

        self.SendString(f'CMODE {class_to_device[mode]}')

