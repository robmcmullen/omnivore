import wx

import numpy as np

from sawx.ui import compactgrid as cg
from sawx.keybindings import KeyBindingControlMixin
from sawx.ui.mouse_mode import MouseMode
from sawx.utils.command import DisplayFlags
from sawx.utils.sortutil import ranges_to_indexes, collapse_overlapping_ranges
from .selection import CurrentSelection
from ..arch.disasm import get_style_name
# from sawx.framework import actions as fa
# from ..byte_edit import actions as ba
# from ..viewers import actions as va
from ..commands import SetSelectionCommand
from .. import clipboard_helpers

import logging
log = logging.getLogger(__name__)


class SegmentTable(cg.HexTable):
    def __init__(self, linked_base, items_per_row, row_labels_in_multiples=True):
        self.linked_base = linked_base
        cg.HexTable.__init__(self, None, None, items_per_row, self.segment.origin, row_labels_in_multiples)

    @property
    def segment(self):
        return self.linked_base.segment

    @property
    def document(self):
        return self.linked_base.document

    @property
    def data(self):
        return self.linked_base.segment.data

    @property
    def style(self):
        return self.linked_base.segment.style

    def get_label_at_index(self, index):
        # Can't just return hex value of index because some segments (like the
        # raw sector segment) use different labels
        return self.segment.label(index, True)


class SegmentVirtualTable(cg.HexTable):
    col_labels = []
    col_sizes = []

    def __init__(self, linked_base, bytes_per_row_ignored=16):
        self.linked_base = linked_base
        data, style = self.get_data_style_view(linked_base)
        num_cols = self.calc_num_cols()
        cg.HexTable.__init__(self, data, style, num_cols)
        if style is None:
            self.style = np.zeros(self.last_valid_index, dtype=np.uint8)

    @property
    def segment(self):
        return self.linked_base.segment

    def get_data_style_view(self, linked_base):
        """Subclasses implement this to return arrays to be used for data and
        style.

        If style is returned as None, a style array will be created based on
        the largest index of the data.
        """
        raise NotImplementedError

    def calc_num_cols(self):
        return len(self.col_labels)

    def get_value_style(self, row, col):
        raise NotImplementedError

    def get_label_at_index(self, index):
        raise NotImplementedError


