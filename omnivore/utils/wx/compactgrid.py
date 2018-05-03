import time

import wx
import numpy as np

try:
    from atrcopy import match_bit_mask, comment_bit_mask, user_bit_mask, selected_bit_mask, diff_bit_mask
except ImportError:
    user_bit_mask = 0x07
    diff_bit_mask = 0x10
    match_bit_mask = 0x20
    comment_bit_mask = 0x40
    selected_bit_mask = 0x80

import logging
logging.basicConfig()
logger = logging.getLogger()
# logger.setLevel(logging.INFO)
log = logging.getLogger(__name__)
draw_log = logging.getLogger("draw")
scroll_log = logging.getLogger("scroll")
# draw_log.setLevel(logging.DEBUG)
debug_refresh = False


def ForceBetween(min, val, max):
    if val  > max:
        return max
    if val < min:
        return min
    return val


def NiceFontForPlatform():
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


class DrawTextImageCache(object):
    def __init__(self, use_cache=True):
        self.cache = {}
        if use_cache:
            self.draw_text = self.draw_cached_text
        else:
            self.draw_text = self.draw_uncached_text

    def invalidate(self):
        self.cache = {}

    def draw_blank(self, dc, rect):
        dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(rect)

    def draw_cached_text(self, parent, dc, rect, text, style):
        k = (text, style, rect.width, rect.height)
        draw_log.debug(str(k))
        try:
            bmp = self.cache[k]
        except KeyError:
            bmp = wx.Bitmap(rect.width, rect.height)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmp)
            r = wx.Rect(0, 0, rect.width, rect.height)
            self.draw_text_to_dc(parent, mdc, r, r, text, style)
            del mdc  # force the bitmap painting by deleting the gc
            self.cache[k] = bmp
        dc.DrawBitmap(bmp, rect.x, rect.y)

    def draw_uncached_text(self, parent, dc, rect, text, style):
        self.draw_text_to_dc(parent, dc, rect, rect, text, style)

    def prepare_dc_style(self, parent, dc, style):
        v = parent.view_params
        dc.SetPen(wx.TRANSPARENT_PEN)
        if style & selected_bit_mask:
            dc.SetBrush(v.selected_brush)
            dc.SetBackground(v.selected_brush)
            dc.SetTextBackground(v.highlight_background_color)
        elif style & match_bit_mask:
            dc.SetBrush(v.match_brush)
            dc.SetBackground(v.match_brush)
            dc.SetTextBackground(v.match_background_color)
        elif style & comment_bit_mask:
            dc.SetBrush(v.comment_brush)
            dc.SetBackground(v.comment_brush)
            dc.SetTextBackground(v.comment_background_color)
        elif style & user_bit_mask:
            dc.SetBrush(v.data_brush)
            dc.SetBackground(v.normal_brush)
            dc.SetTextBackground(v.data_background_color)
        else:
            dc.SetBrush(v.normal_brush)
            dc.SetBackground(v.normal_brush)
            dc.SetTextBackground(v.background_color)
        if style & diff_bit_mask:
            dc.SetTextForeground(v.diff_text_color)
        else:
            dc.SetTextForeground(v.text_color)
        dc.SetFont(v.text_font)

    def draw_text_to_dc(self, parent, dc, bg_rect, fg_rect, text, style):
        self.prepare_dc_style(parent, dc, style)
        dc.SetClippingRegion(bg_rect)
        dc.DrawRectangle(bg_rect)
        dc.DrawText(text, fg_rect.x, fg_rect.y)
        dc.DestroyClippingRegion()

    def draw_selected_string_to_dc(self, parent, dc, rect, before, selected, after, insertion_point_index):
        v = parent.view_params
        self.prepare_dc_style(parent, dc, 0)
        dc.SetClippingRegion(rect)
        dc.DrawRectangle(rect)
        rect.x += v.pixel_width_padding
        caret_x = rect.x + (insertion_point_index * v.text_font_char_width)
        if before:
            dc.DrawText(before, rect.x, rect.y)
            rect.x += v.text_font_char_width * len(before)
        if selected:
            self.prepare_dc_style(parent, dc, selected_bit_mask)
            selected_width = v.text_font_char_width * len(selected)
            dc.DrawRectangle(rect.x, rect.y, selected_width, rect.height)
            dc.DrawText(selected, rect.x, rect.y)
            rect.x += selected_width
        if after:
            self.prepare_dc_style(parent, dc, 0)
            dc.DrawText(after, rect.x, rect.y)

        dc.SetPen(wx.BLACK_PEN)
        dc.DrawLine(caret_x, rect.y, caret_x, rect.y + rect.height)

        dc.DestroyClippingRegion()

    def draw_item(self, parent, dc, rect, text, style, col_widths, col):
        draw_log.debug(str((text, rect)))
        for i, c in enumerate(text):
            s = style[i]
            self.draw_text(parent, dc, rect, c, s)
            rect.x += col_widths[col + i]


class DrawTableCellImageCache(DrawTextImageCache):
    def draw_item(self, parent, dc, rect, items, style, col_widths, col):
        for i, item in enumerate(items):
            s = style[i]
            text = parent.table.calc_display_text(col + i, item)
            w = col_widths[col + i]
            rect.width = w
            self.draw_text(parent, dc, rect, text, s)
            rect.x += w


