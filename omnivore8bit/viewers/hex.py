import os
import sys

import wx
import wx.grid as Grid

from traits.api import on_trait_change, Bool

from atrcopy import match_bit_mask, comment_bit_mask, user_bit_mask, selected_bit_mask, diff_bit_mask

from omnivore8bit.ui.bytegrid import ByteGridTable, ByteGrid

from actions import GotoIndexAction
from commands import ChangeByteCommand

from . import SegmentViewer

import logging
log = logging.getLogger(__name__)

# Grid tips:
# http://www.blog.pythonlibrary.org/2010/04/04/wxpython-grid-tips-and-tricks/


class ImageCache(object):
    def __init__(self, width=-1, height=-1):
        self.width = width
        self.height = height
        self.cache = {}

    def invalidate(self):
        self.cache = {}

    def set_colors(self, m):
        self.color = m.text_color
        self.diff_color = m.diff_text_color
        self.font = m.text_font
        self.selected_background = m.highlight_color
        self.selected_brush = wx.Brush(m.highlight_color, wx.SOLID)
        self.selected_pen = wx.Pen(m.highlight_color, 1, wx.SOLID)
        self.normal_background = m.background_color
        self.normal_brush = wx.Brush(m.background_color, wx.SOLID)
        self.normal_pen = wx.Pen(m.background_color, 1, wx.SOLID)
        self.data_background = m.data_color
        self.data_brush = wx.Brush(m.data_color, wx.SOLID)
        self.cursor_background = m.background_color
        self.cursor_brush = wx.Brush(m.background_color, wx.TRANSPARENT)
        self.cursor_pen = wx.Pen(m.unfocused_cursor_color, 2, wx.SOLID)
        self.match_background = m.match_background_color
        self.match_brush = wx.Brush(m.match_background_color, wx.SOLID)
        self.match_pen = wx.Pen(m.match_background_color, 1, wx.SOLID)
        self.comment_background = m.comment_background_color
        self.comment_brush = wx.Brush(m.comment_background_color, wx.SOLID)
        self.comment_pen = wx.Pen(m.comment_background_color, 1, wx.SOLID)

    def draw_blank(self, dc, rect):
        dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
        dc.SetPen(wx.Pen(wx.WHITE, 1, wx.SOLID))
        dc.DrawRectangle(rect)

    def draw_text(self, dc, rect, text, style):
        k = (text, style, rect.width, rect.height)
        try:
            bmp = self.cache[k]
        except KeyError:
            bmp = wx.Bitmap(rect.width, rect.height)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmp)
            r = wx.Rect(0, 0, rect.width, rect.height)
            self.draw_text_to_dc(mdc, r, text, style)
            del mdc  # force the bitmap painting by deleting the gc
            self.cache[k] = bmp
        dc.DrawBitmap(bmp, rect.x, rect.y)

    def draw_text_to_dc(self, dc, rect, text, style):
        if style & selected_bit_mask:
            dc.SetBrush(self.selected_brush)
            dc.SetPen(self.selected_pen)
            dc.SetTextBackground(self.selected_background)
        elif style & match_bit_mask:
            dc.SetPen(self.match_pen)
            dc.SetBrush(self.match_brush)
            dc.SetTextBackground(self.match_background)
        elif style & comment_bit_mask:
            dc.SetPen(self.comment_pen)
            dc.SetBrush(self.comment_brush)
            dc.SetTextBackground(self.comment_background)
        elif style & user_bit_mask:
            dc.SetPen(self.normal_pen)
            dc.SetBrush(self.data_brush)
            dc.SetTextBackground(self.data_background)
        else:
            dc.SetPen(self.normal_pen)
            dc.SetBrush(self.normal_brush)
            dc.SetTextBackground(self.normal_background)
        dc.SetBackgroundMode(wx.SOLID)
        dc.DrawRectangle(rect)
        if style & diff_bit_mask:
            dc.SetTextForeground(self.diff_color)
        else:
            dc.SetTextForeground(self.color)
        dc.SetFont(self.font)
        dc.DrawText(text, rect.x+1, rect.y+1)


class CachingHexRenderer(Grid.GridCellRenderer):
    def __init__(self, machine, cache):
        """Render data in the specified color and font and fontsize"""
        Grid.GridCellRenderer.__init__(self)
        self.cache = cache
        cache.set_colors(machine)

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        table = grid.table
        index, _ = table.get_index_range(row, col)
        if not table.is_index_valid(index):
            self.cache.draw_blank(dc, rect)
        else:
            text, style = table.get_value_style(row, col)
            self.cache.draw_text(dc, rect, text, style)

            r, c = table.get_row_col(grid.linked_base.editor.cursor_index)
            if row == r and col == c:
                dc.SetPen(self.cache.cursor_pen)
                dc.SetBrush(self.cache.cursor_brush)
                x = rect.x+1
                if sys.platform == "darwin":
                    w = rect.width - 2
                    h = rect.height - 2
                else:
                    w = rect.width - 1
                    h = rect.height - 1
                dc.DrawRectangle(rect.x+1, rect.y+1, w, h)


