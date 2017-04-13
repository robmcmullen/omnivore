import os
import sys

import numpy as np
import wx

from atrcopy import comment_bit_mask, user_bit_mask, diff_bit_mask, data_style
from udis.udis_fast import TraceInfo, flag_origin

from omnivore8bit.ui.bytegrid import ByteGridTable, ByteGrid, HexTextCtrl, HexCellEditor
from omnivore8bit.arch.disasm import iter_disasm_styles

from actions import GotoIndexAction
from commands import MiniAssemblerCommand, SetCommentCommand

import logging
log = logging.getLogger(__name__)


class DisassemblyTable(ByteGridTable):
    column_labels = ["Bytes", "Disassembly", "Comment"]
    column_sizes = [11, 18, 30]

    def set_display_format(self, editor):
        ByteGridTable.set_display_format(self, editor)
        prefs = editor.task.preferences
        for i, w in enumerate(prefs.disassembly_column_widths):
            if w > 0:
                self.__class__.column_pixel_sizes[i] = w

    def __init__(self):
        ByteGridTable.__init__(self)
        self.lines = None
        self._rows = 0
        self.index_to_row = []
        self.start_addr = 0
        self.end_addr = 0
        self.chunk_size = 256
        self.disassembler = None
        self.trace_info = TraceInfo()

    def set_editor(self, editor):
        self.editor = editor
        self.set_display_format(editor)
        self.segment = segment = self.editor.segment
        self.lines = None
        self.index_to_row = []
        self.disassembler = editor.machine.get_disassembler(editor.task.hex_grid_lower_case, editor.task.assembly_lower_case, self.editor.document.document_memory_map, self.segment.memory_map)
        for i, name in iter_disasm_styles():
            self.disassembler.add_chunk_processor(name, i)
        self.highlight_flags = self.disassembler.highlight_flags
        f = editor.machine.assembler
        self.fmt_hex_directive = f['data byte']
        self.fmt_hex_digits = f['data byte prefix'] + "%c%c"
        self.fmt_hex_digit_separator = f['data byte separator']
        self.start_addr = segment.start_addr
        self.end_addr = self.start_addr + len(segment)
        self.disassemble_from(0)

    def disassemble_from(self, index, refresh=False):
        self.lines = None
        info = self.disassembler.disassemble_segment(self.segment)
        self.index_to_row = info.index_to_row
        self.lines = info
        self.jump_targets = info.labels
        grid = self.editor.disassembly
        if refresh:
            # Fixed double resize bug if called from set_editor. Only if
            # refresh requested, like from a UI interaction, should the reset
            # get called
            self.ResetView(grid, None)

    def get_data_rows(self):
        return 0 if self.lines is None else self.lines.num_instructions

    def set_grid_cell_attr(self, grid, col, attr):
        ByteGridTable.set_grid_cell_attr(self, grid, col, attr)
        if col > 0:
            attr.SetReadOnly(False)
        else:
            attr.SetReadOnly(True)

    def get_index_range(self, r, c):
        try:
            try:
                line = self.lines[r]
            except IndexError:
                line = self.lines[-1]
            except TypeError:
                return 0, 0
            index = line.pc - self.start_addr
            return index, index + line.num_bytes
        except IndexError:
            if r >= self._rows:
                index = len(self.segment) - 1
            else:
                index = 0
            return index, index

    def is_index_valid(self, index):
        return self._rows > 0 and index >= 0 and index < len(self.segment)

    def is_pc_valid(self, pc):
        index = pc - self.start_addr
        return self.is_index_valid(index)

    def get_row_col(self, index, col=1):
        try:
            row = self.index_to_row[index]
        except:
            try:
                row = self.index_to_row[-1]
            except IndexError:
                return 0, 0
        return row, col

    def get_next_cursor_pos(self, row, col):
        col += 1
        if col >= self._cols:
            if row < self._rows - 1:
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

    def get_prev_cursor_pos(self, row, col):
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

    def get_value_style(self, row, col, operand_labels_start_pc=-1, operand_labels_end_pc=-1, extra_labels={}, offset_operand_labels={}, line=None):
        if line is None:
            line = self.lines[row]
        pc = line.pc
        index = pc - self.start_addr
        style = 0
        count = line.num_bytes
        for i in range(count):
            style |= self.segment.style[index + i]
        if col == 0:
            if self.lines[row].flag == flag_origin:
                text = ""
            else:
                text = self.disassembler.format_data_list_bytes(index, line.num_bytes)
        elif col == 2:
            text = self.disassembler.format_comment(index, line)
        else:
            text = self.disassembler.format_instruction(index, line)
        return text, style

    def get_style_override(self, row, col, style):
        if self.lines[row].flag & self.highlight_flags:
            return style|diff_bit_mask
        return style

    def get_label_at_index(self, index):
        row = self.index_to_row[index]
        return self.get_label_at_row(row)

    def get_label_at_row(self, row):
        addr = self.get_pc(row)
        return self.fmt_hex4 % addr

    def GetRowLabelValue(self, row):
        if self.get_data_rows() > 0:
            line = self.lines[row]
            return self.disassembler.format_row_label(line)
        return "0000"

    def ResetViewProcessArgs(self, grid, editor, *args, **kwargs):
        if editor is not None:
            self.set_editor(editor)


