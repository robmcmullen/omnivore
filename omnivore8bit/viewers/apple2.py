import os
import sys

import numpy as np
import wx

from traits.api import on_trait_change, Bool, Undefined

from atrcopy import match_bit_mask, comment_bit_mask, selected_bit_mask, diff_bit_mask, user_bit_mask, not_user_bit_mask

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg

from ..arch import colors
from ..ui.segment_grid import SegmentGridControl, SegmentVirtualTable
from ..utils.apple2util import to_560_bw_pixels, hires_byte_order, hgr_offsets

from . import SegmentViewer
from . import actions as va
from . import bitmap2 as b

import logging
log = logging.getLogger(__name__)


class HiresLineRenderer(b.BitmapLineRenderer):
    @classmethod
    def get_image(cls, segment_viewer, bytes_per_row, nr, count, data, style):
        print("get_image", bytes_per_row, nr, count, data)
        subset_count = 14 * len(data)
        bw = np.empty(subset_count, dtype=np.uint8)
        to_560_bw_pixels(data, bw)
        h_colors = colors.get_blended_color_registers([(0, 0, 0), (255, 255, 255)], segment_viewer.preferences.highlight_background_color)
        style_per_pixel = np.repeat(style, 14)

        background = (bw == 0)
        color1 = (bw == 1)
        highlight = (style_per_pixel & selected_bit_mask) == selected_bit_mask
        rgb = np.empty([1, subset_count, 3], dtype=np.uint8)
        rgb[0,background & highlight] = h_colors[0]
        rgb[0,background & np.logical_not(highlight)] = (0, 0, 0)
        rgb[0,color1 & highlight] = h_colors[1]
        rgb[0,color1 & np.logical_not(highlight)] = (255, 255, 255)

        return rgb

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
