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
    def create(cls, parent, linked_base):
        control = BitmapScroller(parent, linked_base, size=(64,500))

        v = cls(linked_base=linked_base, control=control)
        return v
