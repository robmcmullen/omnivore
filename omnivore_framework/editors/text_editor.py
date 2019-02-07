import os

import wx

from omnivore_framework import OmnivoreEditor
from omnivore_framework.filesystem import fsopen as open

import logging
log = logging.getLogger(__name__)


class TextEditor(OmnivoreEditor):
    name = "text_editor"

    menubar_desc = [
    ["File", "new_file", "open_file", None, "save_file", "save_as", None, "quit"],
    ["Edit", "undo", "redo", None, "copy", "cut", "paste", None, "prefs"],
    ["Help", "about"],
    ]

    toolbar_desc = [
        "new_file", "open_file", "save_file", None, "undo", "redo", None, "copy", "cut", "paste"
    ]

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
        return self.control.CanUndo()

    @property
    def can_redo(self):
        return self.control.CanRedo()

    def create_control(self, parent):
        return wx.TextCtrl(parent, -1, style=wx.TE_MULTILINE)

    def load(self, path, mime_info):
        with open(path, 'r') as fh:
            text = fh.read()

        self.control.SetValue(text)
        self.tab_name = os.path.basename(path)

    @classmethod
    def can_edit_mime_exact(cls, mime_type):
        return mime_type == "text/plain"

    @classmethod
    def can_edit_mime_generic(cls, mime_type):
        return mime_type.startswith("text/")
