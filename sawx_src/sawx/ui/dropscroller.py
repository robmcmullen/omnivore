#-----------------------------------------------------------------------------
# Name:        dropscroller.py
# Purpose:     auto scrolling for a list that's being used as a drop target
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007-2016 Rob McMullen
# License:     wxPython
#-----------------------------------------------------------------------------
"""
Automatic scrolling mixin for a list control, including an indicator
showing where the items will be dropped.

It would be nice to have somethin similar for a tree control as well,
but I haven't tackled that yet.
"""
import sys, pickle

import wx


class ListDropScrollerMixin(object):
    """Automatic scrolling for ListCtrls for use when using drag and drop.

    This mixin is used to automatically scroll a list control when
    approaching the top or bottom edge of a list.  Currently, this
    only works for lists in report mode.

    Add this as a mixin in your list, and then call processListScroll
    in your DropTarget's OnDragOver method.  When the drop ends, call
    finishListScroll to clean up the resources (i.e. the wx.Timer)
    that the dropscroller uses and make sure that the insertion
    indicator is erased.

    The parameter interval is the delay time in milliseconds between
    list scroll steps.

    If indicator_width is negative, then the indicator will be the
    width of the list.  If positive, the width will be that number of
    pixels, and zero means to display no indicator.
    """

    def __init__(self, interval=200, width=-1):
        """Don't forget to call this mixin's init method in your List.

        Interval is in milliseconds.
        """
        self._auto_scroll_timer = None
        self._auto_scroll_interval = interval
        self._auto_scroll = 0
        self._auto_scroll_save_y = -1
        self._auto_scroll_save_width = width
        self._auto_scroll_last_state = 0
        self._auto_scroll_last_index = -1
        self._auto_scroll_indicator_line = True
        self.Bind(wx.EVT_TIMER, self.OnAutoScrollTimer)

    def clearAllSelected(self):
        """clear all selected items"""
        list_count = self.GetItemCount()
        for index in range(list_count):
            self.SetItemState(index, 0, wx.LIST_STATE_SELECTED)

    def _startAutoScrollTimer(self, direction = 0):
        """Set the direction of the next scroll, and start the
        interval timer if it's not already running.
        """
        if self._auto_scroll_timer == None:
            self._auto_scroll_timer = wx.Timer(self, wx.TIMER_ONE_SHOT)
            self._auto_scroll_timer.Start(self._auto_scroll_interval)
        self._auto_scroll = direction

    def _stopAutoScrollTimer(self):
        """Clean up the timer resources.
        """
        self._auto_scroll_timer = None
        self._auto_scroll = 0

    def _getAutoScrollDirection(self, index):
        """Determine the scroll step direction that the list should
        move, based on the index reported by HitTest.
        """
        first_displayed = self.GetTopItem()

        if first_displayed == index:
            # If the mouse is over the first index...
            if index > 0:
                # scroll the list up unless...
                return -1
            else:
                # we're already at the top.
                return 0
        elif index >= first_displayed + self.GetCountPerPage() - 1:
            # If the mouse is over the last visible item, but we're
            # not at the last physical item, scroll down.
            return 1
        # we're somewhere in the middle of the list.  Don't scroll
        return 0

    def getDropIndex(self, x, y, index=None, flags=None, insert=True):
        """Find the index to insert the new item, which could be
        before or after the index passed in.
        
        @return: if insert is true, return value is the index of the insert
        point (i.e.  the new data should be inserted at that point, pushing
        the existing data further down the list).  If insert is false, the
        return value is the item on which the drop happened, or -1 indicating
        an invalid drop.
        """
        if index is None:
            index, flags = self.HitTest((x, y))

        # Not clicked on an item
        if index == wx.NOT_FOUND:

            # If it's an empty list or below the last item
            if (flags & (wx.LIST_HITTEST_NOWHERE|wx.LIST_HITTEST_ABOVE|wx.LIST_HITTEST_BELOW)):

                # Append to the end of the list or return an invalid index
                if insert:
                    index = self.GetItemCount()
                else:
                    index = self.GetItemCount() - 1
                #print "getDropIndex: append to end of list: index=%d" % index
            elif (self.GetItemCount() > 0):
                if y <= self.GetItemRect(0).y: # clicked just above first item
                    index = 0 # append to top of list
                    #print "getDropIndex: before first item: index=%d, y=%d, rect.y=%d" % (index, y, self.GetItemRect(0).y)
                elif insert:
                    index = self.GetItemCount() # append to end of list
                    #print "getDropIndex: after last item: index=%d" % index
                else:
                    index = self.GetItemCount() - 1

        # Otherwise, we've clicked on an item.  If we're in insert mode, check
        # to see if the cursor is between items
        elif insert:
            # Get bounding rectangle for the item the user is dropping over.
            rect = self.GetItemRect(index)
            #print "getDropIndex: landed on %d, y=%d, rect=%s" % (index, y, rect)

            # NOTE: On all platforms, the y coordinate used by HitTest
            # is relative to the scrolled window.  There are platform
            # differences, however, because on GTK the top of the
            # vertical scrollbar stops below the header, while on MSW
            # the top of the vertical scrollbar is equal to the top of
            # the header.  The result is the y used in HitTest and the
            # y returned by GetItemRect are offset by a certain amount
            # on GTK.  The HitTest's y=0 in GTK corresponds to the top
            # of the first item, while y=0 on MSW is in the header.

            # From Robin Dunn: use GetMainWindow on the list to find
            # the actual window on which to draw
            if self != self.GetMainWindow():
                y += self.GetMainWindow().GetPosition().Get()[1]

            # If the user is dropping into the lower half of the rect,
            # we want to insert _after_ this item.
            if y >= (rect.y + rect.height/2):
                index = index + 1

        return index

    def processListScroll(self, x, y, line=True):
        """Main handler: call this with the x and y coordinates of the
        mouse cursor as determined from the OnDragOver callback.

        This method will determine which direction the list should be
        scrolled, and start the interval timer if necessary.
        """
        if self.GetItemCount() == 0:
            # don't show any lines if we don't have any items in the list
            return

        index, flags = self.HitTest((x, y))

        direction = self._getAutoScrollDirection(index)
        if direction == 0:
            self._stopAutoScrollTimer()
        else:
            self._startAutoScrollTimer(direction)
        self._auto_scroll_indicator_line = line

        drop_index = self.getDropIndex(x, y, index=index, flags=flags)
        if line:
            self._processLineIndicator(x, y, drop_index)
        else:
            self._processHighlightIndicator(drop_index)

    def _processLineIndicator(self, x, y, drop_index):
        count = self.GetItemCount()
        if drop_index >= count:
            index = min(count, drop_index)
            rect = self.GetItemRect(index - 1)
            y = rect.y + rect.height + 1
        else:
            rect = self.GetItemRect(drop_index)
            y = rect.y

        # From Robin Dunn: on GTK & MAC the list is implemented as
        # a subwindow, so have to use GetMainWindow on the list to
        # find the actual window on which to draw
        if self != self.GetMainWindow():
            y -= self.GetMainWindow().GetPosition().Get()[1]

        if self._auto_scroll_save_y == -1 or self._auto_scroll_save_y != y:
            #print "main window=%s, self=%s, pos=%s" % (self, self.GetMainWindow(), self.GetMainWindow().GetPosition().Get())
            if self._auto_scroll_save_width < 0:
                self._auto_scroll_save_width = rect.width
            dc = self._getIndicatorDC()
            self._eraseIndicator(dc)
            dc.DrawLine(0, y, self._auto_scroll_save_width, y)
            self._auto_scroll_save_y = y

    def _processHighlightIndicator(self, index):
        count = self.GetItemCount()
        if index >= count:
            index = count - 1
        if self._auto_scroll_last_index != index:
            selected = self.GetItemState(index, wx.LIST_STATE_SELECTED)
            if not selected:
                self.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            if self._auto_scroll_last_index != -1:
                #self.SetItemState(self._auto_scroll_last_index, self._auto_scroll_last_state, wx.LIST_STATE_SELECTED)
                self.SetItemState(self._auto_scroll_last_index, 0, wx.LIST_STATE_SELECTED)
            self._auto_scroll_last_state = selected
            self._auto_scroll_last_index = index

    def finishListScroll(self):
        """Clean up timer resource and erase indicator.
        """
        self._stopAutoScrollTimer()
        self._eraseIndicator()
        self._auto_scroll_last_index = -1
        self._auto_scroll_last_state = 0

    def OnAutoScrollTimer(self, evt):
        """Timer event handler to scroll the list in the requested
        direction.
        """
        #print "_auto_scroll = %d, timer = %s" % (self._auto_scroll, self._auto_scroll_timer is not None)
        count = self.GetItemCount()
        if self._auto_scroll == 0:
            # clean up timer resource
            self._auto_scroll_timer = None
        elif count > 0:
            if self._auto_scroll_indicator_line:
                dc = self._getIndicatorDC()
                self._eraseIndicator(dc)
            if self._auto_scroll < 0:
                index = max(0, self.GetTopItem() + self._auto_scroll)
            else:
                index = min(self.GetTopItem() + self.GetCountPerPage(), count - 1)
            self.EnsureVisible(index)
            self._auto_scroll_timer.Start()
        evt.Skip()

    def _getIndicatorDC(self):
        dc = wx.ClientDC(self.GetMainWindow())
        dc.SetPen(wx.Pen(wx.WHITE, 3))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetLogicalFunction(wx.XOR)
        return dc

    def _eraseIndicator(self, dc=None):
        if self._auto_scroll_indicator_line:
            if dc is None:
                dc = self._getIndicatorDC()
            if self._auto_scroll_save_y >= 0:
                # erase the old line
                dc.DrawLine(0, self._auto_scroll_save_y,
                            self._auto_scroll_save_width, self._auto_scroll_save_y)
        self._auto_scroll_save_y = -1


