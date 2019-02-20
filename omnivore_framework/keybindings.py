import collections

import wx

from .action import get_action_id

import logging
log = logging.getLogger(__name__)


class KeyBindingDescription:
    def __init__(self, editor):
        entries = {}
        for action_key, text in editor.keybinding_desc.items():
            a = wx.AcceleratorEntry()
            a.FromString(text)
            # print(f"{a.ToString()}: {action_key} flags={a.GetFlags()} keycode={a.GetKeyCode()}")
            if a.IsOk():
                try:
                    action = editor.calc_usable_action(action_key)
                except KeyError:
                    log.debug(f"action {action_key} not used in this editor")
                    pass
                else:
                    id = get_action_id(action_key)
                    if id not in editor.frame.menubar.valid_id_map:
                        entries[(a.GetFlags(), a.GetKeyCode())] = (action_key, action)
                    else:
                        log.debug(f"action {action_key} already in menubar: id={id}")
            else:
                log.error("Invalid key binding {text} for {action_key} in {editor.name}")
        self.valid_key_map = entries
