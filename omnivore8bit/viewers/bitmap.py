import os
import sys

import wx

from omnivore8bit.ui.bitviewscroller import BitmapScroller
from commands import ChangeByteCommand

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)


class BitmapViewer(SegmentViewer):
    @classmethod
    def create_control(cls, parent, linked_base):
        return BitmapScroller(parent, linked_base, size=(64,500))

    @property
    def window_title(self):
        return self.machine.bitmap_renderer.name