class HexByteImageCache(DrawTextImageCache):
    def draw_cached_text(self, parent, dc, rect, text, style):
        k = (text, style, rect.width, rect.height)
        try:
            bmp = self.cache[k]
        except KeyError:
            bmp = wx.Bitmap(rect.width, rect.height)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmp)
            t = "%02x" % text
            padding = parent.view_params.pixel_width_padding
            r = wx.Rect(padding, 0, rect.width - (padding * 2), rect.height)
            bg_rect = wx.Rect(0, 0, rect.width, rect.height)
            self.draw_text_to_dc(parent, mdc, bg_rect, r, t, style)
            del mdc  # force the bitmap painting by deleting the gc
            self.cache[k] = bmp
        dc.DrawBitmap(bmp, rect.x, rect.y)

    def draw_item(self, parent, dc, rect, data, style, col_widths, col):
        draw_log.debug(str((rect, data)))
        for i, c in enumerate(data):
            draw_log.debug(str((i, c, rect)))
            self.draw_text(parent, dc, rect, c, style[i])
            rect.x += col_widths[col + i]


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
        self.highlight_background_color = wx.Colour(100, 200, 230)
        self.unfocused_caret_color = (128, 128, 128)
        self.data_background_color = (224, 224, 224)
        self.empty_background_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        self.match_background_color = (255, 255, 180)
        self.comment_background_color = (255, 180, 200)
        self.diff_text_color = (255, 0, 0)
        self.caret_pen = wx.Pen(self.unfocused_caret_color, 1, wx.SOLID)

        self.text_font = NiceFontForPlatform()
        self.header_font = wx.Font(self.text_font).MakeBold()

        self.set_paint()
        self.set_font_metadata()

    def set_paint(self):
        self.selected_brush = wx.Brush(self.highlight_background_color, wx.SOLID)
        self.normal_brush = wx.Brush(self.background_color, wx.SOLID)
        self.data_brush = wx.Brush(self.data_background_color, wx.SOLID)
        self.match_brush = wx.Brush(self.match_background_color, wx.SOLID)
        self.comment_brush = wx.Brush(self.comment_background_color, wx.SOLID)
        self.empty_brush = wx.Brush(self.empty_background_color, wx.SOLID)

    def set_font_metadata(self):
        dc = wx.MemoryDC()
        dc.SetFont(self.text_font)
        self.text_font_char_width = dc.GetCharWidth()
        self.text_font_char_height = dc.GetCharHeight()
        self.image_caches = {}

    def calc_cell_size_in_pixels(self, chars_per_cell):
        width = self.pixel_width_padding * 2 + self.text_font_char_width * chars_per_cell
        height = self.row_height_extra_padding + self.text_font_char_height
        return width, height

    def calc_text_width(self, text):
        return self.text_font_char_width * len(text)

    def calc_image_cache(self, cache_cls):
        try:
            c = self.image_caches[cache_cls]
        except KeyError:
            c = cache_cls(self)
            self.image_caches[cache_cls] = c
        return c


class LineRenderer(object):
    default_image_cache = DrawTextImageCache

    def __init__(self, parent, w, h, num_cols, image_cache=None, widths=None, col_labels=None):
        self.w = w
        self.h = h
        self.num_cols = num_cols
        if image_cache is None:
            image_cache = parent.view_params.calc_image_cache(self.default_image_cache)
        self.image_cache = image_cache
        self.set_cell_metadata(widths)
        self.col_label_text = self.calc_col_labels(col_labels)

    def set_cell_metadata(self, widths):
        """
        :param items_per_row: number of entries in each line of the array
        :param col_widths: array, entry containing the number of cells (width)
            required to display that items in that column
        """
        if widths is None:
            widths = [1] * self.num_cols
        self.col_widths = tuple(widths)  # copy to prevent possible weird errors if parent modifies list!
        self.pixel_widths = [self.w * i for i in self.col_widths]
        self.cell_to_col = []
        self.col_to_cell = []
        pos = 0
        self.vw = 0
        for i, width in enumerate(widths):
            self.col_to_cell.append(pos)
            self.cell_to_col.extend([i] * width)
            pos += width
            self.vw += self.pixel_widths[i]
        self.num_cells = pos

    def calc_col_labels(self, labels):
        if labels is None:
            labels = ["%x" % x for x in range(len(self.col_widths))]
        return labels

    def get_col_labels(self, parent, starting_cell, num_cells):
        starting_col = self.cell_to_col[starting_cell]
        last_cell = min(starting_cell + num_cells, self.num_cells) - 1
        last_col = self.cell_to_col[last_cell]
        for col in range(starting_col, last_col + 1):
            rect = self.col_to_rect(0, col)
            text = self.col_label_text[col]
            if text.startswith('^'):
                text = text[1:]
                offset = 0
            else:
                width = parent.view_params.calc_text_width(text)
                offset = (rect.width - width)/2  # center text in cell
            yield rect, offset, text

    def calc_label_size(self, parent):
        t0 = self.col_label_text[0]
        t1 = self.col_label_text[-1]
        w = max(parent.view_params.calc_text_width(t0), parent.view_params.calc_text_width(t1))
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

    def calc_column_range(self, parent, line_num, col, last_col):
        raise NotImplementedError("override to produce column number and start and end indexes")

    def draw_line(self, parent, dc, line_num, col, index, last_index):
        t = parent.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(parent, dc, rect, data, style, self.pixel_widths, col)

    def draw_grid(self, parent, dc, start_row, visible_rows, start_cell, visible_cells):
        first_col = self.cell_to_col[start_cell]
        last_cell = min(start_cell + visible_cells, self.num_cells)
        last_col = self.cell_to_col[last_cell - 1] + 1

        for row in range(start_row, min(start_row + visible_rows, parent.table.num_rows)):
            try:
                col, index, last_index = self.calc_column_range(parent, row, first_col, last_col)
            except IndexError:
                continue  # skip lines with no visible cells
            self.draw_line(parent, dc, row, col, index, last_index)

    def draw_caret(self, parent, dc, line_num, col):
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        try:
            rect = self.col_to_rect(line_num, col)
        except IndexError:
            log.error("draw_caret: unknown rect for %s" % str((line_num, col)))
            return
        pen = parent.view_params.caret_pen
        dc.SetPen(pen)
        dc.DrawRectangle(rect)
        rect.Inflate(1, 1)
        dc.SetPen(wx.Pen(wx.BLACK))
        dc.DrawRectangle(rect)
        rect.Inflate(1, 1)
        dc.SetPen(pen)
        dc.DrawRectangle(rect)

    def draw_edit_cell(self, parent, dc, line_num, col, edit_source):
        # Mimic the display of a TextCtrl in the cell being drawn
        insertion_point_index = edit_source.GetInsertionPoint()
        highlight_start, highlight_end = edit_source.GetSelection()
        value = edit_source.GetValue()
        log.debug("draw_edit_cell: caret=%d sel=%d-%d value=%s" % (insertion_point_index, highlight_start, highlight_end, value))

        before = value[0:highlight_start]
        selected = value[highlight_start:highlight_end]
        after = value[highlight_end:]

        rect = self.col_to_rect(line_num, col)
        self.image_cache.draw_selected_string_to_dc(parent, dc, rect, before, selected, after, insertion_point_index)

        self.draw_caret(parent, dc, line_num, col)


