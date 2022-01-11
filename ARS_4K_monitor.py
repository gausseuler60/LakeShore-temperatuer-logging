import threading
import os
from os import path
import threading
import time
import wx
import wx.adv

from Drivers.LakeShore335 import LakeShore335
from Drivers.ThyracontVSM import ThyracontVSM
from ARS_4K_remote import ARS_4K_slave

TRAY_TOOLTIP = 'ARS 4K cryostat logging tool'
TRAY_ICON = 'Monitor.ico'

temp_log_file_name = 'Temperature.log'
press_log_file_name = 'Pressure.log'
auth_file_name = 'overseer_auth.dat'
temp_buffer_size = 12
current_temp_logging_file = ''
current_press_logging_file = ''

press_sensor_enabled = True

def ensure_logging_directories():
    current_date = time.strftime('%Y-%m-%d')
    logging_dir = path.join(os.getcwd(), 'Logs', current_date)
    if not path.isdir(logging_dir):
        os.makedirs(logging_dir)
    return logging_dir


def check_day_change():
    global current_temp_logging_file
    now = time.localtime()
    hours = now.tm_hour
    minutes = now.tm_min

    if hours == 0 and minutes == 0:
        current_temp_logging_file = path.join(ensure_logging_directories(), temp_log_file_name)
        current_press_logging_file = path.join(ensure_logging_directories(), press_log_file_name)


def add_temperatures_to_lists(temp_A, temp_B):
    last_temps_A.append(temp_A)
    last_temps_B.append(temp_B)
    if len(last_temps_A) > temp_buffer_size:
        last_temps_A.pop(0)
        last_temps_B.pop(0)


def perform_logging_record(temp_A, temp_B, pressure):
    time_to_write = time.strftime('%H-%M-%S')
    with open(current_temp_logging_file, 'a') as f:
        f.write(f'{time_to_write} {temp_A} {temp_B}\n')
        
    if not (pressure is None):
        with open(current_press_logging_file, 'a') as f:
            f.write(f'{time_to_write} {pressure}\n')


def scan_temperatures(device: LakeShore335):
    device.temp_channel = 'A'
    temp_A = device.GetTemperature()
    device.temp_channel = 'B'
    temp_B = device.GetTemperature()
    add_temperatures_to_lists(temp_A, temp_B)
    return temp_A, temp_B
    

def scan_pressure():
    global press_sensor, press_sensor_enabled
    try:
        press = press_sensor.read_pressure()
        pressure_val[0] = press
        return press
    except Exception as e:
        press_sensor_enabled = False
        pressure_val[0] = None
        print(e)
        print('Pressure sensor connection was lost')
        return None


def try_press_sensor():
    global press_sensor, press_sensor_enabled
    if not press_sensor_enabled:
        return
    try:
        press_sensor = ThyracontVSM(device_num=1)
        press_sensor = press_sensor
        press_sensor_enabled = True
    except ValueError:
        press_sensor_enabled = False
        pressure_val = [None]

def logging_thread_proc():
    ls = LakeShore335(device_num=12, control_channel='A', heater_channel=1, mode='passive')
    try_press_sensor()
    if not press_sensor_enabled:
        print('Pressure sensor was not detected')

    temp_A, temp_B = scan_temperatures(ls)
    press = scan_pressure()
    perform_logging_record(temp_A, temp_B, press)

    overseer_authorize(ls)

    time_start = time.time()
    while not event_exit.is_set():
        time_now = time.time()
        temp_A, temp_B = scan_temperatures(ls)
        press = scan_pressure()
        if time_now - time_start >= 30:
            check_day_change()
            
            perform_logging_record(temp_A, temp_B, press)
            time_start = time_now
        time.sleep(5)
        
        
# periodically check whether is pressure sensor connected
def press_sensor_check_thread_proc():
    while not event_exit.is_set():
        if not press_sensor_enabled:
            try_press_sensor()
        time.sleep(30)


def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item


def get_bot_login_password():
    try:
        with open(auth_file_name, 'r') as f:
            for i, line in enumerate(f):
                if i == 0:
                    login = line.strip()
                elif i == 1:
                    password = line.strip()
        return login, password
    except Exception as e:
        print('Cannot authorize in Overseer bot, invalid credentials file')
        return "", ""


def overseer_authorize(lakeshore):
    login, password = get_bot_login_password()
    if len(login) == 0:
        return
    bot = ARS_4K_slave(login, password, 'triangle.enricherclub.com', 23137,
                       last_temps_A, last_temps_B, temp_buffer_size, pressure_val)
    bot.launch()

class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self):
        super(TaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        # create_menu_item(menu, 'Say Hello', self.on_hello)
        # menu.AppendSeparator()
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

    def set_icon(self, icon_path):
        icon = wx.Icon(icon_path)
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_left_down(self, event):
        print('Tray icon was left-clicked.')

    '''def on_hello(self, event):
        print('Hello, world!')'''

    def on_exit(self, event):
        event_exit.set()
        wx.CallAfter(self.Destroy)


last_temps_A = []
last_temps_B = []
pressure_val = [None]

current_temp_logging_file = path.join(ensure_logging_directories(), temp_log_file_name)
current_press_logging_file = path.join(ensure_logging_directories(), press_log_file_name)
event_exit = threading.Event()
log_thread = threading.Thread(target=logging_thread_proc)
log_thread.start()
press_sensor_check_thread = threading.Thread(target=press_sensor_check_thread_proc)
press_sensor_check_thread.start()
app = wx.App()
TaskBarIcon()
app.MainLoop()
event_exit.set()

