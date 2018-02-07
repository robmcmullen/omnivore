import time

import wx

from omnivore.utils.command import DisplayFlags
from omnivore.framework.caret import SelectionHandler

import logging
log = logging.getLogger(__name__)


class MouseEventMixin(SelectionHandler):
    def __init__(self, caret_handler):
        self.caret_handler = caret_handler
        self.multi_select_mode = False
        self.select_extend_mode = False
        self.mouse_drag_started = False
        self.pending_select_awaiting_drag = None

    def create_mouse_event_flags(self):
        flags = DisplayFlags(self)
        flags.selecting_rows = False
        flags.old_carets = self.caret_handler.carets.get_state()
        return flags

    def handle_motion_update_status(self, evt, row, col):
        msg = self.get_status_message_at_cell(row, col)
        if msg:
            self.caret_handler.show_status_message(msg)

    ##### Default selection handlers

    def handle_select_start(self, evt, row, col, flags=None):
        """ select_handler: interface with set_style_ranges to highlight bytes
        that should be selected (e.g. rect select will need different method
        than regular selection).

        caret_handler: object that implements the CaretHandler API
        """
        if flags is None:
            flags = self.create_mouse_event_flags()
        ch = self.caret_handler
        self.mouse_drag_started = True
        r, c, index1, index2, inside = self.get_location_from_event(evt)
        if c < 0 or flags.selecting_rows or not inside:
            c = 0
            selecting_rows = True
        else:
            selecting_rows = False
        log.debug("handle_select_start: rows=%s, input=%d,%d r,c=%d,%d index1,2=%d,%d inside=%s" % (selecting_rows, row, col, r, c, index1, index2, inside))
        if evt.ControlDown():
            self.multi_select_mode = True
            self.select_extend_mode = False
        elif evt.ShiftDown():
            self.multi_select_mode = False
            self.select_extend_mode = True
        if self.select_extend_mode:
            if index1 < ch.anchor_start_index:
                ch.anchor_start_index = index1
                ch.carets.current.index = index1
            elif index2 > ch.anchor_start_index:
                ch.anchor_end_index = index2
                ch.carets.current.index = index2 - 1
            ch.anchor_initial_start_index, ch.anchor_initial_end_index = ch.anchor_start_index, ch.anchor_end_index
            self.select_range(ch, ch.anchor_start_index, ch.anchor_end_index, add=self.multi_select_mode)
        else:
            self.ClearSelection()
            if selecting_rows:
                index1, index2 = self.get_start_end_index_of_row(r)
            ch.anchor_initial_start_index, ch.anchor_initial_end_index = index1, index2
            ch.carets.current.index = index1
            if selecting_rows:
                self.select_range(ch, index1, index2, add=self.multi_select_mode)
            else:
                # initial click when not selecting rows should move the caret,
                # not select the grid square
                self.pending_select_awaiting_drag = (index1, index2)
                if not self.multi_select_mode:
                    self.select_none(ch)
                    # status line doesn't get automatically updated to show
                    # nothing is selected, so force the update
                    flags.message = self.get_status_at_index(index1)
        flags.caret_index = ch.carets.current.index
        flags.caret_column = c
        log.debug("handle_select_start: flags: %s, anchors=%s" % (flags, str((ch.anchor_initial_start_index, ch.anchor_initial_end_index))))
        self.commit_change(flags)

    def handle_select_motion(self, evt, row, col, flags=None):
        if not self.mouse_drag_started:
            # On windows, it's possible to get a motion event before a mouse
            # down event, so need this flag to check
            return
        if flags is None:
            flags = self.create_mouse_event_flags()
        ch = self.caret_handler
        update = False
        r, c, index1, index2, inside = self.get_location_from_col(row, col)
        log.debug("handle_select_motion: r=%d c=%d index1: %s, index2: %s pending: %s, sel rows: %s anchors: initial=%s current=%s" % (r, c, index1, index2, str(self.pending_select_awaiting_drag), flags.selecting_rows, str((ch.anchor_initial_start_index, ch.anchor_initial_end_index)), str((ch.anchor_start_index, ch.anchor_end_index))))
        if c < 0 or flags.selecting_rows or not inside:
            selecting_rows = True
            c = 0
        else:
            selecting_rows = False
            if self.pending_select_awaiting_drag is not None:
                # only start selection if the cursor is over a different cell
                # than the mouse down event
                if index1 == self.pending_select_awaiting_drag[0]:
                    return

                # We have an actual drag so we can begin the selection
                ch.anchor_initial_start_index, ch.anchor_initial_end_index = self.pending_select_awaiting_drag
                self.pending_select_awaiting_drag = None
                self.select_range(ch, ch.anchor_initial_start_index, ch.anchor_initial_end_index, add=self.multi_select_mode)
                update = True
        if self.select_extend_mode:
            if index1 < ch.anchor_initial_start_index:
                self.select_range(ch, index1, ch.anchor_initial_end_index, extend=True)
                update = True
            else:
                self.select_range(ch, ch.anchor_initial_start_index, index2, extend=True)
                update = True
        else:
            if index2 >= ch.anchor_initial_end_index:
                ch.carets.current.index = index1
                if selecting_rows:
                    index1, index2 = self.get_start_end_index_of_row(r)
                if index2 != ch.anchor_end_index:
                    self.select_range(ch, ch.anchor_initial_start_index, index2, extend=self.multi_select_mode)
                    update = True
            elif index1 <= ch.anchor_initial_start_index:
                if selecting_rows:
                    index1, index2 = self.get_start_end_index_of_row(r)
                if index1 != ch.anchor_start_index:
                    self.select_range(ch, index1, ch.anchor_initial_end_index, extend=self.multi_select_mode)
                    update = True
        if update:
            ch.carets.current.index = index1
            flags.keep_selection = True
            self.commit_change(flags)
        log.debug("handle_select_motion: update: %s, flags: %s, anchors: initial=%s current=%s" % (update, flags, str((ch.anchor_initial_start_index, ch.anchor_initial_end_index)), str((ch.anchor_start_index, ch.anchor_end_index))))

    def handle_select_end(self, evt, row, col, flags=None):
        self.mouse_drag_started = False
        self.select_extend_mode = False
        self.multi_select_mode = False

    def commit_change(self, flags):
        self.caret_handler.process_flags(flags)

    def ClearSelection(self):
        # Stub function for those controls that don't have it. Tables use this
        # but nothing else so far.
        pass

    def get_location_from_event(self, evt):
        raise NotImplementedError

    def get_start_end_index_of_row(self, row):
        raise NotImplementedError

    def get_status_message_at_cell(self, row, col):
        raise NotImplementedError

    def highlight_selected_ranges(self, caret_handler):
        ch = self.caret_handler
        ch.document.change_count += 1
        s = ch.segment
        s.clear_style_bits(selected=True)
        self.highlight_selected_ranges_in_segment(ch.selected_ranges, s)
        ch.calc_dependent_action_enabled_flags()

    def highlight_selected_ranges_in_segment(self, selected_ranges, segment):
        # This is default implementation which simply highlights everything
        # between the start/end values of each range. Other selection types
        # (rectangular selection) will need to be defined in the subclass
        segment.set_style_ranges(selected_ranges, selected=True)


