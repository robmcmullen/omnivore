import os
import sys

import wx

from traits.api import on_trait_change, Bool, Undefined
from atrcopy import selected_bit_mask

from omnivore_framework.utils.nputil import intscale
from omnivore_framework.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from . import SegmentViewer
from . import bitmap2 as b
from . import actions as va

import logging
log = logging.getLogger(__name__)


class PixelLineRenderer(b.BitmapLineRenderer):
    """The difference between this and the normal bitmap renderer is this one
    is selectable on the pixel level, rather than the byte level. Since the
    data is stored in bytes, the column range calculations are different.

    The desired column range might start and/or end at a pixel in the middle of
    a byte, so the ranges and drawing rectangles must be expanded to byte
    boundaries.
    """
    def calc_cell_size_in_pixels(self, grid_control):
        w = grid_control.zoom_w * grid_control.scale_width
        h = grid_control.zoom_h * grid_control.scale_height
        return w, h

    def col_to_rect(self, line_num, col):
        cell = self._col_to_cell[col]
        x, y = self.cell_to_pixel(line_num, cell)
        w = self.pixel_widths[col]
        rect = wx.Rect(x, y, w, self.h)
        return rect

    def calc_column_range(self, parent, line_num, first_byte, last_byte):
        t = parent.table
        row_start = (line_num * t.bytes_per_row) - t.start_offset
        index = row_start + first_byte
        if index < 0:
            first_byte -= index
            index = 0
        last_index = row_start + last_byte
        if last_index > t.last_valid_index:
            last_index = t.last_valid_index
        if index >= last_index:
            raise IndexError("No items in this line are in the visible scrolled region")
        return first_byte, index, last_index

    # BaseLineRenderer interface

    def draw_line(self, grid_control, dc, line_num, first_byte, index, last_index):
        t = grid_control.table
        rect = self.col_to_rect(line_num, first_byte * t.pixels_per_byte)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(grid_control, dc, rect, data, style)

    # fast BaseLineRenderer interface drawing entire grid at once

    def add_regular_selection(self, caret, style_per_pixel, t, first_row, last_row, first_byte, last_byte):
        # some part of selection is visible
        start_row = caret.anchor_start[0] - first_row
        first_col = first_byte * t.pixels_per_byte
        last_col = last_byte * t.pixels_per_byte
        width = last_col - first_col
        if start_row < 0:
            start_row = 0
            start_col = 0
        else:
            start_col = max(caret.anchor_start[1] - first_col, 0)
        end_row = caret.anchor_end[0] - first_row
        if end_row >= last_row:
            end_row = last_row
            end_col = width
        else:
            end_col = min(caret.anchor_end[1] - first_col, width)

        start_index = start_row * width + start_col
        end_index = end_row * width + end_col + 1
        s1d = style_per_pixel.reshape(-1)
        print("OETUSHNTOEHUSROEHU selection", start_row, start_col, start_index, end_row, end_col, end_index, style_per_pixel.shape, s1d.shape)
        s1d[start_index:end_index] |= selected_bit_mask

    def add_rectangular_selection(self, caret, style_per_pixel, t, first_row, last_row, first_byte, last_byte):
        # some part of selection is visible
        start_row = max(caret.anchor_start[0] - first_row, 0)
        first_col = first_byte * t.pixels_per_byte
        left_col = max(caret.anchor_start[1] - first_col, 0)
        last_col = last_byte * t.pixels_per_byte
        right_col = min(caret.anchor_end[1] - first_col + 1, last_col - first_col + 1)
        end_row = min(caret.anchor_end[0] - first_row + 1, last_row - first_row + 1)
        s2d = style_per_pixel.reshape((-1, (last_byte - first_byte) * style_per_pixel.shape[-1]))
        print("OETUSHNTOEHUSROEHU rectangular selection", start_row, left_col, end_row, right_col, style_per_pixel.shape, s2d.shape)
        s2d[start_row:end_row, left_col:right_col] |= selected_bit_mask

    def draw_grid(self, grid_control, dc, first_row, visible_rows, first_cell, visible_cells):
        t = grid_control.table
        first_byte = first_cell // t.pixels_per_byte
        last_cell = min(first_cell + visible_cells + t.pixels_per_byte - 1, self.num_cells)
        last_byte = last_cell // t.pixels_per_byte
        last_row = min(first_row + visible_rows, t.num_rows)
        log.debug("draw_grid: rows:%d,%d (vis %d, num %d) cols:%d,%d" % (first_row, last_row, visible_rows, t.num_rows, first_byte, last_byte))

        ul_rect = self.col_to_rect(first_row, first_byte * t.pixels_per_byte)
        lr_rect = self.col_to_rect(last_row - 1, (last_byte * t.pixels_per_byte) - 1)
        frame_rect = wx.Rect(ul_rect.x, ul_rect.y, lr_rect.x - ul_rect.x + lr_rect.width, lr_rect.y - ul_rect.y + lr_rect.height)
        dc.SetClippingRegion(frame_rect)

        # only display complete rows
        nr = last_row - first_row
        if nr > 0:
            bytes_per_row = t.bytes_per_row
            nc = last_byte - first_byte
            first_index = first_row * bytes_per_row
            last_index = first_index + nr * bytes_per_row
            if last_index > t.last_valid_index:
                nr -= 1
                last_index = first_index + nr * bytes_per_row

        if nr > 0:
            log.debug(f"drawing rectangular grid: control={grid_control} bpr={bytes_per_row}, first,last={first_index},{last_index}, nr={nr}")
            data = t.data[first_index:last_index].reshape((nr, bytes_per_row))[0:nr,first_byte:last_byte].flatten()
            style = t.style[first_index:last_index].reshape((nr, bytes_per_row))[0:nr,first_byte:last_byte].flatten()
            if grid_control.segment_viewer.is_focused_viewer and grid_control.caret_handler.has_selection:
                style_per_pixel = (grid_control.bitmap_renderer.calc_style_per_pixel(style))
                style_per_pixel &= 0xff ^ selected_bit_mask
                byte_width = last_byte - first_byte
                for caret in grid_control.caret_handler.carets_with_selection:
                    if caret.anchor_start[0] >= last_row or caret.anchor_end[0] < first_row:
                        continue
                    else:
                        if caret.rectangular or True:
                            self.add_rectangular_selection(caret, style_per_pixel, t, first_row, last_row, first_byte, last_byte)
                        else:
                            self.add_regular_selection(caret, style_per_pixel, t, first_row, last_row, first_byte, last_byte)

                style = None
            else:
                style_per_pixel = None
            print("OETHUSNOEUNOEU style", style.shape if style is not None else None, "style_per_pixel", style_per_pixel.shape if style_per_pixel is not None else None)

            # get_image(cls, machine, antic_font, byte_values, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols):

            array = grid_control.bitmap_renderer.get_image(grid_control.segment_viewer, nc, nr, nc * nr, data, style, style_per_pixel=style_per_pixel)
            width = array.shape[1]
            height = array.shape[0]
            if width > 0 and height > 0:
                array = intscale(array, grid_control.zoom_h, grid_control.zoom_w)
                #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
                image = wx.Image(array.shape[1], array.shape[0])
                image.SetData(array.tobytes())
                bmp = wx.Bitmap(image)
                dc.DrawBitmap(bmp, frame_rect.x, frame_rect.y)