class AssemblerTextCtrl(HexTextCtrl):
    def setMode(self, mode):
        self.mode='6502'
        self.SetMaxLength(0)
        self.autoadvance=0
        self.userpressed=False


class AssemblerEditor(HexCellEditor):
    def Create(self, parent, id, evtHandler):
        """
        Called to create the control, which must derive from wx.Control.
        *Must Override*
        """
        self._tc = AssemblerTextCtrl(parent, id, self.parentgrid)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)


class DisassemblyPanel(ByteGrid):
    """
    View for editing in hexidecimal notation.
    """
    short_name = "disasm"

    # Segment saver interface for menu item display
    export_data_name = "Disassembly"
    export_extensions = [".s"]

    def __init__(self, parent, task, **kwargs):
        """Create the HexEdit viewer
        """
        table = DisassemblyTable()
        ByteGrid.__init__(self, parent, task, table, **kwargs)

        # During idle-time disassembly, an index may not yet be visible.  The
        # value is saved here so the view can be scrolled there once it does
        # get disassembled.
        self.pending_index = -1

    def save_prefs(self):
        prefs = self.task.preferences
        widths = [0] * len(prefs.disassembly_column_widths)
        for i, w in self.table.column_pixel_sizes.iteritems():
            widths[i] = w
        prefs.disassembly_column_widths = tuple(widths)

    def recalc_view(self):
        ByteGrid.recalc_view(self)
        if self.table.editor.can_trace:
            self.update_trace_in_segment()

    def get_default_cell_editor(self):
        return AssemblerEditor(self)

    def restart_disassembly(self, index):
        first_row = self.get_first_visible_row()
        current_row = self.GetGridCursorRow()
        rows_from_top = current_row - first_row
        want_address = self.table.get_pc(current_row)
        self.table.disassemble_from(index, False)
        r, _ = self.table.get_row_col(want_address - self.table.start_addr)
        self.table.ResetView(self, None)
        new_first = max(0, r - rows_from_top)
        self.MakeCellVisible(new_first + self.get_num_visible_rows(), 0)
        self.MakeCellVisible(new_first, 0)
        self.SetGridCursor(r, 0)

    def get_disassembled_text(self, start=0, end=-1):
        return self.table.disassembler.get_disassembled_text(start, end)

    def start_trace(self):
        self.table.trace_info = TraceInfo()
        self.update_trace_in_segment()

    def get_trace(self, save=False):
        if save:
            kwargs = {'user': True}
        else:
            kwargs = {'match': True}
        s = self.table.segment
        mask = s.get_style_mask(**kwargs)
        style = s.get_style_bits(**kwargs)
        is_data = self.table.trace_info.marked_as_data
        size = min(len(is_data), len(s))
        trace = is_data[s.start_addr:s.start_addr + size] * style
        if save:
            # don't change data flags for stuff that's already marked as data
            s = self.table.segment
            already_data = np.logical_and(s.style[0:size] & user_bit_mask > 0, trace > 0)
            indexes = np.where(already_data)[0]
            previous = s.style[indexes]
            trace[indexes] = previous
        return trace, mask

    def update_trace_in_segment(self, save=False):
        trace, mask = self.get_trace(save)
        s = self.table.segment
        size = len(trace)
        s.style[0:size] &= mask
        s.style[0:size] |= trace

    def trace_disassembly(self, pc):
        self.table.disassembler.fast.trace_disassembly(self.table.trace_info, [pc])
        self.update_trace_in_segment()

    def encode_data(self, segment, editor):
        """Segment saver interface: take a segment and produce a byte
        representation to save to disk.
        """
        lines = self.table.disassembler.get_disassembled_text()
        text = os.linesep.join(lines) + os.linesep
        data = text.encode("utf-8")
        return data

    def clamp_column(self, col_from_index, col_from_user):
        if col_from_user <= 1:
            return 1
        return 2

    def goto_index(self, from_control, index, col_from_user=None):
        row, c = self.table.get_row_col(index)

        # user can click on whatever column when clicking in the disassembly
        # window, but on events coming from other windows it should not use the
        # column and instead force the opcode to be displayed
        if from_control == self:
            if col_from_user:
                col = self.clamp_column(c, col_from_user)
            else:
                col = c
        else:
            col = 0

        try:
            row = self.table.index_to_row[index]
            self.pending_index = -1
        except IndexError:
            self.pending_index = index
        else:
            self.SetGridCursor(row, col)
            self.MakeCellVisible(row,col)

    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.

        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        try:
            pc = self.table.get_pc(row)
            if col == 1:
                cmd = text.upper()
                bytes = self.table.disassembler.assemble_text(pc, cmd)
                start, _ = self.table.get_index_range(row, col)
                end = start + len(bytes)
                cmd = MiniAssemblerCommand(self.table.segment, start, end, bytes, cmd)
            else:
                start, _ = self.table.get_index_range(row, col)
                cmd = SetCommentCommand(self.table.segment, [(start, start + 1)], text)
            self.task.active_editor.process_command(cmd)
            return True
        except RuntimeError, e:
            self.task.window.error(unicode(e))
            self.SetFocus()  # OS X quirk: return focus to the grid so the user can keep typing
        return False

    def search(self, search_text, match_case=False):
        return self.table.disassembler.search(search_text, match_case)

    def get_goto_caller_actions(self, addr_called):
        goto_actions = []
        callers = self.table.disassembler.fast.find_callers(addr_called)
        if len(callers) > 0:
            s = self.table.segment
            caller_actions = ["Go to Caller..."]
            for pc in callers:
                if self.table.is_pc_valid(pc):
                    msg = "$%04x" % pc
                    addr_index = pc - s.start_addr
                    action = GotoIndexAction(name=msg, enabled=True, segment_num=self.editor.segment_number, addr_index=addr_index, task=self.task, active_editor=self.editor)
                    caller_actions.append(action)
            goto_actions.append(caller_actions)
        else:
            goto_actions.append(GotoIndexAction(name="No callers of $%04x" % addr_called, enabled=False, task=self.task))
        return goto_actions

    def get_goto_actions(self, r, c):
        if self.table.get_data_rows() == 0:
            return []
        actions = []
        addr_dest = self.table.disassembler.get_addr_dest(r)
        action = self.editor.get_goto_action_in_segment(addr_dest)
        if action:
            actions.append(action)
        index, _ = self.table.get_index_range(r, c)
        addr_called = index + self.table.start_addr
        actions.extend(self.get_goto_caller_actions(addr_called))
        actions.extend(self.editor.get_goto_actions_other_segments(addr_dest))
        actions.extend(self.editor.get_goto_actions_same_byte(index))
        return actions

    def get_popup_actions(self, r, c, inside):
        actions = self.get_goto_actions(r, c)
        actions.append(None)
        actions.extend(self.editor.common_popup_actions())
        return actions


class DisassemblyListSaver(object):
    """ Segment saver interface for ATasm assembler output listing file,
    includes line number and program counter at each instruction.
    """
    export_data_name = "ATasm LST file"
    export_extensions = [".lst"]

    @classmethod
    def encode_data(cls, segment, editor):
        """Segment saver interface: take a segment and produce a byte
        representation to save to disk.
        """
        lines = editor.disassembly.table.disassembler.get_atasm_lst_text()
        text = os.linesep.join(lines) + os.linesep
        data = text.encode("utf-8")
        return data
