#----------------------------------------------------------------------
# Name:         multisash
# Purpose:      Multi Sash control
#
# Author:       Gerrit van Dyk
#
# Created:      2002/11/20
# Version:      0.1
# License:      wxWindows license
#----------------------------------------------------------------------
# 12/09/2003 - Jeff Grimmett (grimmtooth@softhome.net)
#
# o 2.5 compatibility update.
#
# 12/20/2003 - Jeff Grimmett (grimmtooth@softhome.net)
#
# o wxMultiSash -> MultiSash
# o wxMultiSplit -> MultiSplit
# o wxMultiViewLeaf -> MultiViewLeaf
#
import json
from uuid import uuid4

import wx


import logging
#logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)
resize_log = logging.getLogger("resize")
#resize_log.setLevel(logging.DEBUG)


MV_HOR = 0
MV_VER = 1

SH_SIZE = 5
CR_SIZE = SH_SIZE * 3

#----------------------------------------------------------------------

class MultiSash(wx.Window):

    wxEVT_CLIENT_CLOSE = wx.NewEventType()
    EVT_CLIENT_CLOSE = wx.PyEventBinder(wxEVT_CLIENT_CLOSE, 1)

    wxEVT_CLIENT_ACTIVATED = wx.NewEventType()
    EVT_CLIENT_ACTIVATED = wx.PyEventBinder(wxEVT_CLIENT_ACTIVATED, 1)

    def __init__(self, *_args,**_kwargs):
        wx.Window.__init__(self, *_args, **_kwargs)
        self.live_update = True
        self.live_update_control = None
        self._defChild = EmptyChild
        self.child = MultiSplit(self,self,(0,0),self.GetSize())
        self.Bind(wx.EVT_SIZE,self.OnMultiSize)
        self.Bind(wx.EVT_MOTION,self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_UP,self.OnRelease)
        self.last_direction = MV_VER

    def OnMultiSize(self,evt):
        self.child.SetSize(self.GetSize())

    def UnSelect(self):
        self.child.UnSelect()

    def Clear(self):
        old = self.child
        self.child = MultiSplit(self,self,(0,0),self.GetSize())
        old.Destroy()
        self.child.OnSize(None)

    def get_layout(self, to_json=False, pretty=False):
        d = {'child': self.child.get_layout()}
        if to_json:
            if pretty:
                d = json.dumps(d, sort_keys=True, indent=4)
            else:
                d = json.dumps(d)
        return d

    def restore_layout(self, d):
        try:
            layout = d['child']
        except TypeError:
            d = json.loads(d)
            layout = d['child']
        old = self.child
        self.child = MultiSplit(self,self,wx.Point(0,0),self.GetSize())
        try:
            self.child.restore_layout(layout)
        except KeyError, e:
            log.error("Error loading layout: missing key %s. Restoring previous layout." % e.message)
            self.child.Destroy()
            self.child = old
        else:
            old.Destroy()
        self.OnMultiSize(None)
        self.child.OnSize(None)

    def update_captions(self):
        self.Refresh()

    def find_uuid(self, uuid):
        return self.child.find_uuid(uuid)

    def find_empty(self):
        return self.child.find_empty()

    def focus_uuid(self, uuid):
        found = self.find_uuid(uuid)
        if found:
            found.Select()

    def replace_by_uuid(self, control, u):
        found = self.find_uuid(u)
        if found is not None:
            found.replace(control, u)
            return True
        return False

    def add(self, control, u=None, direction=None, use_empty=True):
        if use_empty:
            found = self.find_empty()
            if found:
                found.replace(control, u)
                return
        if direction is None:
            self.last_direction = not self.last_direction
            direction = self.last_direction
        self.child.add(control, u, direction)

    def live_split(self, source, splitter, px, py, side):
        if side == MV_HOR:
            drag_parent, drag_leaf = splitter.AddLeaf(None, None, MV_VER, py)
        else:
            drag_parent, drag_leaf = splitter.AddLeaf(None, None, MV_HOR, px)
        print(splitter, drag_parent, drag_leaf)
        if side == MV_HOR:
            creator = drag_leaf.creatorHor
        else:
            creator = drag_leaf.creatorVer
        creator.drag_parent, creator.drag_leaf = drag_parent, drag_leaf 
        print("start_live_update", source, creator, creator.drag_parent, creator.drag_leaf)
        creator.isDrag = True
        self.live_update_control = creator
        self.CaptureMouse()

    def OnMouseMove(self,evt):
        if self.live_update_control:
            creator = self.live_update_control
            px, py = creator.ClientToScreen((evt.x, evt.y))
            px, py = creator.GetParent().ScreenToClient((px, py))
            log.debug("motion: %s" % str((px, py, self.HasCapture(), self.GetCapture(), self.GetCapture() == self)))
            if creator.side == MV_HOR:
                creator.drag_parent.SizeLeaf(creator.drag_leaf, py,not creator.side)
            else:
                creator.drag_parent.SizeLeaf(creator.drag_leaf, px,not creator.side)
        else:
            evt.Skip()

    def OnRelease(self,evt):
        if self.live_update_control:
            creator = self.live_update_control
            creator.isDrag = False
            self.ReleaseMouse()
        else:
            evt.Skip()


#----------------------------------------------------------------------


