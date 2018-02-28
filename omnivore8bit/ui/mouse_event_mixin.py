import time

import wx

from omnivore import get_image_path
from omnivore.utils.command import DisplayFlags
from omnivore.framework.caret import SelectionHandler

import logging
log = logging.getLogger(__name__)


class MouseEventMixin(SelectionHandler):
    hand_cursor = None
    hand_closed_cursor = None

    def __init__(self, caret_handler, default_mouse_mode_cls):
        self.caret_handler = caret_handler
        self.multi_select_mode = False
        self.select_extend_mode = False
        self.mouse_drag_started = False
        self.pending_select_awaiting_drag = None
        self.source = None
        if self.__class__.hand_cursor is None:
            p = get_image_path("icons/hand.ico")
            self.hand_cursor = wx.Cursor(p, wx.BITMAP_TYPE_ICO, 16, 16)
            p = get_image_path("icons/hand_closed.ico")
            self.hand_closed_cursor = wx.Cursor(p, wx.BITMAP_TYPE_ICO, 16, 16)
        self.forced_cursor = None
        self.batch = None

        self.default_mouse_mode_cls = default_mouse_mode_cls
        self.default_mouse_mode = self.default_mouse_mode_cls(self)
        self.mouse_mode = self.default_mouse_mode  # can't call set_mouse_mode yet because control hasn't been initialized

    def map_mouse_events(self, source):
        self.source = source
        source.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        source.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        source.Bind(wx.EVT_MOTION, self.on_motion)
        source.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        source.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)
        source.Bind(wx.EVT_RIGHT_DOWN, self.on_popup)
        source.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        source.Bind(wx.EVT_SET_FOCUS, self.on_focus)
        source.Bind(wx.EVT_KILL_FOCUS, self.on_focus_lost)
        source.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_enter)
        source.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)

    def set_mouse_mode(self, mode=None):
        self.release_mouse()
        if mode is None:
            mode = self.default_mouse_mode_cls
        self.mouse_mode = mode(self)

    def capture_mouse(self):
        if not self.source.HasFocus():
            self.source.SetFocus()
        self.source.CaptureMouse()

    def has_capture(self):
        return self.source.HasCapture()

    def release_mouse(self):
        self.mouse_is_down = False
        self.selection_box_is_being_defined = False
        while self.source.HasCapture():
            self.source.ReleaseMouse()

    def set_cursor(self, mode=None):
        if (self.forced_cursor is not None):
            self.SetCursor(self.forced_cursor)
            #
            return

        if mode is None:
            mode = self.mouse_mode
        c = mode.get_cursor()
        self.SetCursor(c)

    def get_effective_tool_mode(self, event):
        middle_down = False
        alt_down = False
        if (event is not None):
            try:
                alt_down = event.AltDown()
                # print self.is_alt_key_down
            except:
                pass
            try:
                middle_down = event.MiddleIsDown()
            except:
                pass
        if alt_down or middle_down:
            mode = self.default_mouse_mode
        else:
            mode = self.mouse_mode
        return mode

    def on_left_down(self, evt):
        self.capture_mouse()
        mode = self.get_effective_tool_mode(evt)
        log.debug("on_left_down: effective mode=%s" % mode)
        self.forced_cursor = None
        self.selection_box_is_being_defined = False
        self.mouse_down_position = evt.GetPosition()
        self.mouse_move_position = self.mouse_down_position

        mode.process_left_down(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_motion(self, evt):
        mode = self.get_effective_tool_mode(evt)
        log.debug("on_motion: effective mode=%s" % mode)
        if evt.LeftIsDown() and self.has_capture():
            mode.process_mouse_motion_down(evt)
        else:
            mode.process_mouse_motion_up(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_left_up(self, evt):
        if not self.has_capture():
            return
        self.release_mouse()
        mode = self.get_effective_tool_mode(evt)
        log.debug("on_left_up: effective mode=%s" % mode)
        self.forced_cursor = None
        mode.process_left_up(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_left_dclick(self, evt):
        # self.SetFocus() # why would it not be focused?
        mode = self.get_effective_tool_mode(evt)
        log.debug("on_left_dclick: effective mode=%s" % mode)
        mode.process_left_dclick(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_popup(self, evt):
        mode = self.get_effective_tool_mode(evt)
        log.debug("on_popup: effective mode=%s" % mode)
        self.forced_cursor = None
        mode.process_popup(evt)
        self.set_cursor(mode)

    def on_mouse_wheel(self, evt):
        mode = self.get_effective_tool_mode(evt)
        log.debug("on_mouse_wheel: effective mode=%s" % mode)
        mode.process_mouse_wheel(evt)
        self.set_cursor(mode)

    def on_mouse_enter(self, evt):
        self.set_cursor()
        evt.Skip()

    def on_mouse_leave(self, evt):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.mouse_mode.process_mouse_leave(evt)
        evt.Skip()

    def on_focus(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode.process_focus(evt)

    def on_focus_lost(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode.process_focus_lost(evt)

    ##### 

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
            if selecting_rows:
                index1, index2 = self.get_start_end_index_of_row(r)
            elif self.multi_select_mode:
                flags.add_caret = True
                print("NEW CARET!", str(ch.carets))
            else:
                flags.force_single_caret = True
            ch.carets.current.index = index1
            ch.anchor_initial_start_index, ch.anchor_initial_end_index = index1, index2

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
        if wx.Platform == "__WXMSW__":
            # FIXME: MSW doesn't seem to refresh after a mouse release
            # outside of the window, so force it here to fill in the remaining
            # bits of the selection
            log.debug("Extra refresh on handle_select_end for windows")
            self.refresh_view()

    def commit_change(self, flags):
        self.caret_handler.process_flags(flags)

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
        self.segment_viewer.highlight_selected_ranges_in_segment(ch.selected_ranges, s)
        ch.calc_dependent_action_enabled_flags()
