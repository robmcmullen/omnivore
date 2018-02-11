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
    def __init__(self, segment_viewer, bytes_per_row):
        self.cache = {}
        self.segment_viewer = segment_viewer
        self.bitmap_renderer = segment_viewer.machine.bitmap_renderer
        self.bytes_per_row = self.bitmap_renderer.validate_bytes_per_row(bytes_per_row)
        self.zoom_w = segment_viewer.control.zoom  # * self.bitmap_renderer.scale_width
        self.zoom_h = segment_viewer.control.zoom  # * self.bitmap_renderer.scale_height
        self.pixels_per_byte = self.bitmap_renderer.pixels_per_byte
        self.w = self.zoom_w * self.bitmap_renderer.scale_width * self.pixels_per_byte
        self.h = self.zoom_h * self.bitmap_renderer.scale_height

    def draw_item(self, dc, rect, data, style):
        start = 0
        end = len(data)
        nr = 1
        array = self.bitmap_renderer.get_image(self.segment_viewer, end, nr, end, data, style)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, self.zoom_h, self.zoom_w)
            #print("bitmap: %d,%d,3 after scaling: %s" % (height, width, str(array.shape)))
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tostring())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, rect.x, rect.y)


class BitmapRenderer(cg.TableLineRenderer):
    default_image_cache = BitmapImageCache

    def __init__(self, table, segment_viewer, image_cache=None):
        self.table = table
        image_cache = BitmapImageCache(segment_viewer, table.items_per_row)
        cg.LineRenderer.__init__(self, image_cache.w, image_cache.h, table.items_per_row, segment_viewer.linked_base.cached_preferences, image_cache)

    # BaseLineRenderer interface

    def draw_line(self, dc, line_num, col, index, last_index):
        t = self.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(dc, rect, data, style)


class BitmapGridControl(SegmentGridControl):
    initial_zoom = 2

    def set_viewer_defaults(self):
        old = self.items_per_row
        self.items_per_row = self.view_params.bitmap_width
        if self.items_per_row != old:
            self.recalc_view()

    def calc_default_table(self, segment, view_params):
        return SegmentTable(segment, view_params.bitmap_width)

    def calc_line_renderer(self, table, view_params):
        if hasattr(self, 'segment_grid'):
            return BitmapRenderer(table, self.segment_viewer)
        return SegmentGridControl.calc_line_renderer(self, table, view_params)

    def recalc_view(self):
        bytes_per_row = self.segment_viewer.machine.bitmap_renderer.validate_bytes_per_row(self.items_per_row)
        table = SegmentTable(self.segment_viewer.linked_base.segment, bytes_per_row)
        line_renderer = BitmapRenderer(table, self.segment_viewer)
        log.debug("recalculating %s" % self)
        cg.HexGridWindow.recalc_view(self, table, self.segment_viewer.linked_base.cached_preferences, line_renderer)

    def get_extra_actions(self):
        actions = [None, va.BitmapWidthAction, va.BitmapZoomAction]
        return actions


class BitmapViewer(SegmentViewer):
    name = "bitmap"

    pretty_name = "Bitmap"

    has_bitmap = True

    @classmethod
    def create_control(cls, parent, linked_base):
        return BitmapGridControl(parent, linked_base.segment, linked_base, linked_base.cached_preferences)

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
