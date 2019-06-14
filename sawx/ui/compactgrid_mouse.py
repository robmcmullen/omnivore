import sys
import functools
import weakref

import wx

try:
    from atrcopy import match_bit_mask, comment_bit_mask, user_bit_mask, selected_bit_mask, diff_bit_mask
except ImportError:
    user_bit_mask = 0x07
    diff_bit_mask = 0x10
    match_bit_mask = 0x20
    comment_bit_mask = 0x40
    selected_bit_mask = 0x80

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)
caret_log = logging.getLogger("caret")
# caret_log.setLevel(logging.DEBUG)
mode_log = logging.getLogger("mouse_mode")
# mode_log.setLevel(logging.DEBUG)

##### Carets

@functools.total_ordering
class Caret:
    """Class representing both a caret's row/col position, and optionally a
    single selected range or rectangular region.

    Anchor indexes behave like caret positions: they indicate positions
    between bytes.
    """
    def __init__(self, row=0, col=0, rectangular=False, state=None):
        if state is not None:
            self.restore(state)
        else:
            try:
                row.anchor_start
                self.restore(row.serialize())
            except AttributeError:
                self.rc = (row, col)
                self.anchor_start = self.anchor_initial_start = self.anchor_end = self.anchor_initial_end = (-1, -1)
                self.rectangular = rectangular

    def __bool__(self):
        return self.rc is not None

    __nonzero__=__bool__

    def __eq__(self, other):
        if not hasattr(self, 'rc'):
            caret_log.error("not a Caret object")
            return False
        caret_log.debug("comparing caret positions: %d %d" % (self.rc, other.rc))
        return self.rc == other.rc

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if self.has_selection:
            if other.has_selection:
                return self.anchor_start < other.anchor_start
            return self.anchor_start < other.rc
        return self.rc < other.rc

    def __repr__(self):
        return "Caret%s" % str(self.serialize())

    def __hash__(self):
        return hash(self.serialize())

    @property
    def has_selection(self):
        return self.anchor_start >= (0,0)

    @property
    def range(self):
        if not self.has_selection:
            raise ValueError("No selection")
        s = self.anchor_start
        e = self.anchor_end
        return (s, e) if e > s else (e, s)

    @property
    def range_including_caret(self):
        if self.has_selection:
            s = self.anchor_start
            e = self.anchor_end
            if s > e: s, e = e, s
        else:
            s = e = self.rc
        return (s, e)

    def set(self, r, c):
        self.rc = (r, c)
        self.clear_selection()

    def clear_selection(self):
        self.anchor_start = self.anchor_initial_start = self.anchor_end = self.anchor_initial_end = (-1, -1)

    def set_initial_selection(self, start, end):
        self.anchor_start = self.anchor_initial_start = start
        self.anchor_end = self.anchor_initial_end = end

    def set_selection(self, start, end):
        self.anchor_start = start
        self.anchor_end = end

    def serialize(self):
        return (self.rc, self.anchor_start, self.anchor_initial_start, self.anchor_end, self.anchor_initial_end, self.rectangular)

    def restore(self, state):
        try:
            self.rc, self.anchor_start, self.anchor_initial_start, self.anchor_end, self.anchor_initial_end, self.rectangular = state
        except TypeError:
            self.rc = state
            self.clear_selection()

    def copy(self):
        state = self.serialize()
        return Caret(state=state)

    def contains(self, other):
        return self.anchor_start >= (0,0) and other.anchor_start >= self.anchor_start and other.anchor_end <= self.anchor_end

    def intersects(self, other):
        return not (other.anchor_start > self.anchor_end or other.anchor_end < self.anchor_start)

    def in_selection(self, row, col):
        return (row, col) >= self.anchor_start and (row, col) <= self.anchor_end

    def merge(self, other):
        """Merge boundaries of other into this caret"""
        if other.anchor_start < self.anchor_start:
            self.anchor_start = other.anchor_start
            self.anchor_initial_start = other.anchor_initial_start
            if other.rc < self.rc:
                self.rc = other.rc
        if other.anchor_end > self.anchor_end:
            self.anchor_end = other.anchor_end
            self.anchor_initial_end = other.anchor_initial_end
            if other.rc > self.rc:
                self.rc = other.rc

    def add_selection_to_style(self, table):
        if self.has_selection:
            if self.rectangular:
                pass
            else:
                start, end = self.anchor_start, self.anchor_end
                if end < start:
                    start, end = end, start
                index1, _ = table.get_index_range(*start)
                _, index2 = table.get_index_range(*end)
                table.set_selected_index_range(index1, index2)


