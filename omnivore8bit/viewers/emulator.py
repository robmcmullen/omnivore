import os
import sys
from collections import namedtuple

import wx

from traits.api import on_trait_change, Bool, Undefined

import pyatari800 as a8
from omnivore8bit.byte_edit.segments import SegmentList
from . import SegmentViewer

import logging
log = logging.getLogger(__name__)


class EmulatorViewer(SegmentViewer):
    viewer_category = "Emulator"

    has_caret = False

    def use_default_view_params(self):
        pass

    def restore_view_params(self, params):
        pass

    def update_toolbar(self):
        pass

    def recalc_data_model(self):
        # self.control.recalc_view()
        self.control.Refresh()

    def recalc_view(self):
        # self.control.recalc_view()
        self.control.Refresh()


class Atari800Viewer(EmulatorViewer):
    name = "atari800"

    pretty_name = "Atari 800"

    @classmethod
    def create_control(cls, parent, linked_base, mdict):
        return a8.BitmapScreen(parent, linked_base.emulator)

    def show_caret(self, control, index, bit):
        pass

    ##### Spring Tab interface

    def get_notification_count(self):
        return 0
