import os
import types

import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Trait, TraitHandler, Int, Any, List, Set, Bool, Event, Dict, Set, Unicode, Property

from omnimon.utils.command import UndoStack
from omnimon.utils.file_guess import FileMetadata


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
    
    bytes = Trait("", TraitNumpyConverter())
    
    segments = List
    
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
        return list()

    #### trait property getters

    def _get_name(self):
        return os.path.basename(self.metadata.uri) or 'Untitled'

    def _get_uri(self):
        return self.metadata.uri
    
    @classmethod
    def get_blank(cls):
        return cls(bytes="")
    
    def __str__(self):
        return self.metadata.uri
    
    def __len__(self):
        return np.alen(self.bytes)
    
    def __getitem__(self, val):
        return self.bytes[val]
