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
        return [self.tile_num]
    
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
        print p, index, self.items[index]
        e = self.editor
        if e is not None:
            self.current_tile = index
            e.set_current_draw_pattern(self.items[index].get_bytes(), self)
            self.tile_list.SetSelection(index)
    
    def clear_tile_selection(self):
        self.current_tile = -1
        self.tile_list.SetSelection(-1)
    
    def on_tile(self, event):
        index = event.GetInt()
        print index, self.items[index]
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
            index = e.cursor_index
        value = tile.get_bytes()
        cmd = cmd_cls(e.segment, index, index+len(value), value, True)
        e.process_command(cmd)


class TileButton(buttons.GenBitmapToggleButton):
    labelDelta = 0
    label_border = 4
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
    
    @classmethod
    def set_colors(cls, editor):
        cls.faceDnClr = wx.Colour(*editor.machine.highlight_color)

class TileWrapControl(wx.Panel):
    """
    View for displaying categories of tiles to paint the map
    """

    def __init__(self, parent, task, command=None, **kwargs):
        wx.Panel.__init__(self, parent, -1, **kwargs)
        self.task = task
        self.editor = None
        self.command_cls = command
        
        self.cat = wx.Choice(self, -1)
        self.cat.Bind(wx.EVT_CHOICE, self.on_category)
        self.panel = scrolled.ScrolledPanel(self, -1, style=wx.VSCROLL)
        self.panel.Bind(wx.EVT_SIZE, self.panel_size)
        psiz = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(psiz)
        self.panel.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_ALWAYS)
        self.panel.SetupScrolling(scroll_x=False)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.cat, 0, wx.EXPAND, 0)
        sizer.Add(self.panel, 1, wx.EXPAND, 0)
        self.SetSizer(sizer)
        self.Fit()
        
        self.parse_tile_map(self.panel, [("test", np.arange(0,10, dtype=np.uint8))])
        self.current_tile = None
        self.setup_tiles()
        self.zoom = 2
    
    def panel_size(self, evt):
        size = self.panel.GetSize()
        vsize = self.panel.GetVirtualSize()
        self.panel.SetVirtualSize((size[0] - 20, vsize[1]))

    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.parse_tile_map(self.panel, editor.antic_tile_map)
            self.setup_tiles()
            TileButton.set_colors(editor)
    
    def parse_tile_map(self, panel, tile_map):
        sizer = panel.GetSizer()
        sizer.DeleteWindows()
        self.tile_map = tile_map
        self.categories = []
        self.items = []
        for items in tile_map:
            label = items[0]
            t = wx.StaticText(panel, -1, label)
            sizer.Add(t, 0, wx.EXPAND, 0)
            self.categories.append(t)
            w = wx.WrapSizer()
            for tiles in items[1:]:
                for i in np.arange(np.alen(tiles)):
                    if self.editor:
                        data = tiles[i:i+1]
                        bmp = self.editor.machine.antic_font.get_image(data[0], self.zoom)
                        btn = TileButton(panel, -1, bmp, style=wx.BORDER_NONE|wx.BU_EXACTFIT)
                        btn.tile_data = data
                        btn.Bind(wx.EVT_BUTTON, self.on_tile_clicked)
                        w.Add(btn, 0, wx.ALL, 0)
                        self.items.append(btn)
            sizer.Add(w, 0, wx.EXPAND, 0)
        self.Layout()
    
    def setup_tiles(self):
        cats = [str(c.GetLabelText()) for c in self.categories]
        self.cat.Set(cats)
        self.cat.SetSelection(0)
    
    def on_category(self, event):
        cat = event.GetSelection()
        label = self.categories[cat]
        #self.panel.ScrollChildIntoView(label)
        sppu_x, sppu_y = self.panel.GetScrollPixelsPerUnit()
        vs_x, vs_y = self.panel.GetViewStart()
        cr = label.GetRect()
        print cr
        self.panel.Scroll(0, vs_y + (cr.y / sppu_y))
    
    def on_tile_clicked(self, event):
        btn = event.GetEventObject()
        e = self.editor
        if e is not None:
            self.current_tile = btn
            e.set_current_draw_pattern(btn.tile_data, self)
            self.clear_toggle_except(btn)
    
    def clear_tile_selection(self):
        self.current_tile = None
        self.clear_toggle_except()
    
    def clear_toggle_except(self, btn=None):
        for b in self.items:
            if b != btn:
                b.SetToggle(False)
    
    def on_tile(self, event):
        index = event.GetInt()
        print index, self.items[index]
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
            index = e.cursor_index
        value = tile.get_bytes()
        cmd = cmd_cls(e.segment, index, index+len(value), value, True)
        e.process_command(cmd)




if __name__ == '__main__':
    import sys
    sys.path[0:0] = [".."]
    print sys.path
    import fonts
    import colors
    
    class Wrapper(object):
        def __init__(self, **kwargs):
            for k, v in kwargs.iteritems():
                setattr(self, k, v)
        
        def set_current_draw_pattern(self, *args, **kwargs):
            pass
        
    
    class MyFrame(wx.Frame):
        def __init__(self, parent, id, title):
            wx.Frame.__init__(self, parent, id, title, wx.DefaultPosition, wx.DefaultSize)
            tile_map = [
            ("road", [0x70]),
            ("trees", range(0x80, 0x96), range(0x01, 0x16),),
            ("buildings", range(0x96, 0x9f), range(0x16, 0x1f), range(0x41, 0x51), range(0x5d, 0x60),),
            ("people", range(0xf1, 0xf4), range(0x71, 0x74)),
            ("water", range(0x2e, 0x41),),
            ("bridges", range(0x69, 0x6d),),
            ("vehicles", range(0x51, 0x59),),
            ("airport", range(0x60, 0x68), [0x5f], range(0x59, 0x5d), range(0xd9, 0xdd)), 
            ("golf", range(0xa9, 0xae),),
            ("other", [0x20, 0x25, 0x26, ]),
            ("special", range(0x21, 0x25), range(0x74, 0x76),), 
                ]
            color_converter = colors.gtia_ntsc_to_rgb
            highlight_color = (100, 200, 230)
            unfocused_cursor_color = (128, 128, 128)
            background_color = (255, 255, 255)
            match_background_color = (255, 255, 180)
            comment_background_color = (255, 180, 200)
            antic_font = fonts.AnticFont(fonts.A8DefaultFont, 4, colors.powerup_colors(), highlight_color, match_background_color, comment_background_color, color_converter)
            editor = Wrapper(antic_font=antic_font, antic_tile_map=tile_map, highlight_color=highlight_color)
            task = Wrapper(active_editor=editor)
            panel = TileWrapControl(self, task)
            panel.recalc_view()

    class MyApp(wx.App):
        def OnInit(self):
            frame = MyFrame(None, -1, 'test')
            frame.Show(True)
            frame.Center()
            return True

    app = MyApp(0)
    app.MainLoop()