class MultiSplit(wx.Window):
    def __init__(self,multiView,parent,pos,size,view1 = None):
        wx.Window.__init__(self,id = -1,parent = parent,pos = pos,size = size,
                          style = wx.CLIP_CHILDREN)
        self.multiView = multiView
        self.view2 = None
        if view1:
            self.view1 = view1
            self.view1.Reparent(self)
            self.view1.Move(0,0)
        else:
            self.view1 = MultiViewLeaf(self.multiView,self,
                                         (0,0),self.GetSize())
        self.direction = None
        self.ratio = 0.5

        self.Bind(wx.EVT_SIZE,self.OnSize)

    def find_uuid(self, uuid):
        if self.view1:
            found = self.view1.find_uuid(uuid)
            if found is not None:
                return found
        if self.view2:
            found = self.view2.find_uuid(uuid)
            if found is not None:
                return found
        return None

    def find_empty(self):
        if self.view1:
            found = self.view1.find_empty()
            if found is not None:
                return found
        if self.view2:
            found = self.view2.find_empty()
            if found is not None:
                return found
        return None

    def add(self, control=None, u=None, direction=MV_HOR):
        if control is None:
            control = self.multiView._defChild(self)
        if not self.view2:
            self.add_view2(control, u, direction)
        elif isinstance(self.view2, MultiSplit):
            self.view2.add(control, u, direction)
        elif isinstance(self.view1, MultiSplit):
            self.view1.add(control, u, direction)
        else:
            self.AddLeaf(control, u, direction, self.view1)

    def get_layout(self):
        d = {}
        d['direction'] = self.direction
        if self.view1:
            d['view1'] = self.view1.get_layout()
            if isinstance(self.view1,MultiSplit):
                d['split1'] = True
        if self.view2:
            d['view2'] = self.view2.get_layout()
            if isinstance(self.view2,MultiSplit):
                d['split2'] = True
        d['ratio'] = self.calc_ratio()
        return d

    def restore_layout(self,d):
        self.direction = d['direction']
        self.ratio = d['ratio']
        w, h = self.GetSize()
        v1Data = d.get('view1',None)
        if v1Data:
            isSplit = d.get('split1',None)
            old = self.view1
            if isSplit:
                self.view1 = MultiSplit(self.multiView,self, (0,0),self.GetSize())
            else:
                self.view1 = MultiViewLeaf(self.multiView,self, (0,0),self.GetSize())
            self.view1.restore_layout(v1Data)
            if old:
                old.Destroy()
        v2Data = d.get('view2',None)
        if v2Data:
            isSplit = d.get('split2',None)
            old = self.view2
            if isSplit:
                self.view2 = MultiSplit(self.multiView,self, (0,0),self.GetSize())
            else:
                self.view2 = MultiViewLeaf(self.multiView,self, (0,0),self.GetSize())
            self.view2.restore_layout(v2Data)
            if old:
                old.Destroy()
        self.set_sizes_from_ratio(w, h)

    def UnSelect(self):
        if self.view1:
            self.view1.UnSelect()
        if self.view2:
            self.view2.UnSelect()

    def AddLeaf(self, control, u, direction, caller, pos=None):
        if self.view2:
            if caller == self.view1:
                self.view1 = MultiSplit(self.multiView,self,
                                          caller.GetPosition(),
                                          caller.GetSize(),
                                          caller)
                self.view1.AddLeaf(control, u, direction, caller, pos)
                split = self.view1
                view = split.view1
            else:
                self.view2 = MultiSplit(self.multiView,self,
                                          caller.GetPosition(),
                                          caller.GetSize(),
                                          caller)
                self.view2.AddLeaf(control, u, direction, caller, pos)
                split = self.view2
                view = split.view1
        else:
            view = self.add_view2(control, u, direction, pos)
            split = self
        self.multiView.update_captions()
        return split, view

    def add_view2(self, control, u, direction, pos=None):
        self.direction = direction
        w,h = self.GetSize()
        if pos is None:
            pos = h // 2 if direction == MV_VER else w // 2
        if direction == MV_HOR:
            x,y = (pos,0)
            w1,h1 = (w-pos,h)
            w2,h2 = (pos,h)
        else:
            x,y = (0,pos)
            w1,h1 = (w,h-pos)
            w2,h2 = (w,pos)
        self.view2 = MultiViewLeaf(self.multiView, self, (x,y), (w1,h1), control, u)
        self.view1.SetSize((w2,h2))
        self.view2.OnSize(None)
        return self.view2

    def DestroyLeaf(self,caller):
        if not self.view2:              # We will only have 2 windows if
            return                      # we need to destroy any
        parent = self.GetParent()       # Another splitview
        if parent == self.multiView:    # We'r at the root
            if caller == self.view1:
                old = self.view1
                self.view1 = self.view2
                self.view2 = None
                old.Destroy()
            else:
                self.view2.Destroy()
                self.view2 = None
            self.view1.SetSize(self.GetSize())
            self.view1.Move(self.GetPosition())
        else:
            w,h = self.GetSize()
            x,y = self.GetPosition()
            if caller == self.view1:
                if self == parent.view1:
                    parent.view1 = self.view2
                else:
                    parent.view2 = self.view2
                self.view2.Reparent(parent)
                self.view2.SetSize(x,y,w,h)
            else:
                if self == parent.view1:
                    parent.view1 = self.view1
                else:
                    parent.view2 = self.view1
                self.view1.Reparent(parent)
                self.view1.SetSize(x,y,w,h)
            self.view1 = None
            self.view2 = None
            self.Destroy()

    def calc_ratio(self):
        if self.view1 and self.view2:
            w1, h1 = self.view1.GetSize()
            w2, h2 = self.view2.GetSize()
            if self.direction == MV_HOR:
                ratio = 1.0 * w1 / (w1 + w2)
            else:
                ratio = 1.0 * h1 / (h1 + h2)
        else:
            ratio = 0.5
        return ratio

    def set_sizes_from_ratio(self, w, h):
        if self.view1 and self.view2:
            if self.direction == MV_HOR:
                w1 = int(self.ratio * w)
                w2 = w - w1
                h1 = h2 = h
                x2, y2 = w1, 0
            else:
                h1 = int(self.ratio * h)
                h2 = h - h1
                w1 = w2 = w
                x2, y2 = 0, h1
            self.view1.SetSize(0, 0, w1, h1)
            self.view2.SetSize(x2, y2, w2, h2)
        else:
            self.view1.SetSize(0, 0, w, h)
        if self.view1:
            self.view1.OnSize(None)
        if self.view2:
            self.view2.OnSize(None)

    def CanSize(self,side,view):
        if self.SizeTarget(side,view):
            return True
        return False

    def SizeTarget(self,side,view):
        if self.direction == side and self.view2 and view == self.view1:
            return self
        parent = self.GetParent()
        if parent != self.multiView:
            return parent.SizeTarget(side,self)
        return None

    def SizeLeaf(self,leaf,pos,side):
        if self.direction != side:
            return
        if not (self.view1 and self.view2):
            return
        if pos < 10: return
        w,h = self.GetSize()
        if side == MV_HOR:
            if pos > w - 10: return
        else:
            if pos > h - 10: return
        if w <= 0:
            self.ratio = 0.5
        elif side == MV_HOR:
            self.ratio = 1.0 * pos / w
        else:
            self.ratio = 1.0 * pos / h
        self.set_sizes_from_ratio(w, h)

    def OnSize(self,evt):
        w,h = self.GetSize()
        if not self.view2:
            self.view1.SetSize(0, 0, w, h)
            self.view1.OnSize(None)
            return
        self.set_sizes_from_ratio(w, h)


