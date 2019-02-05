import importlib

import wx

from . import art

import logging
log = logging.getLogger(__name__)


global_action_ids = {
    "about": wx.ID_ABOUT,
    "quit": wx.ID_EXIT,
    "prefs": wx.ID_PREFERENCES,
    "new_file": wx.ID_NEW,
    "open_file": wx.ID_OPEN,
    "save_file": wx.ID_SAVE,
    "save_as": wx.ID_SAVEAS,
    "copy": wx.ID_COPY,
    "cut": wx.ID_CUT,
    "paste": wx.ID_PASTE,
    "undo": wx.ID_UNDO,
    "redo": wx.ID_REDO,
}


def get_action_id(action_key):
    global global_action_ids

    try:
        id = global_action_ids[action_key]
    except KeyError:
        id = wx.NewId()
        global_action_ids[action_key] = id
    return id

def find_action_factory(mod_root, action_key):
    for ext in [f".{action_key}", ""]:
        mod_name = f"{mod_root}{ext}"
        log.debug(f"searching in {mod_name} for 'action_factory'")
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            log.debug(f"no module {mod_name}")
        else:
            try:
                factory = mod.action_factory
            except AttributeError:
                pass
            else:
                log.debug(f"found callable action_factory in {mod_name}")
                return factory
            log.debug(f"searching in {mod_name} for '{action_key}'")
            try:
                factory = getattr(mod, action_key)
            except AttributeError:
                log.debug(f"no callable {action_key} in {mod_name}")
            else:
                log.debug(f"found callable {action_key} in {mod_name}")
                return factory
        

class OmnivoreAction:
    def __init__(self, editor, action_key):
        self.editor = editor
        self.init_from_editor()

    def calc_menu_sub_keys(self, action_key):
        """Return any dynamically created action_keys

        Actions that create multiple entries in the menubar/toolbar must create
        unique action_keys here."""
        raise AttributeError("this action has no dynamically created sub-actions")

    def append_to_menu(self, menu, id, action_key):
        menu.Append(id, self.calc_name(action_key))

    def append_to_toolbar(self, tb, id, action_key):
        name = self.calc_name(action_key)
        tb.AddTool(id, name, self.calc_bitmap(action_key), wx.NullBitmap, wx.ITEM_NORMAL, name, f"Long help for '{name}'", None)

    def calc_bitmap(self, action_key):
        art_id = art.get_art_id(action_key)
        return wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR, self.editor.tool_bitmap_size)

    def init_from_editor(self):
        pass

    def sync_menu_item_from_editor(self, action_key, menu_item):
        pass

    def sync_tool_item_from_editor(self, action_key, toolbar_control, id):
        pass

class OmnivoreActionRadioMixin:
    def append_to_menu(self, menu, id, action_key):
        menu.AppendRadioItem(id, self.calc_name(action_key))

    def append_to_toolbar(self, tb, id, action_key):
        name = self.calc_name(action_key)
        tb.AddTool(id, name, self.calc_bitmap(action_key), wx.NullBitmap, wx.ITEM_RADIO, name, f"Long help for '{name}'", None)
