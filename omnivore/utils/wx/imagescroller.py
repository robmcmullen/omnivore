#-----------------------------------------------------------------------------
# Name:        imagescroller.py
# Purpose:     scrolling container for bitmapped images
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007-2016 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""ImageScroller -- a container for viewing bitmapped images.

This control is designed to be a generic bitmap viewer that can scroll
to handle large images.  In addition, user interaction with the bitmap
is possible through the use of subclasses of the MouseSelector class.
Currently, a crosshair selector and a rubber band selector are
provided, with others to follow.

Coordinate systems
==================

Event coords are in terms of a fixed viewport the size of the client
area of the window containing the scrolled window.  The scrolled
window itself has an origin that can be negative relative to this
viewport.

World coordinates are in terms of the size of canvas of the scrolled
window itself, not the smaller size of the viewport onto the scrolled
window.  The size of the scrolled window's canvas is determined by the
scaled size of the bitmap containing it.

Coordinate systems example
--------------------------

If the original bitmap is 100 pixels wide and 200 pixels high, and the
zoom factor is 4, the size of both the scaled image and the scrolled
window canvas will be 400 x 800 pixels.  If the viewport of the
scrolled window is 200 x 300, some of the scaled bitmap won't be
displayed.

 +-------------+
 |             |--- scaled bitmap
 |    +------+ |
 |    |      | |
 |    |      |----- scrolled window viewport at location (x, y) of the bitmap
 |    |      | |
 |    +------+ |
 |             |
 +-------------+

Again, world coordinates are in terms of the scaled bitmap, but event
coordinates are in terms of the viewport.  An event coordinate of (0,
0) actually occurs at (x, y) on the bitmap.

@author: Rob McMullen
@version: 0.5

Changelog:
    0.4:
        * added methods to allow programmatic specification of rubberband
        * added setSelection to Rubberband
        * added startSelector to ImageScroller
    0.5:
        * changed to wx.Overlay for drawing (instead of XOR)