#----------------------------------------------------------------------


class MultiViewLeaf(wx.Window):
    def __init__(self,multiView,parent,pos,size, child=None, u=None):
        wx.Window.__init__(self,id = -1,parent = parent,pos = pos,size = size,
                          style = wx.CLIP_CHILDREN)
        self.multiView = multiView

        self.sizerHor = MultiSizer(self,MV_HOR)
        self.sizerVer = MultiSizer(self,MV_VER)
        if not self.multiView.live_update:
            self.creatorHor = MultiCreator(self,MV_HOR)
            self.creatorVer = MultiCreator(self,MV_VER)
        self.detail = MultiClient(self, child, u)
        if self.detail.use_close_button:
            self.closer = None
        else:
            self.closer = MultiCloser(self)

        self.Bind(wx.EVT_SIZE,self.OnSize)

        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))

    def find_uuid(self, uuid):
        if uuid == self.detail.child_uuid:
            log.debug("find_uuid: found %s in %s" % (uuid, self.detail.child.GetName()))
            return self.detail
        log.debug("find_uuid: skipping %s in %s" % (self.detail.child_uuid, self.detail.child.GetName()))
        return None

    def find_empty(self):
        if isinstance(self.detail.child, self.multiView._defChild):
            log.debug("find_empty: found %s" % (self.detail.child.GetName()))
            return self.detail
        log.debug("find_empty: skipping %s in %s" % (self.detail.child_uuid, self.detail.child.GetName()))
        return None

    def get_layout(self):
        d = {}
        if hasattr(self.detail.child,'get_layout'):
            attr = getattr(self.detail.child,'get_layout')
            if callable(attr):
                dData = attr()
                if dData:
                    h['detail'] = dData
        d['child_uuid'] = self.detail.child_uuid
        return d

    def restore_layout(self, d):
        old = self.detail
        self.detail = MultiClient(self, None, d['child_uuid'])
        dData = d.get('detail',None)
        if dData:
            if hasattr(self.detail.child,'restore_layout'):
                attr = getattr(self.detail.child,'restore_layout')
                if callable(attr):
                    attr(dData)
        old.Destroy()
        self.detail.OnSize(None)

    def UnSelect(self):
        self.detail.UnSelect()

    def get_multi_split(self):
        return self.GetParent()

    def AddLeaf(self, control, u, direction, pos=None):
        w,h = self.GetSize()
        if pos is None:
            pos = h // 2 if direction == MV_VER else w // 2
        if pos < 10: return
        if direction == MV_VER:
            if pos > h - 10: return
        else:
            if pos > w - 10: return
        return self.GetParent().AddLeaf(control, u, direction, self, pos)

    def DestroyLeaf(self):
        self.GetParent().DestroyLeaf(self)

    def SizeTarget(self,side):
        return self.GetParent().SizeTarget(side,self)

    def CanSize(self,side):
        return self.GetParent().CanSize(side,self)

    def OnSize(self,evt):
        def doresize():
            try:
                self.sizerHor.OnSize(evt)
                self.sizerVer.OnSize(evt)
                if not self.multiView.live_update:
                    self.creatorHor.OnSize(evt)
                    self.creatorVer.OnSize(evt)
                self.detail.OnSize(evt)
                if self.closer is not None:
                    self.closer.OnSize(evt)
            except:
                pass
        wx.CallAfter(doresize)

