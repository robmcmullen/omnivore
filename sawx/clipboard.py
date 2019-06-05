import wx

from .errors import ClipboardError

import logging
log = logging.getLogger(__name__)


# Full list of valid data formats:
#
# >>> import wx
# >>> [x for x in dir(wx) if x.startswith("DF_")]
# ['DF_BITMAP', 'DF_DIB', 'DF_DIF', 'DF_ENHMETAFILE', 'DF_FILENAME', 'DF_HTML',
# 'DF_INVALID', 'DF_LOCALE', 'DF_MAX', 'DF_METAFILE', 'DF_OEMTEXT',
# 'DF_PALETTE', 'DF_PENDATA', 'DF_PRIVATE', 'DF_RIFF', 'DF_SYLK', 'DF_TEXT',
# 'DF_TIFF', 'DF_UNICODETEXT', 'DF_WAVE']

def paste_text_control(editor, data_obj, focused):
    text = data_obj.GetText()
    print(f"found text clipboard object: {text}")
    start, end = focused.GetSelection()
    focused.Replace(start, end, "DEBUG->" + text + "<-DEBUG")

def calc_data_objects_from_control(control):
    if hasattr(control, "GetStringSelection"):
        return calc_data_objects_from_text_control(control)

def calc_data_objects_from_text_control(control):
    data_objs = []
    text = control.GetStringSelection()
    d = wx.TextDataObject()
    d.SetText(text)
    data_objs.append(d)
    return data_objs

def calc_composite_object(data_objs):
    c = wx.DataObjectComposite()
    for d in data_objs:
        c.Add(d)
    return c


def set_clipboard_data(data_objs):
    if not data_objs:
        print(f"no data objects")
    else:
        composite = calc_composite_object(data_objs)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(composite)
            wx.TheClipboard.Close()
            print(f"Set clipboard with {composite} from {data_objs}")
        else:
            raise ClipboardError("System error: unable to open clipboard")


def get_clipboard_data(supported_data_objs):
    if wx.TheClipboard.Open():
        for data_obj in supported_data_objs:
            success = wx.TheClipboard.GetData(data_obj)
            if success:
                break
        wx.TheClipboard.Close()
    else:
        raise ClipboardError("System error: unable to open clipboard")
    return data_obj


def can_paste(supported_data_objs):
    data_formats = [o.GetFormat() for o in supported_data_objs]
    log.debug("Checking clipboard formats %s" % str(data_formats))
    supported = False
    if not wx.TheClipboard.IsOpened():
        try:
            if wx.TheClipboard.Open():
                for f in data_formats:
                    if wx.TheClipboard.IsSupported(f):
                        log.debug("  found clipboard format: %s" % str(f))
                        supported = True
                        break
        finally:
            if wx.TheClipboard.IsOpened():
                wx.TheClipboard.Close()
    return supported

