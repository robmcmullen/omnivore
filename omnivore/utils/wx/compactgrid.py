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



def ForceBetween(min, val, max):
    if val  > max:
        return max
    if val < min:
        return min
    return val


class DrawTextImageCache(object):
    def __init__(self, view_params):
        self.cache = {}
        self.view_params = view_params

    def invalidate(self):
        self.cache = {}

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
        v = self.view_params
        if style & selected_bit_mask:
            dc.SetBrush(v.selected_brush)
            dc.SetPen(v.selected_pen)
            dc.SetBackground(v.selected_brush)
            dc.SetTextBackground(v.selected_background)
        elif style & match_bit_mask:
            dc.SetPen(v.match_pen)
            dc.SetBrush(v.match_brush)
            dc.SetBackground(v.match_brush)
            dc.SetTextBackground(v.match_background)
        elif style & comment_bit_mask:
            dc.SetPen(v.comment_pen)
            dc.SetBrush(v.comment_brush)
            dc.SetBackground(v.comment_brush)
            dc.SetTextBackground(v.comment_background)
        elif style & user_bit_mask:
            dc.SetPen(v.normal_pen)
            dc.SetBrush(v.data_brush)
            dc.SetBackground(v.normal_brush)
            dc.SetTextBackground(v.data_background)
        else:
            dc.SetPen(v.normal_pen)
            dc.SetBrush(v.normal_brush)
            dc.SetBackground(v.normal_brush)
            dc.SetTextBackground(v.normal_background)
        dc.Clear()
        if style & diff_bit_mask:
            dc.SetTextForeground(v.diff_color)
        else:
            dc.SetTextForeground(v.text_color)
        dc.SetFont(v.text_font)
        dc.DrawText(text, fg_rect.x, fg_rect.y)

    def draw_item(self, dc, rect, text, style, widths):
        draw_log.debug(str((text, rect)))
        for i, c in enumerate(text):
            s = style[i]
            self.draw_cached_text(dc, rect, c, s)
            rect.x += widths[i]


class HexByteImageCache(DrawTextImageCache):
    def draw_cached_text(self, dc, rect, text, style):
        k = (text, style, rect.width, rect.height)
        try:
            bmp = self.cache[k]
        except KeyError:
            bmp = wx.Bitmap(rect.width, rect.height)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmp)
            t = "%02x" % text
            padding = self.view_params.pixel_width_padding
            r = wx.Rect(padding, 0, rect.width - (padding * 2), rect.height)
            bg_rect = wx.Rect(0, 0, rect.width, rect.height)
            self.draw_text_to_dc(mdc, bg_rect, r, t, style)
            del mdc  # force the bitmap painting by deleting the gc
            self.cache[k] = bmp
        dc.DrawBitmap(bmp, rect.x, rect.y)

    def draw_item(self, dc, rect, data, style, widths):
        draw_log.debug(str((rect, data)))
        for i, c in enumerate(data):
            draw_log.debug(str((i, c, rect)))
            self.draw_cached_text(dc, rect, c, style[i])
            rect.x += widths[i]


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
        self.unfocused_caret_color = (128, 128, 128)
        self.data_color = (224, 224, 224)
        self.empty_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        self.match_background_color = (255, 255, 180)
        self.comment_background_color = (255, 180, 200)
        self.diff_text_color = (255, 0, 0)
        self.caret_pen = wx.Pen(self.unfocused_caret_color, 1, wx.SOLID)

        self.text_font = self.NiceFontForPlatform()
        self.header_font = wx.Font(self.text_font).MakeBold()

        self.set_paint()
        self.set_font_metadata()

    def set_paint(self):
        self.selected_background = self.highlight_color
        self.selected_brush = wx.Brush(self.highlight_color, wx.SOLID)
        self.selected_pen = wx.Pen(self.highlight_color, 1, wx.SOLID)
        self.normal_background = self.background_color
        self.normal_brush = wx.Brush(self.background_color, wx.SOLID)
        self.normal_pen = wx.Pen(self.background_color, 1, wx.SOLID)
        self.data_background = self.data_color
        self.data_brush = wx.Brush(self.data_color, wx.SOLID)
        self.match_background = self.match_background_color
        self.match_brush = wx.Brush(self.match_background_color, wx.SOLID)
        self.match_pen = wx.Pen(self.match_background_color, 1, wx.SOLID)
        self.comment_background = self.comment_background_color
        self.comment_brush = wx.Brush(self.comment_background_color, wx.SOLID)
        self.comment_pen = wx.Pen(self.comment_background_color, 1, wx.SOLID)

    def set_font_metadata(self):
        dc = wx.MemoryDC()
        dc.SetFont(self.text_font)
        self.text_font_char_width = dc.GetCharWidth()
        self.text_font_char_height = dc.GetCharHeight()
        print(self.text_font_char_width, self.text_font_char_height)
        self.image_caches = {}

    def calc_cell_size_in_pixels(self, chars_per_cell):
        width = self.pixel_width_padding * 2 + self.text_font_char_width * chars_per_cell
        height = self.row_height_extra_padding + self.text_font_char_height
        return width, height

    def calc_text_width(self, text):
        return self.text_font_char_width * len(text)

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

    def calc_image_cache(self, cache_cls):
        try:
            c = self.image_caches[cache_cls]
        except KeyError:
            c = cache_cls(self)
            self.image_caches[cache_cls] = c
        return c


