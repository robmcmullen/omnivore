# Standard library imports.
import sys
import os
import uuid

# Major package imports.
import wx
import numpy as np
import json

from sawx.utils.command import DisplayFlags
from sawx.events import EventHandler

from ..utils.segmentutil import SegmentData, DefaultSegment
from ..jumpman import playfield as jp

import logging
log = logging.getLogger(__name__)


class LinkedBase:
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
    rect_select = False

    def __init__(self, editor):
        self.uuid = str(uuid.uuid4())
        self.editor = editor

        rawdata = SegmentData([])
        self.segment = DefaultSegment(rawdata)
        self.segment_number = 0
        self.has_origin = False
        self.segment_view_params = {}

        self.ensure_visible_event = EventHandler(self)
        self.sync_caret_to_index_event = EventHandler(self)
        self.refresh_event = EventHandler(self)
        self.recalc_event = EventHandler(self)
        self.update_trace = EventHandler(self)
        self.key_pressed = EventHandler(self)
        self.segment_selected_event = EventHandler(self)

        ##### Jumpman-specific stuff
        self.jumpman_trigger_selected_event = EventHandler(self)
        self.jumpman_playfield_model = jp.JumpmanPlayfieldModel(self)

    #### Properties

    @property
    def section_name(self):
        return str(self.segment)

    @property
    def window(self):
        return self.editor.window

    @property
    def document(self):
        return self.editor.document

    @property
    def document_length(self):
        return len(self.segment)

    @property
    def emulator(self):
        return self.editor.emulator

    @property
    def cached_preferences(self):
        return self.editor.preferences

    ##### Cleanup

    def prepare_for_destroy(self):
        self.editor = None

    #### Convenience functions

    def __str__(self):
        return f"LinkedBase {hex(id(self))}: seg={self.segment}"

    def restore_session(self, e):
        log.debug("metadata: %s" % str(e))
        if 'uuid' in e:
            self.uuid = e['uuid']
        if 'diff highlight' in e:
            self.diff_highlight = bool(e['diff highlight'])
        if 'segment view params' in e:
            self.segment_view_params = e['segment view params']
        #self.editor.document.find_initial_visible_segment(self, e.get('segment number', 0))

    def serialize_session(self, mdict):
        # make sure to save latest values of currently viewed segment
        self.save_segment_view_params(self.segment)

        mdict['uuid'] = self.uuid
        mdict['segment view params'] = self.segment_view_params
        mdict['segment number'] = self.segment_number

    def save_segment_view_params(self, segment):
        d = {}
        for viewer in self.editor.viewers:
            if viewer.linked_base == self:
                try:
                    d[viewer.uuid] = viewer.control.calc_view_params()
                except AttributeError:
                    pass
        log.debug("segment view params: %s: %s" % (segment.name, str(d)))
        self.segment_view_params[segment.uuid] = d

    def restore_segment_view_params(self, segment):
        try:
            d = self.segment_view_params[segment.uuid]
        except KeyError:
            log.debug("no view params for %s" % segment.uuid)
            d = {}
        else:
            log.debug("restoring view params for segment %s (%s): %s" % (segment.name, segment.uuid, str(d)))
        for viewer in self.editor.viewers:
            if viewer.linked_base == self:
                try:
                    params = d[viewer.uuid]
                except KeyError:
                    viewer.use_default_view_params()
                    continue
                try:
                    log.debug(" restoring view of %s (%s): %s" % (viewer.window_title, viewer.uuid, str(params)))
                    viewer.restore_view_params(params)
                except AttributeError:
                    continue

    def find_segment_parser(self, parsers, segment_name=None):
        self.document.parse_segments(parsers)
        self.find_segment(segment_name)

    def find_first_valid_segment_index(self):
        return 0

    def find_segment(self, segment, refresh=False, data_model_changed=True):
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
            data_model_changed = False
        else:
            self.segment_number = index
            self.segment_parser = self.document.segment_parser
            self.segment = self.document.segments[index]

        if data_model_changed:
            self.force_data_model_update()
            self.restore_segment_view_params(self.segment)
            self.task.segments_changed = self.document.segments
            self.segment_selected_event(self.segment_number)

    def set_segment_parser(self, parser):
        self.find_segment_parser([parser])
        self.rebuild_ui()

    def view_segment_number(self, number):
        log.debug("view_segment_number: changing to %d from %d" % (number, self.segment_number))
        doc = self.document
        num = number if number < len(doc.segments) else len(doc.segments) - 1
        if num != self.segment_number or len(self.segment) == 0:
            old_segment = self.segment
            if old_segment is not None:
                self.save_segment_view_params(old_segment)
            self.segment = doc.segments[num]
            self.segment_number = num
            self.recalc_event(True)
            self.adjust_selection(old_segment)

            #self.show_trace()
            self.segment_selected_event(self.segment_number)
            #self.task.status_bar.message = "Switched to segment %s" % str(self.segment)
            #self.task.update_window_title()
        log.debug(f"view_segment_number: changed to {self.segment_number}")

    def force_refresh(self):
        flags = DisplayFlags()
        flags.byte_values_changed = True
        self.process_flags(flags)

    #### command flag processors

    def process_flags(self, flags):
        self.editor.process_flags(flags)

    def rebuild_ui(self):
        self.segment = self.document.segments[self.segment_number]
        self.reconfigure_panes()
        self.update_segments_ui()

    # #### CaretHandler overrides

    # def calc_caret_history(self):
    #     return self.segment, CaretHandler.calc_caret_state(self)

    # def restore_caret_history(self, state):
    #     segment, carets = state
    #     number = self.document.find_segment_index(segment)
    #     if number < 0:
    #         log.error("tried to restore caret to a deleted segment? %s" % segment)
    #     else:
    #         if number != self.segment_number:
    #             self.view_segment_number(number)
    #         CaretHandler.restore_caret_state(self, carets)
    #     log.debug(self.caret_history)

    # def collapse_selections_to_carets(self):
    #     CaretHandler.collapse_selections_to_carets(self)
    #     self.document.change_count += 1
    #     self.segment.clear_style_bits(selected=True)

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
        j = json.dumps(metadata).encode('utf-8')
        return j

    @classmethod
    def restore_selected_index_metadata(self, encoded_meta):
        metadata = json.loads(encoded_meta.decode('utf-8'))
        style = np.asarray(metadata[0], dtype=np.uint8)
        where_comments = np.asarray(metadata[1], dtype=np.int32)
        return style, where_comments, metadata[2]

    def get_segments_from_selection(self, size=-1):
        s = self.segment
        segments = []

        # Get the selected ranges directly from the segment style data, because
        # the selected ranges in the caret list can be out of order or
        # overlapping
        ranges = s.get_style_ranges(selected=True)
        if len(ranges) == 1:
            seg_start, seg_end = ranges[0]
            if size < 0:
                size = seg_end - seg_start
            for start in range(seg_start, seg_end, size):
                end = min(seg_end, start + size)
                segment = DefaultSegment(s.rawdata[start:end], s.origin + start)
                segments.append(segment)
        elif len(ranges) > 1:
            # If there are multiple selections, use an indexed segment
            indexes = []
            for start, end in ranges:
                indexes.extend(list(range(start, end)))
            if size < 0:
                size = len(indexes)
            for i in range(0, len(indexes), size):
                raw = s.rawdata.get_indexed(indexes[i:i + size])
                segment = DefaultSegment(raw, s.origin + indexes[i])
                segments.append(segment)
        return segments

    def index_clicked(self, index, bit, from_control, refresh_from=True):
        log.debug("index_clicked: %s from %s at %d, %s" % (refresh_from, from_control, index, bit))
        self.carets.current.index = index
        if refresh_from:
            from_control = None
        self.update_caret = (from_control, index, bit)


class VirtualTableLinkedBase(LinkedBase):
    """A LinkedBase for virtual data; that is, data that is computed on the fly
    or data that is generated and doesn't physically reside in the segment
    data. It is linked to a HexTable that provides the sizing information.
    """

    def __init__(self, *args, **kwargs):
        LinkedBase.__init__(self, *args, **kwargs)
        self.table = None

    @property
    def document_length(self):
        return self.table.last_valid_index + 1

    def find_segment_parser(self, parsers, segment_name=None):
        log.debug("segment change operations ignored on VirtualLinkedBase")

    def find_first_valid_segment_index(self):
        log.debug("segment change operations ignored on VirtualLinkedBase")

    def find_segment(self, segment, refresh=False, data_model_changed=True):
        log.debug("segment change operations ignored on VirtualLinkedBase")

    def set_segment_parser(self, parser):
        log.debug("segment change operations ignored on VirtualLinkedBase")

    def view_segment_number(self, number):
        log.debug("segment change operations ignored on VirtualLinkedBase")