class DebugLineRenderer(LineRenderer):
    def __init__(self, view_params, chars_per_cell=4, image_cache=None, widths=None, col_labels=None):
        w, h = view_params.calc_cell_size_in_pixels(chars_per_cell)
        LineRenderer.__init__(self, w, h, len(widths), view_params, image_cache, widths, col_labels)

    def calc_column_range(self, parent, line_num, col, last_col):
        return col, 0, last_col - col

    def draw_line(self, parent, dc, line_num, col, index, last_index):
        t = self.table
        rect = self.col_to_rect(line_num, col)
        num = last_index - index
        data = ["r%dc%d" % (line_num, c + col) for c in range(num)]
        style = [0] * num
        self.image_cache.draw_item(parent, dc, rect, data, style, self.pixel_widths, col)


class TableLineRenderer(LineRenderer):
    def __init__(self, parent, chars_per_cell, image_cache=None, widths=None, col_labels=None):
        w, h = parent.view_params.calc_cell_size_in_pixels(chars_per_cell)
        LineRenderer.__init__(self, parent, w, h, parent.table.items_per_row, image_cache, widths, col_labels)

    def calc_column_range(self, parent, line_num, col, last_col):
        t = parent.table
        row_start = (line_num * t.items_per_row) - t.start_offset
        index = row_start + col
        if index < 0:
            col -= index
            index = 0
        last_index = row_start + last_col
        if last_index > t.last_valid_index:
            last_index = t.last_valid_index
        if index >= last_index:
            raise IndexError("No items in this line are in the visible scrolled region")
        return col, index, last_index


class HexLineRenderer(TableLineRenderer):
    default_image_cache = HexByteImageCache

    def draw_line(self, parent, dc, line_num, col, index, last_index):
        t = parent.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(parent, dc, rect, data, style, self.pixel_widths, col)


