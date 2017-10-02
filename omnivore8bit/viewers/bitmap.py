import os
import sys

import wx

from traits.api import on_trait_change, Bool

from omnivore8bit.ui.bitviewscroller import BitmapScroller
from commands import ChangeByteCommand

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)


class BitmapViewer(SegmentViewer):
    has_bitmap = Bool(True)

    @classmethod
    def create_control(cls, parent, linked_base):
        return BitmapScroller(parent, linked_base, size=(64,500))

    @property
    def window_title(self):
        return self.machine.bitmap_renderer.name

    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self):
        log.debug("BitmapViewer: machine bitmap changed!")
        self.control.recalc_view()
