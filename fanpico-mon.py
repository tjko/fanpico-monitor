#!/usr/bin/env python3
#
# fanpico_mon.py
#
#
# Copyright (C) 2023 Timo Kokkonen <tjko@iki.fi>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import os
import logging as log
import threading
import copy
import time
import re
import argparse
import configparser
import tkinter as tk
import customtkinter as ctk
from PIL import Image
# from typing import Union, Tuple, Optional

program_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, program_dir + "/scpi_lite")

import scpi_lite
from gui.ctk_dialog import CTkDialog
from gui.edit_unit import EditUnitWindow
from gui.about import AboutWindow
from gui.time_plot import TimePlot


class FanPico:
    def __init__(self, device, baudrate=115200, timeout=2, verbose=0):
        self.device = device
        self.baudrate = baudrate
        self.timeout = timeout
        self.verbose = verbose
        self.manufacturer = 'N/A'
        self.model = 'N/A'
        self.serial = 'N/A'
        self.firmware = 'N/A'
        self.status = {}
        self.mutex = threading.Lock()

        try:
            self.dev = scpi_lite.SCPIDevice(device, baudrate=baudrate, timeout=timeout, verbose=verbose)
        except scpi_lite.SCPIError as err:
            log.error("FanPico: Connection failed: %s", err)
            self.dev = None
            return
        self.manufacturer = self.dev.manufacturer
        self.model = self.dev.model
        self.serial = self.dev.serial
        self.firmware = self.dev.firmware

        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()
        log.info("FanPico: connected (%s, %s, v%s)", self.model, self.serial, self.firmware)

    def connected(self):
        if self.dev:
            return 1
        return 0

    def close(self):
        if self.dev:
            self.dev.close()

    def get_status(self):
        with self.mutex:
            res = copy.deepcopy(self.status)
        return res

    def worker(self):
        log.info("FanPico:worker(%s): started", self.device)
        while True:
            try:
                res = self.dev.query('R?', multi_line=True)
            except scpi_lite.SCPIError as err:
                log.info("FanPico:worker(%s): error: %s", self.device, err)
                return
            log.debug("FanPico:worker(%s): response length: %d", self.device, len(res))
            with self.mutex:
                for line in res.split('\n'):
                    fields = line.split(',')
                    if len(fields) > 1:
                        self.status[fields[0]] = fields[1:]
                self.status['last_update'] = int(time.time())
            time.sleep(2)
        log.info("FanPico:worker: finished %s", self.device)


