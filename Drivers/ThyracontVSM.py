import serial

class ThyracontVSM:
    @staticmethod
    def _calc_checksum(s):
        sum = 0
        for ch in s:
            sum += ord(ch)
        return chr(sum % 64 + 64)
        
    def _read_and_write_cmd(self, cmd, length_read):
        checksum = self._calc_checksum(cmd)
        str_cmd = f'{cmd}{checksum}\r'
        
        data = bytearray(str_cmd.encode())
        
        device = self.device
        device.write(data)
        
        inp = device.read(length_read)
        return inp.decode()
        
    def read_name(self):
        return self._read_and_write_cmd('0010PN00', 20)
    
    def read_pressure(self):
        num = self.device_num
 
        read_str = self._read_and_write_cmd(f'{num:03d}0MV00', 16)
        
        if not read_str.startswith(f'{num:03d}1MV'):
            raise ValueError('Device returned an invalid answer')
        
        length = int(read_str[6:8])
        press = read_str[8:8+length]
        return float(press)
    
    def _detect_device(self):
        f_found = False
        for port in range(1, 10):
            try:
                prt = f'COM{port}'
                comport = serial.Serial(prt, timeout=0.5) 
                comport.baudrate = 9600 
                comport.bytesize = 8    
                comport.parity   = 'N' 
                comport.stopbits = 1
                self.device = comport
            except serial.SerialException:
                continue
            try:
                p = self.read_pressure()
                n = self.read_name()
                if 'VSM77' in n:
                    f_found = True
                    port_found = prt
                    break
            except ValueError:
                continue
        
        if not f_found:
            raise ValueError('Could not detect VSM pressure sensor')
        else:
            print('VSM77 detected on port:', prt)
    
    def __init__(self, device_num=1):
        self.device_num = device_num
        self._detect_device()