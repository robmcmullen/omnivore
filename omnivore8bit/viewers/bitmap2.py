import os
import sys

import wx

from traits.api import on_trait_change, Bool, Undefined

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from . import SegmentViewer
from . import actions as va

import logging
log = logging.getLogger(__name__)


class BitmapImageCache(cg.DrawTextImageCache):
    def draw_item(self, grid_control, dc, rect, data, style):
        start = 0
        end = len(data)
        nr = 1
        array = grid_control.bitmap_renderer.get_image(grid_control.segment_viewer, end, nr, end, data, style)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, grid_control.zoom_h * grid_control.scale_height, grid_control.zoom_w * grid_control.scale_width)
            #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tostring())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, rect.x, rect.y)


class BitmapLineRenderer(cg.TableLineRenderer):
    default_image_cache = BitmapImageCache

    def __init__(self, grid_control, image_cache=None):
        image_cache = BitmapImageCache()
        w = grid_control.zoom_w * grid_control.scale_width * grid_control.pixels_per_byte
        h = grid_control.zoom_h * grid_control.scale_height
        cg.LineRenderer.__init__(self, grid_control, w, h, grid_control.items_per_row, image_cache)

    # BaseLineRenderer interface

    def draw_line(self, grid_control, dc, line_num, col, index, last_index):
        t = grid_control.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(grid_control, dc, rect, data, style)

    # fast BaseLineRenderer interface drawing entire grid at once

    def draw_grid(self, grid_control, dc, first_row, visible_rows, first_cell, visible_cells):
        t = grid_control.table
        first_col = self.cell_to_col[first_cell]
        last_cell = min(first_cell + visible_cells, self.num_cells)
        last_col = self.cell_to_col[last_cell - 1] + 1
        last_row = min(first_row + visible_rows, t.num_rows)
        log.debug("draw_grid: rows:%d,%d (vis %d, num %d) cols:%d,%d" % (first_row, last_row, visible_rows, t.num_rows, first_col, last_col))

        ul_rect = self.col_to_rect(first_row, first_col)
        lr_rect = self.col_to_rect(last_row - 1, last_col - 1)
        frame_rect = wx.Rect(ul_rect.x, ul_rect.y, lr_rect.x - ul_rect.x + lr_rect.width, lr_rect.y - ul_rect.y + lr_rect.height)
        dc.SetClippingRegion(frame_rect)

        # First and last rows may not span entire width. Process those
        # separately
        #
        # First row may not have bytes at the beginning of the row if the start
        # offset is not zero
        if first_row == 0:
            try:
                col, index, last_index = self.calc_column_range(grid_control, first_row, first_col, last_col)
            except IndexError:
                pass  # skip lines with no visible cells
            else:
                self.draw_line(grid_control, dc, first_row, col, index, last_index)
            first_row += 1
            if first_row == last_row:
                return
            frame_rect.y += ul_rect.height

        # Last row may not have bytes at the end of the row
        if last_row == t.num_rows:
            try:
                col, index, last_index = self.calc_column_range(grid_control, last_row - 1, first_col, last_col)
            except IndexError:
                pass  # skip lines with no visible cells
            else:
                self.draw_line(grid_control, dc, last_row - 1, col, index, last_index)
            last_row -= 1

        bytes_per_row = t.items_per_row
        nr = last_row - first_row
        nc = last_col - first_col
        first_index = (first_row * bytes_per_row) - t.start_offset
        last_index = (last_row * bytes_per_row) - t.start_offset
        t = t
        if last_index > len(t.data):
            last_index = len(t.data)
            data = np.zeros((nr * bytes_per_row), dtype=np.uint8)
            data[0:last_index - first_index] = t.data[first_index:last_index]
            style = np.zeros((nr * bytes_per_row), dtype=np.uint8)
            style[0:last_index - first_index] = t.style[first_index:last_index]
        else:
            data = t.data[first_index:last_index]
            style = t.style[first_index:last_index]

        # get_image(cls, machine, antic_font, bytes, style, start_byte, end_byte, bytes_per_row, nr, start_col, visible_cols):

        array = grid_control.bitmap_renderer.get_image(grid_control.segment_viewer, bytes_per_row, nr, bytes_per_row * nr, data, style)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, grid_control.zoom_h, grid_control.zoom_w)
            #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tostring())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, frame_rect.x, frame_rect.y)


class BitmapGridControl(SegmentGridControl):
    def set_viewer_defaults(self):
        self.items_per_row = self.view_params.bitmap_width
        self.zoom = 2

    @property
    def bitmap_renderer(self):
        return self.segment_viewer.machine.bitmap_renderer

    @property
    def zoom_w(self):
        return self.zoom  # * self.bitmap_renderer.scale_width

    @property
    def zoom_h(self):
        return self.zoom  # * self.bitmap_renderer.scale_height

    @property
    def pixels_per_byte(self):
        return self.bitmap_renderer.pixels_per_byte

    @property
    def scale_width(self):
        return self.bitmap_renderer.scale_width

    @property
    def scale_height(self):
        return self.bitmap_renderer.scale_height

    def calc_line_renderer(self):
        if hasattr(self, 'segment_viewer'):
            return BitmapLineRenderer(self)
        return SegmentGridControl.calc_line_renderer(self)

    def verify_line_renderer(self):
        self.recalc_line_renderer()

    def get_extra_actions(self):
        actions = [None, va.BitmapWidthAction, va.BitmapZoomAction]
        return actions


class BitmapViewer(SegmentViewer):
    name = "bitmap"

    pretty_name = "Bitmap"

    control_cls = BitmapGridControl

    has_bitmap = True

    has_colors = True

    has_width = True

    width_text = "bitmap width in bytes"

    has_zoom = True

    zoom_text = "bitmap zoom factor"

    @property
    def window_title(self):
        return self.machine.bitmap_renderer.name

    @on_trait_change('machine.bitmap_shape_change_event,machine.bitmap_color_change_event')
    def update_bitmap(self, evt):
        log.debug("BitmapViewer: machine bitmap changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
            self.linked_base.editor.update_pane_names()

    def validate_width(self, width):
        return self.machine.bitmap_renderer.validate_bytes_per_row(width)


class MemoryMapViewer(BitmapViewer):
    name = "memmap"

    pretty_name = "Memory Page Map"
