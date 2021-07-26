import threading
import os
from os import path
import visa
import threading
import time
import wx
import wx.adv
from Drivers.LakeShore335 import LakeShore335


TRAY_TOOLTIP = 'ARS 4K cryostat logging tool'
TRAY_ICON = 'Monitor.ico'

log_file_name = 'Temperature.log'


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


def perform_logging_record(device: LakeShore335):
    device.temp_channel = 'A'
    temp_A = device.GetTemperature()
    device.temp_channel = 'B'
    temp_B = device.GetTemperature()
    time_to_write = time.strftime('%H-%M-%S')

    with open(current_logging_file, 'a') as f:
        f.write(f'{time_to_write} {temp_A} {temp_B}\n')


def logging_thread_proc():
    ls = LakeShore335(device_num=12, control_channel='A', heater_channel=1, mode='passive')
    time_start = time.time()
    perform_logging_record(ls)
    while not event_exit.is_set():
        time_now = time.time()
        if time_now - time_start >= 30:
            check_day_change()
            perform_logging_record(ls)
            time_start = time_now
        time.sleep(1)


def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item


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


current_logging_file = path.join(ensure_logging_directories(), log_file_name)
event_exit = threading.Event()
log_thread = threading.Thread(target=logging_thread_proc)
log_thread.start()
app = wx.App()
TaskBarIcon()
app.MainLoop()
event_exit.set()

