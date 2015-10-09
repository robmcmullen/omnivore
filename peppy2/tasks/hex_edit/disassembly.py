import sys
import wx

class DisassemblyPanel(wx.ListCtrl):

    """
    A panel for displaying and manipulating the properties of a layer.
    """
    LABEL_SPACING = 2
    VALUE_SPACING = 10
    SIDE_SPACING = 5

    def __init__(self, parent, task):
        self.task = task
        
        wx.ListCtrl.__init__(
            self, parent, -1, 
            style=wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_HRULES|wx.LC_VRULES
            )
        
#        # Mac/Win needs this, otherwise background color is black
#        attr = self.GetDefaultAttributes()
#        self.SetBackgroundColour(attr.colBg)
        
        self.disassembler = None
        self.lines = []
        self.addr_to_lines = {}
        
        self.InsertColumn(0, "Addr")
        self.InsertColumn(1, "Bytes")
        self.InsertColumn(2, "Disassembly")
        self.InsertColumn(3, "Comment")
        self.SetColumnWidth(0, 75)
        self.SetColumnWidth(1, 100)
        self.SetColumnWidth(2, 175)
        self.SetColumnWidth(3, 500)

        self.SetItemCount(0)

    
    def set_disassembler(self, disassembler):
        self.disassembler = disassembler
    
    def set_segment(self, segment):
        d = self.disassembler(segment.data, segment.start_addr, -segment.start_addr)
        lines = []
        addr_map = {}
        for i, (addr, bytes, opstr, comment) in enumerate(d.get_disassembly()):
            lines.append((addr, bytes, opstr, comment))
            addr_map[addr] = i
        self.lines = lines
        self.addr_to_lines = addr_map
        self.SetItemCount(len(lines))
    
    def select_pos(self, addr):
        print "make %s visible in disassembly!" % addr
        addr_map = self.addr_to_lines
        if addr in addr_map:
            index = addr_map[addr]
        else:
            index = 0
            for a in range(addr - 1, addr - 5, -1):
                if a in addr_map:
                    index = addr_map[a]
                    break
        print "addr %s -> index=%d" % (addr, index)
        self.EnsureVisible(index)
        
    def OnGetItemText(self, item, col):
        line = self.lines[item]
        if col == 0:
            return "%04x" % line[col]
        return line[col]

