import os

# Major package imports.
import numpy as np
from fs.opener import opener
import wx
import fs

# Enthought library imports.
from traits.api import on_trait_change, HasTraits, Any, Bool, Int, Unicode, Property, Dict, List, Str, Undefined, Event

from omnivore.utils.command import HistoryList
from omnivore.utils.sortutil import collapse_overlapping_ranges, invert_ranges, ranges_to_indexes

import logging
log = logging.getLogger(__name__)


class Caret(object):
    """Opaque class representing a caret's index and additional metadata
    """
    def __init__(self, index=0, state=None):
        self.index = index
        if state is not None:
            self.restore(state)

    def __bool__(self):
        return self.index is not None

    __nonzero__=__bool__

    def __eq__(self, other):
        if not hasattr(self, 'index'):
            log.error("not a Caret object")
            return False
        log.debug("comparing caret indexes: %d %d" % (self.index, other.index))
        return self.index == other.index

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "Caret(%d)" % self.index

    def serialize(self):
        return self.index

    def restore(self, state):
        self.index = state

    def set(self, index):
        self.index = index

    def add_delta(self, delta):
        self.index += delta

    def apply_function(self, func):
        self.index = func(self.index)

    def copy(self):
        return Caret(self.index)


class CaretList(list):
    def __init__(self, index, *args, **kwargs):
        list(self, *args, **kwargs)
        if isinstance(index, list):
            self.new_carets(index)
        elif index is not None:
            self.new_caret(index)

    def __bool__(self):
        return len(self) >= 1

    __nonzero__=__bool__

    def __eq__(self, other):
        if len(self) != len(other):
            #print("list size different! ", len(self), len(other))
            return False
        for c1, c2 in zip(self, other):
            #print("comparing ", c1, c2)
            if c1 != c2:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def current(self):
        return self[-1]  # The last one added is the most recent

    def new_caret(self, index):
        caret = Caret(index)
        self.append(caret)
        return caret

    def new_carets(self, caret_state):
        for s in caret_state:
            caret = Caret(state=s)
            self.append(caret)

    def get_state(self):
        return [caret.serialize() for caret in self]

    def copy(self):
        c = CaretList(None)
        for caret in self:
            c.append(caret.copy())
        return c

    def add_old_carets(self, old_state):
        """Prefix the existing current caret with the list of old carets.

        This throws away all but the current caret in the self object, but
        hopefully this is what's intended as the current caret will have been
        moved by the compactgrid before hitting the process_caret_flags.
        """
        old_carets = CaretList(old_state)
        self[0:-1] = old_carets[:]
        log.debug("old_carets: %s added: %s" % (str(old_carets), str(self)))

    def remove_old_carets(self):
        """Remove everything but the current caret"""
        self[0:-1] = []
        log.debug("removed all but %s" % (str(self)))

    def validate(self, caret_handler):
        found = set()
        validated = CaretList(None)
        for caret in self:
            index = caret_handler.validate_caret_position(caret.index)
            if index in found:
                continue
            found.add(index)
            caret.set(index)
            validated.append(caret)
        if found:
            validated
        return validated


