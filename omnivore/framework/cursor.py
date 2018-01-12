import os

# Major package imports.
import numpy as np
from fs.opener import opener
import wx
import fs

# Enthought library imports.
from traits.api import on_trait_change, HasTraits, Any, Bool, Int, Unicode, Property, Dict, List, Str, Undefined

from omnivore.utils.command import HistoryList, StatusFlags
from omnivore.utils.sortutil import collapse_overlapping_ranges, invert_ranges, ranges_to_indexes

import logging
log = logging.getLogger(__name__)


class CursorHandler(HasTraits):
    """The pyface editor template for the omnivore framework
    
    The abstract methods 
    """

    # Cursor index points to positions between bytes, so zero is before the
    # first byte and the max index is the number of bytes, which points to
    # after the last byte

    cursor_index = Int(0)

    cursor_history = Any

    # Anchor indexes behave like cursor positions: they indicate positions
    # between bytes
    anchor_start_index = Int(0)

    anchor_initial_start_index = Int(0)

    anchor_initial_end_index = Int(0)

    anchor_end_index = Int(0)

    selected_ranges = List([])

    #### trait default values

    def _cursor_history_default(self):
        return HistoryList()

    def _selected_ranges_default(self):
        return [(0, 0)]

    #### command flag processors

    def ensure_visible(self, flags):
        """Make sure the current range of indexes is shown

        flags: DisplayFlags instance containing index_range that should
        be shown
        """
        pass

    def set_cursor(self, index, refresh=True):
        max_index = self.document_length - 1
        if index < 0:
            index = 0
        elif index > max_index:
            index = max_index
        self.cursor_index = index
        self.select_none(False)

        return index

    def update_cursor_history(self):
        state = self.get_cursor_state()
        last = self.cursor_history.get_undo_command()
        if last is None or last != state:
            cmd = self.cursor_history.get_redo_command()
            if cmd is None or cmd != state:
                self.cursor_history.add_command(state)

    def get_cursor_state(self):
        return self.cursor_index

    def undo_cursor_history(self):
        if not self.cursor_history.can_redo():
            # at the end of the history list, the last item will be the current position, so skip it
            _ = self.cursor_history.prev_command()
        cmd = self.cursor_history.prev_command()
        if cmd is None:
            return
        self.restore_cursor_state(cmd)

    def redo_cursor_history(self):
        if not self.cursor_history.can_undo():
            # at the start of the history list, the last item will be the current position, so skip it
            _ = self.cursor_history.next_command()
        cmd = self.cursor_history.next_command()
        if cmd is None:
            return
        self.restore_cursor_state(cmd)

    def restore_cursor_state(self, state):
        self.set_cursor(state)

    def mark_index_range_changed(self, index_range):
        """Hook for subclasses to be informed when bytes within the specified
        index range have changed.
        """
        pass

    def clear_selection(self):
        self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = self.cursor_index
        self.selected_ranges = [(self.cursor_index, self.cursor_index)]
        #self.highlight_selected_ranges(self)
        self.calc_action_enabled_flags()

    def process_cursor_flags(self, flags, document):
        """Perform the UI updates given the StatusFlags or BatchFlags flags
        
        """
        visible_range = False
        refreshed = False

        if flags.cursor_index is not None:
            if flags.keep_selection:
                self.cursor_index = flags.cursor_index
            else:
                self.cursor_index = self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = flags.cursor_index
            visible_range = True

        if flags.index_range is not None:
            if flags.select_range:
                self.anchor_start_index = self.anchor_initial_start_index = flags.index_range[0]
                self.anchor_end_index = self.anchor_initial_end_index = flags.index_range[1]
                document.change_count += 1
            visible_range = True

        if visible_range:
            # Only update the range on the current editor, not other views
            # which are allowed to remain where they are
            if flags.index_visible is None:
                flags.index_visible = flags.cursor_index if flags.cursor_index is not None else self.anchor_start_index
            self.ensure_visible(flags)

            # Prevent a double refresh since ensure_visible does a refresh as a
            # side effect.
            log.debug("NOTE: turned off do_refresh to prevent double refresh")
            refreshed = True

        return refreshed

    def calc_action_enabled_flags(self):
        pass

    @property
    def selection_handler(self):
        raise NotImplementedError("Subclass needs to define a SelectionHandler")


class SelectionHandler(object):
    """Range & selection routines that may be different depending on which
    viewer is active.
    """

    def select_all(self, cursor_handler, refresh=True):
        """ Selects the entire document
        """
        cursor_handler.anchor_start_index = cursor_handler.anchor_initial_start_index = 0
        cursor_handler.anchor_end_index = cursor_handler.anchor_initial_end_index = cursor_handler.document_length
        cursor_handler.selected_ranges = [(cursor_handler.anchor_start_index, cursor_handler.anchor_end_index)]
        self.highlight_selected_ranges(cursor_handler)
        cursor_handler.calc_action_enabled_flags()

    def select_none(self, cursor_handler, refresh=True):
        """ Clears any selection in the document
        """
        cursor_handler.clear_selection()
        self.highlight_selected_ranges(cursor_handler)

    def select_none_if_selection(self, cursor_handler):
        if cursor_handler.can_copy:
            self.select_none(cursor_handler)

    def select_ranges(self, cursor_handler, ranges, refresh=True):
        """ Selects the specified ranges
        """
        cursor_handler.selected_ranges = ranges
        try:
            start, end = cursor_handler.selected_ranges[-1]
        except IndexError:
            start, end = 0, 0
        cursor_handler.anchor_start_index = cursor_handler.anchor_initial_start_index = start
        cursor_handler.anchor_end_index = cursor_handler.anchor_initial_end_index = end
        self.highlight_selected_ranges(cursor_handler)
        cursor_handler.calc_action_enabled_flags()

    def select_invert(self, cursor_handler, refresh=True):
        """ Selects the entire document
        """
        ranges = self.invert_selection_ranges(cursor_handler, cursor_handler.selected_ranges)
        self.select_ranges(cursor_handler, ranges, refresh)

    def select_range(self, cursor_handler, start, end, add=False, extend=False):
        """ Adjust the current selection to the new start and end indexes
        """
        if extend:
            cursor_handler.selected_ranges[-1] = (start, end)
        elif add:
            cursor_handler.selected_ranges.append((start, end))
        else:
            cursor_handler.selected_ranges = [(start, end)]
        cursor_handler.anchor_start_index = start
        cursor_handler.anchor_end_index = end
        log.debug("selected ranges: %s" % str(cursor_handler.selected_ranges))
        self.highlight_selected_ranges(cursor_handler)
        cursor_handler.calc_action_enabled_flags()

    def highlight_selected_ranges(self, cursor_handler):
        raise NotImplementedError("highlight_selected_ranges must be implemented in subclass")

    def get_optimized_selected_ranges(self, cursor_handler):
        """ Get the list of monotonically increasing, non-overlapping selected
        ranges
        """
        return collapse_overlapping_ranges(cursor_handler.selected_ranges)

    def get_selected_ranges_and_indexes(self, cursor_handler):
        opt = self.get_optimized_selected_ranges(cursor_handler)
        return opt, ranges_to_indexes(opt)

    def invert_selection_ranges(self, cursor_handler, ranges):
        return invert_ranges(ranges, cursor_handler.document_length)
