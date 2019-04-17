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
from sawx.framework.editor import FrameworkEditor
import sawx.framework.clipboard as clipboard
from sawx.utils.file_guess import FileMetadata
from sawx.ui.tilemanager import TileManager
from sawx.persistence import get_template
from ..byte_edit.byte_editor import ByteEditor
from ..arch.machine import Machine, Atari800
from .document import EmulationDocument
from ..utils.segmentutil import SegmentData, DefaultSegment, AnticFontSegment
from .. import guess_emulator

from sawx.utils.processutil import run_detach

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

    #### ByteEditor interface

    def prepare_for_destroy(self):
        self.document.stop_timer()
        ByteEditor.prepare_for_destroy(self)

    def preprocess_document(self, doc):
        args = {}
        skip = 0
        log.debug(f"preprocess_document: EmulatorEditor, {doc}")
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
            try:
                emulator_type = args['machine']
            except KeyError:
                emulator_type = guess_emulator(doc)
            doc = EmulationDocument.create_document(source_document=doc, emulator_type=emulator_type, skip_frames_on_boot=skip)
        doc.boot()
        log.debug(f"Using emulator {doc.emulator_type}")
        return doc
