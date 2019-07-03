import time

import wx
import numpy as np

try:
    from atrip import match_bit_mask, comment_bit_mask, data_bit_mask, selected_bit_mask, diff_bit_mask
except ImportError:
    data_bit_mask = 0x08
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
caret_log = logging.getLogger("caret")
# caret_log.setLevel(logging.DEBUG)
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
        # draw_log.debug(str(k))
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
        elif style & data_bit_mask:
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
        try:
            dc.DrawText(text, fg_rect.x, fg_rect.y)
        except UnicodeDecodeError as e:
            log.error(f"Unicode error drawing text {repr(text)}: {e}")
        dc.DestroyClippingRegion()

    def draw_selected_string_to_dc(self, parent, dc, rect, before, selected, after, insertion_point_index):
        v = parent.view_params
        self.prepare_dc_style(parent, dc, 0)
        dc.SetClippingRegion(rect)
        dc.DrawRectangle(rect)
        rect.x += v.cell_padding_width
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
        # draw_log.debug(str((text, rect)))
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
            padding = parent.view_params.cell_padding_width
            r = wx.Rect(padding, 0, rect.width - (padding * 2), rect.height)
            bg_rect = wx.Rect(0, 0, rect.width, rect.height)
            self.draw_text_to_dc(parent, mdc, bg_rect, r, t, style)
            del mdc  # force the bitmap painting by deleting the gc
            self.cache[k] = bmp
        dc.DrawBitmap(bmp, rect.x, rect.y)

    def draw_item(self, parent, dc, rect, data, style, col_widths, col):
        # draw_log.debug(str((rect, data)))
        for i, c in enumerate(data):
            # draw_log.debug(str((i, c, rect)))
            self.draw_text(parent, dc, rect, c, style[i])
            rect.x += col_widths[col + i]


class TableViewParams(object):
    def __init__(self):
        self.col_label_border_width = 3
        self.row_label_border_width = 3
        self.row_height_extra_padding = -3
        self.base_cell_width_in_chars = 2
        self.cell_padding_width = 2
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
        width = self.cell_padding_width * 2 + self.text_font_char_width * chars_per_cell
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
        self.col_label_drawing_info = self.calc_col_label_drawing_info(parent, col_labels)

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
        self.largest_label_width = 0
        self._cell_to_col = []
        self._col_to_cell = []
        pos = 0
        self.vw = 0
        for i, width in enumerate(widths):
            self._col_to_cell.append(pos)
            self._cell_to_col.extend([i] * width)
            pos += width
            self.vw += self.pixel_widths[i]
        self.num_cells = pos

    def calc_col_labels(self, labels):
        if labels is None:
            labels = ["%x" % x for x in range(len(self.col_widths))]
        return labels

    def get_col_labels(self, parent, starting_cell, num_cells):
        starting_col = self._cell_to_col[starting_cell]
        last_cell = min(starting_cell + num_cells, self.num_cells) - 1
        last_col = self._cell_to_col[last_cell]
        for col in range(starting_col, last_col + 1):
            rect, offset, text = self.col_label_drawing_info[col]
            if rect is None:
                continue
            yield rect, offset, text

    def calc_col_label_drawing_info(self, parent, labels):
        labels = self.calc_col_labels(labels)
        info = []
        if labels is None:
            return
        extra_width = 0
        self.largest_label_width = 0
        for col in range(self.num_cols):
            rect = self.col_to_rect(0, col)
            if extra_width > 0:
                extra_width -= rect.width
                info.append((None, None, None))
            else:
                text = labels[col]
                if text.startswith('^'):
                    text = text[1:]
                    offset = 0
                else:
                    offset = None
                width = parent.view_params.calc_text_width(text)
                if width > rect.width:
                    offset = 0
                    extra_width = width - rect.width
                    rect.width = width
                else:
                    offset = (rect.width - width)/2  # center text in cell
                if width > self.largest_label_width:
                    self.largest_label_width = width
                info.append((rect, offset, text))
        return info

    def calc_label_size(self, parent):
        return self.largest_label_width, self.h

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
        cell = self._col_to_cell[col]
        x, y = self.cell_to_pixel(line_num, cell)
        w = self.pixel_widths[col]
        rect = wx.Rect(x, y, w, self.h)
        return rect

    def calc_caret_cells_from_row_col(self, caret_row, caret_col):
        caret_start_cell = self._col_to_cell[caret_col]
        caret_width = self.col_widths[caret_col]
        return caret_start_cell, caret_width

    def cell_to_col(self, row, cell):
        return self._cell_to_col[cell]

    def col_to_cell(self, row, col):
        return self._col_to_cell[col]

    def calc_column_range(self, parent, line_num, col, last_col):
        raise NotImplementedError("override to produce column number and start and end indexes")

    def draw_line(self, parent, dc, line_num, col, index, last_index):
        t = parent.table
        rect = self.col_to_rect(line_num, col)
        data = t.data[index:last_index]
        style = t.style[index:last_index]
        self.image_cache.draw_item(parent, dc, rect, data, style, self.pixel_widths, col)

    def draw_grid(self, parent, dc, start_row, visible_rows, start_cell, visible_cells):
        first_col = self._cell_to_col[start_cell]
        last_cell = min(start_cell + visible_cells, self.num_cells)
        last_col = self._cell_to_col[last_cell - 1] + 1

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
    default_image_cache = DrawTableCellImageCache

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


