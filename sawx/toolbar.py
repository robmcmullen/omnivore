import collections

import wx

from .action import get_action_id

import logging
log = logging.getLogger("toolbar")
sync_log = logging.getLogger("sync-toolbar")


class ToolbarDescription:
    def __init__(self, parent, editor):
        tb = parent.raw_toolbar
        tb.ClearTools()
        self.valid_id_map = collections.OrderedDict()
        for action_key in editor.toolbar_desc:
            if action_key is None:
                tb.AddSeparator()
            else:
                if action_key.startswith("-"):
                    tb.AddSeparator()
                else:
                    # usable_actions limit the visible actions to what the current editor supports
                    try:
                        action = editor.calc_usable_action(action_key)
                    except KeyError as e:
                        log.debug(f"action {action_key} not used in this editor: {e}")
                        pass
                    else:
                        # a single action can create multiple entries
                        try:
                            action_keys = action.calc_tool_sub_keys(editor)
                            log.debug(f"action {action_key} created subkeys {action_keys}")
                        except AttributeError:
                            action_keys = [action_key]
                        for action_key in action_keys:
                            id = get_action_id(action_key)
                            self.valid_id_map[id] = (action_key, action)
                            action.append_to_toolbar(tb, id, action_key)

    def sync_with_editor(self, toolbar_control):
        for id, (action_key, action) in self.valid_id_map.items():
            sync_log.debug(f"syncing tool {id}: {action_key}, {action}")
            item = toolbar_control.FindById(id)
            try:
                action.sync_tool_item_from_editor(action_key, toolbar_control, id)
            except AttributeError as e:
                sync_log.debug(f"Skipping sync of {action_key} toolbar item from {action.editor}: {e}")
