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
from omnivore8bit.hex_edit.task import HexEditTask
from omnivore8bit.hex_edit.actions import *
from omnivore8bit.hex_edit.preferences import HexEditPreferences
import omnivore8bit.arch.colors as colors
from omnivore.framework.toolbar import get_toolbar_group

from jumpman_editor import JumpmanEditor
from commands import *
import pane_layout
from actions import *


class JumpmanEditTask(HexEditTask):
    """This Jumpman level editor is a complete solution for creating new levels
    for this all-time-classic game.

    Open Omnivore and choose ``File -> New -> Jumpman Level`` and you'll see a
    very simple level definition. You can add to that by clicking one of the
    draw icons in the toolbar and drawing in the main window. By clicking on
    the arrow icon in the toolbar you can select existing items and drag them
    around; you can cut, copy and paste the selected items, and more. Change
    the level settings like the level name and number of bullets in the right
    hand panel.

    Tips:

    * Only one bomb per grid square
    * Use ramps that slope up or down by only one pixel per block

    Girders can be placed at any position, but note that Jumpman can only
    fearlessly navigate the horizontal girders and ramps that are sloped up or
    down by one pixel per block. Ramps that slope up more than that can be
    (carefully) climbed, but down-slopes of more than one pixel will trip up
    and kill poor Jumpman. It's not recommended to use more than one pixel
    slope up or down, but I have left the feature in the editor just in case
    someone comes up with a use for it.

    Ladders can only be placed at even pixel columns (as measured from the left
    side), and are further limited in that only 12 unique columns can be used.
    Ladders can be placed above and below one another in the same column
    without counting against the 12 column limit. The number of columns of
    ladders is shown in the ``Level Data`` window.

    Downropes can likewise only be placed at even pixel columns, and are
    limited to 6 unique column positions. As with ladders, multiple downropes
    can be placed in the same column without counting against that limit. The
    number of downropes is also shown in the ``Level Data`` window.

    Upropes are not limited in either pixel columns or number of unique column
    positions, so knock yourself out.

    The object of the game is to collect bombs, so be sure to place at least
    one bomb or the level will end immediately when you try to play it. When
    you place bombs, you'll notice a grid that appears in the main window.
    Thick red borders between each grid cell denotes invalid bomb locations, so
    place bombs only where they don't touch any of the red cell borders. (Due
    to a speed optimization in the code, the game can crash when Jumpman
    collects a bomb that is touching any part of the red shaded area.) Only one
    bomb may be placed per grid square.

    Finally, you must set Jumpman's respawn position by selecting the the
    Jumpman figure icon on the toolbar. Place the white square at the desired
    location. Typically, Jumpman will be placed on a girder, but other starting
    positions are possible. If the bottom of the square overlaps a girder,
    Jumpman will climb up. Note that Jumpman must not fall more than one pixel;
    more than that results in death.

    To playtest your level: choose ``File -> Save As``, give it a filename with
    the ``.atr`` extension, and run it in your favorite emulator. You can also
    set up Omnivore to run an emulator directly when you press F5; go to the
    ``Disk Image -> Emulators -> Edit Emulators...`` entry to set up the
    emulator for your platform.

    For more complicated levels, Jumpman has a feature where it will draw new
    items or erase existing ones when you collect a bomb. To create a level
    using this feature, use the ``Trigger Painting`` panel to select one of the
    bombs (they are listed by their x and y coordinates). The level will fade
    into the background and you can paint more items in the main window.
    Everything you draw (or erase) here will only get triggered when Jumpman
    collects that bomb. You can even cascade triggers by adding more bombs and
    selecting the new bombs in the trigger painting panel. Bombs will be
    indented to show the parent/child relationship when there are multiple
    levels of nesting. Select the ``Main Level`` entry to paint on the normal
    level definition.

    Advanced Levels With Custom Code
    --------------------------------

    Omnivore now has in integrated `MAC/65 compatible
    <http://mixinc.net/atari/mac65.htm>`_ assembler that recognizes specific
    keywords in your assembly code and puts them in the correct spots in your
    Jumpman level definition.

    You will need to edit the assembly source with your favorite text editor
    and then use the ``Jumpman -> Custom Code...`` menu item to add the source
    file to your level. After that it will remember the file when you load the
    level again. Be sure the source code is in the same directory as the .atr
    image. If you move the .atr file to a new place, be sure to copy your
    assembly file as well.

    The assembler recognizes certain labels in your assembly code. If any start
    with ``trigger``, those labels will be available as targets for peanut
    collection. You can right click on peanuts and set their trigger function
    to any of those in the list.

    There are special vectors that Omnivore knows about; see the section in the
    `Jumpman Reverse Engineering Notes
    <http://playermissile.com/jumpman/notes.html#h.s0ullubzr0vv>`_.

    If you give your code any of those labels:

    * vbi1
    * vbi2
    * vbi3
    * vbi4
    * dead_begin
    * dead_at_bottom
    * dead_falling
    * out_of_lives
    * level_complete
    * collect_callback

    then Omnivore will put the vector for your subroutine in the right place in
    the level definition so that your routine gets automatically called. See
    the reverse engineering notes for more details on what each of the labels
    means.

    There's also one last special label: ``gameloop``. If you define this in
    your code, it will take over the non-VBI main game loop. If you don't
    define it, Omnivore will put the standard game loop at $2860. The game loop
    is responsible for fading in jumpman at the beginning of a level and
    monitoring end-of-game conditions. Only a few examples of a custom game
    loop exist Glover's original levels, so this is not a commonly used feature
    at all.

    Disassembly
    -----------

    If you're interested in exploring the assembly code in Jumpman, you'll want
    to use the standard Jumpman disk image and then get the Omnivore metadata
    file that provides the comments.

    * `Jumpman disk image <http://www.atarimania.com/game-atari-400-800-xl-xe-jumpman_2713.html>`_
    * `latest metadata <http://playermissile.com/jumpman/Jumpman%20(1983)(Epyx)(US)[!].atr.omnivore>`_

    Note that Omnivore recognizes a Jumpman disk image and loads right into the
    level editor. To use the hex editor, you'll need to use the menu option
    ``Window -> New View of Jumpman -> In Hex Editor Window``

    """

    new_file_text = "Jumpman Level"

    editor_id = "omnivore.jumpman"

    pane_layout_version = pane_layout.pane_layout_version

    #### Task interface #######################################################

    id = editor_id + "." + pane_layout_version if pane_layout_version else editor_id
    name = 'Jumpman Level Editor'

    preferences_helper = HexEditPreferences

    #### Menu events ##########################################################

    ui_layout_overrides = {
        "menu": {
            "order": ["File", "Edit", "View", "Jumpman", "Disk Image", "Documents", "Window", "Help"],
            "Disk Image": ["ParserGroup", "EmulatorGroup", "ActionGroup"],
            "Jumpman":  ["LevelGroup", "SelectionGroup", "CustomCodeGroup"],
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
        toolbars.append(get_toolbar_group("%s:Modes" % self.id, JumpmanEditor.valid_mouse_modes))
        toolbars.extend(HexEditTask._tool_bars_default(self))
        return toolbars

    def pane_layout_initial_visibility(self):
        return pane_layout.pane_initially_visible()

    ###########################################################################
    # 'FrameworkTask' interface.
    ###########################################################################

    def get_editor(self, guess=None):
        """ Opens a new empty window
        """
        editor = JumpmanEditor()
        return editor

    @on_trait_change('window.application.preferences_changed_event')
    def refresh_from_new_preferences(self):
        e = self.active_editor
        if e is not None:
            prefs = self.preferences

    def get_actions_Menu_Edit_UndoGroup(self):
        return [
            UndoAction(),
            RedoAction(),
            ]

    def get_actions_Menu_Edit_CopyPasteGroup(self):
        return [
            CutAction(),
            CopyAction(),
            PasteAction(),
            ]

    def get_actions_Menu_Edit_SelectGroup(self):
        return [
            SelectAllJumpmanAction(),
            SelectNoneJumpmanAction(),
            SelectInvertJumpmanAction(),
            ]

    def get_actions_Menu_Edit_FindGroup(self):
        return [
            FlipVerticalAction(),
            FlipHorizontalAction(),
            ]

    def get_actions_Menu_View_ViewPredefinedGroup(self):
        return []

    def get_actions_Menu_View_ViewChangeGroup(self):
        return [
            SMenu(
                Group(
                    ColorStandardAction(name="NTSC", color_standard=0),
                    ColorStandardAction(name="PAL", color_standard=1),
                    id="a0", separator=True),
                Group(
                    UseColorsAction(name="Powerup Colors", colors=colors.powerup_colors()),
                    id="a1", separator=True),
                Group(
                    AnticColorAction(),
                    id="a2", separator=True),
                id='mm4', separator=False, name="Colors"),
            ]

    def get_actions_Menu_Jumpman_LevelGroup(self):
        return [
            SMenu(
                LevelListGroup(id="a2", separator=True),
                id='segmentlist1', separator=False, name="Edit Level"),
            ]

    def get_actions_Menu_Jumpman_SelectionGroup(self):
        return [
            ClearTriggerAction(),
            SetTriggerAction(),
            ]

    def get_actions_Menu_Jumpman_CustomCodeGroup(self):
        return [
            AssemblySourceAction(),
            RecompileAction(),
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
