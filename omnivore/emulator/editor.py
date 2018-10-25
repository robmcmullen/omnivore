# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np
import json

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Dict, Event, Enum, Instance, File, Unicode, Property, provides, on_trait_change
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnivore_framework.framework.editor import FrameworkEditor
import omnivore_framework.framework.clipboard as clipboard
from omnivore_framework.utils.file_guess import FileMetadata
from omnivore_framework.utils.wx.tilemanager import TileManager
from omnivore_framework.templates import get_template
from ..byte_edit.byte_editor import ByteEditor
from ..arch.machine import Machine, Atari800
from .document import EmulationDocument
from ..utils.segmentutil import SegmentData, DefaultSegment, AnticFontSegment

from omnivore_framework.utils.processutil import run_detach

import logging
log = logging.getLogger(__name__)


class EmulatorEditor(ByteEditor):
    """Editor that holds an emulator instance and the associated viewers.
    """

    default_viewers = "hex,video,char,disasm"

    #### trait default values

    #### trait property getters

    # Convenience functions

    @property
    def emulator(self):
        return self.document.emulator

    #### Traits event handlers

    def _closed_changed(self):
        self.document.stop_timer()

    #### ByteEditor interface

    def preprocess_document(self, doc):
        args = {}
        skip = 0
        if self.task_arguments:
            for arg in self.task_arguments.split(","):
                if "=" in arg:
                    arg, v = arg.split("=", 1)
                else:
                    v = None
                args[arg] = v
            if "skip_frames" in args:
                skip = int(args["skip_frames"])
        try:
            doc.emulator_type
        except:
            doc = EmulationDocument.create_document(source_document=doc, emulator_type=args.get('machine', '6502'), skip_frames_on_boot=skip)
        doc.boot(doc.source_document.container_segment)
        return doc
