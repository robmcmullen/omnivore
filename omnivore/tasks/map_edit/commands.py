import numpy as np

from omnivore.framework.errors import ProgressCancelError
from omnivore.utils.command import Batch, Command, UndoInfo
from omnivore.tasks.hex_edit.commands import ChangeByteCommand

import logging
progress_log = logging.getLogger("progress")


class DrawBatchCommand(Batch):
    short_name = "draw"
    pretty_name = "Draw"
    
    def __str__(self):
        if self.commands:
            return "%s %dx%s" % (self.pretty_name, len(self.commands), str(self.commands[0]))
        return self.pretty_name

    def get_next_batch_command(self, segment, index, bytes):
        cmd = ChangeByteCommand(segment, index, index+len(bytes), bytes, False, True)
        return cmd
    