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
from ..commands import SetRangeValueCommand

import logging
log = logging.getLogger(__name__)


class SegmentTable(cg.HexTable):
    def __init__(self, linked_base, bytes_per_row):
        self.linked_base = linked_base
        cg.HexTable.__init__(self, self.segment.data, self.segment.style, bytes_per_row, self.segment.start_addr, start_offset_mask=0x0f)

    @property
    def segment(self):
        return self.linked_base.segment

    def get_label_at_index(self, index):
        # Can't just return hex value of index because some segments (like the
        # raw sector segment) use different labels
        return self.segment.label(index, True)


class SegmentVirtualTable(cg.HexTable):
    col_labels = []
    col_sizes = []

    def __init__(self, linked_base, bytes_per_row_ignored):
        self.linked_base = linked_base
        data, style = self.get_data_style_view(linked_base)
        num_cols = self.calc_num_cols()
        cg.HexTable.__init__(self, data, style, num_cols)

    def get_data_style_view(self, linked_base):
        raise NotImplementedError

    def calc_num_cols(self):
        return len(self.cols)

    def get_value_style(self, row, col):
        raise NotImplementedError

    def get_label_at_index(self, index):
        raise NotImplementedError


class SegmentGridTextCtrl(wx.TextCtrl):
    def __init__(self, parent, id, num_chars_autoadvance, *args, **kwargs):
        # Don't use the validator here, because apparently we can't
        # reset the validator based on the columns.  We have to do the
        # validation ourselves using EVT_KEY_DOWN.
        wx.TextCtrl.__init__(self, parent, id, *args, style=wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER, **kwargs)
        log.debug("parent=%s" % parent)
        self.SetInsertionPoint(0)
        self.Bind(wx.EVT_TEXT, self.on_text)
        self.Bind(wx.EVT_CHAR, self.on_char)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.SetMaxLength(num_chars_autoadvance)
        self.num_chars_autoadvance = num_chars_autoadvance

    def is_valid_keycode(self, keycode):
        return True

    def on_key_down(self, evt):
        """
        Keyboard handler to process command keys before they are
        inserted.  Tabs, arrows, ESC, return, etc. should be handled
        here.  If the key is to be processed normally, evt.Skip must
        be called.  Otherwise, the event is eaten here.

        @param evt: key event to process
        """
        log.debug("key down before evt=%s" % evt.GetKeyCode())
        key = evt.GetKeyCode()

        if key == wx.WXK_TAB:
            wx.CallAfter(self.GetParent().advance_caret)
        elif key == wx.WXK_ESCAPE:
            wx.CallAfter(self.GetParent().end_editing)
            print("OSEUCHORECUHCROEUHSCOEHUESCAPE")
        elif key == wx.WXK_RETURN:
            wx.CallAfter(self.GetParent().accept_edit, self.num_chars_autoadvance)
        else:
            evt.Skip()

    def on_char(self, evt):
        code = evt.GetKeyCode()
        char = evt.GetUnicodeKey()
        log.debug("char keycode=%s unicode=%s" % (code, char))
        if char == wx.WXK_NONE or code == wx.WXK_BACK or self.is_valid_keycode(code):
            evt.Skip()
            wx.CallAfter(self.GetParent().Refresh)

    def get_processed_value(self):
        return self.GetValue()

    def on_text(self, evt):
        """
        Callback used to automatically advance to the next edit field. If
        self.num_chars_autoadvance > 0, this number is used as the max number
        of characters in the field.  Once the text string hits this number, the
        field is processed and advanced to the next position.
        """
        log.debug("evt=%s str=%s cursor=%d" % (evt, evt.GetString(), self.GetInsertionPoint()))

        # NOTE: we check that GetInsertionPoint returns 1 less than
        # the desired number because the insertion point hasn't been
        # updated yet and won't be until after this event handler
        # returns.
        n = self.num_chars_autoadvance
        if n and len(evt.GetString()) >= n and self.GetInsertionPoint() >= n - 1:
            # FIXME: problem here with a bunch of really quick
            # keystrokes -- the interaction with the
            # underlyingSTCChanged callback causes a cell's
            # changes to be skipped over.  Need some flag in grid
            # to see if we're editing, or to delay updates until a
            # certain period of calmness, or something.
            log.debug("advancing after edit")
            wx.CallAfter(self.GetParent().accept_edit, n)


