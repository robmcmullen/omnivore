from ..action import SawxListAction
from .. import errors
from ..persistence import get_json_data, save_json_data

class open_recent(SawxListAction):
    prefix = "open_recent_"

    max_entries = 20

    canonical_list = None

    @classmethod
    def reload(cls):
        data = get_json_data("recent_files", [])
        cls.canonical_list = data

    @classmethod
    def append(cls, uri):
        if cls.canonical_list is None:
            cls.reload()
        try:
            index = cls.canonical_list.index(uri)
            cls.canonical_list.pop(index)
        except ValueError:
            pass
        cls.canonical_list[0:0] = [uri]
        if len(cls.canonical_list) > cls.max_entries:
            cls.canonical_list = cls.canonical_list[:cls.max_entries]
        save_json_data("recent_files", cls.canonical_list)

    def calc_list_items(self):
        if self.canonical_list is None:
            self.reload()
        return self.canonical_list[:]

    def get_path(self, action_key):
        return self.current_list[self.get_index(action_key)]

    def sync_menu_item_from_editor(self, action_key, menu_item):
        if self.current_list != self.canonical_list:
            raise errors.RecreateDynamicMenuBar
        SawxListAction.sync_menu_item_from_editor(self, action_key, menu_item)

    def perform(self, action_key):
        path = self.get_path(action_key)
        self.editor.frame.load_file(path, self.editor)
