from ..action import SawxAction, SawxSubAction, SawxActionRadioMixin
from .. import errors


class debug_text_counting(SawxAction):
    def init_from_editor(self, action_key):
        self.counts = list(range(5, 25, 5))

    def calc_name(self, action_key):
        return action_key.replace("_", " ").title()

    def calc_menu_sub_keys(self, action_key):
        self.count_map = {f"text_count_{c}":c for c in self.counts}
        return [f"text_count_{c}" for c in self.counts]

    def sync_menu_item_from_editor(self, action_key, menu_item):
        count = self.editor.control.GetLastPosition()
        menu_item.Enable(count >= self.count_map[action_key])

class debug_text_last_digit(SawxActionRadioMixin, SawxAction):
    def calc_name(self, action_key):
        return action_key.replace("_", " ").title()

    def calc_menu_sub_keys(self, action_key):
        self.count_map = {f"text_last_digit_{c}":c for c in range(10)}
        return [f"text_last_digit_{c}" for c in range(10)]

    def sync_menu_item_from_editor(self, action_key, menu_item):
        count = self.editor.control.GetLastPosition()
        divisor = self.count_map[action_key]
        menu_item.Check(count % 10 == divisor)

    calc_tool_sub_keys = calc_menu_sub_keys

    def sync_tool_item_from_editor(self, action_key, toolbar_control, id):
        count = self.editor.control.GetLastPosition()
        divisor = self.count_map[action_key]
        toolbar_control.ToggleTool(id, count % 10 == divisor)

class debug_text_last_digit_dyn(SawxAction):
    def init_from_editor(self, action_key):
        self.count = (self.editor.control.GetLastPosition() % 10) + 1

    def calc_name(self, action_key):
        return action_key.replace("_", " ").title()

    def calc_menu_sub_keys(self, action_key):
        self.count_map = {f"text_last_digit_dyn{c}":c for c in range(self.count)}
        return [f"text_last_digit_dyn{c}" for c in range(self.count)]

    def sync_menu_item_from_editor(self, action_key, menu_item):
        count = (self.editor.control.GetLastPosition() % 10) + 1
        if count != self.count:
            raise errors.RecreateDynamicMenuBar

class debug_text_size(SawxAction):
    def init_from_editor(self, action_key):
        self.counts = list(range(5, 25, 5))

    def calc_name(self, action_key):
        size = self.editor.control.GetLastPosition()
        return f"Text Size: {size}"

    def sync_menu_item_from_editor(self, action_key, menu_item):
        name = self.calc_name(action_key)
        menu_item.SetItemLabel(name)

class debug_generated(SawxSubAction):
    def perform(self, action_key):
        print(f"perform: {self.action_list_id}")
