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
        self.next_scroll_time = 0
        self.scroll_timer = None
        self.scroll_delay = 1000  # milliseconds

    def map_mouse_events(self, source):
        source.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        source.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        source.Bind(wx.EVT_MOTION, self.on_motion)
        source.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_TIMER, self.on_timer)

    def create_mouse_event_flags(self):
        flags = DisplayFlags(self)
        flags.selecting_rows = False
        flags.old_carets = set(self.caret_handler.caret_list)
        return flags

    def on_left_up(self, evt):
        self.scroll_timer.Stop()
        flags = self.create_mouse_event_flags()
        self.handle_select_end(self.caret_handler, evt, flags)

    def on_left_down(self, evt):
        flags = self.create_mouse_event_flags()
        self.handle_select_start(self.caret_handler, evt, flags)
        wx.CallAfter(self.SetFocus)

    def on_left_dclick(self, evt):
        self.on_left_down(evt)

    def can_scroll(self):
        self.set_scroll_timer()
        if time.time() >  self.next_scroll_time:
            self.next_scroll_time = time.time() + (self.scroll_delay / 1000.0)
            return True
        else:
            return False

    def set_scroll_timer(self):
        if self.scroll_timer is None:
            self.scroll_timer = wx.Timer(self)
        self.scroll_timer.Start(self.scroll_delay/2, True)

    def on_timer(self, event):
        screenX, screenY = wx.GetMousePosition()
        x, y = self.main.ScreenToClient((screenX, screenY))
        row, cell = self.main.pixel_pos_to_row_cell(x, y)
        self.handle_on_motion(event, row, cell)

    def is_left_of_screen(self, col):
        return col < self.main.sx

    def handle_left_of_screen(self, col):
        scroll_col = -1
        if col + scroll_col < 0:
            scroll_col = 0
        return scroll_col

    def is_right_of_screen(self, col):
        return col >= self.main.sx + self.main.sw

    def handle_right_of_screen(self, col):
        scroll_col = 1
        if col + scroll_col >= self.main.table.num_cells:
            scroll_col = 0
        return scroll_col

    def is_above_screen(self, row):
        return row < self.main.sy

    def handle_above_screen(self, row):
        scroll_row = -1
        if row + scroll_row < 0:
            scroll_row = 0
        return scroll_row

    def is_below_screen(self, row):
        return row >= self.main.sy + self.main.sh

    def handle_below_screen(self, row):
        scroll_row = 1
        if row + scroll_row >= self.main.table.num_rows:
            scroll_row = 0
        return scroll_row

    def on_motion(self, evt, x=None, y=None):
        row, col = self.get_row_col_from_event(evt)
        if evt.LeftIsDown():
            self.handle_on_motion(evt, row, col)
        else:
            self.handle_motion_update_status(row, col)
        evt.Skip()

    def handle_on_motion(self, evt, row, col):
        scroll_row = 0
        scroll_col = 0
        if self.is_left_of_screen(col):
            if self.can_scroll():
                scroll_col = self.handle_left_of_screen(col)
        elif self.is_right_of_screen(col):
            if self.can_scroll():
                scroll_col = self.handle_right_of_screen(col)
        if self.is_above_screen(row):
            if self.can_scroll():
                scroll_row = self.handle_above_screen(row)
        elif self.is_below_screen(row):
            if self.can_scroll():
                scroll_row = self.handle_below_screen(row)
        print("scroll delta: %d, %d" % (scroll_row, scroll_col))
        row += scroll_row
        col += scroll_col
        flags = self.create_mouse_event_flags()
        self.handle_select_motion(self.caret_handler, row, col, flags)
        self.handle_motion_update_status(row, col)
        #self.main.MouseToCaret(evt)

    def handle_motion_update_status(self, row, col):
        msg = self.get_status_message_at_cell(row, col)
        if msg:
            self.caret_handler.show_status_message(msg)

    def on_mouse_wheel(self, evt):
        """Driver to process mouse events.

        This is the main driver to process all mouse events that
        happen on the BitmapScroller.  Once a selector is triggered by
        its event combination, it becomes the active selector and
        further mouse events are directed to its handler.
        """
        if self.end_byte is None:  # end_byte is a proxy for the image being loaded
            return

        w = evt.GetWheelRotation()
        if evt.ControlDown():
            if w < 0:
                self.zoom_out()
            elif w > 0:
                self.zoom_in()

        evt.Skip()

    ##### Default selection handlers

    def handle_select_start(self, caret_handler, evt, flags):
        """ select_handler: interface with set_style_ranges to highlight bytes
        that should be selected (e.g. rect select will need different method
        than regular selection).

        caret_handler: object that implements the CaretHandler API
        """
        log.debug("handle_select_start: selecting_rows: %s" % (flags.selecting_rows))
        self.mouse_drag_started = True
        r, c, index1, index2, inside = self.get_location_from_event(evt)
        if c < 0 or flags.selecting_rows or not inside:
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
        self.commit_change(flags)

    def handle_select_motion(self, caret_handler, row, col, flags):
        if not self.mouse_drag_started:
            # On windows, it's possible to get a motion event before a mouse
            # down event, so need this flag to check
            return
        update = False
        r, c, index1, index2, inside = self.get_location_from_cell(row, col)
        log.debug("handle_select_motion: r=%d c=%d index1: %s, index2: %s pending: %s, sel rows: %s" % (r, c, index1, index2, str(self.pending_select_awaiting_drag), flags.selecting_rows))
        if c < 0 or flags.selecting_rows or not inside:
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
                caret_handler.caret_index = index1
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
            caret_handler.caret_index = index1
            flags.keep_selection = True
            self.commit_change(flags)
        log.debug("handle_select_motion: update: %s, flags: %s, anchors=%s" % (update, flags, str((caret_handler.anchor_initial_start_index, caret_handler.anchor_initial_end_index))))

    def handle_select_end(self, caret_handler, evt, flags):
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


