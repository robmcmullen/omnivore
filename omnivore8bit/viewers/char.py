import os
import sys

import wx

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
        return self.linked_base.machine.font_renderer.name + ", " + self.linked_base.machine.font_mapping.name