class LineRenderer(object):
    default_image_cache = DrawTextImageCache

    def __init__(self, w, h, num_cells, view_params, image_cache=None, widths=None, col_labels=None):
        self.w = w
        self.h = h
        self.num_cells = num_cells
        if image_cache is None:
            image_cache = view_params.calc_image_cache(self.default_image_cache)
        self.image_cache = image_cache
        self.view_params = view_params
        self.set_cell_metadata(widths)
        self.col_label_text = self.calc_col_labels(col_labels)

    def set_cell_metadata(self, widths):
        """
        :param items_per_row: number of entries in each line of the array
        :param col_widths: array, entry containing the number of cells (width)
            required to display that items in that column
        """
        if widths is None:
            widths = [1] * self.num_cells
        self.col_widths = tuple(widths)  # copy to prevent possible weird errors if parent modifies list!
        self.pixel_widths = [self.w * i for i in self.col_widths]
        self.cell_to_col = []
        self.col_to_cell = []
        pos = 0
        for i, width in enumerate(widths):
            self.col_to_cell.append(pos)
            self.cell_to_col.extend([i] * width)
            pos += width
        self.num_cols = i
        if pos != self.num_cells:
            log.error("Line renderer cell count mismatch: %d cells requested, %d found by totaling widths" % (self.num_cells, pos))
        self.vw = self.w * self.num_cells

    def calc_col_labels(self, labels):
        if labels is None:
            labels = ["%d" % x for x in range(len(self.col_widths))]
        return labels

    def get_col_labels(self, starting_cell, num_cells):
        starting_col = self.cell_to_col[starting_cell]
        last_cell = min(starting_cell + num_cells, self.num_cells) - 1
        last_col = self.cell_to_col[last_cell]
        for col in range(starting_col, last_col + 1):
            yield self.col_to_cell[col], self.col_widths[col], self.col_label_text[col]

    def calc_label_size(self):
        t0 = self.col_label_text[0]
        t1 = self.col_label_text[-1]
        w = max(self.view_params.calc_text_width(t0), self.view_params.calc_text_width(t1))
        return w, self.h

    @property
    def virtual_width(self):
        return self.vw

    def cell_to_pixel(self, line_num, cell_num):
        x = cell_num * self.w
        y = line_num * self.h
        return x, y

    def cell_to_rect(self, line_num, cell_num, num_cells=1):
        x, y = self.cell_to_pixel(line_num, cell_num)
        rect = wx.Rect(x, y, self.w * num_cells, self.h)
        return rect

    def col_to_rect(self, line_num, col):
        cell = self.col_to_cell[col]
        x, y = self.cell_to_pixel(line_num, cell)
        w = self.pixel_widths[col]
        rect = wx.Rect(x, y, w, self.h)
        return rect

    def set_scroll_rate(self, parent):
        parent.SetScrollRate(self.w, self.h)

    def draw(self, dc, line_num, start_item, num_items):
        raise NotImplementedError("implement draw() in subclass!")

    def draw_caret(self, dc, line_num, start_cell, num_cells):
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        rect = self.cell_to_rect(line_num, start_cell, num_cells)
        pen = self.view_params.caret_pen
        dc.SetPen(pen)
        dc.DrawRectangle(rect)
        rect.Inflate(1, 1)
        dc.SetPen(wx.Pen(wx.BLACK))
        dc.DrawRectangle(rect)
        rect.Inflate(1, 1)
        dc.SetPen(pen)
        dc.DrawRectangle(rect)


