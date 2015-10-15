import numpy as np

from omnimon.utils.command import UndoStack, BatchStatus
from omnimon.utils.file_guess import FileMetadata


class Document(object):
    @classmethod
    def get_blank(cls):
        metadata = FileMetadata(uri="about:blank")
        return cls(metadata, "")
    
    def __init__(self, metadata, bytes):
        self.metadata = metadata
        self.bytes = np.fromstring(bytes, dtype=np.uint8)
        self.undo_stack = UndoStack()
        self.segments = []
    
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
        b = BatchStatus()
        undo = self.process_batch_command(command, b, editor)
        self.perform_batch_flags(b, editor)
        history = self.undo_stack.serialize()
        editor.window.application.save_log(str(history), "command_log", ".log")
        return undo
        
    def process_batch_command(self, command, b, editor):
        """Process a single command but don't update the UI immediately.
        Instead, update the batch flags to reflect the changes needed to
        the UI.
        
        """
        undo = self.undo_stack.perform(command, editor)
        b.add_flags(command, undo.flags)
        return undo
    
    def perform_batch_flags(self, b, editor):
        """Perform the UI updates given the BatchStatus flags
        
        """
        editor.update_history()
