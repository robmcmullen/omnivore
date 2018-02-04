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
        cg.HexTable.__init__(self, self.segment.data, self.segment.style, 16, self.segment.start_addr, start_offset_mask=0x0f)

    def get_label_at_index(self, index):
        # Can't just return hex value of index because some segments (like the
        # raw sector segment) use different labels
        return self.segment.label(index, True)


class SegmentGridControl(MouseEventMixin, CharEventMixin, cg.HexGridWindow):
    def __init__(self, parent, segment, caret_handler, view_params, grid_cls=None, line_renderer_cls=None):
        MouseEventMixin.__init__(self, caret_handler)
        CharEventMixin.__init__(self, caret_handler)
        table = SegmentTable(segment)

        # override class attributes in cg.HexGridWindow if present
        if grid_cls is not None:
            self.grid_cls = grid_cls
        if line_renderer_cls is not None:
            self.line_renderer_cls = line_renderer_cls

        cg.HexGridWindow.__init__(self, table, view_params, caret_handler, parent)

    @property
    def table(self):
        return self.main.table

    @property
    def page_size(self):
        return self.main.sh * self.table.items_per_row

    ##### Caret handling

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
        r2, c2, index = self.main.enforce_valid_caret(row, col)
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
            return "%s: %s %s" % (self.segment_viewer.name, label, message)
        return ""

    def get_status_message_at_index(self, index):
        msg = get_style_name(self.table.segment, index)
        comments = self.table.segment.get_comment(index)
        return "%s  %s" % (msg, comments)

    def get_status_message_at_cell(self, row, col):
        r, c, index = self.main.enforce_valid_caret(row, col)
        return self.get_status_at_index(index)

    def recalc_view(self):
        table = SegmentTable(self.segment_viewer.linked_base.segment)
        log.debug("recalculating %s" % self)
        cg.HexGridWindow.recalc_view(self, table, self.segment_viewer.linked_base.cached_preferences)