class MultiCaretHandler:
    def __init__(self):
        self.carets = []

    def __str__(self):
        return "MultiCaretHandler: carets=" + " ".join([str(c) for c in self.carets])

    def __len__(self):
        return len(self.carets)

    @property
    def current(self):
        return self.carets[-1]  # last one is the most recent

    @property
    def has_carets(self):
        return len(self.carets) > 0

    @property
    def has_selection(self):
        for caret in self.carets:
            if caret.has_selection:
                return True
        return False

    @property
    def carets_with_selection(self):
        for caret in self.carets:
            if caret.has_selection:
                yield caret

    @property
    def selected_ranges(self):
        return [c.range for c in self.carets if c.has_selection]

    def copy(self):
        handler = MultiCaretHandler()
        handler.carets = [c.copy() for c in self.carets]
        return handler

    def new_carets(self, caret_state):
        self.carets = [Caret(state=s) for s in caret_state]

    def calc_state(self):
        return [caret.serialize() for caret in self.carets]

    def has_changed_state(self, other_state):
        current = self.calc_state()
        return current == other_state

    def convert_to_indexes(self, table):
        index_list = []
        for caret in self.carets:
            index, _ = table.get_index_range(*caret.rc)
            if caret.anchor_start[0] < 0:
                anchor_start = -1
            else:
                anchor_start, _ = table.get_index_range(*caret.anchor_start)
            if caret.anchor_end[0] < 0:
                anchor_end = -1
            else:
                anchor_end, _ = table.get_index_range(*caret.anchor_end)
            index_list.append((index, anchor_start, anchor_end))
        return index_list

    def convert_from_indexes(self, table, indexes):
        self.carets = []
        for index, anchor_start, anchor_end in indexes:
            r, c = table.index_to_row_col(index)
            caret = Caret(r, c)
            r, c = table.index_to_row_col(anchor_start)
            caret.anchor_start = self.anchor_initial_start = (r, c)
            r, c = table.index_to_row_col(anchor_end)
            caret.anchor_end = self.anchor_initial_end = (r, c)
            self.carets.append(caret)

    def add_caret(self, caret):
        self.carets.append(caret)

    def move_carets_vertically(self, table, delta_r):
        caret_log.debug(f"moving vertically: {delta_r}")
        for caret in self.carets:
            caret.rc = table.enforce_valid_row_col(caret.rc[0] + delta_r, caret.rc[1])
            caret.clear_selection()
        self.validate_carets()

    def move_carets_horizontally(self, table, delta_c, wrap=False):
        caret_log.debug(f"moving horizontally: {delta_c}")
        for caret in self.carets:
            r = caret.rc[0]
            c = caret.rc[1] + delta_c
            if wrap and not table.is_row_col_inside(r, c):
                if c < 0:
                    r -= 1
                    c += table.get_items_in_row(r)
                else:
                    r += 1
                    c -= table.get_items_in_row(r)
            caret.rc = table.enforce_valid_row_col(r, c)
            caret.clear_selection()
        self.validate_carets()

    def move_carets_to(self, r, c):
        self.carets = [Caret(r, c)]

    def move_current_caret_to(self, r, c):
        try:
            caret = self.carets[-1]
            caret.rc = r, c
        except IndexError:
            self.move_carets_to(r, c)

    def move_current_caret_to_index(self, table, index):
        r, c = table.index_to_row_col(index)
        self.carets = [Caret(r, c)]

    def move_carets_process_function(self, func):
        for caret in self.carets:
            caret.rc = func(*caret.rc)
            caret.clear_selection()

    def validate_carets(self):
        # new_carets = []
        # for caret in self.carets:
        #     index = self.validate_caret_position(index)
        #     new_carets.append(index)
        # self.carets = new_carets
        pass

    def validate_caret_position(self, table, index):
        return table.enforce_valid_index(index)

    def refresh_style_from_selection(self, table):
        table.clear_selected_style()
        for caret in self.carets:
            caret.add_selection_to_style(table)

    def collapse_overlapping(self):
        """Check if the current caret selection overlaps any existing caret and
        merge any overlaps into the current caret.
        """
        caret_log.debug("before collapsed carets: {str(self.carets)}")
        try:
            current = self.carets.pop()
        except IndexError:
            # No carets! Can't be an overlap
            return
        if self.carets:
            if current.has_selection:
                collapsed = []
                for c in self.carets:
                    if current.contains(c):
                        # gets rid of any selections wholly contained within
                        # the current selection, or any standalone carets
                        # inside the selection
                        continue
                    elif current.intersects(c):
                        current.merge(c)
                    else:
                        collapsed.append(c)
                self.carets = collapsed
            else:
                # Merge caret into selection
                collapsed = []
                for c in self.carets:
                    if current.has_selection:
                        # if caret has been merged into a selection, don't do
                        # any further checking.
                        collapsed.append(c)
                    else:
                        if not c.has_selection and c.rc == current.rc:
                            # gets rid of any duplicate carets
                            continue
                        elif c.contains(current):
                            # if caret inside a selection, make the that the
                            # current caret
                            current = c
                        else:
                            collapsed.append(c)
                self.carets = collapsed
        self.carets.append(current)
        caret_log.debug(f"collapsed carets {str(self.carets)}")

    def collapse_selections_to_carets(self):
        for caret in self.carets:
            caret.clear_selection()

    def get_selected_ranges_and_indexes(self, table):
        opt = self.get_selected_ranges(table)
        return opt, ranges_to_indexes(opt)

    def invert_selection_ranges(self, table, ranges):
        return invert_ranges(ranges, caret_handler.document_length)

    def process_char_flags(self, flags):
        """Perform the UI updates given the StatusFlags or BatchFlags flags
        
        """
        visible_range = False
        caret_moved = False
        log.debug("processing caret flags: %s" % str(flags))

        if flags.old_carets is not None:
            log.debug(f"old_carets: {flags.old_carets}")
            if flags.add_caret:
                self.carets.add_old_carets(flags.old_carets)
                caret_moved = True
                log.debug("caret added! before: %s, after: %s" % (flags.old_carets, self.carets))
            elif flags.force_single_caret:
                if flags.caret_index is not None:
                    self.carets.new_caret(flags.caret_index)
                self.carets.remove_old_carets()
                caret_moved = True
                log.debug("force_single_caret")
            else:
                self.validate_carets()
                caret_state = self.calc_state()
                caret_moved = caret_state != flags.old_carets
                log.debug("caret moved: %s old_carets: %s, new carets: %s" % (caret_moved, flags.old_carets, caret_state))
            if caret_moved:
                if not flags.keep_selection:
                    index = self.current.index
                    self.current.set_initial_selection(index, index)
                visible_range = True
                # self.sync_caret_event = flags
                log.debug("caret_moved")
        elif flags.force_single_caret:
            log.debug(f"force_single_caret: caret_index={flags.caret_index}")
            if flags.caret_index is not None:
                c = Caret(flags.caret_index)
                self.carets.force_single_caret(c)
                caret_moved = True
                # self.sync_caret_event = flags

        if flags.index_range is not None:
            log.debug(f"index_range: {flags.index_range}")
            if flags.select_range:
                log.debug(f"select_range")
                self.current.set_anchors(flags.index_range[0], flags.index_range[1])
                document.change_count += 1
            visible_range = True

        if visible_range:
            # Only update the range on the current editor, not other views
            # which are allowed to remain where they are
            log.debug(f"visible_range: index_visible={flags.index_visible}")
            if flags.index_visible is None:
                flags.index_visible = self.current.index
            self.ensure_visible_event = flags

            flags.refresh_needed = True

        if flags.viewport_origin is not None:
            flags.source_control.move_viewport_origin(flags.viewport_origin)
            flags.skip_source_control_refresh = True
            flags.refresh_needed = True
        log.debug(f"FINISHED process_caret_flags: refresh_needed={flags.refresh_needed}, skip_source_control_refresh={flags.skip_source_control_refresh}")