class SegmentGridControl(MouseEventMixin, CharEventMixin, cg.CompactGrid):
    default_table_cls = SegmentTable

    def __init__(self, parent, linked_base, mdict, viewer_cls):
        MouseEventMixin.__init__(self, linked_base, viewer_cls.default_mouse_mode_cls)
        CharEventMixin.__init__(self, linked_base)

        self.original_metadata = mdict.copy()

        if viewer_cls.override_table_cls is not None:
            # instance attribute will override class attribute
            self.default_table_cls = viewer_cls.override_table_cls
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
        return self.default_table_cls(self.caret_handler, self.items_per_row)

    def recalc_view(self):
        # just recreate everything. If a subclass wants something different,
        # let it do it itself.
        self.view_params = self.segment_viewer.linked_base.cached_preferences
        self.table = self.calc_default_table()
        self.line_renderer = self.calc_line_renderer()
        log.debug("recalculating %s; items_per_row=%d" % (self, self.items_per_row))
        self.recalc_view_extra_setup()
        cg.CompactGrid.recalc_view(self)

    def recalc_view_extra_setup(self):
        """Hook for subclasses to set up any data needed before actually
        displaying the screen
        """
        pass

    @property
    def page_size(self):
        return (self.main.fully_visible_rows - 1) * self.table.items_per_row

    ##### Caret handling

    def stop_scroll_timer(self):
        self.main.scroll_timer.Stop()

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

    ##### editing

    def handle_char_ordinary(self, evt):
        c = evt.GetKeyCode()
        print(("ordinary char: %s", c))
        if not self.is_editing_in_cell:
            if self.verify_keycode_can_start_edit(c):
                self.start_editing(evt)
        else:
            self.edit_source.EmulateKeyPress(evt)

    def verify_keycode_can_start_edit(self, c):
        return True

    def mouse_event_in_edit_cell(self, evt):
        r, c = self.get_row_col_from_event(evt)
        index, _ = self.table.get_index_range(r, c)
        print(("mouse edit cell check: r,c=%d,%d, index=%d" % (r, c, index)))
        return self.caret_handler.is_index_of_caret(index)

    def on_left_down_in_edit_cell(self, evt):
        pass

    def on_motion_in_edit_cell(self, evt):
        pass

    def on_left_up_in_edit_cell(self, evt):
        pass

    def start_editing(self, evt):
        self.is_editing_in_cell = True
        self.edit_source = self.create_hidden_text_ctrl()
        self.edit_source.SetFocus()
        if self.use_first_char_when_starting_edit():
            print(("EmulateKeyPress: %s" % evt.GetKeyCode()))
            self.edit_source.EmulateKeyPress(evt)

    def use_first_char_when_starting_edit(self):
        return True

    def accept_edit(self, autoadvance=False):
        val = self.edit_source.get_processed_value()
        self.end_editing()
        print(("changing to %s" % val))
        self.process_edit(val)

    def process_edit(self, val):
        ranges = []
        # for c in self.caret_handler.carets:
        #     ranges.append((c.index, c.index + 1))
        ranges = self.get_selected_ranges_including_carets(self.caret_handler)
        cmd = SetRangeValueCommand(self.segment_viewer.segment, ranges, val, advance=True)
        self.segment_viewer.editor.process_command(cmd)

    def end_editing(self):
        if self.is_editing_in_cell:
            self.edit_source.Destroy()
            self.edit_source = None
            self.is_editing_in_cell = False
            self.SetFocus()

    def create_hidden_text_ctrl(self):
        c = SegmentGridTextCtrl(self, -1, 0, pos=(600,100), size=(400,24))
        return c


class SegmentVirtualGridControl(SegmentGridControl):
    default_table_cls = SegmentVirtualTable

    def calc_default_table(self):
        linked_base = self.caret_handler
        table = self.default_table_cls(linked_base)
        self.items_per_row = table.items_per_row
        self.want_row_header = table.want_row_header
        self.want_col_header = table.want_col_header
        return table

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 1, widths=self.table.col_sizes, col_labels=self.table.col_labels)

    ##### editing

    def set_viewer_defaults(self):
        self.items_per_row = -1
