import numpy as np

from omnivore.framework.errors import ProgressCancelError
from omnivore.utils.command import Batch, Command, UndoInfo
from omnivore.tasks.hex_edit.commands import ChangeByteCommand, SetValueCommand

import logging
progress_log = logging.getLogger("progress")


class CreateObjectCommand(SetValueCommand):
    short_name = "create_jumpman_obj"
    pretty_name = "Create Object"


class MoveObjectCommand(SetValueCommand):
    short_name = "move_jumpman_obj"
    pretty_name = "Move Object"


class FlipVerticalCommand(SetValueCommand):
    short_name = "vflip_jumpman_obj"
    pretty_name = "Flip Vertically"


class FlipHorizontalCommand(SetValueCommand):
    short_name = "hflip_jumpman_obj"
    pretty_name = "Flip Horizontally"
