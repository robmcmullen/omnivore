import wx

from .selection_mixin import MouseEventMixin
from omnivore.utils.wx import compactgrid as cg
from omnivore.utils.wx.char_event_mixin import CharEventMixin
from omnivore8bit.arch.disasm import get_style_name

import logging
log = logging.getLogger(__name__)


class SegmentTable(cg.HexTable):
    def __init__(self, segment):
        self.segment = segment
        cg.HexTable.__init__(self, self.segment.data, self.segment.style, 16, self.segment.start_addr, col_widths=None, start_offset_mask=0x0f)

    def get_label_at_index(self, index):
        # Can't just return hex value of index because some segments (like the
        # raw sector segment) use different labels
        return self.segment.label(index, True)


class SegmentGridControl(MouseEventMixin, CharEventMixin, cg.HexGridWindow):
    def __init__(self, parent, segment, caret_handler, view_params):
        MouseEventMixin.__init__(self, caret_handler)
        CharEventMixin.__init__(self, caret_handler)
        table = SegmentTable(segment)
        cg.HexGridWindow.__init__(self, table, view_params, parent)

    def map_events(self):
        self.map_mouse_events(self.main)
        self.map_char_events(self.main)

        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)
        self.main.Bind(wx.EVT_SCROLLWIN, self.on_scroll_window)
        self.main.Bind(wx.EVT_PAINT, self.main.OnPaint)
        self.main.Bind(wx.EVT_SIZE, self.main.OnSize)
        self.main.Bind(wx.EVT_WINDOW_DESTROY, self.main.OnDestroy)
        self.main.Bind(wx.EVT_ERASE_BACKGROUND, self.main.OnEraseBackground)

    @property
    def table(self):
        return self.main.table

    ##### Caret handling

    def handle_char_move_down(self, event):
        self.main.cVert(+1)

    def handle_char_move_up(self, event):
        self.main.cVert(-1)

    def handle_char_move_left(self, event):
        if self.main.cx == 0:
            if self.main.cy == 0:
                wx.Bell()
            else:
                self.main.cVert(-1)
                self.main.cx = self.main.current_line_length
        else:
            self.main.cx -= 1

    def handle_char_move_right(self, event):
        linelen = self.main.current_line_length - 1
        if self.main.cx >= linelen:
            if self.main.cy == len(self.main.lines) - 1:
                wx.Bell()
            else:
                self.main.cx = 0
                self.main.cVert(1)
        else:
            self.main.cx += 1

    def handle_char_move_page_down(self, event):
        self.main.cVert(self.main.sh)

    def handle_char_move_page_up(self, event):
        self.main.cVert(-self.main.sh)

    def handle_char_move_Home(self, event):
        self.main.cx = 0

    def handle_char_move_end(self, event):
        self.main.cx = self.main.current_line_length

    def handle_char_move_start_of_file(self, event):
        self.main.cy = 0
        self.main.cx = 0

    def handle_char_move_end_of_file(self, event):
        self.main.cy = len(self.main.lines) - 1
        self.main.cx = self.main.current_line_length

    def handle_char_move_start_of_line(self, event):
        self.main.cx = 0

    def handle_char_move_end_of_line(self, event):
        self.main.cx = self.main.current_line_length

    def show_new_caret_position(self):
        self.main.cx = self.table.enforce_valid_caret(self.main.cy, self.main.cx)
        self.main.UpdateView()
        self.main.AdjustScrollbars()

    #####

    def get_location_from_event(self, evt):
        row, cell = self.main.pixel_pos_to_row_cell(evt.GetX(), evt.GetY())
        c2 = self.table.enforce_valid_caret(row, cell)
        inside = cell == c2
        index1, index2 = self.table.get_index_range(row, c2)
        return row, 0, index1, index2, inside

    def get_start_end_index_of_row(self, row):
        index1, _ = self.get_index_range(row, 0)
        _, index2 = self.get_index_range(row, self.bytes_per_row - 1)
        return index1, index2

    def get_status_at_index(self, index):
        if self.table.is_index_valid(index):
            label = self.table.get_label_at_index(index)
            message = self.get_status_message_at_index(index)
            return "%s: %s %s" % (self.short_name, label, message)
        return ""

    def get_status_message_at_index(self, index):
        msg = get_style_name(self.table.segment, index)
        comments = self.table.segment.get_comment(index)
        return "%s  %s" % (msg, comments)

    def recalc_view(self):
        raise NotImplementedError("override this in subclass!")
