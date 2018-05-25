import os
import sys

import wx

from traits.api import on_trait_change, Bool, Undefined

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentVirtualTable
from ..utils.apple2util import to_560_pixels, hires_data_view

from . import SegmentViewer
from . import actions as va
from . import bitmap2 as b

import logging
log = logging.getLogger(__name__)


class HiresLineRenderer(b.BitmapLineRenderer):
    @classmethod
    def get_image(cls, segment_viewer, bytes_per_row, nr, count, data, style):
        return to_560_pixels(data)


class HiresTable(SegmentVirtualTable):
    def get_data_style_view(self, linked_base):
        data = hires_data_view(linked_base.segment.data)
        style = np.zeros(8192, dtype=np.uint8)
        return data, style

    def calc_num_cols(self):
        return 560


class HiresGridControl(b.BitmapGridControl):
    default_table_cls = HiresTable

    def set_viewer_defaults(self):
        self.items_per_row = 560
        self.zoom = 2

    @property
    def bitmap_renderer(self):
        return hires_renderer

    @property
    def pixels_per_byte(self):
        return 7 * 2  # doubling horizontal res for half pixel shifts

    @property
    def scale_width(self):
        return 1

    @property
    def scale_height(self):
        return 2

    def calc_line_renderer(self):
        if hasattr(self, 'segment_viewer'):
            return HiresLineRenderer(self, self.segment_viewer)
        return SegmentGridControl.calc_line_renderer(self)

    def get_extra_actions(self):
        actions = [None, va.BitmapZoomAction]
        return actions


class HiresViewer(b.BitmapViewer):
    name = "hires"

    pretty_name = "Apple ][ Hi-res"

    control_cls = HiresGridControl

    has_bitmap = True

    has_colors = True

    has_width = False

    has_zoom = True

    zoom_text = "bitmap zoom factor"

    @property
    def window_title(self):
        return self.pretty_name

    def validate_width(self, width):
        return 560
