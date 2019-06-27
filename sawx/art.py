import wx

from .filesystem import find_image_path

default_icon_size = 24

import logging
log = logging.getLogger(__name__)


found_bitmaps = {}

def get_bitmap(action_key, icon_size=0):
    try:
        bitmap = find_bitmap(action_key, icon_size)
    except KeyError:
        try:
            bitmap = find_bitmap("question-mark", icon_size)
        except KeyError:
            bitmap = wx.ArtProvider.GetBitmap(wx.ART_QUESTION, wx.ART_TOOLBAR, (icon_size, icon_size))
        bitmap_key = (action_key, icon_size)
        found_bitmaps[bitmap_key] = bitmap
    return bitmap

def find_bitmap(action_key, icon_size=0):
    bitmap_key = (action_key, icon_size)
    if icon_size < 16:
        icon_size = default_icon_size
    try:
        bitmap = found_bitmaps[bitmap_key]
    except KeyError:
        path = None
        action_key_dashes = action_key.replace("_", "-")
        for prefix in [action_key, f"{action_key}-{icon_size}", f"icons8-{action_key}-{icon_size}", f"icons8-{action_key_dashes}-{icon_size}"]:
            print("PREFIX!", prefix)
            try:
                path = find_image_path(prefix + ".png")
            except OSError:
                log.warning(f"No icon found at {prefix} for {action_key}")

        if path is not None:
            bitmap = wx.Bitmap(wx.Image(path))
            print("USING", path)
            found_bitmaps[bitmap_key] = bitmap
        else:
            raise KeyError
    return bitmap