class TextLineRenderer(LineRenderer):
    def __init__(self, table, view_params, chars_per_cell, image_cache=None):
        self.table = table
        w, h = view_params.calc_cell_size_in_pixels(chars_per_cell)
        LineRenderer.__init__(self, w, h, table.items_per_row, view_params, image_cache)


class HexLineRenderer(TextLineRenderer):
    default_image_cache = HexByteImageCache

    def draw(self, dc, line_num, start_cell, num_cells):
        """
        """
        col = self.cell_to_col[start_cell]
        last_cell = min(start_cell + num_cells, self.num_cells)
        last_col = self.cell_to_col[last_cell - 1] + 1
        t = self.table
        row_start = (line_num * t.items_per_row) - t.start_offset
        index = row_start + col
        if index < 0:
            col -= index
            index = 0
        last_index = row_start + last_col
        if last_index > t.last_valid_index:
            last_index = t.last_valid_index
        if index >= last_index:
            # no items in this line are in the visible scrolled region
            return

        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(dc, rect, data, style, self.pixel_widths[col:col + (last_index - index)])


class FixedFontDataWindow(wx.ScrolledCanvas):
    def __init__(self, parent, settings_obj, table, view_params, line_renderer):

        wx.ScrolledCanvas.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.parent = parent
        self.zoom = 1
        self.SetBackgroundColour(wx.RED)
        self.calc_visible()
        self.next_scroll_time = 0
        self.scroll_timer = wx.Timer(self)
        self.scroll_delay = 100  # milliseconds
        self.carets = []
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: False)
        self.recalc_view(table, view_params, line_renderer)

    def recalc_view(self, table=None, view_params=None, line_renderer=None):
        if view_params is not None:
            self.view_params = view_params
        if table is None:
            table = self.table
        self.SetFocus()
        self.set_table(table)
        if line_renderer is None:
            line_renderer = self.line_renderer
        self.set_renderer(line_renderer)

    def set_table(self, table):
        self.table = table
        self.AdjustScrollbars()

    def set_renderer(self, renderer):
        self.line_renderer = renderer

    @property
    def cell_width_in_pixels(self):
        return self.line_renderer.w

    @property
    def cell_height_in_pixels(self):
        return self.line_renderer.h

    @property
    def lines(self):
        return self.table.data

    @property
    def style(self):
        return self.table.style

    @property
    def page_size(self):
        return self.visible_rows * self.table.items_per_row

    def pixel_pos_to_row_cell(self, x, y):
        sx, sy = self.parent.GetViewStart()
        row  = sy + int(y / self.cell_pixel_height)
        cell = sx + int(x / self.cell_pixel_width)
        return row, cell

    def clamp_row_col(self, row, col):
        sx, sy = self.parent.GetViewStart()
        row2 = ForceBetween(sy, row, sy + self.fully_visible_rows - 1)
        col2 = ForceBetween(sx, col, sx + self.fully_visible_cells - 1)
        print("clamp: before=%d,%d after=%d,%d" % (row, col, row2, col2))
        return row2, col2

    def ensure_visible(self, row, col):
        sx, sy = self.parent.GetViewStart()
        sy2 = ForceBetween(max(0, row - self.visible_rows), sy, row)
        sx2 = ForceBetween(max(0, col - self.visible_cells), sx, col)
        print("ensure_visible: before=%d,%d after=%d,%d" % (sy, sx, sy2, sx2))
        self.parent.move_viewport(sy2, sx2)

    def enforce_valid_caret(self, row, col):
        # restrict row, col to grid boundaries first so we don't get e.g. cells
        # from previous line if cell number is negative
        if col >= self.line_renderer.num_cols:
            col = self.line_renderer.num_cols - 1
        elif col < 0:
            col = 0
        if row >= self.table.num_rows:
            row = self.table.num_rows - 1
        elif row < 0:
            row = 0

        # now make sure we have a valid index to handle partial lines at the
        # first or last row
        index, _ = self.table.get_index_range(row, col)
        if index < 0:
            row = 0
            if col < self.table.start_offset:
                col = self.table.start_offset
        elif index >= self.table.last_valid_index:
            row = self.table.num_rows - 1
            _, c2 = self.table.index_to_row_col(self.last_valid_index)
            if col > c2:
                col = c2 - 1
        return row, col, index

    def on_size(self, event ):
        self.calc_visible()

    def calc_visible(self):
        # For proper buffered painting, the visible_rows must include the
        # (possibly) partially obscured last row.  fully_visible_rows
        # indicates the number of rows without that last partially obscured
        # row (if it exists).
        w, h = self.GetClientSize().Get()
        self.cell_pixel_height = self.parent.line_renderer.h * self.zoom
        self.cell_pixel_width = self.parent.line_renderer.w * self.zoom
        self.fully_visible_rows = int(h / self.cell_pixel_height)
        self.fully_visible_cells = int(w / self.cell_pixel_width)
        self.visible_rows = ((h + self.cell_pixel_height - 1) / self.cell_pixel_height)
        self.visible_cells = ((w + self.cell_pixel_width - 1) / self.cell_pixel_width)

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        self.first_visible_cell, self.first_visible_row = self.parent.GetViewStart()

        px, py = self.parent.CalcUnscrolledPosition(0, 0)
        dc.SetLogicalOrigin(px, py)

        print("on_paint: %dx%d at %d,%d. origin=%d,%d" % (self.visible_cells, self.visible_rows, self.first_visible_cell, self.first_visible_row, px, py))

        line_num = self.first_visible_row
        for line in range(line_num, min(line_num + self.visible_rows, self.table.num_rows)):
            self.line_renderer.draw(dc, line, self.first_visible_cell, self.visible_cells)

        for caret in self.carets:
            r, c = caret
            self.line_renderer.draw_caret(dc, r, c, 1)
     
    def can_scroll(self):
        self.set_scroll_timer()
        if time.time() >  self.next_scroll_time:
            self.next_scroll_time = time.time() + (self.scroll_delay / 1000.0)
            return True
        else:
            return False

    def set_scroll_timer(self):
        print("starting timer")
        self.scroll_timer.Start(self.scroll_delay, True)

    def on_timer(self, event):
        screenX, screenY = wx.GetMousePosition()
        x, y = self.ScreenToClient((screenX, screenY))
        row, cell = self.pixel_pos_to_row_cell(x, y)
        print("on_timer: time=%f pos=%d,%d" % (time.time(), row, cell))
        self.handle_on_motion(event, row, cell)

    def is_left_of_screen(self, sx, col):
        return col < sx

    def handle_left_of_screen(self, col):
        scroll_col = -1
        if col + scroll_col < 0:
            scroll_col = 0
        return scroll_col

    def is_right_of_screen(self, sx, col):
        return col >= sx + self.visible_cells

    def handle_right_of_screen(self, col):
        scroll_col = 1
        if col + scroll_col >= self.visible_cells:
            scroll_col = 0
        return scroll_col

    def is_above_screen(self, sy, row):
        return row < sy

    def handle_above_screen(self, row):
        scroll_row = -1
        if row + scroll_row < 0:
            scroll_row = 0
        return scroll_row

    def is_below_screen(self, sy, row):
        return row >= sy + self.visible_rows

    def handle_below_screen(self, row):
        scroll_row = 1
        if row + scroll_row >= self.visible_rows:
            scroll_row = 0
        return scroll_row

    def get_row_col_from_event(self, evt):
        row, cell = self.pixel_pos_to_row_cell(evt.GetX(), evt.GetY())
        return row, cell

    def on_left_down(self, evt):
        print("left down")
        self.CaptureMouse()

    def on_motion(self, evt, x=None, y=None):
        row, col = self.get_row_col_from_event(evt)
        if evt.LeftIsDown() and self.HasCapture() and not self.scroll_timer.IsRunning():
            self.handle_on_motion(evt, row, col)

    def on_left_up(self, event):
        self.scroll_timer.Stop()
        if not self.HasCapture():
            return
        self.ReleaseMouse()
        print
        print "Title " + str(self)
        print "Position " + str(self.GetPosition())
        print "Size " + str(self.GetSize())
        print "VirtualSize " + str(self.GetVirtualSize())

    def handle_on_motion(self, evt, row, col):
        scroll_row = 0
        scroll_col = 0
        sx, sy = self.GetViewStart()
        if self.is_left_of_screen(sx, col):
            if self.can_scroll():
                scroll_col = self.handle_left_of_screen(sx)
        elif self.is_right_of_screen(sx, col):
            if self.can_scroll():
                scroll_col = self.handle_right_of_screen(sx)
        if self.is_above_screen(sy, row):
            if self.can_scroll():
                scroll_row = self.handle_above_screen(sy)
        elif self.is_below_screen(sy, row):
            if self.can_scroll():
                scroll_row = self.handle_below_screen(sy)
        print("on_motion: loc=%d,%d top=%d,%d size=%d,%d delta: %d, %d" % (row, col, sy, sx, self.visible_rows, self.visible_cells, scroll_row, scroll_col))
        if scroll_row != 0 or scroll_col != 0 or True:
            self.process_motion_scroll(row, col, scroll_row, scroll_col)

    def process_motion_scroll(self, row, col, scroll_row, scroll_col):
        row += scroll_row
        col += scroll_col
        self.ensure_visible(row, col)
        self.carets = [self.clamp_row_col(row, col)]
        self.parent.Refresh()

