from sawx.action import SawxAction, SawxListAction, SawxPersistentDictAction
from sawx import errors
from sawx.persistence import get_json_data, save_json_data


class layout_save(SawxAction):
    name = "Save Layout"

    def perform(self, action_key):
        label = self.editor.frame.prompt("Enter name for layout", "Save Layout")
        if label:
            layout = {}
            self.editor.serialize_session(layout, False)
            import pprint
            pprint.pprint(layout)

            layout_restore.add(label, layout)


class layout_restore(SawxPersistentDictAction):
    prefix = "layout_restore_"

    json_name = "tilemanager_layout"

    def get_layout(self, action_key):
        label = self.current_list[self.get_index(action_key)]
        return self.canonical_dict[label]

    def perform(self, action_key):
        layout = self.get_layout(action_key)
        self.editor.replace_layout(layout)