class BaseGridDrawControl(wx.ScrolledCanvas):
    refresh_count = 0

    def __init__(self, parent):
        wx.ScrolledCanvas.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.parent = parent
        self.offscreen_scroll_divisor = 3
        #self.SetBackgroundColour(wx.RED)
        self.event_row = self.event_col = self.event_modifiers = None
        self.next_scroll_time = 0
        self.last_mouse_event = None
        self.scroll_timer = wx.Timer(self)
        self.scroll_delay = 50  # milliseconds
        self.recalc_view()

        if wx.Platform == "__WXMSW__":
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_windows_erase_background)
        else:
            self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: False)

    ##### properties

    @property
    def table(self):
        return self.parent.table

    @property
    def line_renderer(self):
        return self.parent.line_renderer

    @property
    def cell_width_in_pixels(self):
        return self.parent.line_renderer.w

    @property
    def cell_height_in_pixels(self):
        return self.parent.line_renderer.h

    @property
    def lines(self):
        return self.parent.table.data

    @property
    def style(self):
        return self.parent.table.style

    @property
    def page_size(self):
        return self.visible_rows * self.parent.table.items_per_row

    @property
    def fully_visible_area(self):  # r,c -> r,c
        left_col, top_row = self.parent.GetViewStart()
        right_col = left_col + self.fully_visible_cells - 1
        bot_row = top_row + self.fully_visible_rows - 1
        return top_row, left_col, bot_row, right_col

    ##### wxPython method overrides


    ##### object method overrides


    ##### initialization helpers


    ##### serialization


    ##### event handlers

    def on_size(self, evt):
        self.calc_visible()
        self.parent.calc_scrolling()

    def on_paint(self, evt):
        dc = wx.PaintDC(self)
        self.first_visible_cell, self.first_visible_row = self.parent.GetViewStart()

        px, py = self.parent.CalcUnscrolledPosition(0, 0)
        dc.SetLogicalOrigin(px, py)

        # print("on_paint: %dx%d at %d,%d. origin=%d,%d" % (self.visible_cells, self.visible_rows, self.first_visible_cell, self.first_visible_row, px, py))

        line_num = self.first_visible_row
        self.line_renderer.draw_grid(self.parent, dc, self.first_visible_row, self.visible_rows, self.first_visible_cell, self.visible_cells)
        self.parent.draw_carets(dc, self.first_visible_row, self.visible_rows)
        if debug_refresh:
            dc.DrawText("%d" % self.refresh_count, 0, 0)
            self.refresh_count += 1

    def on_windows_erase_background(self, evt):
        """Windows flickers like crazy when erasing the whole screen, so just
        erase the parts that won't be filled in later.
        """
        dc = evt.GetDC()

        px, py = self.parent.CalcUnscrolledPosition(0, 0)
        dc.SetLogicalOrigin(px, py)

        ch = self.cell_pixel_height
        empty_x = self.line_renderer.vw
        empty_y = self.table.num_rows * ch

        w, h = self.GetClientSize()
        last_x, last_y = self.parent.CalcUnscrolledPosition(w, h)
        #print("size: w,h=%d,%d empty: x,y=%d,%d last: x,y=%d,%d origin=%d,%d" % (w, h, empty_x, empty_y, last_x, last_y, px, py))
 
        dc.SetBrush(self.parent.view_params.empty_brush)
        dc.SetPen(wx.TRANSPARENT_PEN)

        dc.DrawRectangle(empty_x, py, last_x, last_y)  # right side

        # Need to handle special cases: both the first row and last row may be
        # partial, so fill in an extra row. Some of that will get drawn over,
        # but it's not worth actually calculating those parts.

        dc.DrawRectangle(px, py, last_x, ch)  # top
        dc.DrawRectangle(px, empty_y - ch, last_x, last_y)  # bottom

    def on_timer(self, evt):
        screenX, screenY = wx.GetMousePosition()
        x, y = self.ScreenToClient((screenX, screenY))
        row, cell = self.pixel_pos_to_row_cell(x, y)
        # row, col, offscreen = self.calc_desired_caret(row, cell)
        scroll_log.debug("on_timer: time=%f pos=%d,%d" % (time.time(), row, cell))
        # self.handle_on_motion(row, col, offscreen)
        flags = self.parent.create_mouse_event_flags()
        last_row, last_col = self.current_caret_row, self.current_caret_col
        self.handle_user_caret(row, cell, flags)
        if not self.parent.automatic_refresh:
            if last_row != self.current_caret_row or last_col != self.current_caret_col:
                self.parent.handle_select_motion(evt, self.current_caret_row, self.current_caret_col, flags)

    def on_left_down(self, evt):
        if not self.HasFocus():
            self.SetFocus()
        flags = self.parent.create_mouse_event_flags()
        row, cell = self.get_row_cell_from_event(evt)
        self.event_modifiers = evt.GetModifiers()
        self.process_motion_scroll(row, cell, flags)
        self.last_mouse_event = (row, cell)
        self.CaptureMouse()
        self.parent.handle_select_start(evt, self.current_caret_row, self.current_caret_col, flags)

    def on_motion(self, evt, x=None, y=None):
        input_row, input_cell = self.get_row_cell_from_event(evt)
        if (input_row, input_cell) == self.last_mouse_event:
            # only process if mouse has moved to a new cell; no sub-cell
            # events!
            return
        flags = self.parent.create_mouse_event_flags()
        if evt.LeftIsDown() and self.HasCapture():
            last_row, last_col = self.current_caret_row, self.current_caret_col
            self.handle_user_caret(input_row, input_cell, flags)
            if last_row != self.current_caret_row or last_col != self.current_caret_col:
                self.parent.handle_select_motion(evt, self.current_caret_row, self.current_caret_col, flags)
        else:
            col = self.cell_to_col(input_cell)
            self.parent.handle_motion_update_status(evt, input_row, col)
        self.last_mouse_event = (input_row, input_cell)

    def on_left_up(self, evt):
        self.scroll_timer.Stop()
        if not self.HasCapture():
            return
        self.ReleaseMouse()
        self.event_row = self.event_col = self.event_modifiers = None
        self.parent.handle_select_end(evt, self.current_caret_row, self.current_caret_col)

    ##### row/cell/col info

    def pixel_pos_to_row_cell(self, x, y):
        sx, sy = self.parent.GetViewStart()
        row  = sy + int(y / self.cell_pixel_height)
        cell = sx + int(x / self.cell_pixel_width)
        return row, cell

    def cell_to_col(self, cell):
        cell = ForceBetween(0, cell, self.line_renderer.num_cells - 1)
        return self.line_renderer.cell_to_col[cell]

    def pixel_pos_to_row_col(self, x, y):
        row, cell = self.pixel_pos_to_row_cell(x, y)
        col = self.cell_to_col(cell)
        return row, col

    def get_row_cell_from_event(self, evt):
        row, cell = self.pixel_pos_to_row_cell(evt.GetX(), evt.GetY())
        return row, cell

    def is_inside(self, row, col):
        return row >= 0 and row < self.table.num_rows and col >= 0 and col < self.line_renderer.num_cols

    def calc_desired_cell(self, row, cell):
        top_row, left_cell, bot_row, right_cell = self.fully_visible_area
        offscreen = False
        scroll_cell = 0
        scroll_row = 0
        caret_start_cell = self.line_renderer.col_to_cell[self.current_caret_col]
        caret_width = self.line_renderer.col_widths[self.current_caret_col]

        if cell < left_cell:  # off left side
            if caret_start_cell > left_cell:
                # print("LEFT: caret_start_cell=%d caret_width=%d cell=%d left_cell=%d" % (caret_start_cell, caret_width, cell, left_cell))
                new_cell = left_cell
            else:
                delta = left_cell - cell
                # print("LEFT: caret_start_cell=%d caret_width=%d cell=%d left_cell=%d delta=%d" % (caret_start_cell, caret_width, cell, left_cell, delta))
                scroll_cell = -1
                delta = max(delta / self.offscreen_scroll_divisor, 1)
                new_cell = left_cell - delta
                offscreen = True
        elif cell >= right_cell:  # off right side
            if caret_start_cell + caret_width - 1 < right_cell:  # caret was on screen so force to edge
                new_cell = right_cell
            else:
                delta = cell - right_cell
                scroll_cell = 1
                delta = max(delta / self.offscreen_scroll_divisor, 1)
                new_cell = right_cell + delta
                offscreen = True
        else:
            new_cell = cell

        # if scroll_cell != 0:
        #     delta = max(delta / self.offscreen_scroll_divisor, 1)
        #     new_cell = caret_start_cell + (scroll_cell * delta)
        #     offscreen = True

        caret_row = self.current_caret_row
        if row < top_row:
            if caret_row > top_row:
                new_row = top_row
            else:
                delta = top_row - row
                scroll_row = -1
        elif row >= bot_row:
            if caret_row < bot_row:
                new_row = bot_row
            else:
                caret_row = bot_row
                delta = row - bot_row
                scroll_row = 1
        else:
            new_row = row

        if scroll_row != 0:
            delta = max(delta / self.offscreen_scroll_divisor, 1)
            new_row = caret_row + (scroll_row * delta)
            offscreen = True

        # print("desired caret: offscreen=%s user input=%d,%d current=%d,%d new=%d,%d visible=%d,%d -> %d,%d scroll=%d,%d" % (offscreen, row,cell, self.current_caret_row, caret_start_cell, new_row, new_cell, top_row, left_cell, bot_row, right_cell, scroll_row, scroll_cell))
        return new_row, new_cell, offscreen

    def calc_desired_cell_from_event(self, evt):
        row, cell = self.get_row_cell_from_event(evt)
        return self.calc_desired_cell(row, cell)

    ##### row/cell/col utilities

    def clamp_visible_row_cell(self, row, cell):
        sx, sy = self.parent.GetViewStart()
        row2 = ForceBetween(sy, row, sy + self.fully_visible_rows - 1)
        cell2 = ForceBetween(sx, cell, sx + self.fully_visible_cells - 1)
        # print("clamp visible: before=%d,%d after=%d,%d" % (row, cell, row2, cell2))
        return row2, cell2

    def clamp_allowable_row_cell(self, row, cell):
        row2 = ForceBetween(0, row, self.table.num_rows - 1)
        cell2 = ForceBetween(0, cell, self.line_renderer.num_cells - 1)
        # print("clamp allowable: before=%d,%d after=%d,%d" % (row, cell, row2, cell2))
        return row2, cell2

    ##### redrawing

    def recalc_view(self):
        self.calc_visible()

    def calc_visible(self):
        # For proper buffered painting, the visible_rows must include the
        # (possibly) partially obscured last row.  fully_visible_rows
        # indicates the number of rows without that last partially obscured
        # row (if it exists).
        w, h = self.GetClientSize().Get()
        self.cell_pixel_height = self.line_renderer.h
        self.cell_pixel_width = self.line_renderer.w
        self.fully_visible_rows = int(h / self.cell_pixel_height)
        self.fully_visible_cells = int(w / self.cell_pixel_width)
        self.visible_rows = int((h + self.cell_pixel_height - 1) / self.cell_pixel_height)
        self.visible_cells = int((w + self.cell_pixel_width - 1) / self.cell_pixel_width)
        log.debug("fully visible: %d,%d including partial: %d,%d" % (self.fully_visible_rows, self.fully_visible_cells, self.visible_rows, self.visible_cells))

    ##### caret

    def handle_user_caret(self, input_row, input_cell, flags):
        row, cell, offscreen = self.calc_desired_cell(input_row, input_cell)
        if not offscreen or self.can_scroll():
            self.process_motion_scroll(row, cell, flags)

    def update_caret_from_mouse(self, row, cell, flags):
        self.ensure_visible(row, cell, flags)
        col = self.cell_to_col(cell)
        self.current_caret_row, self.current_caret_col = row, col

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
            _, c2 = self.table.index_to_row_col(self.table.last_valid_index)
            if col > c2:
                col = c2 - 1
        return row, col, index

    ##### scrolling

    def can_scroll(self):
        self.set_scroll_timer()
        if time.time() >  self.next_scroll_time:
            self.next_scroll_time = time.time() + (self.scroll_delay / 1000.0)
            return True
        else:
            return False

    def set_scroll_timer(self):
        scroll_log.debug("starting timer")
        self.scroll_timer.Start(self.scroll_delay, True)

    def ensure_visible(self, row, cell, flags):
        sx, sy = self.parent.GetViewStart()
        sy2 = ForceBetween(max(0, row - self.fully_visible_rows + 1), sy, row)
        sx2 = ForceBetween(max(0, cell - self.fully_visible_cells + 1), sx, cell)
        if sx == sx2 and sy == sy2:
            # print("Already visible! Not moving")
            return
        # print("ensure_visible: before=%d,%d after=%d,%d" % (sy, sx, sy2, sx2))
        if self.parent.automatic_refresh:
            self.parent.move_viewport_origin((sy2, sx2))
        else:
            flags.source_control = self.parent
            flags.viewport_origin = (sy2, sx2)
            # print("Moving viewport origin to %d,%d from %s" % (sy2, sx2, flags.source_control))

    def process_motion_scroll(self, row, cell, flags):
        self.ensure_visible(row, cell, flags)
        col = self.cell_to_col(cell)
        index, _ = self.table.get_index_range(row, col)
        self.parent.caret_handler.move_current_caret_to(index)
        if self.parent.automatic_refresh:
            self.parent.Refresh()
        self.current_caret_row, self.current_caret_col = row, col


