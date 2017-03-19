import numpy as np

from omnivore.framework.errors import ProgressCancelError
from omnivore.utils.command import Batch, Command, UndoInfo
from omnivore8bit.hex_edit.commands import ChangeByteCommand, SetValueCommand

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


class ClearTriggerCommand(SetValueCommand):
    short_name = "cleartrigger_jumpman_obj"
    pretty_name = "Clear Trigger Function"

class SetTriggerCommand(SetValueCommand):
    short_name = "settrigger_jumpman_obj"
    pretty_name = "Set Trigger Function"


class AssemblyChangedCommand(SetValueCommand):
    short_name = "jumpman_custom_code"
    pretty_name = "Reassemble Custom Code"