class VirtualTableImageCache(DrawTableCellImageCache):
    def draw_item_at(self, parent, dc, rect, row, col, last_col, widths):
        for c in range(col, last_col):
            text, style = parent.table.get_value_style(row, col)
            w = widths[c]
            rect.width = w
            self.draw_text_to_dc(parent, dc, rect, rect, text, style)
            rect.x += w
            col += 1


class VirtualTableLineRenderer(TableLineRenderer):
    default_image_cache = VirtualTableImageCache

    def draw(self, parent, dc, line_num, start_cell, num_cells):
        col = self._cell_to_col[start_cell]
        last_cell = min(start_cell + num_cells, self.num_cells)
        last_col = self._cell_to_col[last_cell - 1] + 1
        rect = self.col_to_rect(line_num, col)
        self.image_cache.draw_item_at(parent, dc, rect, line_num, col, last_col, self.pixel_widths)

    def draw_grid(self, parent, dc, start_row, visible_rows, start_cell, visible_cells):
        first_col = self._cell_to_col[start_cell]
        last_cell = min(start_cell + visible_cells, self.num_cells)
        last_col = self._cell_to_col[last_cell - 1] + 1

        for row in range(start_row, min(start_row + visible_rows, parent.table.num_rows)):
            rect = self.col_to_rect(row, first_col)
            self.image_cache.draw_item_at(parent, dc, rect, row, first_col, last_col, self.pixel_widths)

    def calc_column_range(self, parent,line_num, col, last_col):
        index, last_index = parent.table.get_index_range(line_num, col)
        return col, index, last_index


class ConstantWidthImageCache(VirtualTableImageCache):
    def draw_item_at(self, parent, dc, rect, row, col, last_col, width):
        rect.width = width
        for c in range(col, last_col):
            text, style = parent.table.get_value_style(row, col)
            self.draw_text_to_dc(parent, dc, rect, rect, text, style)
            rect.x += width
            col += 1


