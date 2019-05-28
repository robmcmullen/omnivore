import os
import sys

import numpy as np

import wx

from ..udis_fast import TraceInfo, flag_origin

from sawx.framework.enthought_api import EditorAction
from sawx.utils.nputil import intscale
from sawx.ui import compactgrid as cg
import sawx.framework.clipboard as clipboard

from ..ui.segment_grid import SegmentGridControl, SegmentTable, SegmentGridTextCtrl
from .hex2 import HexEditControl
from ..arch.disasm import iter_disasm_styles
from ..utils import searchutil
from ..commands import SetIndexedDataCommand
from .actions import ViewerAction

from ..viewer import SegmentViewer

import logging
log = logging.getLogger(__name__)



class UdisFastTable(cg.HexTable):
    column_labels = ["Bytes", "Disassembly", "Comment"]
    column_sizes = [11, 18, 30]

    def __init__(self, linked_base):
        s = linked_base.segment
        cg.HexTable.__init__(self, s.data, s.style, 2, s.origin)
        self.lines = None
        self.num_rows = 0
        self.index_to_row = []
        self.end_addr = 0
        self.chunk_size = 256
        self.set_display_format(linked_base.cached_preferences)

    def set_display_format(self, prefs):
        for i, w in enumerate(prefs.disassembly_column_widths):
            if w > 0:
                self.__class__.column_pixel_sizes[i] = w
        self.set_fmt_hex(prefs.hex_format_character)

    def set_fmt_hex(self, fmt_char):
        self.fmt_hex1 = "%" + fmt_char
        self.fmt_hex2 = "%02" + fmt_char
        self.fmt_hex4 = "%04" + fmt_char

    def update_disassembly(self, segment, disassembly, index=0, refresh=False):
        self.segment = segment
        self.data = segment.data
        self.style = segment.style
        self.last_valid_index = len(self.data)
        self.disassembly = disassembly
        # cache some values for fewer deep references
        self.index_to_row = self.disassembly.info.index_to_row
        self.lines = self.disassembly.info
        self.jump_targets = self.disassembly.info.labels
        self.origin = self.disassembly.origin
        self.end_addr = self.disassembly.end_addr
        self.num_rows = self.lines.num_instructions
        # print(self.disassembly, self.num_rows)

    def get_index_range(self, r, c):
        try:
            try:
                line = self.lines[r]
            except IndexError:
                line = self.lines[-1]
            except TypeError:
                return 0, 0
            index = line.pc - self.origin
            return index, index + line.num_bytes
        except IndexError:
            if r >= self.num_rows:
                index = self.last_valid_index - 1
            else:
                index = 0
            return index, index

    def is_index_valid(self, index):
        return self.num_rows > 0 and index >= 0 and index <= self.last_valid_index

    def get_index_of_row(self, row):
        line = self.lines[row]
        index = line.pc - self.origin
        return index

    def get_start_end_index_of_row(self, row):
        line = self.lines[row]
        index = line.pc - self.origin
        return index, index + line.num_bytes

    def is_pc_valid(self, pc):
        index = pc - self.origin
        return self.is_index_valid(index)

    def index_to_row_col(self, index, col=1):
        try:
            row = self.index_to_row[index]
        except:
            try:
                row = self.index_to_row[-1]
            except IndexError:
                return 0, 0
        return row, col

    def get_next_caret_pos(self, row, col):
        col += 1
        if col >= self._cols:
            if row < self.num_rows - 1:
                row += 1
                col = 1
            else:
                col = self._cols - 1
        return (row, col)

    def get_next_editable_pos(self, row, col):
        if col < 1:
            col = 1
        elif col == 1:
            col = 1
            row += 1
        elif col == 2:
            col = 2
            row += 1
        return (row, col)

    def get_prev_caret_pos(self, row, col):
        col -= 1
        if col < 1:
            if row > 0:
                row -= 1
                col = self._cols - 1
            else:
                col = 1
        return (row, col)

    def get_page_index(self, index, segment_page_size, dir, grid):
        r, c = self.get_row_col(index)
        vr = grid.get_num_visible_rows() - 1
        r += (dir * vr)
        if r < 0:
            r = 0
        index, _ = self.get_index_range(r, 0)
        return index

    def get_pc(self, row):
        try:
            row = self.lines[row]
            return row.pc
        except IndexError:
            return 0
        except TypeError:
            return 0

    def get_value_style(self, row, col, operand_labels_start_pc=-1, operand_labels_end_pc=-1, extra_labels={}, offset_operand_labels={}, line=None):
        if line is None:
            line = self.lines[row]
        index = line.pc - self.origin
        style = 0
        for i in range(line.num_bytes):
            style |= self.style[index + i]
        text = self.calc_display_text(row, col, line, index)
        return text, style

    def calc_display_text(self, row, col, line=None, index=None):
        if line is None:
            line = self.lines[row]
            index = line.pc - self.origin
        if col == 0:
            if self.lines[row].flag == flag_origin:
                text = ""
            else:
                text = self.disassembly.format_data_list_bytes(index, line.num_bytes)
        else:
            text = self.disassembly.format_instruction(index, line)
            comment = self.disassembly.format_comment(index, line)
            if comment:
                text += " ; " + comment
        return text

    def get_label_at_index(self, index):
        row = self.index_to_row[index]
        return self.get_label_at_row(row)

    def get_label_at_row(self, row):
        addr = self.get_pc(row)
        return self.fmt_hex4 % addr