#-------------- Keyboard movement implementations

    def handle_char_move_down(self, evt, flags):
        self.move_carets(self.table.items_per_row)

    def handle_char_move_up(self, evt, flags):
        self.move_carets(-self.table.items_per_row)

    def handle_char_move_left(self, evt, flags):
        self.move_carets(-1)

    def handle_char_move_right(self, evt, flags):
        self.move_carets(1)

    def handle_char_move_page_down(self, evt, flags):
        self.move_carets(self.page_size)

    def handle_char_move_page_up(self, evt, flags):
        self.move_carets(-self.page_size)

    def handle_char_move_start_of_file(self, evt, flags):
        self.move_carets_to(0)

    def handle_char_move_end_of_file(self, evt, flags):
        self.move_carets_to(self.table.last_valid_index)

    def handle_char_move_start_of_line(self, evt, flags):
        self.move_carets_process_function(self.clamp_left_column)

    def handle_char_move_end_of_line(self, evt, flags):
        self.move_carets_process_function(self.clamp_right_column)

    def clamp_left_column(self, index):
        r, c = self.table.index_to_row_col(index)
        c = 0
        index = max(0, self.table.get_index_range(r, c)[0])
        return index

    def clamp_right_column(self, index):
        r, c = self.table.index_to_row_col(index)
        c = self.table.items_per_row - 1
        index = min(self.table.last_valid_index, self.table.get_index_range(r, c)[0])
        return self.table.get_index_range(r, c)

    def move_carets(self, delta):
        self.carets = [i + delta for i in self.carets]

    def move_carets_to(self, index):
        self.carets = [index]

    def move_carets_process_function(self, func):
        self.move_carets_to(func(self.caret_handler.caret_index))

    def validate_caret_position(self):
        index = self.table.enforce_valid_index(self.carets[0])
        self.carets = [index]

    def on_char(self, event):
        action = {}
        action[wx.WXK_DOWN]  = self.handle_char_move_down
        action[wx.WXK_UP]    = self.handle_char_move_up
        action[wx.WXK_LEFT]  = self.handle_char_move_left
        action[wx.WXK_RIGHT] = self.handle_char_move_right
        action[wx.WXK_PAGEDOWN]  = self.handle_char_move_page_down
        action[wx.WXK_PAGEUP] = self.handle_char_move_page_up
        action[wx.WXK_HOME]  = self.handle_char_move_home
        action[wx.WXK_END]   = self.handle_char_move_end
        key = event.GetKeyCode()
        try:
            action[key](event)
            self.cx = self.table.enforce_valid_cursor(self.cy, self.cx)
            self.UpdateView()
            self.AdjustScrollbars()
        except KeyError:
            print(key)
            event.Skip()

    def zoom_in(self):
        pass

    def zoom_out(self):
        pass


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
        self.table.hex_renderer.draw(dc, rect, [t], [style], x_width)

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
    """Table works in rows and columns, knows nothing about display cells.

    Each column may be displayed across an integer number of cells which is
    controlled by the line renderer.
    """
    def __init__(self, data, style, items_per_row, start_addr, start_offset_mask=0):
        self.data = data
        self.style = style
        self.start_addr = start_addr
        self.items_per_row = items_per_row
        self.start_offset = start_addr & start_offset_mask if start_offset_mask else 0
        self.num_rows = ((self.start_offset + len(self.data) - 1) / items_per_row) + 1
        self.last_valid_index = len(self.data)
        print(self.data, self.num_rows, self.start_offset, self.start_addr)
        self.calc_labels()

    def calc_labels(self):
        self.label_start_addr = int(self.start_addr // self.items_per_row) * self.items_per_row
        self.label_char_width = 4

    def enforce_valid_index(self, index):
        return ForceBetween(0, index, self.last_valid_index)

    def get_row_label_text(self, start_line, num_lines):
        last_line = min(start_line + num_lines, self.num_rows)
        for line in range(start_line, last_line):
            yield "%04x" % (self.get_index_of_row(line) + self.start_addr)

    def calc_row_label_width(self, view_params):
        r = list(self.get_row_label_text(0, 1))
        if r:
            r0 = r[0]
            r1 = list(self.get_row_label_text(self.num_rows - 1, 1))[0]
            return max(view_params.calc_text_width(r0), view_params.calc_text_width(r1))
        return 20

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


class AuxWindow(wx.ScrolledCanvas):
    def __init__(self, parent, main, label_char_width=10):
        wx.ScrolledCanvas.__init__(self, parent, -1)
        self.main = main
        self.label_char_width = label_char_width
        self.isDrawing = False
        self.EnableScrolling(False, False)
        self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: False)

    def on_size(self, event):
        self.AdjustScrollbars()
        self.SetFocus()

    def UpdateView(self, dc = None):
        if dc is None:
            dc = wx.ClientDC(self)
        if dc.IsOk():
            self.Draw(dc)

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        if self.isDrawing:
            return
        self.isDrawing = True
        self.UpdateView(dc)
        self.isDrawing = False


