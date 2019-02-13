# Standard library imports.
import sys
import os
import functools

# Major package imports.
import wx
import numpy as np

# Enthought library imports.
from traits.api import on_trait_change, Any, Bool, Int, Str, List, Event, Enum, Instance, File, Unicode, Property, provides, Undefined, CArray

# Local imports.
from omnivore_framework.utils.command import Overlay
from ..utils.drawutil import get_bounds
from omnivore_framework.utils.sortutil import invert_rects, rect_ranges_to_indexes
#import omnivore_framework.framework.actions as fa
from ..byte_edit.commands import ChangeByteCommand
from ..clipboard_commands import PasteCommand, PasteRectCommand

from .char2 import CharViewer
from .map_commands import *
from . import mouse_modes as m

import logging
log = logging.getLogger(__name__)


class MapViewer(CharViewer):
    name = "map"

    pretty_name = "Map"

    valid_mouse_modes = [m.RectangularSelectMode, m.EyedropperMode, m.DrawMode, m.LineMode, m.SquareMode, m.FilledSquareMode]

    default_mouse_mode_cls = m.RectangularSelectMode

    draw_pattern = CArray(dtype=np.uint8, value=(0,))

    @property
    def window_title(self):
        return "Map: " + self.machine.font_renderer.name + ", " + self.machine.font_mapping.name + ", " + self.machine.color_standard_name

    ##### Selections

    def highlight_selected_ranges_in_segment(self, selected_ranges, segment):
        # This is default implementation which simply highlights everything
        # between the start/end values of each range. Other selection types
        # (rectangular selection) will need to be defined in the subclass
        segment.set_style_ranges_rect(selected_ranges, self.control.items_per_row, selected=True)

    ##### Clipboard & Copy/Paste

    @property
    def clipboard_data_format(self):
        return "numpy,columns"

    def get_paste_command(self, serialized_data, *args, **kwargs):
        print(serialized_data)
        print((serialized_data.source_data_format_name))
        if serialized_data.source_data_format_name == "numpy,columns":
            cmd_cls = PasteRectCommand
        cmd_cls = PasteCommand
        return cmd_cls(self.segment, serialized_data, *args, **kwargs)

    ##### Drawing pattern

    def set_draw_pattern(self, value):
        log.debug("new draw pattern: %s" % str(value))
        self.draw_pattern = np.asarray([value], dtype=np.uint8)

    #### popup menus

    def common_popup_actions(self):
        return [fa.CutAction, fa.CopyAction, fa.PasteAction, None, fa.SelectAllAction, fa.SelectNoneAction, fa.SelectInvertAction]
