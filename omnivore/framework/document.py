import os
import types
import cStringIO as StringIO

import numpy as np
import fs

# Enthought library imports.
from traits.api import HasTraits, Trait, TraitHandler, Int, Any, List, Set, Bool, Event, Dict, Set, Unicode, Property, Str

from atrcopy import SegmentData, DefaultSegment, DefaultSegmentParser, InvalidSegmentParser

from omnivore.utils.command import UndoStack
from omnivore.utils.file_guess import FileGuess, FileMetadata


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

    read_only = Property(Bool, depends_on='metadata')

    document_id = Int(-1)
    
    baseline_document = Any(transient=True)
    
    last_task_id = Str
    
    bytes = Trait("", TraitNumpyConverter())
    
    style = Trait("", TraitNumpyConverter())
    
    segments = List
    
    segment_parser = Any
    
    user_segments = List
    
    extra_metadata = Dict
    
    emulator = Any

    emulator_change_event = Event
    
    # Trait events to provide view updating
    
    undo_stack_changed = Event
    
    byte_values_changed = Event  # but not the size of the bytes array. That's not handled yet
    
    change_count = Int()
    
    can_revert = Property(Bool, depends_on='metadata')

    permute = Any

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
        r = SegmentData(self.bytes,self.style)
        return list([DefaultSegment(r, 0)])

    #### trait property getters

    def _get_name(self):
        return self.metadata.name or 'Untitled'

    def _get_uri(self):
        return self.metadata.uri

    def _set_uri(self, uri):
        self.metadata.uri = uri

    def _get_read_only(self):
        return self.metadata.read_only

    def _set_read_only(self, read_only):
        self.metadata.read_only = read_only
    
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
        return "Document(id=%s): %s" % (self.document_id, self.metadata.uri)
    
    def __len__(self):
        return np.alen(self.bytes)
    
    def __getitem__(self, val):
        return self.bytes[val]
    
    @property
    def dirty(self):
        return self.undo_stack.is_dirty()

    def to_bytes(self):
        return self.bytes.tostring()

    def load_permute(self, editor):
        if self.permute:
            self.permute.load(self, editor)

    def filesystem_path(self):
        try:
            fs_, relpath = fs.opener.opener.parse(self.uri)
            if fs_.hassyspath(relpath):
                return fs_.getsyspath(relpath)
        except fs.errors.FSError:
            pass
        return None
    
    @property
    def bytestream(self):
        return StringIO.StringIO(self.bytes)

    def parse_segments(self, parser_list):
        parser_list.append(DefaultSegmentParser)
        for parser in parser_list:
            try:
                r = SegmentData(self.bytes, self.style)
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
    
    @property
    def global_segment(self):
        return self.segments[0]
    
    def add_user_segment(self, segment, replace=False):
        if replace:
            if self.find_matching_user_segment(segment):
                return
        self.user_segments.append(segment)
        self.segments.append(segment)
    
    def is_user_segment(self, segment):
        return segment in self.user_segments
    
    def delete_user_segment(self, segment):
        self.user_segments.remove(segment)
        self.segments.remove(segment)

    def find_matching_user_segment(self, segment):
        for s in self.user_segments:
            if len(s) == len(segment) and s.start_addr == segment.start_addr and s.name == segment.name:
                return True
        return False
    
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
    
    def find_segment_in_range(self, addr):
        """Assuming segments had a start_addr param, find first segment that
        has addr as a valid address
        """
        for i, s in enumerate(self.segments):
            if addr >= s.start_addr and addr < (s.start_addr + len(s)):
                return i, s, addr - s.start_addr
        return -1, None, None

    def set_emulator(self, emu):
        self.emulator = emu
        self.emulator_change_event = True
    
    def init_baseline(self, metadata, bytes):
        d = Document(metadata=metadata, bytes=bytes)
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