class NumpyGridDrawControl(BaseGridDrawControl):
    @property
    def current_line_length(self):
        return self.table.num_cells


class HexTable(object):
    """Table works in rows and columns, knows nothing about display cells.

    Each column may be displayed across an integer number of cells which is
    controlled by the line renderer.
    """
    def __init__(self, data, style, items_per_row, start_addr=0, start_offset_mask=0):
        self.data = data
        self.style = style
        self.start_addr = start_addr
        self.items_per_row = items_per_row
        self.start_offset = start_addr & start_offset_mask if start_offset_mask else 0
        self.num_rows = ((self.start_offset + len(self.data) - 1) / items_per_row) + 1
        self.last_valid_index = len(self.data)
        # print(self.data, self.num_rows, self.start_offset, self.start_addr)
        self.calc_labels()

    def calc_labels(self):
        self.label_start_addr = int(self.start_addr // self.items_per_row) * self.items_per_row
        self.label_char_width = 4

    def enforce_valid_index(self, index):
        return ForceBetween(0, index, self.last_valid_index)

    def get_row_label_text(self, start_line, num_lines, step=1):
        last_line = min(start_line + num_lines, self.num_rows)
        for line in range(start_line, last_line, step):
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

    def clamp_index(self, index):
        if index < 0:
            index = 0
        elif index > self.last_valid_index:
            index = self.last_valid_index
        return index

    validate_caret_position = clamp_index

    def get_index_range(self, row, col):
        """Get the byte offset from start of file given row, col
        position.
        """
        index = self.clamp_index(row * self.items_per_row + col - self.start_offset)
        if index >= self.last_valid_index:
            index = self.last_valid_index - 1
        if index < 0:
            index = 0
        return index, index + 1

    def get_index_of_row(self, line):
        return (line * self.items_per_row) - self.start_offset

    def get_start_end_index_of_row(self, row):
        index1, _ = self.get_index_range(row, 0)
        _, index2 = self.get_index_range(row, self.items_per_row - 1)
        return index1, index2

    def index_to_row_col(self, index):
        return divmod(index + self.start_offset, self.items_per_row)

    def clamp_left_column(self, index):
        r, c = self.index_to_row_col(index)
        c = 0
        index = max(0, self.get_index_range(r, c)[0])
        return index

    def clamp_right_column(self, index):
        r, c = self.index_to_row_col(index)
        c = self.items_per_row - 1
        index = min(self.last_valid_index, self.get_index_range(r, c)[0])
        return index


class VariableWidthHexTable(HexTable):
    def get_index_range(self, row, cell):
        """Get the byte offset from start of file given row, col
        position.
        """
        index = row * self.items_per_row
        index += self.cell_to_col[cell]
        return index, index + 1


class AuxWindow(wx.ScrolledCanvas):
    def __init__(self, parent):
        wx.ScrolledCanvas.__init__(self, parent, -1)
        self.parent = parent
        self.set_font_metadata()
        self.isDrawing = False
        self.EnableScrolling(False, False)
        self.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: False)

    def on_size(self, evt):
        #self.SetFocus()  # why?
        pass

    def set_font_metadata(self):
        dc = wx.MemoryDC()
        dc.SetFont(self.parent.view_params.header_font)
        self.char_width = dc.GetCharWidth()
        self.char_height = max(dc.GetCharHeight(), 2)
        self.row_skip = self.calc_row_skip()

    def calc_row_skip(self):
        row_height = self.parent.line_renderer.h
        if row_height < self.char_height + self.parent.view_params.row_height_extra_padding:
            skip = (self.char_height + row_height - 1) // row_height
        else:
            skip = 1
        return skip

    def recalc_view(self, *args, **kwargs):
        self.set_font_metadata()
        self.UpdateView()

    def UpdateView(self, dc = None):
        if dc is None:
            dc = wx.ClientDC(self)
        if dc.IsOk():
            self.draw_header(dc)

    def on_paint(self, evt):
        dc = wx.PaintDC(self)
        if self.isDrawing:
            return
        # upd = wx.RegionIterator(self.GetUpdateRegion())  # get the update rect list
        # r = []
        # while upd.HaveRects():
        #     rect = upd.GetRect()

        #     # Repaint this rectangle
        #     #PaintRectangle(rect, dc)
        #     r.append("update: %s" % str(rect))
        #     upd.Next()
        # size = self.GetClientSize()
        # focused = "(Focused)" if self.HasFocus() else "(Unfocused)"
        # print "Updating %s %s size=%dx%d" % (self.__class__.__name__, focused, size.x, size.y), " ".join(r), "clip: %s" % str(dc.GetClippingRect())
        self.isDrawing = True
        self.UpdateView(dc)
        self.isDrawing = False


