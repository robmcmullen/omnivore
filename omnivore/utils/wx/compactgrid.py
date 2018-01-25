import time

import wx
import numpy as np

from atrcopy import match_bit_mask, comment_bit_mask, user_bit_mask, selected_bit_mask, diff_bit_mask

import logging
logger = logging.getLogger()
# logger.setLevel(logging.INFO)
draw_log = logging.getLogger("draw")
scroll_log = logging.getLogger("scroll")
# draw_log.setLevel(logging.DEBUG)

class AuxWindow(wx.ScrolledWindow):
    def __init__(self, parent, scroll_source, label_char_width=10):
        wx.ScrolledWindow.__init__(self, parent, -1)
        self.scroll_source = scroll_source
        self.label_char_width = label_char_width
        self.isDrawing = False
        self.EnableScrolling(False, False)
        self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_MOUSEWHEEL, self.scroll_source.settings_obj.on_mouse_wheel)

    def OnSize(self, event):
        self.AdjustScrollbars()
        self.SetFocus()

    def UpdateView(self, dc = None):
        if dc is None:
            dc = wx.ClientDC(self)
        if dc.IsOk():
            self.Draw(dc)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        if self.isDrawing:
            return
        self.isDrawing = True
        self.UpdateView(dc)
        self.isDrawing = False

    def OnEraseBackground(self, evt):
        pass


class LeftAuxWindow(AuxWindow):
    def DrawVertText(self, t, line, dc):
        s = self.scroll_source
        y = (line - s.sy) * s.cell_height_in_pixels
        dc.DrawText(t, 0, y)

    def Draw(self, odc=None):
        if not odc:
            odc = wx.ClientDC(self)

        dc = wx.BufferedDC(odc)
        s = self.scroll_source
        if dc.IsOk():
            dc.SetFont(s.view_params.header_font)
            dc.SetBackgroundMode(wx.SOLID)
            dc.SetTextBackground(s.view_params.row_header_bg_color)
            dc.SetTextForeground(s.view_params.text_color)
            dc.SetBackground(wx.Brush(s.view_params.row_header_bg_color))
            dc.Clear()
            for line, header in self.scroll_source.table.get_row_label_text(s.sy, s.sh):
                if s.IsLine(line):
                    self.DrawVertText(header, line, dc)

class TopAuxWindow(AuxWindow):
    def DrawHorzText(self, t, sx, num_cells, dc):
        s = self.scroll_source
        x = (sx - s.sx) * s.cell_width_in_pixels
        width = len(t) * s.fw
        offset = ((s.cell_width_in_pixels * num_cells) - width)/2  # center text in cell
        dc.DrawText(t, x + offset, 0)

    def Draw(self, odc=None):
        if not odc:
            odc = wx.ClientDC(self)

        dc = wx.BufferedDC(odc)
        s = self.scroll_source
        if dc.IsOk():
            dc.SetFont(s.view_params.header_font)
            dc.SetBackgroundMode(wx.SOLID)
            dc.SetTextBackground(s.view_params.col_header_bg_color)
            dc.SetTextForeground(s.view_params.text_color)
            dc.SetBackground(wx.Brush(s.view_params.col_header_bg_color))
            dc.Clear()
            for cell, num_cells, header in self.scroll_source.table.get_col_labels(s.sx):
                self.DrawHorzText(header, cell, num_cells, dc)


def ForceBetween(min, val, max):
    if val  > max:
        return max
    if val < min:
        return min
    return val

class Scroller:
    def __init__(self, parent):
        self.parent = parent
        self.ow = None
        self.oh = None
        self.ox = None
        self.oy = None

    def SetScrollbars(self, fw, fh, w, h, x, y):
        if (self.ow != w or self.oh != h or self.ox != x or self.oy != y):
            scroll_log.debug("Setting scrollbar to: %s" % str([fw, fh, w, h, x, y]))
            self.parent.SetScrollbars(fw, fh, w, h, x, y)
            self.ow = w
            self.oh = h
            self.ox = x
            self.oy = y

class FakeList(object):
    def __init__(self, count):
        self.num_items = count

    def __len__(self):
        return self.num_items

    def __getitem__(self, item):
        #print(item, type(item))
        try:
            #return "0A 0X 0Y FF sv-bdizc  00 00 00 LDA $%04x" % ((item * 4) + 0x600)
            #return "%04x c0f3 f4e1 f2f4 cdcd cdcd 48ad c602" % (item * 16 + 0x6000)
            return "%02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x" % tuple([a & 0xff for a in range(item & 0xff, (item & 0xff) + 16)])
        except:
            return "slice"