class PickledDataObject(wx.CustomDataObject):
    """Sample custom data object storing indexes of the selected items"""

    def __init__(self):
        wx.CustomDataObject.__init__(self, "Pickled")


class PickledDropTarget(wx.PyDropTarget):
    """Custom drop target modified from the wxPython demo."""
    debug = False

    def __init__(self, window):
        wx.PyDropTarget.__init__(self)
        self.dv = window

        # specify the type of data we will accept
        self.data = PickledDataObject()
        self.SetDataObject(self.data)

    def cleanup(self):
        self.dv.finishListScroll()

    # some virtual methods that track the progress of the drag
    def OnEnter(self, x, y, d):
        if self.debug: print(("OnEnter: %d, %d, %d\n" % (x, y, d)))
        return d

    def OnLeave(self):
        if self.debug: print("OnLeave\n")
        self.cleanup()

    def OnDrop(self, x, y):
        if self.debug: print(("OnDrop: %d %d\n" % (x, y)))
        self.cleanup()
        return True

    def OnDragOver(self, x, y, d):
        top = self.dv.GetTopItem()
        if self.debug: print(("OnDragOver: %d, %d, %d, top=%s" % (x, y, d, top)))

        self.dv.processListScroll(x, y)

        # The value returned here tells the source what kind of visual
        # feedback to give.  For example, if wxDragCopy is returned then
        # only the copy cursor will be shown, even if the source allows
        # moves.  You can use the passed in (x,y) to determine what kind
        # of feedback to give.  In this case we return the suggested value
        # which is based on whether the Ctrl key is pressed.
        return d

    # Called when OnDrop returns True.  We need to get the data and
    # do something with it.
    def OnData(self, x, y, d):
        if self.debug: print(("OnData: %d, %d, %d\n" % (x, y, d)))

        self.cleanup()
        # copy the data from the drag source to our data object
        if self.GetData():
            # convert it back to a list of lines and give it to the viewer
            items = pickle.loads(self.data.GetData())
            self.dv.add_dropped_items(x, y, items)

        # what is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return d