class RowLabelWindow(AuxWindow):
    refresh_count = 0

    def draw_row_label_text(self, t, line, dc, skip=1):
        y = line * self.parent.line_renderer.h
        #print("row: y=%d line=%d text=%s" % (y, line, t))
        if skip > 1:
            w, _ = self.GetClientSize()
            dc.DrawLine(0, y, w, y)
        dc.DrawText(t, 0, y)

    def draw_header(self, odc=None):
        if odc is None:
            odc = wx.ClientDC(self)

        s = self.parent
        #dc = wx.BufferedDC(odc)
        dc = odc
        _, row = s.GetViewStart()
        if dc.IsOk():
            px, py = s.CalcUnscrolledPosition(0, 0)
            dc.SetLogicalOrigin(0, py)
            dc.SetFont(s.view_params.header_font)
            dc.SetBackgroundMode(wx.SOLID)
            dc.SetTextBackground(s.view_params.row_header_bg_color)
            dc.SetTextForeground(s.view_params.text_color)
            dc.SetBackground(wx.Brush(s.view_params.row_header_bg_color))
            dc.SetPen(wx.Pen(s.view_params.text_color))
            dc.Clear()
            if self.row_skip > 1:
                # when vertically scrolling, want the tick marks and labels to
                # remain fixed to their respective rows, not always starting
                # from the first visible row and skipping rows from there.
                row = (row // self.row_skip) * self.row_skip
            for header in s.table.get_row_label_text(row, s.main.visible_rows, self.row_skip):
                self.draw_row_label_text(header, row, dc, self.row_skip)
                row += self.row_skip
            if debug_refresh:
                _, row = s.GetViewStart()
                self.draw_row_label_text("%d" % self.refresh_count, row, dc)
                self.refresh_count += 1

class ColLabelWindow(AuxWindow):
    refresh_count = 0

    def draw_col_label_text(self, t, cell, num_cells, dc):
        lr = self.parent.line_renderer
        rect = lr.cell_to_rect(0, cell, num_cells)
        width = self.parent.view_params.calc_text_width(t)
        offset = (rect.width - width)/2  # center text in cell
        dc.DrawText(t, rect.x + offset, 0)

    def draw_header(self, odc=None):
        if odc is None:
            odc = wx.ClientDC(self)

        #dc = wx.BufferedDC(odc)
        dc = odc
        s = self.parent
        cell, _ = s.GetViewStart()
        if dc.IsOk():
            px, py = s.CalcUnscrolledPosition(0, 0)
            dc.SetLogicalOrigin(px, 0)
            dc.SetFont(s.view_params.header_font)
            dc.SetBackgroundMode(wx.SOLID)
            dc.SetTextBackground(s.view_params.col_header_bg_color)
            dc.SetTextForeground(s.view_params.text_color)
            dc.SetBackground(wx.Brush(s.view_params.col_header_bg_color))
            dc.Clear()
            for rect, offset, header in s.line_renderer.get_col_labels(s, cell, s.main.visible_cells):
                dc.DrawText(header, rect.x + offset, 0)
            if debug_refresh:
                cell, _ = s.GetViewStart()
                self.draw_col_label_text("%d" % self.refresh_count, cell, 1, dc)
                self.refresh_count += 1


class MultiCaretHandler(object):
    def __init__(self, table):
        self.carets = []
        self.table = table

    def move_carets(self, delta):
        self.carets = [i + delta for i in self.carets]

    def move_carets_to(self, index):
        self.carets = [index]

    def move_current_caret_to(self, index):
        self.carets = [index]

    def move_carets_process_function(self, func):
        self.move_carets_to(func(self.caret_handler.caret_index))

    def validate_carets(self):
        new_carets = []
        for index in self.carets:
            index = self.validate_caret_position(index)
            new_carets.append(index)
        self.carets = new_carets

    def validate_caret_position(self, index):
        return self.table.enforce_valid_index(index)

    def iter_caret_indexes(self):
        for index in self.carets:
            yield index


class CompactGrid(wx.ScrolledWindow):
    initial_zoom = 1

    def __init__(self, table, view_params, caret_handler, *args, **kwargs):
        wx.ScrolledWindow.__init__ (self, *args, style=wx.WANTS_CHARS, **kwargs)
        self.SetAutoLayout(True)
        self.view_params = view_params
        self.caret_handler = caret_handler
        self.want_col_header = True
        self.want_row_header = True

        self.set_view_param_defaults()

        self.edit_source = None  # if the user is typing in a cell

        # omnivore sets this to false so it can update multiple views at the
        # same time without any double refreshes
        self.automatic_refresh = True

        if table is None:
            table = self.calc_default_table()
        self.table = table
        self.line_renderer = self.calc_line_renderer()
        self.col_label_renderer = self.line_renderer
        self.row_label_renderer = self.line_renderer
        self.main = self.calc_main_grid()
        self.top = ColLabelWindow(self)
        self.left = RowLabelWindow(self)
        self.SetTargetWindow(self.main)
        self.calc_header_sizes()
        self.calc_scrolling()
        self.SetBackgroundColour(self.view_params.col_header_bg_color)
        self.map_events()

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.ShowScrollbars(wx.SHOW_SB_ALWAYS, wx.SHOW_SB_ALWAYS)
        self.main.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.top.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)
        self.left.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)

    ##### wxPython method overrides

    def DoGetBestSize(self):
        """ Base class virtual method for sizer use to get the best size
        """
        left_width, _ = self.calc_header_sizes()
        width = self.main.line_renderer.vw + left_width
        height = -1

        # add in scrollbar width to allow for it if the grid doesn't need it at
        # the moment
        width += wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X) + 1
        best = wx.Size(width, height)

        # Cache the best size so it doesn't need to be calculated again,
        # at least until some properties of the window change
        self.CacheBestSize(best)

        return best

    def SetFocus(self):
        # Windows needs the focus to be explicitly set to the main window to
        # get text events. No harm on Linux/MacOS.
        self.main.SetFocus()

    ##### object method overrides

    def __repr__(self):
        c, r = self.GetViewStart()
        vx, vy = self.main.GetVirtualSize()
        return "%s view_start=%d,%d size=%d,%d vsize=%d,%d" % (self.__class__.__name__, r, c, self.table.num_rows, self.line_renderer.num_cells, vy, vx)

    ##### initialization helpers

    def set_view_param_defaults(self):
        self.scroll_delay = 30  # milliseconds
        self.zoom = 1
        self.min_zoom = 1  # arbitrary
        self.max_zoom = 16  # arbitrary

    def calc_default_table(self):
        # In this generic base class, we don't know enough about the data to
        # generate a table! Subclasses might, though, so allow them the
        # opportunity.
        raise NotImplementedError("no default table implementation defined")

    def calc_line_renderer(self):
        return HexLineRenderer(self, 2)

    def calc_main_grid(self):
        return NumpyGridDrawControl(self)

    def calc_header_sizes(self):
        w, h = self.col_label_renderer.calc_label_size(self)
        top_height = h + self.view_params.col_label_border_width
        w = self.main.table.calc_row_label_width(self.view_params)
        left_width = w + self.view_params.row_label_border_width
        self.top.pixel_height = top_height
        self.left.pixel_width = left_width
        return left_width, top_height

    def calc_scrolling(self):
        lr = self.main.line_renderer
        # left_width = self.left.pixel_width if self.want_row_header else 0
        # top_height = self.top.pixel_height if self.want_col_header else 0
        left_width = self.left.pixel_width
        top_height = self.top.pixel_height
        main_width, main_height = lr.virtual_width, self.main.table.num_rows * lr.h
        self.main.SetScrollbars(lr.w, lr.h, lr.num_cells, self.main.table.num_rows, 0, 0)
        self.top.SetVirtualSize(wx.Size(main_width, top_height))
        self.left.SetVirtualSize(wx.Size(left_width, main_height))
        #self.corner.SetMinSize(left_width, top_height)
        self.SetScrollRate(lr.w, lr.h)

    def map_events(self):
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)
        self.main.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)

        self.map_char_events()
        self.map_mouse_events()

        # These events aren't part of the mouse movement so are kept separate.
        self.main.Bind(wx.EVT_PAINT, self.main.on_paint)
        self.main.Bind(wx.EVT_SIZE, self.main.on_size)
        self.main.Bind(wx.EVT_TIMER, self.main.on_timer)

    def map_char_events(self):
        self.main.Bind(wx.EVT_CHAR, self.on_char)

    def map_mouse_events(self):
        # mouse movement event bindings are here so subclasses don't also have
        # to subclass the NumpyGridDrawControl
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.main.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.main.Bind(wx.EVT_LEFT_DOWN, self.main.on_left_down)
        self.main.Bind(wx.EVT_MOTION, self.main.on_motion)
        self.main.Bind(wx.EVT_LEFT_UP, self.main.on_left_up)
        self.main.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)

    ##### serialization

    def calc_view_params(self):
        col, row = self.GetViewStart()
        return [row, col]  # viewport origin takes row, col!

    def restore_view_params(self, data):
        log.debug("restoring viewport of %s to: %s" % (self, str(data)))
        self.move_viewport_origin(data)
        log.debug("restored viewport of %s to: %s (size: %s)" % (self, str(self.GetViewStart()), str(self.main.GetVirtualSize())))

    def use_default_view_params(self):
        self.move_viewport_origin((0, 0))
        log.debug("restored viewport to default: %s" % str(self.GetViewStart()))

    ##### event handlers

    def on_size(self, evt):
        w, h = self.GetClientSize()
        if self.want_row_header:
            x = self.left.pixel_width
        else:
            x = 0
        if self.want_col_header:
            y = self.top.pixel_height
        else:
            y = 0
        self.main.SetSize(x, y, w - x, h - y)
        self.left.Show(x > 0)
        self.left.SetSize(0, y, x, h - y)
        self.top.Show(y > 0)
        self.top.SetSize(x, 0, w - x, y)

    def on_scroll_window(self, evt):
        """
        OnScrollWindow Event Callback. This should let the main panel scroll in
        both direction but transmit the vertical scrolling to the left panel
        and the horizontal scrolling to the top window
        """
        sx,sy = self.GetScrollPixelsPerUnit()
        if evt.GetOrientation() == wx.HORIZONTAL:
            dx = evt.GetPosition()
            dy = self.GetScrollPos(wx.VERTICAL)
        else:
            dx = self.GetScrollPos(wx.HORIZONTAL)
            dy = evt.GetPosition()
       
        pos = (dx ,dy)
        #print "scrolling..." + str(pos) + str(evt.GetPosition())
        self.Scroll(dx, dy)
        self.main.Scroll(dx, dy)
        self.top.Scroll(dx, 0)
        self.left.Scroll(0, dy)
        self.Refresh()
        evt.Skip()

    def on_mouse_wheel(self, evt):
        w = evt.GetWheelRotation()
        print("on_mouse_wheel rotation=%d, lines_per_action %s" % (w, evt.GetLinesPerAction()))
        if evt.ControlDown():
            if w < 0:
                self.zoom_out()
            elif w > 0:
                self.zoom_in()
        elif not evt.ShiftDown() and not evt.AltDown():
            self.pan_mouse_wheel(evt)
        else:
            evt.Skip()

    def pan_mouse_wheel(self, evt):
        w = evt.GetWheelRotation()
        dx = self.GetScrollPos(wx.HORIZONTAL)
        dy = self.GetScrollPos(wx.VERTICAL)
        dy -= w / self.view_params.text_font_char_height
        self.Scroll(dx, dy)
        self.main.Scroll(dx, dy)
        self.top.Scroll(dx, 0)
        self.left.Scroll(0, dy)
        self.Refresh()

    def on_popup(self, evt):
        # for subclasses
        evt.Skip()

    def on_char(self, evt):
        action = {}
        action[ord('c')] = self.handle_toggle_col_header
        action[ord('r')] = self.handle_toggle_row_header
        action[wx.WXK_DOWN]  = self.handle_char_move_down
        action[wx.WXK_UP]    = self.handle_char_move_up
        action[wx.WXK_LEFT]  = self.handle_char_move_left
        action[wx.WXK_RIGHT] = self.handle_char_move_right
        action[wx.WXK_PAGEDOWN]  = self.handle_char_move_page_down
        action[wx.WXK_PAGEUP] = self.handle_char_move_page_up
        action[wx.WXK_HOME]  = self.handle_char_move_start_of_line
        action[wx.WXK_END]   = self.handle_char_move_end_of_line
        key = evt.GetKeyCode()
        print("Trying %d" % key)
        try:
            action[key](evt, None)
            self.caret_handler.validate_carets()
            #self.UpdateView()
        except KeyError:
            print("Error! %d not recognized" % key)
            evt.Skip()

    ##### redrawing

    def recalc_view(self, *args, **kwargs):
        # if view_params is not None:
        #     self.view_params = view_params
        # if table is not None:
        #     self.table = table
        # if line_renderer is not None:
        #     self.line_renderer = line_renderer
        self.main.recalc_view(*args, **kwargs)
        self.calc_header_sizes()
        self.calc_scrolling()
        self.on_size(None)
        self.left.recalc_view()
        self.top.recalc_view()

    def refresh_view(self, *args, **kwargs):
        self.Refresh()
        self.top.Refresh()
        self.left.Refresh()

    def refresh_headers(self):
        self.top.Refresh()
        self.left.Refresh()

    def process_visibility_change(self):
        focused_before = self.FindFocus()
        self.on_size(None)
        focused_after = self.FindFocus()
        # print("Focused: before=%s after=%s" % (focused_before, focused_after))
        if focused_before != focused_after:
            wx.CallAfter(focused_before.SetFocus)

    def move_viewport_origin(self, row_col_tuple):
        row, col = row_col_tuple
        sx, sy = self.GetViewStart()
        if sx == col and sy == row:
            log.debug("viewport: already at %d,%d" % (row, col))
            # already there!
            return
        self.main.Scroll(col, row)
        self.left.Scroll(0, row)
        self.top.Scroll(col, 0)
        self.Scroll(col, row)
        log.debug("viewport: %d,%d" % (row, col))
        # if self.automatic_refresh:
        #     self.Refresh()

    ##### places for subclasses to process stuff (should really use events)

    def create_mouse_event_flags(self):
        return None

    def handle_on_motion(self, evt, row, col):
        pass

    def handle_motion_update_status(self, evt, row, col):
        pass

    def handle_select_start(self, evt, row, col, flags):
        pass

    def handle_select_motion(self, evt, row, col, flags):
        pass

    def handle_select_end(self, evt, row, col):
        pass

    def zoom_in(self, zoom=1):
        self.set_zoom(self.zoom + zoom)
        self.recalc_view()

    def zoom_out(self, zoom=1):
        self.set_zoom(self.zoom - zoom)
        self.recalc_view()

    def set_zoom(self, zoom):
        if zoom > self.max_zoom:
            zoom = self.max_zoom
        elif zoom < self.min_zoom:
            zoom = self.min_zoom
        self.zoom = zoom

    def set_caret_index(self, rel_pos, flags, refresh=True):
        r, c = self.table.index_to_row_col(rel_pos)
        dummy_flags = self.create_mouse_event_flags()
        self.main.ensure_visible(r, c, dummy_flags)
        if self.automatic_refresh or refresh:
            if dummy_flags.viewport_origin is not None:
                self.move_viewport_origin(dummy_flags.viewport_origin)
                flags.refreshed_as_side_effect.add(self)
                self.refresh_view()

    def draw_carets(self, dc, start_row, visible_rows):
        for index in self.caret_handler.iter_caret_indexes():
            r, c = self.table.index_to_row_col(index)
            if r >= start_row and r < start_row + visible_rows:
                if self.edit_source is not None:
                    log.debug("drawing edit cell at r,c=%d,%d" % (r, c))
                    self.line_renderer.draw_edit_cell(self, dc, r, c, self.edit_source)
                else:
                    log.debug("drawing caret at r,c=%d,%d" % (r, c))
                    self.line_renderer.draw_caret(self, dc, r, c)
            else:
                log.debug("skipping offscreen caret at r,c=%d,%d" % (r, c))

    ##### Keyboard movement implementations

    def advance_caret_position(self):
        self.handle_char_move_right(None, None)

    def handle_toggle_col_header(self, evt, flags):
        self.want_col_header = not self.want_col_header
        self.process_visibility_change()

    def handle_toggle_row_header(self, evt, flags):
        self.want_row_header = not self.want_row_header
        self.process_visibility_change()

    def handle_char_move_down(self, evt, flags):
        self.caret_handler.move_carets(self.table.items_per_row)

    def handle_char_move_up(self, evt, flags):
        self.caret_handler.move_carets(-self.table.items_per_row)

    def handle_char_move_left(self, evt, flags):
        self.caret_handler.move_carets(-1)

    def handle_char_move_right(self, evt, flags):
        self.caret_handler.move_carets(1)

    def handle_char_move_page_down(self, evt, flags):
        self.caret_handler.move_carets(self.page_size)

    def handle_char_move_page_up(self, evt, flags):
        self.caret_handler.move_carets(-self.page_size)

    def handle_char_move_start_of_file(self, evt, flags):
        self.caret_handler.move_carets_to(0)

    def handle_char_move_end_of_file(self, evt, flags):
        self.caret_handler.move_carets_to(self.table.last_valid_index)

    def handle_char_move_start_of_line(self, evt, flags):
        self.caret_handler.move_carets_process_function(self.table.clamp_left_column)

    def handle_char_move_end_of_line(self, evt, flags):
        self.caret_handler.move_carets_process_function(self.table.clamp_right_column)