class FanPicoFrame(ctk.CTkFrame):
    def __init__(self, master, name, device, baudrate, verbose=0):
        super().__init__(master)

        self.dev = FanPico(device, baudrate, verbose=verbose)
        self.name = name
        self.label_font = ctk.CTkFont(family='Helvetica', size=14, weight="bold")
        self.text_font = ctk.CTkFont(family='Courier', size=13, weight="bold")
        self.small_font = ctk.CTkFont(family='Helvetica', size=10)

        self.model = tk.StringVar(value=str(name + ': ' + self.dev.model + ' v' + self.dev.firmware + ' [' + self.dev.serial + ']'))

        self.model_label = ctk.CTkLabel(self, textvariable=self.model)
        self.w = 510
        self.h = 460
        self.cn = tk.Canvas(self, width=self.w, height=self.h, bg='gray50', borderwidth=-3, relief="flat")

        self.columnconfigure(0, weight=1)
        self.model_label.grid(row=0, column=0, padx=5, pady=(0, 0), sticky="w")
        self.cn.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="we")

        self.ci = {}
        self.initialized = 0
        self.data = {}
        self.tstamp = None
        self.status = None

        self.after(2000, self.update)
        self.after(3600000, self._purge_old_data)

    def destroy(self):
        log.info('FanPicoFrame:destroy %s', self.name)
        if self.dev:
            self.dev.close()
        super().destroy()

    def update(self):
        log.debug('FanPicoFrame:update %s', self.name)
        if self.dev.connected():
            self.status = self.dev.get_status()
            if 'last_update' in self.status:
                for k, v in self.status.items():
                    if k.startswith('fan'):
                        self.data.setdefault(k, {})[self.status['last_update']] = v[3]
                    if k.startswith('mbfan'):
                        self.data.setdefault(k, {})[self.status['last_update']] = v[3]
                    if k.startswith('sensor'):
                        self.data.setdefault(k, {})[self.status['last_update']] = v[1]
                if not self.initialized:
                    self._populate_canvas()
                self._update_canvas()
                self.after(1000, self.update)

    def _purge_old_data(self):
        purge_t = int(time.time()) - 360
        for k, v in self.data.items():
            a = [i for i in v.keys() if i < purge_t]
            if len(a) > 0:
                log.debug("purging old data %s: %d entries", k, len(a))
                for k in a:
                    del v[k]
        self.after(3600000, self._purge_old_data)

    def _populate_canvas(self):
        spacing = 30
        self.initialized = 1
        if log.getLogger().isEnabledFor(log.DEBUG):
            self.tstamp = self.cn.create_text(5, self.h - 10 , text='', font=self.small_font, fill='black', anchor="nw")
        count = 0
        for k, v in sorted(self.status.items()):
            #log.info("item='%s': %s", k, v)
            match = re.search(r"^(\S+)(\d+)$", k)
            if match:
                group = match[1]
                # num = int(match[2])
                line = count * spacing + 10
                count += 1
                if group == "fan" or group == "mbfan":
                    self.ci.setdefault(group, {}).setdefault(k, {})['label'] = self.cn.create_text(5,
                                                    line, text=k, font=self.small_font, fill='gray30', anchor="nw")
                    self.ci.setdefault(group, {}).setdefault(k, {})['name'] = self.cn.create_text(50,
                                                    line, text=v[0].strip('"'), font=self.label_font, fill='black', anchor="nw")
                    self.ci.setdefault(group, {}).setdefault(k, {})['pwm'] = self.cn.create_text(200, line + 3, text="",
                                                                                font=self.text_font, fill='black', anchor="nw")
                    self.ci.setdefault(group, {}).setdefault(k, {})['rpm'] = self.cn.create_text(250, line + 3, text="",
                                                                     font=self.text_font, fill='black', anchor="nw")
                    p = TimePlot(self.cn, self.data[k], width=150, height=spacing-5, bd=-3, bg='gray50', color='#2cc985', t_range=60)
                    self.ci[group][k]['plot'] = self.cn.create_window(350, line-7, anchor="nw", window=p, width=150, height=spacing-5)
                    self.ci[group][k]['plot_obj'] = p
                if group == "sensor":
                    self.ci.setdefault(group, {}).setdefault(k, {})['label'] = self.cn.create_text(5, line, text=k,
                                                                     font=self.small_font, fill='gray30', anchor="nw")
                    self.ci.setdefault(group, {}).setdefault(k, {})['name'] = self.cn.create_text(50, line, text=v[0].strip('"'),
                                                                     font=self.label_font, fill='black', anchor="nw")
                    self.ci.setdefault(group, {}).setdefault(k, {})['temp'] = self.cn.create_text(250, line + 3, text="",
                                                                     font=self.text_font, fill='black', anchor="nw")
                    p = TimePlot(self.cn, self.data[k], width=151, height=spacing-5, bd=-3, bg='gray50', color='#2cc985', t_range=60)
                    self.ci[group][k]['plot'] = self.cn.create_window(350, line-7, anchor="nw", window=p, width=150, height=spacing-5)
                    self.ci[group][k]['plot_obj'] = p
                self.cn.create_line(5, line+20, self.w-5, line+20, fill='gray40')

    def _update_canvas(self):
        t = int(time.time())
        log.debug("update canvas %s", self.name)
        if self.tstamp:
            self.cn.itemconfigure(self.tstamp, text=f"{self.status['last_update']:.0f}")
        for fan in self.ci['fan']:
            v = self.status[fan]
            self.cn.itemconfigure(self.ci['fan'][fan]['pwm'], text=f"{float(v[3]):3.0f} %")
            self.cn.itemconfigure(self.ci['fan'][fan]['rpm'], text=f"{int(v[1]):6d} rpm")
            self.ci['fan'][fan]['plot_obj'].update_plot(t)
        for mbfan in self.ci['mbfan']:
            v = self.status[mbfan]
            self.cn.itemconfigure(self.ci['mbfan'][mbfan]['pwm'], text=f"{float(v[3]):3.0f} %")
            self.cn.itemconfigure(self.ci['mbfan'][mbfan]['rpm'], text=f"{int(v[1]):6d} rpm")
            self.ci['mbfan'][mbfan]['plot_obj'].update_plot(t)
        for sensor in self.ci['sensor']:
            v = self.status[sensor]
            self.cn.itemconfigure(self.ci['sensor'][sensor]['temp'], text=f"{float(v[1]):6.2f} C")
            self.ci['sensor'][sensor]['plot_obj'].update_plot(t)