from wx.lib.mixins import listctrl


class ReorderableList(wx.ListCtrl, listctrl.ListCtrlAutoWidthMixin, ListDropScrollerMixin):
    """Simple list control that provides a drop target and uses
    the new mixin for automatic scrolling.
    """

    def __init__(self, parent, items, get_item_text, columns=None, resize_column=0, allow_drop=True, size=(400,400)):
        if columns is None:
            header_style = wx.LC_NO_HEADER
        else:
            header_style = 0
        wx.ListCtrl.__init__(self, parent, size=size, style=wx.LC_REPORT|header_style)
        listctrl.ListCtrlAutoWidthMixin.__init__(self)
        self.debug = False
        self.get_item_text = get_item_text

        # The mixin needs to be initialized
        ListDropScrollerMixin.__init__(self, interval=200)
        self.set_columns(columns, resize_column)

        if allow_drop:
            self.drop_target = PickledDropTarget(self)
            self.SetDropTarget(self.drop_target)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_start_drag)
        self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)

        self.set_items(items)

    def set_columns(self, columns, resize_column):
        if columns is None:
            columns = ["items"]
        for i, title in enumerate(columns):
            self.InsertColumn(i, title)
        self.setResizeColumn(resize_column)
        self.resizeLastColumn(0)

    def set_items(self, items):
        self.clear(None)
        for item in items:
            self.insert_item(sys.maxsize, item)
        self.resizeLastColumn(0)

    def insert_item(self, index, item):
        index = self.InsertStringItem(index, "placeholder")
        self.set_item_text(index, item)
        self.items[index:index] = [item]

    def set_item_text(self, index, item):
        text = self.get_item_text(item)
        c = self.GetColumnCount()
        if c > 1:
            for i in range(c):
                self.SetStringItem(index, i, text[i])
        else:
            self.SetStringItem(index, 0, text)
        #self.SetItemData(index, sid)

    def on_start_drag(self, evt):
        index = evt.GetIndex()
        #print "beginning drag of item %d" % index

        # Create the data object containing all currently selected
        # items
        data = PickledDataObject()
        items = []
        index = self.GetFirstSelected()
        while index != -1:
            items.append((index, self.items[index]))
            index = self.GetNextSelected(index)
        data.SetData(pickle.dumps((id(self), items),-1))

        # And finally, create the drop source and begin the drag
        # and drop opperation
        drop_source = wx.DropSource(self)
        drop_source.SetData(data)
        #print "Begining DragDrop\n"
        result = drop_source.DoDragDrop(wx.Drag_AllowMove)
        #print "DragDrop completed: %d\n" % result

    def on_context_menu(self, evt):
        menu = wx.Menu()
        menu.Append(wx.ID_SELECTALL, "Select All")
        menu.Append(wx.ID_CLEAR, "Deselect All")
        id = self.GetPopupMenuSelectionFromUser(menu)
        menu.Destroy()
        if id == wx.ID_SELECTALL:
            self.select_all()
        elif id == wx.ID_CLEAR:
            self.deselect_all()

    def add_dropped_items(self, x, y, data):
        src, items = data
        start_index = self.getDropIndex(x, y)
        if self.debug: print(("At (%d,%d), index=%d, adding %s" % (x, y, start_index, items)))
        if start_index == -1:
            start_index = 0

        list_count = self.GetItemCount()

        if src == id(self):
            # reordering items in the same list!
            new_order = list(range(list_count))
            new_indexes = []
            for index, item in items:
                if index < start_index:
                    start_index -= 1
                new_order.remove(index)
                new_indexes.append(index)
            if self.debug: print(("inserting %s into %s at %d" % (str(items), str(new_order), start_index)))
            new_order[start_index:start_index] = new_indexes
            if self.debug: print(("orig list = %s" % str(list(range(list_count)))))
            if self.debug: print((" new list = %s" % str(new_order)))

            self.change_list(new_order, new_indexes)
        else:
            # dropping items from another list
            for _, item in items:
                self.insert_item(start_index, item)
                start_index += 1

    def delete_selected(self):
        list_count = self.GetItemCount()
        new_order = list(range(list_count))
        index = self.GetFirstSelected()
        while index != -1:
            new_order.remove(index)
            index = self.GetNextSelected(index)
        if self.debug: print(("orig list = %s" % str(list(range(list_count)))))
        if self.debug: print((" new list = %s" % str(new_order)))
        self.change_list(new_order)

    @property
    def can_move_up(self):
        return self.GetFirstSelected() > 0

    @property
    def can_move_down(self):
        # There's no convenient way to get all selected items, so as long as
        # the selected item isn't the last one, it can be moved down
        num = self.GetItemCount()
        return num > 0 and self.GetSelectedItemCount() > 0 and not self.IsSelected(num - 1)

    def move_selected(self, delta=-1):
        list_count = self.GetItemCount()
        index_map = [None for i in range(list_count)]
        unselected = set(range(list_count))
        try:
            index = self.GetFirstSelected()
            while index != -1:
                index_map[index + delta] = index
                unselected.remove(index)
                index = self.GetNextSelected(index)
        except IndexError:
            return
        unselected = sorted(unselected)
        new_order = []
        make_selected = []
        for index in range(list_count):
            if index_map[index] is not None:
                new_order.append(index_map[index])
                make_selected.append(index_map[index])
            else:
                new_order.append(unselected.pop(0))
        if self.debug: print(("orig list = %s" % str(list(range(list_count)))))
        if self.debug: print((" new list = %s" % str(new_order)))
        self.change_list(new_order, make_selected)

    def change_list(self, new_order, make_selected=[]):
        """Reorder the list given the new list of indexes.
        
        The new list will be constructed by building up items based on the
        indexes specified in new_order as taken from the current list.  The
        ListCtrl contents is then replaced with the new list of items.  Items
        may also be deleted from the list by not including items in the
        new_order.
        
        @param new_order: list of indexes used to compose the new list
        
        @param make_selected: optional list showing indexes of original order
        that should be marked as selected in the new list.
        """
        new_selection = []
        new_count = len(new_order)
        new_items = []
        for i in range(new_count):
            new_i = new_order[i]
            new_item = self.items[new_i]
            new_items.append(new_item)
            if i != new_i:
                self.set_item_text(i, new_item)

                # save the new highlight position
                if new_i in make_selected:
                    new_selection.append(i)

            # Selection stays with the index even when the item text changes,
            # so remove the selection from all items for the moment
            self.SetItemState(i, 0, wx.LIST_STATE_SELECTED)

        # if the list size has been reduced, clean up any extra items
        list_count = self.GetItemCount()
        for i in range(new_count, list_count):
            self.DeleteItem(new_count)

        # Turn the selection back on for the new positions of the moved items
        for i in new_selection:
            self.SetItemState(i, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

        self.items = new_items
        if self.debug:
            for i, item in enumerate(self.items):
                print((i, item, self.get_item_text(item)))

    def clear(self, evt=None):
        self.DeleteAllItems()
        self.items = []

    def refresh(self):
        selected = list()  # can't use dict because items might be unhashable
        index = self.GetFirstSelected()
        while index != -1:
            item = self.items[index]
            selected.append(item)
            index = self.GetNextSelected(index)
        items = self.items
        self.set_items(items)
        for i, item in enumerate(self.items):
            if item in selected:  # pay for the slowdown here with O(N^2) search
                self.SetItemState(i, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

    def select_all(self):
        for i in range(self.GetItemCount()):
            self.SetItemState(i, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

    def deselect_all(self):
        for i in range(self.GetItemCount()):
            self.SetItemState(i, 0, wx.LIST_STATE_SELECTED)


if __name__ == '__main__':
    class TestList(wx.ListCtrl, ListDropScrollerMixin):
        """Simple list control that provides a drop target and uses
        the new mixin for automatic scrolling.
        """

        def __init__(self, parent, name, count=100):
            wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)

            # The mixin needs to be initialized
            ListDropScrollerMixin.__init__(self, interval=200)

            self.drop_target=PickledDropTarget(self)
            self.SetDropTarget(self.drop_target)

            self.create(name, count)

            self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_start_drag)

        def create(self, name, count):
            """Set up some test data."""

            self.InsertColumn(0, "#")
            self.InsertColumn(1, "Title")
            for i in range(count):
                self.InsertStringItem(sys.maxsize, str(i))
                self.SetStringItem(i, 1, "%s-%d" % (name, i))

        def on_start_drag(self, evt):
            index = evt.GetIndex()
            print(("beginning drag of item %d" % index))

            # Create the data object containing all currently selected
            # items
            data = PickledDataObject()
            items = []
            index = self.GetFirstSelected()
            while index != -1:
                items.append((self.GetItem(index, 0).GetText(),
                              self.GetItem(index, 1).GetText()))
                index = self.GetNextSelected(index)
            data.SetData(pickle.dumps(items,-1))

            # And finally, create the drop source and begin the drag
            # and drop opperation
            drop_source = wx.DropSource(self)
            drop_source.SetData(data)
            print("Begining DragDrop\n")
            result = drop_source.DoDragDrop(wx.Drag_AllowMove)
            print(("DragDrop completed: %d\n" % result))

        def add_dropped_items(self, x, y, items):
            index = self.getDropIndex(x, y)
            print(("At (%d,%d), index=%d, adding %s" % (x, y, index, items)))

            list_count = self.GetItemCount()
            for item in items:
                if index == -1:
                    index = 0
                index = self.InsertStringItem(index, item[0])
                self.SetStringItem(index, 1, item[1])
                index += 1

        def clear(self, evt):
            self.DeleteAllItems()

    class ListPanel(wx.SplitterWindow):
        def __init__(self, parent):
            wx.SplitterWindow.__init__(self, parent)

            self.list1 = TestList(self, "left", 100)
            self.list2 = TestList(self, "right", 10)
            self.SplitVertically(self.list1, self.list2, 200)
            self.Layout()

    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='List Drag Test', size=(400,500))
    frame.CreateStatusBar()

    panel = ListPanel(frame)
    label = wx.StaticText(frame, -1, "Drag items from a list to either list.\nThe lists will scroll when the cursor\nis near the first and last visible items")

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
    sizer.Add(panel, 1, wx.EXPAND | wx.ALL, 5)
    hsizer = wx.BoxSizer(wx.HORIZONTAL)
    btn1 = wx.Button(frame, -1, "Clear List 1")
    btn1.Bind(wx.EVT_BUTTON, panel.list1.clear)
    btn2 = wx.Button(frame, -1, "Clear List 2")
    btn2.Bind(wx.EVT_BUTTON, panel.list2.clear)
    hsizer.Add(btn1, 1, wx.EXPAND)
    hsizer.Add(btn2, 1, wx.EXPAND)
    sizer.Add(hsizer, 0, wx.EXPAND)

    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)

    app.MainLoop()
