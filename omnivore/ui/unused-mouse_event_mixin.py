import time

import wx

from sawx import get_image_path
from sawx.utils.command import DisplayFlags
from sawx.framework.caret import Caret, SelectionHandler

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
        self.is_editing_in_cell = False
        self.is_mousing_while_editing = False
        self.pending_select_awaiting_drag = None
        self.caret_with_selection = None
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
        if self.mouse_mode.__class__ != mode:
            log.debug("set_mouse_mode: %s" % mode)
            self.mouse_mode = mode(self)
        else:
            log.debug("mouse mode already %s" % mode)

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
        if self.is_editing_in_cell and self.mouse_event_in_edit_cell(evt):
            self.is_mousing_while_editing = True
            self.on_left_down_in_edit_cell(evt)
        else:
            self.end_editing()
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
        if self.is_mousing_while_editing:
            self.on_motion_in_edit_cell(evt)
        else:
            mode = self.get_effective_tool_mode(evt)
            # log.debug("on_motion: effective mode=%s" % mode)
            if evt.LeftIsDown() and self.has_capture():
                mode.process_mouse_motion_down(evt)
            else:
                mode.process_mouse_motion_up(evt)
            self.set_cursor(mode)
        evt.Skip()

    def on_left_up(self, evt):
        self.stop_scroll_timer()
        if not self.has_capture():
            return
        self.release_mouse()
        if self.is_mousing_while_editing:
            self.is_mousing_while_editing = False
            self.on_left_up_in_edit_cell(evt)
        else:
            mode = self.get_effective_tool_mode(evt)
            log.debug("on_left_up: effective mode=%s" % mode)
            self.forced_cursor = None
            mode.process_left_up(evt)
            self.set_cursor(mode)
        evt.Skip()

    def on_left_dclick(self, evt):
        # self.SetFocus() # why would it not be focused?
        self.end_editing()
        mode = self.get_effective_tool_mode(evt)
        log.debug("on_left_dclick: effective mode=%s" % mode)
        mode.process_left_dclick(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_popup(self, evt):
        self.end_editing()
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

    ##### mouse processing while in cell edit mode

    def mouse_event_in_edit_cell(self, evt):
        return False

    def on_left_down_in_edit_cell(self, evt):
        pass

    def on_motion_in_edit_cell(self, evt):
        pass

    def on_left_up_in_edit_cell(self, evt):
        pass

    ##### autoscrolling

    def stop_scroll_timer(self):
        pass

    ##### command processor

    def create_mouse_event_flags(self):
        return self.segment_viewer.create_mouse_event_flags()

    def handle_motion_update_status(self, evt, row, col):
        msg = self.get_status_message_at_cell(row, col)
        if msg:
            self.segment_viewer.show_status_message(msg)

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
        try:
            r, c, index1, index2, inside = self.get_location_from_event(evt)
        except IndexError:
            log.warning("mouse event on invalid index")
            return
        self.mouse_drag_started = True
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
        log.debug(("start before:", ch.carets, "multi", self.multi_select_mode, "extend", self.select_extend_mode))
        if self.select_extend_mode:
            caret = self.caret_with_selection = ch.carets.current
            if index1 < caret.anchor_start_index:
                self.select_extend_mode = "bottom anchor"
                if not caret.has_selection:
                    caret.anchor_end_index += 1
                caret.anchor_start_index = index1
                caret.index = index1
            else:
                self.select_extend_mode = "top anchor"
                caret.anchor_end_index = index2
                caret.index = index2 - 1
            caret.anchor_initial_start_index, caret.anchor_initial_end_index = caret.anchor_start_index, caret.anchor_end_index
        else:
            if selecting_rows:
                index1, index2 = self.get_start_end_index_of_row(r)
                caret = Caret(index2)
                ch.carets.force_single_caret(caret)
                self.caret_with_selection = caret
                caret.anchor_initial_start_index, caret.anchor_initial_end_index = index1, index2
                caret.anchor_start_index, caret.anchor_end_index = index1, index2
                flags.keep_selection = True
                log.debug("handle_select_start selecting rows: flags: %s, anchors=%s" % (flags, str((caret.anchor_initial_start_index, caret.anchor_initial_end_index))))
            else:
                flags.keep_selection = True
                # initial click when not selecting rows should move the caret,
                # not select the grid square
                caret = Caret(index1)
                if self.multi_select_mode:
                    ch.add_caret(caret)
                    log.debug(("adding caret", caret))
                else:
                    ch.force_single_caret(caret)
                    log.debug(("forced single caret", caret))
                self.caret_with_selection = caret
                self.pending_select_awaiting_drag = (index1, index2)
                log.debug("handle_select_start placing cursor: flags: %s, index=%s" % (flags, index1))
        flags.caret_column = c
        self.commit_change(flags)
        log.debug(f"start after: {ch.carets}")

    def handle_select_motion(self, evt, row, col, flags=None):
        if not self.mouse_drag_started:
            # On windows, it's possible to get a motion event before a mouse
            # down event, so need this flag to check
            return
        if flags is None:
            flags = self.create_mouse_event_flags()
        ch = self.caret_handler
        update = False
        try:
            r, c, index1, index2, inside = self.get_location_from_col(row, col)
        except IndexError:
            log.debug("mouse location is a hidden cell; skipping")
            return
        log.debug("handle_select_motion: r=%d c=%d index1: %s, index2: %s pending: %s, sel rows: %s" % (r, c, index1, index2, str(self.pending_select_awaiting_drag), flags.selecting_rows))
        # log.debug("handle_select_motion: r=%d c=%d index1: %s, index2: %s pending: %s, sel rows: %s anchors: initial=%s current=%s" % (r, c, index1, index2, str(self.pending_select_awaiting_drag), flags.selecting_rows, str((caret.anchor_initial_start_index, caret.anchor_initial_end_index)), str((caret.anchor_start_index, caret.anchor_end_index))))
        log.debug(("motion before:", ch.carets))
        caret = self.caret_with_selection
        if c < 0 or flags.selecting_rows or not inside:
            selecting_rows = True
            index1, index2 = self.get_start_end_index_of_row(r)
            c = 0
        else:
            selecting_rows = False
            if self.pending_select_awaiting_drag is not None:
                # only start selection if the cursor is over a different cell
                # than the mouse down event
                if index1 == self.pending_select_awaiting_drag[0]:
                    return

                # We have an actual drag so we can begin the selection
                caret.anchor_initial_start_index, caret.anchor_initial_end_index = self.pending_select_awaiting_drag
                caret.anchor_start_index, caret.anchor_end_index = self.pending_select_awaiting_drag
                self.pending_select_awaiting_drag = None
                update = True

        if self.select_extend_mode == "top anchor":
            if index1 < caret.anchor_initial_start_index:
                caret.index = index1
                caret.anchor_start_index = index1
                caret.anchor_end_index = caret.anchor_initial_start_index + 1
                update = True
            else:
                caret.index = index2 - 1
                caret.anchor_start_index = caret.anchor_initial_start_index
                caret.anchor_end_index = index2
                update = True
        elif self.select_extend_mode == "bottom anchor":
            if index1 < caret.anchor_initial_end_index:
                caret.index = index1
                caret.anchor_start_index = index1
                caret.anchor_end_index = caret.anchor_initial_end_index
                update = True
            else:
                caret.index = index2 - 1
                caret.anchor_start_index = caret.anchor_initial_end_index
                caret.anchor_end_index = index2
                update = True
        else:
            if index2 >= caret.anchor_initial_end_index:
                caret.index = index2 - 1
                if index2 != caret.anchor_end_index:
                    caret.anchor_start_index = caret.anchor_initial_start_index
                    caret.anchor_end_index = index2
                    update = True
            elif index1 <= caret.anchor_initial_start_index:
                caret.index = index1
                if index1 != caret.anchor_start_index:
                    caret.anchor_start_index = index1
                    caret.anchor_end_index = caret.anchor_initial_end_index
                    update = True

        if update:
            self.commit_change(flags)
        log.debug("handle_select_motion: update: %s, flags: %s, anchors: initial=%s current=%s" % (update, flags, str((caret.anchor_initial_start_index, caret.anchor_initial_end_index)), str((caret.anchor_start_index, caret.anchor_end_index))))
        # log.debug(f"motion after: {ch.carets}")

    def handle_select_end(self, evt, row, col, flags=None):
        if flags is None:
            flags = self.create_mouse_event_flags()
        self.mouse_drag_started = False
        self.select_extend_mode = False
        self.multi_select_mode = False
        self.caret_with_selection = None
        self.caret_handler.carets.collapse_overlapping()
        if wx.Platform == "__WXMSW__":
            # FIXME: MSW doesn't seem to refresh after a mouse release
            # outside of the window, so force it here to fill in the remaining
            # bits of the selection
            log.debug("Extra refresh on handle_select_end for windows")
            self.refresh_view()
        self.commit_change(flags)
        log.debug(("end after:", self.caret_handler.carets))

    def commit_change(self, flags):
        log.debug(("commit before:", self.caret_handler.carets))
        self.refresh_ranges(self.caret_handler)
        self.caret_handler.sync_caret_event = flags
        self.caret_handler.ensure_visible_event = flags
        self.caret_handler.refresh_event = flags
        log.debug(("commit after:", self.caret_handler.carets))

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
        self.segment_viewer.highlight_selected_ranges_in_segment(ch.carets.selected_ranges, s)
        ch.calc_dependent_action_enabled_flags()
