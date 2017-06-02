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

    In addition to the main map window, there is a drawing toolbar and three
    supporting panes, all of which are described below.

    Getaway
    -------

    I interviewed Mark Reid in `Player/Missile episode 19
    <https://playermissile.com/podcast/ep019.html>`_ and he subsequently
    located the original floppy disks containing his original source code. He
    generously placed the code in the public domain, and I have set up a
    `github repository <https://github.com/robmcmullen/getaway>`_ to further
    development.

    Wade of the `Inverse ATASCII <https://inverseatascii.info>`_ and `1632
    Atari PodcaST <https://1632podcast.info>`_ created the first new map for
    Getaway using the map editor in Omnivore. He discovered some limitations
    with custom maps that the original game didn't handle because the original
    game wasn't meant to have different maps. For instance, the hideout was
    hardcoded in a certain position, and the game would freeze if a cop reached
    a dead end because the original game didn't have any dead ends.

    AtariAge user itaych fixed those bugs that caused custom maps to freeze the
    game, and I added the ability to place the hideout at any location.

    Toolbar
    =======

    Choosing any tool on the toolbar palette keeps that mode active until a new
    toolbar icon is selected.

    Selection
    ---------

    The default mode is selection. Click the left button to place the cursor at
    a location, and drag while holding down the left button to select a
    rectangular region.

    Multiple selection is supported: hold down the Control key (Command on Mac)
    while clicking and dragging and new rectangular areas can be selected.

    Tile Picker
    -----------

    This mode will set the current drawing tile from a location on the screen.
    Click the left mouse button on a tile and that tile will be highlighted in
    the `Tile Map`_ and the `Character Set`_, and therefore will be used as the
    current drawing tile.

    Freehand Drawing
    ----------------

    The current tile will be used to replace the tile at the mouse pointer
    location when the left button is held down.

    Line Drawing
    ------------

    To start drawing a line with the current tile, left click on the starting
    location and hold the mouse button. As you move the mouse, a preview of the
    line will be drawn between the starting location and the current mouse
    position. When you release the mouse button, the line will be copied to the
    map.

    Square
    ------

    The process for drawing a square is much the line: left click on a point
    (this will become a corner) and hold the mouse button while you choose a
    point that will become the opposite corner. Like the line, it is a preview
    until you release the button, whereupon it will be copied to the map.

    The border is one tile wide, and the interior is not filled.

    Filled Square
    -------------

    This is the same the square above, except the interior is filled with the
    tile.

    Dockable Windows
    ================

    Character Set
    -------------

    From this grid of all 256 possible tiles, you can select a tile to use as
    the drawing pattern. All of the drawing commands in the toolbar above will
    use the selected tile.

    For the Atari, it includes the inverse characters in the second 128
    positions.

    Tile Map
    --------

    This pane also shows tiles, but in this case they are grouped together in
    sections. Use the drop-down list at the top to choose a section, which will
    scroll the tiles belonging to that section into view.

    So far, this is only used for Getaway maps, and it is hardcoded. Eventually
    there will be a way to define custom sections.

    Overview Map
    ------------

    This is a small version of the map, showing a view at one pixel per
    character. Note that the page map is just greyscale; it uses the tile
    number (i.e. the byte value) at a particular location as the intensity.

    """

    new_file_text = "Getaway Map"

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

    def get_actions_Menu_Edit_CopyPasteGroup(self):
        return [
            CutAction(),
            CopyAction(),
            PasteAction(),
            ]

    def get_actions_Menu_Edit_SelectGroup(self):
        return [
            SelectAllAction(),
            SelectNoneAction(),
            SelectInvertAction(),
            ]

    def get_actions_Menu_Edit_FindGroup(self):
        return []

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
