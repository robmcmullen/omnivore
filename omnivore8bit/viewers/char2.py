import os
import sys

import wx

from traits.api import on_trait_change, Bool, Undefined

from omnivore.utils.nputil import intscale
from omnivore.utils.wx import compactgrid as cg

from ..ui.segment_grid import SegmentGridControl, SegmentTable

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)


class AnticCharImageCache(cg.DrawTextImageCache):
    def __init__(self, segment_viewer):
        self.cache = {}
        self.segment_viewer = segment_viewer
        self.font = segment_viewer.current_antic_font
        self.font_renderer = segment_viewer.machine.font_renderer
        self.zoom_w = segment_viewer.control.zoom * self.font_renderer.scale_width
        self.zoom_h = segment_viewer.control.zoom * self.font_renderer.scale_height
        self.w = self.font_renderer.char_bit_width * self.zoom_w
        self.h = self.font_renderer.char_bit_height * self.zoom_h

    def draw_item(self, dc, rect, data, style):
        start = 0
        end = len(data)
        nr = 1
        data = data.reshape((nr, -1))
        style = style.reshape((nr, -1))
        array = self.font_renderer.get_image(self.segment_viewer, self.font, data, style, start, end, end, nr, start, end)
        width = array.shape[1]
        height = array.shape[0]
        if width > 0 and height > 0:
            array = intscale(array, self.zoom_h, self.zoom_w)
            image = wx.Image(array.shape[1], array.shape[0])
            image.SetData(array.tostring())
            bmp = wx.Bitmap(image)
            dc.DrawBitmap(bmp, rect.x, rect.y)


class AnticCharRenderer(cg.LineRenderer):
    default_image_cache = AnticCharImageCache

    def __init__(self, table, segment_viewer, image_cache=None):
        self.table = table
        image_cache = AnticCharImageCache(segment_viewer)
        cg.LineRenderer.__init__(self, image_cache.w, image_cache.h, table.items_per_row, segment_viewer.linked_base.cached_preferences, image_cache)

    # BaseLineRenderer interface

    def draw_line(self, dc, line_num, col, index, last_index):
        t = self.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(dc, rect, data, style)


class CharGridControl(SegmentGridControl):
    initial_zoom = 2

    def calc_line_renderer(self, table, view_params):
        if hasattr(self, 'segment_grid'):
            return AnticCharRenderer(table, self.segment_viewer)
        return SegmentGridControl.calc_line_renderer(self, table, view_params)

    def recalc_view(self):
        table = SegmentTable(self.segment_viewer.linked_base.segment)
        line_renderer = AnticCharRenderer(table, self.segment_viewer)
        log.debug("recalculating %s" % self)
        cg.HexGridWindow.recalc_view(self, table, self.segment_viewer.linked_base.cached_preferences, line_renderer)


class CharViewer(SegmentViewer):
    name = "char"

    pretty_name = "Character"

    has_font = True

    @classmethod
    def create_control(cls, parent, linked_base):
        return CharGridControl(parent, linked_base.segment, linked_base, linked_base.cached_preferences)

    @property
    def window_title(self):
        return self.machine.font_renderer.name + ", " + self.machine.font_mapping.name

    @on_trait_change('machine.font_change_event')
    def update_bitmap(self, evt):
        log.debug("CharViewer: machine font changed for %s" % self.control)
        if evt is not Undefined:
            self.control.recalc_view()