class DrawTextImageCache(object):
    def __init__(self, view_params, window, font=None):
        self.font = font
        self.window = window
        self.cache = {}
        self.set_colors(view_params)

    def invalidate(self):
        self.cache = {}

    def set_colors(self, m):
        self.color = m.text_color
        self.diff_color = m.diff_text_color
        if self.font is None:
            self.font = m.text_font
        self.selected_background = m.highlight_color
        self.selected_brush = wx.Brush(m.highlight_color, wx.SOLID)
        self.selected_pen = wx.Pen(m.highlight_color, 1, wx.SOLID)
        self.normal_background = m.background_color
        self.normal_brush = wx.Brush(m.background_color, wx.SOLID)
        self.normal_pen = wx.Pen(m.background_color, 1, wx.SOLID)
        self.data_background = m.data_color
        self.data_brush = wx.Brush(m.data_color, wx.SOLID)
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

    def draw_cached_text(self, dc, rect, text, style):
        k = (text, style, rect.width, rect.height)
        draw_log.debug(str(k))
        try:
            bmp = self.cache[k]
        except KeyError:
            bmp = wx.Bitmap(rect.width, rect.height)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmp)
            r = wx.Rect(0, 0, rect.width, rect.height)
            self.draw_text_to_dc(mdc, r, r, text, style)
            del mdc  # force the bitmap painting by deleting the gc
            self.cache[k] = bmp
        dc.DrawBitmap(bmp, rect.x, rect.y)

    def draw_text_to_dc(self, dc, bg_rect, fg_rect, text, style):
        if style & selected_bit_mask:
            dc.SetBrush(self.selected_brush)
            dc.SetPen(self.selected_pen)
            dc.SetBackground(self.selected_brush)
            dc.SetTextBackground(self.selected_background)
        elif style & match_bit_mask:
            dc.SetPen(self.match_pen)
            dc.SetBrush(self.match_brush)
            dc.SetBackground(self.match_brush)
            dc.SetTextBackground(self.match_background)
        elif style & comment_bit_mask:
            dc.SetPen(self.comment_pen)
            dc.SetBrush(self.comment_brush)
            dc.SetBackground(self.comment_brush)
            dc.SetTextBackground(self.comment_background)
        elif style & user_bit_mask:
            dc.SetPen(self.normal_pen)
            dc.SetBrush(self.data_brush)
            dc.SetBackground(self.normal_brush)
            dc.SetTextBackground(self.data_background)
        else:
            dc.SetPen(self.normal_pen)
            dc.SetBrush(self.normal_brush)
            dc.SetBackground(self.normal_brush)
            dc.SetTextBackground(self.normal_background)
        dc.Clear()
        if style & diff_bit_mask:
            dc.SetTextForeground(self.diff_color)
        else:
            dc.SetTextForeground(self.color)
        dc.SetFont(self.font)
        dc.DrawText(text, fg_rect.x, fg_rect.y)

    def draw_text(self, dc, rect, text, style):
        draw_log.debug(str((text, rect)))
        for i, c in enumerate(text):
            s = style[i]
            self.draw_cached_text(dc, rect, c, s)
            rect.x += self.window.cell_width_in_pixels


class FakeStyle(object):
    def __init__(self, window):
        self.window = window

    def __len__(self):
        return len(self.window.table.data)

    def __getitem__(self, item):
        index, last_index = item.start, item.stop
        try:
            index, last_index = item.start, item.stop
        except:
            index, last_index = item, item + 1
        count = last_index - index
        style = np.zeros(count, dtype=np.uint8)
        if self.window is None:
            return style
        if last_index < self.window.SelectBegin or index >= self.window.SelectEnd:
            pass
        else:
            for i in range(index, last_index):
                if i >= self.window.SelectBegin and i < self.window.SelectEnd:
                    style[i - index] = selected_bit_mask
        return style


class FixedFontDataWindow(wx.ScrolledWindow):
    def __init__(self, parent, settings_obj, table, view_params):

        wx.ScrolledWindow.__init__(self, parent, -1, style=wx.WANTS_CHARS)

        self.isDrawing = False
        self.settings_obj = settings_obj
        self.InitDoubleBuffering()
        self.InitScrolling(parent)
        self.recalc_view(table, view_params)

    def recalc_view(self, table=None, view_params=None):
        if view_params is not None:
            self.view_params = view_params
        if table is None:
            table = self.table
        self.InitFonts()
        self.SelectOff()
        self.SetFocus()
        self.set_table(table)

    def set_table(self, table):
        self.InitCoords()
        self.table = table
        self.cx = self.table.enforce_valid_cursor(self.cy, self.cx)
        self.AdjustScrollbars()
        self.init_renderers()
        self.UpdateView(None)

    def init_renderers(self):
        self.text_renderer = self.table.create_renderer(None, self.view_params, self)

    @property
    def lines(self):
        return self.table.data

    @property
    def style(self):
        return self.table.style

##------------------ Init stuff

    def InitCoords(self):
        self.cx = 0
        self.cy = 0
        self.sx = 0
        self.sy = 0
        self.sw = 0
        self.sh = 0