#----------------------------------------------------------------------


class MultiClient(wx.Window):
    use_title_bar = True
    use_close_button = True

    child_window_x = 2
    child_window_y = 2

    title_bar_height = 20
    title_bar_margin = 3
    title_bar_font = wx.NORMAL_FONT
    title_bar_font_height = None
    title_bar_x = None
    title_bar_y = None

    focused_color = wx.Colour(0x2e, 0xb5, 0xf4) # Blue
    focused_brush = None
    focused_text_color = wx.WHITE
    focused_pen = None

    unfocused_color = None
    unfocused_brush = None
    unfocused_text_color = wx.BLACK
    unfocused_pen = None

    title_font = wx.NORMAL_FONT

    close_button_size = (11, 11)

    def __init__(self, parent, child=None, uuid=None):
        w,h = self.CalcSize(parent)
        wx.Window.__init__(self,id = -1,parent = parent,
                          pos = (0,0),
                          size = (w,h),
                          style = wx.CLIP_CHILDREN | wx.SUNKEN_BORDER)
        if uuid is None:
            uuid = str(uuid4())
        self.child_uuid = uuid
        self.selected = False
        self.setup_paint()

        if self.use_title_bar:
            self.title_bar = TitleBar(self)

        top = self.GetParent().multiView

        if child is None:
            child = top._defChild(self)
        self.child = child
        self.child.Reparent(self)
        self.move_child()
        log.debug("Created client for %s" % self.child_uuid)

        self.Bind(wx.EVT_SET_FOCUS,self.OnSetFocus)
        self.Bind(wx.EVT_CHILD_FOCUS,self.OnChildFocus)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def do_send_event(self, evt):
        return not self.GetEventHandler().ProcessEvent(evt) or evt.IsAllowed()

    @classmethod
    def setup_paint(cls):
        if cls.title_bar_font_height is not None:
            return

        cls.unfocused_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        cls.focused_brush = wx.Brush(cls.focused_color, wx.SOLID)
        cls.unfocused_brush = wx.Brush(cls.unfocused_color, wx.SOLID)
        cls.focused_pen = wx.Pen(cls.focused_text_color)
        cls.unfocused_pen = wx.Pen(cls.unfocused_text_color)
        cls.focused_fill = wx.Brush(cls.focused_text_color, wx.SOLID)
        cls.unfocused_fill = wx.Brush(cls.unfocused_text_color, wx.SOLID)

        dc = wx.MemoryDC()
        dc.SetFont(cls.title_bar_font)
        cls.title_bar_font_height = max(dc.GetCharHeight(), 2)
        cls.title_bar_x = cls.title_bar_margin
        cls.title_bar_y = (cls.title_bar_height - cls.title_bar_font_height) // 2

    def get_paint_tools(self):
        if self.selected:
            brush = self.focused_brush
            pen = self.focused_pen
            fill = self.focused_fill
            text = self.focused_text_color
            textbg = self.focused_color
        else:
            brush = self.unfocused_brush
            pen = self.unfocused_pen
            fill = self.unfocused_fill
            text = self.unfocused_text_color
            textbg = self.unfocused_color
        return brush, pen, fill, text, textbg

    def draw_title_bar(self, dc):
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetPen(wx.TRANSPARENT_PEN)
        brush, _, _, text, textbg = self.get_paint_tools()
        dc.SetBrush(brush)

        w, h = self.GetSize()
        dc.SetFont(wx.NORMAL_FONT)
        dc.SetTextBackground(textbg)
        dc.SetTextForeground(text)
        dc.DrawRectangle(0, 0, w, self.title_bar_height)
        dc.DrawText(self.child.GetName(), self.title_bar_x, self.title_bar_y)

    def OnPaint(self, event):
        if self.use_title_bar:
            dc = wx.PaintDC(self)
            self.draw_title_bar(dc)

    def UnSelect(self):
        if self.selected:
            self.selected = False
            self.Refresh()

    def Select(self):
        self.GetParent().multiView.UnSelect()
        self.selected = True
        evt = MultiSashEvent(MultiSash.wxEVT_CLIENT_ACTIVATED, self)
        evt.SetChild(self.child)
        self.do_send_event(evt)
        self.child.SetFocus()
        self.Refresh()

    def CalcSize(self,parent):
        w,h = parent.GetSize()
        w -= SH_SIZE
        h -= SH_SIZE
        return (w,h)

    def OnSize(self,evt):
        w,h = self.CalcSize(self.GetParent())
        self.SetSize(0,0,w,h)
        w,h = self.GetClientSize()
        if self.use_title_bar:
            self.title_bar.SetSize((w, self.title_bar_height))
            self.child.SetSize((w, h - self.title_bar_height))
        else:
            self.child.SetSize((w - 2 * self.child_window_x, h - 2 * self.child_window_y))

    def replace(self, child, u=None):
        if self.child:
            self.child.Destroy()
            self.child = None
        self.child = child
        self.child.Reparent(self)
        if u is None:
            u = str(uuid4())
        self.child_uuid = u
        self.move_child()
        self.OnSize(None)

    def move_child(self):
        if self.use_title_bar:
            self.title_bar.Move(0, 0)
            self.child.Move(0, self.title_bar_height)
        else:
            self.child.Move(self.child_window_x, self.child_window_y)

    def OnSetFocus(self,evt):
        self.Select()

    def OnChildFocus(self,evt):
        self.OnSetFocus(evt)
