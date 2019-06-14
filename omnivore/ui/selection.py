# Standard library imports.

# Major package imports.
import numpy as np

import sawx.ui.compactgrid as cg

import logging
log = logging.getLogger(__name__)


class SelectionMixin:
    def __str__(self):
        return f"{self.__class__.__name__}: source={self.control.segment_viewer.ui_name} carets=" + " ".join([str(c) for c in self.carets])

    def get_selected_status_message(self):
        carets = list(self.carets_with_selection)
        if len(carets) == 0:
            return ""
        elif len(carets) == 1:
            table = self.table
            viewer = self.control.segment_viewer
            caret = carets[0]
            anchor_start, _ = table.get_index_range(*caret.anchor_start)
            _, anchor_end = table.get_index_range(*caret.anchor_end)
            num = anchor_end - anchor_start
            if num == 1:
                text = f"[1 byte selected ${viewer.get_address_at_index(anchor_start)}]"
            elif num > 0:
                text = f"[{num} bytes selected ${viewer.get_address_at_index(anchor_start)}-${viewer.get_address_at_index(anchor_end)}]"
        else:
            text = "[%d ranges selected]" % (len(carets))
        text += f" from {self.control.segment_viewer.window_title}"
        return text

    def calc_indexes(self, dest_segment, use_carets_without_selections=True):
        table = self.table
        indexes = np.empty(200000, dtype=np.uint32)
        current = 0
        for caret in self.carets:
            index, _ = table.get_index_range(*caret.rc)
            if caret.anchor_start[0] < 0:
                if not use_carets_without_selections:
                    continue
                indexes[current:current + 1] = index
                current += 1
            else:
                anchor_start, _ = table.get_index_range(*caret.anchor_start)
                _, anchor_end = table.get_index_range(*caret.anchor_end)
                count = anchor_end - anchor_start
                indexes[current:current + count] = np.arange(anchor_start, anchor_end, dtype=np.uint32)
                current += count
        dest_indexes = dest_segment.calc_indexes_from_other_segment(indexes[0:current], self.segment)
        return dest_indexes

    def convert_carets_from(self, other_char_handler):
        new_carets = []
        table = self.table
        other_table = other_char_handler.table
        other_segment = other_char_handler.segment
        for caret in other_char_handler.carets:
            other_index, _ = other_table.get_index_range(*caret.rc)
            index = self.segment.calc_index_from_other_segment(other_index, other_segment)
            r, c = table.index_to_row_col(index)
            new_caret = cg.Caret(r, c)

            # other_index, _ = other_table.get_index_range(*caret.anchor_start)
            # index = self.segment.calc_index_from_other_segment(other_index, other_segment)
            # r, c = table.index_to_row_col(index)
            # caret.anchor_start = caret.anchor_initial_start = (r, c)

            # _, other_index = other_table.get_index_range(*caret.anchor_end)
            # index = self.segment.calc_index_from_other_segment(other_index, other_segment)
            # r, c = table.index_to_row_col(index)
            # caret.anchor_end = caret.anchor_initial_end = (r, c)

            log.debug(f"converted {caret} from {other_char_handler.control},index={other_index} to {self.control},index={index}, new_caret")
            new_carets.append(new_caret)
        self.carets = new_carets

    def set_caret_from_indexes(self, index, anchor_start=-1, anchor_end=-1):
        table = self.table
        r, c = table.index_to_row_col(index)
        caret = cg.Caret(r, c)
        if anchor_start >= 0:
            r, c = table.index_to_row_col(anchor_start)
            caret.anchor_start = caret.anchor_initial_start = (r, c)
            r, c = table.index_to_row_col(anchor_end)
            caret.anchor_end = caret.anchor_initial_end = (r, c)
        self.carets = [caret]

    def convert_style_to_carets(self):
        table = self.table
        ranges = self.segment.get_style_ranges(selected=True)
        print(ranges)
        new_carets = []
        for start, end in ranges:
            r, c = table.index_to_row_col(end - 1)
            caret = cg.Caret(r, c)
            r, c = table.index_to_row_col(end)
            caret.anchor_end = caret.anchor_initial_end = (r, c)
            r, c = table.index_to_row_col(start)
            caret.anchor_start = caret.anchor_initial_start = (r, c)
            new_carets.append(caret)
        self.carets = new_carets
        print(self.carets)


class FrozenSelection(SelectionMixin, cg.MultiCaretHandler):
    def __init__(self, current_selection):
        cg.MultiCaretHandler.__init__(self)
        self.control = current_selection.control
        self.table = current_selection.table
        self.segment = current_selection.segment
        self.carets = [c.copy() for c in current_selection.carets]


class CurrentSelection(SelectionMixin, cg.MultiCaretHandler):
    def __init__(self, control):
        cg.MultiCaretHandler.__init__(self)
        self.control = control

    @property
    def table(self):
        return self.control.table

    @property
    def segment(self):
        return self.control.segment_viewer.caret_conversion_segment

    def copy(self):
        return FrozenSelection(self)