##-------------------- UpdateView/Caret code

    def OnSize(self, event):
        self.AdjustScrollbars()
        self.SetFocus()

    def SetCharDimensions(self):
        # TODO: We need a code review on this.  It appears that Linux
        # improperly reports window dimensions when the scrollbar's there.
        self.bw, self.bh = self.GetClientSize()
        self.bh += self.view_params.row_height_extra_padding

        if wx.Platform == "__WXMSW__":
            self.sh = int(self.bh // self.cell_height_in_pixels) - 1
            self.sw = int(self.bw // self.cell_width_in_pixels) - 1
        else:
            self.sh = int(self.bh // self.cell_height_in_pixels) - 1
            if self.table.num_rows >= self.sh:
                self.bw = self.bw - wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
                self.sw = int(self.bw // self.cell_width_in_pixels) - 1

            self.sw = int(self.bw // self.cell_width_in_pixels) - 1
            if self.table.num_cells >= self.sw:
                self.bh = self.bh - wx.SystemSettings.GetMetric(wx.SYS_HSCROLL_Y)
                self.sh = int(self.bh // self.cell_height_in_pixels) - 1

    def UpdateView(self, dc = None):
        if dc is None:
            dc = wx.ClientDC(self)
        if dc.IsOk():
            self.SetCharDimensions()
            scroll_log.debug(str(("scroll:", self.sx, self.sy, "cursor", self.cx, self.cy)))
            if self.Selecting:
                self.KeepCaretOnScreen()
            else:
                self.AdjustScrollbars()
            self.DrawSimpleCaret(0,0, dc, True)
            self.Draw(dc)
            self.parent_scrolled_window.update_dependents()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        if self.isDrawing:
            return
        self.isDrawing = True
        self.UpdateView(dc)
        wx.CallAfter(self.AdjustScrollbars)
        self.isDrawing = False

    def OnEraseBackground(self, evt):
        pass

##-------------------- Drawing code

    def InitFonts(self):
        dc = wx.ClientDC(self)
        dc.SetFont(self.view_params.text_font)
        self.fw = dc.GetCharWidth()
        self.fh = dc.GetCharHeight()
        self.cell_width_in_pixels = self.view_params.pixel_width_padding * 2 + self.view_params.base_cell_width_in_chars * self.fw
        self.cell_height_in_pixels = self.fh + self.view_params.row_height_extra_padding

    def InitDoubleBuffering(self):
        pass

##-------- Enforcing screen boundaries, cursor movement

    def KeepCaretOnScreen(self):
        self.sy = ForceBetween(max(0, self.cy-self.sh), self.sy, self.cy)
        self.sx = ForceBetween(max(0, self.cx-self.sw), self.sx, self.cx)
        self.cx = self.table.enforce_valid_cursor(self.cy, self.cx)
        self.AdjustScrollbars()

    def show_cursor(self, col, row):
        self.cy = ForceBetween(0, row, self.table.num_rows - 1)
        self.sy = ForceBetween(self.cy - self.sh + 1, self.sy, self.cy)
        self.cx = ForceBetween(0, col, self.current_line_length - 1)
        self.sx = ForceBetween(self.cx - self.sw + 1, self.sx, self.cx)
        self.cx = self.table.enforce_valid_cursor(self.cy, self.cx)
        self.AdjustScrollbars()

    def HorizBoundaries(self):
        self.SetCharDimensions()
        self.sx = ForceBetween(0, self.sx, max(self.sw, self.table.num_cells - self.sw + 1))

    def VertBoundaries(self):
        self.SetCharDimensions()
        self.sy = ForceBetween(0, self.sy, max(self.sh, self.table.num_rows - self.sh + 1))

    def cVert(self, num):
        self.cy = self.cy + num
        self.cy = ForceBetween(0, self.cy, self.table.num_rows - 1)
        self.sy = ForceBetween(self.cy - self.sh + 1, self.sy, self.cy)
        self.cx = min(self.cx, self.current_line_length - 1)
        self.cx = self.table.enforce_valid_cursor(self.cy, self.cx)

    def cHoriz(self, num):
        self.cx = self.cx + num
        self.cx = ForceBetween(0, self.cx, self.current_line_length - 1)
        self.sx = ForceBetween(self.cx - self.sw + 1, self.sx, self.cx)
        self.cx = self.table.enforce_valid_cursor(self.cy, self.cx)

    def AboveScreen(self, row):
        return row < self.sy

    def BelowScreen(self, row):
        return row >= self.sy + self.sh

    def LeftOfScreen(self, col):
        return col < self.sx

    def RightOfScreen(self, col):
        return col >= self.sx + self.sw

##----------------- data structure helper functions

    def IsLine(self, lineNum):
        return (0<=lineNum) and (lineNum<self.table.num_rows)

##-------------------------- Mouse scroll timing functions

    def InitScrolling(self, parent):
        # we don't rely on the windows system to scroll for us; we just
        # redraw the screen manually every time
        self.parent_scrolled_window = parent
        self.EnableScrolling(False, False)
        self.nextScrollTime = 0
        self.scrollTimer = wx.Timer(self)
        self.scroller = Scroller(self)

    def SetScrollManager(self, parent):
        self.scroller = Scroller(parent)
        self.AdjustScrollbars()

    def CanScroll(self):
       if time.time() >  self.nextScrollTime:
           self.nextScrollTime = time.time() + (self.settings_obj.scroll_delay / 1000.0)
           return True
       else:
           return False

    def SetScrollTimer(self):
        oneShot = True
        self.scrollTimer.Start(self.settings_obj.scroll_delay/2, oneShot)
        self.Bind(wx.EVT_TIMER, self.OnTimer)

    def OnTimer(self, event):
        screenX, screenY = wx.GetMousePosition()
        x, y = self.ScreenToClient((screenX, screenY))
        self.MouseToRow(y)
        self.MouseToCol(x)
        self.update_selection()

##-------------------------- Mouse off screen functions

    def HandleAboveScreen(self, row):
        self.SetScrollTimer()
        if self.CanScroll():
            row = self.sy - 1
            row = max(0, row)
            self.cy = row

    def HandleBelowScreen(self, row):
        self.SetScrollTimer()
        if self.CanScroll():
            row = self.sy + self.sh + 1
            row  = min(row, self.table.num_rows - 1)
            self.cy = row

    def HandleLeftOfScreen(self, col):
        self.SetScrollTimer()
        if self.CanScroll():
            col = self.sx - 1
            col = max(0,col)
            self.cx = col

    def HandleRightOfScreen(self, col):
        self.SetScrollTimer()
        if self.CanScroll():
            col = self.sx + self.sw + 1
            col = min(col, self.current_line_length - 1)
            self.cx = col

##------------------------ mousing functions

    def pixel_pos_to_row_cell(self, x, y):
        row  = self.sy + int(y / self.cell_height_in_pixels)
        cell = self.sx + int(x / self.cell_width_in_pixels)
        return row, cell

    def MouseToRow(self, mouseY):
        row  = self.sy + int(mouseY / self.cell_height_in_pixels)
        if self.AboveScreen(row):
            self.HandleAboveScreen(row)
        elif self.BelowScreen(row):
            self.HandleBelowScreen(row)
        else:
            self.cy  = min(row, self.table.num_rows - 1)

    def MouseToCol(self, mouseX):
        cell = self.sx + int(mouseX / self.cell_width_in_pixels)
        if self.LeftOfScreen(cell):
            self.HandleLeftOfScreen(cell)
        elif self.RightOfScreen(cell):
            self.HandleRightOfScreen(cell)
        else:
            self.cx = min(cell, self.current_line_length)
        # MouseToRow must be called first so the cursor is in the correct row
        self.cx = self.table.enforce_valid_cursor(self.cy, self.cx)

    def MouseToCaret(self, event):
        self.MouseToRow(event.GetY())
        self.MouseToCol(event.GetX())

    def OnMotion(self, event):
        if event.LeftIsDown() and self.HasCapture():
            self.Selecting = True
            self.MouseToCaret(event)
            self.update_selection()

    def OnLeftDown(self, event):
        self.MouseToCaret(event)
        self.start_selection()
        self.UpdateView()
        self.CaptureMouse()
        self.SetFocus()

    def OnLeftUp(self, event):
        if not self.HasCapture():
            return

        if self.SelectEnd is None:
            self.OnClick()
        else:
            self.Selecting = False
            self.SelectNotify(False, self.SelectBegin, self.SelectEnd)

        self.ReleaseMouse()
        self.scrollTimer.Stop()


#------------------------- Scrolling

    def HorizScroll(self, event, eventType):
        if eventType == wx.wxEVT_SCROLLWIN_LINEUP:
            self.sx -= 1
        elif eventType == wx.wxEVT_SCROLLWIN_LINEDOWN:
            self.sx += 1
        elif eventType == wx.wxEVT_SCROLLWIN_PAGEUP:
            self.sx -= self.sw
        elif eventType == wx.wxEVT_SCROLLWIN_PAGEDOWN:
            self.sx += self.sw
        elif eventType == wx.wxEVT_SCROLLWIN_TOP:
            self.sx = self.cx = 0
        elif eventType == wx.wxEVT_SCROLLWIN_BOTTOM:
            self.sx = self.table.num_cells - self.sw
            self.cx = self.table.num_cells
        else:
            self.sx = event.GetPosition()

        self.HorizBoundaries()

    def VertScroll(self, event, eventType):
        if   eventType == wx.wxEVT_SCROLLWIN_LINEUP:
            self.sy -= 1
        elif eventType == wx.wxEVT_SCROLLWIN_LINEDOWN:
            self.sy += 1
        elif eventType == wx.wxEVT_SCROLLWIN_PAGEUP:
            self.sy -= self.sh
        elif eventType == wx.wxEVT_SCROLLWIN_PAGEDOWN:
            self.sy += self.sh
        elif eventType == wx.wxEVT_SCROLLWIN_TOP:
            self.sy = self.cy = 0
        elif eventType == wx.wxEVT_SCROLLWIN_BOTTOM:
            self.sy = self.table.num_rows - self.sh
            self.cy = self.table.num_rows
        else:
            print("Position:", event.GetPosition(), "old:", self.sy, self.GetViewStart())
            self.sy = event.GetPosition()

        self.VertBoundaries()

    def AdjustScrollbars(self):
        if self:
            self.SetCharDimensions()
            self.scroller.SetScrollbars(
                self.cell_width_in_pixels, self.cell_height_in_pixels,
                self.table.num_cells+3, max(self.table.num_rows+1, self.sh),
                self.sx, self.sy)
        else:
            print("NOT ADJUSTING SCROLLBARS!")

#-------------- Keyboard movement implementations

    def MoveDown(self, event):
        self.cVert(+1)

    def MoveUp(self, event):
        self.cVert(-1)

    def MoveLeft(self, event):
        if self.cx == 0:
            if self.cy == 0:
                wx.Bell()
            else:
                self.cVert(-1)
                self.cx = self.current_line_length
        else:
            self.cx -= 1

    def MoveRight(self, event):
        linelen = self.current_line_length - 1
        if self.cx >= linelen:
            if self.cy == len(self.lines) - 1:
                wx.Bell()
            else:
                self.cx = 0
                self.cVert(1)
        else:
            self.cx += 1

    def MovePageDown(self, event):
        self.cVert(self.sh)

    def MovePageUp(self, event):
        self.cVert(-self.sh)

    def MoveHome(self, event):
        self.cx = 0

    def MoveEnd(self, event):
        self.cx = self.current_line_length

    def MoveStartOfFile(self, event):
        self.cy = 0
        self.cx = 0

    def MoveEndOfFile(self, event):
        self.cy = len(self.lines) - 1
        self.cx = self.current_line_length

    def OnChar(self, event):
        action = {}
        action[wx.WXK_DOWN]  = self.MoveDown
        action[wx.WXK_UP]    = self.MoveUp
        action[wx.WXK_LEFT]  = self.MoveLeft
        action[wx.WXK_RIGHT] = self.MoveRight
        action[wx.WXK_PAGEDOWN]  = self.MovePageDown
        action[wx.WXK_PAGEUP] = self.MovePageUp
        action[wx.WXK_HOME]  = self.MoveHome
        action[wx.WXK_END]   = self.MoveEnd
        key = event.GetKeyCode()
        print("OESUHCOEHUSRCOUHSRCOHEUCROEHUH")
        try:
            action[key](event)
            self.cx = self.table.enforce_valid_cursor(self.cy, self.cx)
            self.UpdateView()
            self.AdjustScrollbars()
        except KeyError:
            print(key)
            event.Skip()

##----------- selection routines

    def start_selection(self):
        self.SelectBegin = (self.cy, self.cx)
        self.SelectEnd = None

    def update_selection(self):
        self.SelectEnd = (self.cy, self.cx)
        self.SelectNotify(self.Selecting, self.SelectBegin, self.SelectEnd)
        self.UpdateView()

    def SelectOff(self):
        self.SelectBegin = None
        self.SelectEnd = None
        self.Selecting = False
        self.SelectNotify(False,None,None)

#----------------------- Eliminate memory leaks

    def OnDestroy(self, event):
        self.mdc = None
        self.odc = None
        self.scrollTimer = None
        self.eofMarker = None

#--------------------  Abstract methods for subclasses

    def OnClick(self):
        pass

    def SelectNotify(self, Selecting, SelectionBegin, SelectionEnd):
        pass

    def zoom_in(self):
        pass

    def zoom_out(self):
        pass

    #### Overrides

    def DrawCaret(self, dc = None):
        if not dc:
            dc = wx.ClientDC(self)

        if (self.table.num_rows)<self.cy: #-1 ?
            self.cy = self.table.num_rows-1
        if self.cy >= 0:
            x = self.cx - self.sx
            y = self.cy - self.sy
            self.DrawSimpleCaret(x, y, dc)

    def DrawSimpleCaret(self, cell_x, cell_y, dc = None, old=False):
        if not dc:
            dc = wx.ClientDC(self)

        t = self.table
        col = t.cell_to_col[cell_x]
        num_cells = t.col_widths[col]
        w = (num_cells * self.cell_width_in_pixels) + 2
        h = self.cell_height_in_pixels + 1
        cell_x = t.col_to_cell[col]
        x = (cell_x * self.cell_width_in_pixels) - 1
        y = (cell_y * self.cell_height_in_pixels)
        self.draw_caret(dc, x, y, w, h)

    def draw_caret(self, dc, x, y, w, h):
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(self.view_params.cursor_pen)
        dc.DrawRectangle(x, y, w, h)
        x -= 1
        y -= 1
        w += 2
        h += 2
        dc.SetPen(wx.Pen(wx.BLACK))
        dc.DrawRectangle(x, y, w, h)
        x -= 1
        y -= 1
        w += 2
        h += 2
        dc.SetPen(self.view_params.cursor_pen)
        dc.DrawRectangle(x, y, w, h)

    def DrawEditText(self, t, style, x, y, dc, num_cells=1):
        #dc.DrawText(t, x * self.cell_width_in_pixels, y * self.cell_height_in_pixels)
        rect = wx.Rect(x * self.cell_width_in_pixels, y * self.cell_height_in_pixels, num_cells * self.cell_width_in_pixels, self.cell_height_in_pixels)
        self.text_renderer.draw_text(dc, rect, t, style)

    def DrawLine(self, sy, line, dc):
        if self.IsLine(line):
            l   = line
            t   = self.lines[l]
            style = self.style[l]
            t   = t[self.sx:]
            style = style[self.sx:]
            self.DrawEditText(t, style, 0, sy - self.sy, dc)

    def Draw(self, odc=None):
        if not odc:
            odc = wx.ClientDC(self)

        dc = wx.BufferedDC(odc)
        if dc.IsOk():
            dc.SetBackgroundMode(wx.SOLID)
            dc.SetBackground(wx.Brush(self.view_params.empty_color))
            dc.Clear()
            for line in range(self.sy, self.sy + self.sh + 1):
                self.DrawLine(line, line, dc)
            self.DrawCaret(dc)


class FixedFontTextWindow(FixedFontDataWindow):
    @property
    def current_line_length(self):
        try:
            return len(self.lines[self.cy])
        except IndexError:
            return 0

    @property
    def num_rows(self):
        return len(self.lines)

    @property
    def num_cells(self):
        return 64


class HexByteImageCache(DrawTextImageCache):
    num_chars = 2

    def draw_cached_text(self, dc, rect, text, style):
        k = (text, style, rect.width, rect.height)
        try:
            bmp = self.cache[k]
        except KeyError:
            bmp = wx.Bitmap(rect.width, rect.height)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmp)
            t = "%02x" % text
            v = self.window
            r = wx.Rect(v.view_params.pixel_width_padding, 0, v.fw * 2, rect.height)
            bg_rect = wx.Rect(0, 0, rect.width, rect.height)
            self.draw_text_to_dc(mdc, bg_rect, r, t, style)
            del mdc  # force the bitmap painting by deleting the gc
            self.cache[k] = bmp
        dc.DrawBitmap(bmp, rect.x, rect.y)

    def draw_text(self, dc, rect, text, style, num_cells=1):
        draw_log.debug(str((rect, text)))
        rect.width = num_cells * self.window.cell_width_in_pixels
        for i, c in enumerate(text):
            draw_log.debug(str((i, c, rect)))
            self.draw_cached_text(dc, rect, c, style[i])
            rect.x += rect.width


class FixedFontNumpyWindow(FixedFontDataWindow):
    def init_renderers(self):
        self.text_renderer = self.table.create_renderer(0, self.view_params, self)

    @property
    def current_line_length(self):
        return self.table.num_cells

    def start_selection(self):
        self.SelectBegin, self.SelectEnd = self.table.get_index_range(self.cy, self.cx)
        self.anchor_start_index, self.anchor_end_index = self.SelectBegin, self.SelectEnd

    def update_selection(self):
        index1, index2 = self.table.get_index_range(self.cy, self.cx)
        if index1 < self.anchor_start_index:
            self.SelectBegin = index1
            self.SelectEnd = self.anchor_end_index
        elif index2 > self.anchor_end_index:
            self.SelectBegin = self.anchor_start_index
            self.SelectEnd = index2
        self.SelectNotify(self.Selecting, self.SelectBegin, self.SelectEnd)
        self.UpdateView()

    def get_style_array(self, index, last_index):
        count = last_index - index
        style = np.zeros(count, dtype=np.uint8)
        if last_index < self.SelectBegin or index >= self.SelectEnd:
            pass
        else:
            for i in range(index, last_index):
                if i >= self.SelectBegin and i < self.SelectEnd:
                    style[i - index] = selected_bit_mask
        return style

    def DrawLine(self, sy, line, dc):
        if self.IsLine(line):
            t = self.table
            if line == 0:
                index = 0
                cell_start = t.start_offset
            else:
                index = (line * t.bytes_per_row) - t.start_offset
                cell_start = 0
            if line == t.num_rows - 1:
                last_index = t.last_valid_index
                cell_end = last_index - index
            else:
                cell_end = t.bytes_per_row - cell_start
                last_index = index + cell_end

            d = self.lines[index:last_index]
            style = self.style[index:last_index]
            self.DrawEditText(d, style, cell_start - self.sx, sy - self.sy, dc)


class FixedFontMultiCellNumpyWindow(FixedFontNumpyWindow):
    def start_selection(self):
        self.SelectBegin, self.SelectEnd = self.table.get_index_range(self.cy, self.cx)
        self.anchor_start_index, self.anchor_end_index = self.SelectBegin, self.SelectEnd

    def update_selection(self):
        index1, index2 = self.table.get_index_range(self.cy, self.cx)
        if index1 < self.anchor_start_index:
            self.SelectBegin = index1
            self.SelectEnd = self.anchor_end_index
        elif index2 > self.anchor_end_index:
            self.SelectBegin = self.anchor_start_index
            self.SelectEnd = index2
        self.SelectNotify(self.Selecting, self.SelectBegin, self.SelectEnd)
        self.UpdateView()

    def DrawEditText(self, t, style, start_x, show_at_x, x_width, y, dc):
        #dc.DrawText(t, x * self.cell_width_in_pixels, y * self.cell_height_in_pixels)
        draw_log.debug("DRAWEDIT: %d %d %d" % (start_x, show_at_x, x_width))
        rect = wx.Rect(show_at_x * self.cell_width_in_pixels, y * self.cell_height_in_pixels, x_width * self.cell_width_in_pixels, self.cell_height_in_pixels)
        self.table.hex_renderer.draw_text(dc, rect, [t], [style], x_width)

    def DrawLine(self, sy, line, dc):
        if self.IsLine(line):
            # import pdb; pdb.set_trace()
            t = self.table
            start_col = t.cell_to_col[self.sx]
            index = line * t.items_per_row
            last_index = (line + 1) * t.items_per_row
            data = self.lines[index:last_index]
            style = self.style[index:last_index]
            for col in range(start_col, t.items_per_row):
                cell_start = t.col_to_cell[col]
                cell_width = t.col_widths[col]
                self.DrawEditText(data[col], style[col], cell_start, cell_start - self.sx, cell_width, sy - self.sy, dc)


class HexTable(object):
    def __init__(self, data, style, bytes_per_row, start_addr, col_widths=None, start_offset_mask=0):
        self.data = data
        self.style = style
        self.start_addr = start_addr
        self.bytes_per_row = bytes_per_row
        if col_widths is None:
            col_widths = [1] * bytes_per_row
        self.items_per_row = len(col_widths)
        self.start_offset = start_addr & start_offset_mask if start_offset_mask else 0
        self.num_rows = ((self.start_offset + len(self.data) - 1) / bytes_per_row) + 1
        self.last_valid_index = len(self.data)
        print(self.data, self.num_rows, self.start_offset, self.start_addr)
        self.calc_cells(col_widths)
        self.calc_labels()

        self.default_renderer = None
        self.hex_renderer = None

    def calc_cells(self, col_widths):
        """
        :param items_per_row: number of entries in each line of the array
        :param col_widths: array, entry containing the number of cells (width)
            required to display that items in that column
        """
        self.col_widths = tuple(col_widths)  # copy to prevent possible weird errors if parent modifies list!
        self.cell_to_col = []
        self.col_to_cell = []
        pos = 0
        for i, width in enumerate(col_widths):
            self.col_to_cell.append(pos)
            self.cell_to_col.extend([i] * width)
            pos += width
        self.num_cells = pos

    def calc_labels(self):
        self.label_start_addr = int(self.start_addr // self.bytes_per_row) * self.bytes_per_row
        self.col_label_text = ["%x" % x for x in range(self.items_per_row)]
        self.label_char_width = 4

    def create_renderer(self, col, view_params, viewer):
        if not self.default_renderer:
            self.default_renderer = DrawTextImageCache(view_params, viewer)
        if not self.hex_renderer:
            self.hex_renderer = HexByteImageCache(view_params, viewer)
        if col is None:
            return self.default_renderer
        return self.hex_renderer

    def enforce_valid_cursor(self, row, cell):
        if cell >= self.num_cells:
            cell = self.num_cells - 1
        index, _ = self.get_index_range(row, cell)
        if index < 0:
            cell = 0
        elif index >= self.last_valid_index:
            cell = self.num_cells - 1
        return cell

    def get_row_label_text(self, start_line, num_lines):
        for line in range(start_line, start_line + num_lines + 1):
            yield line, "%04x" % (self.get_index_of_row(line) + self.start_addr)

    def get_col_labels(self, starting_cell):
        starting_col = self.cell_to_col[starting_cell]
        for col in range(starting_col, self.items_per_row):
            yield self.col_to_cell[col], self.col_widths[col], self.col_label_text[col]

    def is_index_valid(self, index):
        return index > 0 and index <= self.last_valid_index

    def get_index_range(self, row, col):
        """Get the byte offset from start of file given row, col
        position.
        """
        index = row * self.items_per_row + col - self.start_offset
        return index, index + 1

    def get_index_of_row(self, line):
        return (line * self.items_per_row) - self.start_offset

    def index_to_row_col(self, index):
        return divmod(index + self.start_offset, self.items_per_row)


class VariableWidthHexTable(HexTable):
    def get_index_range(self, row, cell):
        """Get the byte offset from start of file given row, col
        position.
        """
        index = row * self.items_per_row
        index += self.cell_to_col[cell]
        return index, index + 1


class FixedFontMixedMultiCellNumpyWindow(FixedFontMultiCellNumpyWindow):
        #             "0A 0X 0Y FF sv-bdizc  00 00 00 LDA $%04x"
        #self.header = " A  X  Y SP sv-bdizc  Opcodes  Assembly"
    pass


class TableViewParams(object):
    def __init__(self):
        self.col_label_border_width = 3
        self.row_label_border_width = 3
        self.row_height_extra_padding = -3
        self.base_cell_width_in_chars = 2
        self.pixel_width_padding = 2
        self.background_color = wx.WHITE
        self.text_color = wx.BLACK
        self.row_header_bg_color = wx.Colour(224, 224, 224)
        self.col_header_bg_color = wx.Colour(224, 224, 224)
        self.highlight_color = wx.Colour(100, 200, 230)
        self.unfocused_cursor_color = (128, 128, 128)
        self.data_color = (224, 224, 224)
        self.empty_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        self.match_background_color = (255, 255, 180)
        self.comment_background_color = (255, 180, 200)
        self.diff_text_color = (255, 0, 0)
        self.cursor_pen = wx.Pen(self.unfocused_cursor_color, 1, wx.SOLID)

        self.text_font = self.NiceFontForPlatform()
        self.header_font = wx.Font(self.text_font).MakeBold()

    def NiceFontForPlatform(self):
        point_size = 10
        family = wx.DEFAULT
        style = wx.NORMAL
        weight = wx.NORMAL
        underline = False
        if wx.Platform == "__WXMAC__":
            face_name = "Monaco"
        elif wx.Platform == "__WXMSW__":
            face_name = "Lucida Console"
        else:
            face_name = "monospace"
        font = wx.Font(point_size, family, style, weight, underline, face_name)
        return font


class HexGridWindow(wx.ScrolledWindow):
    grid_cls = FixedFontNumpyWindow

    def __init__(self, table, view_params, *args, **kwargs):
        wx.ScrolledWindow.__init__ (self, *args, **kwargs)
        self.SetAutoLayout(True)

        self.scroll_delay = 30  # milliseconds

        self.update_dependents = self.update_dependents_null
        self.view_params = view_params
        self.main = self.grid_cls(self, self, table, self.view_params)
        self.top = TopAuxWindow(self, self.main)
        self.left = LeftAuxWindow(self, self.main)
        sizer = wx.FlexGridSizer(2,2,0,0)
        self.corner = sizer.Add(5, 5, 0, wx.EXPAND)
        sizer.Add(self.top, 0, wx.EXPAND)
        sizer.Add(self.left, 0, wx.EXPAND)
        sizer.Add(self.main, 0, wx.EXPAND)
        sizer.AddGrowableCol(1)
        sizer.AddGrowableRow(1)
        self.SetSizer(sizer)
        self.SetTargetWindow(self.main)
        self.set_pane_sizes(3000, 1000)
        self.SetBackgroundColour(self.view_params.col_header_bg_color)
        #self.SetScrollRate(20,20)
        self.map_events()

        self.ShowScrollbars(wx.SHOW_SB_ALWAYS, wx.SHOW_SB_ALWAYS)
        self.main.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.top.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.left.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.update_dependents = self.update_dependents_post_init

    def map_events(self):
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)

        self.main.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.main.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.main.Bind(wx.EVT_MOTION, self.on_motion)
        self.main.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.main.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)
        self.main.Bind(wx.EVT_CHAR, self.main.OnChar)
        self.main.Bind(wx.EVT_PAINT, self.main.OnPaint)
        self.main.Bind(wx.EVT_SIZE, self.main.OnSize)
        self.main.Bind(wx.EVT_WINDOW_DESTROY, self.main.OnDestroy)
        self.main.Bind(wx.EVT_ERASE_BACKGROUND, self.main.OnEraseBackground)

    def recalc_view(self, *args, **kwargs):
        self.main.recalc_view(*args, **kwargs)

    def refresh_view(self, *args, **kwargs):
        self.main.Refresh()

    def on_left_down(self, evt):
        evt.Skip()

    def on_motion(self, evt):
        evt.Skip()

    def on_left_up(self, event):
        print
        print "Title " + str(self)
        print "Position " + str(self.GetPosition())
        print "Size " + str(self.GetSize())
        print "VirtualSize " + str(self.GetVirtualSize())
        event.Skip()
       
    def set_pane_sizes(self, width, height):
        """
        Set the size of the 3 panes as follow:
            - main = width, height
            - top = width, 40
            - left = 80, height
        """
        top_height = self.main.cell_height_in_pixels + self.view_params.col_label_border_width
        left_width = self.main.table.label_char_width * self.main.fw + self.view_params.row_label_border_width
        self.main.SetVirtualSize(wx.Size(width,height))
        #(wt, ht) = self.top.GetSize()
        self.top.SetVirtualSize(wx.Size(width, top_height))
        #(wl, hl) = self.left.GetSize()
        self.left.SetVirtualSize(wx.Size(left_width, height))
        self.corner.SetMinSize(left_width, top_height)
        #self.Layout()
        wx.CallAfter(self.main.SetScrollManager, self)

    def HorizScroll(self, event, eventType):
        if eventType == wx.wxEVT_SCROLLWIN_LINEUP:
            self.main.sx -= 1
        elif eventType == wx.wxEVT_SCROLLWIN_LINEDOWN:
            self.main.sx += 1
        elif eventType == wx.wxEVT_SCROLLWIN_PAGEUP:
            self.main.sx -= self.main.sw
        elif eventType == wx.wxEVT_SCROLLWIN_PAGEDOWN:
            self.main.sx += self.main.sw
        elif eventType == wx.wxEVT_SCROLLWIN_TOP:
            self.main.sx = self.main.cx = 0
        elif eventType == wx.wxEVT_SCROLLWIN_BOTTOM:
            self.main.sx = self.main.max_line_len - self.main.sw
            self.main.cx = self.main.max_line_len
        else:
            self.main.sx = event.GetPosition()

        self.main.HorizBoundaries()

    def VertScroll(self, event, eventType):
        if   eventType == wx.wxEVT_SCROLLWIN_LINEUP:
            self.main.sy -= 1
        elif eventType == wx.wxEVT_SCROLLWIN_LINEDOWN:
            self.main.sy += 1
        elif eventType == wx.wxEVT_SCROLLWIN_PAGEUP:
            self.main.sy -= self.main.sh
        elif eventType == wx.wxEVT_SCROLLWIN_PAGEDOWN:
            self.main.sy += self.main.sh
        elif eventType == wx.wxEVT_SCROLLWIN_TOP:
            self.main.sy = self.main.cy = 0
        elif eventType == wx.wxEVT_SCROLLWIN_BOTTOM:
            self.main.sy = self.main.LinesInFile() - self.main.sh
            self.main.cy = self.main.LinesInFile()
        elif eventType == wx.wxEVT_MOUSEWHEEL:
            # Not a normal scroll event. Wheel scrolling is handled by the
            # scrolled window by a wxEVT_SCROLLWIN_THUMBTRACK, but on GTK its
            # internal value didn't match the scrollbar so it was getting
            # repositioned. This value is only received through the call to
            # on_mouse_wheel below.
            if event < 0:
                self.main.sy += 4
            else:
                self.main.sy -= 4
        else:
            self.main.sy = event.GetPosition()

        self.main.VertBoundaries()

    def on_scroll_window(self, event):
        dir = event.GetOrientation()
        eventType = event.GetEventType()
        if dir == wx.HORIZONTAL:
            self.HorizScroll(event, eventType)
        else:
            self.VertScroll(event, eventType)
        self.main.UpdateView()

    def on_mouse_wheel(self, evt):
        w = evt.GetWheelRotation()
        if evt.ControlDown():
            if w < 0:
                self.main.zoom_out()
            elif w > 0:
                self.main.zoom_in()
        elif not evt.ShiftDown() and not evt.AltDown():
            self.VertScroll(w, wx.wxEVT_MOUSEWHEEL)
            self.main.UpdateView()
        else:
            evt.Skip()

    def update_dependents_null(self):
        pass

    def update_dependents_post_init(self):
        self.top.UpdateView()
        self.left.UpdateView()

    def set_data(self, data, *args, **kwargs):
        self.main.set_data(data, *args, **kwargs)

    def set_cursor_index(self, from_control, rel_pos, first_row=None):
        r, c = self.main.table.index_to_row_col(rel_pos)
        self.main.show_cursor(c, r)
        self.refresh_view()


class NonUniformGridWindow(HexGridWindow):
    grid_cls = FixedFontMultiCellNumpyWindow


       
#For testing
if __name__ == '__main__':
    app = wx.App()
    frame = wx.Frame(None, -1, "Test", size=(400,400))
    splitter = wx.SplitterWindow(frame, -1, style = wx.SP_LIVE_UPDATE)
    splitter.SetMinimumPaneSize(20)
    view_params = TableViewParams()
    style1 = FakeStyle(None)
    table = VariableWidthHexTable(np.arange(1024, dtype=np.uint8), style1, 4, 0x602, [1, 2, 3, 4])
    scroll1 = NonUniformGridWindow(table, view_params, splitter)
    style1.window = scroll1.main
    style2 = FakeStyle(None)
    table = HexTable(np.arange(1024, dtype=np.uint8), style2, 16, 0x602)
    scroll2 = HexGridWindow(table, view_params, splitter)
    style2.window = scroll2.main

    splitter.SplitVertically(scroll1, scroll2)
    frame.Show(True)
    app.MainLoop()
