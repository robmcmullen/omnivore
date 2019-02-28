import collections

import wx

from .action import get_action_id

import logging
log = logging.getLogger(__name__)


class MenuDescription:
    def __init__(self, desc, editor, valid_id_map, keybinding_desc):
        self.menu = wx.Menu()
        log.debug(f"adding menu {desc}")
        self.name = desc[0]
        allow_separator = False
        for action_key in desc[1:]:
            if action_key is None:
                if allow_separator:
                    self.menu.AppendSeparator()
                    allow_separator = False
            elif str(action_key) == action_key:
                if action_key.startswith("-"):
                    if allow_separator:
                        self.menu.AppendSeparator()
                        allow_separator = False
                else:
                    # usable_actions limit the visible actions to what the current editor supports
                    try:
                        action = editor.calc_usable_action(action_key)
                    except KeyError:
                        log.debug(f"action {action_key} not used in this editor")
                        pass
                    else:
                        # a single action can create multiple entries
                        try:
                            action_keys = action.calc_menu_sub_keys(editor)
                            log.debug(f"action {action_key} created subkeys {action_keys}")
                        except AttributeError:
                            action_keys = [action_key]
                        for action_key in action_keys:
                            id = get_action_id(action_key)
                            valid_id_map[id] = (action_key, action)
                            action.append_to_menu(self.menu, id, action_key)
                            try:
                                accel_text = keybinding_desc[action_key]
                            except KeyError:
                                pass
                            else:
                                if accel_text:
                                    accel_entry = wx.AcceleratorEntry()
                                    accel_entry.FromString(accel_text)
                                    menu_item = self.menu.FindItemById(id)
                                    try:
                                        menu_item.SetAccel(accel_entry)
                                    except Exception:
                                        log.error(f"Invalid key binding {accel_text} for {action_key}")
                            allow_separator = True
            else:
                submenu = MenuDescription(action_key, editor, valid_id_map, keybinding_desc)
                if submenu.count > 0:
                    self.menu.AppendSubMenu(submenu.menu, submenu.name)
                    allow_separator = True

    @property
    def count(self):
        return self.menu.GetMenuItemCount()


class MenubarDescription:
    def __init__(self, parent, editor):
        self.menus = []
        self.valid_id_map = collections.OrderedDict()
        num_old_menus = parent.raw_menubar.GetMenuCount()
        num_new_menus = 0
        for desc in editor.menubar_desc:
            menu = MenuDescription(desc, editor, self.valid_id_map, editor.keybinding_desc)
            if menu.count > 0:
                if num_new_menus < num_old_menus:
                    parent.raw_menubar.Replace(num_new_menus, menu.menu, menu.name)
                else:
                    parent.raw_menubar.Append(menu.menu, menu.name)
                self.menus.append(menu)
                num_new_menus += 1
        while num_new_menus < num_old_menus:
            parent.raw_menubar.Remove(num_new_menus)
            num_old_menus -= 1

    def sync_with_editor(self, menubar_control):
        for id, (action_key, action) in self.valid_id_map.items():
            log.debug(f"syncing {id}: {action_key}, {action}")
            menu_item = menubar_control.FindItemById(id)
            try:
                action.sync_menu_item_from_editor(action_key, menu_item)
            except AttributeError as e:
                log.warning(f"Skipping sync of {action_key} menu item from {action.editor}: {e}")
