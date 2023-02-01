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

import os
import sys
import logging
import threading
import time
import argparse
import serial
import serial.tools.list_ports
import configparser
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from pprint import pprint
from typing import Union, Tuple, Optional

from gui.ctk_dialog import CTkDialog
from gui.edit_unit import EditUnitWindow


class BackgroundFrame(ctk.CTkFrame):
    width = 0
    height = 0

    def __init__(self, master, *args, **kw):
        ctk.CTkFrame.__init__(self, master, *args, **kw)

        self.image = Image.open("./assets/bg.jpg")
        self.bg_image = ctk.CTkImage(self.image, size=(1024, 1024))
        self.bg_label = ctk.CTkLabel(self, image=self.bg_image, text="")
        self.bg_label.pack(fill='both',expand=True)
        self.bg_label.bind('<Configure>', self.__resize_bg)

    def __resize_bg(self, event):
        w = event.width
        h = event.height

        if (self.width != w or self.height != h):
            # print("resize - width:", w, " height:", h)
            self.bg_image = ctk.CTkImage(self.image, size=(w, h))
            self.bg_label.configure(image = self.bg_image)
            self.width = w
            self.height = h



class MonitorApp(ctk.CTk):
    w = 800
    h = 600
    program_dir = os.path.dirname(os.path.realpath(__file__))

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.geometry(f"{self.w}x{self.h}")
        self.title("FanPico Monitor")

        asset_path = "./assets"

        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar);

        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(label='Help' )
        self.help_menu.add_command(label='About...' )
        self.menubar.add_cascade(label='Help',menu=self.help_menu)

        self.background = BackgroundFrame(self)
        #self.background.grid(row=0,column=0,rowspan=5,columnspan=5,sticky=('N','S','E','W'))
        self.app_logo = ctk.CTkImage(Image.open(os.path.join(asset_path, "fanpico-logo-color.png")),
                                     size=(64,64))
        self.add_icon_image = ctk.CTkImage(light_image=Image.open(os.path.join(asset_path, "plus-circle_light.png")),
                                           dark_image=Image.open(os.path.join(asset_path, "plus-circle_dark.png")),
                                           size=(20,20))
        self.del_icon_image = ctk.CTkImage(light_image=Image.open(os.path.join(asset_path, "trash_light.png")),
                                           dark_image=Image.open(os.path.join(asset_path, "trash_dark.png")),
                                           size=(20,20))
        self.edit_icon_image = ctk.CTkImage(light_image=Image.open(os.path.join(asset_path, "settings_light.png")),
                                           dark_image=Image.open(os.path.join(asset_path, "settings_dark.png")),
                                           size=(20,20))

        self.app_logo = ctk.CTkLabel(self, text='FanPico Monitor',
                                     font=ctk.CTkFont(size=15, weight='bold'),
                                     image=self.app_logo,
                                     compound='left')
        self.app_logo.grid(row=0, column=0, padx=10, pady=10)

        self.unit_frame = ctk.CTkFrame(self)
        self.add_button = ctk.CTkButton(self.unit_frame, text="", width=40,
                                        command = self.__add_unit,
                                        image=self.add_icon_image)
        self.edit_button = ctk.CTkButton(self.unit_frame, text="", width=40,
                                         command = self.__edit_unit,
                                         image=self.edit_icon_image)
        self.del_button = ctk.CTkButton(self.unit_frame, text="", width=40,
                                        command = self.__del_unit,
                                        image=self.del_icon_image)
        self.unitnames = tk.StringVar(value=config.sections())
        self.unit_list = tk.Listbox(self.unit_frame,
                                    listvariable=self.unitnames,
                                    height=5, selectmode='browse',
                                    bd=0, selectborderwidth=0,
                                    activestyle='none', relief='sunken',
                                    bg='Gray75', selectbackground='#2CC985',
                                    font=ctk.CTkFont(size=15, slant='roman'))
        self.unit_list.selection_set(0)
        self.unit_list.bind('<<ListboxSelect>>', self.__unit_select)

        self.add_button.grid(row=1,column=0,padx=5,pady=5)
        self.edit_button.grid(row=1,column=1,padx=5,pady=5)
        self.del_button.grid(row=1,column=2,padx=5,pady=5)
        self.unit_list.grid(row=0,column=0,columnspan=3,padx=10,pady=10)

        self.unit_frame.grid(row=1,column=0,padx=10,pady=5,)

        self.exit_button = ctk.CTkButton(self, text="Quit", command=self.exit_event)
        self.exit_button.grid(row=2,column=0,padx=10,pady=10)

        self.appearance_mode_menu = ctk.CTkOptionMenu(self, values=["Light", "Dark", "System"],
                                                      command=self.change_appearance_mode_event)
        self.appearance_mode_menu.set(config.get("DEFAULT", "theme"))
        self.appearance_mode_menu.grid(row=4, column=0, padx=20, pady=20, sticky="sw")

        self.columnconfigure(4,weight=1)
        self.rowconfigure(3,weight=1)


    def exit_event(self):
        logging.info("exit_event")
        self.destroy()

    def change_appearance_mode_event(self, new_appearance_mode):
        ctk.set_appearance_mode(new_appearance_mode)

    def __unit_select(self, event):
        if self.unit_list.curselection():
            logging.debug("select unit: %d", self.unit_list.curselection()[0])

    def __add_unit(self):
        logging.debug("add unit")
        l = 1 + len(list(config.sections()))
        while True:
            name = f"fanpico{l}"
            if not config.has_section(name):
                break
            l += 1
        res = EditUnitWindow(name,'','115200').dialog()
        print(res)
        if len(res['values']) < 1:
            return

        name = res['values']['name']
        if config.has_section(name):
            logging.debug("duplicate unit name: %s", name)
            CTkDialog(title='Duplicate unit name',
                      text='Unit with same name already existing unit: ' + res['values']['name'],
                      show_cancel_button=False).get_input()
        else:
            logging.debug("add unit: %s",name)
            config[name] = res['values']
            units = config.sections()
            self.unitnames.set(units)
            self.unit_list.selection_clear(0,tk.END)
            self.unit_list.selection_set(0)
            self.unit_list.activate(0)
            save_config()

    def __edit_unit(self):
        if self.unit_list.curselection():
            unit = self.unit_list.curselection()[0]
            units = config.sections()
            logging.debug("edit unit: %d", unit)
            name = units[unit]
            res = EditUnitWindow(name, config.get(name,'device',fallback=''), config.get(name,'speed',fallback='115200')).dialog()
            if len(res['changed']) > 0:
                logging.debug("save changes to unit")
                if 'name' in res['changed']:
                    logging.debug("rename unit")
                    if config.has_section(res['values']['name']):
                        CTkDialog(title='Duplicate unit name', text='Cannot rename unit over existing unit: ' + res['values']['name'],
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
            #self.del_button.configure(state='disabled')
            unit = self.unit_list.curselection()[0]
            units = config.sections()
            unit_name = units[unit]
            if CTkDialog(title='Remove unit?', text='Remove ' + unit_name + '?').get_input():
                logging.debug("delete unit: %d (%s) ", unit, unit_name)
                config.remove_section(unit_name)
                units = config.sections()
                self.unitnames.set(units)
                self.unit_list.selection_clear(0,tk.END)
                self.unit_list.selection_set(0)
                self.unit_list.activate(0)
                save_config()



def save_config():
    logging.info("Saving config: " + config_filename)
    with open(config_filename, 'w') as configfile:
        config.write(configfile)


##############################################################################


program_dir = os.path.dirname(os.path.realpath(__file__))
config_filename = os.environ.get("HOME") + '/.fanpico-mon.ini'

config = configparser.ConfigParser(defaults={'theme':'System'})



parser = argparse.ArgumentParser(description='FanPico Monitor')
parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose (debug) output')
parser.add_argument('--debug', action='store_true', help='enable debug in GUI')
args = parser.parse_args()

logformat = "%(asctime)s: %(message)s"
loglevel = logging.WARN

if args.verbose:
    loglevel = logging.INFO

if args.debug:
    loglevel = logging.DEBUG

logging.basicConfig(format=logformat, level=loglevel)


if os.path.exists(config_filename):
    logging.info("Main: reading config file: " + config_filename)
    config.read(config_filename)
else:
    logging.warn("Main: No config file found: " + config_filename)


ctk.set_appearance_mode(config.get("DEFAULT", "theme"))
ctk.set_default_color_theme("green")

app = MonitorApp()
app.mainloop()

logging.info("Main: program done.")

# eof :-)
