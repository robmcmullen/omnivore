import wx

from .mouse_event_mixin import MouseEventMixin
from omnivore.utils.command import DisplayFlags
from omnivore.utils.wx import compactgrid as cg
from omnivore.utils.wx.char_event_mixin import CharEventMixin
from omnivore.framework.mouse_mode import MouseMode
from omnivore8bit.arch.disasm import get_style_name
from omnivore.framework import actions as fa
from ..byte_edit import actions as ba
from ..viewers import actions as va

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


class SegmentGridControl(MouseEventMixin, CharEventMixin, cg.CompactGrid):
    def __init__(self, parent, linked_base, mdict, viewer_cls):
        MouseEventMixin.__init__(self, linked_base, viewer_cls.default_mouse_mode_cls)
        CharEventMixin.__init__(self, linked_base)

        self.original_metadata = mdict.copy()

        cg.CompactGrid.__init__(self, None, linked_base.cached_preferences, linked_base, parent)
        self.automatic_refresh = False

    def map_char_events(self):
        CharEventMixin.map_char_events(self, self.main)

    def map_mouse_events(self):
        MouseEventMixin.map_mouse_events(self, self.main)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

    def set_view_param_defaults(self):
        # called from base class to set up initial viewer
        cg.CompactGrid.set_view_param_defaults(self)
        self.set_viewer_defaults()
        self.restore_extra_from_dict(self.original_metadata)

    def set_viewer_defaults(self):
        self.items_per_row = 99  # unlikely to be used normally, so something is likely wrong if a viewer ever appears with 99 colums
        self.zoom = 1

    def serialize_extra_to_dict(self, mdict):
        """Save extra metadata to a dict so that it can be serialized
        """
        mdict['items_per_row'] = self.items_per_row
        mdict['zoom'] = self.zoom

    def restore_extra_from_dict(self, e):
        log.debug("metadata: %s" % str(e))
        if 'items_per_row' in e:
            self.items_per_row = e['items_per_row']
        if 'zoom' in e:
            self.zoom = e['zoom']

    def calc_default_table(self):
        linked_base = self.caret_handler
        return SegmentTable(linked_base.segment, self.items_per_row)

    def recalc_view(self):
        # just recreate everything. If a subclass wants something different,
        # let it do it itself.
        self.view_params = self.segment_viewer.linked_base.cached_preferences
        self.table = SegmentTable(self.segment_viewer.linked_base.segment, self.items_per_row)
        self.line_renderer = self.calc_line_renderer()
        log.debug("recalculating %s; items_per_row=%d" % (self, self.items_per_row))
        cg.CompactGrid.recalc_view(self)

    @property
    def page_size(self):
        return (self.main.fully_visible_rows - 1) * self.table.items_per_row

    ##### Caret handling

    def keep_index_on_screen(self, index):
        row, col = self.table.index_to_row_col(index)
        self.main.ensure_visible(row, col)

    # FIXME: temporary hack until compactgrid uses indexes directly
    def caret_indexes_to_display_coords(self):
        row, col = self.table.index_to_row_col(self.caret_handler.caret_index)
        self.main.show_caret(col, row)

    ##### Rectangular regions

    def get_rects_from_selections(self):
        rects = []
        for caret in self.caret_handler.carets_with_selection:
            _, _, ul, lr = self.segment_viewer.segment.get_rect_indexes(caret.anchor_start_index, caret.anchor_end_index, self.table.items_per_row)
            rects.append((ul, lr))
        return rects

    def get_data_from_rect(self, r):
        (r1, c1), (r2, c2) = r
        last = r2 * self.table.items_per_row
        d = self.segment_viewer.segment[:last].reshape(-1, self.table.items_per_row)
        data = d[r1:r2, c1:c2]
        return r2 - r1, c2 - c1, data

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

    def calc_control_popup_actions(self, popup_data):
        actions = self.calc_common_popup_actions(popup_data)
        last = self.segment_viewer.calc_viewer_popup_actions(popup_data)
        if last:
            actions.append(None)
            actions.extend(last)
        return actions

    def calc_common_popup_actions(self, popup_data):
        copy_special = self.segment_viewer.all_known_copy_special_actions(self.segment_viewer.task)
        copy_special[0:0] = ["Copy Special"]  # sub-menu title
        paste_special = self.segment_viewer.all_known_paste_special_actions(self.segment_viewer.task)
        paste_special[0:0] = ["Paste Special"]  # sub-menu title

        return [fa.CutAction, fa.CopyAction, copy_special, fa.PasteAction, paste_special, None, fa.SelectAllAction, fa.SelectNoneAction, ["Mark Selection As", ba.MarkSelectionAsCodeAction, ba.MarkSelectionAsDataAction, ba.MarkSelectionAsUninitializedDataAction, ba.MarkSelectionAsDisplayListAction, ba.MarkSelectionAsJumpmanLevelAction, ba.MarkSelectionAsJumpmanHarvestAction], None, ba.GetSegmentFromSelectionAction, ba.RevertToBaselineAction, None, va.AddCommentPopupAction, va.RemoveCommentPopupAction, va.AddLabelPopupAction,va.RemoveLabelPopupAction]
