import os
import types
import cStringIO as StringIO

import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Trait, TraitHandler, Int, Any, List, Set, Bool, Event, Dict, Set, Unicode, Property, Str

from omnivore.utils.command import UndoStack
from omnivore.utils.file_guess import FileMetadata
from omnivore.utils.segmentutil import DefaultSegment, DefaultSegmentParser, InvalidSegmentParser


class TraitNumpyConverter(TraitHandler):
    """Trait validator to convert bytes to numpy array"""
    def validate(self, object, name, value):
        if type(value) is np.ndarray:
            return value
        elif type(value) is types.StringType:
            return np.fromstring(value, dtype=np.uint8)
        self.error(object, name, value)

    def info(self):
        return '**a string or numpy array**'


class Document(HasTraits):
    undo_stack = Any
    
    metadata = Any

    name = Property(Unicode, depends_on='metadata')

    uri = Property(Unicode, depends_on='metadata')
    
    document_id = Int(-1)
    
    last_task_id = Str
    
    bytes = Trait("", TraitNumpyConverter())
    
    style = Trait("", TraitNumpyConverter())
    
    segments = List
    
    segment_parser = Any
    
    user_segments = List
    
    extra_metadata = Dict
    
    # Trait events to provide view updating
    
    undo_stack_changed = Event
    
    byte_values_changed = Event  # but not the size of the bytes array. That's not handled yet
    
    change_count = Int()
    
    can_revert = Property(Bool, depends_on='metadata')

    #### trait default values
    
    def _metadata_default(self):
        return FileMetadata(uri="")
    
    def _undo_stack_default(self):
        return UndoStack()
    
    def _bytes_default(self):
        return ""
    
    def _style_default(self):
        return np.zeros(len(self), dtype=np.uint8)
    
    def _segments_default(self):
        return list([DefaultSegment(self.bytes, self.style, 0)])

    #### trait property getters

    def _get_name(self):
        return self.metadata.name or 'Untitled'

    def _get_uri(self):
        return self.metadata.uri
    
    def _get_can_revert(self):
        return self.metadata.uri != ""
    
    @property
    def menu_name(self):
        if self.uri:
            return "%s (%s)" % (self.name, self.uri)
        return self.name
    
    @classmethod
    def get_blank(cls):
        return cls(bytes="")
    
    def __str__(self):
        return self.metadata.uri
    
    def __len__(self):
        return np.alen(self.bytes)
    
    def __getitem__(self, val):
        return self.bytes[val]

    def to_bytes(self):
        return self.bytes.tostring()
    
    @property
    def bytestream(self):
        return StringIO.StringIO(self.bytes)

    def parse_segments(self, parser_list):
        parser_list.append(DefaultSegmentParser)
        for parser in parser_list:
            try:
                s = parser(self)
                break
            except InvalidSegmentParser:
                pass
        self.set_segments(s)
    
    def set_segments(self, parser):
        self.segment_parser = parser
        self.segments = []
        self.segments.extend(parser.segments)
        self.segments.extend(self.user_segments)
    
    @property
    def global_segment(self):
        return self.segments[0]
    
    def add_user_segment(self, segment):
        self.user_segments.append(segment)
        self.segments.append(segment)
    
    def is_user_segment(self, segment):
        return segment in self.user_segments
    
    def delete_user_segment(self, segment):
        self.user_segments.remove(segment)
        self.segments.remove(segment)
    
    def find_segment_index_by_name(self, name):
        for i, s in enumerate(self.segments):
            if s.name == name:
                return i
        return -1
    
    def find_segment_in_range(self, addr):
        """Assuming segments had a start_addr param, find first segment that
        has addr as a valid address
        """
        for i, s in enumerate(self.segments):
            if addr >= s.start_addr and addr < (s.start_addr + len(s)):
                return i, s, addr - s.start_addr
        return -1, None, None
