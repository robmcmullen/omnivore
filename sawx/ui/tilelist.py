import sys

import numpy as np
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.buttons as buttons

import logging
log = logging.getLogger(__name__)


class TileCategory(object):
    def __init__(self, name):
        self.name = name

    def get_height(self, parent):
        w, h = parent.GetTextExtent(self.name)
        return h + 5

    def draw(self, font, dc, rect):
        dc.DrawLabel(self.name, rect, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)


class Tile(object):
    def __init__(self, tile_num, keystroke):
        self.tile_num = tile_num
        self.keystroke = keystroke

    def get_bytes(self):
        return (self.tile_num, )  # has to be tuple so it's hashable

    def get_height(self, parent):
        if parent.editor:  # Might get called before an editor is set
            return parent.editor.machine.antic_font.get_height(parent.zoom)
        return 10

    def draw(self, parent, dc, rect):
        if parent.editor:  # Might get called before an editor is set
            bmp = parent.editor.machine.antic_font.get_image(self.tile_num, parent.zoom)
            dc.DrawBitmap(bmp, rect.x+10, rect.y)


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
        item.draw(self.GetParent(), dc, rect)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, n):
        item = self.GetParent().items[n]
        h = item.get_height(self.GetParent())
        return h


class TileListControl(wx.Panel):
    """
    View for displaying categories of tiles to paint the map
    """

    def __init__(self, parent, task, command=None, **kwargs):
        wx.Panel.__init__(self, parent, -1, **kwargs)
        self.task = task
        self.editor = None
        self.command_cls = command

        self.tile_list = TileListBox(self, -1, style=wx.VSCROLL)
        self.tile_list.Bind(wx.EVT_LEFT_DOWN, self.on_tile_clicked)
        self.tile_list.Bind(wx.EVT_LISTBOX, self.on_tile)
        self.cat = wx.Choice(self, -1)
        self.cat.Bind(wx.EVT_CHOICE, self.on_category)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.cat, 0, wx.EXPAND, 0)
        sizer.Add(self.tile_list, 1, wx.EXPAND, 0)
        self.SetSizer(sizer)
        self.Fit()

        self.pattern_to_index = {}
        self.parse_tile_map([("test", np.arange(0,10, dtype=np.uint8))])
        self.current_tile = -1
        self.setup_tiles()
        self.zoom = 2

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
                self.pattern_to_index[item.get_bytes] = i

    def setup_tiles(self):
        cats = [c[0].name for c in self.categories]
        self.cat.Set(cats)
        self.cat.SetSelection(0)
        self.tile_list.SetItemCount(len(self.items))
        self.tile_list.SetSelection(self.current_tile)

    def on_category(self, event):
        cat = event.GetSelection()
        item, index = self.categories[cat]
        self.tile_list.ScrollToRow(index)

    def on_tile_clicked(self, event):
        p = event.GetPosition()
        index = self.tile_list.HitTest(p)
        e = self.editor
        if e is not None:
            self.current_tile = index
            wx.CallAfter(e.set_current_draw_pattern, self.items[index].get_bytes(), self)

    def show_pattern(self, pattern):
        index = self.index_from_pattern.get(pattern, None)
        if index is not None:
            self.tile_list.SetSelection(index)
            self.tile_list.ScrollToRow(index)

    def clear_tile_selection(self):
        self.current_tile = -1
        self.tile_list.SetSelection(-1)

    def on_tile(self, event):
        index = event.GetInt()
        self.change_tile(self.items[index])

    def change_tile(self, tile):
        e = self.editor
        if e is None:
            return
        cmd_cls = self.command_cls
        if cmd_cls is None:
            return
        if e.can_copy:
            index = e.anchor_start_index
        else:
            index = e.caret_index
        value = tile.get_bytes()
        cmd = cmd_cls(e.segment, index, index+len(value), value, True)
        e.process_command(cmd)


class TileButton(buttons.GenBitmapToggleButton):
    labelDelta = 0
    label_border = 4
    bgClr = wx.Colour(255, 255, 255)
    faceDnClr = wx.Colour(100, 200, 230)

    def DoGetBestSize(self):
        """
        Overridden base class virtual.  Determines the best size of the
        button based on the label and bezel size.
        """
        w, h, useMin = self._GetLabelSize()
        width = w + self.label_border + 2 * self.bezelWidth + 4 * int(self.useFocusInd)
        height = h + self.label_border + 2 * self.bezelWidth + 4 * int(self.useFocusInd)
        return (width, height)

    def InitColours(self):
        pass

    def DrawBezel(self, dc, x1, y1, x2, y2):
        pass

    def GetBackgroundBrush(self, dc):
        """
        Returns the current :class:`wx.Brush` to be used to draw the button background.

        :param wx.DC `dc`: the device context used to draw the button background.
        """
        if self.up:
            col = self.bgColor
        else:
            col = self.faceDnClr
        brush = wx.Brush(col)
        return brush

    @classmethod
    def set_colors(cls, machine):
        cls.bgColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND)
        cls.faceDnClr = wx.Colour(*machine.highlight_color)
