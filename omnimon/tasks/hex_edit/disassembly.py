import sys
import wx

from omnimon.utils.wx.bytegrid import ByteGridTable, ByteGrid
from omnimon.utils.binutil import DefaultSegment

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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
    
    def get_index_range(self, r, c):
        line = self.lines[r]
        index = line[0] - self.start_addr
        return index, index + len(line[1]) - 1
    
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
    
    def GetRowLabelValue(self, row):
        if self.lines:
            line = self.lines[row]
            return "%04x" % line[0]
        return "0000"
    
    def GetValue(self, row, col):
        line = self.lines[row]
        if col == 0:
            return " ".join("%02x" % i for i in line[1])
        return str(line[col + 1])

    def SetValue(self, row, col, value):
        val=int(value,16)
        if val>=0 and val<256:
            bytes = chr(val)
        else:
            log.debug('SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value,val))
            
        i, _ = self.get_index_range(row, col)
        end = loc + len(bytes)
        
        self.segment[i:end] = bytes

    def ResetViewProcessArgs(self, editor, *args):
        self.set_editor(editor)


class DisassemblyPanel(ByteGrid):
    """
    View for editing in hexidecimal notation.
    """

    def __init__(self, parent, task):
        """Create the HexEdit viewer
        """
        table = DisassemblyTable()
        ByteGrid.__init__(self, parent, task, table)

    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.table.ResetView(self, editor)
            self.table.UpdateValues(self)