class PixelTable(SegmentTable):
    def __init__(self, linked_base, bytes_per_row, pixels_per_byte):
        self.pixels_per_byte = pixels_per_byte
        self.bytes_per_row = bytes_per_row
        SegmentTable.__init__(self, linked_base, bytes_per_row * pixels_per_byte)

    def calc_num_rows(self):
        return ((self.start_offset + len(self.data) - 1) // self.bytes_per_row) + 1

    def get_label_at_index(self, index):
        # Can't just return hex value of index because some segments (like the
        # raw sector segment) use different labels
        return self.segment.label(index // self.bytes_per_row, True)

    def get_index_range(self, row, col):
        """Get the byte offset from start of file given row, col
        position.
        """
        byte_index = col // self.pixels_per_byte
        index = self.clamp_index(row * self.bytes_per_row + byte_index - self.start_offset)
        if index >= self.last_valid_index:
            index = self.last_valid_index - 1
        if index < 0:
            index = 0
        return index, index + 1

    def get_index_of_row(self, line):
        return (line * self.bytes_per_row) - self.start_offset

    def index_to_row_col(self, index):
        r, byte_index = divmod(index + self.start_offset, self.bytes_per_row)
        c = byte_index * self.pixels_per_byte
        print("OEHURSOEHURSOHEUSR", index, r, byte_index, c)
        return r, c


class PixelGridControl(b.BitmapGridControl):
    default_table_cls = PixelTable

    def set_viewer_defaults(self):
        self.bytes_per_row = 7
        self.items_per_row = 8  # 1 byte per pixel fallback
        self.zoom = 2

    def calc_default_table(self, linked_base):
        if hasattr(self, 'segment_viewer'):
            p = self.pixels_per_byte
        else:
            p = 1
        print("OTNEUHSNTOEHSUOEHU", self.items_per_row, p)
        return self.default_table_cls(linked_base, self.items_per_row // p, p)

    def calc_line_renderer(self):
        if hasattr(self, 'segment_viewer'):
            self.items_per_row = self.bytes_per_row * self.pixels_per_byte
            return PixelLineRenderer(self)
        return SegmentGridControl.calc_line_renderer(self)


class PixelViewer(SegmentViewer):
    name = "pixel"

    pretty_name = "Pixel Array"

    control_cls = PixelGridControl

    has_bitmap = True

    has_colors = True

    has_width = True

    width_text = "bitmap width in pixels"

    has_zoom = True

    zoom_text = "bitmap zoom factor"

    @property
    def window_title(self):
        return "Pixels: " + self.control.bitmap_renderer.name

    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self, evt):
        log.debug("BitmapViewer: machine bitmap changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
            self.linked_base.editor.update_pane_names()

    def validate_width(self, width):
        return self.machine.bitmap_renderer.validate_bytes_per_row(width)

    def recalc_data_model(self):
        self.control.recalc_view()
