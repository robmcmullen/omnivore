import wx

from .mouse_event_mixin import MouseEventMixin
from omnivore.utils.command import DisplayFlags
from omnivore.utils.wx import compactgrid as cg
from omnivore.utils.wx.char_event_mixin import CharEventMixin
from omnivore8bit.arch.disasm import get_style_name
from omnivore.framework import actions as fa
from ..byte_edit import actions as ba

import logging
log = logging.getLogger(__name__)


class SegmentTable(cg.HexTable):
    def __init__(self, segment, bytes_per_row):
        self.segment = segment
        cg.HexTable.__init__(self, self.segment.data, self.segment.style, bytes_per_row, self.segment.start_addr, start_offset_mask=0x0f)

    def get_label_at_index(self, index):
        # Can't just return hex value of index because some segments (like the
        # raw sector segment) use different labels
        return self.segment.label(index, True)


class SegmentGridControl(MouseEventMixin, CharEventMixin, cg.HexGridWindow):
    def __init__(self, parent, segment, caret_handler, view_params, grid_cls=None, line_renderer_cls=None, table=None):
        MouseEventMixin.__init__(self, caret_handler)
        CharEventMixin.__init__(self, caret_handler)

        self.view_params = view_params
        self.items_per_row = None
        self.set_viewer_defaults()

        if table is None:
            table = self.calc_default_table(segment, view_params)

        # override class attributes in cg.HexGridWindow if present
        if grid_cls is not None:
            self.grid_cls = grid_cls
        if line_renderer_cls is not None:
            self.line_renderer_cls = line_renderer_cls

        cg.HexGridWindow.__init__(self, table, view_params, caret_handler, parent)
        self.automatic_refresh = False

    def set_viewer_defaults(self):
        pass

    def calc_default_table(self, segment, view_params):
        return SegmentTable(segment, view_params.hex_grid_width)

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
        row, col = self.main.pixel_pos_to_row_col(evt.GetX(), evt.GetY())
        return row, col

    def get_location_from_event(self, evt):
        row, col = self.main.pixel_pos_to_row_col(evt.GetX(), evt.GetY())
        return self.get_location_from_col(row, col)

    def get_location_from_col(self, row, col):
        r2, c2, index = self.main.enforce_valid_caret(row, col)
        inside = col == c2 and row == r2
        return r2, c2, index, index + 1, inside

    def get_start_end_index_of_row(self, row):
        return self.table.get_start_end_index_of_row(row)

    def get_status_at_index(self, index):
        if self.table.is_index_valid(index):
            label = self.table.get_label_at_index(index)
            message = self.get_status_message_at_index(index)
            return "%s: %s %s" % (self.segment_viewer.name, label, message)
        return ""

    def get_status_message_at_index(self, index):
        s = self.segment_viewer.linked_base.segment
        msg = get_style_name(s, index)
        comments = s.get_comment(index)
        return "%s  %s" % (msg, comments)

    def get_status_message_at_cell(self, row, col):
        r, c, index = self.main.enforce_valid_caret(row, col)
        return self.get_status_at_index(index)

    def recalc_view(self):
        table = SegmentTable(self.segment_viewer.linked_base.segment, self.items_per_row)
        log.debug("recalculating %s" % self)
        cg.HexGridWindow.recalc_view(self, table, self.segment_viewer.linked_base.cached_preferences)

    def on_popup(self, evt):
        row, col = self.get_row_col_from_event(evt)
        index, _ = self.table.get_index_range(row, col)
        inside = True  # fixme
        style = self.table.segment.style[index] if inside else 0
        popup_data = {
            'index': index,
            'in_selection': style&0x80,
            'row': row,
            'col': col,
            'inside': inside,
            }
        actions = self.get_popup_actions(popup_data)
        if actions:
            self.segment_viewer.popup_context_menu_from_actions(actions, popup_data)

    def get_popup_actions(self, popup_data):
        actions = self.common_popup_actions(popup_data)
        actions.extend(self.extra_popup_actions(popup_data))
        return actions

    def common_popup_actions(self, popup_data):
        copy_special = [ba.CopyAsReprAction, ba.CopyAsCBytesAction]
        for v in self.segment_viewer.editor.task.known_viewers:
            copy_special.extend(v.copy_special)
        copy_special.sort(key=lambda a:a().name)  # name is a trait, so only exists on an instance, not the class
        copy_special[0:0] = ["Copy Special"]  # sub-menu title

        return [fa.CutAction, fa.CopyAction, copy_special, fa.PasteAction, ["Paste Special", ba.PasteAndRepeatAction, ba.PasteCommentsAction], None, fa.SelectAllAction, fa.SelectNoneAction, ["Mark Selection As", ba.MarkSelectionAsCodeAction, ba.MarkSelectionAsDataAction, ba.MarkSelectionAsUninitializedDataAction, ba.MarkSelectionAsDisplayListAction, ba.MarkSelectionAsJumpmanLevelAction, ba.MarkSelectionAsJumpmanHarvestAction], None, ba.GetSegmentFromSelectionAction, ba.RevertToBaselineAction, None, ba.AddCommentPopupAction, ba.RemoveCommentPopupAction, ba.AddLabelPopupAction, ba.RemoveLabelPopupAction]

    def extra_popup_actions(self, popup_data):
        # for subclasses!
        return []
