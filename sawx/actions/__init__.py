import wx

from ..action import SawxAction, SawxListAction
from ..templates import iter_templates
from ..ui.dialogs import prompt_for_dec

import logging
log = logging.getLogger(__name__)


class new_blank_file(SawxAction):
    prefix = "new_blank_file"

    def calc_name(self, action_key):
        return "Blank File"

    def perform(self, event=None):
        frame = self.editor.frame
        val = prompt_for_dec(frame, 'Enter file size in bytes', 'New Blank File', 256)
        if val > 256*256*16:
            if not frame.confirm(f"{val} bytes seems large. Are you sure you want to open a file this big?", "Confirm Large File"):
                val = 0
        if val is not None and val > 0:
            uri = "blank://%d" % val
            frame.load_file(uri)

class new_file_from_template(SawxListAction):
    prefix = "new_file_from_template_"

    canonical_list = None

    @classmethod
    def calc_list_items(cls):
        if cls.canonical_list is None:
            cls.canonical_list = cls.calc_canonical_list()
        return cls.canonical_list

    @classmethod
    def calc_canonical_list(cls):
        items = []
        for template in iter_templates("new file"):
            items.append(template)
        items.sort()
        return items

    def perform(self, action_key):
        frame = self.editor.frame
        item = self.get_item(action_key)
        frame.load_file(item["uri"])

class open_file(SawxAction):
    def calc_name(self, action_key):
        return "Open"

    def perform(self, action_key):
        frame = self.editor.frame
        path = frame.prompt_local_file_dialog()
        if path is not None:
            frame.load_file(path, self.editor)

class save_file(SawxAction):
    def calc_name(self, action_key):
        return "Save"

    def calc_enabled(self, action_key):
        return self.editor.is_dirty

    def perform(self, action_key):
        self.editor.save()

class save_as(SawxAction):
    def calc_name(self, action_key):
        return "Save As"

    def perform(self, action_key):
        self.editor.save_as()

class quit(SawxAction):
    def calc_name(self, action_key):
        return "Quit"

    def perform(self, action_key):
        wx.GetApp().quit()

class undo(SawxAction):
    def calc_name(self, action_key):
        return "Undo"

    def calc_enabled(self, action_key):
        return self.editor.can_undo

    def perform(self, action_key):
        self.editor.undo()

class redo(SawxAction):
    def calc_name(self, action_key):
        return "Redo"

    def calc_enabled(self, action_key):
        return self.editor.can_redo

    def perform(self, action_key):
        self.editor.redo()

class cut(SawxAction):
    def calc_name(self, action_key):
        return "Cut"

    def calc_enabled(self, action_key):
        return self.editor.can_copy

class copy(cut):
    def calc_name(self, action_key):
        return "Copy"

class paste(SawxAction):
    def calc_name(self, action_key):
        return "Paste"

    def calc_enabled(self, action_key):
        return self.editor.can_paste

class prefs(SawxAction):
    def calc_name(self, action_key):
        return "Preferences"

class about(SawxAction):
    def calc_name(self, action_key):
        return "About"

    def perform(self, action_key):
        wx.GetApp().show_about_dialog()

class prev_line(SawxAction):
    def calc_name(self, action_key):
        return "Previous Line"

    def perform(self, action_key):
        print("Up!")

class next_line(SawxAction):
    def calc_name(self, action_key):
        return "Next Line"

    def perform(self, action_key):
        print("Down!")

class prev_char(SawxAction):
    def calc_name(self, action_key):
        return "Previous Char"

    def perform(self, action_key):
        print("Left!")

class next_char(SawxAction):
    def calc_name(self, action_key):
        return "Next Char"

    def perform(self, action_key):
        print("Right!")
