from ..action import OmnivoreAction
from .. import errors
from ..persistence import get_json_data, save_json_data

class open_recent(OmnivoreAction):
    prefix = "open_recent_"

    prefix_count = len(prefix)

    max_entries = 20

    canonical_list = None

    @classmethod
    def reload(cls):
        data = get_json_data("recent_files", [])
        cls.canonical_list = data

    @classmethod
    def append(cls, uri):
        try:
            index = cls.canonical_list.index(uri)
            cls.canonical_list.pop(index)
        except ValueError:
            pass
        cls.canonical_list[0:0] = [uri]
        if len(cls.canonical_list) > cls.max_entries:
            cls.canonical_list = cls.canonical_list[:cls.max_entries]
        save_json_data("recent_files", cls.canonical_list)

    def init_from_editor(self):
        if self.canonical_list is None:
            self.reload()
        self.current_list = self.canonical_list[:]

    def get_index(self, action_key):
        return int(action_key[self.prefix_count:])

    def get_path(self, action_key):
        return self.current_list[self.get_index(action_key)]

    def calc_name(self, action_key):
        if len(self.current_list) == 0:
            return "No recent files"
        return self.get_path(action_key)

    def calc_menu_sub_keys(self, action_key):
        if len(self.current_list) == 0:
            return [self.prefix + "empty"]
        return [f"{self.prefix}{i}" for i in range(len(self.current_list))]

    def sync_menu_item_from_editor(self, action_key, menu_item):
        if self.current_list != self.canonical_list:
            raise errors.RecreateDynamicMenuBar
        state = not len(self.current_list) == 0
        menu_item.Enable(state)

    def execute(self, action_key):
        path = self.get_path(action_key)
        self.editor.frame.load_file(path, self.editor)
