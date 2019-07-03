import os
import sys

import wx
import numpy as np

from sawx.utils.nputil import intscale
from sawx.ui import compactgrid as cg

from atrip.machines import atari8bit

from ..viewer import SegmentViewer

import logging
log = logging.getLogger(__name__)


class AnticColorViewer(SegmentViewer):
    has_colors = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._antic_color_registers = list(atari8bit.powerup_colors())
        self._color_standard_name = "NTSC"
        self._color_standard = None
        self._color_registers = None

    @property
    def antic_color_registers(self):
        return self._antic_color_registers

    @antic_color_registers.setter
    def antic_color_registers(self, value):
        baseline = list(atari8bit.powerup_colors())
        # need to operate on a copy of the colors to make sure we're not
        # changing some global value. Also force as python int so we're not
        # mixing numpy and python values.
        if len(value) == 5:
            baseline[4:9] = [int(i) for i in value]
        else:
            baseline[0:len(value)] = [int(i) for i in value]
        self._antic_color_registers = baseline
        self._color_registers = None
        print("ANTIC COLOR REGISTERS", self._antic_color_registers)
        self.colors_changed()
        self.graphics_properties_changed()

    @property
    def color_standard_name(self):
        return self._color_standard_name

    @color_standard_name.setter
    def color_standard_name(self, value):
        self._color_standard_name = value
        self._color_standard = None
        self._color_registers = None
        self.colors_changed()
        self.graphics_properties_changed()

    @property
    def color_standard(self):
        if self._color_standard is None:
            self._color_standard = atari8bit.valid_color_standards[self.color_standard_name]
        return self._color_standard

    @property
    def color_registers(self):
        if self._color_registers is None:
            self._color_registers = atari8bit.get_color_registers(self.antic_color_registers, self.color_standard)
        return self._color_registers

    def colors_changed(self):
        """Hook for subclasses that need to invalidate stuff when colors change
        """
        pass

    def graphics_properties_changed(self):
        print(f"graphics_properties_changed! std={self.color_standard_name}")
        self.control.recalc_view()
        self.control.refresh_view()