class DisassemblyGridControl(SegmentGridControl):
    def calc_default_table(self, linked_base):
        return UdisFastTable(linked_base)

    def calc_line_renderer(self):
        return cg.VirtualTableLineRenderer(self, 2, widths=[5,25], col_labels=['^Opcodes','^      Operand'])

    def recalc_view(self):
        v = self.segment_viewer
        v.restart_disassembly()
        cg.CompactGrid.recalc_view(self)
        if v.is_tracing:
            v.update_trace_in_segment()

    def get_disassembled_text(self, start=0, end=-1):
        return self.table.disassembly.get_disassembled_text(start, end)

    def encode_data(self, segment, linked_base):
        """Segment saver interface: take a segment and produce a byte
        representation to save to disk.
        """
        lines = self.table.disassembly.get_disassembled_text()
        text = os.linesep.join(lines) + os.linesep
        data = text.encode("utf-8")
        return data

    def extra_popup_actions(self, popup_data):
        actions = []
        addr_dest = self.table.disassembly.get_addr_dest(popup_data['row'], popup_data['col'])
        actions.extend(self.segment_viewer.linked_base.get_goto_actions_other_segments(addr_dest))
        actions.extend(self.segment_viewer.linked_base.get_goto_actions_same_byte(popup_data['index']))
        return actions

    ##### editing

    def advance_caret_position(self):
        self.handle_char_move_down(None, None)

    def verify_keycode_can_start_edit(self, c):
        if c == ord(";"):
            self.editing_type = "comment"
        else:
            self.editing_type = "code"
        return True

    def use_first_char_when_starting_edit(self):
        return self.editing_type != "comment"

    def process_edit(self, val):
        if self.editing_type == "comment":
            self.process_comment(val)
        else:
            try:
                self.process_mnemonic(val)
            except RuntimeError as e:
                log.error(f"Invalid assembly: {e}")
                self.segment_viewer.editor.window.error(str(e), "Invalid Assembly")

    def process_comment(self, val):
        ranges = self.get_selected_ranges_including_carets(self.caret_handler)
        cmd = SetCommentCommand(self.segment_viewer.segment, ranges, val)
        self.segment_viewer.editor.process_command(cmd)

    def process_mnemonic(self, val):
        t = self.table
        d = t.disassembly
        op = val.upper()
        ranges = self.get_selected_ranges_including_carets(self.caret_handler)
        max_possible = ranges[-1][1] + 16  # assuming max opcode length < 16 bytes
        data = np.zeros([max_possible], dtype=np.int16) - 1  # negative == unused

        # Have to calculate each line individually because PC relative
        # operations will have different opcode bytes depending on what the PC
        # is at the current location.
        for r in ranges:
            print(("processing range %s" % str(r)))
            row = t.index_to_row[r[0]]
            data_index = t.get_index_of_row(row)
            pc = t.get_pc(row)
            subset = None
            while data_index < r[1]:
                opcodes = d.assemble_text(pc, op)
                next_data_index = data_index + len(opcodes)
                print(("pc=%x op=%s data[%d:%d]=%s" % (pc, op, data_index, next_data_index, opcodes)))
                data[data_index:next_data_index] = opcodes
                data_index = next_data_index
                pc += len(opcodes)

        indexes = np.where(data >= 0)[0]
        byte_data = np.empty([len(indexes)], dtype=np.uint8)
        byte_data[:] = data[indexes]
        print(indexes)
        print(byte_data)
        cmd = SetIndexedDataCommand(self.segment_viewer.segment, indexes, byte_data, advance=True)
        self.segment_viewer.editor.process_command(cmd)


