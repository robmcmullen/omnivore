# Standard library imports.
import sys
import os

# Major package imports.
import wx
import numpy as np

# Enthought library imports.
from traits.api import Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides
from pyface.key_pressed_event import KeyPressedEvent

# Local imports.
from omnimon.tasks.hex_edit.hex_editor import HexEditor
from omnimon.framework.document import Document
from omnimon.utils.wx.bitviewscroller import FontMapScroller


class MapEditor(HexEditor):
    """ The toolkit specific implementation of a HexEditor.  See the
    IHexEditor interface for the API documentation.
    """
    
    antic_tile_map = Any
    
    ##### Default traits
    
    def _antic_tile_map_default(self):
        return [("trees", np.arange(26, 45, dtype=np.uint8)),
                ("roads", np.arange(50, 72, dtype=np.uint8)),
                ("buildings", np.arange(75, 80, dtype=np.uint8)),
                ]

    ###########################################################################
    # 'FrameworkEditor' interface.
    ###########################################################################

    def update_fonts(self):
        self.font_map.Refresh()
    
    def refresh_panes(self):
        self.control.recalc_view()
        self.memory_map.recalc_view()
        self.tile_map.recalc_view()
    
    ###########################################################################
    # Trait handlers.
    ###########################################################################


    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_control(self, parent):
        """ Creates the toolkit-specific control for the widget. """

        # Base-class constructor.
        print "CONSTRUCTOR!!!"
        self.control = self.font_map = FontMapScroller(parent, self.task, 40, 0)

        ##########################################
        # Events.
        ##########################################

        # Get related controls
        self.memory_map = self.window.get_dock_pane('map_edit.memory_map').control
        self.tile_map = self.window.get_dock_pane('map_edit.tile_map').control
        self.segment_list = self.window.get_dock_pane('map_edit.segments').control
        self.undo_history = self.window.get_dock_pane('map_edit.undo').control

        # Load the editor's contents.
        self.load()

        return self.control

    #### wx event handlers ####################################################
    
    def index_clicked(self, index, bit, control):
        if control != self.control:
            self.control.select_index(index)
        if control != self.memory_map:
            self.memory_map.select_index(index)
        self.can_copy = (self.anchor_start_index != self.anchor_end_index)
