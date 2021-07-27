import threading
import os
from os import path
import threading
import time
import wx
import wx.adv

from Drivers.LakeShore335 import LakeShore335
from ARS_4K_remote import ARS_4K_slave

TRAY_TOOLTIP = 'ARS 4K cryostat logging tool'
TRAY_ICON = 'Monitor.ico'

log_file_name = 'Temperature.log'
auth_file_name = 'overseer_auth.dat'
temp_buffer_size = 12


def ensure_logging_directories():
    current_date = time.strftime('%Y-%m-%d')
    logging_dir = path.join(os.getcwd(), 'Logs', current_date)
    if not path.isdir(logging_dir):
        os.makedirs(logging_dir)
    return logging_dir


def check_day_change():
    global current_logging_file
    now = time.localtime()
    hours = now.tm_hour
    minutes = now.tm_min

    if hours == 0 and minutes == 0:
        current_logging_file = path.join(ensure_logging_directories(), log_file_name)


def add_temperatures_to_lists(temp_A, temp_B):
    last_temps_A.append(temp_A)
    last_temps_B.append(temp_B)
    if len(last_temps_A) > temp_buffer_size:
        last_temps_A.pop(0)
        last_temps_B.pop(0)


def perform_logging_record(temp_A, temp_B):
    time_to_write = time.strftime('%H-%M-%S')
    with open(current_logging_file, 'a') as f:
        f.write(f'{time_to_write} {temp_A} {temp_B}\n')


def scan_temperatures(device: LakeShore335):
    device.temp_channel = 'A'
    temp_A = device.GetTemperature()
    device.temp_channel = 'B'
    temp_B = device.GetTemperature()
    add_temperatures_to_lists(temp_A, temp_B)
    return temp_A, temp_B

def logging_thread_proc():
    ls = LakeShore335(device_num=12, control_channel='A', heater_channel=1, mode='passive')

    temp_A, temp_B = scan_temperatures(ls)
    perform_logging_record(temp_A, temp_B)

    overseer_authorize(ls)

    time_start = time.time()
    while not event_exit.is_set():
        time_now = time.time()
        temp_A, temp_B = scan_temperatures(ls)
        if time_now - time_start >= 30:
            check_day_change()
            perform_logging_record(temp_A, temp_B)
            time_start = time_now
        time.sleep(5)


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
                       last_temps_A, last_temps_B, temp_buffer_size)
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

current_logging_file = path.join(ensure_logging_directories(), log_file_name)
event_exit = threading.Event()
log_thread = threading.Thread(target=logging_thread_proc)
log_thread.start()
app = wx.App()
TaskBarIcon()
app.MainLoop()
event_exit.set()

