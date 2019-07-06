import os

import wx

from ..editor import SawxEditor
from ..filesystem import fsopen as open
from ..keybindings import KeyBindingControlMixin
from ..preferences import SawxEditorPreferences

import logging
log = logging.getLogger(__name__)


class TextEditorControl(KeyBindingControlMixin, wx.TextCtrl):
    # FIXME: is this second level of keyboard processing necessary now that the
    # on_char_hook event raises a ProcessKeystrokeNormally error, allowing the
    # control to process that keytroke?
    keybinding_desc = {
        "prev_line": "Up",
        "next_line": "Down",
        "prev_char": "Left",
        "next_char": "Right",
        "delete_selection": "Delete",
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

    def delete_selection(self, evt):
        print("delete_selection")


class TextEditorPreferences(SawxEditorPreferences):
    pass


class TextEditor(SawxEditor):
    editor_id = "text_editor"

    ui_name = "Text Editor"

    preferences_module = "sawx.editors.text_editor"

    @property
    def is_dirty(self):
        return self.control.IsModified()

    @property
    def can_copy(self):
        return self.control.CanCopy()

    @property
    def can_undo(self):
        return self.control.CanUndo()

    @property
    def can_redo(self):
        return self.control.CanRedo()

    def create_control(self, parent):
        # return TextEditorControl(parent, -1, style=wx.TE_MULTILINE)
        return wx.TextCtrl(parent, -1, style=wx.TE_MULTILINE)

    def create_event_bindings(self):
        self.control.Bind(wx.EVT_CONTEXT_MENU, self.on_popup)

    def show(self, args=None):
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
    def can_edit_document_exact(cls, document):
        return document.mime == "text/plain"

    @classmethod
    def can_edit_document_generic(cls, document):
        return document.mime.startswith("text/")

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

    #### selection

    def select_all(self):
        self.control.SelectAll()

    def select_none(self):
        self.control.SelectNone()

    def select_invert(self):
        start, end = self.control.GetSelection()
        if start == end:
            self.control.SelectAll()
        elif start == 0 and end == self.control.GetLastPosition():
            self.control.SelectNone()
        else:
            # need to implement multi-select here
            pass

    #### copy/paste stuff

    supported_clipboard_handlers = [
        (wx.TextDataObject(), "paste_text_control"),
    ]

    def delete_selection_from(self, focused):
        start, end = focused.GetSelection()
        focused.Remove(start, end)


class DebugTextEditor(TextEditor):
    editor_id = "debug"

    ui_name = "Debug Text Editor"

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
        ["Generated",
            "debug_gen_sub_menu()",
            None,
            "debug_generated{1}",
            "debug_generated{34}",
            "debug_generated{whatever}",
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
        "prev_line": "Up",
        "next_line": "Down",
        "prev_char": "Left",
        "next_char": "Right",
        "delete_selection": "Delete",
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

    def debug_gen_sub_menu(self):
        return [
            ["Sub Menu 1", "about", ["Sub Sub Menu 1!", "about"]],
            ["Sub Menu 2", "about", "about",],
            ["Sub Menu 3", "about", "about", "about", "debug_gen_sub_sub_menu()"],
            ["Sub Menu 4", "about", "about", "about", "debug_gen_sub_sub_menu(5)"],
        ]

    def debug_gen_sub_sub_menu(self, count="2"):
        menu = ["Sub Sub Menu 2!"]
        count = int(count)
        for i in range(count):
            menu.append("about")
        return [menu]
