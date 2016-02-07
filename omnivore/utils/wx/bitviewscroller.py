#-----------------------------------------------------------------------------
# Name:        bitviewscroller.py
# Purpose:     scrolling container for bit patterns
#
# Author:      Rob McMullen
#
# Created:     2014
# RCS-ID:      $Id: $
# Copyright:   (c) 2014 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""BitviewScroller -- a container for viewing bit patterns

"""

import os
import time

import numpy as np
import wx
import wx.lib.newevent

from pyface.action.api import Action
from pyface.tasks.action.api import EditorAction

from atrcopy import DefaultSegment

from omnivore.framework.actions import *
from omnivore.tasks.hex_edit.actions import *
import fonts

try:
    import bitviewscroller_speedups as speedups
except ImportError:
    speedups = None

import logging
log = logging.getLogger(__name__)

class BitviewEvent(wx.PyCommandEvent):
    """Event sent when a LayerControl is changed."""

    def __init__(self, eventType, id, byte, bit):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self.byte = byte
        self.bit = bit


class BitviewScroller(wx.ScrolledWindow):
    dbg_call_seq = 0
    
    def __init__(self, parent, task, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, -1, **kwargs)

        # Settings
        self.task = task
        self.editor = None
        self.segment = None
        self.background_color = None
        self.max_zoom = 16
        self.min_zoom = 1
        self.bytes_per_row = 1

        # internal storage
        self.start_addr = 0
        self.start_byte = None
        self.end_byte = None
        self.img = None
        self.scaled_bmp = None
        self.grid_width = 0
        self.grid_height = 0
        self.zoom = 5
        self.border_width = 1
        self.start_row = 0
        self.start_col = 0
        self.fully_visible_rows = 1
        self.fully_visible_cols = 1
        self.visible_rows = 1
        self.visible_cols = 1

        self.rect_select = False
        
        self.select_extend_mode = False
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)
        self.Bind(wx.EVT_SET_FOCUS, self.on_focus)
        self.Bind(wx.EVT_KILL_FOCUS, self.on_focus_lost)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)
        self.Bind(wx.EVT_CHAR, self.on_char)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
    
    def __repr__(self):
        return "<%s at 0x%x>" % (self.__class__.__name__, id(self))
    
    def is_ready_to_render(self):
        return self.editor is not None
    
    def set_task(self, task):
        self.task = task
    
    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.segment = editor.segment
            self.rect_select = editor.rect_select
            self.start_addr = editor.segment.start_addr
            self.match_color = self.editor.match_background_color
            self.comment_color = self.editor.comment_background_color
            self.background_color = self.editor.empty_color
            self.set_colors()
            self.set_font()
            self.update_bytes_per_row()
            self.update_zoom()
            self.set_scale()
    
    def refresh_view(self):
        editor = self.task.active_editor
        if editor is not None:
            if self.editor != editor:
                self.recalc_view()
            else:
                self.Refresh()
        
    def sync_settings(self):
        e = self.editor
        if e is not None:
            self.sync_to_editor(e)
    
    def sync_to_editor(self, e):
        pass

    def set_colors(self):
        pass
    
    def set_font(self):
        pass

    def zoom_in(self, zoom=1):
        self.set_zoom(self.zoom + zoom)
        self.set_scale()
        
    def zoom_out(self, zoom=1):
        self.set_zoom(self.zoom - zoom)
        self.set_scale()
    
    def set_zoom(self, zoom):
        if zoom > self.max_zoom:
            zoom = self.max_zoom
        elif zoom < self.min_zoom:
            zoom = self.min_zoom
        self.zoom = zoom
        self.sync_settings()
    
    def get_zoom_factors(self):
        return self.zoom, self.zoom

    def get_highlight_indexes(self):
        e = self.editor
        anchor_start, anchor_end = e.anchor_start_index, e.anchor_end_index
        r1 = c1 = r2 = c2 = -1
        if self.rect_select:
            anchor_start, anchor_end, (r1, c1), (r2, c2) = self.get_rect_indexes(anchor_start, anchor_end)
        elif anchor_start > anchor_end:
            anchor_start, anchor_end = anchor_end, anchor_start
        elif anchor_start == anchor_end:
            anchor_start = e.cursor_index
            anchor_end = anchor_start + 1
        return anchor_start, anchor_end, (r1, c1), (r2, c2)
    
    def get_rect_indexes(self, anchor_start, anchor_end):
        # determine row,col of upper left and lower right of selected
        # rectangle.  The values are inclusive, so ul=(0,0) and lr=(1,2)
        # is 2 rows and 3 columns.  Columns need to be adjusted slightly
        # depending on quadrant of selection because anchor indexes are
        # measured as cursor positions, that is: positions between the
        # bytes where as rect select needs to think of the selections as
        # on the byte positions themselves, not in between.
        bpr = self.bytes_per_row
        r1, c1 = divmod(anchor_start, bpr)
        r2, c2 = divmod(anchor_end, bpr)
        log.debug("rect select before:       anchors=%d,%d ul=%s lr=%s" % ( anchor_start, anchor_end, (r1, c1), (r2, c2)))
        if c1 >= c2:
            # start column is to the right of the end column so columns
            # need to be swapped
            if r1 >= r2:
                # start row is below end row, so rows swapped as well
                c1, c2 = c2, c1 + 1
                r1, r2 = r2, r1
            elif c2 == 0:
                # When the cursor is at the end of a line, anchor_end points
                # to the first character of the next line.  Handle this
                # special case by pointing to end of the previous line.
                c2 = bpr
                r2 -= 1
            else:
                c1, c2 = c2 - 1, c1 + 1
        else:
            # start column is to the left of the end column, so don't need
            # to swap columns
            if r1 > r2:
                # start row is below end row
                r1, r2 = r2, r1
                c2 += 1
        anchor_start = r1 * bpr + c1
        anchor_end = r2 * bpr + c2
        r2 += 1
        log.debug("rect select computations: anchors=%d,%d ul=%s lr=%s" % ( anchor_start, anchor_end, (r1, c1), (r2, c2)))
        return anchor_start, anchor_end, (r1, c1), (r2, c2)
    
    def get_image(self):
        raise NotImplementedError

    def copy_to_clipboard(self):
        """Copies current image to clipboard.

        Copies the current image, including scaling, zooming, etc. to
        the clipboard.
        """
        bmpdo = wx.BitmapDataObject(self.scaled_bmp)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(bmpdo)
            wx.TheClipboard.Close()

    def prepare_image(self):
        """Creates new image at specified zoom factor.

        Creates a new image that is to be used as the background of
        the scrolled bitmap.  Currently, actually creates the entire
        image, which could lead to memory problems if the image is
        really huge and the zoom factor is large.
        """
        if self.is_ready_to_render():
            self.calc_image_size()
            
            w, h = self.GetClientSizeTuple()
            dc = wx.MemoryDC()
            self.scaled_bmp = wx.EmptyBitmap(w, h)
            
            dc.SelectObject(self.scaled_bmp)
            dc.SetBackground(wx.Brush(self.background_color))
            dc.Clear()
            
            array = self.get_image()
            width = array.shape[1]
            height = array.shape[0]
            if width > 0 and height > 0:
                image = wx.EmptyImage(width, height)
                image.SetData(array.tostring())
                zw, zh = self.get_zoom_factors()
                image.Rescale(width * zw, height * zh)
                bmp = wx.BitmapFromImage(image)
                dc.DrawBitmap(bmp, 0, 0)
    
    def calc_image_size(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        self.start_row = y
        self.start_col = x
        
        # For proper buffered paiting, the visible_rows must include the
        # (possibly) partially obscured last row.  fully_visible_rows
        # indicates the number of rows without that last partially obscured
        # row (if it exists).
        self.fully_visible_rows = h / self.zoom
        self.fully_visible_cols = w / self.zoom
        self.visible_rows = ((h + self.zoom - 1) / self.zoom)
        self.visible_cols = ((w + self.zoom - 1) / self.zoom)
        log.debug("x, y, w, h, start, num: %s" % str([x, y, w, h, self.start_row, self.visible_rows]))

    def update_bytes_per_row(self):
        pass

    def update_zoom(self):
        pass

    def set_scale(self):
        """Creates new image at specified zoom factor.

        Creates a new image that is to be used as the background of
        the scrolled bitmap.  Currently, actually creates the entire
        image, which could lead to memory problems if the image is
        really huge and the zoom factor is large.
        """
        if self.segment is not None:
            self.calc_scale_from_bytes()
        else:
            self.grid_width = 10
            self.grid_height = 10
        log.debug("set_scale: %s" % str([self.grid_width, self.grid_height]))
        self.calc_scroll_params()
        self.Refresh()
    
    def calc_scale_from_bytes(self):
        self.total_rows = (len(self.segment) + self.bytes_per_row - 1) / self.bytes_per_row
        self.grid_width = int(8 * self.bytes_per_row) + (2 * self.border_width)
        self.grid_height = int(self.total_rows)
    
    def calc_scroll_params(self):
        self.SetVirtualSize((self.grid_width * self.zoom, self.grid_height * self.zoom))
        rate = int(self.zoom)
        if rate < 1:
            rate = 1
        self.SetScrollRate(rate, rate)

    def event_coords_to_byte(self, evt):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        raise NotImplementedError
    
    def byte_to_row_col(self, addr):
        r = addr // self.bytes_per_row
        c = addr - (r * self.bytes_per_row)
        return r, c
    
    def select_index(self, rel_pos):
        r, c = self.byte_to_row_col(rel_pos)
#        print "r, c, start, vis", r, c, self.start_row, self.fully_visible_rows
        last_row = self.start_row + self.fully_visible_rows - 1
        last_col = self.start_col + self.fully_visible_cols - 1
        
        update = False
        if r < self.start_row:
            # above current view
            update = True
        elif r >= last_row:
            # below last row
            last_scroll_row = self.total_rows - self.fully_visible_rows
            if r >= last_scroll_row:
                r = last_scroll_row
                update = True
            elif r >= self.fully_visible_rows:
                r = r - self.fully_visible_rows + 1
                update = True
        else:
            # row is already visible so don't change row position
            r = self.start_row
        
        if c < self.start_col:
            # left of start column, so set start view to that column
            update = True
        elif c >= last_col:
            c = c - self.fully_visible_cols + 1
            update = True
        else:
            c = self.start_col

        if update:
            self.Scroll(c, r)
        self.Refresh()
    
    def select_addr(self, addr):
        rel_pos = addr - self.start_addr
        self.select_index(rel_pos)

    def on_mouse_wheel(self, evt):
        """Driver to process mouse events.

        This is the main driver to process all mouse events that
        happen on the BitmapScroller.  Once a selector is triggered by
        its event combination, it becomes the active selector and
        further mouse events are directed to its handler.
        """
        if self.end_byte is None:  # end_byte is a proxy for the image being loaded
            return
        
        w = evt.GetWheelRotation()
        if evt.ControlDown():
            if w < 0:
                self.zoom_out()
            elif w > 0:
                self.zoom_in()

        evt.Skip()

    def on_left_up(self, evt):
        evt.Skip()

    def set_cursor_pos_from_event(self, evt):
        e = self.editor
        byte, bit, inside = self.event_coords_to_byte(evt)
        if inside:
            self.select_extend_mode = evt.ShiftDown()
            if self.select_extend_mode:
                if byte < e.anchor_start_index:
                    e.anchor_start_index = byte
                elif byte + 1 > e.anchor_start_index:
                    e.anchor_end_index = byte + 1
                e.anchor_initial_start_index, e.anchor_initial_end_index = e.anchor_start_index, e.anchor_end_index
                e.cursor_index = byte
            else:
                e.set_cursor(byte, False)
            wx.CallAfter(e.index_clicked, byte, bit, None)

    def on_left_down(self, evt):
        self.set_cursor_pos_from_event(evt)
        evt.Skip()

    def on_left_dclick(self, evt):
        self.on_left_down(evt)
 
    def set_selection_from_event(self, evt):
        e = self.editor
        byte, bit, inside = self.event_coords_to_byte(evt)
        if inside:
            index1 = byte
            index2 = byte + 1
#                print index1, index2, e.anchor_start_index, e.anchor_end_index
            update = False
            if evt.ShiftDown():
                if not self.select_extend_mode:
                    # Shift pressed during drag; turn into extend mode
                    e.anchor_initial_start_index, e.anchor_initial_end_index = e.anchor_start_index, e.anchor_end_index
                if index1 < e.anchor_initial_start_index:
                    e.anchor_start_index = index1
                    e.anchor_end_index = e.anchor_initial_end_index
                    e.cursor_index = index1
                    update = True
                else:
                    e.anchor_start_index = e.anchor_initial_start_index
                    e.anchor_end_index = index2
                    e.cursor_index = index2
                    update = True
            else:
                if e.anchor_start_index <= index1:
                    if index2 != e.anchor_end_index:
                        e.anchor_start_index = e.anchor_initial_start_index
                        e.anchor_end_index = index2
                        e.cursor_index = index2
                        update = True
                else:
                    if index1 != e.anchor_end_index:
                        e.anchor_start_index = e.anchor_initial_end_index
                        e.anchor_end_index = index1
                        e.cursor_index = index1
                        update = True
            self.select_extend_mode = evt.ShiftDown()
            if update:
                if self.rect_select:
                    index = byte
                else:
                    index = e.anchor_end_index
                wx.CallAfter(e.index_clicked, index, bit, None)
#                print "motion: byte, start, end", byte, e.anchor_start_index, e.anchor_end_index
 
    def on_motion(self, evt):
        if self.editor is not None and evt.LeftIsDown():
            self.set_selection_from_event(evt)
        evt.Skip()

    def on_paint(self, evt):
        self.dbg_call_seq += 1
        log.debug("In on_paint %d" % self.dbg_call_seq)
        self.prepare_image()
        if self.scaled_bmp is not None:
            dc = wx.BufferedPaintDC(self, self.scaled_bmp, wx.BUFFER_CLIENT_AREA)
        evt.Skip()
    
    def on_resize(self, evt):
        if self.is_ready_to_render():
            self.calc_image_size()
    
    def on_popup(self, evt):
        actions = self.get_popup_actions()
        if actions:
            self.editor.popup_context_menu_from_actions(self, actions)
    
    def get_popup_actions(self):
        return [CutAction, CopyAction, PasteAction, None, SelectAllAction, SelectNoneAction]
    
    def on_focus(self, evt):
        log.debug("on_focus!")
    
    def on_focus_lost(self, evt):
        log.debug("on_focus_lost!")
    
    def on_mouse_enter(self, evt):
        evt.Skip()
    
    def on_mouse_leave(self, evt):
        evt.Skip()
    
    def on_char(self, evt):
        log.debug("on_char!")
        evt.Skip()
    
    def process_movement_keys(self, char):
        delta_index = None
        if char == wx.WXK_UP:
            delta_index = -self.bytes_per_row
        elif char == wx.WXK_DOWN:
            delta_index = self.bytes_per_row
        elif char == wx.WXK_LEFT:
            delta_index = -1
        elif char == wx.WXK_RIGHT:
            delta_index = 1
        elif char == wx.WXK_PAGEUP:
            page_size = self.editor.segment.page_size
            if page_size < 0:
                delta_index = -(self.fully_visible_rows * self.bytes_per_row)
            else:
                delta_index = -page_size
        elif char == wx.WXK_PAGEDOWN:
            page_size = self.editor.segment.page_size
            if page_size < 0:
                delta_index = self.fully_visible_rows * self.bytes_per_row
            else:
                delta_index = page_size
        return delta_index
    
    def process_delta_index(self, delta_index):
        e = self.editor
        index = e.set_cursor(e.cursor_index + delta_index, False)
        wx.CallAfter(self.select_index, index)
        wx.CallAfter(e.index_clicked, index, 0, self)
    
    def on_char_hook(self, evt):
        log.debug("on_char_hook! char=%s, key=%s, modifiers=%s" % (evt.GetUniChar(), evt.GetKeyCode(), bin(evt.GetModifiers())))
        mods = evt.GetModifiers()
        char = evt.GetUniChar()
        if char == 0:
            char = evt.GetKeyCode()
        delta_index = self.process_movement_keys(char)
        if delta_index is not None:
            self.process_delta_index(delta_index)
        else:
            evt.Skip()


class BitmapScroller(BitviewScroller):
    def update_bytes_per_row(self):
        self.bytes_per_row = self.editor.bitmap_width
    
    def update_zoom(self):
        self.set_zoom(self.editor.bitmap_zoom)
    
    def sync_to_editor(self, e):
        e.bitmap_zoom = self.zoom
        e.bitmap_width = self.bytes_per_row
    
    def event_coords_to_byte(self, evt):
        if self.end_byte is None:  # end_byte is a proxy for the image being loaded
            return 0, 0, False
        
        inside = True

        x, y = self.GetViewStart()
        x = (evt.GetX() // self.zoom) + x
        y = (evt.GetY() // self.zoom) + y
        if x < 0 or x >= self.grid_width or y < 0 or y > (self.start_row + self.visible_rows):
            inside = False
        if self.bytes_per_row == 1:
            # border only used on single byte width drawing
            x -= self.border_width
        if x < 0:
            x = 0
        elif x >= 8 * self.bytes_per_row:
            x = 8 * self.bytes_per_row - 1
        xbyte = (x // 8)
        byte = (self.bytes_per_row * y) + xbyte
        if byte > self.end_byte:
            inside = False
        bit = 7 - (x & 7)
        return byte, bit, inside
    
    def get_image(self):
        log.debug("get_image: bit image: start=%d, num=%d" % (self.start_row, self.visible_rows))
        sr = self.start_row
        nr = self.visible_rows
        self.start_byte = sr * self.bytes_per_row
        self.end_byte = self.start_byte + (nr * self.bytes_per_row)
        if self.end_byte > len(self.segment):
            self.end_byte = len(self.segment)
            count = self.end_byte - self.start_byte
            bytes = np.zeros((nr * self.bytes_per_row), dtype=np.uint8)
            bytes[0:count] = self.segment[self.start_byte:self.end_byte]
            style = np.zeros((nr * self.bytes_per_row), dtype=np.uint8)
            style[0:count] = self.segment.style[self.start_byte:self.end_byte]
        else:
            count = self.end_byte - self.start_byte
            bytes = self.segment[self.start_byte:self.end_byte]
            style = self.segment.style[self.start_byte:self.end_byte]
        if self.bytes_per_row == 1:
            array = self.get_image_1(sr, nr, count, bytes, style)
        else:
            array = self.get_image_multi(sr, nr, count, bytes, style)
        sc = self.start_col
        nc = self.visible_cols
        clipped = array[:,sc:sc + nc,:]
        return clipped
    
    def get_image_1(self, sr, nr, count, bytes, style):
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8 * self.bytes_per_row))
        bits[bits==0]=255
        bits[bits==1]=0
        bitwidth = 8 * self.bytes_per_row
        border = self.border_width
        width = bitwidth + 2 * border
        array = np.empty((nr, width, 3), dtype=np.uint8)
        array[:,border:border + bitwidth,0] = bits
        array[:,border:border + bitwidth,1] = bits
        array[:,border:border + bitwidth,2] = bits
        array[:,0:border,:] = self.background_color
        array[:,border + bitwidth:width,:] = self.background_color
        array[count:,border:border + bitwidth,:] = self.background_color
        e = self.editor
        start_index, end_index, rc1, rc2 = self.get_highlight_indexes()
        start_highlight = max(start_index - self.start_byte, 0)
        end_highlight = min(end_index - self.start_byte, count)
        log.debug("highlight %d-%d" % (start_highlight, end_highlight))
        
        mask = array == (255, 255, 255)
        mask = np.all(mask, axis=2)
        
        # highlight any comments
        match = style & 0x80
        style_mask = match==0x80
        # This doesn't do anything! A mask of a mask apparently doesn't work
        # array[style_mask,:,:][mask[style_mask]] = self.comment_color
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = self.comment_color
        array[style_mask,0:border,:] = self.comment_color
        array[style_mask,border + bitwidth:width,:] = self.comment_color
        
        # highlight any matches
        match = style & 0x1
        style_mask = match==0x1
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = self.match_color
        array[style_mask,0:border,:] = self.match_color
        array[style_mask,border + bitwidth:width,:] = self.match_color

        if start_highlight < count and end_highlight >= 0:
            # change all white pixels to the highlight color.  The mask
            # must be collapsed on the color axis to result in one entry
            # per row so it can be applied to the array.
            array[start_highlight:end_highlight,:,:][mask[start_highlight:end_highlight]] = self.editor.highlight_color
            
            # Highlight the border areas so the selection is visible even
            # if there's an all-filled area
            array[start_highlight:end_highlight,0:border,:] = self.editor.highlight_color
            array[start_highlight:end_highlight,border + bitwidth:width,:] = self.editor.highlight_color

        return array
    
    def get_image_multi(self, sr, nr, count, bytes, style):
        bits = np.unpackbits(bytes)
        bits = bits.reshape((-1, 8 * self.bytes_per_row))
        bits[bits==0]=255
        bits[bits==1]=0
        width = 8 * self.bytes_per_row
        bitimage = np.empty((nr, width, 3), dtype=np.uint8)
        bitimage[:,:,0] = bits
        bitimage[:,:,1] = bits
        bitimage[:,:,2] = bits
        e = self.editor
        start_index, end_index, rc1, rc2 = self.get_highlight_indexes()
        start_highlight = max(start_index - self.start_byte, 0)
        end_highlight = min(end_index - self.start_byte, count)
        log.debug("highlight %d-%d" % (start_highlight, end_highlight))
        
        array = bitimage.reshape((-1, 8, 3))
        array[count:,:,:] = self.background_color

        mask = array == (255, 255, 255)
        mask = np.all(mask, axis=2)
        
        # highlight any comments
        match = style & 0x80
        style_mask = match==0x80
        # This doesn't do anything! A mask of a mask apparently doesn't work
        # array[style_mask,:,:][mask[style_mask]] = self.comment_color
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = self.comment_color
        
        # highlight any matches
        match = style & 0x1
        style_mask = match==0x1
        s = np.tile(style_mask, (mask.shape[1], 1)).T
        m2 = np.logical_and(mask, s)
        array[m2] = self.match_color

        if start_highlight < count and end_highlight >= 0:
            # change all white pixels to the highlight color.  The mask
            # must be collapsed on the color axis to result in one entry
            # per row so it can be applied to the array.
            array[start_highlight:end_highlight,:,:][mask[start_highlight:end_highlight]] = self.editor.highlight_color

        return bitimage
    
    def get_popup_actions(self):
        actions = BitviewScroller.get_popup_actions(self)
        actions.extend([None, BitmapWidthAction, BitmapZoomAction])
        return actions


class FontMapScroller(BitviewScroller):
    font_to_atascii_mapping = np.hstack([np.arange(64, 96, dtype=np.uint8),np.arange(64, dtype=np.uint8),np.arange(96, 128, dtype=np.uint8)])
    font_to_atascii_mapping = np.hstack([font_to_atascii_mapping, font_to_atascii_mapping + 128])
    font_mappings = [
        (wx.NewId(), "ANTIC Map", "Internal Character Codes", np.arange(256, dtype=np.uint8)),
        (wx.NewId(), "ATASCII", "ATASCII Characters", font_to_atascii_mapping),
        ]
    
    def __init__(self, parent, task, bytes_per_row=8, font_mapping=1, command=None, **kwargs):
        BitviewScroller.__init__(self, parent, task, **kwargs)
        self.zoom = 2
        self.bytes_per_row = bytes_per_row
        self.font = None
        self.command_cls = command
        self.set_font_mapping(font_mapping)
        self.inverse = 0
        self.editing = False
    
    def is_ready_to_render(self):
        return self.font is not None

    def update_bytes_per_row(self):
        self.bytes_per_row = self.editor.map_width
    
    def update_zoom(self):
        self.set_zoom(self.editor.map_zoom)
    
    def sync_to_editor(self, e):
        e.map_zoom = self.zoom
        e.map_width = self.bytes_per_row
    
    def calc_scale_from_bytes(self):
        self.total_rows = (len(self.segment) + self.bytes_per_row - 1) / self.bytes_per_row
        self.grid_width = int(8 * self.bytes_per_row)
        self.grid_height = int(8 * self.total_rows)
    
    def get_zoom_factors(self):
        zw = self.font.scale_w
        zh = self.font.scale_h
        return zw * self.zoom, zh * self.zoom
    
    def calc_scroll_params(self):
        zw, zh = self.get_zoom_factors()
        self.SetVirtualSize((self.grid_width * zw, self.grid_height * zh))
        self.SetScrollRate(8 * zw, 8 * zh)
    
    def calc_image_size(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        self.start_row = y
        self.start_col = y
        
        # For proper buffered paiting, the visible_rows must include the
        # (possibly) partially obscured last row.  fully_visible_rows
        # indicates the number of rows without that last partially obscured
        # row (if it exists).
        zw, zh = self.get_zoom_factors()
        zoom_factor = 8 * zh
        self.fully_visible_rows = h / zoom_factor
        self.visible_rows = (h + zoom_factor - 1) / zoom_factor
        zoom_factor = 8 * zw
        self.fully_visible_cols = w / zoom_factor
        self.start_col, self.visible_cols = x, (w + zoom_factor - 1) / zoom_factor
        log.debug("fontmap: x, y, w, h, row start, num: %s" % str([x, y, w, h, self.start_row, self.visible_rows, "col start, num:", self.start_col, self.visible_cols]))
    
    def set_font(self):
        self.font = self.editor.antic_font
        self.calc_scroll_params()
    
    def set_font_mapping(self, index):
        self.font_mapping_index = index
        self.font_mapping = self.font_mappings[self.font_mapping_index][3]
    
    def get_font_mapping_name(self):
        return self.font_mappings[self.font_mapping_index][1]

    def get_image(self):
        log.debug("get_image: fontmap: start=%d, num=%d" % (self.start_row, self.visible_rows))
        sr = self.start_row
        nr = self.visible_rows
        self.start_byte = sr * self.bytes_per_row
        self.end_byte = self.start_byte + (nr * self.bytes_per_row)
        if self.end_byte > len(self.segment):
            self.end_byte = len(self.segment)
            bytes = np.zeros((nr * self.bytes_per_row), dtype=np.uint8)
            bytes[0:self.end_byte - self.start_byte] = self.segment[sr * self.bytes_per_row:self.end_byte]
            style = np.zeros((nr * self.bytes_per_row), dtype=np.uint8)
            style[0:self.end_byte - self.start_byte] = self.segment.style[sr * self.bytes_per_row:self.end_byte]
        else:
            bytes = self.segment[self.start_byte:self.end_byte]
            style = self.segment.style[self.start_byte:self.end_byte]
        bytes = bytes.reshape((nr, -1))
        style = style.reshape((nr, -1))
        #log.debug("get_image: bytes", bytes)
        
        anchor_start, anchor_end, rc1, rc2 = self.get_highlight_indexes()
        if speedups is not None:
            array = speedups.get_numpy_font_map_image(bytes, style, self.start_byte, self.end_byte, self.bytes_per_row, nr, self.start_col, self.visible_cols, self.background_color, self.font, self.font_mapping, anchor_start, anchor_end, self.rect_select, rc1, rc2)
        else:
            array = self.get_numpy_font_map_image(bytes, style, self.start_byte, self.end_byte, self.bytes_per_row, nr, self.start_col, self.visible_cols, self.background_color, self.font, self.font_mapping, anchor_start, anchor_end, self.rect_select, rc1, rc2)
        
        self.show_highlight(array, rc1, rc2)
        
        return array
    
    def show_highlight(self, array, rc1, rc2):
        if rc1 is None:
            return
        r1, c1 = rc1
        r2, c2 = rc2
        sr = r1 - self.start_row
        er = r2 - self.start_row
        sc = c1 - self.start_col
        ec = c2 - self.start_col
        x1 = sc * 8
        x2 = ec * 8 - 1
        y1 = sr * 8
        y2 = er * 8 - 1
        xmax = array.shape[1]
        ymax = array.shape[0]
        c1 = max(x1, 0)
        c2 = min(x2, xmax)
        if y1 >= 0 and y1 < ymax and c2 > c1:
            array[y1, c1:c2 + 1] = self.background_color
        if y2 >= 0 and y2 < ymax and c2 > c1:
            array[y2, c1:c2 + 1] = self.background_color
        c1 = max(y1, 0)
        c2 = min(y2, ymax)
        if x1 >= 0 and x1 < xmax and c2 > c1:
            array[c1:c2 + 1, x1] = self.background_color
        if x2 >= 0 and x2 < xmax and c2 > c1:
            array[c1:c2 + 1, x2] = self.background_color
    
    def get_numpy_font_map_image(self, bytes, style, start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols, background_color, font, font_mapping, anchor_start, anchor_end, rect_select, rc1, rc2):
        width = int(font.char_w * num_cols)
        height = int(num_rows * font.char_h)
        log.debug("pixel width: %dx%d" % (width, height))
        array = np.empty((height, width, 3), dtype=np.uint8)
        
        log.debug("start byte: %s, end_byte: %s, bytes_per_row=%d num_rows=%d start_col=%d num_cols=%d" % (start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols))
        end_col = min(bytes_per_row, start_col + num_cols)
        y = 0
        e = start_byte
        f = font.normal_font
        fh = font.highlight_font
        fm = font.match_font
        fc = font.comment_font
        if rect_select:
            r1, c1 = rc1
            r2, c2 = rc2
        for j in range(num_rows):
            x = 0
            for i in range(start_col, start_col + num_cols):
                if e + i >= end_byte or i >= end_col:
                    array[y:y+8,x:x+8,:] = background_color
                else:
                    c = font_mapping[bytes[j, i]]
                    if anchor_start <= e + i < anchor_end and (not rect_select or c1 <= i < c2):
                        array[y:y+8,x:x+8,:] = fh[c]
                    elif style[j, i] & 1:
                        array[y:y+8,x:x+8,:] = fm[c]
                    elif style[j, i] & 0x80:
                        array[y:y+8,x:x+8,:] = fc[c]
                    else:
                        array[y:y+8,x:x+8,:] = f[c]
                x += 8
            y += 8
            e += bytes_per_row
        return array

    def event_coords_to_byte(self, evt):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        inside = True

        zw, zh = self.get_zoom_factors()
        x, y = self.GetViewStart()
        x = (evt.GetX() // zw // 8) + x
        y = (evt.GetY() // zh // 8) + y
        if x < 0 or x >= self.bytes_per_row or y < 0 or y > (self.start_row + self.visible_rows):
            inside = False
        byte = (self.bytes_per_row * y) + x
        if byte > self.end_byte:
            inside = False
        bit = 7 - (y & 7)
        return byte, bit, inside
    
    def get_popup_actions(self):
        actions = BitviewScroller.get_popup_actions(self)
        actions.extend([None, FontMappingWidthAction, FontMappingZoomAction, None])
        actions.extend(self.task.get_font_mapping_actions())
        return actions
    
    def set_status_message(self):
        e = self.editor
        if e is None:
            return
        if not self.editing:
            message = "Double click or press F2 to begin editing text"
        else:
            if self.inverse:
                message = "Editing text (INVERSE MODE): Press F1 for normal characters"
            else:
                message = "Editing text: Press F1 for inverse"
            message += " (press F2 to stop editing or click outside the character map window)"
        e.task.status_bar.message = message
    
    def on_focus(self, evt):
        log.debug("on_focus!")
        self.inverse = 0
        self.pending_esc = False
        self.set_status_message()
        self.editing = False
        
    def on_focus_lost(self, evt):
        log.debug("on_focus_lost!")
        e = self.editor
        if e is not None:
            e.task.status_bar.message = ""
        self.editing = False

    def on_left_dclick(self, evt):
        e = self.editor
        byte, bit, inside = self.event_coords_to_byte(evt)
        if inside:
            e.set_cursor(byte, False)
            wx.CallAfter(e.index_clicked, byte, bit, None)
            self.editing = True
            self.set_status_message()
        evt.Skip()
    
    def on_char(self, evt):
        log.debug("on_char! char=%s, key=%s, shift=%s, ctrl=%s, cmd=%s" % (evt.GetUniChar(), evt.GetRawKeyCode(), evt.ShiftDown(), evt.ControlDown(), evt.CmdDown()))
        if not self.editing:
            evt.Skip()
            return
        char = evt.GetUniChar()
        if char > 0:
            self.change_byte(char | self.inverse)
    
    def change_byte(self, value):
        e = self.editor
        if e is None:
            return
        cmd_cls = self.command_cls
        if cmd_cls is None:
            return
        if e.can_copy:
            index = e.anchor_start_index
        else:
            index = e.cursor_index
        cmd = cmd_cls(e.segment, index, index+1, value, True)
        e.process_command(cmd)
    
    def on_char_hook(self, evt):
        log.debug("on_char_hook! char=%s, key=%s, modifiers=%s" % (evt.GetUniChar(), evt.GetKeyCode(), bin(evt.GetModifiers())))
        mods = evt.GetModifiers()
        char = evt.GetUniChar()
        if char == 0:
            char = evt.GetKeyCode()
        byte = None
        delta_index = None
        if not self.editing:
            if char == wx.WXK_F2:
                self.editing = True
                self.set_status_message()
            else:
                delta_index = self.process_movement_keys(char)
        else:
            if mods == wx.MOD_RAW_CONTROL:
                if char == 44:  # Ctrl-, prints ATASCII 0 (heart)
                    byte = 0 + self.inverse
                elif char >= 65 and char <= 90:  # Ctrl-[A-Z] prints ATASCII chars 1-26
                    byte = char - 64 + self.inverse
                elif char == 46:  # Ctrl-. prints ATASCII 96 (diamond)
                    byte = 96 + self.inverse
                elif char == 59:  # Ctrl-; prints ATASCII 123 (spade)
                    byte = 123 + self.inverse
                elif char == wx.WXK_TAB:
                    byte = 158
                elif char == 50:  # Ctrl-2 prints ATASCII 253 (buzzer)
                    byte = 253
                elif char == wx.WXK_INSERT:
                    byte = 255
            elif mods == wx.MOD_SHIFT:
                if char == wx.WXK_BACK:
                    byte = 156
                elif char == wx.WXK_INSERT:
                    byte = 157
                elif char == wx.WXK_TAB:
                    byte = 159
            elif char == wx.WXK_HOME:
                byte = 125
            elif char == wx.WXK_BACK:
                byte = 126
            elif char == wx.WXK_TAB:
                byte = 127
            elif char == wx.WXK_RETURN:
                byte = 155
            elif char == wx.WXK_DELETE:
                byte = 254
            elif char == wx.WXK_INSERT:
                byte = 255
            
            elif char == wx.WXK_F1:
                self.inverse = (self.inverse + 0x80) & 0x80
                self.set_status_message()
            elif char == wx.WXK_F2:
                self.editing = False
                self.set_status_message()
            
            elif self.pending_esc:
                if char == wx.WXK_ESCAPE:
                    byte = 27
                elif char == wx.WXK_UP:
                    byte = 28
                elif char == wx.WXK_DOWN:
                    byte = 29
                elif char == wx.WXK_LEFT:
                    byte = 30
                elif char == wx.WXK_RIGHT:
                    byte = 31
            
            elif char == wx.WXK_ESCAPE:
                self.pending_esc = True
        
            else:
                delta_index = self.process_movement_keys(char)
        
        if byte is not None:
            self.change_byte(byte)
            self.pending_esc = False
        elif delta_index is not None:
            e = self.editor
            index = e.set_cursor(e.cursor_index + delta_index, False)
            wx.CallAfter(self.select_index, index)
            wx.CallAfter(e.index_clicked, index, 0, self)
        else:
            evt.Skip()


class CharacterSetViewer(FontMapScroller):
    def __init__(self, parent, task, bytes_per_row=16, font_mapping=0, command=None, **kwargs):
        FontMapScroller.__init__(self, parent, task, bytes_per_row, font_mapping, command, **kwargs)
        self.segment = DefaultSegment(0, np.arange(256, dtype=np.uint8))
        self.start_addr = 0
        self.selected_char = -1
    
    def set_selected_char(self, index):
        self.selected_char = index
        e = self.editor
        if e is not None:
            e.set_current_draw_pattern(self.selected_char, self)
    
    def clear_tile_selection(self):
        self.selected_char = -1
        self.Refresh()
    
    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.background_color = self.editor.empty_color
            self.set_colors()
            self.set_font()
            self.set_scale()

    def on_left_down(self, evt):
        e = self.editor
        byte, bit, inside = self.event_coords_to_byte(evt)
        if inside:
            self.set_selected_char(byte)
            wx.CallAfter(self.Refresh)
        evt.Skip()
 
    def on_left_dclick(self, evt):
        e = self.editor
        byte, bit, inside = self.event_coords_to_byte(evt)
        if inside:
            self.set_selected_char(byte)
            wx.CallAfter(self.Refresh)
        evt.Skip()
    
    def on_motion(self, evt):
        e = self.editor
        if e is not None and evt.LeftIsDown():
            byte, bit, inside = self.event_coords_to_byte(evt)
            if inside:
                pass
        evt.Skip()
    
    def set_status_message(self):
        return
    
    def get_popup_actions(self):
        return []
    
    def get_highlight_indexes(self):
        if self.selected_char < 0:
            return 0, 0, None, None
        return self.selected_char, self.selected_char + 1, None, None
    
    def process_delta_index(self, delta_index):
        _, byte = divmod(self.selected_char + delta_index, 256)
        self.set_selected_char(byte)
        self.Refresh()
    
    def on_char_hook(self, evt):
        log.debug("on_char_hook! char=%s, key=%s, modifiers=%s" % (evt.GetUniChar(), evt.GetKeyCode(), bin(evt.GetModifiers())))
        mods = evt.GetModifiers()
        char = evt.GetUniChar()
        if char == 0:
            char = evt.GetKeyCode()
        delta_index = self.process_movement_keys(char)
        if delta_index is not None:
            self.process_delta_index(delta_index)
        else:
            evt.Skip()


class MemoryMapScroller(BitviewScroller):
    def __init__(self, parent, task, **kwargs):
        BitviewScroller.__init__(self, parent, task, **kwargs)
        self.bytes_per_row = 256
        self.zoom = 2
    
    def calc_scale_from_bytes(self):
        self.total_rows = (len(self.segment) + self.bytes_per_row - 1) / self.bytes_per_row
        self.grid_width = int(self.bytes_per_row)
        self.grid_height = int(self.total_rows)
    
    def calc_scroll_params(self):
        z = self.zoom
        self.SetVirtualSize((self.grid_width * z, self.grid_height * z))
        self.SetScrollRate(z, z)
    
    def calc_image_size(self):
        x, y = self.GetViewStart()
        w, h = self.GetClientSizeTuple()
        self.start_row = y
        self.start_col = x
        
        # For proper buffered paiting, the visible_rows must include the
        # (possibly) partially obscured last row.  fully_visible_rows
        # indicates the number of rows without that last partially obscured
        # row (if it exists).
        z = self.zoom
        self.fully_visible_rows = h / z
        self.fully_visible_cols = w / z
        self.visible_rows = (h + z - 1) / z
        self.start_col, self.visible_cols = x, (w + z - 1) / z
        log.debug("memory map: x, y, w, h, row start, num: %s" % str([x, y, w, h, self.start_row, self.visible_rows, "col start, num:", self.start_col, self.visible_cols]))

    def get_image(self):
        log.debug("get_image: memory map: start=%d, num=%d" % (self.start_row, self.visible_rows))
        t0 = time.clock()
        sr = self.start_row
        nr = self.visible_rows
        self.start_byte = sr * self.bytes_per_row
        self.end_byte = self.start_byte + (nr * self.bytes_per_row)
        if self.end_byte > len(self.segment):
            self.end_byte = len(self.segment)
            bytes = np.zeros((nr * self.bytes_per_row), dtype=np.uint8)
            bytes[0:self.end_byte - self.start_byte] = self.segment[sr * self.bytes_per_row:self.end_byte]
        else:
            bytes = self.segment[sr * self.bytes_per_row:self.end_byte]
        bytes = bytes.reshape((nr, -1))
        #log.debug("get_image: bytes", bytes)
        
        e = self.editor
        anchor_start, anchor_end, rc1, rc2 = self.get_highlight_indexes()
        if speedups is not None:
            array = speedups.get_numpy_memory_map_image(bytes, self.start_byte, self.end_byte, self.bytes_per_row, nr, self.start_col, self.visible_cols, self.background_color, anchor_start, anchor_end, e.highlight_color, self.rect_select, rc1, rc2)
        else:
            array = self.get_numpy_memory_map_image(bytes, self.start_byte, self.end_byte, self.bytes_per_row, nr, self.start_col, self.visible_cols, self.background_color, anchor_start, anchor_end, e.highlight_color, self.rect_select, rc1, rc2)
        log.debug(array.shape)
        t = time.clock()
        log.debug("get_image: time %f" % (t - t0))
        return array

    def get_numpy_memory_map_image(self, bytes, start_byte, end_byte, bytes_per_row, num_rows, start_col, num_cols, background_color, anchor_start, anchor_end, selected_color, rect_select, rc1, rc2):
        log.debug("SLOW VERSION OF get_numpy_memory_map_image!!!")
        num_rows_with_data = (end_byte - start_byte + bytes_per_row - 1) / bytes_per_row
        
        log.debug(str([end_byte, start_byte, (end_byte - start_byte) / bytes_per_row]))
        end_row = min(num_rows_with_data, num_rows)
        end_col = min(bytes_per_row, start_col + num_cols)
        
        width = end_col - start_col
        height = num_rows_with_data
        log.debug("memory map size: %dx%d, zoom=%d, rows with data=%d, rows %d, cols %d-%d" % (width, height, self.zoom, num_rows_with_data, num_rows, start_col, start_col + width - 1))
        array = np.empty((height, width, 3), dtype=np.uint8)
        array[:,:] = background_color
        
        y = 0
        e = start_byte
        if rect_select:
            r1, c1 = rc1
            r2, c2 = rc2
        for j in range(end_row):
            x = 0
            for i in range(start_col, end_col):
                if e + i >= end_byte:
                    break
                c = bytes[j, i] ^ 0xff
                if anchor_start <= e + i < anchor_end and (not rect_select or c1 <= i < c2):
                    r = selected_color[0] * c >> 8
                    g = selected_color[1] * c >> 8
                    b = selected_color[2] * c >> 8
                    array[y,x,:] = (r, g, b)
                else:
                    array[y,x,:] = (c, c, c)
                x += 1
            y += 1
            e += bytes_per_row
        return array

    def event_coords_to_byte(self, evt):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        inside = True

        z = self.zoom
        x, y = self.GetViewStart()
        x = (evt.GetX() // z) + x
        y = (evt.GetY() // z) + y
        if x < 0 or x >= self.bytes_per_row or y < 0 or y > (self.start_row + self.visible_rows):
            inside = False
        byte = (self.bytes_per_row * y) + x
        if byte > self.end_byte:
            inside = False
        return byte, 0, inside


if __name__ == '__main__':
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='Test', size=(500,500))
    frame.CreateStatusBar()
    
    panel = BitviewScroller(frame)
    bytes = np.arange(256, dtype=np.uint8)
    panel.set_data(bytes)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel,  1, wx.EXPAND | wx.ALL, 5)
    
    def buttonHandler(evt):
        id = evt.GetId()
        if id == 100:
            panel.zoom_in()
        elif id == 101:
            panel.zoom_out()
        elif id == 200:
            wildcard="*"
            dlg = wx.FileDialog(
                frame, message="Open File",
                defaultFile="", wildcard=wildcard, style=wx.OPEN)

            # Show the dialog and retrieve the user response. If it is the
            # OK response, process the data.
            if dlg.ShowModal() == wx.ID_OK:
                # This returns a Python list of files that were selected.
                paths = dlg.GetPaths()

                for path in paths:
                    dprint("open file %s:" % path)
                    fh = open(path, 'rb')
                    img = wx.EmptyImage()
                    if img.LoadStream(fh):
                        panel.setImage(img)
                    else:
                        dprint("Invalid image: %s" % path)
            # Destroy the dialog. Don't do this until you are done with it!
            # BAD things can happen otherwise!
            dlg.Destroy()
        elif id == 201:
            pass
        elif id == 202:
            panel.copy_to_clipboard()
    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
    button = wx.Button(frame, 100, 'Zoom In')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 101, 'Zoom Out')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 200, 'Load')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 202, 'Copy to Clipboard')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)

    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    app.MainLoop()
