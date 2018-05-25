import os
import sys

import numpy as np
import wx

from traits.api import on_trait_change, Bool, Undefined

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentVirtualTable
from ..utils.apple2util import to_560_pixels, hires_byte_order, hgr_offsets

from . import SegmentViewer
from . import actions as va
from . import bitmap2 as b

import logging
log = logging.getLogger(__name__)


class HiresLineRenderer(b.BitmapLineRenderer):
    @classmethod
    def get_image(cls, segment_viewer, bytes_per_row, nr, count, data, style):
        print("get_image", bytes_per_row, nr, count, data)
        return to_560_pixels(data)

    def draw_line(self, grid_control, dc, line_num, col, index, last_index):
        t = grid_control.table
        rect = self.col_to_rect(line_num, col)
        print("draw_line: col=%d indexes:%d-%d" % (col, index, last_index))
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(grid_control, dc, rect, data, style)

    def draw_grid(self, *args, **kwargs):
        cg.TableLineRenderer.draw_grid(self, *args, **kwargs)


class HiresTable(SegmentVirtualTable):
    def get_data_style_view(self, linked_base):
        byte_order = hires_byte_order(len(linked_base.segment))
        print(linked_base.segment, byte_order)
        self.hires_segment = linked_base.segment.create_subset(byte_order, "Hi-res", "Apple ][ Hi-res")
        data = self.hires_segment.data
        style = self.hires_segment.style
        return data, style

    def calc_num_cols(self):
        return 40

    def get_index_of_row(self, line):
        return hgr_offsets[line]

    def get_label_at_index(self, index):
        return(str(index // 40))


class HiresGridControl(b.BitmapGridControl):
    default_table_cls = HiresTable

    def set_viewer_defaults(self):
        self.items_per_row = 40
        self.zoom = 2

    @property
    def bitmap_renderer(self):
        return HiresLineRenderer

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
