import sys
import importlib
import inspect

import wx

from . import action
from . import errors

import logging
log = logging.getLogger(__name__)


class OmnivoreEditor:
    name = "simple_editor"

    menubar_desc = [
    ["File", "new_file", "open_file", None, "save_file", "save_as", None, "quit"],
    ["Edit", "undo", "redo", None, "copy", "cut", "paste", None, "prefs"],
    ["Help", "about"],
    ]

    toolbar_desc = [
        "new_file", "open_file", "save_file", None, "undo", "redo", None, "copy", "cut", "paste"
    ]

    module_search_order = ["omnivore_framework.actions"]

    tool_bitmap_size = (24, 24)

    @property
    def is_dirty(self):
        return not self.control.IsEmpty()

    @property
    def can_copy(self):
        return self.control.CanCopy()

    @property
    def can_paste(self):
        return self.control.CanPaste()

    @property
    def can_undo(self):
        return False

    @property
    def can_redo(self):
        return False

    def __init__(self, action_factory_lookup=None):
        self.title = "Sample Editor"
        self.tab_name = "Text"
        self.attached_to_frame = None
        if action_factory_lookup is None:
            action_factory_lookup = {}
        self.action_factory_lookup = action_factory_lookup

    def prepare_destroy(self):
        print(f"prepare_destroy: {self.tab_name}")
        self.control = None
        self.attached_to_frame = None

    def create_control(self, parent):
        return wx.TextCtrl(parent, -1, style=wx.TE_MULTILINE)

    def calc_usable_action(self, action_key):
        try:
            action_factory = self.action_factory_lookup[action_key]
        except KeyError:
            action_factory = None
            for mod in self.module_search_order:
                action_factory = action.find_action_factory(mod, action_key)
                if action_factory is not None:
                    break
            else:
                raise KeyError(f"no action factory found for {action_key}")
            self.action_factory_lookup[action_key] = action_factory
        return action_factory(self, action_key)
