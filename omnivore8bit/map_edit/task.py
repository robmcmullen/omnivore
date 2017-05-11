""" Map editor

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
from map_editor import MapEditor
from preferences import MapEditPreferences
from commands import *
from omnivore8bit.hex_edit.task import HexEditTask
from omnivore8bit.hex_edit.actions import *
import omnivore8bit.arch.fonts as fonts
import omnivore8bit.arch.colors as colors
import pane_layout
from omnivore.framework.toolbar import get_toolbar_group


class MapEditTask(HexEditTask):
    """Map edit mode provides a tile-based editor, capable of handling
    scrolling playfields much wider than the screen.

    Currently it has mostly been testing with Getaway! level editing, but it
    can edit arbitrary maps. It needs a segment that exactly fits the
    dimensions of the map, so some number of bytes wide times the number of
    rows. If it does recognize the disk image as a Getaway! disk, it will set
    up some extra features.

    Selecting a segment will then show the map on a scrolling window. There are
    tools available in the toolbar, such as line and rectangle drawing, that
    can help speed up the process of creating areas. Cut and paste of
    rectangular areas is supported. The basic usage of the draw tools is to
    select a tile and use that as the drawing tile for whatever shape was
    selected. Holding down the left mouse button while moving extends the shape
    and releasing the mouse ends the shape. Full undo/redo support is
    available.

    In addition to the main map window, there are three supporting panes: a
    tile map pane that shows characters broken down by groups, a character set
    pane that shows the entire 256 byte character set (which for Atari includes
    the inverse characters in the second 128 positions), and a page map pane
    that shows an overview of the map at one pixel per character. Note that the
    page map is just greyscale; it uses the value of the byte at a particular
    location as the intensity.
    """

    new_file_text = ""

    editor_id = "omnivore.map_edit"

    pane_layout_version = pane_layout.pane_layout_version

    #### Task interface #######################################################

    id = editor_id + "." + pane_layout_version if pane_layout_version else editor_id
    name = 'Map Editor'

    preferences_helper = MapEditPreferences

    #### Menu events ##########################################################

    ui_layout_overrides = {
        "menu": {
            "order": ["File", "Edit", "View", "Segment", "Documents", "Window", "Help"],
            "View": ["ColorGroup", "FontGroup", "ZoomGroup", "ChangeGroup", "ConfigGroup", "ToggleGroup", "TaskGroup", "DebugGroup"],
            "Segment": ["ListGroup"],
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
        toolbars.append(get_toolbar_group("%s:Modes" % self.id, MapEditor.valid_mouse_modes))
        toolbars.extend(HexEditTask._tool_bars_default(self))
        return toolbars

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = MapEditor()
        return editor

    @on_trait_change('window.application.preferences_changed_event')
    def refresh_from_new_preferences(self):
        e = self.active_editor
        if e is not None:
            prefs = self.preferences

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