##### Mouse modes

class MouseMode(object):
    """
    Processing of mouse events, separate from the rendering window
    
    This is an object-based control system of mouse modes
    """
    icon = "help.png"
    menu_item_name = "Generic Mouse Mode"
    menu_item_tooltip = "Tooltip for generic mouse mode"

    mouse_too_close_pixel_tolerance = 5

    def __init__(self, window):
        self.control = weakref.proxy(window)
        self.snapped_point = None, 0
        self.first_mouse_down_position = 0, 0
        self.after_first_mouse_up = False
        self.mouse_up_too_close = False
        self.can_snap = False

        # left_up events can be called after double click on some platforms, so
        # this parameter can be set by the parent of the handler if the handler
        # wants to differentiate response to left_up
        self.num_clicks = 0

        # Optional (only OS X at this point) mouse wheel event filter
        self.wheel_scroll_count = 0
        self.use_every_nth_wheel_scroll = 5

        self.init_post_hook()

    def init_post_hook(self):
        pass

    def cleanup(self):
        pass

    def get_cursor(self):
        return wx.Cursor(wx.CURSOR_ARROW)

    def get_position(self, evt):
        return evt.GetPosition()

    def reset_early_mouse_params(self):
        self.mouse_up_too_close = False
        self.after_first_mouse_up = False

    def check_early_mouse_release(self, evt):
        c = self.control
        p = evt.GetPosition()
        dx = p[0] - self.first_mouse_down_position[0]
        dy = p[1] - self.first_mouse_down_position[1]
        tol = self.mouse_too_close_pixel_tolerance
        if abs(dx) < tol and abs(dy) < tol:
            return True
        return False

    ##### Sublasses need to override these for customized actions

    def process_mouse_motion_down(self, evt):
        evt.Skip()

    def process_left_down(self, evt):
        evt.Skip()

    def process_mouse_motion_up(self, evt):
        evt.Skip()

    def process_left_up(self, evt):
        evt.Skip()

    def process_left_dclick(self, evt):
        evt.Skip()

    def process_popup(self, evt):
        data = self.calc_popup_data(evt)
        self.control.add_popup_data(evt, data)
        log.debug(f"process_popup: found popup data {data}")
        popup_desc = self.calc_popup_menu(evt)
        if popup_desc:
            log.debug(f"process_popup: found popup menu for mode {self.menu_item_name}; skipping calc_popup_menu from {self.control}")
        else:
            popup_desc = self.control.calc_popup_menu(evt)
        log.debug(f"process_popup: using popup menu {popup_desc}")
        if popup_desc:
            self.show_popup(popup_desc, data)

    def calc_popup_data(self, evt):
        return {}

    def calc_popup_menu(self, evt):
        return []

    def show_popup(self, popup_desc, data):
        # default is a proxy to the CompactGrid object, but subclasses may have
        # different needs depending on the mode, so this hook is provided.
        self.control.show_popup(popup_desc, data)

    def process_mouse_wheel(self, evt):
        c = self.control
        rotation = evt.GetWheelRotation()
        delta = evt.GetWheelDelta()
        window = evt.GetEventObject()
        mode_log.debug("on_mouse_wheel_scroll. rot=%s delta=%d win=%s" % (rotation, delta, window))
        if rotation == 0 or delta == 0:
            return

        if sys.platform == "darwin":
            # OS X mouse wheel handling is not the same as other platform.
            # The delta value is 10 while the other platforms are 120,
            # and the rotation amount varies, seemingly due to the speed at
            # which the wheel is rotated (or how fast the trackpad is swiped)
            # while other platforms are either 120 or -120.  When mouse wheel
            # handling is performed in the usual manner on OS X it produces a
            # strange back-and-forth zooming in/zooming out.  So, this extra
            # hack is needed to operate like the other platforms.

            # add extra to the rotation so the minimum amount is 1 or -1
            extra = delta if rotation > 0 else -delta
            amount = (rotation + extra) // delta
            self.wheel_scroll_count -= abs(amount)
            if self.wheel_scroll_count > 0:
                return
            self.wheel_scroll_count = self.use_every_nth_wheel_scroll
        else:
            amount = rotation // delta

        if evt.ControlDown():
            if amount < 0:
                self.zoom_out(evt, amount)
            elif amount > 0:
                self.zoom_in(evt, amount)
        elif not evt.ShiftDown() and not evt.AltDown():
            self.pan_mouse_wheel(evt, amount)
        else:
            evt.Skip()

    def zoom_out(self, evt, amount):
        evt.Skip()

    def zoom_in(self, evt, amount):
        evt.Skip()

    def pan_mouse_wheel(self, evt, amount):
        self.control.pan_mouse_wheel(evt)

    def process_mouse_enter(self, evt):
        evt.Skip()

    def process_mouse_leave(self, evt):
        evt.Skip()

    def process_focus(self, evt):
        pass

    def process_focus_lost(self, evt):
        pass

    #### Selection

    def select_all(self, caret_handler, refresh=True):
        """ Selects the entire document
        """
        caret_handler.move_carets_to(0, 0)
        caret = caret_handler.current
        start = caret.rc
        t = self.control.table
        end = t.index_to_row_col(t.last_valid_index)
        caret.set_initial_selection(start, end)
        self.highlight_selected_ranges(caret_handler)
        self.control.update_ui_for_selection_change()

    def select_none(self, caret_handler, refresh=True):
        """ Clears any selection in the document
        """
        caret_handler.collapse_selections_to_carets()
        self.highlight_selected_ranges(caret_handler)
        self.control.update_ui_for_selection_change()

    def select_none_if_selection(self, caret_handler):
        if caret_handler.has_selection:
            self.select_none(caret_handler)

    def select_ranges(self, caret_handler, ranges, refresh=True):
        """ Selects the specified ranges
        """
        caret_handler.carets.selected_ranges = ranges
        try:
            start, end = caret_handler.carets.selected_ranges[-1]
        except IndexError:
            start, end = 0, 0
        caret_handler.anchor_start_index = caret_handler.anchor_initial_start_index = start
        caret_handler.anchor_end_index = caret_handler.anchor_initial_end_index = end
        self.highlight_selected_ranges(caret_handler)
        self.control.update_ui_for_selection_change()

    def select_invert(self, caret_handler, refresh=True):
        """ Selects the entire document
        """
        ranges = self.invert_selection_ranges(caret_handler, caret_handler.carets.selected_ranges)
        self.select_ranges(caret_handler, ranges, refresh)

    def select_range(self, caret_handler, start, end, add=False, extend=False):
        """ Adjust the current selection to the new start and end indexes
        """
        if extend:
            caret = caret_handler.current
            caret.set_selection(start, end)
        elif add:
            caret = Caret(end)
            caret.set_initial_selection(start, end)
            caret_handler.add_caret(caret)
        else:
            caret = Caret(end)
            caret.set_initial_selection(start, end)
            caret_handler.carets.force_single_caret(caret)
        self.refresh_ranges(caret_handler)

    def refresh_ranges(self, caret_handler):
        log.debug("refreshing ranges: %s" % str(caret_handler.carets))
        self.highlight_selected_ranges(caret_handler)
        self.control.update_ui_for_selection_change()

    def highlight_selected_ranges(self, caret_handler):
        # log.error("highlight_selected_ranges not defined in mouse mode")
        caret_handler.refresh_style_from_selection(self.control.table)


