import wx

from .mouse_event_mixin import MouseEventMixin
from omnivore.utils.command import DisplayFlags
from omnivore.utils.wx import compactgrid as cg
from omnivore.utils.wx.char_event_mixin import CharEventMixin
from omnivore.framework.mouse_mode import MouseMode
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


class NormalSelectMode(MouseMode):
    def init_post_hook(self):
        self.last_mouse_event = -1, -1
        self.event_modifiers = None

    def process_mouse_motion_up(self, evt):
        log.debug("NormalSelectMode: process_mouse_motion_up")
        cg = self.control
        input_row, input_cell = cg.main.get_row_cell_from_event(evt)
        if (input_row, input_cell) == self.last_mouse_event:
            # only process if mouse has moved to a new cell; no sub-cell
            # events!
            return
        col = cg.main.cell_to_col(input_cell)
        cg.handle_motion_update_status(evt, input_row, col)
        self.last_mouse_event = (input_row, input_cell)

    def process_left_down(self, evt):
        log.debug("NormalSelectMode: process_left_down")
        cg = self.control
        flags = cg.create_mouse_event_flags()
        row, cell = cg.main.get_row_cell_from_event(evt)
        self.event_modifiers = evt.GetModifiers()
        cg.main.process_motion_scroll(row, cell, flags)
        self.last_mouse_event = (row, cell)
        cg.handle_select_start(evt, cg.main.current_caret_row, cg.main.current_caret_col, flags)

    def process_mouse_motion_down(self, evt):
        log.debug("NormalSelectMode: process_mouse_motion_down")
        cg = self.control
        input_row, input_cell = cg.main.get_row_cell_from_event(evt)
        if (input_row, input_cell) == self.last_mouse_event:
            # only process if mouse has moved to a new cell; no sub-cell
            # events!
            return
        flags = cg.create_mouse_event_flags()
        last_row, last_col = cg.main.current_caret_row, cg.main.current_caret_col
        cg.main.handle_user_caret(input_row, input_cell, flags)
        if last_row != cg.main.current_caret_row or last_col != cg.main.current_caret_col:
            cg.handle_select_motion(evt, cg.main.current_caret_row, cg.main.current_caret_col, flags)
        self.last_mouse_event = (input_row, input_cell)

    def process_left_up(self, evt):
        log.debug("NormalSelectMode: process_left_up")
        cg = self.control
        cg.main.scroll_timer.Stop()
        self.event_modifiers = None
        cg.handle_select_end(evt, cg.main.current_caret_row, cg.main.current_caret_col)

    def process_left_dclick(self, evt):
        log.debug("NormalSelectMode: process_left_dclick")
        evt.Skip()

    def calc_popup_data(self, evt):
        c = self.control
        row, col = c.get_row_col_from_event(evt)
        index, _ = c.table.get_index_range(row, col)
        inside = True  # fixme
        style = c.table.segment.style[index] if inside else 0
        popup_data = {
            'index': index,
            'in_selection': style&0x80,
            'row': row,
            'col': col,
            'inside': inside,
            }
        return popup_data

    def calc_popup_actions(self, evt, popup_data):
        actions = self.calc_mode_popup_actions(popup_data)
        if not actions:
            actions = self.control.calc_popup_actions(popup_data)
        if actions:
            self.segment_viewer.popup_context_menu_from_actions(actions, popup_data)

    def calc_mode_popup_actions(self, popup_data):
        return []

    def show_popup(self, actions):
        self.control.viewer.popup_context_menu_from_actions(actions)

    def zoom_in(self, evt, amount):
        self.control.zoom_in()

    def zoom_out(self, evt, amount):
        self.control.zoom_out()


class SegmentGridControl(MouseEventMixin, CharEventMixin, cg.HexGridWindow):
    def __init__(self, parent, linked_base, mdict={}, table=None):
        MouseEventMixin.__init__(self, linked_base, NormalSelectMode)
        CharEventMixin.__init__(self, linked_base)

        self.original_metadata = mdict.copy()

        cg.HexGridWindow.__init__(self, table, linked_base.cached_preferences, linked_base, parent)
        self.automatic_refresh = False

    def map_char_events(self):
        CharEventMixin.map_char_events(self, self.main)

    def map_mouse_events(self):
        MouseEventMixin.map_mouse_events(self, self.main)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

    def set_view_param_defaults(self):
        # called from base class to set up initial viewer
        cg.HexGridWindow.set_view_param_defaults(self)
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
        cg.HexGridWindow.recalc_view(self)

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
        actions.extend(self.calc_extra_popup_actions(popup_data))
        return actions

    def calc_common_popup_actions(self, popup_data):
        copy_special = [ba.CopyAsReprAction, ba.CopyAsCBytesAction]
        for v in self.segment_viewer.editor.task.known_viewers:
            copy_special.extend(v.copy_special)
        copy_special.sort(key=lambda a:a().name)  # name is a trait, so only exists on an instance, not the class
        copy_special[0:0] = ["Copy Special"]  # sub-menu title

        return [fa.CutAction, fa.CopyAction, copy_special, fa.PasteAction, ["Paste Special", ba.PasteAndRepeatAction, ba.PasteCommentsAction], None, fa.SelectAllAction, fa.SelectNoneAction, ["Mark Selection As", ba.MarkSelectionAsCodeAction, ba.MarkSelectionAsDataAction, ba.MarkSelectionAsUninitializedDataAction, ba.MarkSelectionAsDisplayListAction, ba.MarkSelectionAsJumpmanLevelAction, ba.MarkSelectionAsJumpmanHarvestAction], None, ba.GetSegmentFromSelectionAction, ba.RevertToBaselineAction, None, ba.AddCommentPopupAction, ba.RemoveCommentPopupAction, ba.AddLabelPopupAction, ba.RemoveLabelPopupAction]

    def calc_extra_popup_actions(self, popup_data):
        # for subclasses!
        return []