class SegmentGridControl(KeyBindingControlMixin, cg.CompactGrid):
    default_table_cls = SegmentTable

    keybinding_desc = {
        "caret_move_up": "Up",
        "caret_move_down": "Down",
        "caret_move_left": "Left",
        "caret_move_right": "Right",
        "caret_move_page_down": "Pagedown",
        "caret_move_page_up": "Pageup",
        "caret_move_start_of_line": "Home",
        "caret_move_end_of_line": "End",
        "caret_move_next_line": "Tab",
        "advance_caret_position": "Space",
    }

    def __init__(self, parent, linked_base, mdict, viewer_cls):
        self.original_metadata = mdict.copy()

        if viewer_cls.override_table_cls is not None:
            # instance attribute will override class attribute
            self.default_table_cls = viewer_cls.override_table_cls

        self.view_params = linked_base.editor.preferences
        self.set_view_param_defaults()
        table = self.calc_default_table(linked_base)

        cg.CompactGrid.__init__(self, table, linked_base.editor.preferences, None, viewer_cls.default_mouse_mode_cls, parent)
        KeyBindingControlMixin.__init__(self)
        # self.automatic_refresh = False

    def map_char_events(self):
        # force keys to be bound on main grid, not parent (which is a panel)
        KeyBindingControlMixin.map_char_events(self, self.main)

    # def map_mouse_events(self):
    #     MouseEventMixin.map_mouse_events(self, self.main)
    #     self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

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

    def calc_default_table(self, linked_base):
        return self.default_table_cls(linked_base, self.items_per_row)

    def calc_caret_handler(self):
        return CurrentSelection(self)

    def recalc_view(self):
        # just recreate everything. If a subclass wants something different,
        # let it do it itself.
        try:
            self.view_params = self.segment_viewer.linked_base.editor.preferences
        except AttributeError:
            log.warning("segment_viewer not set in recalc_view (probably not a real problem; likely a trait event before setup has been completed)")
        else:
            self.table = self.calc_default_table(self.segment_viewer.linked_base)
            self.recalc_line_renderer()

    def recalc_line_renderer(self):
        self.line_renderer = self.calc_line_renderer()
        log.debug("recalculating %s; items_per_row=%s" % (self, self.items_per_row))
        cg.CompactGrid.recalc_view(self)

    def verify_line_renderer(self):
        # hook for subclass to recreate the line renderer if it needs data from
        # the Machine (which isn't created until after the control and segment
        # viewer instances are created)
        pass

    @property
    def page_size(self):
        return (self.main.fully_visible_rows - 1) * self.table.items_per_row

    ##### Caret handling

    def stop_scroll_timer(self):
        self.main.scroll_timer.Stop()

    # FIXME: temporary hack until compactgrid uses indexes directly
    def caret_indexes_to_display_coords(self):
        row, col = self.table.index_to_row_col(self.caret_handler.caret_index)
        self.main.show_caret(col, row)

    #### event handling

    def create_char_event_flags(self):
        flags = DisplayFlags(self)
        flags.old_carets = set(self.caret_handler.calc_state())
        return flags

    def do_char_action(self, evt, action):
        flags = self.create_char_event_flags()
        flags.source_control = self
        action(evt, flags)
        self.keep_current_caret_on_screen(flags)
        self.commit_change(flags)

    def do_char_ordinary(self, evt):
        c = evt.GetKeyCode()
        print(f"do_char_ordinary: {c} for {self}")
        if not self.is_editing_in_cell:
            if self.verify_keycode_can_start_edit(c):
                print(f"do_char_ordinary: {c} starts editing!")
                self.start_editing(evt)
            else:
                print(f"do_char_ordinary: {c} not valid to start editing in cell")
                evt.Skip()
        else:
            print(f"do_char_ordinary: editing in cell")
            self.edit_source.EmulateKeyPress(evt)

    def commit_change(self, flags):
        flags.advance_caret_position_in_control = self
        flags.sync_caret_from_control = self

        log.debug(f"\n\ncommit before: {self.caret_handler.carets} flags={flags}")
        linked_base = self.segment_viewer.linked_base
        self.segment_viewer.update_current_selection(self.caret_handler)
        self.mouse_mode.refresh_ranges(self.caret_handler)
        if flags.viewport_origin is not None:
            self.move_viewport_origin(flags.viewport_origin)
        linked_base.sync_caret_event(flags=flags)
        linked_base.ensure_visible_event(flags=flags)
        linked_base.refresh_event(flags=flags)
        log.debug(f"commit after: {self.caret_handler.carets} flags={flags}\n\n")

    def process_flags(self, flags):
        self.caret_handler.process_char_flags(flags)

    def post_process_caret_flags(self, flags):
        """Perform any caret updates after the data model has been regenerated
        (e.g. the disassembler where the number of bytes per row can change
        after an edit)

        """
        log.debug(f"post_process_caret_flags: advancing to next position {str(flags)}")
        ch = self.caret_handler
        selection_before = ch.has_selection
        self.advance_caret_position(None, flags)
        ch.validate_carets()
        if selection_before:
            ch.collapse_selections_to_carets()
            ch.refresh_style_from_selection(self.table)
        flags.sync_caret_from_control = self


    ##### Rectangular regions

    def get_rects_from_selections(self):
        rects = []
        for caret in self.caret_handler.carets_with_selection:
            if caret.rectangular:
                rects.append(caret.range)
        return rects

    def get_data_from_rect(self, r):
        (r1, c1), (r2, c2) = r
        last = r2 * self.table.items_per_row
        d = self.segment_viewer.segment[:last].reshape(-1, self.table.items_per_row)
        data = d[r1:r2, c1:c2]
        return r2 - r1, c2 - c1, data

    ##### Copy/paste

    def calc_clipboard_data_objs(self, focused_control):
        segment = self.table.segment
        ranges = self.get_selected_ranges()
        indexes = ranges_to_indexes(ranges)
        log.debug(f"calc_clipboard_data_objs: {self}, ranges={ranges} indexes={indexes}")
        data_objs = []
        if len(ranges) > 0:
            blob = clipboard_helpers.create_numpy_clipboard_blob(ranges, indexes, segment, self)
            data_objs.append(blob.data_obj)
            data_objs.append(blob.text_data_obj(self.view_params.text_copy_stringifier))
            # elif np.alen(indexes) > 0:
            #     data = segment[indexes]
            #     s1 = data.tobytes()
            #     s2 = indexes.tobytes()
            #     serialized = b"%d,%d,%s%s%s" % (len(s1), len(s2), s1, s2, metadata)
            #     name = "numpy,multiple"

        return data_objs


        # rects = self.get_rects_from_selections()
        # data = []
        # for (r1, c1), (r2, c2) in rects:
        #     start, _ = self.table.get_index_range(r1, c1)
        #     _, end = self.table.get_index_range(r2, c2)
        #     data.append((start, end, self.table.data[start:end]))
        # if len(data) > 1:
        #     data_obj = wx.CustomDataObject("numpy,multiple")
        #     # multiple





    def get_start_end_index_of_row(self, row):
        return self.table.get_start_end_index_of_row(row)

    def get_status_at_index(self, index):
        if self.table.is_index_valid(index):
            label = self.table.get_label_at_index(index)
            message = self.get_status_message_at_index(index)
            return "%s: %s %s" % (self.segment_viewer.name, label, message)
        return ""

    def get_status_message_at_index(self, index):
        if self.table.is_index_valid(index):
            s = self.segment_viewer.linked_base.segment
            msg = get_style_name(s, index)
            comments = s.get_comment_at(index)
            return "%s  %s" % (msg, comments)
        return ""

    def get_status_message_at_cell(self, row, col):
        try:
            r, c, index, index2 = self.main.enforce_valid_caret(row, col)
            return self.get_status_at_index(index)
        except IndexError:
            pass
        return ""

    def show_popup(self, popup_desc, data):
        self.segment_viewer.editor.show_popup(popup_desc, data)

    def add_popup_data(self, evt, popup_data):
        popup_data["popup_viewer"] = self.segment_viewer

    def calc_popup_menu(self, evt):
        return self.segment_viewer.popup_menu_desc

    ##### editing

    def verify_keycode_can_start_edit(self, c):
        return False

    def mouse_event_in_edit_cell(self, evt):
        r, c, _ = self.get_row_col_from_event(evt)
        index, _ = self.table.get_index_range(r, c)
        print(f"mouse_event_in_edit_cell: {r},{c}, index={index}")
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
            print(f"start_editing: EmulateKeyPress: {evt.GetKeyCode()} for {self.edit_source}")
            self.edit_source.EmulateKeyPress(evt)

    def use_first_char_when_starting_edit(self):
        return True

    def accept_edit(self, autoadvance=False):
        val = self.edit_source.get_processed_value()
        self.end_editing()
        print(f"accept_edit: changing to {val}")
        self.process_edit(val)

    def process_edit(self, val):
        cmd = self.calc_edit_command(val)
        flags = self.segment_viewer.editor.process_command(cmd)

    def calc_edit_command(self, val):
        cmd = SetSelectionCommand(self.segment_viewer.segment, self.caret_handler, val, advance=True)
        return cmd

    def end_editing(self):
        if self.is_editing_in_cell:
            self.edit_source.Destroy()
            self.edit_source = None
            self.is_editing_in_cell = False
            self.SetFocus()

    def create_hidden_text_ctrl(self):
        c = cg.GridCellTextCtrl(self, -1, 0, pos=(600,100), size=(400,24))
        return c


class SegmentVirtualGridControl(SegmentGridControl):
    default_table_cls = SegmentVirtualTable

    def calc_default_table(self, linked_base):
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
