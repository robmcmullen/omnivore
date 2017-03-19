import numpy as np

from omnivore.framework.document import BaseDocument, TraitNumpyConverter

# Enthought library imports.
from traits.api import Trait, Any, List, Event, Dict

from atrcopy import SegmentData, DefaultSegment, DefaultSegmentParser, InvalidSegmentParser, iter_parsers

import logging
log = logging.getLogger(__name__)


class SegmentedDocument(BaseDocument):
    baseline_document = Any(transient=True)
    
    style = Trait("", TraitNumpyConverter())
    
    segment_parser = Any
    
    user_segments = List
    
    extra_metadata = Dict
    
    emulator = Any

    emulator_change_event = Event

    #### trait default values
    
    def _style_default(self):
        return np.zeros(len(self), dtype=np.uint8)
    
    def _segments_default(self):
        r = SegmentData(self.bytes,self.style)
        return list([DefaultSegment(r, 0)])



    def parse_segments(self, parser_list):
        parser_list.append(DefaultSegmentParser)
        r = SegmentData(self.bytes, self.style)
        for parser in parser_list:
            try:
                s = parser(r)
                break
            except InvalidSegmentParser:
                pass
        self.set_segments(s)
    
    def set_segments(self, parser):
        self.segment_parser = parser
        self.segments = []
        self.segments.extend(parser.segments)
        self.segments.extend(self.user_segments)

    def parse_sub_segments(self, segment):
        mime, parser = iter_parsers(segment.rawdata)
        if parser is not None:
            index = self.find_segment_index(segment)
            self.segments[index + 1:index + 1] = parser.segments[1:] # Skip the "All" segment as it would just be a duplicate of the expanded segment
        return parser
    
    @property
    def global_segment(self):
        return self.segments[0]
    
    def add_user_segment(self, segment, replace=False):
        if replace:
            current = self.find_matching_user_segment(segment)
            if current is not None:
                log.debug("replacing %s with %s" % (current, segment))
                self.replace_user_segment(current, segment)
                return
        self.user_segments.append(segment)
        self.segments.append(segment)
    
    def is_user_segment(self, segment):
        return segment in self.user_segments
    
    def delete_user_segment(self, segment):
        self.user_segments.remove(segment)
        self.segments.remove(segment)
    
    def replace_user_segment(self, current_segment, segment):
        try:
            i = self.user_segments.index(current_segment)
            self.user_segments[i:i+1] = [segment]
            i = self.segments.index(current_segment)
            self.segments[i:i+1] = [segment]
        except ValueError:
            log.error("Attempted to replace segment %s that isn't here!")

    def find_matching_segment(self, segment):
        for s in self.segments:
            if len(s) == len(segment) and s.start_addr == segment.start_addr and s.name == segment.name:
                return True
        return False

    def find_matching_user_segment(self, segment):
        for s in self.user_segments:
            if len(s) == len(segment) and s.start_addr == segment.start_addr and s.name == segment.name:
                return s
        return None
    
    def find_segment_index(self, segment):
        try:
            return self.segments.index(segment)
        except ValueError:
            return -1
    
    def find_segment_index_by_name(self, name):
        for i, s in enumerate(self.segments):
            if s.name == name:
                return i
        return -1
    
    def find_segments_in_range(self, addr):
        """Assuming segments had a start_addr param, find first segment that
        has addr as a valid address
        """
        found = []
        for i, s in enumerate(self.segments):
            if addr >= s.start_addr and addr < (s.start_addr + len(s)):
                found.append((i, s, addr - s.start_addr))
        return found
    
    def find_segments_with_raw_index(self, raw_index):
        """Find all segments that contain the specified raw index

        The raw index points to a specific byte, so this will return all
        segments that have a view of this byte. This function ignores the
        segment start address because different views may have different start
        addresses; to find segments that contain a specific address, use
        find_segment_in_range.
        """
        found = []
        for i, s in enumerate(self.segments):
            try:
                index = s.get_index_from_base_index(raw_index)
                found.append((i, s, index))
            except IndexError:
                pass
        return found

    def set_emulator(self, emu):
        self.emulator = emu
        self.emulator_change_event = True
    
    def init_baseline(self, metadata, bytes):
        d = SegmentedDocument(metadata=metadata, bytes=bytes)
        d.parse_segments([])
        self.baseline_document = d
    
    def del_baseline(self):
        self.baseline_document = None
    
    def update_baseline(self):
        if self.baseline_document is not None:
            self.change_count += 1
            self.global_segment.compare_segment(self.baseline_document.global_segment)
    
    def clear_baseline(self):
        self.change_count += 1
        self.global_segment.clear_style_bits(diff=True)
    
    @property
    def has_baseline(self):
        return self.baseline_document is not None