##        from Funcs import FindFocusedChild
##        child = FindFocusedChild(self)
##        child.Bind(wx.EVT_KILL_FOCUS,self.OnChildKillFocus)


class TitleBar(wx.Window):
    def __init__(self, parent):
        wx.Window.__init__(self, parent, -1)
        self.client = parent

        button_index = 0
        self.buttons = []
        button_index += 1
        self.buttons.append(TitleBarCloser(self, button_index))
        top = self.client.GetParent().multiView
        button_index += 1
        self.buttons.append(TitleBarHSplitNewBot(self, button_index))
        button_index += 1
        self.buttons.append(TitleBarVSplitNewRight(self, button_index))

        self.SetBackgroundColour(wx.RED)
        self.hide_buttons()

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnLeave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.OnEnter)

    def draw_title_bar(self, dc):
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetPen(wx.TRANSPARENT_PEN)
        brush, _, _, text, textbg = self.client.get_paint_tools()
        dc.SetBrush(brush)

        w, h = self.GetSize()
        dc.SetFont(wx.NORMAL_FONT)
        dc.SetTextBackground(textbg)
        dc.SetTextForeground(text)
        dc.DrawRectangle(0, 0, w, h)
        dc.DrawText(self.client.child.GetName(), self.client.title_bar_x, self.client.title_bar_y)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.draw_title_bar(dc)

    def OnSize(self, evt):
        for button in self.buttons:
            x, y, w, h = button.CalcSizePos(self)
            button.SetSize(x, y, w, h)

    def hide_buttons(self):
        for b in self.buttons[1:]:
            if b: b.Hide()

    def show_buttons(self):
        for b in self.buttons[1:]:
            if b: b.Show()

    def OnEnter(self, evt):
        self.show_buttons()

    def OnLeave(self, evt):
        # check if left the window but still in the title bar, otherwise will
        # enter an endless cycle of leave/enter events as the buttons due to
        # the show/hide of the buttons being right under the cursor
        x, y = evt.GetPosition()
        w, h = self.GetSize()
        if x < 0 or x >= w or y < 0 or y >= h:
            self.hide_buttons()


#----------------------------------------------------------------------


class MultiSizer(wx.Window):
    def __init__(self,parent,side):
        self.side = side
        x,y,w,h = self.CalcSizePos(parent)
        wx.Window.__init__(self,id = -1,parent = parent,
                          pos = (x,y),
                          size = (w,h),
                          style = wx.CLIP_CHILDREN)

        self.px = None                  # Previous X
        self.py = None                  # Previous Y
        self.isDrag = False             # In Dragging
        self.dragTarget = None          # View being sized

        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnLeave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.OnEnter)
        self.Bind(wx.EVT_MOTION,self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN,self.OnPress)
        self.Bind(wx.EVT_LEFT_UP,self.OnRelease)

        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))


    def CalcSizePos(self,parent):
        pw,ph = parent.GetSize()
        if self.side == MV_HOR:
            x = CR_SIZE + 2
            y = ph - SH_SIZE
            w = pw - CR_SIZE - SH_SIZE - 2
            h = SH_SIZE
        else:
            x = pw - SH_SIZE
            y = CR_SIZE + 2 + SH_SIZE
            w = SH_SIZE
            h = ph - CR_SIZE - SH_SIZE - 4 - SH_SIZE # For Closer
        return (x,y,w,h)

    def OnSize(self,evt):
        x,y,w,h = self.CalcSizePos(self.GetParent())
        self.SetSize(x,y,w,h)

    def OnLeave(self,evt):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def OnEnter(self,evt):
        if not self.GetParent().CanSize(not self.side):
            return
        if self.side == MV_HOR:
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))

    def OnMouseMove(self,evt):
        if self.isDrag:
            top = self.GetParent().multiView
            if not top.live_update:
                DrawSash(self.dragTarget,self.px,self.py,self.side)
            self.px,self.py = self.ClientToScreen((evt.x, evt.y))
            self.px,self.py = self.dragTarget.ScreenToClient((self.px,self.py))
            if top.live_update:
                if self.side == MV_HOR:
                    self.dragTarget.SizeLeaf(self.GetParent(),
                                             self.py,not self.side)
                else:
                    self.dragTarget.SizeLeaf(self.GetParent(),
                                             self.px,not self.side)
            else:
                DrawSash(self.dragTarget,self.px,self.py,self.side)
        else:
            evt.Skip()

    def OnPress(self,evt):
        self.dragTarget = self.GetParent().SizeTarget(not self.side)
        if self.dragTarget:
            self.isDrag = True
            self.px,self.py = self.ClientToScreen((evt.x, evt.y))
            self.px,self.py = self.dragTarget.ScreenToClient((self.px,self.py))
            DrawSash(self.dragTarget,self.px,self.py,self.side)
            self.CaptureMouse()
        else:
            evt.Skip()

    def OnRelease(self,evt):
        if self.isDrag:
            self.ReleaseMouse()
            top = self.GetParent().multiView
            if not top.live_update:
                DrawSash(self.dragTarget,self.px,self.py,self.side)
                if self.side == MV_HOR:
                    self.dragTarget.SizeLeaf(self.GetParent(),
                                             self.py,not self.side)
                else:
                    self.dragTarget.SizeLeaf(self.GetParent(),
                                             self.px,not self.side)
            self.isDrag = False
            self.dragTarget = None
        else:
            evt.Skip()

