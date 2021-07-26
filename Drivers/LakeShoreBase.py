from Drivers import visa_device
import numpy as np
import time
import threading
from enum import Enum


# An exception to be thrown if we try to control a temperature in a passive mode
class LakeShoreException(Exception):
    def __init__(self):
        super().__init__("Temperature sweep is allowed only in active mode")


# PID loop type
class PIDLoopType(Enum):
    off = 0
    close_loop = 1
    open_loop = 2


class LakeShoreBase(visa_device.visa_device):
    # device parameter setters
    # all of them must be overridden in child classes
    # and overriding methods must call super()._set_pid

    # set PID as a string, e.g. "10,20,30"
    def _set_pid(self, pid):
        print('PID is:', pid)
        self._pid = pid

    # set heater range
    def _set_heater_range(self, htrrng):
        print('Heater range is:', htrrng)
        self._htrrng = htrrng

    # set thermometer excitation range
    def _set_excitation(self, excitation):
        print('Excitation is:', excitation)
        self._excitation = excitation

    # set channel for temperature control
    def _set_channel(self, chan):
        self._temp_channel = chan
        print('Scanning', chan, 'channel')

    # Functions for updating LakeShore params depending on temperature
    @staticmethod
    def _get_excitation_from_temperature(temp):
        # must be overridden in a child class
        return 0

    # Updates thermometer excitation in dependence of temperature
    def _update_excitation(self, T):
        n_setting = self._get_excitation_from_temperature(T)
        self._set_excitation(n_setting)

    @staticmethod
    def _get_heater_range_from_temperature(temp):
        # must be overridden in a child class
        return 0

    # Updates heater range in dependence of temperature
    def _update_heater_range(self, T):
        rng = self._get_heater_range_from_temperature(T)
        self._set_heater_range(rng)

    def _get_pid_from_temperature(self, temp):
        # must be overridden in a child class
        return 0

    # Updates PID in dependence of temperature
    def _update_pid(self, T):
        new_pid = self._get_pid_from_temperature(T)
        self._set_pid(new_pid)

    # Main function which is updating LakeShore parameters at each temperature change
    def _update_params(self, T):
        print('---------------')
        print('LakeShore status:')
        print('Temperature is:', T)
        self._update_excitation(T)
        self._update_pid(T)
        self._update_heater_range(T)
        print('---------------')

    # Remember old LakeShore parameters (PID, excitation and heater range)
    def _remember_old_params(self):
        # must be overridden in a child class
        pass

    def _restore_old_params(self):
        # must be overridden in a child class
        pass

    # Measure a current temperature
    def _meas_temperature(self):
        # must be overridden in a child class
        return 0

    def GetTemperature(self):
        self.__SensorFree.wait()  # wait for another thread (if one present) to complete operation
        self.__SensorFree.clear()  # lock for another threads

        # check if previous request was too close in time
        curr_meas = time.time()
        time.sleep(0.5)
        if curr_meas - self.__prev_measured < 1:
            time.sleep(1)
        try:
            resp = self._meas_temperature()
            temp = np.float64(resp)
            res = temp
        except Exception:
            res = 0
            print('Error while measuring temperature')

        self.__prev_measured = time.time()
        self.__SensorFree.set()  # unlock

        return res

    # Number of swept temperature values
    @property
    def NumTemps(self):
        if not self._active:
            raise LakeShoreException()
        return len(self._tempValues)

    # All swept temperature values (as Numpy array)
    @property
    def TempRange(self):
        if not self._active:
            raise LakeShoreException()
        return self._tempValues

    @property
    def pid(self):
        return self._pid

    @property
    def htrrng(self):
        return self._htrrng

    @property
    def excitation(self):
        return self._excitation

    @property
    def temp_channel(self):
        return self._temp_channel

    @temp_channel.setter
    def temp_channel(self, chan):
        curr_change = time.time()
        if curr_change - self.__prev_changed < 2:
            time.sleep(2)
        self._set_channel(chan)
        self.__prev_changed = time.time()

    # Changes a setpoint (in Kelvins)
    def _set_setpoint(self, setp):
        # must be overridden in a child class
        pass

    # Changes PID loop control type
    def _set_control_mode(self, mode: PIDLoopType):
        # must be overridden in a child class
        pass

    # A class constructor
    # temp0 - starter swept temperature (if None, use current temperature)
    # max_temp - maximum swept temperature, must be <=1.7 K
    # step - sweep step
    def __init__(self, device_num, control_channel, temp_0=None, max_temp=1.7, verbose=True, mode="active",
                 temp_step=0.1):
        self._verbose = verbose
        self._active = (mode == "active")

        # Time from previous temperature measurement request.
        # It is made to avoid a device to stop responding because of a buffer overflow.
        self.__prev_measured = time.time()
        self.__prev_changed = time.time()

        # Load and configure a device
        if self._verbose:
            print('Connecting LakeShore bridge...')

        # connect to device
        super().__init__(device_num)

        # Event to prevent simultaneous temperature request - it will cause an error
        self.__SensorFree = threading.Event()
        self.__SensorFree.set()

        # remember current heater paramrters to restore them after program end
        self._remember_old_params()

        # Select temperature channel
        self._set_channel(control_channel)

        # Set LakeShore control and heating parameters
        if self._active:
            initialTemp = temp_0 if temp_0 is not None else self.GetTemperature()
            self._set_setpoint(initialTemp)
            self._set_control_mode(PIDLoopType.close_loop)  # control mode - closed-loop PID
            self._update_params(initialTemp)

            # temperature swept values
            self._tempValues = np.arange(initialTemp, max_temp, temp_step)

        if self._verbose:
            print('LakeShore bridge connection success')

    # Iterate over all temperatures and set them on a device
    def __iter__(self):
        if not self._active:
            raise LakeShoreException()

        tol_temp = 0.001
        for temp in self._tempValues:
            # assert temp <= 1.7, 'ERROR! Attempt to set too high temperature was made.'
            self._set_setpoint(temp)

            # Update temperature measurement parameters depending on T
            self._update_params(temp)

            actual_temp = self.GetTemperature()
            print(f'Heating... (target temperature - {temp})')

            # Wait for temperature to be established
            c = 0
            while abs(actual_temp - temp) >= tol_temp:
                time.sleep(1)
                actual_temp = self.GetTemperature()

            # A temperature must be stable for 3 seconds
            print('Temperature is set, waiting to be stable...')
            count_ok = 0
            while count_ok < 3:
                time.sleep(3)
                actual_temp = self.GetTemperature()
                print('Now:', actual_temp, 'K, must be:', temp, 'K')
                if abs(actual_temp - temp) <= tol_temp:
                    count_ok += 1
                    print('Stable', count_ok, 'times')
                else:
                    count_ok = 0
                c += 1
                if c > 50:
                    print('Warning! Cannot set a correct temperature')
                    break

            print('Temperature was set')

            yield actual_temp  # last actual temperature

    # class destructor - turn off a heater and free VISA resources
    def __del__(self):
        # Turn off heater and PID control
        if self._active:
            self._set_heater_range(0)
            self._set_control_mode(PIDLoopType.off)
            self._restore_old_params()

        if self._verbose:
            print('LakeShore bridge disconnected.')
            if self._active:
                print('Heater is off.')
                print('Old heater range parameters restored.')