class NormalSelectMode(MouseMode):
    def init_post_hook(self):
        self.last_mouse_event = -1, -1
        self.event_modifiers = None

    def process_mouse_motion_up(self, evt):
        mode_log.debug("NormalSelectMode: process_mouse_motion_up")
        cg = self.control
        input_row, input_cell = cg.get_row_cell_from_event(evt)
        if (input_row, input_cell) == self.last_mouse_event:
            # only process if mouse has moved to a new cell; no sub-cell
            # events!
            return
        self.last_mouse_event = (input_row, input_cell)
        cmd = self.calc_mouse_motion_up_command(evt, input_row, input_cell)
        if cmd:
            cg.process_command(cmd)

    def calc_mouse_motion_up_command(self, evt, row, cell):
        cg = self.control
        col = cg.main.cell_to_col(row, cell)
        cg.handle_motion_update_status(evt, row, col)

    def process_left_down(self, evt):
        cg = self.control
        flags = cg.create_mouse_event_flags()
        input_row, input_cell = cg.get_row_cell_from_event(evt)
        mode_log.debug(f"NormalSelectMode: process_left_down: {input_row} {input_cell}")
        self.event_modifiers = evt.GetModifiers()
        self.last_mouse_event = (input_row, input_cell)
        cmd = self.calc_left_down_command(evt, input_row, input_cell, flags)
        if cmd:
            cg.process_command(cmd)
        else:
            cg.Refresh()

    def calc_left_down_command(self, evt, row, cell, flags):
        cg = self.control
        cg.main.update_caret_from_mouse(row, cell, flags)
        cg.handle_select_start(evt, cg.main.current_caret_row, cg.main.current_caret_col, flags)

    def process_mouse_motion_down(self, evt):
        cg = self.control
        input_row, input_cell = cg.get_row_cell_from_event(evt)
        if (input_row, input_cell) == self.last_mouse_event:
            # only process if mouse has moved to a new cell; no sub-cell
            # events!
            return
        mode_log.debug(f"NormalSelectMode: process_mouse_motion_down: {input_row} {input_cell}")
        self.last_mouse_event = (input_row, input_cell)
        flags = cg.create_mouse_event_flags()
        cmd = self.calc_mouse_motion_down_command(evt, input_row, input_cell, flags)
        if cmd:
            cg.process_command(cmd)
        else:
            cg.Refresh()

    def calc_mouse_motion_down_command(self, evt, row, cell, flags):
        cg = self.control
        last_row, last_col = cg.main.current_caret_row, cg.main.current_caret_col
        cg.main.handle_user_caret(row, cell, flags)
        if last_row != cg.main.current_caret_row or last_col != cg.main.current_caret_col:
            cg.handle_select_motion(evt, cg.main.current_caret_row, cg.main.current_caret_col, flags)

    def process_left_up(self, evt):
        mode_log.debug("NormalSelectMode: process_left_up")
        cg = self.control
        cg.main.scroll_timer.Stop()
        self.event_modifiers = None
        cg.handle_select_end(evt, cg.main.current_caret_row, cg.main.current_caret_col)

    def process_left_dclick(self, evt):
        mode_log.debug("NormalSelectMode: process_left_dclick")
        evt.Skip()

    def calc_popup_data(self, evt):
        cg = self.control
        row, col, inside = cg.get_row_col_from_event(evt)
        if inside:
            index, _ = cg.table.get_index_range(row, col)
            style = cg.table.segment.style[index]
        else:
            style = 0
        popup_data = {
            'control': cg,
            'index': index,
            'in_selection': style&0x80,
            'row': row,
            'col': col,
            'inside': inside,
            }
        return popup_data

    def zoom_in(self, evt, amount):
        self.control.zoom_in()

    def zoom_out(self, evt, amount):
        self.control.zoom_out()


