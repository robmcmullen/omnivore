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

    #### range selection

    def select_all(self, refresh=True):
        """ Selects the entire document
        """
        self.anchor_start_index = self.anchor_initial_start_index = 0
        self.anchor_end_index = self.anchor_initial_end_index = self.document_length
        self.selected_ranges = [(self.anchor_start_index, self.anchor_end_index)]
        self.highlight_selected_ranges()
        self.calc_action_enabled_flags()

    def select_none(self, refresh=True):
        """ Clears any selection in the document
        """
        self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = self.cursor_index
        self.selected_ranges = [(self.cursor_index, self.cursor_index)]
        self.highlight_selected_ranges()
        self.calc_action_enabled_flags()

    def select_none_if_selection(self):
        if self.can_copy:
            self.select_none()

    def select_ranges(self, ranges, refresh=True):
        """ Selects the specified ranges
        """
        self.selected_ranges = ranges
        try:
            start, end = self.selected_ranges[-1]
        except IndexError:
            start, end = 0, 0
        self.anchor_start_index = self.anchor_initial_start_index = start
        self.anchor_end_index = self.anchor_initial_end_index = end
        self.highlight_selected_ranges()
        self.calc_action_enabled_flags()

    def select_invert(self, refresh=True):
        """ Selects the entire document
        """
        ranges = self.invert_selection_ranges(self.selected_ranges)
        self.select_ranges(ranges, refresh)

    def select_range(self, start, end, add=False, extend=False):
        """ Adjust the current selection to the new start and end indexes
        """
        if extend:
            self.selected_ranges[-1] = (start, end)
        elif add:
            self.selected_ranges.append((start, end))
        else:
            self.selected_ranges = [(start, end)]
        self.anchor_start_index = start
        self.anchor_end_index = end
        log.debug("selected ranges: %s" % str(self.selected_ranges))
        self.highlight_selected_ranges()
        self.calc_action_enabled_flags()

    def highlight_selected_ranges(self):
        pass

    def get_optimized_selected_ranges(self):
        """ Get the list of monotonically increasing, non-overlapping selected
        ranges
        """
        return collapse_overlapping_ranges(self.selected_ranges)

    def get_selected_ranges_and_indexes(self):
        opt = self.get_optimized_selected_ranges()
        return opt, ranges_to_indexes(opt)

    def invert_selection_ranges(self, ranges):
        return invert_ranges(ranges, self.document_length)

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