import numpy as np
from copy import copy
import math

from slave import Slave
from Drivers.LakeShore335 import LakeShore335

LAKESHORE_MODEL_370 = 0
LAKESHORE_MODEL_335 = 1


class ARS_4K_slave(Slave):
    def __init__(self, nickname, password, server_address, server_port, temp_list_A, temp_list_B, temp_buffer_size, pressure):
        self._temps_A = temp_list_A
        self._temps_B = temp_list_B
        self._pressure = pressure
        self._buffer_size = temp_buffer_size
        self._xaxis = np.linspace(1, self._buffer_size, self._buffer_size)
        # self._last_event_check_time = datetime.now()
        super().__init__(nickname, password, server_address, server_port)

    # def generate_alert_messages(self):
    # TODO: maybe add messages about some events
    #     return []
    
    @staticmethod   
    def _format_unicode_sci(number):
        try:
            exponent = int(round(math.log10(abs(number))))
            mantis = number / 10 ** exponent
            
            sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
            
            # format like it is shown on a sensor
            if mantis < 1:
                mantis *= 10
                exponent -= 1
                
            return f"{mantis:.2f}·10{str(exponent).translate(sup)}"
        except Exception:
            return str(number)   
       
    def generate_info_message(self):
        if len(self._temps_A) == 0:
            return "Please wait, loading..."

        temp_A = self._temps_A[-1]
        temp_B = self._temps_B[-1]

        # Determine warming or cooling status
        if len(self._temps_A) >= 5:
            frozen_temps = copy(self._temps_A)
            n_frozen_temps = len(frozen_temps)
            rng = np.linspace(0, n_frozen_temps, n_frozen_temps)
            temps_approx_k = np.polyfit(rng, frozen_temps, deg=1)[0]
            if temps_approx_k > 0:
                status = '🔴Warming'
            else:
                status = '🟢Cooling'
            if abs(self._temps_A[-1] - self._temps_A[0]) < 0.2:
                status = '🔵Approx. stable'
        else:
            status = 'Gathering statistics...'

        message = f'Temperatures:\n✔Channel A: {temp_A:.3f} K\n✔Channel B: {temp_B:.3f}K'
        press = self._pressure[0]

        if press is not None:
            message += f'\n\n Pressure:\n {self._format_unicode_sci(press)} mBar'
        final = '\n' + status + '\n\n' + message

        return final



