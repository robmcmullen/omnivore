""" Font editor

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
from font_editor import FontEditor
from preferences import FontEditPreferences
from commands import *
from omnivore8bit.hex_edit.task import HexEditTask
import omnivore8bit.arch.fonts as fonts
import omnivore8bit.arch.colors as colors
import pane_layout
from omnivore.framework.toolbar import get_toolbar_group


class FontEditTask(HexEditTask):
    """Font edit mode provides font (or tile) editor where the font bits
    are manipulated directly using the graphical interface, so no more
    converting to hex digits to change a font!

    Selecting a segment will then show the array of available glyphs in the
    main window and the bit editor, color selector, and others in dockable
    panes. There are tools available in the toolbar, such as line and rectangle
    drawing, that can help speed up the process of creating areas. Cut and
    paste of rectangular areas is supported. The basic usage of the draw tools
    is to select a color and use that to draw in the glyph. Holding down the
    left mouse button while moving extends the shape and releasing the mouse
    ends the shape. Full undo/redo support is available.

    Selecting a glyph from the grid of glyphs will display the zoomed version
    in the bit editor. Changes to the glyph in the bit editor will be updated
    immediately in the glyph grid.

    The glyph list can vary for different font classes; for example, Atari
    fonts have 256 glyphs, but the second 128 characters are inverse video
    versions of the first 128 and can not be changed independently from its
    compliment.

    In addition to the main glyph window, there is a drawing toolbar and three
    supporting panes, all of which are described below.

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

    Color Picker
    ------------

    This mode will set the current drawing color from a location in the editor.
    Click the left mouse button on a pixel and that color will be highlighted
    in the `Color`_ pane.

    Freehand Drawing
    ----------------

    The current color will be used to replace the pixels at the mouse pointer
    location when the left button is held down.

    Line Drawing
    ------------

    To start drawing a line with the current color, left click on the starting
    location and hold the mouse button. As you move the mouse, a preview of the
    line will be drawn between the starting location and the current mouse
    position. When you release the mouse button, the line will be copied to the
    glyph.

    Square
    ------

    The process for drawing a square is much the line: left click on a point
    (this will become a corner) and hold the mouse button while you choose a
    point that will become the opposite corner. Like the line, it is a preview
    until you release the button, whereupon it will be copied to the glyph.

    The border is one tile wide, and the interior is not filled.

    Filled Square
    -------------

    This is the same the square above, except the interior is filled with the
    tile.

    Dockable Windows
    ================

    Bit Editor
    -------------

    This is the zoomed version of the selected glyph. Each bit is individually
    addressable using the mouse pointer. The basic usage is clicking the left
    mouse button on a bit which will change its color to the currently selected
    color (see below). Toolbar functions can be used to draw shapes or affect
    multiple bits.

    Color Selector
    --------------

    The available colors are shown here.

    """

    new_file_text = ["Atari Font", "Apple ][ Font"]

    editor_id = "omnivore.font_edit"

    pane_layout_version = pane_layout.pane_layout_version

    #### Task interface #######################################################

    id = editor_id + "." + pane_layout_version if pane_layout_version else editor_id
    name = 'Font Editor'

    preferences_helper = FontEditPreferences

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
        toolbars.append(get_toolbar_group("%s:Modes" % self.id, FontEditor.valid_mouse_modes))
        toolbars.extend(HexEditTask._tool_bars_default(self))
        return toolbars

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = FontEditor()
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