class RowLabelWindow(AuxWindow):
    def DrawVertText(self, t, line, dc):
        y = line * self.main.line_renderer.h
        #print("row: y=%d line=%d text=%s" % (y, line, t))
        dc.DrawText(t, 0, y)

    def Draw(self, odc=None):
        if odc is None:
            odc = wx.ClientDC(self)

        s = self.main
        #dc = wx.BufferedDC(odc)
        dc = odc
        _, row = s.parent.GetViewStart()
        if dc.IsOk():
            px, py = s.parent.CalcUnscrolledPosition(0, 0)
            dc.SetLogicalOrigin(0, py)
            dc.SetFont(s.view_params.header_font)
            dc.SetBackgroundMode(wx.SOLID)
            dc.SetTextBackground(s.view_params.row_header_bg_color)
            dc.SetTextForeground(s.view_params.text_color)
            dc.SetBackground(wx.Brush(s.view_params.row_header_bg_color))
            dc.Clear()
            for header in s.table.get_row_label_text(row, s.visible_rows):
                self.DrawVertText(header, row, dc)
                row += 1

class ColLabelWindow(AuxWindow):
    def DrawHorzText(self, t, cell, num_cells, dc):
        lr = self.main.line_renderer
        rect = lr.cell_to_rect(0, cell)
        width = self.main.view_params.calc_text_width(t)
        offset = (rect.width - width)/2  # center text in cell
        dc.DrawText(t, rect.x + offset, 0)

    def Draw(self, odc=None):
        if odc is None:
            odc = wx.ClientDC(self)

        #dc = wx.BufferedDC(odc)
        dc = odc
        s = self.main
        cell, _ = s.parent.GetViewStart()
        if dc.IsOk():
            px, py = s.parent.CalcUnscrolledPosition(0, 0)
            dc.SetLogicalOrigin(px, 0)
            dc.SetFont(s.view_params.header_font)
            dc.SetBackgroundMode(wx.SOLID)
            dc.SetTextBackground(s.view_params.col_header_bg_color)
            dc.SetTextForeground(s.view_params.text_color)
            dc.SetBackground(wx.Brush(s.view_params.col_header_bg_color))
            dc.Clear()
            print("col label starting cell: %d, visible: %d" % (cell, s.visible_cells))
            for cell, num_cells, header in s.line_renderer.get_col_labels(cell, s.visible_cells):
                self.DrawHorzText(header, cell, num_cells, dc)