#----------------------------------------------------------------------


class MultiCreator(wx.Window):
    def __init__(self,parent,side):
        self.side = side
        x,y,w,h = self.CalcSizePos(parent)
        wx.Window.__init__(self,id = -1,parent = parent,
                          pos = (x,y),
                          size = (w,h),
                          style = wx.CLIP_CHILDREN)

        self.px = None                  # Previous X
        self.py = None                  # Previous Y
        self.isDrag = False           # In Dragging

        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnLeave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.OnEnter)
        self.Bind(wx.EVT_MOTION,self.OnMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN,self.OnPress)
        self.Bind(wx.EVT_LEFT_UP,self.OnRelease)
        self.Bind(wx.EVT_PAINT,self.OnPaint)

    def CalcSizePos(self,parent):
        pw,ph = parent.GetSize()
        if self.side == MV_HOR:
            x = 2
            y = ph - SH_SIZE
            w = CR_SIZE
            h = SH_SIZE
        else:
            x = pw - SH_SIZE
            y = 4
            if not MultiClient.use_close_button:
                y += SH_SIZE             # Make provision for closer
            w = SH_SIZE
            h = CR_SIZE
        return (x,y,w,h)

    def OnSize(self,evt):
        x,y,w,h = self.CalcSizePos(self.GetParent())
        self.SetSize(x,y,w,h)

    def OnLeave(self,evt):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def OnEnter(self,evt):
        if self.side == MV_HOR:
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_POINT_LEFT))

    def OnMouseMove(self,evt):
        if self.isDrag:
            parent = self.GetParent()
            top = parent.multiView
            if not top.live_update:
                DrawSash(parent,self.px,self.py,self.side)
            self.px,self.py = self.ClientToScreen((evt.x, evt.y))
            self.px,self.py = parent.ScreenToClient((self.px,self.py))
            if top.live_update:
                if self.side == MV_HOR:
                    self.drag_parent.SizeLeaf(self.drag_leaf, self.py,not self.side)
                else:
                    self.drag_parent.SizeLeaf(self.drag_leaf, self.px,not self.side)
            else:
                DrawSash(parent,self.px,self.py,self.side)
        else:
            evt.Skip()

    def OnPress(self,evt):
        parent = self.GetParent()
        top = parent.multiView
        self.px,self.py = self.ClientToScreen((evt.x, evt.y))
        self.px,self.py = parent.ScreenToClient((self.px,self.py))
        if top.live_update:
            wx.CallAfter(top.live_split, self, parent, self.px, self.py, self.side)
        else:
            DrawSash(parent,self.px,self.py,self.side)
            self.isDrag = True
            self.CaptureMouse()

    def OnRelease(self,evt):
        if self.isDrag:
            self.isDrag = False
            self.ReleaseMouse()
            # print("left up", self.px, self.py, self.HasCapture(), self.GetCapture())
            parent = self.GetParent()
            top = parent.multiView
            if not top.live_update:
                DrawSash(parent,self.px,self.py,self.side)

                if self.side == MV_HOR:
                    parent.AddLeaf(None, None, MV_VER, self.py)
                else:
                    parent.AddLeaf(None, None, MV_HOR, self.px)
            self.drag_target = None
            self.drag_leaf = None
        else:
            evt.Skip()

    def OnPaint(self,evt):
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour(),wx.BRUSHSTYLE_SOLID))
        dc.Clear()

        highlight = wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHIGHLIGHT), 1, wx.PENSTYLE_SOLID)
        shadow = wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW), 1, wx.PENSTYLE_SOLID)
        black = wx.Pen(wx.BLACK,1,wx.PENSTYLE_SOLID)
        w,h = self.GetSize()
        w -= 1
        h -= 1

        # Draw outline
        dc.SetPen(highlight)
        dc.DrawLine(0,0, 0,h)
        dc.DrawLine(0,0, w,0)
        dc.SetPen(black)
        dc.DrawLine(0,h, w+1,h)
        dc.DrawLine(w,0, w,h)
        dc.SetPen(shadow)
        dc.DrawLine(w-1,2, w-1,h)

#----------------------------------------------------------------------


class MultiCloser(wx.Window):
    def __init__(self,parent):
        self.title_bar = parent
        self.client = parent.GetParent()
        self.splitter = self.client.GetParent()
        x,y,w,h = self.CalcSizePos(parent)
        wx.Window.__init__(self,id = -1,parent = parent,
                          pos = (x,y),
                          size = (w,h),
                          style = wx.CLIP_CHILDREN)

        self.down = False
        self.entered = False

        self.Bind(wx.EVT_LEFT_DOWN,self.OnPress)
        self.Bind(wx.EVT_LEFT_UP,self.OnRelease)
        self.Bind(wx.EVT_PAINT,self.OnPaint)
        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnLeave)
        self.Bind(wx.EVT_ENTER_WINDOW,self.OnEnter)

    def OnLeave(self,evt):
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        self.entered = False

    def OnEnter(self,evt):
        self.SetCursor(wx.Cursor(wx.CURSOR_BULLSEYE))
        self.entered = True

    def OnPress(self,evt):
        self.down = True
        evt.Skip()

    def OnRelease(self,evt):
        if self.down and self.entered:
            wx.CallAfter(self.title_bar.hide_buttons)
            self.do_action(evt)
        else:
            evt.Skip()
        self.down = False

    def do_action(self, evt):
        self.GetParent().DestroyLeaf()

    def OnPaint(self,evt):
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(wx.RED,wx.BRUSHSTYLE_SOLID))
        dc.Clear()

    def CalcSizePos(self,parent):
        pw,ph = parent.GetSize()
        x = pw - SH_SIZE
        w = SH_SIZE
        h = SH_SIZE + 2
        y = 1
        return (x,y,w,h)

    def OnSize(self,evt):
        x,y,w,h = self.CalcSizePos(self.title_bar)
        self.SetSize(x,y,w,h)


