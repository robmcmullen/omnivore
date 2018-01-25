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
from ..utils.wx.char_event_mixin import CharEventMixin

import logging
log = logging.getLogger(__name__)


class CaretHandler(HasTraits):
    """The pyface editor template for the omnivore framework
    
    The abstract methods 
    """

    # Caret index points to positions between bytes, so zero is before the
    # first byte and the max index is the number of bytes, which points to
    # after the last byte

    caret_index = Int(0)

    caret_history = Any

    # Anchor indexes behave like caret positions: they indicate positions
    # between bytes
    anchor_start_index = Int(0)

    anchor_initial_start_index = Int(0)

    anchor_initial_end_index = Int(0)

    anchor_end_index = Int(0)

    selected_ranges = List([])

    #### trait default values

    def _caret_history_default(self):
        return HistoryList()

    def _selected_ranges_default(self):
        return [(0, 0)]

    #### properties

    @property
    def has_selection(self):
        return bool(self.selected_ranges)

    #### command flag processors

    def ensure_visible(self, flags):
        """Make sure the current range of indexes is shown

        flags: DisplayFlags instance containing index_range that should
        be shown
        """
        pass

    def set_caret(self, index, refresh=True):
        max_index = self.document_length - 1
        if index < 0:
            index = 0
        elif index > max_index:
            index = max_index
        self.caret_index = index
        self.clear_selection()

        return index

    def update_caret_history(self):
        state = self.get_caret_state()
        last = self.caret_history.get_undo_command()
        if last is None or last != state:
            cmd = self.caret_history.get_redo_command()
            if cmd is None or cmd != state:
                self.caret_history.add_command(state)

    def get_caret_state(self):
        return self.caret_index

    def undo_caret_history(self):
        if not self.caret_history.can_redo():
            # at the end of the history list, the last item will be the current position, so skip it
            _ = self.caret_history.prev_command()
        cmd = self.caret_history.prev_command()
        if cmd is None:
            return
        self.restore_caret_state(cmd)

    def redo_caret_history(self):
        if not self.caret_history.can_undo():
            # at the start of the history list, the last item will be the current position, so skip it
            _ = self.caret_history.next_command()
        cmd = self.caret_history.next_command()
        if cmd is None:
            return
        self.restore_caret_state(cmd)

    def restore_caret_state(self, state):
        self.set_caret(state)

    def mark_index_range_changed(self, index_range):
        """Hook for subclasses to be informed when bytes within the specified
        index range have changed.
        """
        pass

    def clear_selection(self):
        self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = self.caret_index
        self.selected_ranges = [(self.caret_index, self.caret_index)]
        #self.highlight_selected_ranges(self)
        self.calc_action_enabled_flags()

    def process_caret_flags(self, flags, document):
        """Perform the UI updates given the StatusFlags or BatchFlags flags
        
        """
        visible_range = False
        refreshed = False

        if flags.caret_index is not None:
            if flags.keep_selection:
                self.caret_index = flags.caret_index
            else:
                self.caret_index = self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = flags.caret_index
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
                flags.index_visible = flags.caret_index if flags.caret_index is not None else self.anchor_start_index
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


class CaretEventMixin(CharEventMixin):
    def __init__(self, caret_handler):
        CharEventMixin.__init__(self)
        self.caret_handler = caret_handler

    def show_new_caret_position(self):
        pass


class SelectionHandler(object):
    """Range & selection routines that may be different depending on which
    viewer is active.
    """

    def select_all(self, caret_handler, refresh=True):
        """ Selects the entire document
        """
        caret_handler.anchor_start_index = caret_handler.anchor_initial_start_index = 0
        caret_handler.anchor_end_index = caret_handler.anchor_initial_end_index = caret_handler.document_length
        caret_handler.selected_ranges = [(caret_handler.anchor_start_index, caret_handler.anchor_end_index)]
        self.highlight_selected_ranges(caret_handler)
        caret_handler.calc_action_enabled_flags()

    def select_none(self, caret_handler, refresh=True):
        """ Clears any selection in the document
        """
        caret_handler.clear_selection()
        self.highlight_selected_ranges(caret_handler)

    def select_none_if_selection(self, caret_handler):
        if caret_handler.has_selection:
            self.select_none(caret_handler)

    def select_ranges(self, caret_handler, ranges, refresh=True):
        """ Selects the specified ranges
        """
        caret_handler.selected_ranges = ranges
        try:
            start, end = caret_handler.selected_ranges[-1]
        except IndexError:
            start, end = 0, 0
        caret_handler.anchor_start_index = caret_handler.anchor_initial_start_index = start
        caret_handler.anchor_end_index = caret_handler.anchor_initial_end_index = end
        self.highlight_selected_ranges(caret_handler)
        caret_handler.calc_action_enabled_flags()

    def select_invert(self, caret_handler, refresh=True):
        """ Selects the entire document
        """
        ranges = self.invert_selection_ranges(caret_handler, caret_handler.selected_ranges)
        self.select_ranges(caret_handler, ranges, refresh)

    def select_range(self, caret_handler, start, end, add=False, extend=False):
        """ Adjust the current selection to the new start and end indexes
        """
        if extend:
            caret_handler.selected_ranges[-1] = (start, end)
        elif add:
            caret_handler.selected_ranges.append((start, end))
        else:
            caret_handler.selected_ranges = [(start, end)]
        caret_handler.anchor_start_index = start
        caret_handler.anchor_end_index = end
        log.debug("selected ranges: %s" % str(caret_handler.selected_ranges))
        self.highlight_selected_ranges(caret_handler)
        caret_handler.calc_action_enabled_flags()

    def highlight_selected_ranges(self, caret_handler):
        raise NotImplementedError("highlight_selected_ranges must be implemented in subclass")

    def get_optimized_selected_ranges(self, caret_handler):
        """ Get the list of monotonically increasing, non-overlapping selected
        ranges
        """
        return collapse_overlapping_ranges(caret_handler.selected_ranges)

    def get_selected_ranges_and_indexes(self, caret_handler):
        opt = self.get_optimized_selected_ranges(caret_handler)
        return opt, ranges_to_indexes(opt)

    def invert_selection_ranges(self, caret_handler, ranges):
        return invert_ranges(ranges, caret_handler.document_length)