"""

import os

import wx
import wx.lib.newevent

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        #print txt
        pass


##### - Here are some utility functions from wx.lib.mixins.rubberband

def normalizeBox(box):
    """
    Convert any negative measurements in the current
    box to positive, and adjust the origin.
    """
    x, y, w, h = box
    if w < 0:
        x += (w+1)
        w *= -1
    if h < 0:
        y += (h+1)
        h *= -1
    return (x, y, w, h)


def boxToExtent(box):
    """
    Convert a box specification to an extent specification.
    I put this into a seperate function after I realized that
    I had been implementing it wrong in several places.
    """
    b = normalizeBox(box)
    return (b[0], b[1], b[0]+b[2]-1, b[1]+b[3]-1)


def pointInBox(x, y, box):
    """
    Return True if the given point is contained in the box.
    """
    e = boxToExtent(box)
    state = x >= e[0] and x <= e[2] and y >= e[1] and y <= e[3]
    # dprint("x=%d y=%d box=%s state=%s" % (x, y, e, state))
    return state


def pointOnBox(x, y, box, thickness=1):
    """
    Return True if the point is on the outside edge
    of the box.  The thickness defines how thick the
    edge should be.  This is necessary for HCI reasons:
    For example, it's normally very difficult for a user
    to manuever the mouse onto a one pixel border.
    """
    outerBox = box
    innerBox = (box[0]+thickness, box[1]+thickness, box[2]-(thickness*2), box[3]-(thickness*2))
    return pointInBox(x, y, outerBox) and not pointInBox(x, y, innerBox)


class MouseSelector(object):
    """Base class for user interaction classes.

    A selector is a class that represents a user interaction with the
    bitmap.  User interactions are triggered by a certain mouse event
    combination, and once triggered, the ImageScroller makes that the
    current selector.

    Mouse event processing for the ImageScroller is directed to the
    current selector through the processEvent method, which directs
    the action depending on which combination of mouse events occur.
    The processEvent handler should return False when an event
    combination is reached that signals the end of the selector's
    processing.  The selector will be destroyed by the ImageScroller
    when this occurs.
    """
    cursor = wx.CURSOR_ARROW

    def __init__(self, scroller, ev=None):
        self.scroller = scroller
        self.world_coords = None
        self.start_img_coords = None
        self.last_img_coords = None

        # autoscrolling enabled?
        self.want_autoscroll = False

        # cursor stuff
        self.want_blank_cursor = False

        if ev is not None:
            self.startEvent(ev)

    @classmethod
    def trigger(self, ev):
        """Identify the trigger event to turn on this selector.

        Return True if the event passed in is the event that triggers
        this selector to begin.
        """
        if ev.LeftDown():
            return True
        return False

    def processEvent(self, ev):
        """Process a mouse event for this selector.

        This callback is called for any mouse event once the selector
        is active in the scroller.  The selector is not deactivated
        until this handler returns False, so make sure some event will
        cause it to return False.
        """
        if ev.LeftIsDown() and ev.Dragging():
            self.handleEvent(ev)
        elif ev.LeftUp():
            self.finishEvent(ev)
            return False
        return True

    def startEvent(self, ev):
        """Set up the initial state to begin event processing.

        This is generally called by the constructor to set up whatever
        initial state is necessary to allow further events to be
        handled by the processEvent method.
        """
        coords = self.scroller.convertEventCoords(ev)
        self.scroller.CaptureMouse()
        self.start_img_coords = self.scroller.getImageCoords(*coords)
        self.setWorldCoordsFromImageCoords(*self.start_img_coords)
        self.draw()
        self.handleEventPostHook(ev)
        # dprint("ev: (%d,%d), coords: (%d,%d)" % (ev.GetX(), ev.GetY(), coords[0], coords[1]))
        self.want_autoscroll = True

    def handleEvent(self, ev):
        """General event handler.

        This method is called by processEvent to show the results of
        the user interaction on the bitmap.
        """
        coords = self.scroller.convertEventCoords(ev)
        img_coords = self.scroller.getImageCoords(*coords)
        if img_coords != self.last_img_coords:
            self.setWorldCoordsFromImageCoords(*img_coords)
            self.draw()
            self.handleEventPostHook(ev)
        #dprint("ev: (%d,%d), coords: (%d,%d)" % (ev.GetX(), ev.GetY(), coords[0], coords[1]))

    def handleEventPostHook(self, ev):
        """Hook called during every event handled by L{handleEvent}
        
        This is a no-op in the base class; it's designed to be overridden in
        subclasses.
        """
        pass

    def finishEvent(self, ev):
        """User interaction is complete.

        This method is called when the user has completed the
        interaction.  This does not necessarily destroy the selector
        -- it's up to the processEvent returning False to signal the
        ImageScroller to kill the selector.

        This could be used in multi-stage processing; see the
        RubberBand for an example where finishEvent doesn't mean that
        the selector should be destroyed.
        """
        self.want_autoscroll = False
        self.scroller.ReleaseMouse()
        self.cleanup()
        self.finishEventPostHook(ev)

    def finishEventPostHook(self, ev):
        """Hook that gets called when the selector has been dismissed.
        
        This is a no-op in the base class; it's designed to be overridden in
        subclasses.
        """
        pass

    def draw(self):
        #print("draw")
        if self.start_img_coords:
            dc, odc = self.getOverlayDC()
            self.drawSelector(dc)
            del odc # workaround big in python wrappers; delete overlay dc first

    def cleanup(self):
        dc = wx.ClientDC(self.scroller)
        odc = wx.DCOverlay(self.scroller.overlay, dc)
        odc.Clear()
        del odc
        self.scroller.overlay.Reset()
        self.scroller.Refresh()
        self.world_coords = None

    def recalc(self):
        self.setWorldCoordsFromImageCoords(*self.last_img_coords)

    def recalc_and_draw(self):
        #print("recalc and draw")
        self.scroller.overlay.Reset()
        self.recalc()
        self.draw()

    def getOverlayDC(self):
        dc = wx.ClientDC(self.scroller)
        odc = wx.DCOverlay(self.scroller.overlay, dc)
        odc.Clear()
        dc.SetPen(wx.Pen(wx.WHITE, 1, wx.DOT))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        return dc, odc

    def getViewOffset(self):
        xView, yView = self.scroller.GetViewStart()
        xDelta, yDelta = self.scroller.GetScrollPixelsPerUnit()
        xoff = xView * xDelta
        yoff = yView * yDelta
        return -xoff, -yoff

    def setWorldCoordsFromImageCoords(self, x, y):
        self.last_img_coords = (x, y)
        zoom = self.scroller.zoom
        offset = int(zoom / 2)
        x = int(x * zoom)
        y = int(y * zoom)
        self.world_coords = (x + offset, y + offset)


class NullSelector(MouseSelector):
    def startEvent(self, ev):
        pass

    def handleEvent(self, ev):
        pass

    def draw(self):
        pass


# create a new Event class and a EVT binder function for a crosshair
# motion event
(CrosshairMotionEvent, EVT_CROSSHAIR_MOTION) = wx.lib.newevent.NewEvent()


class Crosshair(MouseSelector):
    def __init__(self, scroller, ev=None):
        MouseSelector.__init__(self, scroller)

        self.want_blank_cursor = True
        self.crossbox = None

        if ev is not None:
            self.startEvent(ev)

    def handleEventPostHook(self, ev):
        x, y = self.last_img_coords
        if self.scroller.crop is not None:
            dx, dy, w, h = self.scroller.crop
        else:
            dx, dy = (0, 0)
        cev = CrosshairMotionEvent(imageCoords = (x, y),
                                   uncroppedImageCoords = (x + dx, y + dy))
        wx.PostEvent(self.scroller, cev)

    def drawCrossBox(self, x, y, xoff, yoff, dc):
        dc.DrawRectangle(self.crossbox[0] + xoff, self.crossbox[1] + yoff,
                         self.crossbox[2], self.crossbox[3])
        dc.DrawLine(x, 0, x, self.crossbox[1] + yoff)
        dc.DrawLine(x, self.crossbox[1] + self.crossbox[3] + yoff + 1,
                    x, self.scroller.height)
        dc.DrawLine(0, y, self.crossbox[0] + xoff, y)
        dc.DrawLine(self.crossbox[0] + self.crossbox[2] + xoff + 1, y,
                    self.scroller.width, y)

    def drawSelector(self, dc):
        xoff, yoff = self.getViewOffset()
        x = self.world_coords[0] + xoff
        y = self.world_coords[1] + yoff
        if self.crossbox:
            dc.SetPen(wx.Pen(wx.BLACK, 1))
            self.drawCrossBox(x, y, xoff, yoff, dc)
            dc.SetPen(wx.Pen(wx.WHITE, 1, wx.DOT))
            self.drawCrossBox(x, y, xoff, yoff, dc)
        else:
            dc.SetPen(wx.Pen(wx.BLACK, 1))
            dc.DrawLine(x, 0, x, self.scroller.height)
            dc.DrawLine(0, y, self.scroller.width, y)
            dc.SetPen(wx.Pen(wx.WHITE, 1, wx.DOT))
            dc.DrawLine(x, 0, x, self.scroller.height)
            dc.DrawLine(0, y, self.scroller.width, y)

    def setWorldCoordsFromImageCoords(self, x, y):
        self.last_img_coords = (x, y)
        zoom = self.scroller.zoom
        offset = int(zoom / 2)
        x = int(x * zoom)
        y = int(y * zoom)
        self.world_coords = (x + offset, y + offset)
        if self.scroller.zoom >= 1:
            self.crossbox = (x-1, y-1, zoom + 2, zoom + 2)
        else:
            self.crossbox = None
        # dprint("crosshair = %s, img = %s" % (self.world_coords, self.last_img_coords))


# create a new Event class and a EVT binder function for a crosshair
# motion event
(RubberBandSizeEvent, EVT_RUBBERBAND_SIZE) = wx.lib.newevent.NewEvent()
(RubberBandMotionEvent, EVT_RUBBERBAND_MOTION) = wx.lib.newevent.NewEvent()


class RubberBand(MouseSelector):
    move_cursor = wx.CURSOR_SIZING
    resize_cursors = [wx.CURSOR_SIZENWSE,
                      wx.CURSOR_SIZENS,
                      wx.CURSOR_SIZENESW,
                      wx.CURSOR_SIZEWE,
                      wx.CURSOR_SIZENWSE,
                      wx.CURSOR_SIZENS,
                      wx.CURSOR_SIZENESW,
                      wx.CURSOR_SIZEWE
                      ]

    def __init__(self, scroller, ev=None):
        MouseSelector.__init__(self, scroller)

        self.border_sensitivity = 3
        self.resize_index = None
        self.event_type = None
        self.move_img_coords = None

        if ev is not None:
            self.startEvent(ev)

    def processEvent(self, ev):
        """Process a mouse event for this selector.

        This callback is called for any mouse event once the selector
        is active in the scroller.  The selector is not deactivated
        until this handler returns False, so make sure some event will
        cause it to return False.
        """
        if ev.LeftDown():
            # restart event if we get another LeftDown
            self.startEvent(ev)
        elif ev.LeftIsDown() and ev.Dragging():
            self.handleEvent(ev)
        elif ev.LeftUp():
            self.finishEvent(ev)
        elif ev.Moving():
            # no mouse buttons; change cursor if over resize box
            self.handleCursorChanges(ev)
        return True

    def startEvent(self, ev):
        """Driver for new event.

        This selector recognizes a few different types of events: a
        normal event where the user uses the mouse to select a new
        rectangular area, a move event where the user can drag around
        the area without changing its size, and a bunch of resize
        events where the user can grab a corner or edge and make the
        rectangular area bigger.
        """
        self.scroller.CaptureMouse()
        coords = self.scroller.convertEventCoords(ev)
        # dprint("mouse=%s world=%s" % (coords, self.world_coords))
        if self.isOnBorder(coords):
            self.startResizeEvent(ev, coords)
        elif self.isInside(coords):
            self.startMoveEvent(ev, coords)
        else:
            self.startNormalEvent(ev, coords)
        self.want_autoscroll = True

    def startNormalEvent(self, ev, coords):
        self.event_type = None
        self.start_img_coords = self.scroller.getImageCoords(*coords)
        self.setWorldCoordsFromImageCoords(*self.start_img_coords)
        self.draw()
        self.handleEventPostHook(ev)
        # dprint("ev: (%d,%d), coords: (%d,%d)" % (ev.GetX(), ev.GetY(), coords[0], coords[1]))

    def startResizeEvent(self, ev, coords):
        self.event_type = "resize"
        self.normalizeImageCoords()
        self.move_img_coords = self.scroller.getImageCoords(*coords)
        # dprint("%s: index=%d starting from %s" % (self.event_type, self.resize_index, self.move_img_coords))

    def startMoveEvent(self, ev, coords):
        self.event_type = "move"
        self.normalizeImageCoords()
        self.move_img_coords = self.scroller.getImageCoords(*coords)
        # dprint("%s: starting from %s" % (self.event_type, self.move_img_coords))

    def handleEvent(self, ev):
        if self.event_type == "resize":
            self.handleResizeEvent(ev)
        elif self.event_type == "move":
            self.handleMoveEvent(ev)
        else:
            MouseSelector.handleEvent(self, ev)
        # dprint(self.world_coords)

    def handleResizeEvent(self, ev):
        coords = self.scroller.convertEventCoords(ev)
        img_coords = self.scroller.getImageCoords(coords[0],
                                                  coords[1],
                                                  fixbounds=False)
        # dprint("img_coords = %s" % str(img_coords))
        if img_coords != self.move_img_coords:
            self.resizeWorldCoordsFromImageCoords(*img_coords)
            self.draw()
            self.handleEventPostHook(ev)

    def handleMoveEvent(self, ev):
        coords = self.scroller.convertEventCoords(ev)
        img_coords = self.scroller.getImageCoords(coords[0],
                                                  coords[1],
                                                  fixbounds=False)
        # dprint("img_coords = %s" % str(img_coords))
        if img_coords != self.move_img_coords:
            self.moveWorldCoordsFromImageCoords(*img_coords)
            self.draw()
            self.handleEventPostHook(ev)

    def handleCursorChanges(self, ev):
        coords = self.scroller.convertEventCoords(ev)
        # dprint("mouse=%s world=%s" % (coords, self.world_coords))
        self.resize_index = None
        if self.isOnBorder(coords):
            self.resize_index = self.getBorderCursorIndex(coords)
            cursor = self.resize_cursors[self.resize_index]
        elif self.isInside(coords):
            cursor = self.move_cursor
        else:
            cursor = self.cursor
        self.scroller.setCursor(cursor)

    def finishEvent(self, ev):
        # dprint()
        self.scroller.ReleaseMouse()
        self.want_autoscroll = False

    def handleEventPostHook(self, ev):
        x0, y0 = self.start_img_coords
        x1, y1 = self.last_img_coords
        # normalize coords
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        if self.event_type == "move":
            rbev = RubberBandMotionEvent(upperLeftImageCoords = (x0, y0),
                                         lowerRightImageCoords = (x1, y1))
        else:
            rbev = RubberBandSizeEvent(upperLeftImageCoords = (x0, y0),
                                       lowerRightImageCoords = (x1, y1))
        wx.PostEvent(self.scroller, rbev)

    def drawSelector(self, dc):
        xoff, yoff = self.getViewOffset()
        x = self.world_coords[0] + xoff
        y = self.world_coords[1] + yoff
        w = self.world_coords[2]
        h = self.world_coords[3]

        # dprint("start=%s current=%s  xywh=%s" % (self.start_img_coords, self.last_img_coords, (x,y,w,h)))
        dc.SetPen(wx.Pen(wx.BLACK, 1))
        dc.DrawRectangle(x, y, w, h)
        dc.SetPen(wx.Pen(wx.WHITE, 1, wx.DOT))
        dc.DrawRectangle(x, y, w, h)

    def isOnBorder(self, coords):
        """Are the world coordinates on the selection border?

        Return true if the world coordinates specified are on or
        within a tolerance of the selecton border.
        """
        # dprint(self.world_coords)
        if self.world_coords is None:
            return False
        return pointOnBox(coords[0], coords[1], self.world_coords, self.border_sensitivity)

    def getBorderCursorIndex(self, coords):
        """Get resize cursor depending on position on border.

        Modified from wx.lib.mixins.rubberband: Return a position
        number in the range 0 .. 7 to indicate where on the box border
        the point is.  The layout is:

              0    1    2
              7         3
              6    5    4
        """
        x0, y0, x1, y1 = boxToExtent(self.world_coords)
        x = coords[0]
        y = coords[1]
        t = self.border_sensitivity
        if x >= x0-t and x <= x0+t:
            # O, 7, or 6
            if y >= y0-t and y <= y0+t:
                index = 0
            elif y >= y1-t and y <= y1+t:
                index = 6
            else:
                index = 7
        elif x >= x1-t and x <= x1+t:
            # 2, 3, or 4
            if y >= y0-t and y <= y0+t:
                index = 2
            elif y >= y1-t and y <= y1+t:
                index = 4
            else:
                index = 3
        elif y >= y0-t and y <= y0+t:
            index = 1
        else:
            index = 5
        return index

    def isInside(self, coords):
        """Are the world coordinates on the selection border?

        Return true if the world coordinates specified are on or
        within a tolerance of the selecton border.
        """
        # dprint(self.world_coords)
        if self.world_coords is None:
            return False
        return pointInBox(coords[0], coords[1], self.world_coords)

    def recalc(self):
        zoom = self.scroller.zoom
        x, y = self.last_img_coords
        xi, yi = self.start_img_coords
        if x > xi:
            x0 = int(xi * zoom)
            x1 = int((x+1) * zoom)
        else:
            x0 = int(x * zoom)
            x1 = int((xi+1) * zoom)

        if y > yi:
            y0 = int(yi * zoom)
            y1 = int((y+1) * zoom)
        else:
            y0 = int(y * zoom)
            y1 = int((yi+1) * zoom)

        # (x0, y0) and (x1, y1) always point within the pixel, so we
        # need to expand the area so that the highlighted area is
        # outside the selection region.
        self.world_coords = (x0 - 1, y0 - 1, x1 - x0 + 2, y1 - y0 + 2)

    def normalizeImageCoords(self):
        x0, y0 = self.start_img_coords
        x1, y1 = self.last_img_coords
        self.normalizeNewImageCoords(x0, y0, x1, y1)

    def normalizeNewImageCoords(self, x0, y0, x1, y1):
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        self.start_img_coords = (x0, y0)
        self.last_img_coords = (x1, y1)

    def setWorldCoordsFromImageCoords(self, x, y):
        self.last_img_coords = (x, y)
        self.recalc()

    def moveWorldCoordsFromImageCoords(self, x, y):
        dx = x - self.move_img_coords[0]
        dy = y - self.move_img_coords[1]
        self.move_img_coords = (x, y)
        x0, y0 = self.start_img_coords
        x1, y1 = self.last_img_coords
        if x0 + dx < 0:
            dx = -x0
        elif x1 + dx >= self.scroller.img.GetWidth():
            dx = self.scroller.img.GetWidth() - x1 - 1
        if y0 + dy < 0:
            dy = -y0
        elif y1 + dy >= self.scroller.img.GetHeight():
            dy = self.scroller.img.GetHeight() - y1 - 1
        self.start_img_coords = (x0 + dx, y0 + dy)
        self.last_img_coords = (x1 + dx, y1 + dy)
        self.recalc()

    def resizeWorldCoordsFromImageCoords(self, x, y):
        dx = x - self.move_img_coords[0]
        dy = y - self.move_img_coords[1]
        self.move_img_coords = self.scroller.getBoundedCoords(x, y)
        index = self.resize_index
        if index == 1 or index == 5:
            dx = 0
        elif index == 3 or index == 7:
            dy = 0
        x0, y0 = self.start_img_coords
        x1, y1 = self.last_img_coords
        if index >= 1 and index <= 3:
            # fix lower left corner
            x1 += dx
            y0 += dy
        elif index == 4:
            # fix upper left corner
            x1 += dx
            y1 += dy
        elif index >=5 and index <=7:
            # fix upper right corner:
            x0 += dx
            y1 += dy
        else:
            # fix upper left corner
            x0 += dx
            y0 += dy
        self.start_img_coords = self.scroller.getBoundedCoords(x0, y0)
        self.last_img_coords = self.scroller.getBoundedCoords(x1, y1)
        self.recalc()

    def getSelectedBox(self):
        """Return selected box in image coords.

        Returns an (x, y, w, h) tuple of the selected rectangle.
        """
        x0, y0 = self.start_img_coords
        x1, y1 = self.last_img_coords
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        return (x0, y0, x1 - x0 + 1, y1 - y0 + 1)

    def setSelection(self, x0, y0, x1, y1):
        """Programmatically set the selection rectangle.
        """
        self.start_img_coords = self.scroller.getBoundedCoords(x0, y0)
        self.last_img_coords = self.scroller.getBoundedCoords(x1, y1)
        self.recalc()
        self.draw()


class ImageScroller(wx.ScrolledWindow):
    dbg_call_seq = 0

    def __init__(self, parent, task, selector=Crosshair):
        wx.ScrolledWindow.__init__(self, parent, -1)
        self.task = task
        self.editor = None

        # Settings
        self.background_color = wx.Colour(160, 160, 160)
        self.use_checkerboard = True
        self.checkerboard_box_size = 8
        self.checkerboard_color = wx.Colour(96, 96, 96)
        self.max_zoom = 16.0
        self.min_zoom = 0.0625

        # internal storage
        self.orig_img = None
        self.img = None
        self.scaled_bmp = None
        self.width = 0
        self.height = 0
        self.zoom = 1.0
        self.crop = None

        # hacks
        self.just_scrolled = False

        # cursors
        self.default_cursor = wx.CURSOR_ARROW
        self.save_cursor = None

        self.Bind(wx.EVT_PAINT, self.OnPaint)

        # selectors and related storage
        self.use_selector = None
        self.selector = None
        self.selector_event_callback = None
        self.overlay = wx.Overlay()
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvent)

        self.setSelector(selector)

    def recalc_view(self):
        editor = self.task.active_editor
        if editor is not None:
            self.editor = editor
            self.document = editor.document
            self.set_data()

    def set_data(self):
        img = wx.Image(1,1)
        if not img.LoadMimeStream(self.document.bytestream, self.document.metadata.mime):
            #raise TypeError("Bad image -- either it really isn't an image, or wxPython doesn't support the image format.")
            img = wx.Image(1,1)
        self.setImage(img)

    def zoomIn(self, zoom=2):
        self.zoom *= zoom
        if self.zoom > self.max_zoom:
            self.zoom = self.max_zoom
        self._scaleImage()

    def zoomOut(self, zoom=2):
        self.zoom /= zoom
        if self.zoom < self.min_zoom:
            self.zoom = self.min_zoom
        self._scaleImage()

    def _clearBackground(self, dc, w, h):
        dc.SetBackground(wx.Brush(self.background_color))
        dc.Clear()

    def _checkerboardBackground(self, dc, w, h):
        # draw checkerboard for transparent background
        box = self.checkerboard_box_size
        y = 0
        while y < h:
            #dprint("y=%d, y/box=%d" % (y, (y/box)%2))
            x = box * ((y/box)%2)
            while x < w:
                dc.SetPen(wx.Pen(self.checkerboard_color))
                dc.SetBrush(wx.Brush(self.checkerboard_color))
                dc.DrawRectangle(x, y, box, box)
                #dprint("draw: xywh=%s" % ((x, y, box, box),))
                x += box*2
            y += box

    def _drawBackground(self, dc, w, h):
        self._clearBackground(dc, w, h)
        if self.use_checkerboard:
            self._checkerboardBackground(dc, w, h)

    def inOrigImage(self, x, y):
        if x>=0 and x<self.orig_img.GetWidth() and y>=0 and y<self.orig_img.GetHeight():
            return True
        return False

    def _getCroppedImage(self):
        """Returns cropped image.

        Creates and returns a new image if there is a cropping
        specified, otherwise just returns the original image
        unchanged.
        """
        if self.crop is not None and isinstance(self.crop, tuple):
            if self.inOrigImage(self.crop[0], self.crop[1]) and self.inOrigImage(self.crop[0] + self.crop[2] - 1, self.crop[1] + self.crop[3] - 1):
                return self.orig_img.GetSubImage(self.crop)
            else:
                print("trying to crop outside of image: %s" % str(self.crop))
        return self.orig_img

    def _scaleImage(self):
        """Creates new image at specified zoom factor.

        Creates a new image that is to be used as the background of
        the scrolled bitmap.  Currently, actually creates the entire
        image, which could lead to memory problems if the image is
        really huge and the zoom factor is large.
        """
        if self.orig_img is not None:
            self.img = self._getCroppedImage()
            w = int(self.img.GetWidth() * self.zoom)
            h = int(self.img.GetHeight() * self.zoom)
            dc = wx.MemoryDC()
            self.scaled_bmp = wx.Bitmap(w, h)
            dc.SelectObject(self.scaled_bmp)
            self._drawBackground(dc, w, h)

            # For very large bitmaps, the memory consumption of the
            # BitmapFromImage call can cause memory errors.  So, here
            # it breaks up the source image into chunks and only calls
            # BitmapFromImage on the chunk.
            ydest = 0
            source_step = 256
            for ysource in range(0, self.img.GetHeight(), source_step):
                if ysource + source_step > self.img.GetHeight():
                    hsource = self.img.GetHeight() - ysource
                else:
                    hsource = source_step
                hdest = hsource * self.zoom
                crop = [0, ysource, self.img.GetWidth(), hsource]
                #dprint(crop)
                subimg = self.orig_img.GetSubImage(crop)
                bmp = wx.Bitmap(subimg.Scale(w, hdest))
                dc.DrawBitmap(bmp, 0, ydest, True)
                ydest += hdest
            self.width = self.scaled_bmp.GetWidth()
            self.height = self.scaled_bmp.GetHeight()
        else:
            self.width = 10
            self.height = 10
        self.SetVirtualSize((self.width, self.height))
        rate = int(self.zoom)
        if rate < 1:
            rate = 1
        self.SetScrollRate(rate, rate)
        if self.selector:
            self.selector.recalc()
        self.Refresh()

    def setImage(self, img=None, zoom=None, rot=None,
                 vmirror=False, hmirror=False, crop=None):
        """Sets the control to contain a new image.

        Main user interaction with this control -- makes the control
        display a new image, discarding the old image.

        @param img: new wx.Image to display
        @param zoom: optional floating point zoom factor
        @param rot: not working yet
        @param vmirror: not working yet
        @param hmirror: not working yet
        @param crop: None for no cropping, or (x, y, w, h) tuple
        """
        if img is not None:
            # change the bitmap if specified
            self.bmp = None
            self.orig_img = img
        else:
            self.bmp = self.orig_img = None

        if zoom is not None:
            self.zoom = zoom

        self.crop = crop
        self.endActiveSelector()
        self._scaleImage()

    def setBitmap(self, bmp=None, zoom=None):
        """Set the control to display a new bitmap.

        Similar to setImage, but takes a wx.Bitmap instead of a
        wx.Image.
        """
        if bmp is not None:
            img = bmp.ConvertToImage()
            self.setImage(img, zoom)
        else:
            self.setImage(None, zoom)

    def setCrop(self, crop=None):
        """Set the image cropping.

        Crops the image to the specified size.  If crop is an (x, y,
        w, h) tuple, it crops the image as specified.  If crop is
        None, it restores the original image.
        """
        if crop is not None and self.crop is not None:
            # If we're cropping an image that's already cropped,
            # add the offsets to find the new subimage.
            x = crop[0] + self.crop[0]
            y = crop[1] + self.crop[1]
            crop = (x, y, crop[2], crop[3])
        self.crop = crop
        self.endActiveSelector()
        self._scaleImage()

    def copyToClipboard(self):
        """Copies current image to clipboard.

        Copies the current image, including scaling, zooming, etc. to
        the clipboard.
        """
        img = self._getCroppedImage()
        w = int(img.GetWidth() * self.zoom)
        h = int(img.GetHeight() * self.zoom)
        clip = wx.Bitmap(img.Scale(w, h))
        bmpdo = wx.BitmapDataObject(clip)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(bmpdo)
            wx.TheClipboard.Close()

    def saveImage(self, filename):
        """Copies current image to clipboard.

        Copies the current image, including scaling, zooming, etc. to
        the clipboard.
        """
        handlers = {'.png': wx.BITMAP_TYPE_PNG,
                    '.jpg': wx.BITMAP_TYPE_JPEG,
                    }

        root, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext in handlers:
            try:
                status = self.scaled_bmp.SaveFile(filename, handlers[ext])
            except:
                status = False
            return status
        raise TypeError("Unknown image file extension %s" % ext)

    def convertEventCoords(self, ev):
        """Convert event coordinates to world coordinates.

        Convert the event coordinates to world coordinates by locating
        the offset of the scrolled window's viewport and adjusting the
        event coordinates.
        """
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        x = ev.GetX() + (xView * xDelta)
        y = ev.GetY() + (yView * yDelta)
        return (x, y)

    def getBoundedCoords(self, x, y):
        """Return image coordinates clipped to boundary of image."""

        if x<0: x=0
        elif x>=self.img.GetWidth(): x=self.img.GetWidth()-1
        if y<0: y=0
        elif y>=self.img.GetHeight(): y=self.img.GetHeight()-1
        return (x, y)

    def getImageCoords(self, x, y, fixbounds = True):
        """Convert scrolled window coordinates to image coordinates.

        Convert from the scrolled window coordinates (where (0,0) is
        the upper left corner when the window is scrolled to the
        top-leftmost position) to the corresponding point on the
        original (i.e. unzoomed, unrotated, uncropped) image.
        """
        x = int(x / self.zoom)
        y = int(y / self.zoom)
        if fixbounds:
            return self.getBoundedCoords(x, y)
        else:
            return (x, y)

    def isInBounds(self, x, y):
        """Check if world coordinates are on the image.

        Return True if the world coordinates lie on the image.
        """
        if self.img is None or x<0 or y<0 or x>=self.width or y>=self.height:
            return False
        return True

    def isEventInClientArea(self, ev):
        """Check if event is in the viewport.

        Return True if the event is within the visible viewport of the
        scrolled window.
        """
        size = self.GetClientSize().Get()
        x = ev.GetX()
        y = ev.GetY()
        if x < 0 or x >= size[0] or y < 0 or y >= size[1]:
            return False
        return True

    def setCursor(self, cursor):
        """Set cursor for the window.

        A mild enhancement of the wx standard SetCursor that takes an
        integer id as well as a wx.Cursor instance.
        """
        if isinstance(cursor, int):
            cursor = wx.Cursor(cursor)
        self.SetCursor(cursor)

    def blankCursor(self, ev, coords=None):
        """Turn off cursor.

        Some selectors, like the crosshair selector, work better when
        the mouse cursor isn't obscuring the image.  This method is
        called by the selector itself to blank the cursor when over
        the image.
        """
        #dprint()
        if coords is None:
            coords = self.convertEventCoords(ev)
        if self.isInBounds(*coords) and self.isEventInClientArea(ev):
            if not self.save_cursor:
                self.save_cursor = True
                self.setCursor(wx.Cursor(wx.CURSOR_BLANK))
        else:
            if self.save_cursor:
                self.setCursor(self.use_selector.cursor)
                self.save_cursor = False

    def getSelectorCoordsOnImage(self, with_cropped_offset=True):
        if self.selector:
            x, y = self.getImageCoords(*self.selector.world_coords)
            if self.crop is not None and with_cropped_offset:
                x += self.crop[0]
                y += self.crop[1]
            return (x, y)
        return None

    #### - Automatic scrolling  FIXME: doesn't work yet

    def autoScroll(self, ev):
        x = ev.GetX()
        y = ev.GetY()
        size = self.GetClientSize().Get()
        if x < 0:
            dx = x
        elif x > size[0]:
            dx = x - size[0]
        else:
            dx = 0
        if y < 0:
            dy = y
        elif y > size[1]:
            dy = y - size[1]
        else:
            dy = 0
        self.autoScrollCallback(dx, dy)

    def autoScrollCallback(self, dx, dy):
        self.dbg_call_seq += 1
        #print("In autoScrollCallback %d: dx=%d dy=%d" % (self.dbg_call_seq, dx, dy))
        spx = self.GetScrollPos(wx.HORIZONTAL)
        spy = self.GetScrollPos(wx.VERTICAL)
        if self.selector:
            self.selector.cleanup()
        wx.CallAfter(self.Scroll, spx+dx, spy+dy)
        self.just_scrolled = True

    def setSelector(self, selector):
        if self.selector:
            self.selector.cleanup()
            self.selector = None
        self.use_selector = selector
        self.setCursor(self.use_selector.cursor)
        self.save_cursor = None

    def startSelector(self, ev=None):
        self.selector = self.use_selector(self, ev)

    def getActiveSelector(self):
        """Returns the currently active selector."""
        return self.selector

    def endActiveSelector(self):
        if self.selector:
            self.selector.cleanup()
            self.selector = None
        if self.save_cursor:
            self.setCursor(self.use_selector.cursor)
            self.save_cursor = None

    def OnMouseEvent(self, ev):
        """Driver to process mouse events.

        This is the main driver to process all mouse events that
        happen on the ImageScroller.  Once a selector is triggered by
        its event combination, it becomes the active selector and
        further mouse events are directed to its handler.
        """
        if self.img:
            inside = self.isEventInClientArea(ev)

            try:
                # First, process the event itself or start it up if it has
                # been triggered.
                if self.selector:
                    if not self.selector.processEvent(ev):
                        self.endActiveSelector()
                elif inside and self.use_selector.trigger(ev):
                    self.startSelector(ev)

                # Next, if we have a selector, process some user interface
                # side effects
                if self.selector:
                    if self.selector.want_autoscroll and not inside:
                        self.autoScroll(ev)
                    if self.selector.want_blank_cursor:
                        self.blankCursor(ev)
            except:
                # If something bad happens, make sure we return control of the
                # mouse pointer to the user
                if self.HasCapture():
                    self.ReleaseMouse()
                raise
        ev.Skip()

    def OnPaint(self, evt):
        self.dbg_call_seq += 1
        #print("In OnPaint %d" % self.dbg_call_seq)
        if self.scaled_bmp is not None:
            dc=wx.BufferedPaintDC(self, self.scaled_bmp, wx.BUFFER_VIRTUAL_AREA)
            # Note that the drawing actually happens when the dc goes
            # out of scope and is destroyed.
            self.OnPaintHook(evt, dc)

            # FIXME: This check for MSW is because it gets multiple onpaint
            # events, so make sure it's only called once for consecutive
            # repaints.  HACK!
            if self.selector and (wx.Platform != '__WXMSW__' or not self.just_scrolled):
                wx.CallAfter(self.selector.recalc_and_draw)
            #self.overlay.Reset()
        self.just_scrolled = False
        evt.Skip()

    def OnPaintHook(self, evt, dc):
        """Hook to draw any additional items onto the saved bitmap.

        Note that any changes made to the dc will be reflected in the
        saved bitmap, so subsequent times calling this function will
        continue to add new data to the image.
        """
        pass


if __name__ == '__main__':
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='ImageScroller Test', size=(500,500))
    frame.CreateStatusBar()

    # Add a panel that the rubberband will work on.
    panel = ImageScroller(frame)
    img = wx.ImageBitmap(wx.ArtProvider_GetBitmap(wx.ART_WARNING, wx.ART_OTHER, wx.Size(48, 48)))
    panel.setImage(img)

    # Add the callbacks
    def crosshairCallback(ev):
        x, y = ev.imageCoords
        frame.SetStatusText("x=%d y=%d" % (x, y))
    panel.Bind(EVT_CROSSHAIR_MOTION, crosshairCallback)

    def rubberbandMotionCallback(ev):
        x0, y0 = ev.upperLeftImageCoords
        x1, y1 = ev.lowerRightImageCoords
        frame.SetStatusText("moving rubberband: ul = (%d,%d) lr = (%d,%d)" % (x0, y0, x1, y1))
    panel.Bind(EVT_RUBBERBAND_MOTION, rubberbandMotionCallback)

    def rubberbandSizeCallback(ev):
        x0, y0 = ev.upperLeftImageCoords
        x1, y1 = ev.lowerRightImageCoords
        frame.SetStatusText("sizing rubberband: ul = (%d,%d) lr = (%d,%d)" % (x0, y0, x1, y1))
    panel.Bind(EVT_RUBBERBAND_SIZE, rubberbandSizeCallback)

    # Layout the frame
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel,  1, wx.EXPAND | wx.ALL, 5)

    def buttonHandler(ev):
        id = ev.GetId()
        if id == 100:
            panel.zoomIn()
        elif id == 101:
            panel.zoomOut()
        elif id == 102:
            panel.setSelector(Crosshair)
        elif id == 103:
            panel.setSelector(RubberBand)
        elif id == 104:
            selector = panel.getActiveSelector()
            dprint("selector = %s" % selector)
            if isinstance(selector, RubberBand):
                box = selector.getSelectedBox()
                dprint("selected box = %s" % str(box))
                panel.setCrop(box)
        elif id == 105:
            panel.setCrop(None)
        elif id == 106:
            panel.setSelector(RubberBand)
            panel.startSelector()
            selector = panel.getActiveSelector()
            img = panel.orig_img
            selector.setSelection(0,0, img.GetWidth()/2, img.GetHeight()/2)
        elif id == 200:
            wildcard="*"
            dlg = wx.FileDialog(
                frame, message="Open File",
                defaultFile="", wildcard=wildcard, style=wx.FD_OPEN)

            # Show the dialog and retrieve the user response. If it is the
            # OK response, process the data.
            if dlg.ShowModal() == wx.ID_OK:
                # This returns a Python list of files that were selected.
                paths = dlg.GetPaths()

                for path in paths:
                    dprint("open file %s:" % path)
                    fh = open(path, 'rb')
                    img = wx.Image()
                    if img.LoadStream(fh):
                        panel.setImage(img)
                    else:
                        dprint("Invalid image: %s" % path)
            # Destroy the dialog. Don't do this until you are done with it!
            # BAD things can happen otherwise!
            dlg.Destroy()
        elif id == 201:
            pass
        elif id == 202:
            panel.copyToClipboard()
    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
    button = wx.Button(frame, 100, 'Zoom In')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 101, 'Zoom Out')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 102, 'Crosshair')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 103, 'Select')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)

    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
    button = wx.Button(frame, 104, 'Crop')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 105, 'Uncrop')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 106, 'Select half')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)

    buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(buttonsizer, 0, wx.EXPAND | wx.ALL, 5)
    button = wx.Button(frame, 200, 'Load')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)
    button = wx.Button(frame, 202, 'Copy to Clipboard')
    frame.Bind(wx.EVT_BUTTON, buttonHandler, button)
    buttonsizer.Add(button, 0, wx.EXPAND, 0)

    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    app.MainLoop()
