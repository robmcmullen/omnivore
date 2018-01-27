import wx

from .mouse_event_mixin import MouseEventMixin
from omnivore.utils.command import DisplayFlags
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


class UniformNumpyWindow(cg.FixedFontNumpyWindow):
    # Mostly overrides to put the control into the SegmentGridControl rather
    # than the lower level main window
    def init_timer(self):
        pass


class SegmentGridControl(MouseEventMixin, CharEventMixin, cg.HexGridWindow):
    def __init__(self, parent, segment, caret_handler, view_params, grid_cls=None):
        MouseEventMixin.__init__(self, caret_handler)
        CharEventMixin.__init__(self, caret_handler)
        table = SegmentTable(segment)
        if grid_cls is None:
            # override class attribute in cg.HexGridWindow
            self.grid_cls = UniformNumpyWindow
        else:
            self.grid_cls = grid_cls
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

    @property
    def page_size(self):
        return self.main.sh * self.table.items_per_row

    ##### Caret handling

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
        self.caret_handler.caret_index += delta

    def move_carets_to(self, index):
        self.caret_handler.caret_index = index

    def move_carets_process_function(self, func):
        self.caret_handler.caret_index = func(self.caret_handler.caret_index)

    def validate_caret_position(self):
        index = self.table.enforce_valid_index(self.caret_handler.caret_index)
        self.caret_handler.caret_index = index
        self.main.cy, self.main.cx = self.table.index_to_row_col(index)

    def keep_index_on_screen(self, index):
        row, col = self.table.index_to_row_col(index)
        self.main.ensure_visible(row, col)

    # FIXME: temporary hack until compactgrid uses indexes directly
    def caret_indexes_to_display_coords(self):
        row, col = self.table.index_to_row_col(self.caret_handler.caret_index)
        self.main.show_caret(col, row)

    #####

    def get_row_col_from_event(self, evt):
        row, cell = self.main.pixel_pos_to_row_cell(evt.GetX(), evt.GetY())
        return row, cell

    def get_location_from_event(self, evt):
        row, col = self.main.pixel_pos_to_row_cell(evt.GetX(), evt.GetY())
        return self.get_location_from_cell(row, col)

    def get_location_from_cell(self, row, col):
        r2, c2, index = self.table.enforce_valid_caret(row, col)
        inside = col == c2 and row == r2
        return r2, c2, index, index + 1, inside

    def get_start_end_index_of_row(self, row):
        index1, _ = self.table.get_index_range(row, 0)
        _, index2 = self.table.get_index_range(row, self.table.items_per_row - 1)
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

    def get_status_message_at_cell(self, row, col):
        r, c, index = self.table.enforce_valid_caret(row, col)
        return self.get_status_at_index(index)

    def recalc_view(self):
        raise NotImplementedError("override this in subclass!")
