import sys
import wx

from omnimon.utils.wx.bytegrid import ByteGridTable, ByteGrid, HexTextCtrl, HexCellEditor
from omnimon.utils.binutil import DefaultSegment

from omnimon.third_party.asm6502 import assemble_text

from commands import ChangeByteCommand

import logging
log = logging.getLogger(__name__)


class DisassemblyTable(ByteGridTable):
    column_labels = ["Bytes", "Disassembly", "Comment"]
    column_sizes = [8, 12, 20]
    
    def __init__(self):
        ByteGridTable.__init__(self)
        self.lines = []
        self._rows = 0
        self.addr_to_lines = {}
        self.start_addr = 0

    def set_editor(self, editor):
        self.editor = editor
        self.segment = segment = self.editor.segment
        lines = []
        addr_map = {}
        d = editor.disassembler(segment.data, segment.start_addr, -segment.start_addr)
        for i, (addr, bytes, opstr, comment) in enumerate(d.get_disassembly()):
            lines.append((addr, bytes, opstr, comment))
            addr_map[addr] = i
        self.lines = lines
        self.addr_to_lines = addr_map
        if self.lines:
            self.start_addr = self.lines[0][0]
        else:
            self.start_addr = 0

        self._rows = len(self.lines)
    
    def set_grid_cell_attr(self, grid, col, attr):
        ByteGridTable.set_grid_cell_attr(self, grid, col, attr)
        if col == 1:
            attr.SetReadOnly(False)
        else:
            attr.SetReadOnly(True)
    
    def get_index_range(self, r, c):
        line = self.lines[r]
        index = line[0] - self.start_addr
        return index, index + len(line[1])
    
    def is_index_valid(self, index):
        return index < len(self.segment)
    
    def get_row_col(self, index):
        addr = index + self.start_addr
        addr_map = self.addr_to_lines
        if addr in addr_map:
            row = addr_map[addr]
        else:
            row = 0
            for a in range(addr - 1, addr - 5, -1):
                if a in addr_map:
                    row = addr_map[a]
                    break
        print "addr %s -> row=%d" % (addr, row)
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

    def SetValue(self, row, col, value):
        print "VALUE!!!!!", value
        return True

    def ResetViewProcessArgs(self, editor, *args):
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
        print "CREATED ASSEMBLEREDITOR"
        self._tc = AssemblerTextCtrl(parent, id, self.parentgrid)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)

    def EndEdit(self, row, col, grid, old_val):
        """
        Complete the editing of the current cell. Returns True if the value
        has changed.  If necessary, the control may be destroyed.
        *Must Override*
        """
        log.debug("row,col=(%d,%d)" % (row, col))
        changed = False

        val = self._tc.GetValue()
        
        if val != self.startValue:
            print "GRID!!!", grid
            changed = grid.change_value(row, col, val) # update the table

        self.startValue = ''
        self._tc.SetValue('')
        return changed


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
        print "SET CELL EDITOR"
        return AssemblerEditor(self)

    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.table.ResetView(self, editor)
            self.table.UpdateValues(self)
    
    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.
        
        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        print "HERE!!!!"
        try:
            pc = self.table.get_pc(row)
            bytes = assemble_text(text.upper(), pc)
            start, _ = self.table.get_index_range(row, col)
            end = start + len(bytes)
            cmd = ChangeByteCommand(self.table.segment, start, end, bytes)
            self.task.active_editor.process_command(cmd)
            return True
        except ValueError:
            pass
        return False
