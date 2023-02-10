#
# time_plot.py - Widget for displaying RPM/PWM signal
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

import logging as log
import tkinter as tk
from typing import Tuple, Optional


class TimePlot(tk.Canvas):
    def __init__(self, master, data,
                 y_range: Optional[Tuple[int, int]] = (0, 100),
                 t_range: Optional[int] = 120,
                 width: Optional[int] = 300,
                 height: Optional[int] = 200,
                 color: str = 'red',
                 *args, **kwargs):
        super().__init__(master, width=width, height=height, *args, **kwargs)

        self.data = data
        self.y_range = y_range
        self.t_range = t_range
        self.color = color
        self.w = width
        self.h = height
        self.plot = None

    def update_plot(self, time):
        t = int(time)
        log.debug("TimePlot:update %d", t)
        t_min = t - self.t_range
        x_f = self.t_range / self.w
        y_f = (self.y_range[1] - self.y_range[0]) / (self.h - 1)
        sums = [0 for i in range(self.w + 1)]
        count = [0 for i in range(self.w + 1)]

        for k, v in self.data.items():
            if k >= t_min:
                slot = int((k - t_min) / x_f)
                # print(k,slot)
                sums[slot] += float(v)
                count[slot] += 1

        points = []
        for i in range(self.w):
            if count[i]:
                points.append(i)
                a = sums[i] / count[i]
                # if (a < self.y_range[0]):
                #     a=self.y_range[0]
                # if (a > self.y_range[1]):
                #     a=self.y_range[1]
                a -= self.y_range[0]
                points.append(self.h - int(a / y_f) - 1)

        if len(points) >= 4:
            if points[-2] < self.w - 1:
                points.extend((self.w - 1, points[-1]))
            # points.extend((self.w -1, self.h - 1, points[0], self.h - 1))
            if self.plot:
                self.coords(self.plot, points)
            else:
                self.plot = self.create_line(points, fill=self.color)


# eof :-)
