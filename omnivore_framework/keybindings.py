import collections

import wx

from .action import get_action_id

import logging
log = logging.getLogger(__name__)


class KeyBindingActionMixin:
    keybinding_desc = None

    def calc_usable_action(self, action_key):
        pass


class KeyBindingDescription:
    """Class that Holds a mapping of keystrokes to actions

    Takes an instance of a KeyBindingActionMixin, which defines the keybinding
    mapping and a lookup function.

    The keybinding description in the form of a dictionary mapping of a text
    string that represents the name of the action to a text string representing
    an accelerator key combination.

    The action name will be searched for using the calc_usable_action method of
    the source.

    For example:

        keybinding_desc = {
            "new_file": "Ctrl+N",
            "open_file": "Ctrl+O",
            "save_file" : "Ctrl+S",
            "save_as" : "Shift+Ctrl+S",
            "cut": "Ctrl+X",
            "copy": "Ctrl+C",
            "paste": "Ctrl+V",
        }

    If an id mapping is specified, the action ID will be computed to see if the
    action is already in a menubar, and if so will not create a keybinding for
    it. The key will already have been processed by the menu accelerator.
    """
    def __init__(self, source, valid_id_map=None):
        entries = {}
        for action_key, text in source.keybinding_desc.items():
            a = wx.AcceleratorEntry()
            a.FromString(text)
            # print(f"{a.ToString()}: {action_key} flags={a.GetFlags()} keycode={a.GetKeyCode()}")
            if a.IsOk():
                try:
                    action = source.calc_usable_action(action_key)
                except KeyError:
                    log.debug(f"action {action_key} not used in this source")
                    pass
                else:
                    if valid_id_map is not None:
                        id = get_action_id(action_key)
                        if id not in valid_id_map:
                            entries[(a.GetFlags(), a.GetKeyCode())] = (action_key, action)
                        else:
                            log.debug(f"action {action_key} already in menubar: id={id}")
            else:
                log.error("Invalid key binding {text} for {action_key} in {source.name}")
        self.valid_key_map = entries
