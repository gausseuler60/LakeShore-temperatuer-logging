# A base class for VISA devices manipulating.
# Every driver is an ancestor if this class.
# To work with devices you must install a PyVISA library
# (pip install pyvisa)
import visa
import numpy as np


class visa_device:
    def __init__(self, device_id):
        rm = visa.ResourceManager()
        if isinstance(device_id, int):
            device_num = int(device_id)
            device = rm.open_resource(f"GPIB0::{device_num}::INSTR")
        elif isinstance(device_id, str):
            addr = str(device_id)
            device = rm.open_resource(addr)
        else:
            raise ValueError('Invalid device initialization, please provide GPIB num or device address.')
        self.device = device

    def __error_message(self):
        print('Check that device is connected, visible in NI MAX and is not used by another software.')

    def SendString(self, cmd_str):
        device = self.device
        try:
            device.write(cmd_str)
        except visa.VisaIOError as e:
            print('Unable to connect device.\n', e)
            self.__error_message()

    def GetString(self, cmd_str):
        device = self.device
        try:
            resp = device.query(cmd_str)
            return resp
        except Exception as e:
            print('Unable to connect device.\n', e)
            self.__error_message()
            return ""

    def GetFloat(self, cmd_str):
        device = self.device
        resp = ""

        try:
            resp = device.query(cmd_str)
            num = np.float64(resp)
            return num
        except visa.VisaIOError as e:
            print('Unable to read data from device.\n', e)
            self.__error_message()
            return 0
        except Exception:
            print('Device returned an invalid responce:', resp)
