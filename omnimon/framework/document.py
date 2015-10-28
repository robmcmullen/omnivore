import os
import types

import numpy as np

# Enthought library imports.
from traits.api import HasTraits, Trait, TraitHandler, Int, Any, List, Set, Bool, Event, Dict, Set, Unicode, Property

from omnimon.utils.command import UndoStack, BatchFlags
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
    
    def process_command(self, command, editor):
        """Process a single command and immediately update the UI to reflect
        the results of the command.
        """
        b = BatchFlags()
        undo = self.process_batch_command(command, b)
        if undo.flags.success:
            editor.perform_batch_flags(self, b)
        return undo
        
    def process_batch_command(self, command, b):
        """Process a single command but don't update the UI immediately.
        Instead, update the batch flags to reflect the changes needed to
        the UI.
        
        """
        undo = self.undo_stack.perform(command, self)
        b.add_flags(command, undo.flags)
        return undo
