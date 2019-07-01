import os
import sys

import wx
import numpy as np

from sawx.utils.nputil import intscale
from sawx.ui import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentVirtualTable
from ..viewer import SegmentViewer
from .emulator import EmulatorViewerMixin
from . import bitmap as b
from ..arch.bitmap_renderers import MemoryAccessMap

import logging
log = logging.getLogger(__name__)


class MemoryAccessTable(SegmentVirtualTable):
    segment_name = "memaccess"
    segment_ui_name = "Memory Access"

    def get_data_style_view(self, linked_base):
        self.access_segment = linked_base.document.find_segment_by_name("Memory Access")
        self.type_segment = linked_base.document.find_segment_by_name("Access Type")
        data = self.access_segment.data
        style = self.type_segment.data
        return data, style

    def calc_num_cols(self):
        return 256

    def get_label_at_index(self, index):
        return(str(hex(index)))


class MemoryAccessGridControl(b.BitmapGridControl):
    default_table_cls = MemoryAccessTable

    def set_viewer_defaults(self):
        self.items_per_row = 256
        self.zoom = 1

    @property
    def bitmap_renderer(self):
        return MemoryAccessMap()

    @property
    def pixels_per_byte(self):
        return 1

    @property
    def scale_width(self):
        return self.bitmap_renderer.scale_width

    @property
    def scale_height(self):
        return self.bitmap_renderer.scale_height


class MemoryAccessViewer(EmulatorViewerMixin, SegmentViewer):
    name = "mem"

    ui_name = "Memory Access"

    viewer_category = "Emulator"

    control_cls = MemoryAccessGridControl

    has_bitmap = True

    has_colors = True

    has_width = False

    has_zoom = True

    zoom_text = "bitmap zoom factor"

    priority_refresh_frame_count = 1

    def update_bitmap(self, evt):
        log.debug("BitmapViewer: machine bitmap changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
            self.linked_base.editor.update_pane_names()

    def validate_width(self, width):
        return 256

    def recalc_data_model(self):
        self.control.recalc_view()

    @property
    def current_frame_number(self):
        return self.linked_base.emulator.current_frame_number