class ByteTable(ByteGridTable):
    def __init__(self, linked_base, bytes_per_row=16):
        ByteGridTable.__init__(self, linked_base)

        self._debug=False
        self.bytes_per_row = bytes_per_row
        self._cols = self.bytes_per_row
        self._rows = 0
        self.start_offset = 0
        self.recalc_segment_info()

    def recalc_segment_info(self):
        self.set_display_format(self.linked_base)
        self.segment = segment = self.linked_base.segment
        self.start_offset = segment.start_addr & 0x0f
        log.debug("segment %s: rows=%d cols=%d len=%d" % (segment, self._rows, self.bytes_per_row, len(segment)))

    def get_data_rows(self):
        return ((self.start_offset + len(self.linked_base.segment) - 1) / self.bytes_per_row) + 1

    def last_valid_index(self):
        return len(self.segment)

    def get_index_range(self, row, col):
        """Get the byte offset from start of file given row, col
        position.
        """
        index = row * self.bytes_per_row + col - self.start_offset
        return index, index + 1

    def get_row_col(self, index, col=0):
        return divmod(index + self.start_offset, self.bytes_per_row)

    def is_index_valid(self, index):
        return 0 <= index < len(self.segment)

    def get_addr_dest(self, r, c):
        index = self.get_index_range(r, c)[0]
        if self.is_index_valid(index):
            return index + self.segment.start_addr
        return -1

    def get_col_size(self, col, char_width=8):
        return 2 * char_width + self.extra_column_padding

    def get_value_style(self, row, col):
        i, _ = self.get_index_range(row, col)
        return self.fmt_hex2 % self.segment[i], self.segment.style[i]

    def get_label_at_index(self, index):
        # Can't just return hex value of index because some segments (like the
        # raw sector segment) use different labels
        return self.segment.label(index, self.fmt_hex1 == "%x")

    def GetRowLabelValue(self, row):
        return self.get_label_at_index(row*self.bytes_per_row - self.start_offset)

    def GetColLabelValue(self, col):
        return self.fmt_hex1 % col

    def SetValue(self, row, col, value):
        val=int(value,16)
        if val>=0 and val<256:
            i, _ = self.get_index_range(row, col)
            if self.is_index_valid(i):
                self.segment[i:i+1] = val
                return True
            log.debug('SetValue(%d, %d, "%s")=%d index %d out of range.' % (row, col, value, val, i))
            return False
        else:
            log.debug('SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value, val))
            return False

    def ResetViewProcessArgs(self, grid, *args):
        grid.image_cache.invalidate()
        self.recalc_segment_info()


class HexEditControl(ByteGrid):
    """
    View for editing in hexidecimal notation.
    """

    def __init__(self, parent, linked_base, **kwargs):
        """Create the HexEdit viewer
        """
        table = ByteTable(linked_base)
        ByteGrid.__init__(self, parent, linked_base, table, **kwargs)
        self.image_cache = ImageCache()

    def get_grid_cell_renderer(self, grid):
        return CachingHexRenderer(grid.segment_viewer.machine, self.image_cache)

    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.
        
        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        try:
            val = int(text,16)
            if val >= 0 and val < 256:
                start, end = self.table.get_index_range(row, col)
                if self.table.is_index_valid(start):
                    cmd = ChangeByteCommand(self.table.segment, start, end, val)
                    self.linked_base.editor.process_command(cmd)
        except ValueError:
            pass
        return False

    def get_goto_actions(self, r, c):
        actions = []
        addr_dest = self.table.get_addr_dest(r, c)
        actions.extend(self.linked_base.editor.get_goto_actions_other_segments(addr_dest))
        index, _ = self.table.get_index_range(r, c)
        actions.extend(self.linked_base.editor.get_goto_actions_same_byte(index))
        return actions

    def get_popup_actions(self, r, c, inside):
        if not inside:
            actions = []
        else:
            actions = self.get_goto_actions(r, c)
            if actions:
                actions.append(None)
        actions.extend(self.linked_base.editor.common_popup_actions())
        return actions


class HexEditViewer(SegmentViewer):
    name = "hex"

    pretty_name = "Hex"

    has_hex = Bool(True)

    @classmethod
    def create_control(cls, parent, linked_base):
        return HexEditControl(parent, linked_base)

    @property
    def window_title(self):
        return "Hex"

    def recalc_data_model(self):
        """Rebuild the data model after a document formatting (or other
        structural change) or loading a new document.
        """
        self.control.table.recalc_segment_info()
