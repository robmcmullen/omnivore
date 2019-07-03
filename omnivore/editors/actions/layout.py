from sawx.action import SawxAction, SawxListAction, SawxPersistentDictAction
from sawx import errors
from sawx.persistence import get_json_data, save_json_data


class layout_save(SawxAction):
    name = "Save Layout"

    def save_layout(self, label, layout):
        layout_restore.add(label, layout)

    def perform(self, action_key):
        label = self.editor.frame.prompt("Enter name for layout", "Save Layout")
        if label:
            layout = {}
            self.editor.serialize_session(layout, False)
            self.save_layout(label, layout)


class layout_restore(SawxPersistentDictAction):
    prefix = "layout_restore_"

    json_name = "tilemanager_layouts"

    def get_layout(self, action_key):
        label = self.current_list[self.get_index(action_key)]
        d = self.get_dict()
        return d[label]

    def perform(self, action_key):
        layout = self.get_layout(action_key)
        self.editor.replace_layout(layout)


class layout_save_emu(layout_save):
    name = "Save Emulator Layout"

    def save_layout(self, label, layout):
        layout_restore_emu.add(label, layout)


class layout_restore_emu(layout_restore):
    prefix = "layout_restore_emu_"

    json_name = "tilemanager_emulator_layouts"

    def perform(self, action_key):
        doc = self.editor.document
        doc.pause_emulator()
        try:
            layout_restore.perform(self, action_key)
        finally:
            doc.resume_emulator()