class CopyDisassemblyAction(ViewerAction):
    """Copy the disassembly text of the current selection to the clipboard.

    """
    name = 'Copy Disassembly Text'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(selected=True)
        lines = []
        try:
            for start, end in ranges:
                lines.extend(self.viewer.control.table.disassembly.get_disassembled_text(start, end))
        except IndexError:
            e.window.error("Disassembly tried to jump to an address outside this segment.")
            return
        text = os.linesep.join(lines) + os.linesep
        data_obj = wx.TextDataObject()
        data_obj.SetText(text)
        clipboard.set_clipboard_object(data_obj)

    def _update_enabled(self, ui_state):
        self.enabled = self.active_editor.focused_viewer.has_cpu


class CopyDisassemblyCommentsAction(ViewerAction):
    """Copy the text of the comments only, using the disassembly for line
    breaks. Any blank lines that appear in the disassembly are included in the
    copy.

    """
    name = 'Copy Disassembly Comments'
    enabled_name = 'can_copy'

    def perform(self, event):
        e = self.active_editor
        s = e.segment
        ranges = s.get_style_ranges(selected=True)
        lines = []
        for start, end in ranges:
            for _, _, _, comment, _ in self.viewer.control.table.disassembly.iter_row_text(start, end):
                lines.append(comment)
        text = os.linesep.join(lines) + os.linesep
        data_obj = wx.TextDataObject()
        data_obj.SetText(text)
        clipboard.set_clipboard_object(data_obj)

    def _update_enabled(self, ui_state):
        self.enabled = self.active_editor.focused_viewer.has_cpu


class PasteDisassemblyCommentsAction(ViewerAction):
    name = 'Paste Disassembly Comments'
    tooltip = 'Paste text as comment lines'
    enabled_name = 'can_paste'
    accelerator = 'Shift-F6'

    def perform(self, event):
        self.active_editor.paste(PasteDisassemblyCommentsCommand, disasm=self.viewer.control.table.disassembly)


class PasteDisassemblyCommentsCommand(SetCommentCommand):
    """Copy the text of the comments only, using the disassembly for line
    breaks. Any blank lines that appear in the disassembly are included in the
    copy.

    """
    name = 'Paste Disassembly Comments'

    def __init__(self, segment, serializer, disasm=None):
        ranges = serializer.dest_carets.selected_ranges
        if not ranges:
            # use the range from caret to end
            ranges = [(serializer.dest_carets.current.index, len(segment))]
        SetCommentCommand.__init__(self, segment, ranges, serializer.clipboard_data)
        self.comments = self.text.tobytes().splitlines()
        self.num_lines = len(self.comments)
        self.disasm = disasm

    def __str__(self):
        return "%s: %d line%s" % (self.ui_name, self.num_lines, "" if self.num_lines == 1 else "s")

    def clamp_ranges_and_indexes(self, editor):
        disasm = self.disasm
        count = self.num_lines
        comment_indexes = []
        clamped = []
        for start, end in self.ranges:
            index = start
            log.debug("starting range %d:%d" % (start, end))
            while index < end and count > 0:
                comment_indexes.append(index)
                pc = index + self.segment.origin
                log.debug("comment at %d, %04x" % (index, pc))
                try:
                    index = disasm.get_next_instruction_pc(pc)
                    count -= 1
                except IndexError:
                    count = 0
            clamped.append((start, index))
            if count <= 0:
                break
        return clamped, comment_indexes

    def change_comments(self, ranges, indexes):
        """Add comment lines as long as we don't go out of range (if specified)
        or until the end of the segment or the comment list is exhausted.

        Depends on a valid disassembly to find the lines; we are adding a
        comment for the first byte in each statement.
        """
        log.debug("ranges: %s" % str(ranges))
        log.debug("indexes: %s" % str(indexes))
        self.segment.set_comments_at_indexes(ranges, indexes, self.comments)
        self.segment.set_style_at_indexes(indexes, comment=True)



# Disassembly searcher uses the __call__ method to return the object because it
# needs extra info: the machine type & the disassembly list. Normal searchers
# just use the segment's raw data and returns itself in the constructor.
class DisassemblySearcher(searchutil.BaseSearcher):
    def __init__(self, viewer, panel):
        self.search_text = None
        self.matches = []
        self.panel = panel
        self.ui_name = viewer.machine.disassembler.name

    def __call__(self, editor, search_text):
        self.search_text = self.get_search_text(search_text)
        if len(self.search_text) > 0:
            self.matches = self.get_matches(editor)
            self.set_style(editor)
        else:
            self.matches = []
        return self

    def __str__(self):
        return "disasm matches: %s" % str(self.matches)

    def get_search_text(self, text):
        return text

    def get_matches(self, editor):
        matches = self.panel.search(self.search_text, editor.last_search_settings.get('match_case', False))
        return matches


