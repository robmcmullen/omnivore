import os
import sys
import wx

from atrcopy import comment_bit_mask, user_bit_mask, diff_bit_mask, data_style
from udis.udis_fast import flag_jump, flag_branch, flag_return, flag_store, flag_undoc, flag_data_bytes, TraceInfo

from omni8bit.ui.bytegrid import ByteGridTable, ByteGrid, HexTextCtrl, HexCellEditor

from actions import GotoIndexAction
from commands import MiniAssemblerCommand

import logging
log = logging.getLogger(__name__)


class DisassemblyTable(ByteGridTable):
    column_labels = ["Bytes", "Disassembly", "Comment"]
    column_sizes = [11, 18, 30]
    label_format = "L%04x"
    
    @classmethod
    def update_preferences(cls, prefs):
        # Can't call ByteGridTable.update_preferences(prefs) because the
        # get_value_style method would be assigned from the base class and not
        # this DisassemblyTable
        if prefs.hex_grid_lower_case:
            cls.get_value_style = cls.get_value_style_lower
            cls.label_format = "L%04x"
        else:
            cls.get_value_style = cls.get_value_style_upper
            cls.label_format = "L%04X"
        for i, w in enumerate(prefs.disassembly_column_widths):
            if w > 0:
                cls.column_pixel_sizes[i] = w

    def __init__(self):
        ByteGridTable.__init__(self)
        self.lines = None
        self._rows = 0
        self.index_to_row = []
        self.start_addr = 0
        self.end_addr = 0
        self.chunk_size = 256
        self.disassembler = None
        self.use_labels_on_operands = False
        self.trace_info = TraceInfo()

    def set_editor(self, editor):
        self.editor = editor
        self.segment = segment = self.editor.segment
        self.lines = None
        self.index_to_row = []
        self.disassembler = editor.machine.get_disassembler(editor.task.hex_grid_lower_case, editor.task.assembly_lower_case)
        self.disassembler.add_chunk_processor("data", 1)
        self.disassembler.add_chunk_processor("antic_dl", 2)
        self.disassembler.add_chunk_processor("jumpman_level", 3)
        self.disassembler.add_chunk_processor("jumpman_harvest", 4)
        self.hex_lower = editor.task.hex_grid_lower_case
        if self.hex_lower:
            self.fmt_hex2 = "%02x"
            self.fmt_hex4 = "%04x"
        else:
            self.fmt_hex2 = "%02X"
            self.fmt_hex4 = "%04X"
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
        if col == 1:
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
            return 0, 0
    
    def is_index_valid(self, index):
        return self._rows > 0 and index >= 0 and index < len(self.segment)
    
    def is_pc_valid(self, pc):
        index = pc - self.start_addr
        return self.is_index_valid(index)
    
    def get_row_col(self, index):
        try:
            row = self.index_to_row[index]
        except:
            row = self.index_to_row[-1]
        return row, 1

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
        else:
            col = 1
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

    def get_value_style_lower(self, row, col, operand_labels_start_pc=-1, operand_labels_end_pc=-1, extra_labels={}, offset_operand_labels={}, line=None):
        if line is None:
            line = self.lines[row]
        pc = line.pc
        index = pc - self.start_addr
        style = 0
        count = line.num_bytes
        for i in range(count):
            style |= self.segment.style[index + i]
        if col == 0:
            text = self.disassembler.format_data_list_bytes(index, line.num_bytes)
        elif col == 2:
            text = self.disassembler.format_comment(index, line)
        else:
            text = self.disassembler.format_instruction(index, line)
        return text, style
    
    get_value_style_upper = get_value_style_lower
    
    def get_style_override(self, row, col, style):
        if self.lines[row].flag & flag_undoc:
            return style|diff_bit_mask
        return style

    def get_label_at_index(self, index):
        row = self.index_to_row[index]
        return self.get_label_at_row(row)
    
    def get_label_at_row(self, row):
        addr = self.get_pc(row)
        if self.get_value_style == self.get_value_style_lower:
            return "%04x" % addr
        return "%04X" % addr

    def GetRowLabelValue(self, row):
        if self.lines is not None:
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
        prefs = self.task.get_preferences()
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
        self.table.disassemble_from(index, True)
    
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
        print "get_trace", s.start_addr, size, trace
        return trace, mask

    def update_trace_in_segment(self, save=False):
        trace, mask = self.get_trace(save)
        print self.table.segment, trace
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

    def get_status_message_at_index(self, index, row, col):
        msg = ByteGrid.get_status_message_at_index(self, index, row, col)
        comments = self.table.disassembler.format_comment(index)
        return "%s  %s" % (msg, comments)

    def goto_index(self, index):
        try:
            row = self.table.index_to_row[index]
            self.pending_index = -1
        except IndexError:
            self.pending_index = index
        else:
            row, col = self.table.get_row_col(index)
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
            cmd = text.upper()
            bytes = self.table.disassembler.assemble_text(pc, cmd)
            start, _ = self.table.get_index_range(row, col)
            end = start + len(bytes)
            cmd = MiniAssemblerCommand(self.table.segment, start, end, bytes, cmd)
            self.task.active_editor.process_command(cmd)
            return True
        except RuntimeError, e:
            self.task.window.error(unicode(e))
            self.SetFocus()  # OS X quirk: return focus to the grid so the user can keep typing
        return False
    
    def search(self, search_text, match_case=False):
        # FIXME! search broken with udis_fast
        lines = self.table.lines
        s = self.table.start_addr
        if not match_case:
            search_text = search_text.lower()
            matches = [(t.pc - s, t.pc - s + t.num_bytes) for t in lines if search_text in t.instruction.lower()]
        else:
            matches = [(t.pc - s, t.pc - s + t.num_bytes) for t in lines if search_text in t.instruction]

        for index, comment in self.table.segment.iter_comments_in_segment():
            if index < lines.num_bytes:
                if not match_case:
                    matched = search_text in comment.lower()
                else:
                    matched = search_text in comment
                if matched:
                    row = self.table.index_to_row[index]
                    line = lines[row]
                    instruction_index = line.pc - s
                    #print "Matched! ->%s<-" % comment, hex(index), hex(instruction_index), hex(line.pc), line.instruction
                    matches.append((instruction_index, instruction_index + line.num_bytes))
        return matches
    
    def get_goto_actions(self, r, c):
        goto_actions = []
        addr_dest = self.table.disassembler.get_addr_dest(r)
        if addr_dest >= 0:
            segment_start = self.table.segment.start_addr
            segment_num = -1
            addr_index = addr_dest - segment_start
            segments = self.editor.document.find_segments_in_range(addr_dest)
            if addr_dest < segment_start or addr_dest > segment_start + len(self.table.segment):
                # segment_num, segment_dest, addr_index = self.editor.document.find_segment_in_range(addr_dest)
                if not segments:
                    msg = "Address $%04x not in any segment" % addr_dest
                    addr_dest = -1
                else:
                    # Don't chose a default segment, just show the sub menu
                    msg = None
            else:
                msg = "Go to $%04x" % addr_dest
        else:
            msg = "No address to jump to"
        if addr_dest >= 0:
            if msg is not None:
                goto_actions.append(GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.task, active_editor=self.task.active_editor))
            if len(segments) > 0:
                other_segment_actions = ["Go to $%04x in Other Segment..." % addr_dest]
                for segment_num, segment_dest, addr_index in segments:
                    if segment_dest == self.table.segment:
                        continue
                    msg = str(segment_dest)
                    action = GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.task, active_editor=self.task.active_editor)
                    other_segment_actions.append(action)
                if len(other_segment_actions) > 1:
                    # found another segment other than itself
                    goto_actions.append(other_segment_actions)
        else:
            goto_actions.append(GotoIndexAction(name=msg, enabled=False, task=self.task))
        return goto_actions
    
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