class RectangularSelectMode(NormalSelectMode):
    icon = "select.png"
    menu_item_name = "Select"
    menu_item_tooltip = "Select rectangular regions"

    def display_coords(self, evt, extra=None):
        mode_log.debug("display_coords")
        cg = self.control
        v = cg.segment_viewer
        row, col, inside = cg.get_row_col_from_event(evt)
        index, _ = cg.table.get_index_range(row, col)
        msg = "x=$%x y=$%x index=$%x" % (col, row, index)
        if extra:
            msg += " " + extra
        cg.show_status_message(msg)






class DisplayFlags:
    def __init__(self, source_control=None, args=[]):
        # True if command successfully completes, must set to False on failure
        self.success = True

        # True if command made a change to the document and therefore should be recorded
        self.changed_document = True

        # List of errors encountered
        self.errors = []

        # Message displayed to the user
        self.message = ""

        # has any data values changed, forcing all views to be refreshed?
        self.byte_values_changed = False

        # has any data style changed, forcing all views to be refreshed?
        self.byte_style_changed = False

        # has anything in the data or metadata changed to require a rebuild
        # of the data model?
        self.data_model_changed = False

        # set to True if the all views of the data need to be refreshed
        self.refresh_needed = False

        # ensure the specified index is visible
        self.index_visible = None

        # ensure the specified index range is visible
        self.index_range = None

        # set to True if the index_range should be selected
        self.select_range = False

        # set caret index to position
        self.caret_index = None

        # keep any selection instead of erasing during a caret move
        self.keep_selection = None

        # set if document properties have changed, but not the actual data
        self.metadata_dirty = None

        # set if user interface needs to be updated (very heavyweight call!)
        self.rebuild_ui = None

        # the source control on which the event happened, if this is the
        # result of a user interface change
        self.source_control = source_control

        # if the source control is refreshed as a side-effect of some action,
        # set this flag so that the event manager can skip that control when
        # it refreshes the others
        self.skip_source_control_refresh = False

        # if the portion of the window looking at the data needs to be changed,
        # these will be the new upper left coordinates
        self.viewport_origin = None

        # list of viewers that have been refreshed during the caret_flags
        # processing so it won't be updated again
        self.refreshed_as_side_effect = set()

        # set if the user is selecting by entire rows
        self.selecting_rows = False

        # if not None, will contain the set carets to determine if any have
        # moved and need to be updated.
        self.old_carets = None

        # if True will add the old carets to the current caret to increase the
        # number of carets by one
        self.add_caret = False

        # if True will remove all carets except the current caret
        self.force_single_caret = False

        # move the caret(s) to the next edit position (usually column) using
        # the control as the basis for how much the index needs to be adjusted
        # to get to the next column.
        self.advance_caret_position_in_control = None

        # sync the carets in all other controls from the given control.
        self.sync_caret_from_control = None

        if args:
            for flags in args:
                self.add_flags(flags)

    def __str__(self):
        flags = []
        flags.append(f"source_control={self.source_control}")
        for name in dir(self):
            if name.startswith("_"):
                continue
            val = getattr(self, name)
            if val is None or not val or hasattr(val, "__call__"):
                continue
            flags.append("%s=%s" % (name, val))
        return ", ".join(flags)

    def add_flags(self, flags, cmd=None):
        if flags.message is not None:
            self.message += flags.message
        if flags.errors:
            if cmd is not None:
                self.errors.append("In %s:" % str(cmd))
            for e in flags.errors:
                self.errors.append("  %s" % e)
            self.errors.append("")
        if flags.byte_values_changed:
            self.byte_values_changed = True
        if flags.byte_style_changed:
            self.byte_style_changed = True
        if flags.refresh_needed:
            self.refresh_needed = True
        if flags.select_range:
            self.select_range = True
        if flags.metadata_dirty:
            self.metadata_dirty = True
        if flags.rebuild_ui:
            self.rebuild_ui = True

        # Expand the index range to include the new range specified in flags
        if flags.index_range is not None:
            if self.index_range is None:
                self.index_range = flags.index_range
            else:
                s1, s2 = self.index_range
                f1, f2 = flags.index_range
                if f1 < s1:
                    s1 = f1
                if f2 > s2:
                    s2 = f1
                self.index_range = (s1, s2)

        if flags.caret_index is not None:
            self.caret_index = flags.caret_index
        if flags.force_single_caret:
            self.force_single_caret = flags.force_single_caret
        if flags.keep_selection:
            self.keep_selection = flags.keep_selection
        if flags.source_control:
            self.source_control = flags.source_control
        if flags.advance_caret_position_in_control:
            self.advance_caret_position_in_control = flags.advance_caret_position_in_control
        if flags.sync_caret_from_control:
            self.sync_caret_from_control = flags.sync_caret_from_control




