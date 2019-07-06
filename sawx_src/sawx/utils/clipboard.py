# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Clipboard utilities for wx

On non-X11 systems, there's only one clipboard.  However, on X11 there are
two: the primary selection and the clipboard.  Due to a current wxWidgets
limitation (due to be resolved in 3.0), only one of those clipboards is
available at a time, and stuffing data into one cancels out the other.
    
On non-X11 systems, there's only one real clipboard and there isn't a
system equivalent to the primary selection.  When on a non-X11 platform,
these routines attempt to mimic the primary selection middle mouse paste.
Unfortunately the primary selection will only be application local if we
aren't on an X11 system.
"""

from . import wx


# Global boolean use_x11_primary_selection describes whether or not the
# platform supports true X11 style primary selection.
use_x11_primary_selection = None


def setAllowX11PrimarySelection(default=True):
    global use_x11_primary_selection
    try:
        version = wx.version().split('.')
        version = int(version[0]) * 100 + int(version[1]) * 10 + int(version[2])
        if wx.Platform == "__WXGTK__" and version > 287:
            use_x11_primary_selection = default
        else:
            use_x11_primary_selection = False
    except:
        use_x11_primary_selection = False


# Initialize the value for use_x11_primary_selection
if use_x11_primary_selection is None:
    setAllowX11PrimarySelection()

# Global storage non_x11_primary_selection is only used on a non-x11 platform,
# and simulates the primary selection capability of the X11 platform.
# Assuming the STC handles calls SetClipboardText in response to the end of
# a selection event (i.e.  in response to a left mouse up event), the middle
# mouse usage can be simulated on a non-X11 platform.
non_x11_primary_selection = None


def GetClipboardText(primary_selection=False):
    """Returns the current clipboard value.
    
    On non-X11 systems, there's only one clipboard.  However, on X11 there are
    two: the primary selection and the clipboard.  Due to a current wxWidgets
    limitation, only one of those clipboards is available at a time, and
    stuffing data into one cancels out the other.  The calling method will
    have to check the return value to see if data from the requested clipboard
    type is valid.
    
    @param primary_selection: True for the X11 primary selection, False (the
    default) for the normal clipboard.
    """
    global use_x11_primary_selection
    global non_x11_primary_selection

    success = False
    if primary_selection:
        if use_x11_primary_selection:
            wx.TheClipboard.UsePrimarySelection(primary_selection)
        else:
            #dprint(non_x11_primary_selection)
            return non_x11_primary_selection
    do = wx.TextDataObject()
    if wx.TheClipboard.Open():
        success = wx.TheClipboard.GetData(do)
        wx.TheClipboard.Close()

    if success:
        return do.GetText()
    return None


def SetClipboardText(txt, primary_selection=False):
    """Sets the current clipboard value to the given text.
    
    wxWidgets knows about two types of clipboards: the primary selection and
    the clipboard.  On non-X11 systems, there's only one real clipboard and
    there isn't a system equivalent to the primary selection
    
    This method, however, simulates the primary selection when using a non-X11
    system.  It keeps a separate copy of the text so that a middle mouse paste
    can work, although it is only application local and middle paste to some
    other Windows application won't work.
    
    When using a real X11 system, there is a current wxWidgets limitation: only
    one of those clipboards is available at a time.  Stuffing data into one
    cancels out the other.
    
    @param txt: the text string to store in the clipboard
    
    @param primary_selection: True for the X11 primary selection, False (the
    default) for the normal clipboard.
    """
    global use_x11_primary_selection
    global non_x11_primary_selection

    if primary_selection:
        if use_x11_primary_selection:
            wx.TheClipboard.UsePrimarySelection(primary_selection)
        else:
            non_x11_primary_selection = txt
            #dprint(non_x11_primary_selection)
            return 1
    do = wx.TextDataObject()
    do.SetText(txt)
    if wx.TheClipboard.Open():
        wx.TheClipboard.SetData(do)
        wx.TheClipboard.Close()
        return 1
    else:
        eprint("Can't open clipboard!")
    return 0


__all__ = ['GetClipboardText', 'SetClipboardText']