class HexGridWindow(wx.ScrolledWindow):
    grid_cls = FixedFontNumpyWindow
    line_renderer_cls = HexLineRenderer

    def __init__(self, table, view_params, chars_per_cell, *args, **kwargs):
        wx.ScrolledWindow.__init__ (self, *args, **kwargs)
        self.SetAutoLayout(True)

        self.scroll_delay = 30  # milliseconds

        self.update_dependents = self.update_dependents_null
        self.line_renderer = self.line_renderer_cls(table, view_params, chars_per_cell)
        self.col_label_renderer = self.line_renderer
        self.row_label_renderer = self.line_renderer
        self.view_params = view_params
        self.main = self.grid_cls(self, self, table, self.view_params, self.line_renderer)
        self.top = ColLabelWindow(self, self.main)
        self.left = RowLabelWindow(self, self.main)
        sizer = wx.FlexGridSizer(2,2,0,0)
        self.corner = sizer.Add(5, 5, 0, wx.EXPAND)
        sizer.Add(self.top, 0, wx.EXPAND)
        sizer.Add(self.left, 0, wx.EXPAND)
        sizer.Add(self.main, 0, wx.EXPAND)
        sizer.AddGrowableCol(1)
        sizer.AddGrowableRow(1)
        self.SetSizer(sizer)
        self.SetTargetWindow(self.main)
        self.set_pane_sizes(self.line_renderer.virtual_width, table.num_rows * self.line_renderer.h)
        self.line_renderer.set_scroll_rate(self)
        self.SetBackgroundColour(self.view_params.col_header_bg_color)
        self.map_events()

        self.ShowScrollbars(wx.SHOW_SB_ALWAYS, wx.SHOW_SB_ALWAYS)
        self.main.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.top.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.left.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.update_dependents = self.update_dependents_post_init

    def map_events(self):
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)

        self.main.Bind(wx.EVT_LEFT_DOWN, self.main.on_left_down)
        self.main.Bind(wx.EVT_LEFT_UP, self.main.on_left_up)
        self.main.Bind(wx.EVT_MOTION, self.main.on_motion)
        self.main.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.main.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)
        self.main.Bind(wx.EVT_CHAR, self.main.on_char)
        self.main.Bind(wx.EVT_PAINT, self.main.on_paint)
        self.main.Bind(wx.EVT_SIZE, self.main.on_size)
        self.main.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: False)

    def recalc_view(self, *args, **kwargs):
        self.main.recalc_view(*args, **kwargs)

    def refresh_view(self, *args, **kwargs):
        self.Refresh()
        self.top.Refresh()
        self.left.Refresh()
       
    def set_pane_sizes(self, width, height):
        """
        Set the size of the 3 panes as follow:
            - main = width, height
            - top = width, 40
            - left = 80, height
        """
        w, h = self.col_label_renderer.calc_label_size()
        top_height = h + self.view_params.col_label_border_width
        w = self.main.table.calc_row_label_width(self.view_params)
        left_width = w + self.view_params.row_label_border_width
        self.main.SetVirtualSize(wx.Size(width,height))
        #(wt, ht) = self.top.GetSize()
        self.top.SetVirtualSize(wx.Size(width, top_height))
        #(wl, hl) = self.left.GetSize()
        self.left.SetVirtualSize(wx.Size(left_width, height))
        self.corner.SetMinSize(left_width, top_height)
        #self.Layout()


    def on_scroll_window(self, event):
        """
        OnScrollWindow Event Callback. This should let the main panel scroll in
        both direction but transmit the vertical scrolling to the left panel
        and the horizontal scrolling to the top window
        """
        sx,sy = self.GetScrollPixelsPerUnit()
        if event.GetOrientation() == wx.HORIZONTAL:
            dx = event.GetPosition()
            dy = self.GetScrollPos(wx.VERTICAL)
        else:
            dx = self.GetScrollPos(wx.HORIZONTAL)
            dy = event.GetPosition()
       
        pos = (dx ,dy)
        print "scrolling..." + str(pos) + str(event.GetPosition())
        self.Scroll(dx, dy)
        # self.main.Scroll(dx, dy)
        #self.top.Scroll(dx, 0)
        #self.left.Scroll(0, dy)
        self.Refresh()
        event.Skip()

    def move_viewport(self, row, col):
        # self.main.SetScrollPos(wx.HORIZONTAL, col)
        # self.main.SetScrollPos(wx.VERTICAL, row)
        self.Scroll(col, row)
        self.left.Scroll(0, row)
        self.top.Scroll(col, 0)
        print("viewport: %d,%d" % (row, col))
        self.Refresh()

    def on_mouse_wheel(self, evt):
        print("on_mouse_wheel")
        w = evt.GetWheelRotation()
        if evt.ControlDown():
            if w < 0:
                self.main.zoom_out()
            elif w > 0:
                self.main.zoom_in()
        # elif not evt.ShiftDown() and not evt.AltDown():
        #     self.VertScroll(w, wx.wxEVT_MOUSEWHEEL)
        #     self.main.UpdateView()
        else:
            evt.Skip()

    def update_dependents_null(self):
        pass

    def update_dependents_post_init(self):
        self.top.UpdateView()
        self.left.UpdateView()

    def set_data(self, data, *args, **kwargs):
        self.main.set_data(data, *args, **kwargs)

    def set_caret_index(self, from_control, rel_pos, first_row=None):
        r, c = self.main.table.index_to_row_col(rel_pos)
        self.main.show_caret(c, r)
        self.refresh_view()