class MonitorApp(ctk.CTk):
    w = 800
    h = 600
    program_dir = os.path.dirname(os.path.realpath(__file__))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.geometry(f"{self.w}x{self.h}")
        self.title("FanPico Monitor")

        log.info("Screen size: %dx%d", self.winfo_screenwidth(), self.winfo_screenheight())

        asset_path = "./assets"
        self.about_window = None
        self.devices = {}
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        #self.help_menu = tk.Menu(self.menubar, tearoff=0)
        #self.help_menu.add_command(label='Help')
        #self.help_menu.add_command(label='About...', command=self._about_menu)
        #self.menubar.add_cascade(label='Help', menu=self.help_menu)

        self.wm_iconbitmap(os.path.join(asset_path, "fanpico.ico"))
        self.iconphoto(True, tk.PhotoImage(file=os.path.join(asset_path, "fanpico-logo-color.png")))

        self.app_logo = ctk.CTkImage(Image.open(os.path.join(asset_path, "fanpico-logo-color.png")),
                                     size=(64, 64))
        self.add_icon_image = ctk.CTkImage(light_image=Image.open(os.path.join(asset_path, "plus-circle_light.png")),
                                           dark_image=Image.open(os.path.join(asset_path, "plus-circle_dark.png")),
                                           size=(20, 20))
        self.del_icon_image = ctk.CTkImage(light_image=Image.open(os.path.join(asset_path, "trash_light.png")),
                                           dark_image=Image.open(os.path.join(asset_path, "trash_dark.png")),
                                           size=(20, 20))
        self.edit_icon_image = ctk.CTkImage(light_image=Image.open(os.path.join(asset_path, "settings_light.png")),
                                            dark_image=Image.open(os.path.join(asset_path, "settings_dark.png")),
                                            size=(20, 20))
        self.power_icon_image = ctk.CTkImage(light_image=Image.open(os.path.join(asset_path, "power_light.png")),
                                             dark_image=Image.open(os.path.join(asset_path, "power_dark.png")),
                                             size=(20, 20))
        self.info_icon_image = ctk.CTkImage(light_image=Image.open(os.path.join(asset_path, "info_light.png")),
                                            dark_image=Image.open(os.path.join(asset_path, "info_dark.png")),
                                            size=(20, 20))

        self.app_logo = ctk.CTkLabel(self, text='FanPico Monitor',
                                     font=ctk.CTkFont(size=15, weight='bold'),
                                     image=self.app_logo,
                                     compound='left')

        # frame for list of units...
        self.unit_frame = ctk.CTkFrame(self)
        self.add_button = ctk.CTkButton(self.unit_frame, text="", width=30,
                                        fg_color='transparent',
                                        command=self.__add_unit,
                                        image=self.add_icon_image)
        self.edit_button = ctk.CTkButton(self.unit_frame, text="", width=30,
                                        fg_color='transparent',
                                         command=self.__edit_unit,
                                         image=self.edit_icon_image)
        self.del_button = ctk.CTkButton(self.unit_frame, text="", width=30,
                                        fg_color='transparent',
                                        command=self.__del_unit,
                                        image=self.del_icon_image)
        self.unitnames = tk.StringVar(value=config.sections())
        self.unit_list = tk.Listbox(self.unit_frame,
                                    listvariable=self.unitnames,
                                    height=5, selectmode='browse',
                                    bd=0, selectborderwidth=0,
                                    activestyle='none', relief='flat',
                                    bg='Gray50', selectbackground='#2CC985',
                                    font=ctk.CTkFont(size=15, slant='roman'))
        self.unit_list.selection_set(0)
        self.unit_list.bind('<<ListboxSelect>>', self.__unit_select)
        self.add_button.grid(row=1, column=0, padx=5, pady=5)
        self.edit_button.grid(row=1, column=1, padx=5, pady=5)
        self.del_button.grid(row=1, column=2, padx=5, pady=5)
        self.unit_list.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        self.button_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.exit_button = ctk.CTkButton(self.button_frame, text="", width=30,
                                         image=self.power_icon_image,
                                         fg_color='transparent',
                                         command=self.exit_event)

        self.info_button = ctk.CTkButton(self.button_frame, text="", width=30,
                                         image=self.info_icon_image,
                                         fg_color='transparent',
                                         command=self._about_menu)

        self.appearance_mode_menu = ctk.CTkOptionMenu(self.button_frame, values=["Light", "Dark", "System"],
                                                      command=self.change_appearance_mode_event)
        self.appearance_mode_menu.set(config.get("DEFAULT", "theme"))
        self.exit_button.grid(row=0,column=2,padx=1,pady=10)
        self.info_button.grid(row=0,column=1,padx=1,pady=10)
        self.appearance_mode_menu.grid(row=0,column=0,padx=10,pady=10)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame_label = ctk.CTkLabel(self, text='Test')

        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)
        self.app_logo.grid(row=0, column=0, padx=10, pady=10)
        self.main_frame.grid(row=0, column=1, rowspan=5, padx=(0, 10), pady=(10, 10), sticky="nwse")
        self.unit_frame.grid(row=1, column=0, padx=10, pady=5)
        #self.appearance_mode_menu.grid(row=4, column=0, padx=10, pady=10, sticky="sw")
        #self.info_button.grid(row=3, column=0, padx=20, pady=10, sticky="se")
        #self.exit_button.grid(row=3, column=1, padx=20, pady=10, sticky="se")
        self.button_frame.grid(row=4, column=0, padx=5, pady=10, sticky='sw')

        self.after(100, self.unit_list.focus)
        self.after(1000, self.__unit_select)

    def exit_event(self):
        log.info("exit_event")
        self.destroy()

    def change_appearance_mode_event(self, new_appearance_mode):
        ctk.set_appearance_mode(new_appearance_mode)

    def select_unit(self, unit):
        units = config.sections()
        name = units[unit]
        log.debug("unit=%d, name='%s'", unit, name)
        if not name in self.devices:
            log.info("Connecting to device: %s", name)
            self.devices[name] = FanPicoFrame(self.main_frame, name, config.get(name, 'device', fallback=''),
                                                baudrate=config.get(name, 'baudrate', fallback=115200),
                                                verbose=0)
            self.devices[name].pack(padx=10, pady=10, side="top", fill="x")

    def __unit_select(self, event=None):
        if self.unit_list.curselection():
            unit = self.unit_list.curselection()[0]
            log.debug("select unit: %d", unit)
            self.select_unit(unit)

    def __add_unit(self):
        log.debug("add unit")
        l = 1 + len(list(config.sections()))
        while True:
            name = f"fanpico{l}"
            if not config.has_section(name):
                break
            l += 1
        res = EditUnitWindow(self, name, '', '115200').dialog()
        log.info(res)
        if len(res['values']) < 1:
            return

        name = res['values']['name']
        if config.has_section(name):
            log.debug("duplicate unit name: %s", name)
            CTkDialog(self, relative_position=(50, 50),
                      title='Duplicate unit name',
                      text='Unit with same name already existing unit: ' + res['values']['name'],
                      show_cancel_button=False).get_input()
        else:
            log.debug("add unit: %s", name)
            config[name] = res['values']
            units = config.sections()
            self.unitnames.set(units)
            self.unit_list.selection_clear(0, tk.END)
            self.unit_list.selection_set(0)
            self.unit_list.activate(0)
            save_config()

    def __edit_unit(self):
        if self.unit_list.curselection():
            unit = self.unit_list.curselection()[0]
            units = config.sections()
            log.debug("edit unit: %d", unit)
            name = units[unit]
            res = EditUnitWindow(self, name, config.get(name, 'device', fallback=''),
                                 config.get(name, 'speed', fallback='115200')).dialog()
            if len(res['changed']) > 0:
                log.debug("save changes to unit")
                if 'name' in res['changed']:
                    log.debug("rename unit")
                    if config.has_section(res['values']['name']):
                        CTkDialog(self, relative_position=(50, 50),
                                  title='Duplicate unit name',
                                  text='Cannot rename unit over existing unit: ' + res['values']['name'],
                                  show_cancel_button=False).get_input()
                        return
                    else:
                        # rename config section
                        config.remove_section(name)
                        name = res['values']['name']
                config[name] = res['values']
                units = config.sections()
                self.unitnames.set(units)
                save_config()

    def __del_unit(self):
        if self.unit_list.curselection():
            unit = self.unit_list.curselection()[0]
            units = config.sections()
            unit_name = units[unit]
            if CTkDialog(self, relative_position=(50, 75),
                         title='Remove unit?',
                         text='Remove ' + unit_name + '?').get_input():
                log.debug("delete unit: %d (%s) ", unit, unit_name)
                self.devices[unit_name].destroy()
                del self.devices[unit_name]
                config.remove_section(unit_name)
                units = config.sections()
                self.unitnames.set(units)
                self.unit_list.selection_clear(0, tk.END)
                self.unit_list.selection_set(0)
                self.unit_list.activate(0)
                save_config()

    def _about_menu(self):
        log.debug('display about window')
        if self.about_window:
            self.about_window.deiconify()
        else:
            self.about_window = AboutWindow(self, program_version)


def save_config():
    log.info("Saving config: " + config_filename)
    with open(config_filename, 'w') as configfile:
        config.write(configfile)


##############################################################################

program_version = '1.0.0beta'
config_filename = os.environ.get("HOME") + '/.fanpico-mon.ini'

config = configparser.ConfigParser(defaults={'theme': 'System'})

parser = argparse.ArgumentParser(description='FanPico Monitor')
parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose (debug) output')
parser.add_argument('--debug', action='store_true', help='enable debug in GUI')
args = parser.parse_args()

if args.debug:
    log_level = log.DEBUG
elif args.verbose:
    log_level = log.INFO
else:
    log_level = log.WARN
log.basicConfig(format="%(asctime)s: %(message)s", level=log_level)

if os.path.exists(config_filename):
    log.info("Main: reading config file: " + config_filename)
    config.read(config_filename)
else:
    log.warning("Main: No config file found: " + config_filename)

ctk.set_appearance_mode(config.get("DEFAULT", "theme"))
ctk.set_default_color_theme("green")


app = MonitorApp()
app.mainloop()


log.info("Main: program done.")

# eof :-)
