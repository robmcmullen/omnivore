import sys
import wx

from omnivore.utils.wx.bytegrid import ByteGridTable, ByteGrid, HexTextCtrl, HexCellEditor
from omnivore.utils.binutil import DefaultSegment

from omnivore.third_party.asm6502 import assemble_text, AssemblyError

from omnivore.framework.actions import *
from actions import *
from commands import MiniAssemblerCommand

import logging
log = logging.getLogger(__name__)


class DisassemblyTable(ByteGridTable):
    column_labels = ["Bytes", "Disassembly", "Comment"]
    column_sizes = [8, 12, 20]
    
    def __init__(self):
        ByteGridTable.__init__(self)
        self.lines = []
        self._rows = 0
        self.index_to_row = []
        self.start_addr = 0
        self.next_row = -1
        self.chunk_size = 32
        self.disassembler = None

    def set_editor(self, editor):
        self.editor = editor
        self.segment = segment = self.editor.segment
        self.lines = []
        self.index_to_row = []
        self._rows = 0
        self.disassembler = editor.disassembler(segment.data, segment.start_addr, -segment.start_addr)
        self.disassembler.set_pc(segment.data, segment.start_addr)
        self.next_row = 0
        self.start_addr = segment.start_addr
        self.disassemble_next()
    
    def restart_disassembly(self, index):
        self.next_row = self.index_to_row[index]
        pc = self.get_pc(self.next_row)
        self.disassembler.set_pc(self.segment.data, pc)
    
    def disassemble_next(self):
        if self.next_row < 0:
            return
        lines = []
        start_row = self.next_row
        try:
            for i in range(self.chunk_size):
                (addr, bytes, opstr, comment) = self.disassembler.get_instruction()
                count = len(bytes)
                data = (addr, bytes, opstr, comment, count)
                lines.append(data)
        except StopIteration:
            pass
        if lines:
            n = len(lines)
            self.lines[start_row:start_row+n] = lines
            start_index, index_to_row = self.get_index_to_row(lines, start_row)
            self.index_to_row[start_index:start_index+len(index_to_row)] = index_to_row
            self.next_row += n
        else:
            self.next_row = -1
    
    def get_index_to_row(self, lines, start_row):
        row = start_row
        index = lines[0][0] - self.start_addr
        counts = [d[4] for d in lines]
        index_to_row = []
        for c in counts:
            index_to_row.extend([row] * c)
            row += 1
        return index, index_to_row
        
    def set_grid_cell_attr(self, grid, col, attr):
        ByteGridTable.set_grid_cell_attr(self, grid, col, attr)
        if col == 1:
            attr.SetReadOnly(False)
        else:
            attr.SetReadOnly(True)
    
    def get_index_range(self, r, c):
        line = self.lines[r]
        index = line[0] - self.start_addr
        return index, index + line[4]
    
    def is_index_valid(self, index):
        return index < len(self.segment)
    
    def get_row_col(self, index):
        try:
            row = self.index_to_row[index]
        except:
            row = self.index_to_row[-1]
        return row, 0

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
    
    def get_pc(self, row):
        return self.lines[row][0]

    def get_value_style(self, row, col):
        line = self.lines[row]
        index = line[0] - self.start_addr
        style = 0
        for i in range(line[4]):
            style |= self.segment.style[index + i]
        if col == 0:
            return " ".join("%02x" % i for i in line[1]), style
        return str(line[col + 1]), style
    
    def GetRowLabelValue(self, row):
        if self.lines:
            addr = self.get_pc(row)
            return "%04x" % addr
        return "0000"
    
    def GetValue(self, row, col):
        line = self.lines[row]
        if col == 0:
            return " ".join("%02x" % i for i in line[1])
        return str(line[col + 1])

    def ResetViewProcessArgs(self, grid, editor, *args):
        if editor is not None:
            self.set_editor(editor)
        else:
            self._rows = len(self.lines)


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

    def __init__(self, parent, task, **kwargs):
        """Create the HexEdit viewer
        """
        table = DisassemblyTable()
        ByteGrid.__init__(self, parent, task, table, **kwargs)
    
    def get_default_cell_editor(self):
        return AssemblerEditor(self)

    def perform_idle(self):
        if self.table.next_row >= 0:
            self.table.disassemble_next()
            self.table.ResetView(self, None)
    
    def restart_disassembly(self, index):
        self.table.restart_disassembly(index)
        
    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.
        
        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        try:
            pc = self.table.get_pc(row)
            cmd = text.upper()
            bytes = assemble_text(cmd, pc)
            start, _ = self.table.get_index_range(row, col)
            end = start + len(bytes)
            cmd = MiniAssemblerCommand(self.table.segment, start, end, bytes, cmd)
            self.task.active_editor.process_command(cmd)
            return True
        except AssemblyError, e:
            self.task.window.error(unicode(e))
            self.SetFocus()  # OS X quirk: return focus to the grid so the user can keep typing
        return False
    
    def search(self, search_text, match_case=False):
        lines = self.table.lines
        s = self.table.start_addr
        if not match_case:
            search_text = search_text.lower()
            matches = [(t[0] - s, t[0] - s + len(t[1])) for t in lines if search_text in t[3].lower()]
        else:
            matches = [(t[0] - s, t[0] - s + len(t[1])) for t in lines if search_text in t[3]]
        return matches
    
    def get_goto_action(self, r, c):
        index, _ = self.table.get_index_range(r, c)
        index_addr = self.table.get_pc(r)
        d = self.editor.disassembler(self.table.segment.data[index:], index_addr, -index_addr)
        next_addr, bytes, opstr, memloc, rw, addr_dest = d.disasm()
        segment_start = self.table.segment.start_addr
        segment_num = -1
        addr_index = addr_dest-segment_start
        if addr_dest is not None:
            if addr_dest < segment_start or addr_dest > segment_start + len(self.table.segment):
                segment_num, segment_dest, addr_index = self.editor.document.find_segment_in_range(addr_dest)
                if segment_dest is not None:
                    msg = "Go to address $%04x in segment %s" % (addr_dest, str(segment_dest))
                else:
                    msg = "Address $%04x not in any segment" % addr_dest
                    addr_dest = None
            else:
                msg = "Go to address $%04x" % addr_dest
        else:
            msg = "No address to jump to"
        if addr_dest is not None:
            goto_action = GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.task, active_editor=self.task.active_editor)
        else:
            goto_action = GotoIndexAction(name=msg, enabled=False, task=self.task)
        return goto_action
    
    def get_popup_actions(self, r, c):
        goto_action = self.get_goto_action(r, c)
        return [goto_action, None, CutAction, CopyAction, PasteAction, None, SelectAllAction, SelectNoneAction, GetSegmentFromSelectionAction]