class CaretHandler(HasTraits):
    """The pyface editor template for the omnivore framework
    
    The abstract methods 
    """

    # Caret index points to positions between bytes, so zero is before the
    # first byte and the max index is the number of bytes, which points to
    # after the last byte

    carets = Any

    caret_history = Any

    # Anchor indexes behave like caret positions: they indicate positions
    # between bytes
    anchor_start_index = Int(0)

    anchor_initial_start_index = Int(0)

    anchor_initial_end_index = Int(0)

    anchor_end_index = Int(0)

    selected_ranges = List([])

    ensure_visible_event = Event

    sync_caret_event = Event

    refresh_event = Event

    #### trait default values

    def _carets_default(self):
        return CaretList(0)

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
        self.carets = CaretList(index)
        self.validate_carets()
        return self.carets.current

    def clear_carets(self):
        self.set_caret(0)

    def move_carets(self, delta):
        for caret in self.carets:
            caret.add_delta(delta)
        self.validate_carets()

    def move_carets_to(self, index):
        self.set_caret(index)

    def move_current_caret_to(self, index):
        index = self.validate_caret_position(index)
        self.carets.current.set(index)

    def move_carets_process_function(self, func):
        for caret in self.carets:
            caret.apply_function(func)
        self.validate_carets()

    def validate_carets(self):
        """Confirms the index position of all carets and collapses multiple
        carets that have the same index into a single caret
        """
        self.carets = self.carets.validate(self)

    def validate_caret_position(self, index):
        max_index = self.document_length - 1
        if index < 0:
            index = 0
        elif index > max_index:
            index = max_index
        return index

    def iter_caret_indexes(self):
        for caret in self.carets:
            yield caret.index

    def carets_as_ranges(self):
        return [(c.index, c.index + 1) for c in self.carets]

    def update_caret_history(self):
        state = self.carets.get_state()
        last = self.caret_history.get_undo_command()
        if last is None or last != state:
            cmd = self.caret_history.get_redo_command()
            if cmd is None or cmd != state:
                self.caret_history.add_command(state)

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

    def calc_caret_state(self):
        return self.carets.get_state()

    def restore_caret_state(self, state):
        carets = CaretList(state)
        self.carets = carets

    def mark_index_range_changed(self, index_range):
        """Hook for subclasses to be informed when bytes within the specified
        index range have changed.
        """
        pass

    def set_anchors(self, start, end):
        self.anchor_start_index = self.anchor_initial_start_index = start
        self.anchor_end_index = self.anchor_initial_end_index = end
        log.debug("set anchors: initial to: %d,%d" % (start, end))

    def clear_selection(self):
        index = self.carets.current.index
        self.anchor_start_index = self.anchor_initial_start_index = self.anchor_end_index = self.anchor_initial_end_index = index
        log.debug("clear_selection: initial to: %d,%d" % (index, index))
        # if index > 0:
        #     import pdb; pdb.set_trace()
        self.selected_ranges = []
        #self.highlight_selected_ranges(self)
        self.calc_action_enabled_flags()

    def process_caret_flags(self, flags, document):
        """Perform the UI updates given the StatusFlags or BatchFlags flags
        
        """
        visible_range = False
        caret_moved = False
        log.debug("processing caret flags: %s" % str(flags))

        if flags.old_carets is not None:
            if flags.add_caret:
                self.carets.add_old_carets(flags.old_carets)
                caret_moved = True
                log.debug("caret added! before: %s, after: %s" % (flags.old_carets, self.carets))
            elif flags.force_single_caret:
                self.carets.remove_old_carets()
                caret_moved = True
            else:
                self.validate_carets()
                caret_state = self.carets.get_state()
                caret_moved = caret_state != flags.old_carets
                log.debug("caret moved! old_carets: %s, new carets: %s" % (flags.old_carets, caret_state))
            if caret_moved:
                if not flags.keep_selection:
                    index = self.carets.current.index
                    self.set_anchors(index, index)
                visible_range = True
                self.sync_caret_event = flags

        if flags.index_range is not None:
            if flags.select_range:
                self.set_anchors(flags.index_range[0], flags.index_range[1])
                document.change_count += 1
            visible_range = True

        if visible_range:
            # Only update the range on the current editor, not other views
            # which are allowed to remain where they are
            if flags.index_visible is None:
                flags.index_visible = self.carets.current.index if caret_moved else self.anchor_start_index
            self.ensure_visible_event = flags

            flags.refresh_needed = True

        if flags.viewport_origin is not None:
            flags.source_control.move_viewport_origin(flags.viewport_origin)
            flags.skip_source_control_refresh = True
            flags.refresh_needed = True


    def calc_action_enabled_flags(self):
        pass

    @property
    def selection_handler(self):
        raise NotImplementedError("Subclass needs to define a SelectionHandler")


class SelectionHandler(object):
    """Range & selection routines that may be different depending on which
    viewer is active.
    """

    def select_all(self, caret_handler, refresh=True):
        """ Selects the entire document
        """
        caret_handler.set_anchors(0, caret_handler.document_length)
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

    def get_selected_ranges(self, caret_handler):
        ranges = caret_handler.carets_as_ranges()
        ranges.extend(caret_handler.selected_ranges)
        return collapse_overlapping_ranges(ranges)

    def get_selected_ranges_and_indexes(self, caret_handler):
        opt = self.get_selected_ranges(caret_handler)
        return opt, ranges_to_indexes(opt)

    def invert_selection_ranges(self, caret_handler, ranges):
        return invert_ranges(ranges, caret_handler.document_length)
