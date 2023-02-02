#
# about.py - About dialog for FanPico Monitor
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
import tkinter as tk
import customtkinter as ctk
from PIL import Image


class BackgroundFrame(ctk.CTkFrame):
    width = 0
    height = 0

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.image = Image.open("./assets/bg.jpg")
        self.bg_image = ctk.CTkImage(self.image, size=(1024, 768))
        self.bg_label = ctk.CTkLabel(self, text="test")
        self.bg_label.grid(row=0,column=0,sticky="nwse")
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
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



class AboutWindow(ctk.CTkToplevel):
    def __init__(self, master, program_version, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.title('About FanPico Monitor')
        #self.geometry("500x400")
        self.lift()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        about_text='FanPico Monitor v' + program_version + '\nby\n Timo Kokkonen <tjko@iki.fi>'

        #self.bg_frame_img = BackgroundFrame(self)
        #self.bg_frame_img.grid(row=0,column=0,sticky=('nwse'))

        self.bg_frame = ctk.CTkFrame(self, border_width=4)

        self.bg_image = ctk.CTkImage(Image.open("./assets/fanpico.png"), size=(300, 200))
        self.bg_label = ctk.CTkLabel(self.bg_frame, text="", image=self.bg_image)
        self.label = ctk.CTkLabel(self.bg_frame, fg_color='transparent', corner_radius=0, text=about_text)

        self.label.grid(row=1,column=0,padx=15,pady=5,sticky="swe")
        self.bg_label.grid(row=2,column=0,padx=15,pady=5,sticky="nesw")

        self.bg_frame.rowconfigure(0,weight=1)
        self.bg_frame.rowconfigure(3,weight=1)
        self.bg_frame.columnconfigure(0,weight=1)
        self.bg_frame.grid(row=0,column=0,padx=5,pady=5,sticky="nwse")

        self.bind('<Button-1>', self._click_event)

        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        logging.debug("AboutWindow : window created")

    def _click_event(self, event):
        logging.info("AboutWindow : mouse click");
        self.withdraw()

    def _on_closing(self):
        logging.info("AboutWindow: window withdrawn")
        self.withdraw()


# eof :-)
