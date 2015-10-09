import numpy as np

from peppy2.utils.command import UndoStack, BatchStatus


class Document(object):
    def __init__(self, metadata, bytes):
        self.metadata = metadata
        self.bytes = np.fromstring(bytes, dtype=np.uint8)
        self.undo_stack = UndoStack()
    
    def __str__(self):
        return self.metadata.uri
    
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
