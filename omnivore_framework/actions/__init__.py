import wx

from ..action import OmnivoreAction

import logging
log = logging.getLogger(__name__)


class new_file(OmnivoreAction):
    def calc_name(self, action_key):
        return "&New"

    def execute(self, action_key):
        new_editor = self.editor.__class__()
        self.editor.frame.add_editor(new_editor)

class open_file(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Open"

    def execute(self, action_key):
        frame = self.editor.frame
        path = frame.prompt_local_file_dialog()
        if path is not None:
            frame.load_file(path, self.editor)

class save_file(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Save"

    def sync_menu_item_from_editor(self, action_key, menu_item):
        menu_item.Enable(self.editor.is_dirty)

class save_as(OmnivoreAction):
    def calc_name(self, action_key):
        return "Save &As"

class quit(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Quit"

    def execute(self, action_key):
        wx.GetApp().quit()

class undo(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Undo"

    def sync_menu_item_from_editor(self, action_key, menu_item):
        menu_item.Enable(self.editor.can_undo)

    def sync_tool_item_from_editor(self, action_key, toolbar_control, id):
        toolbar_control.EnableTool(id, self.editor.can_undo)

class redo(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Redo"

    def sync_menu_item_from_editor(self, action_key, menu_item):
        menu_item.Enable(self.editor.can_redo)

    def sync_tool_item_from_editor(self, action_key, toolbar_control, id):
        toolbar_control.EnableTool(id, self.editor.can_redo)

class cut(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Cut"

    def sync_menu_item_from_editor(self, action_key, menu_item):
        menu_item.Enable(self.editor.can_copy)

    def sync_tool_item_from_editor(self, action_key, toolbar_control, id):
        state = self.editor.can_copy
        log.debug(f"tool item {id}, {state}, {self.editor.tab_name}")
        toolbar_control.EnableTool(id, state)

class copy(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Copy"

    def sync_menu_item_from_editor(self, action_key, menu_item):
        menu_item.Enable(self.editor.can_copy)

    def sync_tool_item_from_editor(self, action_key, toolbar_control, id):
        state = self.editor.can_copy
        log.debug(f"tool item {id}, {state}, {self.editor.tab_name}")
        toolbar_control.EnableTool(id, state)

class paste(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Paste"

    def sync_menu_item_from_editor(self, action_key, menu_item):
        menu_item.Enable(self.editor.can_paste)

    def sync_tool_item_from_editor(self, action_key, toolbar_control, id):
        state = self.editor.can_paste
        log.debug(f"tool item {id}, {state}, {self.editor.tab_name}")
        toolbar_control.EnableTool(id, state)

class prefs(OmnivoreAction):
    def calc_name(self, action_key):
        return "&Preferences"

class about(OmnivoreAction):
    def calc_name(self, action_key):
        return "&About"

    def execute(self, action_key):
        wx.GetApp().show_about_dialog()