class TitleBarButton(MultiCloser):
    def __init__(self, parent, order):
        self.order = order
        MultiCloser.__init__(self, parent)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        size = self.GetClientSize()

        bg_brush, pen, fg_brush, _, _ = self.client.get_paint_tools()
        self.draw_button(dc, size, bg_brush, pen, fg_brush)

    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        print("draw")

    def OnLeave(self,evt):
        self.entered = False

    def OnEnter(self,evt):
        self.entered = True

    def do_action(self, evt):
        pass

    def CalcSizePos(self, parent):
        pw, ph = parent.GetClientSize()
        w, h = self.client.close_button_size
        x = pw - (w - self.client.title_bar_margin) * self.order * 2
        y = (self.client.title_bar_height - h) // 2
        return (x, y, w, h)


class TitleBarCloser(TitleBarButton):
    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        dc.SetBrush(bg_brush)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.SetPen(pen)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.DrawLine(0, 0, size.x, size.y)
        dc.DrawLine(0, size.y, size.x, 0)

    def do_action(self, evt):
        requested_close = self.ask_close()
        if requested_close:
            self.close()

    def ask_close(self):
        return True

    def close(self):
        self.splitter.DestroyLeaf()


class TitleBarVSplitNewRight(TitleBarCloser):
    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        split = size.x // 2
        dc.SetBrush(bg_brush)
        dc.SetPen(pen)
        dc.DrawRectangle(0, 0, split + 1, size.y)
        dc.SetBrush(fg_brush)
        dc.DrawRectangle(split, 0, size.x - split, size.y)

    def do_action(self, evt):
        self.splitter.AddLeaf(None, None, MV_HOR)


class TitleBarHSplitNewBot(TitleBarCloser):
    def draw_button(self, dc, size, bg_brush, pen, fg_brush):
        split = size.y // 2
        dc.SetBrush(bg_brush)
        dc.SetPen(pen)
        dc.DrawRectangle(0, 0, size.x, split + 1)
        dc.SetBrush(fg_brush)
        dc.DrawRectangle(0, split, size.x, size.y - split)

    def do_action(self, evt):
        self.splitter.AddLeaf(None, None, MV_VER)

#----------------------------------------------------------------------


class EmptyChild(wx.Window):
    def __init__(self,parent):
        wx.Window.__init__(self,parent,-1, style = wx.CLIP_CHILDREN)


#----------------------------------------------------------------------

# TODO: Switch to wx.Overlay instead of screen DC

def DrawSash(win,x,y,direction):
    dc = wx.ScreenDC()
    dc.StartDrawingOnTop(win)
    bmp = wx.Bitmap(8,8)
    bdc = wx.MemoryDC()
    bdc.SelectObject(bmp)
    bdc.DrawRectangle(-1,-1, 10,10)
    for i in range(8):
        for j in range(8):
            if ((i + j) & 1):
                bdc.DrawPoint(i,j)

    brush = wx.Brush(wx.Colour(0,0,0))
    brush.SetStipple(bmp)

    dc.SetBrush(brush)
    dc.SetLogicalFunction(wx.XOR)

    body_w,body_h = win.GetClientSize()

    if y < 0:
        y = 0
    if y > body_h:
        y = body_h
    if x < 0:
        x = 0
    if x > body_w:
        x = body_w

    if direction == MV_HOR:
        x = 0
    else:
        y = 0

    x,y = win.ClientToScreen((x,y))

    w = body_w
    h = body_h

    if direction == MV_HOR:
        dc.DrawRectangle(x,y-2, w,4)
    else:
        dc.DrawRectangle(x-2,y, 4,h)

    dc.EndDrawingOnTop()


