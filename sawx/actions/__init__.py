import time

import wx
import wx.lib.inspection

from ..action import SawxAction, SawxNameChangeAction, SawxListAction
from ..persistence import iter_templates
from ..ui.dialogs import prompt_for_dec, get_file_dialog_wildcard
from ..ui.prefs_dialog import PreferencesDialog
from ..ui.error_logger import show_logging_frame
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
    icon = "file"

    def calc_name(self, action_key):
        return "Open"

    def perform(self, action_key):
        frame = self.editor.frame
        path = frame.prompt_local_file_dialog()
        if path is not None:
            frame.load_file(path, self.editor)

class save_file(SawxAction):
    icon = "save"
    ext_list = [("All Documents", ".*")]

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
        path = e.frame.prompt_local_file_dialog("Save As", save=True, default_filename=e.document.name, wildcard=get_file_dialog_wildcard(self.ext_list))
        if path is not None:
            e.save_to_uri(path)

class save_as(save_file):
    def calc_name(self, action_key):
        return "Save As"

    def calc_enabled(self, action_key):
        return True

    perform = save_file.perform_prompt

class save_as_image(save_as):
    ext_list = [("PNG Images", ".png"), ("JPEG Images", ".jpg")]

    def calc_name(self, action_key):
        return "Save As Image"

    def perform(self, action_key):
        e = self.editor
        try:
            raw_data = e.get_numpy_image_before_prompt()
        except RuntimeError:
            # cancelled
            return
        path = e.frame.prompt_local_file_dialog("Save As Image", save=True, default_filename=e.document.root_name, wildcard=get_file_dialog_wildcard(self.ext_list))
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
        return "Invert Selection"

    def calc_enabled(self, action_key):
        return True

    def perform(self, action_key):
        self.editor.select_invert()

class prefs(SawxAction):
    def calc_name(self, action_key):
        return "Preferences"

    def perform(self, action_key):
        wx.GetApp().show_preferences_dialog(self.editor.frame, self.editor.ui_name)

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

class raise_exception(SawxAction):
    def calc_name(self, action_key):
        return "Raise Exception"

    def perform(self, action_key):
        val = int("this will raise a ValueError")

class test_progress(SawxAction):
    def calc_name(self, action_key):
        return "Test Progress Dialog"

    def perform(self, action_key):
        progress_log = logging.getLogger("progress")
        progress_log.info("START=First Test")
        try:
            progress_log.info("TITLE=Starting timer")
            for i in range(1000):
                print(i)
                progress_log.info("Trying %d" % i)
                for j in range(10):
                    time.sleep(.001)
                    wx.Yield()
                if i > 4:
                    progress_log.info("TIME_DELTA=Finished trying %d" % i)
                progress_log.info("PULSE")
                wx.Yield()

        except errors.ProgressCancelError as e:
            error = str(e)
        finally:
            progress_log.info("END")

class show_debug_log(SawxAction):
    def calc_name(self, action_key):
        return "View Error Log"

    def perform(self, action_key):
        show_logging_frame()

class widget_inspector(SawxAction):
    def calc_name(self, action_key):
        return "View Widget Inspector"

    def perform(self, action_key):
        wx.lib.inspection.InspectionTool().Show()

class show_focus(SawxAction):
    def calc_name(self, action_key):
        return "Show Control With Focus"

    def perform(self, action_key):
        focused = wx.Window.FindFocus()
        info = f"{focused.__class__.__name__}, {hex(id(focused))}, {focused.GetName()}, {focused.GetParent().GetName()}"
        print(info)
        self.editor.frame.status_message(info)
