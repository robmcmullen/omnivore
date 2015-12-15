import os
import types

import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Trait, TraitHandler, Int, Any, List, Set, Bool, Event, Dict, Set, Unicode, Property

from omnivore.utils.command import UndoStack
from omnivore.utils.file_guess import FileMetadata
from omnivore.utils.binutil import DefaultSegment, DefaultSegmentParser, InvalidSegmentParser


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
    
    invariant = Int(-1)
    
    bytes = Trait("", TraitNumpyConverter())
    
    segments = List
    
    user_segments = List
    
    # Trait events to provide view updating
    
    undo_stack_changed = Event
    
    byte_values_changed = Event  # but not the size of the bytes array. That's not handled yet

    #### trait default values
    
    def _metadata_default(self):
        return FileMetadata(uri="")
    
    def _undo_stack_default(self):
        return UndoStack()
    
    def _bytes_default(self):
        return ""
    
    def _segments_default(self):
        return list([DefaultSegment()])

    #### trait property getters

    def _get_name(self):
        return os.path.basename(self.metadata.uri) or 'Untitled'

    def _get_uri(self):
        return self.metadata.uri
    
    @property
    def menu_name(self):
        return "%s (%s)" % (self.name, self.uri)
    
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

    def parse_segments(self, parser_list):
        parser_list.append(DefaultSegmentParser)
        for parser in parser_list:
            try:
                s = parser(self.bytes)
                break
            except InvalidSegmentParser:
                pass
        self.segments = s.segments
        self.segments.extend(self.user_segments)
        return parser
    
    def add_user_segment(self, segment):
        self.user_segments.append(segment)
        self.segments.append(segment)
    
    def find_segment_index_by_name(self, name):
        for i, s in enumerate(self.segments):
            if s.name == name:
                return i
        return -1