class DisassemblyTable(HexTable):
    def calc_display_text(self, col, item):
        return "col %d: %s" % (col, str(item))


class NonUniformGridWindow(CompactGrid):
    def calc_line_renderer(self):
        image_cache = DrawTableCellImageCache(self)
        return TableLineRenderer(self, 2, image_cache=image_cache, widths=[5,1,2,4,8])


       
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
    table = DisassemblyTable(np.arange(1024, dtype=np.uint8), style1, 5)
    carets = MultiCaretHandler(table)
    scroll1 = NonUniformGridWindow(table, view_params, carets, splitter)
    style1.set_window(scroll1.main)
    # style1 = FakeStyle()
    # table = HexTable(np.arange(1024, dtype=np.uint8), style1, 16, 0x600, 0xf)
    # carets = MultiCaretHandler(table)
    # scroll1 = CompactGrid(table, view_params, carets, splitter)
    # style1.set_window(scroll1.main)
    style2 = FakeStyle()
    table = HexTable(np.arange(1024, dtype=np.uint8), style2, 16, 0x602, 0xf)
    carets = MultiCaretHandler(table)
    scroll2 = CompactGrid(table, view_params, carets, splitter)
    style2.set_window(scroll2.main)

    splitter.SplitVertically(scroll1, scroll2)
    frame.Show(True)
    app.MainLoop()
