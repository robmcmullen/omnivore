import wx

from ..action import SawxAction, SawxNameChangeAction, SawxListAction
from ..persistence import iter_templates
from ..ui.dialogs import prompt_for_dec, get_file_dialog_wildcard
from ..ui.prefs_dialog import PreferencesDialog
from .. import errors

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
        e = self.editor
        try:
            e.save_to_uri()
        except errors.ReadOnlyFilesystemError:
            self.perform_prompt(action_key)

    def perform_prompt(self, action_key):
        e = self.editor
        path = e.frame.prompt_local_file_dialog("Save As", save=True, default_filename=e.document.name, wildcard=get_file_dialog_wildcard("MapRoom Project Files", [".maproom"]))
        if path is not None:
            e.save_to_uri(path)

class save_as(save_file):
    def calc_name(self, action_key):
        return "Save As"

    def calc_enabled(self, action_key):
        return True

    perform = save_file.perform_prompt

class save_as_image(save_as):
    def calc_name(self, action_key):
        return "Save As Image"

    def perform(self, action_key):
        e = self.editor
        try:
            raw_data = e.get_numpy_image_before_prompt()
        except RuntimeError:
            # cancelled
            return
        path = e.frame.prompt_local_file_dialog("Save As Image", save=True, default_filename=e.document.root_name, wildcard=get_file_dialog_wildcard("Images", [".png", ".jpg"]))
        if path is not None:
            e.save_as_image(path, raw_data)

class quit(SawxAction):
    def calc_name(self, action_key):
        return "Quit"

    def perform(self, action_key):
        wx.GetApp().quit()

class undo(SawxNameChangeAction):
    def calc_name(self, action_key):
        command = self.editor.document.undo_stack.get_undo_command()
        if command is None:
            label = "Undo"
        else:
            text = str(command).replace("&", "&&")
            label = "Undo: " + text
        return label

    def calc_enabled(self, action_key):
        return self.editor.document.undo_stack.can_undo

    def perform(self, action_key):
        self.editor.undo()

class redo(SawxNameChangeAction):
    def calc_name(self, action_key):
        command = self.editor.document.undo_stack.get_redo_command()
        if command is None:
            label = "Redo"
        else:
            text = str(command).replace("&", "&&")
            label = "Redo: " + text
        return label

    def calc_enabled(self, action_key):
        return self.editor.document.undo_stack.can_redo

    def perform(self, action_key):
        self.editor.redo()

class cut(SawxAction):
    def calc_name(self, action_key):
        return "Cut"

    def calc_enabled(self, action_key):
        return self.editor.can_cut

    def perform(self, action_key):
        self.editor.copy_selection_to_clipboard()
        self.editor.delete_selection()

class copy(cut):
    def calc_name(self, action_key):
        return "Copy"

    def perform(self, action_key):
        self.editor.copy_selection_to_clipboard()

class paste(SawxAction):
    def calc_name(self, action_key):
        return "Paste"

    def calc_enabled(self, action_key):
        return self.editor.can_paste

    def perform(self, action_key):
        self.editor.paste_clipboard()

class delete_selection(SawxAction):
    def calc_name(self, action_key):
        return "Delete Selection"

    def calc_enabled(self, action_key):
        return self.editor.can_cut

    def perform_as_keystroke(self, action_key):
        if self.calc_enabled(action_key):
            self.perform(action_key)
        else:
            raise errors.ProcessKeystrokeNormally("No selection")

    def perform(self, action_key):
        self.editor.delete_selection()

class select_all(SawxAction):
    def calc_name(self, action_key):
        return "Select All"

    def calc_enabled(self, action_key):
        return True

    def perform(self, action_key):
        self.editor.select_all()

class select_none(SawxAction):
    def calc_name(self, action_key):
        return "Select None"

    def calc_enabled(self, action_key):
        return True

    def perform(self, action_key):
        self.editor.select_none()

class select_invert(SawxAction):
    def calc_name(self, action_key):
        return "Select Invert"

    def calc_enabled(self, action_key):
        return True

    def perform(self, action_key):
        self.editor.select_invert()

class prefs(SawxAction):
    def calc_name(self, action_key):
        return "Preferences"

    def perform(self, action_key):
        wx.GetApp().show_preferences_dialog(self.editor.frame)

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
