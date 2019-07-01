import os
import sys

import numpy as np
import wx

from atrip import Segment, style_bits

from sawx.utils.nputil import intscale
from sawx.ui import compactgrid as cg

from ..arch import colors
from ..ui.segment_grid import SegmentGridControl, SegmentVirtualTable
from ..utils import apple2util as a2
from ..editors.linked_base import LinkedBase

from ..viewer import SegmentViewer
from . import bitmap as b
from . import char as c

import logging
log = logging.getLogger(__name__)


class HiresLineRenderer(b.BitmapLineRenderer):
    @classmethod
    def get_image(cls, segment_viewer, bytes_per_row, nr, count, data, style):
        log.debug(f"get_image {bytes_per_row} {nr} {count} {data}")
        subset_count = 14 * len(data)
        bw = np.empty(subset_count, dtype=np.uint8)
        a2.to_560_bw_pixels(data, bw)
        h_colors = colors.get_blended_color_registers([(0, 0, 0), (255, 255, 255)], segment_viewer.preferences.highlight_background_color)
        style_per_pixel = np.repeat(style, 14)

        background = (bw == 0)
        color1 = (bw == 1)
        highlight = (style_per_pixel & style_bits.selected_bit_mask) == style_bits.selected_bit_mask
        rgb = np.empty([1, subset_count, 3], dtype=np.uint8)
        rgb[0,background & highlight] = h_colors[0]
        rgb[0,background & np.logical_not(highlight)] = (0, 0, 0)
        rgb[0,color1 & highlight] = h_colors[1]
        rgb[0,color1 & np.logical_not(highlight)] = (255, 255, 255)

        return rgb

    def draw_line(self, grid_control, dc, line_num, col, index, last_index):
        t = grid_control.table
        rect = self.col_to_rect(line_num, col)
        log.debug(f"draw_line: table={t} col={col} indexes:{index}-{last_index}")
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(grid_control, dc, rect, data, style)

    def draw_grid(self, parent, dc, *args, **kwargs):
        try:
            cg.TableLineRenderer.draw_grid(self, parent, dc, *args, **kwargs)
        except IndexError as e:
            log.warning("Index error in draw_grid; likely attempted to render grid on hidden index")


class HiresTable(SegmentVirtualTable):
    row_offset_for_line = a2.hgr_offsets
    segment_name = "Hi-res"
    segment_ui_name = "Apple ][ Hi-res"

    def get_data_style_view(self, linked_base):
        s = linked_base.segment
        byte_order = self.calc_byte_order(s)
        self.apple2_segment = Segment(s, byte_order, name=self.segment_name, verbose_name=self.segment_ui_name)
        data = self.apple2_segment.data
        style = self.apple2_segment.style
        return data, style

    @property
    def segment(self):
        return self.apple2_segment

    def calc_byte_order(self, segment):
        byte_order = a2.hires_byte_order(len(segment))
        return byte_order[0:len(segment)]

    def calc_num_cols(self):
        return 40


class HiresGridControl(b.BitmapGridControl):
    default_table_cls = HiresTable

    def set_viewer_defaults(self):
        self.items_per_row = 40
        self.zoom = 1

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

    ##### Keyboard handling

    def handle_char_move_left(self, evt, flags):
        self.segment_viewer.document.emulator.send_char(0x88)

    def handle_char_move_right(self, evt, flags):
        self.segment_viewer.document.emulator.send_char(0x95)

    def handle_char_move_up(self, evt, flags):
        self.segment_viewer.document.emulator.send_char(0x8b)

    def handle_char_move_down(self, evt, flags):
        self.segment_viewer.document.emulator.send_char(0x8a)


class AppleSegmentChecker:
    @classmethod
    def is_segment_specific_for_display(cls, segment):
        print(f"checking {segment} for origin {cls.segment_origin}: {segment.origin}, size {cls.segment_size}: {len(segment)}")
        return segment.origin == cls.segment_origin and len(segment) == cls.segment_size


class HiresPage1Viewer(AppleSegmentChecker, b.BitmapViewer):
    name = "hgr1"

    ui_name = "Apple ][ Hi-res Page 1"

    viewer_category = "Video"

    control_cls = HiresGridControl

    has_bitmap = True

    has_colors = True

    has_width = False

    has_zoom = True

    zoom_text = "bitmap zoom factor"

    segment_origin = 0x2000

    segment_size = 0x2000

    priority_refresh_frame_count = 1

    @property
    def window_title(self):
        return self.ui_name

    def validate_width(self, width):
        return 560

    def copy_data_from_selections(self):
        segment = self.control.table.segment
        indexes = segment.get_style_indexes(selected=True)
        data = segment[indexes].copy()
        return data

    @property
    def caret_conversion_segment(self):
        return self.control.table.segment


class HiresPage2Viewer(HiresPage1Viewer):
    name = "hgr2"

    ui_name = "Apple ][ Hi-res Page 2"

    segment_origin = 0x4000


class TextTable(HiresTable):
    row_offset_for_line = a2.gr_offsets
    segment_name = "Text"
    segment_ui_name = "Apple ][ Text"

    def calc_byte_order(self, linked_base):
        byte_order = a2.lores_byte_order(len(linked_base.segment))
        return byte_order


class TextGridControl(c.CharGridControl):
    default_table_cls = TextTable

    def set_viewer_defaults(self):
        c.CharGridControl.set_viewer_defaults(self)
        self.items_per_row = 40


class TextPage1Viewer(AppleSegmentChecker, c.CharViewer):
    name = "text1"

    ui_name = "Apple ][ Text Page 1"

    viewer_category = "Video"

    control_cls = TextGridControl

    segment_origin = 0x400

    segment_size = 0x400

    @property
    def window_title(self):
        return self.ui_name


class TextPage2Viewer(TextPage1Viewer):
    name = "text2"

    ui_name = "Apple ][ Text Page 2"

    segment_origin = 0x800