class GridCellTextCtrl(wx.TextCtrl):
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





class MouseEventMixin:
    default_mouse_mode_cls = NormalSelectMode

    def __init__(self, caret_handler, mouse_mode_cls=None):
        self.caret_handler = caret_handler
        self.multi_select_mode = False
        self.select_extend_mode = False
        self.mouse_drag_started = False
        self.is_editing_in_cell = False
        self.is_mousing_while_editing = False
        self.pending_select_awaiting_drag = None
        self.source = None
        self.edit_source = None
        self.forced_cursor = None
        self.batch = None

        if mouse_mode_cls is None:
            mouse_mode_cls = self.default_mouse_mode_cls
        self.default_mouse_mode_cls = mouse_mode_cls  # override class attr
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
        mode_log.debug(f"set_mouse_mode: current mode: {self.mouse_mode}")
        if mode is None:
            mode = self.default_mouse_mode_cls
        if not self.is_mouse_mode(mode):
            mode_log.debug("set_mouse_mode: %s" % mode)
            self.mouse_mode = mode(self)
        else:
            mode_log.debug("mouse mode already %s" % mode)

    def is_mouse_mode(self, mode):
        return self.mouse_mode.__class__ == mode

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
            mode_log.debug("on_left_down: effective mode=%s" % mode)
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
            # mode_log.debug("on_motion: effective mode=%s" % mode)
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
            mode_log.debug("on_left_up: effective mode=%s" % mode)
            self.forced_cursor = None
            mode.process_left_up(evt)
            self.set_cursor(mode)
        evt.Skip()

    def on_left_dclick(self, evt):
        # self.SetFocus() # why would it not be focused?
        self.end_editing()
        mode = self.get_effective_tool_mode(evt)
        mode_log.debug("on_left_dclick: effective mode=%s" % mode)
        mode.process_left_dclick(evt)
        self.set_cursor(mode)
        evt.Skip()

    def on_popup(self, evt):
        self.end_editing()
        mode = self.get_effective_tool_mode(evt)
        mode_log.debug("on_popup: effective mode=%s" % mode)
        self.forced_cursor = None
        mode.process_popup(evt)
        self.set_cursor(mode)

    def on_mouse_wheel(self, evt):
        mode = self.get_effective_tool_mode(evt)
        mode_log.debug("on_mouse_wheel: effective mode=%s" % mode)
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
        flags = DisplayFlags(self)
        flags.selecting_rows = False
        flags.old_carets = self.caret_handler.calc_state()
        return flags

    def handle_motion_update_status(self, evt, row, col):
        msg = self.get_status_message_at_row_col(row, col)
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
        r, c, inside = self.get_row_col_from_event(evt)
        self.mouse_drag_started = True
        if c < 0 or flags.selecting_rows or not inside:
            c = 0
            selecting_rows = True
            c_end_of_row = self.table.get_items_in_row(r)
        else:
            selecting_rows = False
        mouse_at = (r, c)
        mode_log.debug("handle_select_start: rows=%s, row,col=%d,%d r,c=%d,%d inside=%s" % (selecting_rows, row, col, r, c, inside))
        if evt.ControlDown():
            self.multi_select_mode = True
            self.select_extend_mode = False
        elif evt.ShiftDown():
            self.multi_select_mode = False
            self.select_extend_mode = True
        mode_log.debug(f"start before: {ch.carets}, multi {self.multi_select_mode}, extend {self.select_extend_mode}")
        if self.select_extend_mode:
            caret = ch.current
            if mouse_at < caret.anchor_start:
                self.select_extend_mode = "bottom anchor"
                if not caret.has_selection:
                    caret.anchor_end = mouse_at
                caret.anchor_start = mouse_at
                caret.rc = mouse_at
            else:
                self.select_extend_mode = "top anchor"
                caret.anchor_end = mouse_at
                caret.rc = mouse_at
            caret.anchor_initial_start, caret.anchor_initial_end = caret.anchor_start, caret.anchor_end
        else:
            if selecting_rows:
                ch.move_carets_to(*mouse_at)
                caret = ch.current
                caret.anchor_initial_start = caret.anchor_start = mouse_at
                caret.anchor_initial_end = caret.anchor_end = (r, c_end_of_row)
                flags.keep_selection = True
                mode_log.debug("handle_select_start selecting rows: flags: %s, anchors=%s" % (flags, str((caret.anchor_initial_start, caret.anchor_initial_end))))
            else:
                flags.keep_selection = True
                # initial click when not selecting rows should move the caret,
                # not select the grid square
                if self.multi_select_mode:
                    caret = Caret(*mouse_at)
                    ch.add_caret(caret)
                    mode_log.debug(("adding caret", caret))
                else:
                    ch.move_carets_to(*mouse_at)
                    caret = ch.current
                    mode_log.debug(("forced single caret", caret))
                self.pending_select_awaiting_drag = mouse_at
                mode_log.debug("handle_select_start placing cursor: flags: %s, rc=%s" % (flags, mouse_at))
        self.commit_change(flags)
        mode_log.debug(f"start after: {ch.carets}")

    def handle_select_motion(self, evt, row, col, flags=None):
        if not self.mouse_drag_started:
            # On windows, it's possible to get a motion event before a mouse
            # down event, so need this flag to check
            return
        if flags is None:
            flags = self.create_mouse_event_flags()
        ch = self.caret_handler
        update = flags.refresh_needed
        inside = True ## FIXME
        r = row
        c = col
        mouse_at = (r, c)
        mode_log.debug("handle_select_motion: r=%d c=%d pending: %s, flags: %s" % (r, c, str(self.pending_select_awaiting_drag), flags))
        # mode_log.debug("handle_select_motion: r=%d c=%d index1: %s, index2: %s pending: %s, sel rows: %s anchors: initial=%s current=%s" % (r, c, index1, index2, str(self.pending_select_awaiting_drag), flags.selecting_rows, str((caret.anchor_initial_start_index, caret.anchor_initial_end_index)), str((caret.anchor_start_index, caret.anchor_end_index))))
        mode_log.debug(("motion before:", ch.carets))
        caret = ch.current
        if c < 0 or flags.selecting_rows or not inside:
            selecting_rows = True
            c = 0
        else:
            selecting_rows = False
            if self.pending_select_awaiting_drag is not None:
                # only start selection if the cursor is over a different cell
                # than the mouse down event
                if mouse_at == self.pending_select_awaiting_drag:
                    return

                # We have an actual drag so we can begin the selection
                caret.anchor_initial_start = caret.anchor_initial_end = self.pending_select_awaiting_drag
                caret.anchor_start = caret.anchor_end = self.pending_select_awaiting_drag
                self.pending_select_awaiting_drag = None
                update = True

        if self.select_extend_mode == "top anchor":
            if mouse_at < caret.anchor_initial_start:
                caret.rc = mouse_at
                caret.anchor_start = mouse_at
                caret.anchor_end = caret.anchor_initial_start
                update = True
            else:
                caret.rc = mouse_at
                caret.anchor_start = caret.anchor_initial_start
                caret.anchor_end = mouse_at
                update = True
        elif self.select_extend_mode == "bottom anchor":
            if mouse_at < caret.anchor_initial_end:
                caret.rc = mouse_at
                caret.anchor_start = mouse_at
                caret.anchor_end = caret.anchor_initial_end
                update = True
            else:
                caret.rc = mouse_at
                caret.anchor_start = caret.anchor_initial_end
                caret.anchor_end = mouse_at
                update = True
        else:
            if mouse_at >= caret.anchor_initial_end:
                caret.rc = mouse_at
                if mouse_at != caret.anchor_end:
                    caret.anchor_start = caret.anchor_initial_start
                    caret.anchor_end = mouse_at
                    update = True
            elif mouse_at <= caret.anchor_initial_start:
                caret.rc = mouse_at
                if mouse_at != caret.anchor_start:
                    caret.anchor_start = mouse_at
                    caret.anchor_end = caret.anchor_initial_end
                    update = True

        if update:
            self.commit_change(flags)
        mode_log.debug("handle_select_motion: update: %s, flags: %s, anchors: initial=%s current=%s" % (update, flags, str((caret.anchor_initial_start, caret.anchor_initial_end)), str((caret.anchor_start, caret.anchor_end))))
        # mode_log.debug(f"motion after: {ch.carets}")

    def handle_select_end(self, evt, row, col, flags=None):
        if flags is None:
            flags = self.create_mouse_event_flags()
        self.mouse_drag_started = False
        self.select_extend_mode = False
        self.multi_select_mode = False
        self.caret_handler.collapse_overlapping()
        if wx.Platform == "__WXMSW__":
            # FIXME: MSW doesn't seem to refresh after a mouse release
            # outside of the window, so force it here to fill in the remaining
            # bits of the selection
            mode_log.debug("Extra refresh on handle_select_end for windows")
            self.refresh_view()
        self.commit_change(flags)
        mode_log.debug(("end after:", self.caret_handler.carets))

    def commit_change(self, flags):
        mode_log.debug(("commit before:", self.caret_handler.carets))
        self.mouse_mode.refresh_ranges(self.caret_handler)
        self.send_caret_event(flags)
        # self.caret_handler.sync_caret_event = flags
        # self.caret_handler.ensure_visible_event = flags
        # self.caret_handler.refresh_event = flags
        mode_log.debug(("commit after:", self.caret_handler.carets))

    def get_start_end_index_of_row(self, row):
        raise NotImplementedError

    def get_status_message_at_row_col(self, row, col):
        raise NotImplementedError

    def highlight_selected_ranges(self, caret_handler):
        ch = self.caret_handler
        ch.document.change_count += 1
        s = ch.segment
        s.clear_style_bits(selected=True)
        self.segment_viewer.highlight_selected_ranges_in_segment(ch.carets.selected_ranges, s)
        ch.calc_dependent_action_enabled_flags()

    ##### editing

    def handle_char_ordinary(self, evt):
        c = evt.GetKeyCode()
        print("ordinary char: {c}")
        if not self.is_editing_in_cell:
            print("handle_char_ordinary: not editing in cell")
            if self.verify_keycode_can_start_edit(c):
                self.start_editing(evt)
            else:
                evt.Skip()
        else:
            print("handle_char_ordinary: editing in cell")
            self.edit_source.EmulateKeyPress(evt)

    def verify_keycode_can_start_edit(self, c):
        return True

    def mouse_event_in_edit_cell(self, evt):
        r, c, _ = self.get_row_col_from_event(evt)
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
        ranges = self.get_selected_ranges_including_carets()
        cmd = SetRangeValueCommand(self.segment_viewer.segment, ranges, val, advance=True)
        self.segment_viewer.editor.process_command(cmd)

    def end_editing(self):
        if self.is_editing_in_cell:
            self.edit_source.Destroy()
            self.edit_source = None
            self.is_editing_in_cell = False
            self.SetFocus()

    def create_hidden_text_ctrl(self):
        c = GridCellTextCtrl(self, -1, 0, pos=(600,100), size=(400,24))
        return c