class NonUniformGridWindow(HexGridWindow):
    grid_cls = FixedFontMultiCellNumpyWindow


       
#For testing
if __name__ == '__main__':
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

    class FakeStyle(object):
        def __init__(self):
            self.window = None

        def set_window(self, window):
            self.window = window
            self.window.SelectBegin = 20
            self.window.SelectEnd = 100

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

    app = wx.App()
    frame = wx.Frame(None, -1, "Test", size=(400,400))
    splitter = wx.SplitterWindow(frame, -1, style = wx.SP_LIVE_UPDATE)
    splitter.SetMinimumPaneSize(20)
    view_params = TableViewParams()
    # style1 = FakeStyle()
    # table = VariableWidthHexTable(np.arange(1024, dtype=np.uint8), style1, 4, 0x602, [1, 2, 3, 4])
    # scroll1 = NonUniformGridWindow(table, view_params, splitter)
    # style1.set_window(scroll1.main)
    style1 = FakeStyle()
    table = HexTable(np.arange(1024, dtype=np.uint8), style1, 16, 0x600, 0xf)
    scroll1 = HexGridWindow(table, view_params, 2, splitter)
    style1.set_window(scroll1.main)
    style2 = FakeStyle()
    table = HexTable(np.arange(1024, dtype=np.uint8), style2, 16, 0x602, 0xf)
    scroll2 = HexGridWindow(table, view_params, 2, splitter)
    style2.set_window(scroll2.main)

    splitter.SplitVertically(scroll1, scroll2)
    frame.Show(True)
    app.MainLoop()
