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
    
    def __init__(self, segment):
        ByteGridTable.__init__(self)
        
        self.disassembler = None
        self.set_segment(segment)

    def set_segment(self, segment):
        self.segment = segment
        lines = []
        addr_map = {}
        if self.disassembler is not None:
            d = self.disassembler(segment.data, segment.start_addr, -segment.start_addr)
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
   
    def GetRowLabelValue(self, row):
        line = self.lines[row]
        return "%04x" % line[0]
    
    def GetValue(self, row, col):
        line = self.lines[row]
        return str(line[col + 1])

    def SetValue(self, row, col, value):
        val=int(value,16)
        if val>=0 and val<256:
            bytes = chr(val)
        else:
            log.debug('SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value,val))
            
        i = self.get_index(row, col)
        end = loc + len(bytes)
        
        self.segment[i:end] = bytes

    def ResetViewProcessArgs(self, segment, *args):
        self.set_segment(segment)


class DisassemblyPanel(ByteGrid):
    """
    View for editing in hexidecimal notation.
    """

    def __init__(self, parent, task, segment=None):
        """Create the HexEdit viewer
        """
        if segment is None:
            segment = DefaultSegment()
        table = DisassemblyTable(segment)
        ByteGrid.__init__(self, parent, task, table)

    def set_segment(self, segment):
        self.table.ResetView(self, segment)
        self.table.UpdateValues(self)

    def set_disassembler(self, d):
        self.table.disassembler = d
    
    def pos_to_row(self, pos):
        addr = pos + self.GetTable().start_addr
        addr_map = self.GetTable().addr_to_lines
        if addr in addr_map:
            index = addr_map[addr]
        else:
            index = 0
            for a in range(addr - 1, addr - 5, -1):
                if a in addr_map:
                    index = addr_map[a]
                    break
        print "addr %s -> index=%d" % (addr, index)
        return index

    def select_pos(self, pos):
        print "make %s visible in disassembly!" % pos
        row = self.pos_to_row(pos)
        self.select_range(row, row)
        self.SetGridCursor(row, 0)
        self.MakeCellVisible(row, 0)
    
    def select_range(self, start, end):
        self.ClearSelection()
        self.anchor_index = start
        self.end_index = end
        self.ForceRefresh()
