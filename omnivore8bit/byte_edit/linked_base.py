# Standard library imports.
import sys
import os
import uuid

# Major package imports.
import wx
import numpy as np
import json

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, provides, on_trait_change, HasTraits, Undefined
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore.framework.editor import FrameworkEditor
from omnivore.framework.caret import CaretHandler
from omnivore.utils.command import DisplayFlags
from omnivore8bit.utils.segmentutil import SegmentData, DefaultSegment
from . import actions as ba

import logging
log = logging.getLogger(__name__)


class LinkedBase(CaretHandler):
    """Model for the state of a set of viewers. A ByteEditor can have an
    arbitrary number of LinkedBases, but all viewers that point to a common
    LinkedBase will all show the same data.

    A LinkedBase is tied to a Segment, and any data that can be applied
    segment-wide should also live here, e.g. the disassembly trace.

    Currently, a LinkedBase contains a single Machine, which specifies how to
    look at the data, like: CPU used for disassembly/assembly, available
    graphics and text modes, current colors and font. All views of the data
    using this LinkedBase will show the same Machine.

    In the future, each view will have its own Machine, because there's nothing
    in the Machine that could affect other viewers, so it should really be part
    of the view.
    """

    #### Traits

    # 

    obj = Instance(File)

    uuid = Str

    editor = Instance(FrameworkEditor)

    segment = Instance(DefaultSegment)

    segment_number = Int(0)

    last_caret_index = Int(0)

    last_anchor_start_index = Int(0)

    last_anchor_end_index = Int(0)

    has_origin = Bool(False)

    segment_view_params = Dict

    cached_preferences = Any(transient=True)

    #### Events

    recalc_event = Event

    update_trace = Event

    key_pressed = Event(KeyPressedEvent)

    #### Class attributes (not traits)

    rect_select = False

    #### Default traits

    def _segment_default(self):
        rawdata = SegmentData([])
        return DefaultSegment(rawdata)

    def _uuid_default(self):
        return str(uuid.uuid4())

    def _cached_preferences_default(self):
        return self.task.preferences

    def _segment_view_params_default(self):
        return {}

    #### Properties

    @property
    def section_name(self):
        return str(self.segment)

    @property
    def task(self):
        return self.editor.task

    @property
    def window(self):
        return self.editor.window

    @property
    def document(self):
        return self.editor.document

    @property
    def document_length(self):
        return len(self.segment)

    #### Convenience functions

    def __str__(self):
        return "LinkedBase: seg=%s" % self.segment

    def from_metadata_dict(self, e):
        log.debug("metadata: %s" % str(e))
        if 'uuid' in e:
            self.uuid = e['uuid']
        if 'diff highlight' in e:
            self.diff_highlight = bool(e['diff highlight'])
        if 'segment view params' in e:
            self.segment_view_params = e['segment view params']
        if 'segment number' in e:
            self.segment_number = e['segment number']
        else:
            self.segment_number = self.editor.initial_segment

    def to_metadata_dict(self, mdict, document):
        if document == self.document:
            mdict['uuid'] = self.uuid
            # If we're saving the document currently displayed, save the
            # display parameters too.
            mdict["segment view params"] = dict(self.segment_view_params)  # shallow copy, but only need to get rid of Traits dict wrapper
            mdict['segment number'] = self.segment_number

    def save_segment_view_params(self, segment):
        d = {
            'carets': self.calc_caret_state(),
            'selected_ranges': list(self.selected_ranges),
        }
        for viewer in self.editor.viewers:
            if viewer.linked_base == self:
                try:
                    d[viewer.uuid] = viewer.control.calc_view_params()
                except AttributeError:
                    pass
        print("segment view params: %s: %s" % (segment.name, str(d)))
        self.segment_view_params[segment.uuid] = d

    def restore_segment_view_params(self, segment):
        try:
            d = self.segment_view_params[segment.uuid]
        except KeyError:
            log.debug("no view params for %s" % segment.uuid)
            self.clear_carets()
            return
        log.debug("restoring view params for %s" % segment.uuid)
        self.restore_caret_state(d['carets'])
        self.selected_ranges = d['selected_ranges']
        for viewer in self.editor.viewers:
            if viewer.linked_base == self:
                try:
                    params = d[viewer.uuid]
                except KeyError:
                    continue
                try:
                    viewer.control.restore_view_params(params)
                except AttributeError:
                    continue

    def find_segment_parser(self, parsers, segment_name=None):
        self.document.parse_segments(parsers)
        self.find_segment(segment_name)

    def find_first_valid_segment_index(self):
        return 0

    def find_segment(self, segment, refresh=False):
        if segment is not None:
            index = self.document.find_segment_index(segment)
        elif self.segment_number == 0:
            index = self.find_first_valid_segment_index()
        else:
            index = self.segment_number
        log.debug("find_segment: changing from %d to %d, input=%s" % (self.segment_number, index, segment))
        if index < 0:
            index = 0
        self.segment_parser = self.document.segment_parser
        if refresh:
            self.view_segment_number(index)
        else:
            self.segment_number = index
            self.segment_parser = self.document.segment_parser
            self.segment = self.document.segments[index]
            self.clear_selection()
            self.force_data_model_update()
            self.task.segments_changed = self.document.segments
            self.task.segment_selected = self.segment_number

    def set_segment_parser(self, parser):
        self.find_segment_parser([parser])
        self.rebuild_ui()

    def view_segment_number(self, number):
        log.debug("view_segment_number: changing to %d from %d" % (number, self.segment_number))
        doc = self.document
        num = number if number < len(doc.segments) else len(doc.segments) - 1
        if num != self.segment_number:
            old_segment = self.segment
            if old_segment is not None:
                self.save_segment_view_params(old_segment)
            self.segment = doc.segments[num]
            self.adjust_selection(old_segment)
            self.segment_number = num

            self.force_data_model_update()

            #self.show_trace()
            # if self.segment_list is not None:
            #     self.segment_list.SetSelection(self.segment_number)
            # else:
            #     self.sidebar.refresh_active()
            self.editor.sidebar.refresh_active()
            self.task.segment_selected = self.segment_number
            #self.task.status_bar.message = "Switched to segment %s" % str(self.segment)
            self.task.update_window_title()

    def force_data_model_update(self):
        flags = DisplayFlags()
        flags.data_model_changed = True
        self.process_flags(flags)

    def force_refresh(self):
        flags = DisplayFlags()
        flags.byte_values_changed = True
        self.process_flags(flags)

    def save_segment(self, saver, uri):
        try:
            bytes = saver.encode_data(self.segment, self)
            saver = lambda a,b: bytes
            self.document.save_to_uri(uri, self, saver, save_metadata=False)
        except Exception, e:
            log.error("%s: %s" % (uri, str(e)))
            #self.window.error("Error trying to save:\n\n%s\n\n%s" % (uri, str(e)), "File Save Error")
            raise

    #### command flag processors

    def process_flags(self, flags):
        self.editor.process_flags(flags)

    def rebuild_ui(self):
        self.segment = self.document.segments[self.segment_number]
        self.reconfigure_panes()
        self.update_segments_ui()

    def calc_action_enabled_flags(self):
        e = self.editor
        e.can_copy = len(self.selected_ranges) > 1 or (bool(self.selected_ranges) and (self.selected_ranges[0][0] != self.selected_ranges[0][1]))
        self.calc_dependent_action_enabled_flags()

    def calc_dependent_action_enabled_flags(self):
        e = self.editor
        e.can_copy_baseline = e.can_copy and e.baseline_present

    #### CaretHandler overrides

    def check_document_change(self):
        if self.last_caret_index != self.carets.current.index or self.last_anchor_start_index != self.anchor_start_index or self.last_anchor_end_index != self.anchor_end_index:
            self.document.change_count += 1
            self.update_caret_history()

    def calc_caret_history(self):
        return self.segment, CaretHandler.calc_caret_state(self)

    def restore_caret_history(self, state):
        segment, carets = state
        number = self.document.find_segment_index(segment)
        if number < 0:
            log.error("tried to restore caret to a deleted segment? %s" % segment)
        else:
            if number != self.segment_number:
                self.view_segment_number(number)
            CaretHandler.restore_caret_state(self, carets)
        log.debug(self.caret_history)

    #### selection utilities

    def adjust_selection(self, old_segment):
        """Adjust the selection of the current segment so that it is limited to the
        bounds of the new segment.
        
        If the current selection is entirely out of bounds of the new segment,
        all the selection indexes will be set to zero.
        """
        # find byte index of view into master array
        g = self.document.container_segment
        s = self.segment
        global_offset = g.get_raw_index(0)
        new_offset = s.get_raw_index(0)
        old_offset = old_segment.get_raw_index(0)

        self.restore_segment_view_params(s)
        if False:  # select same bytes in new segment, if possible
            self.selected_ranges = s.get_style_ranges(selected=True)
            if self.selected_ranges:
                # Arbitrarily puth the anchor on the last selected range
                last = self.selected_ranges[-1]
                self.anchor_initial_start_index = self.anchor_start_index = last[0]
                self.anchor_initial_end_index = self.anchor_end_index = last[1]
            g.clear_style_bits(selected=True)
        self.document.change_count += 1

    def convert_ranges(self, from_style, to_style):
        s = self.segment
        ranges = s.get_style_ranges(**from_style)
        s.clear_style_bits(**from_style)
        s.clear_style_bits(**to_style)
        s.set_style_ranges(ranges, **to_style)
        self.selected_ranges = s.get_style_ranges(selected=True)
        self.document.change_count += 1

    def get_selected_index_metadata(self, indexes):
        """Return serializable string containing style information"""
        style = self.segment.get_style_at_indexes(indexes)
        r_orig = self.segment.get_style_ranges(comment=True)
        comments = self.segment.get_comments_at_indexes(indexes)
        log.debug("after get_comments_at_indexes: %s" % str(comments))
        metadata = [style.tolist(), comments[0].tolist(), comments[1]]
        j = json.dumps(metadata)
        return j

    def restore_selected_index_metadata(self, metastr):
        metadata = json.loads(metastr)
        style = np.asarray(metadata[0], dtype=np.uint8)
        where_comments = np.asarray(metadata[1], dtype=np.int32)
        return style, where_comments, metadata[2]

    def get_segments_from_selection(self, size=-1):
        s = self.segment
        segments = []

        # Get the selected ranges directly from the segment style data, because
        # the individual range entries in self.selected_ranges can be out of
        # order or overlapping
        ranges = s.get_style_ranges(selected=True)
        if len(ranges) == 1:
            seg_start, seg_end = ranges[0]
            if size < 0:
                size = seg_end - seg_start
            for start in range(seg_start, seg_end, size):
                end = min(seg_end, start + size)
                segment = DefaultSegment(s.rawdata[start:end], s.start_addr + start)
                segments.append(segment)
        elif len(ranges) > 1:
            # If there are multiple selections, use an indexed segment
            indexes = []
            for start, end in ranges:
                indexes.extend(range(start, end))
            if size < 0:
                size = len(indexes)
            for i in range(0, len(indexes), size):
                raw = s.rawdata.get_indexed(indexes[i:i + size])
                segment = DefaultSegment(raw, s.start_addr + indexes[i])
                segments.append(segment)
        return segments

    def get_selected_status_message(self):
        if not self.selected_ranges:
            return ""
        if len(self.selected_ranges) == 1:
            r = self.selected_ranges
            first = r[0][0]
            last = r[0][1]
            num = abs(last - first)
            if num == 1: # python style, 4:5 indicates a single byte
                return "[1 byte selected %s]" % self.editor.get_label_of_ranges(r)
            elif num > 0:
                return "[%d bytes selected %s]" % (num, self.editor.get_label_of_ranges(r))
        else:
            return "[%d ranges selected]" % (len(self.selected_ranges))

    def show_status_message(self, msg):
        s = self.get_selected_status_message()
        if s:
            msg = "%s %s" % (msg, s)
        self.editor.task.status_bar.message = msg

    #### segment utilities

    def add_user_segment(self, segment, update=True):
        self.document.add_user_segment(segment)
        self.added_segment(segment, update)

    def added_segment(self, segment, update=True):
        if update:
            self.update_segments_ui()
            if self.segment_list is not None:
                self.segment_list.ensure_visible(segment)
        self.metadata_dirty = True

    def delete_user_segment(self, segment):
        self.document.delete_user_segment(segment)
        self.view_segment_number(self.segment_number)
        self.update_segments_ui()
        self.metadata_dirty = True

    def find_in_user_segment(self, base_index):
        for s in self.document.user_segments:
            try:
                index = s.get_index_from_base_index(base_index)
                return s, index
            except IndexError:
                continue
        for s in self.document.segment_parser.segments[1:]:
            try:
                index = s.get_index_from_base_index(base_index)
                return s, index
            except IndexError:
                continue
        return None, None

    def get_goto_action_in_segment(self, addr_dest):
        if addr_dest >= 0:
            segment_start = self.segment.start_addr
            segment_num = -1
            addr_index = addr_dest - segment_start
            segments = self.document.find_segments_in_range(addr_dest)
            if addr_dest < segment_start or addr_dest > segment_start + len(self.segment):
                # segment_num, segment_dest, addr_index = self.document.find_segment_in_range(addr_dest)
                if not segments:
                    msg = "Address $%04x not in any segment" % addr_dest
                    addr_dest = -1
                else:
                    # Don't chose a default segment, just show the sub menu
                    msg = None
            else:
                msg = "Go to $%04x" % addr_dest
            if msg:
                action = ba.GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.editor.task, active_editor=self)
            else:
                action = None
        else:
            msg = "No address to jump to"
            action = ba.GotoIndexAction(name=msg, enabled=False, task=self.editor.task)
        return action

    def get_goto_actions_other_segments(self, addr_dest):
        """Add sub-menu to popup list for segments that have the same address
        """
        goto_actions = []
        segments = self.document.find_segments_in_range(addr_dest)
        if len(segments) > 0:
            other_segment_actions = ["Go to $%04x in Other Segment..." % addr_dest]
            for segment_num, segment_dest, addr_index in segments:
                if segment_dest == self.segment:
                    continue
                msg = str(segment_dest)
                action = ba.GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.editor.task, active_editor=self)
                other_segment_actions.append(action)
            if len(other_segment_actions) > 1:
                # found another segment other than itself
                goto_actions.append(other_segment_actions)
        return goto_actions

    def get_goto_actions_same_byte(self, index):
        """Add sub-menu to popup list for for segments that have the same raw
        index (index into the base array) as the index into the current segment
        """
        goto_actions = []
        raw_index = self.segment.get_raw_index(index)
        segments = self.document.find_segments_with_raw_index(raw_index)
        if len(segments) > 0:
            other_segment_actions = ["Go to Same Byte in Other Segment..."]
            for segment_num, segment_dest, addr_index in segments:
                if segment_dest == self.segment:
                    continue
                msg = str(segment_dest)
                action = ba.GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.editor.task, active_editor=self)
                other_segment_actions.append(action)
            if len(other_segment_actions) > 1:
                # found another segment other than itself
                goto_actions.append(other_segment_actions)
        return goto_actions

    def popup_context_menu_from_actions(self, *args, **kwargs):
        self.editor.popup_context_menu_from_actions(*args, **kwargs)

    def index_clicked(self, index, bit, from_control, refresh_from=True):
        log.debug("index_clicked: %s from %s at %d, %s" % (refresh_from, from_control, index, bit))
        self.carets.current.index = index
        self.check_document_change()
        if refresh_from:
            from_control = None
        self.update_caret = (from_control, index, bit)
        self.calc_action_enabled_flags()
