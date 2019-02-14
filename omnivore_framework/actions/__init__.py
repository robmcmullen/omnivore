import wx

from ..action import OmnivoreAction

import logging
log = logging.getLogger(__name__)


class new_file(OmnivoreAction):
    def calc_name(self, action_key):
        return "&New"

    def perform(self, action_key):
        new_editor = self.editor.__class__()
        self.editor.frame.add_editor(new_editor)

class open_file(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Open"

    def perform(self, action_key):
        frame = self.editor.frame
        path = frame.prompt_local_file_dialog()
        if path is not None:
            frame.load_file(path, self.editor)

class save_file(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Save"

    def calc_enabled(self, action_key):
        return self.editor.is_dirty

class save_as(OmnivoreAction):
    def calc_name(self, action_key):
        return "Save &As"

class quit(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Quit"

    def perform(self, action_key):
        wx.GetApp().quit()

class undo(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Undo"

    def calc_enabled(self, action_key):
        return self.editor.can_undo

class redo(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Redo"

    def calc_enabled(self, action_key):
        return self.editor.can_redo

class cut(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Cut"

    def calc_enabled(self, action_key):
        return self.editor.can_copy

class copy(cut):
    def calc_name(self, action_key):
        return "&Copy"

class paste(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Paste"

    def calc_enabled(self, action_key):
        return self.editor.can_paste

class prefs(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Preferences"

class about(OmnivoreAction):
    def calc_name(self, action_key):
        return "&About"

    def perform(self, action_key):
        wx.GetApp().show_about_dialog()
