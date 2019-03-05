""" Text editor sample task

"""
# Enthought library imports.
from pyface.action.api import Separator, Group
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import SMenuBar, SMenu, SToolBar, SchemaAddition
from traits.api import on_trait_change, Property, Instance, Any, Event, Int, Bool

from .. import known_emulators

from sawx.framework.task import FrameworkTask
from sawx.framework import actions as fa
from sawx.framework.toolbar import get_toolbar_group
from . import actions as ea
from .preferences import EmulatorPreferences
from .editor import EmulatorEditor
from ..byte_edit.task import ByteEditTask
from ..byte_edit import actions as ba
from ..viewers import actions as va
from ..arch import fonts, colors, machine
from ..utils.segmentutil import iter_known_segment_parsers


class EmulatorTask(ByteEditTask):
    """The emulator task supports a variety of 8-bit system emulators, 
    providing a common front-end and debugger to all of them.

    All data viewers from the `ByteEditTask`__ are available here, as well as
    viewers that only make sense when examining emulator internals and output.

    Currently there are emulators for systems:

    * Atari 8-bit computer

      * Atari 400/800
      * Atari XL

    * Generic 6502

    * Apple ][+ (very limited support)
    """

    new_file_text = []

    editor_id = "omnivore.emulator"

    pane_layout_version = ""

    #### Task interface #######################################################

    id = editor_id

    name = 'Emulator'

    preferences_helper = EmulatorPreferences

    #### Menu events ##########################################################

    ui_layout_overrides = {
        "menu": {
            "order": ["File", "Edit", "View", "Bytes", "Segment", "Emulation", "Documents", "Window", "Help"],
            "View": ["PredefinedGroup", "ProcessorGroup", "AssemblerGroup", "MemoryMapGroup", "ColorGroup", "FontGroup", "BitmapGroup", "SizeGroup", "ChangeGroup", "ConfigGroup", "ToggleGroup", "TaskGroup", "DebugGroup"],
            "Bytes": ["HexModifyGroup"],
            "Segment": ["ListGroup", "ActionGroup", "LabelGroup"],
            "Disk Image": ["ParserGroup", "ActionGroup"],
            "Emulation":  ["ConfigGroup", "CommandGroup"],
        },
    }


    #### FrameworkTask interface

    def get_editor(self, task_arguments="", **kwargs):
        """ Opens a new empty window
        """
        editor = EmulatorEditor(task_arguments=task_arguments)
        return editor

    #### Menu and toolbar definition

    def get_actions_Menu_Emulation_CommandGroup(self):
        return [
            ea.PauseResumeAction(),
            ea.PreviousSaveStateAction(),
            ea.NextSaveStateAction(),
            Separator(),
            ea.StepAction(),
            ea.StepIntoAction(),
            ea.StepOverAction(),
            ea.EndOfFrameAction(),
            ea.BreakVBIStart(),
            Separator(),
            ea.StartAction(),
            ea.SelectAction(),
            ea.OptionAction(),
            Separator(),
            ea.WarmstartAction(),
            ea.ColdstartAction(),
            ]

    #### file recognizer

    @classmethod
    def can_edit(cls, document):
        return hasattr(document, "emulator_type")

    @classmethod
    def get_match_score(cls, document):
        """Return a number based on how good of a match this task is to the
        incoming Document.
        
        0 = generic match
        ...
        10 = absolute match
        """
        return 10
