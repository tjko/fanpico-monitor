#
# edit_unit.py
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

import logging
import serial.tools.list_ports
import tkinter as tk
import customtkinter as ctk


class EditUnitWindow(ctk.CTkToplevel):
    def __init__(self, master, name, device, speed):
        super().__init__(master)

        self.title('Edit unit: ' + name)
        self.lift()
        self.attributes("-topmost",True)
        self.protocol("WM_DELETE_WINDOW", self._close_event)
        self.resizable(False,False)
        self.grab_set()

        win_x = master.winfo_x() + 100
        win_y = master.winfo_y() + 100
        self.geometry(f"+{win_x}+{win_y}")

        serial_ports = []
        for s_port in serial.tools.list_ports.comports():
            port = s_port.name
            if port.startswith("COM"):
                serial_ports.append(port + ':')
            elif port.startswith("/"):
                serial_ports.append(port)
            else:
                serial_ports.append("/dev/" + port)

        self.result = { 'changed': [], 'values': {} }
        self.orig_name = name
        self.orig_device = device
        self.orig_speed = speed
        self.unit_name = tk.StringVar(value=name)
        self.speed = tk.StringVar(value=speed)
        if device:
            self.device = tk.StringVar(value=device)
        else:
            self.device = tk.StringVar(value=serial_ports[0])



        self._entry_label = ctk.CTkLabel(master=self, text='Device Name:')
        self._entry = ctk.CTkEntry(master=self, width=200, height=25,
                                   textvariable=self.unit_name)

        self._device_label = ctk.CTkLabel(master=self, text='Device Connection:')
        self._device = ctk.CTkComboBox(master=self,
                                       variable=self.device,
                                       width=300,
                                       values=serial_ports)

        self._speed_label = ctk.CTkLabel(master=self, text='Baud Rate (serial):')
        self._speed = ctk.CTkComboBox(master=self,
                                      variable=self.speed,
                                      width=150,
                                      values=["115200","57600","38400","19200","9600"])

        self._button_frame = ctk.CTkFrame(master=self,fg_color='transparent')
        self._ok_button = ctk.CTkButton(master=self._button_frame,
                                        text='OK',
                                        width=100,
                                        command=self._ok_event)
        self._cancel_button = ctk.CTkButton(master=self._button_frame,
                                            text='Cancel',
                                            width=100,
                                            command=self._cancel_event)
        self._ok_button.grid(row=0,column=0,padx=10,pady=10,sticky="e")
        self._cancel_button.grid(row=0,column=1,padx=10,pady=10, sticky="w")


        #self.columnconfigure(1, weight=1)
        #self.rowconfigure(1, weight=1)
        self._entry_label.grid(row=0,column=0,padx=5,pady=(5,0),sticky="w")
        self._entry.grid(row=1,column=0,padx=5,pady=(0,5), sticky="w")
        self._device_label.grid(row=2,column=0,padx=5,pady=(5,1), sticky="w")
        self._device.grid(row=3,column=0,padx=5,pady=(1,5), sticky="w")
        self._speed_label.grid(row=2,column=1,padx=5,pady=(5,1),sticky="w",)
        self._speed.grid(row=3,column=1,padx=5,pady=(1,5),sticky="w")
        self._button_frame.grid(row=4,column=0,columnspan=2)
        self.after(150, lambda: self._entry.focus())
        logging.debug("EditUnitWindow : created")



    def _ok_event(self, event=None):
        logging.info("EditUnitWindow : ok pressed")
        changed = []
        values = {}
        if self.orig_name != self.unit_name.get():
            changed.append('name')
        if self.orig_device != self.device.get():
            changed.append('device')
        if self.orig_speed != self.speed.get():
            changed.append('speed')
        values['name'] = self.unit_name.get()
        values['device'] = self.device.get()
        values['speed'] = self.speed.get()

        for field in values:
            if values[field] == '':
                CTkDialog(title='Missing Input',
                          text='Field ' + field + ' cannot be empty.',
                          show_cancel_button=False).get_input()
                return

        self.grab_release()
        self.destroy()
        self.result = { 'changed': changed, 'values': values }

    def _cancel_event(self, event=None):
        logging.info("EditUnitWindow : cancel pressed")
        self.grab_release()
        self.destroy()

    def _close_event(self, event=None):
        logging.info("EditUnitWindow : window closed")
        self.grab_release()
        self.destroy()

    def dialog(self):
        self.master.wait_window(self)
        self.master.lift()
        return self.result



# eof :-)
