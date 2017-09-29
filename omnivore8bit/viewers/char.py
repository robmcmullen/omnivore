import os
import sys

import wx

from traits.api import on_trait_change

from omnivore8bit.ui.bitviewscroller import FontMapScroller
from commands import ChangeByteCommand

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)


class CharViewer(SegmentViewer):
    @classmethod
    def create_control(cls, parent, linked_base):
        return FontMapScroller(parent, linked_base, size=(160,500), command=ChangeByteCommand)

    @property
    def window_title(self):
        return self.machine.font_renderer.name + ", " + self.machine.font_mapping.name

    @on_trait_change('machine.font_change_event')
    def update_bitmap(self):
        log.debug("BitmapViewer: machine font changed!")
        self.control.recalc_view()