class DisassemblyViewer(SegmentViewer):
    name = "disassembly"

    ui_name = "Disassembly"

    control_cls = DisassemblyGridControl

    has_cpu = True

    has_hex = True

    copy_special = [CopyDisassemblyAction, CopyDisassemblyCommentsAction]

    paste_special = [PasteDisassemblyCommentsAction]

    current_disassembly_ = Any(None)

    trace = Instance(TraceInfo)

    # trait defaults

    def _trace_default(self):
        return TraceInfo()

    # properties

    @property
    def window_title(self):
        return self.machine.disassembler.name + " (" + self.machine.memory_map.name + ")"

    @property
    def searchers(self):
        return [DisassemblySearcher(self, self.control)]

    # @on_trait_change('machine.disassembler_change_event')
    def do_disassembler_change(self, evt):
        log.debug("do_disassembler_change for %s using %s; flags=%s" % (self.control, self.linked_base, str(evt)))
        if evt is not Undefined:
            self.clear_disassembly()
            self.restart_disassembly()
            self.linked_base.editor.update_pane_names()

    # @on_trait_change('linked_base.editor.document.byte_values_changed')
    def byte_values_changed(self, index_range):
        log.debug("byte_values_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.restart_disassembly(index_range)

    # @on_trait_change('linked_base.editor.document.byte_style_changed')
    def byte_style_changed(self, index_range):
        log.debug("byte_style_changed: %s index_range=%s" % (self, str(index_range)))
        if index_range is not Undefined:
            self.restart_disassembly(index_range)

    def recalc_data_model(self):
        self.clear_disassembly()
        self.restart_disassembly()

    def do_priority_level_refresh(self):
        index, row1, offset1, col1 = self.control.calc_primary_caret_visible_info()
        self.recalc_data_model()
        index2, row2, offset2, col2 = self.control.calc_primary_caret_visible_info()
        new_first_row = row2 - offset1
        log.debug(f"keep caret in same place: before={row1} {offset1}, after={row2} {offset2}, new={new_first_row}")
        self.control.move_viewport_origin((new_first_row, -1))
        self.refresh_view(True)
        self.frame_count = 0

    ##### UdisFast interface

    def create_disassembler(self):
        prefs = self.linked_base.cached_preferences
        d = self.machine.get_disassembler(prefs.hex_grid_lower_case, prefs.assembly_lower_case, self.document.document_memory_map, self.segment.memory_map)
        for i, name in iter_disasm_styles():
            d.add_chunk_processor(name, i)
        return d

    @property
    def current_disassembly(self):
        if self.current_disassembly_ is None:
            d = self.create_disassembler()
            self.current_disassembly_ = d
        return self.current_disassembly_

    def clear_disassembly(self):
        self.current_disassembly_ = None

    def restart_disassembly(self, index=None):
        self.current_disassembly.disassemble_segment(self.segment)
        self.control.table.update_disassembly(self.segment, self.current_disassembly)

    ##### disassembly tracing

    def start_trace(self):
        self.trace_info = TraceInfo()
        self.is_tracing = True
        self.update_trace_in_segment()
        self.linked_base.force_refresh()

    def get_trace(self, save=False):
        if save:
            kwargs = {'user': True}
        else:
            kwargs = {'match': True}
        s = self.segment
        mask = s.get_style_mask(**kwargs)
        style = s.get_style_bits(**kwargs)
        is_data = self.trace_info.marked_as_data
        size = min(len(is_data), len(s))
        trace = is_data[s.origin:s.origin + size] * style
        if save:
            # don't change data flags for stuff that's already marked as data
            s = self.segment
            already_data = np.logical_and(s.style[0:size] & user_bit_mask > 0, trace > 0)
            indexes = np.where(already_data)[0]
            previous = s.style[indexes]
            trace[indexes] = previous
        return trace, mask

    def update_trace_in_segment(self, save=False):
        trace, mask = self.get_trace(save)
        s = self.segment
        size = len(trace)
        s.style[0:size] &= mask
        s.style[0:size] |= trace

    def trace_disassembly(self, pc):
        self.current_disassembly.fast.trace_disassembly(self.trace_info, [pc])
        self.update_trace_in_segment()

    ##### popup commands

    def calc_viewer_popup_actions(self, popup_data):
        return []
