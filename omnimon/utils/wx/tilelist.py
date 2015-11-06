import sys

import numpy as np
import wx

import logging
log = logging.getLogger(__name__)


class TileCategory(object):
    def __init__(self, name):
        self.name = name
    
    def get_height(self, parent):
        w, h = parent.GetTextExtent(self.name)
        return h + 5
    
    def draw(self, dc, rect):
        dc.DrawLabel(self.name, rect, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

class Tile(object):
    def __init__(self, tile_num, keystroke):
        self.tile_num = tile_num
        self.keystroke = keystroke
    
    def get_height(self, parent):
        return 20
    
    def draw(self, dc, rect):
        dc.DrawLabel("  *", rect, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)


class TileListBox(wx.VListBox):
    # This method must be overridden.  When called it should draw the
    # n'th item on the dc within the rect.  How it is drawn, and what
    # is drawn is entirely up to you.
    def OnDrawItem(self, dc, rect, n):
        if self.GetSelection() == n:
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            c = self.GetForegroundColour()
        dc.SetFont(self.GetFont())
        dc.SetTextForeground(c)
        item = self.GetParent().items[n]
        item.draw(dc, rect)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, n):
        item = self.GetParent().items[n]
        h = item.get_height(self)
        return h


class TileListControl(wx.Panel):
    """
    View for displaying categories of tiles to paint the map
    """

    def __init__(self, parent, task, **kwargs):
        wx.Panel.__init__(self, parent, -1, **kwargs)
        self.task = task
        self.editor = None
        
        self.tile_list = TileListBox(self, -1, style=wx.VSCROLL)
        self.cat = wx.Choice(self, -1)
        self.cat.Bind(wx.EVT_CHOICE, self.on_category)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.cat, 0, wx.EXPAND, 0)
        sizer.Add(self.tile_list, 1, wx.EXPAND, 0)
        self.SetSizer(sizer)
        self.Fit()
        
        self.parse_tile_map([("test", np.arange(0,10, dtype=np.uint8))])
        self.setup_tiles()

    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.parse_tile_map(editor.antic_tile_map)
            self.setup_tiles()
    
    def parse_tile_map(self, tile_map):
        self.tile_map = tile_map
        self.categories = []
        self.items = []
        for label, tiles in tile_map:
            item = TileCategory(label)
            self.categories.append((item, len(self.items)))
            self.items.append(item)
            for i in np.arange(np.alen(tiles)):
                item = Tile(tiles[i:i+1], "")
                self.items.append(item)
    
    def setup_tiles(self):
        cats = [c[0].name for c in self.categories]
        self.cat.Set(cats)
        self.cat.SetSelection(0)
        self.tile_list.SetItemCount(len(self.items))
        self.tile_list.SetSelection(0)
    
    def on_category(self, event):
        cat = event.GetSelection()
        item, index = self.categories[cat]
        self.tile_list.ScrollToRow(index)
