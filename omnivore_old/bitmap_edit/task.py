""" Bitmap editor

"""
# Enthought library imports.
from pyface.api import GUI, ImageResource, ConfirmationDialog, FileDialog, \
    ImageResource, YES, OK, CANCEL
from pyface.action.api import Action, ActionItem, Separator, Group
from pyface.tasks.api import Task, TaskWindow, TaskLayout, PaneItem, IEditor, \
    IEditorAreaPane, EditorAreaPane, Editor, DockPane, HSplitter, VSplitter
from pyface.tasks.action.api import DockPaneToggleGroup, SMenuBar, \
    SMenu, SToolBar, TaskAction, TaskToggleGroup, EditorAction, SchemaAddition
from traits.api import on_trait_change, Property, Instance, Any, Event, Int

from omnivore.framework.actions import *
from bitmap_editor import BitmapEditor
from preferences import BitmapEditPreferences
from commands import *
from omnivore8bit.hex_edit.task import HexEditTask
from omnivore8bit.hex_edit.actions import *
import pane_layout
from omnivore.framework.toolbar import get_toolbar_group
import omnivore8bit.arch.colors as colors


class BitmapEditTask(HexEditTask):
    """The Bitmap editor will be a pixel-level editor for any of the graphics
    modes that Omnivore supports.

    But currently it is little more than an image viewer and not terribly
    interesting apart from that.  I will document this more when I add some
    editing functions.
    """

    new_file_text = ""

    editor_id = "omnivore.bitmap_edit"

    pane_layout_version = pane_layout.pane_layout_version

    #### Task interface #######################################################

    id = editor_id + "." + pane_layout_version if pane_layout_version else editor_id
    name = 'Bitmap Editor'

    preferences_helper = BitmapEditPreferences

    #### Menu events ##########################################################

    ui_layout_overrides = {
        "menu": {
            "order": ["File", "Edit", "View", "Segment", "Documents", "Window", "Help"],
            "View": ["ColorGroup", "BitmapGroup", "ZoomGroup", "ChangeGroup", "ConfigGroup", "ToggleGroup", "TaskGroup", "DebugGroup"],
            "Segment": ["ListGroup", "ActionGroup"],
        },
    }

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def _default_layout_default(self):
        return pane_layout.pane_layout()

    def create_dock_panes(self):
        return pane_layout.pane_create()

    def _tool_bars_default(self):
        toolbars = []
        toolbars.append(get_toolbar_group("%s:Modes" % self.id, BitmapEditor.valid_mouse_modes))
        toolbars.extend(HexEditTask._tool_bars_default(self))
        return toolbars

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = BitmapEditor()
        return editor

    @on_trait_change('window.application.preferences_changed_event')
    def refresh_from_new_preferences(self):
        # no prefs for bitmap editor yet, but hex edit has prefs that bitmap
        # doesn't have so we override it here so the hex edit prefs don't get
        # used.
        pass

    def get_actions_Menu_Segment_ActionGroup(self):
        return [
            GetSegmentFromSelectionAction(),
            MultipleSegmentsFromSelectionAction(),
            ]

    ###
    @classmethod
    def can_edit(cls, document):
        return document.metadata.mime == "application/octet-stream" or document.segments

    @classmethod
    def get_match_score(cls, document):
        """Return a number based on how good of a match this task is to the
        incoming Document.
        
        0 = generic match
        ...
        10 = absolute match
        """
        return 0
