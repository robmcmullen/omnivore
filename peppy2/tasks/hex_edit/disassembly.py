import sys
import wx

from wx.lib.agw import ultimatelistctrl as ULC


class DisassemblyPanel(ULC.UltimateListCtrl):

    """
    A panel for displaying and manipulating the properties of a layer.
    """
    LABEL_SPACING = 2
    VALUE_SPACING = 10
    SIDE_SPACING = 5

    def __init__(self, parent, task):
        self.task = task
        
        ULC.UltimateListCtrl.__init__(
            self, parent, -1, 
            agwStyle=wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_HRULES|wx.LC_VRULES|ULC.ULC_USER_ROW_HEIGHT
            )
        
#        # Mac/Win needs this, otherwise background color is black
#        attr = self.GetDefaultAttributes()
#        self.SetBackgroundColour(attr.colBg)
        
        self.disassembler = None
        self.lines = []
        self.start_addr = 0
        self.addr_to_lines = {}
        self.start_select = 0
        
        self.InsertColumn(0, "Addr")
        self.InsertColumn(1, "Bytes")
        self.InsertColumn(2, "Disassembly")
        self.InsertColumn(3, "Comment")
        self.SetColumnWidth(0, 75)
        self.SetColumnWidth(1, 100)
        self.SetColumnWidth(2, 175)
        self.SetColumnWidth(3, 500)
        self.SetUserLineHeight(10)

        self.SetItemCount(0)

        self.selected_attr = wx.ListItemAttr()
        self.selected_attr.SetBackgroundColour("cyan")

        self.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select)
        
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
        if self.lines:
            self.start_addr = self.lines[0][0]
        else:
            self.start_addr = 0
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
    
    def OnGetItemToolTip(self, item, col):
        return None

    def OnGetItemTextColour(self, item, col):
        return None

    def OnGetItemAttr(self, item):
        return None

    def event_coords_to_byte(self, ev):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        inside = True

        x = ev.GetX()
        y = ev.GetY()
        index, flags = self.HitTest((x, y))
        print "on index", index, "flags", flags
        if index == wx.NOT_FOUND:
            if flags is not None and flags & wx.LIST_HITTEST_NOWHERE:
                index = self.GetItemCount()
            else:
                inside = False
        if inside:
            byte = self.lines[index][0] - self.start_addr
        else:
            byte = 0
        return byte, 0, inside

    def on_mouse(self, ev):
        """Driver to process mouse events.

        This is the main driver to process all mouse events that
        happen on the BitmapScroller.  Once a selector is triggered by
        its event combination, it becomes the active selector and
        further mouse events are directed to its handler.
        """
        byte, bit, inside = self.event_coords_to_byte(ev)
        #log.debug(x, y, byte, bit, inside)
        
        if ev.LeftIsDown() and inside:
            wx.CallAfter(self.task.active_editor.byte_clicked, byte, bit, self.start_addr, self)
#        w = ev.GetWheelRotation()
#        if w < 0:
#            self.scroll_up()
#        elif w > 0:
#            self.scroll_down()

        ev.Skip()

    def on_select(self, ev):
        self.start_select = ev.GetIndex()