class MultiSashEvent(wx.PyCommandEvent):
    """
    This event class is almost the same as `wx.SplitterEvent` except
    it adds an accessor for the sash index that is being changed.  The
    same event type IDs and event binders are used as with
    `wx.SplitterEvent`.
    """
    def __init__(self, type=wx.wxEVT_NULL, splitter=None):
        """
        Constructor.

        Used internally by wxWidgets only.

        :param `eventType`:
        :type `eventType`: EventType
        :param `splitter`:
        :type `splitter`: SplitterWindow

        """
        wx.PyCommandEvent.__init__(self, type)
        if splitter:
            self.SetEventObject(splitter)
            self.SetId(splitter.GetId())
        self.child = None
        self.isAllowed = True

    def SetChild(self, child):
        """
        The MultiClient that is reporting the event

        :param `client`: MultiClient instance

        """
        self.child = child

    def GetChild(self):
        """
        The MultiClient that is reporting the event

        :param `client`: MultiClient instance

        """
        return self.child

    def SetSashPosition(self, pos):
        """
        In the case of ``wxEVT_SPLITTER_SASH_POS_CHANGED`` events, sets the
        new sash position.

        In the case of ``wxEVT_SPLITTER_SASH_POS_CHANGING`` events, sets the
        new tracking bar position so visual feedback during dragging will
        represent that change that will actually take place. Set to -1 from
        the event handler code to prevent repositioning.

        May only be called while processing ``wxEVT_SPLITTER_SASH_POS_CHANGING``
        and ``wxEVT_SPLITTER_SASH_POS_CHANGED`` events.

        :param int `pos`: New sash position.

        """
        self.sashPos = pos

    def GetSashIdx(self):
        """
        Returns the new sash index.

        May only be called while processing ``wxEVT_SPLITTER_SASH_POS_CHANGING``
        and  ``wxEVT_SPLITTER_SASH_POS_CHANGED`` events.

        :rtype: `int`

        """
        return self.sashIdx

    def GetSashPosition(self):
        """
        Returns the new sash position.

        May only be called while processing ``wxEVT_SPLITTER_SASH_POS_CHANGING``
        and  ``wxEVT_SPLITTER_SASH_POS_CHANGED`` events.

        :rtype: `int`

        """
        return self.sashPos

    # methods from wx.NotifyEvent
    def Veto(self):
        """
        Prevents the change announced by this event from happening.

        It is in general a good idea to notify the user about the reasons
        for vetoing the change because otherwise the applications behaviour
        (which just refuses to do what the user wants) might be quite
        surprising.

        """
        self.isAllowed = False

    def Allow(self):
        """
        This is the opposite of :meth:`Veto` : it explicitly allows the
        event to be processed.

        For most events it is not necessary to call this method as the events
        are allowed anyhow but some are forbidden by default (this will be
        mentioned in the corresponding event description).

        """
        self.isAllowed = True

    def IsAllowed(self):
        """
        Returns ``True`` if the change is allowed (:meth:`Veto` hasn't been
        called) or ``False`` otherwise (if it was).

        :rtype: `bool`

        """
        return self.isAllowed


#For testing
if __name__ == '__main__':
    import sys

    class SizeReportCtrl(wx.Control):

        def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                    size=wx.DefaultSize):

            wx.Control.__init__(self, parent, id, pos, size, style=wx.NO_BORDER)
            self.Bind(wx.EVT_PAINT, self.OnPaint)
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
            self.Bind(wx.EVT_SIZE, self.OnSize)

        def OnPaint(self, event):
            dc = wx.PaintDC(self)
            size = self.GetClientSize()

            s = "Size: %d x %d"%(size.x, size.y)

            dc.SetFont(wx.NORMAL_FONT)
            w, height = dc.GetTextExtent(s)
            height += 3
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.SetPen(wx.WHITE_PEN)
            dc.DrawRectangle(0, 0, size.x, size.y)
            dc.SetPen(wx.LIGHT_GREY_PEN)
            dc.DrawLine(0, 0, size.x, size.y)
            dc.DrawLine(0, size.y, size.x, 0)
            dc.DrawText(s, (size.x-w)/2, (size.y-height*5)/2)
            pos = self.GetPosition()
            s = "Position: %d, %d" % (pos.x, pos.y)
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*3))

        def OnEraseBackground(self, event):
            pass

        def OnSize(self, event):
            size = self.GetClientSize()
            s = "Size: %d x %d"%(size.x, size.y)
            self.SetName(s)
            self.Refresh()

    def save_state(evt):
        global multi, json_text

        json_text.SetValue(multi.get_layout(True, True))

    def load_state(evt):
        global multi, json_text

        state = json_text.GetValue()
        multi.restore_layout(state)

    def find_uuid(evt):
        global multi, uuid_text

        u = uuid_text.GetValue()
        multi.focus_uuid(u)

    def replace_uuid(u):
        found = multi.find_uuid(u)
        if found is not None:
            test = EmptyChild(multi)
            found.replace(test)

    def add_control(evt):
        test = EmptyChild(multi)
        multi.add(test)

    app = wx.App()
    frame = wx.Frame(None, -1, "Test", size=(800,400))
    multi = MultiSash(frame, -1, pos = (0,0), size = (640,480))
    sizer = wx.BoxSizer(wx.VERTICAL)
    horz = wx.BoxSizer(wx.HORIZONTAL)
    horz.Add(multi, 1, wx.EXPAND)
    json_text = wx.TextCtrl(frame, -1, size=(400,400), style=wx.TE_MULTILINE)
    horz.Add(json_text, 0, wx.EXPAND)
    bsizer = wx.BoxSizer(wx.HORIZONTAL)
    btn = wx.Button(frame, -1, "Show State")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, save_state)
    btn = wx.Button(frame, -1, "Load State")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, load_state)
    uuid_text = wx.TextCtrl(frame, -1)
    bsizer.Add(uuid_text, 0, wx.EXPAND)
    btn = wx.Button(frame, -1, "Find UUID")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, find_uuid)
    btn = wx.Button(frame, -1, "Add Control")
    bsizer.Add(btn, 0, wx.EXPAND)
    btn.Bind(wx.EVT_BUTTON, add_control)

    sizer.Add(horz, 1, wx.EXPAND)
    sizer.Add(bsizer, 0, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show(True)

    try:
        state = sys.argv[1]
    except IndexError:
        pass
    else:
        text = open(state, 'r').read()
        print text
        multi.restore_layout(text)

        try:
            u = sys.argv[2]
        except IndexError:
            pass
        else:
            print("searching for %s" % u)
            wx.CallAfter(replace_uuid, u)

    app.MainLoop()