class VariableWidthLineRenderer(VirtualTableLineRenderer):
    """Table where each row can have a different number of cells
    
    The constraint is that every column in a given row is always the same size;
    that is, each column is the same multiple of cells. Other rows may have
    their own cell width per column, only within a row is every column the same
    width.
    """
    default_image_cache = ConstantWidthImageCache

    def __init__(self, parent, chars_per_cell, col_sizes, cells_per_col, image_cache=None):
        """
        Constructs a table; each entry in col_sizes is the number of columns in
        each row. The number of rows is determined from the size of this array.

        Args:
            parent (CompactGrid): CompactGrid instance
            w (int): pixel width of one cell
            h (int): pixel height of one cell
            col_sizes (list): number of columns in each row
            image_cache (DrawTextImageCache, optional): image cache if
                something other than default is desired
            widths (list, optional): number of cells in a column, one entry
                per row
            col_labels (None, optional): Description
        """
        self.w, self.h = parent.view_params.calc_cell_size_in_pixels(chars_per_cell)
        self.num_cols = -1
        self.col_widths = tuple(col_sizes)
        self.num_rows = len(col_sizes)
        if image_cache is None:
            image_cache = parent.view_params.calc_image_cache(self.default_image_cache)
        self.image_cache = image_cache
        self.set_cell_metadata(cells_per_col)
        self.col_label_drawing_info = self.calc_col_label_drawing_info(parent, None)

    def set_cell_metadata(self, widths):
        """
        :param items_per_row: number of entries in each line of the array
        :param col_widths: array, entry containing the number of cells (width)
            required to display that items in that column
        
        Args:
            widths (list): one entry per row, number of cells in a column
        """
        self.cell_widths = tuple(widths)  # copy to prevent possible weird errors if parent modifies list!
        self.pixel_widths = [self.w * i for i in self.cell_widths]
        self.largest_label_width = 0
        pos = 0
        self.vw = max([c * p for c, p in zip(self.col_widths, self.pixel_widths)])
        self.num_cells = self.vw // self.w

    def calc_col_labels(self, labels):
        return None

    def get_col_labels(self, parent, starting_cell, num_cells):
        return []

    def calc_caret_cells_from_row_col(self, row, col):
        if row > self.num_rows:
            row = -1
        cell = col * self.cell_widths[row]
        cell_width = self.cell_widths[row]
        return cell, cell_width

    def col_to_rect(self, line_num, col):
        cell, _ = self.calc_caret_cells_from_row_col(line_num, col)
        x, y = self.cell_to_pixel(line_num, cell)
        w = self.pixel_widths[line_num]
        rect = wx.Rect(x, y, w, self.h)
        return rect

    def cell_to_col(self, row, cell):
        if row >= self.num_rows:
            row = -1
        col = cell // self.cell_widths[row]
        return col

    def col_to_cell(self, row, col):
        if row >= self.num_rows:
            row = -1
        return col * self.cell_widths[row]

    def calc_column_range(self, parent, line_num, col, last_col):
        t = parent.table
        index, _ = t.get_index_range(line_num, col)
        last_index, _ = t.get_index_range(line_num, last_col)
        return col, index, last_index

    def draw_grid(self, parent, dc, start_row, visible_rows, start_cell, visible_cells):
        for row in range(start_row, min(start_row + visible_rows, parent.table.num_rows)):
            first_col = self.cell_to_col(row, start_cell)
            last_cell = min(start_cell + visible_cells, self.num_cells)
            last_col = min(self.col_widths[row], self.cell_to_col(row, last_cell - 1) + 1)
            rect = self.col_to_rect(row, first_col)
            # print(f"row: {row}, cells:{start_cell}->{last_cell}, cols:{first_col}->{last_col}, {rect}, {self.cell_widths[row]}")
            if first_col < last_col:
                self.image_cache.draw_item_at(parent, dc, rect, row, first_col, last_col, self.pixel_widths[row])


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
        self.table.prepare_for_drawing(self.first_visible_row, self.visible_rows, self.first_visible_cell, self.visible_cells)
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
        flags.refresh_needed = True
        last_row, last_col = self.current_caret_row, self.current_caret_col
        self.handle_user_caret(row, cell, flags)
        if not self.parent.automatic_refresh:
            if last_row != self.current_caret_row or last_col != self.current_caret_col:
                scroll_log.debug(f"on_timer: update to {self.current_caret_row},{self.current_caret_col}")
                self.parent.handle_select_motion(evt, self.current_caret_row, self.current_caret_col, flags)

    ##### row/cell/col info

    def pixel_pos_to_row_cell(self, x, y):
        sx, sy = self.parent.GetViewStart()
        row  = sy + int(y // self.cell_pixel_height)
        cell = sx + int(x // self.cell_pixel_width)
        return row, cell

    def cell_to_col(self, row, cell):
        cell = ForceBetween(0, cell, self.line_renderer.num_cells - 1)
        return self.line_renderer.cell_to_col(row, cell)

    def pixel_pos_to_row_col(self, x, y):
        row, cell = self.pixel_pos_to_row_cell(x, y)
        col = self.cell_to_col(row, cell)
        return row, col

    def get_location_from_col(self, row, col):
        r2, c2, index, index2 = self.main.enforce_valid_caret(row, col)
        inside = col == c2 and row == r2
        return r2, c2, index, index2, inside

    def is_inside(self, row, col):
        return row >= 0 and row < self.table.num_rows and col >= 0 and col < self.line_renderer.num_cols

    def calc_desired_cell(self, row, cell):
        top_row, left_cell, bot_row, right_cell = self.fully_visible_area
        offscreen = False
        scroll_cell = 0
        scroll_row = 0
        caret_start_cell, caret_width = self.line_renderer.calc_caret_cells_from_row_col(self.current_caret_row, self.current_caret_col)

        if cell < left_cell:  # off left side
            if caret_start_cell > left_cell:
                # print("LEFT: caret_start_cell=%d caret_width=%d cell=%d left_cell=%d" % (caret_start_cell, caret_width, cell, left_cell))
                new_cell = left_cell
            else:
                delta = left_cell - cell
                # print("LEFT: caret_start_cell=%d caret_width=%d cell=%d left_cell=%d delta=%d" % (caret_start_cell, caret_width, cell, left_cell, delta))
                scroll_cell = -1
                delta = max(delta // self.offscreen_scroll_divisor, 1)
                new_cell = left_cell - delta
                offscreen = True
        elif cell >= right_cell:  # off right side
            if caret_start_cell + caret_width - 1 < right_cell:  # caret was on screen so force to edge
                new_cell = right_cell
            else:
                delta = cell - right_cell
                scroll_cell = 1
                delta = max(delta // self.offscreen_scroll_divisor, 1)
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
            delta = max(delta // self.offscreen_scroll_divisor, 1)
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
        self.fully_visible_rows = int(h // self.cell_pixel_height)
        self.fully_visible_cells = int(w // self.cell_pixel_width)
        self.visible_rows = int((h + self.cell_pixel_height - 1) // self.cell_pixel_height)
        self.visible_cells = int((w + self.cell_pixel_width - 1) // self.cell_pixel_width)
        log.debug("fully visible: %d,%d including partial: %d,%d" % (self.fully_visible_rows, self.fully_visible_cells, self.visible_rows, self.visible_cells))

    ##### caret

    def handle_user_caret(self, input_row, input_cell, flags):
        row, cell, offscreen = self.calc_desired_cell(input_row, input_cell)
        caret_log.debug(f"handle_user_caret: input={input_row},{input_cell}, desired={row},{cell} offscreen={offscreen} flags={flags}")
        if not offscreen or self.can_scroll():
            self.process_motion_scroll(row, cell, flags)

    def update_caret_from_mouse(self, row, cell, flags):
        self.ensure_visible(row, cell, flags)
        col = self.cell_to_col(row, cell)
        self.current_caret_row, self.current_caret_col = row, col

    def enforce_valid_caret(self, row, col):
        """Can raise IndexError (from get_index_range) to indicate that the
        cursor is in a hidden cell
        """
        # restrict row, col to grid boundaries first so we don't get e.g. cells
        # from previous line if cell number is negative
        row, col = self.table.enforce_valid_row_col(row, col)

        # # now make sure we have a valid index to handle partial lines at the
        # # first or last row
        # index, index2 = self.table.get_index_range(row, col)
        # if index < 0:
        #     row = 0
        #     if col < self.table.start_offset:
        #         col = self.table.start_offset
        # elif index >= self.table.last_valid_index:
        #     row = self.table.num_rows - 1
        #     _, c2 = self.table.index_to_row_col(self.table.last_valid_index)
        #     if col > c2:
        #         col = c2 - 1
        # return row, col, index, index2
        return row, col

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
        """Make sure a `row`, `cell` is visible in the grid.

        Returns boolean to indicate if the position was already visible.
        """
        sx, sy = self.parent.GetViewStart()
        if row < sy:
            sy2 = row
        elif row >= sy + self.fully_visible_rows - 1:
            sy2 = max(0, row - (self.fully_visible_rows - 1))
        else:
            sy2 = sy
        if cell < sx:
            sx2 = cell
        elif self.fully_visible_cells > 0 and cell >= sx + self.fully_visible_cells - 1:
            sx2 = max(0, cell - (self.fully_visible_cells - 1))
        else:
            sx2 = sx
        caret_log.debug(f"ensure_visible: row={row}, cell={cell} sx={sx} sy={sy} sx2={sx2} sy2={sy2} fully_vis: {self.fully_visible_rows}, {self.fully_visible_cells}")
        if sx == sx2 and sy == sy2:
            # print("Already visible! Not moving")
            return True
        caret_log.debug("ensure_visible: before=%d,%d after=%d,%d" % (sy, sx, sy2, sx2))
        if self.parent.automatic_refresh:
            self.parent.move_viewport_origin((sy2, sx2))
        else:
            flags.source_control = self.parent
            flags.viewport_origin = (sy2, sx2)
            caret_log.debug("Moving viewport origin to %d,%d; flags=%s" % (sy2, sx2, flags))
        return False

    def process_motion_scroll(self, row, cell, flags):
        if row < 0:
            row = 0
        elif row >= self.table.num_rows:
            row = self.table.num_rows - 1
        col = self.cell_to_col(row, cell)
        row, col = self.table.enforce_valid_row_col(row, col)
        cell = self.line_renderer.col_to_cell(row, col)
        self.ensure_visible(row, cell, flags)
        self.parent.caret_handler.move_current_caret_to(row, col)
        self.parent.handle_select_motion(None, row, col, flags)
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

    If the view of this table should indent the first line to allow the row
    labels to be even multiples of the number of items per row (e.g. hex view
    where the labels all end in zero), use row_labels_in_multiples at creation
    time.
    """
    def __init__(self, data, style, items_per_row, start_addr=0, row_labels_in_multiples=False):
        # allow subclasses to turn data/style into properties
        if data is not None:
            self.data = data
        if style is not None:
            self.style = style
        self.start_addr = start_addr
        self.items_per_row = items_per_row
        self.start_offset = start_addr % items_per_row if row_labels_in_multiples else 0
        self.init_boundaries()
        # print(self.data, self.num_rows, self.start_offset, self.start_addr)
        self.create_row_labels()

    @property
    def indexes_per_row(self):
        return self.items_per_row

    @property
    def items_per_index(self):
        return self.items_per_row // self.indexes_per_row

    def get_items_in_row(self, line):
        return self.items_per_row

    def init_boundaries(self):
        self.num_rows = self.calc_num_rows()
        self.last_valid_index = self.calc_last_valid_index()

    def calc_num_rows(self):
        return ((self.start_offset + len(self.data) - 1) // self.indexes_per_row) + 1

    def calc_last_valid_index(self):
        return len(self.data)

    def create_row_labels(self):
        self.label_start_addr = int(self.start_addr // self.indexes_per_row) * self.indexes_per_row
        self.label_char_width = 4

    def enforce_valid_index(self, index):
        return ForceBetween(0, index, self.last_valid_index)

    def is_row_col_inside(self, row, col):
        return row >= 0 and row < self.num_rows and col >=0 and col < self.items_per_row

    def enforce_valid_row_col(self, row, col):
        if row < 0:
            row = 0
        elif row >= self.num_rows:
            row = self.num_rows - 1
        if col < 0:
            col = 0
        elif col >= self.items_per_row:
            col = self.items_per_row - 1
        return row, col

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
        return index >= 0 and index <= self.last_valid_index

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
        index = self.clamp_index(row * self.indexes_per_row + (col // self.items_per_index) - self.start_offset)
        if index >= self.last_valid_index:
            index = self.last_valid_index - 1
        if index < 0:
            index = 0
        return index, index + 1

    def get_index_of_row(self, line):
        return (line * self.indexes_per_row) - self.start_offset

    def get_start_end_index_of_row(self, row):
        index1, _ = self.get_index_range(row, 0)
        _, index2 = self.get_index_range(row, self.indexes_per_row - 1)
        return index1, index2

    def index_to_row_col(self, index):
        row, index_of_col = divmod(index + self.start_offset, self.indexes_per_row)
        col = index_of_col * self.items_per_index
        return row, col

    def clamp_left_column(self, r, c):
        c = 0
        return r, c

    def clamp_right_column(self, r, c):
        c = self.items_per_row - 1
        return r, c

    def prepare_for_drawing(self, start_row, visible_rows, start_cell, visible_cells):
        """Called immediately before the line renderer, this is used to
        update any internal structures before drawing takes place.
        """
        pass

    def clear_selected_style(self):
        self.style[:] &= (0xff ^ selected_bit_mask)

    def set_selected_index_range(self, index1, index2):
        self.style[index1:index2] |= selected_bit_mask


class VariableWidthHexTable(HexTable):
    """Table works in rows and columns, knows nothing about display cells.

    Each row may contain any number of columns, but all columns in each row
    must be the same data type (and therefore the same width in the display).
    """
    def __init__(self, data, style, table_description, start_addr=0, row_labels_in_multiples=False):
        self.data = data
        self.style = style
        self.start_addr = start_addr
        self.start_offset = 0
        self.init_table_description(table_description)

    def init_boundaries(self):
        self.num_rows = self.calc_num_rows()
        # last_valid_index calculated in init_table_description

    def calc_num_rows(self):
        return len(self.items_per_row)

    def init_table_description(self, desc):
        self.parse_table_description(desc)
        self.init_boundaries()
        # print(self.data, self.num_rows, self.start_offset, self.start_addr)
        self.create_row_labels()

    def get_items_in_row(self, row):
        return self.items_per_row[row]

    def parse_table_description(self, desc):
        items_per_row = []
        index_of_row = []
        row_of_index = []
        index = 0
        row = 0
        for d in desc:
            s = self.size_of_entry(d)
            if s > 0:
                items_per_row.append(s)
                index_of_row.append(index)
                row_of_index.extend([row] * s)
                # print(f"row_of_index: index={index}, s={s}: {row_of_index}")
                # print(f"index_of_row: {index_of_row}")
                index += s
                row += 1
        self.index_of_row = index_of_row
        self.row_of_index = row_of_index
        self.items_per_row = items_per_row
        self.last_valid_index = index

    def size_of_entry(self, d):
        return d

    def create_row_labels(self):
        pass

    def get_value_style(self, row, col):
        index, _ = self.get_index_range(row, col)
        return str(self.data[index]), self.style[index]

    def is_row_col_inside(self, row, col):
        if row >= 0 and row < self.num_rows:
            return col >=0 and col < self.items_per_row[row]
        return False

    def enforce_valid_row_col(self, row, col):
        if row < 0:
            row = 0
        elif row >= self.num_rows:
            row = self.num_rows - 1
        if col < 0:
            col = 0
        elif col >= self.items_per_row[row]:
            col = self.items_per_row[row] - 1
        return row, col

    def get_index_range(self, row, col):
        """Get the byte offset from start of file given row, col
        position.
        """
        try:
            index = self.index_of_row[row]
        except IndexError:
            if row < 0:
                row = 0
            elif row > self.num_rows:
                row = -1
            index = self.index_of_row[row]
        index = min(index + col, index + self.items_per_row[row])
        return index, index + 1

    def get_index_of_row(self, line):
        return self.index_of_row[line]

    def get_start_end_index_of_row(self, row):
        index1, _ = self.get_index_range(row, 0)
        index2 = index1 + self.items_per_row[row] - 1
        return index1, index2

    def index_to_row_col(self, index):
        try:
            row = self.row_of_index[index]
        except IndexError:
            if index < 0:
                row = 0
                col = 0
            else:
                row = self.num_rows - 1
                col = self.items_per_row[row] - 1
        else:
            start = self.index_of_row[row]
            col = index - start
        # print(f"index_to_row_col: index={index} row={row} col={col}")
        return row, col

    def clamp_right_column(self, r, c):
        c = self.items_per_row[r] - 1
        return r, c


class VirtualTable(HexTable):
    def __init__(self, *args, **kwargs):
        HexTable.__init__(self, None, None, *args, **kwargs)

    def calc_num_rows(self):
        raise NotImplementedError

    def calc_last_valid_index(self):
        raise NotImplementedError

    def get_value_style(self, row, col):
        raise NotImplementedError


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
        _, self.char_height = self.parent.view_params.calc_cell_size_in_pixels(1)
        self.row_skip = self.calc_row_skip()
        self.SetBackgroundColour(self.parent.view_params.empty_background_color)

    def calc_row_skip(self):
        return 1

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

    def calc_row_skip(self):
        row_height = self.parent.line_renderer.h
        if row_height < self.char_height + self.parent.view_params.row_height_extra_padding:
            skip = (self.char_height + row_height - 1) // row_height
        else:
            skip = 1
        return skip

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


##### Main grid

try:
    from .compactgrid_mouse import MouseEventMixin, Caret, MultiCaretHandler, MouseMode, NormalSelectMode, RectangularSelectMode, GridCellTextCtrl, DisplayFlags
except ModuleNotFoundError:
    from compactgrid_mouse import MouseEventMixin, Caret, MultiCaretHandler, MouseMode, NormalSelectMode, RectangularSelectMode, GridCellTextCtrl, DisplayFlags


class CompactGridEvent(wx.PyCommandEvent):
    """This event class is used for all events generated by the CompactGrid
    """
    def __init__(self, type=wx.wxEVT_NULL, compact_grid=None):
        wx.PyCommandEvent.__init__(self, type)
        if compact_grid:
            self.SetEventObject(compact_grid)
            self.SetId(compact_grid.GetId())
        self.flags = None

    def SetFlags(self, flags):
        """The caret flags representing the change that just occurred.
        """
        self.flags = flags

    def GetFlags(self):
        """The caret flags representing the change that just occurred.
        """
        return self.flags


class CompactGrid(wx.ScrolledWindow, MouseEventMixin):
    initial_zoom = 1

    wxEVT_CARET_MOVED = wx.NewEventType()
    EVT_CARET_MOVED = wx.PyEventBinder(wxEVT_CARET_MOVED, 1)

    def __init__(self, table, view_params, caret_handler, mouse_mode_cls, *args, **kwargs):
        wx.ScrolledWindow.__init__ (self, *args, style=wx.WANTS_CHARS, **kwargs)
        self.SetAutoLayout(True)
        self.view_params = view_params
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
        if caret_handler is None:
            caret_handler = self.calc_caret_handler()
        MouseEventMixin.__init__(self, caret_handler, mouse_mode_cls)

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

    def calc_caret_handler(self):
        return MultiCaretHandler()

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

    #### events

    def send_caret_event(self, flags):
        evt = CompactGridEvent(CompactGrid.wxEVT_CARET_MOVED, self)
        evt.SetFlags(flags)
        self.GetEventHandler().ProcessEvent(evt)

    def map_events(self):
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)
        self.main.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)

        self.map_char_events()
        self.map_mouse_events(self.main)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

        # These events aren't part of the mouse movement so are kept separate.
        self.main.Bind(wx.EVT_PAINT, self.main.on_paint)
        self.main.Bind(wx.EVT_SIZE, self.main.on_size)
        self.main.Bind(wx.EVT_TIMER, self.main.on_timer)

    def map_char_events(self):
        self.main.Bind(wx.EVT_CHAR, self.on_char)

    def unmap_events(self):
        self.main.Unbind(wx.EVT_PAINT)
        self.main.Unbind(wx.EVT_SIZE)
        self.main.Unbind(wx.EVT_TIMER)

    def get_row_cell_from_event(self, evt):
        row, cell = self.main.pixel_pos_to_row_cell(evt.GetX(), evt.GetY())
        return row, cell

    def get_row_col_from_event(self, evt):
        row, col = self.main.pixel_pos_to_row_col(evt.GetX(), evt.GetY())
        return row, col, self.main.table.is_row_col_inside(row, col)

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

    ##### command processing

    def process_command(self, cmd):
        log.error(f"No command processor defined for {cmd}")

    def show_popup(self, actions, popup_data):
        log.error("no popup handler defined")

    def add_popup_data(self, evt, data):
        pass

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

    def pan_mouse_wheel(self, evt):
        w = evt.GetWheelRotation()
        dx = self.GetScrollPos(wx.HORIZONTAL)
        dy = self.GetScrollPos(wx.VERTICAL)
        dy -= w // self.view_params.text_font_char_height
        self.Scroll(dx, dy)
        self.main.Scroll(dx, dy)
        self.top.Scroll(dx, 0)
        self.left.Scroll(0, dy)
        self.Refresh()

    def on_char(self, evt):
        action = {}
        action[ord('c')] = self.toggle_col_header
        action[ord('r')] = self.toggle_row_header
        action[wx.WXK_DOWN]  = self.caret_move_down
        action[wx.WXK_UP]    = self.caret_move_up
        action[wx.WXK_LEFT]  = self.caret_move_left
        action[wx.WXK_RIGHT] = self.caret_move_right
        action[wx.WXK_PAGEDOWN]  = self.caret_move_page_down
        action[wx.WXK_PAGEUP] = self.caret_move_page_up
        action[wx.WXK_HOME]  = self.caret_move_start_of_line
        action[wx.WXK_END]   = self.caret_move_end_of_line
        key = evt.GetKeyCode()
        log.debug(f"on_char: trying {key}")
        try:
            action[key](evt, None)
            self.caret_handler.validate_carets()
            caret = self.caret_handler.current
            cell = self.line_renderer.col_to_cell(*caret.rc)
            self.main.ensure_visible(caret.rc[0], cell, None)
            if self.automatic_refresh:
                self.Refresh()
            #self.UpdateView()
        except KeyError:
            log.debug(f"on_char: Error! {key} not recognized")
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
        if row < 0: row = sy
        if col < 0: col = sx
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

    #### carets

    def keep_index_on_screen(self, index, flags):
        row, col = self.table.index_to_row_col(index)
        return self.main.ensure_visible(row, col, flags)

    def keep_caret_on_screen(self, caret, flags):
        cell = self.line_renderer.col_to_cell(*caret.rc)
        return self.main.ensure_visible(caret.rc[0], cell, flags)

    def keep_current_caret_on_screen(self, flags):
        caret = self.caret_handler.current
        return self.keep_caret_on_screen(caret, flags)

    def draw_carets(self, dc, start_row, visible_rows):
        caret_log.debug(f"draw_carets: using caret_handler {self.caret_handler}")
        for caret in self.caret_handler.carets:
            r, c = caret.rc
            if r >= start_row and r < start_row + visible_rows:
                if self.edit_source is not None:
                    caret_log.debug("drawing edit cell at r,c=%d,%d" % (r, c))
                    self.line_renderer.draw_edit_cell(self, dc, r, c, self.edit_source)
                else:
                    caret_log.debug(f"drawing caret at r,c={r},{c} for {self}")
                    self.line_renderer.draw_caret(self, dc, r, c)
            else:
                caret_log.debug("skipping offscreen caret at r,c=%d,%d" % (r, c))

    def calc_primary_caret_visible_info(self):
        start_row = self.main.first_visible_row
        last_row = start_row + self.main.visible_rows
        for caret in self.caret_handler.carets:
            r, c = caret.rc
            if r >= start_row and r < last_row:
                row_info = index, r, r - start_row, c
                break
        else:
            row_info = index, start_row, 0, 0
        return row_info

    def get_selected_ranges(self):
        table = self.table
        ch = self.caret_handler
        ranges = []
        for r in [c.range for c in ch.carets]:
            start, _ = table.get_index_range(*r[0])
            _, end = table.get_index_range(*r[1])
            ranges.append((start, end))
        return ranges

    def get_selected_ranges_including_carets(self, ch=None):
        table = self.table
        if ch is None:
            ch = self.caret_handler
        ranges = []
        for r in [c.range_including_caret for c in ch.carets]:
            start, _ = table.get_index_range(*r[0])
            _, end = table.get_index_range(*r[1])
            ranges.append((start, end))
        return ranges

    def get_current_caret_index(self):
        c = self.caret_handler.current
        index, _ = self.table.get_index_range(c.rc[0], c.rc[1])
        return index

    ##### Keyboard movement implementations

    def advance_caret_position(self, evt, flags):
        self.caret_handler.move_carets_horizontally(self.table, 1, True)

    def toggle_col_header(self, evt, flags):
        self.want_col_header = not self.want_col_header
        self.process_visibility_change()

    def toggle_row_header(self, evt, flags):
        self.want_row_header = not self.want_row_header
        self.process_visibility_change()

    def caret_move_down(self, evt, flags):
        self.caret_handler.move_carets_vertically(self.table, 1)

    def caret_move_up(self, evt, flags):
        self.caret_handler.move_carets_vertically(self.table, -1)

    def caret_move_left(self, evt, flags):
        self.caret_handler.move_carets_horizontally(self.table, -1)

    def caret_move_right(self, evt, flags):
        self.caret_handler.move_carets_horizontally(self.table, 1)

    def caret_move_page_down(self, evt, flags):
        self.caret_handler.move_carets_vertically(self.table, self.page_size)

    def caret_move_page_up(self, evt, flags):
        self.caret_handler.move_carets_vertically(self.table, -self.page_size)

    def caret_move_start_of_file(self, evt, flags):
        self.caret_handler.move_carets_to(0, 0)

    def caret_move_end_of_file(self, evt, flags):
        self.caret_handler.move_carets_to_index(self.table.last_valid_index)

    def caret_move_start_of_line(self, evt, flags):
        self.caret_handler.move_carets_process_function(self.table.clamp_left_column)

    def caret_move_end_of_line(self, evt, flags):
        self.caret_handler.move_carets_process_function(self.table.clamp_right_column)

    #### info

    def get_status_message_at_row_col(self, row, col):
        return ""

    #### UI stuff

    def update_ui_for_selection_change(self):
        pass

class DisassemblyTable(HexTable):
    def calc_display_text(self, col, item):
        return "col %d: %s" % (col, str(item))


class NonUniformGridWindow(CompactGrid):
    def calc_line_renderer(self):
        return VariableWidthLineRenderer(self, 2, self.table.items_per_row, [1,2,1,2,1,1,2,3,5]*10)

    def set_view_param_defaults(self):
        super().set_view_param_defaults()
        self.want_col_header = False

       
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

    app = wx.App()
    frame = wx.Frame(None, -1, "Test", size=(400,400))
    splitter = wx.SplitterWindow(frame, -1, style = wx.SP_LIVE_UPDATE)
    splitter.SetMinimumPaneSize(20)
    view_params = TableViewParams()

    len1 = 1024
    data1 = np.arange(len1, dtype=np.uint8)
    style1 = np.zeros(len1, dtype=np.uint8)
    table1 = DisassemblyTable(data1, style1, 5)
    scroll1 = CompactGrid(table1, view_params, None, None, splitter)

    len2 = 1024
    data2 = np.arange(len2, dtype=np.uint8)
    style2 = np.zeros(len2, dtype=np.uint8)
    table2 = VariableWidthHexTable(data2, style2, [1,2,3,4,32,2,1,1,2]*10, 0x602)
    scroll2 = NonUniformGridWindow(table2, view_params, None, None, splitter)
    # style2.set_window(scroll2.main)

    splitter.SplitVertically(scroll1, scroll2)
    frame.Show(True)
    app.MainLoop()
