import collections

import wx

from .action import get_action_id

import logging
log = logging.getLogger("keybindings")


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
        try:
            desc = source.keybinding_desc.items()
        except AttributeError:
            log.debug(f"No keybinding description found in {source}")
        else:
            for action_key, text in source.keybinding_desc.items():
                if not text:
                    continue
                a = wx.AcceleratorEntry()
                a.FromString(text)
                # print(f"{a.ToString()}: {action_key} flags={a.GetFlags()} keycode={a.GetKeyCode()}")
                if a.IsOk():
                    try:
                        action = source.calc_usable_action(action_key)
                    except KeyError:
                        log.debug(f"action {action_key} not used in source {source}")
                        pass
                    else:
                        key_id = (a.GetFlags(), a.GetKeyCode())
                        if valid_id_map is not None:
                            id = get_action_id(action_key)
                            if id in valid_id_map:
                                log.debug(f"action {action_key} already in menubar: id={id}")
                                key_id = None
                        if key_id is not None:
                            entries[key_id] = (action_key, action)
                else:
                    log.error(f"Invalid key binding {text} for {action_key} in {source.name}")
        self.valid_key_map = entries

    def __str__(self):
        e = self.valid_key_map
        # return "\n".join([f"{key_id}: {e[key_id][0]}->{e[key_id][1]}" for key_id in sorted(e.keys())]) + "\n"
        return str(self.valid_key_map)


class KeyBindingControlMixin:
    """Mixin for a wx control to provide EVT_CHAR handling to map keystrokes to
    method calls

    Uses the same keybinding handling in `KeyBindingDescription`, but instead
    of looking for actions in modules, looks for actions as methods of the
    control.
    """
    keybinding_desc = None

    def __init__(self):
        wx.GetApp().keybindings_changed_event += self.on_keybindings_changed
        self.create_control_keybindings()
        self.map_char_events()

    def on_keybindings_changed(self, evt):
        log.warning(f"global keybindings have changed; rebuilding keybindings for {self}")
        self.create_control_keybindings()

    def create_control_keybindings(self):
        self.keybindings = KeyBindingDescription(self)
        log.debug(f"keybindings for {self}: {self.keybindings}")

    def calc_usable_action(self, action_key):
        """Returns the method named `action_key` from this control, if it
        exists
        """
        log.debug(f"looking for {action_key} in {self.keybinding_desc}")
        try:
            return getattr(self, action_key)
        except AttributeError as e:
            raise KeyError(e)

    def map_char_events(self, source=None):
        if source is None:
            source = self
        source.Bind(wx.EVT_CHAR, self.on_char)
        source.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

    def on_key_down(self, evt):
        key = evt.GetKeyCode()
        mods = evt.GetModifiers()
        key_id = (mods, key)
        log.debug("char_event_mixin: on_key_down speficier=%s" % str(key_id))
        evt.Skip()

    def on_char(self, evt):
        key_id = (evt.GetModifiers(), evt.GetKeyCode())
        log.debug(f"on_char: key: {key_id}")
        try:
            action_key, action = self.keybindings.valid_key_map[key_id]
        except KeyError as e:
            log.debug(f"on_char: key id {key_id} not found in {self.keybindings}")
            self.do_char_ordinary(evt)
        else:
            log.debug(f"on_char: calling action {action}")
            self.do_char_action(evt, action)

    def do_char_action(self, evt, action):
        action(evt)

    def do_char_ordinary(self, evt):
        key = evt.GetKeyCode()
        mods = evt.GetModifiers()
        log.debug("No handler for keyboard event: key=%d mods=%d" % (key, mods))
        evt.Skip()
