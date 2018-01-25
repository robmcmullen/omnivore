import wx

from omnivore.utils.command import DisplayFlags
from omnivore.framework.caret import SelectionHandler

import logging
log = logging.getLogger(__name__)


class SelectionMixin(SelectionHandler):
    def __init__(self):
        self.multi_select_mode = False
        self.select_extend_mode = False
        self.mouse_drag_started = False
        self.pending_select_awaiting_drag = None

    def handle_select_start(self, caret_handler, evt, selecting_rows=False, col=0):
        """ select_handler: interface with set_style_ranges to highlight bytes
        that should be selected (e.g. rect select will need different method
        than regular selection).

        caret_handler: object that implements the CaretHandler API
        """
        log.debug("handle_select_start: selecting_rows: %s, col=%s" % (selecting_rows, col))
        flags = DisplayFlags(self)
        flags.dont_move_caret = self
        caret_handler.pending_focus = self
        self.mouse_drag_started = True
        r, c, index1, index2, inside = self.get_location_from_event(evt)
        if c < 0 or selecting_rows or not inside:
            c = 0
            selecting_rows = True
        else:
            selecting_rows = False
        if evt.ControlDown():
            self.multi_select_mode = True
            self.select_extend_mode = False
        elif evt.ShiftDown():
            self.multi_select_mode = False
            self.select_extend_mode = True
        if self.select_extend_mode:
            if index1 < caret_handler.anchor_start_index:
                caret_handler.anchor_start_index = index1
                caret_handler.caret_index = index1
            elif index2 > caret_handler.anchor_start_index:
                caret_handler.anchor_end_index = index2
                caret_handler.caret_index = index2 - 1
            caret_handler.anchor_initial_start_index, caret_handler.anchor_initial_end_index = caret_handler.anchor_start_index, caret_handler.anchor_end_index
            self.select_range(caret_handler, caret_handler.anchor_start_index, caret_handler.anchor_end_index, add=self.multi_select_mode)
        else:
            self.ClearSelection()
            if selecting_rows:
                index1, index2 = self.get_start_end_index_of_row(r)
            caret_handler.anchor_initial_start_index, caret_handler.anchor_initial_end_index = index1, index2
            caret_handler.caret_index = index1
            if selecting_rows:
                self.select_range(caret_handler, index1, index2, add=self.multi_select_mode)
            else:
                # initial click when not selecting rows should move the caret,
                # not select the grid square
                self.pending_select_awaiting_drag = (index1, index2)
                if not self.multi_select_mode:
                    self.select_none(caret_handler)
                    # status line doesn't get automatically updated to show
                    # nothing is selected, so force the update
                    flags.message = self.get_status_at_index(index1)
        flags.caret_index = caret_handler.caret_index
        flags.caret_column = c
        log.debug("handle_select_start: flags: %s, anchors=%s" % (flags, str((caret_handler.anchor_initial_start_index, caret_handler.anchor_initial_end_index))))
        wx.CallAfter(caret_handler.process_flags, flags)

    def handle_select_motion(self, caret_handler, evt, selecting_rows=False):
        log.debug("handle_select_motion: selecting_rows: %s" % (selecting_rows))
        if not self.mouse_drag_started:
            # On windows, it's possible to get a motion event before a mouse
            # down event, so need this flag to check
            return
        flags = DisplayFlags(None)
        update = False
        r, c, index1, index2, inside = self.get_location_from_event(evt)
        log.debug("handle_select_motion: index1: %s, index2: %s pending: %s" % (index1, index2, str(self.pending_select_awaiting_drag)))
        if c < 0 or selecting_rows or not inside:
            selecting_rows = True
            c = 0
        else:
            selecting_rows = False
            if self.pending_select_awaiting_drag is not None:
                # We have an actual drag so we can begin the selection
                caret_handler.anchor_initial_start_index, caret_handler.anchor_initial_end_index = self.pending_select_awaiting_drag
                self.pending_select_awaiting_drag = None
                self.select_range(caret_handler, caret_handler.anchor_initial_start_index, caret_handler.anchor_initial_end_index, add=self.multi_select_mode)
                update = True
        if self.select_extend_mode:
            if index1 < caret_handler.anchor_initial_start_index:
                self.select_range(caret_handler, index1, caret_handler.anchor_initial_end_index, extend=True)
                update = True
            else:
                self.select_range(caret_handler, caret_handler.anchor_initial_start_index, index2, extend=True)
                update = True
        else:
            if index2 >= caret_handler.anchor_initial_end_index:
                flags.caret_index = index1
                if selecting_rows:
                    index1, index2 = self.get_start_end_index_of_row(r)
                if index2 != caret_handler.anchor_end_index:
                    self.select_range(caret_handler, caret_handler.anchor_initial_start_index, index2, extend=self.multi_select_mode)
                    update = True
            elif index1 <= caret_handler.anchor_initial_start_index:
                if selecting_rows:
                    index1, index2 = self.get_start_end_index_of_row(r)
                if index1 != caret_handler.anchor_start_index:
                    self.select_range(caret_handler, index1, caret_handler.anchor_initial_end_index, extend=self.multi_select_mode)
                    update = True
        if update:
            flags.caret_index = index1
            flags.keep_selection = True
            wx.CallAfter(caret_handler.process_flags, flags)
        log.debug("handle_select_motion: update: %s, flags: %s, anchors=%s" % (update, flags, str((caret_handler.anchor_initial_start_index, caret_handler.anchor_initial_end_index))))

    def handle_select_end(self, caret_handler, evt):
        self.mouse_drag_started = False
        self.select_extend_mode = False
        self.multi_select_mode = False
        caret_handler.pending_focus = None

    def ClearSelection(self):
        # Stub function for those controls that don't have it. Tables use this
        # but nothing else so far.
        pass

    def get_location_from_event(self, evt):
        raise NotImplementedError

    def get_start_end_index_of_row(self, row):
        raise NotImplementedError

    def highlight_selected_ranges(self, caret_handler):
        caret_handler.document.change_count += 1
        s = caret_handler.segment
        s.clear_style_bits(selected=True)
        self.highlight_selected_ranges_in_segment(caret_handler.selected_ranges, s)
        caret_handler.calc_dependent_action_enabled_flags()

    def highlight_selected_ranges_in_segment(self, selected_ranges, segment):
        # This is default implementation which simply highlights everything
        # between the start/end values of each range. Other selection types
        # (rectangular selection) will need to be defined in the subclass
        segment.set_style_ranges(selected_ranges, selected=True)
