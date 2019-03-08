import os

import wx

from ..editor import SawxEditor
from ..document import BaseDocument
from ..filesystem import fsopen as open
from ..keybindings import KeyBindingControlMixin

import logging
log = logging.getLogger(__name__)


class TextEditorControl(KeyBindingControlMixin, wx.TextCtrl):
    keybinding_desc = {
        "prev_line": "Up",
        "next_line": "Down",
        "prev_char": "Left",
        "next_char": "Right",
    }

    def __init__(self, *args, **kwargs):
        wx.TextCtrl.__init__(self, *args, **kwargs)
        KeyBindingControlMixin.__init__(self)

    def prev_line(self, evt):
        print("prev_line")

    def next_line(self, evt):
        print("next_line")

    def prev_char(self, evt):
        print("prev_char")

    def next_char(self, evt):
        print("next_char")


class TextDocument(BaseDocument):
    def __init__(self, uri):
        super().__init__("")
        self.mime = "text/plain"
        if uri:
            self.load_from_uri(uri)

    def load_from_uri(self, uri):
        with open(uri, 'r') as fh:
            text = fh.read()
        self.raw_data = self.calc_raw_data(text)
        self.uri = uri

    def calc_raw_data(self, raw):
        return str(raw)

    def calc_raw_data_to_save(self):
        return self.raw_data

    def save_raw_data(self, uri, raw_data):
        fh = open(uri, 'w')
        log.debug("saving to %s" % uri)
        fh.write(raw_data)
        fh.close()


class TextEditor(SawxEditor):
    name = "text_editor"

    @property
    def is_dirty(self):
        return self.control.IsModified()

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
        return TextEditorControl(parent, -1, style=wx.TE_MULTILINE)

    def create_event_bindings(self):
        self.control.Bind(wx.EVT_CONTEXT_MENU, self.on_popup)

    def load(self, path, file_metadata, args=None):
        self.document = TextDocument(path)

        self.control.SetValue(self.document.raw_data)
        if args is not None:
            size = int(args.get('size', -1))
            if size > 0:
                font = self.control.GetFont()
                font.SetPointSize(size)
                self.control.SetFont(font)
        self.control.DiscardEdits()

    def save(self):
        self.document.raw_data = self.control.GetValue()
        super().save()
        self.control.DiscardEdits()

    @classmethod
    def can_edit_file_exact(cls, file_metadata):
        return file_metadata['mime'] == "text/plain"

    @classmethod
    def can_edit_file_generic(cls, file_metadata):
        return file_metadata['mime'].startswith("text/")

    def on_popup(self, evt):
        popup_menu_desc = [
            "undo",
            "redo",
            None,
            "copy",
            "cut",
            "paste",
        ]
        self.show_popup(popup_menu_desc)


class DebugTextEditor(TextEditor):
    name = "debug"

    menubar_desc = [
        ["File",
            ["New",
                "new_file",
            ],
            "open_file",
            ["Open Recent",
                "open_recent",
            ],
            None,
            "save_file",
            "save_as",
            None,
            "quit",
        ],
        ["Edit",
            "undo",
            "redo",
            None,
            "copy",
            "cut",
            "paste",
            ["Paste Special",
                "paste_as_text",
                "paste_as_hex",
            ],
            None,
            "select_all",
            "select_none",
            "select_invert",
            None,
            "prefs",
        ],
        ["Debug",
            None,
            None,
            None,
            "debug_text_counting",
            None,
            None,
            None,
            "debug_text_last_digit",
            None,
            "debug_text_size",
        ],
        ["Dynamic",
            "debug_text_last_digit_dyn",
        ],
        ["Help",
            "about",
        ],
    ]

    toolbar_desc = [
    "new_file", "open_file", "save_file", None, "undo", "redo", None, "copy", "cut", "paste", "paste_as_text", "paste_as_hex",
    ]

    keybinding_desc = {
        "new_file": "Ctrl+N",
        "open_file": "Ctrl+O",
        "save_file" : "Ctrl+S",
        "save_as" : "Shift+Ctrl+S",
        "cut": "Ctrl+X",
        "copy": "Ctrl+C",
        "paste": "Ctrl+V",
    }

    @property
    def tab_name(self):
        return "DEBUG " + super().tab_name

    # won't automatically match anything; must force this editor with the -t
    # command line flag
    @classmethod
    def can_edit_file_exact(cls, file_metadata):
        return False

    @classmethod
    def can_edit_file_generic(cls, file_metadata):
        return file_metadata['mime'].startswith("text/")
