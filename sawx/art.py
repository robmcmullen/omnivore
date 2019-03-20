import wx

from .filesystem import find_image_path

import logging
log = logging.getLogger(__name__)


global_art_ids = {
    "quit": wx.ART_QUIT,
    "new_file": wx.ART_NEW,
    "open_file": wx.ART_FILE_OPEN,
    "save_file": wx.ART_FILE_SAVE,
    "save_as": wx.ART_FILE_SAVE_AS,
    "copy": wx.ART_COPY,
    "cut": wx.ART_CUT,
    "paste": wx.ART_PASTE,
    "undo": wx.ART_UNDO,
    "redo": wx.ART_REDO,
}


def get_art_id(action_key):
    global global_art_ids

    return global_art_ids.get(action_key, wx.ART_QUESTION)

found_bitmaps = {}

def get_bitmap(action_key, icon_size):
    try:
        bitmap = find_bitmap(action_key, icon_size)
    except KeyError:
        art_id = get_art_id(action_key)
        bitmap = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR, icon_size)
        bitmap_key = (action_key, icon_size)
        found_bitmaps[bitmap_key] = bitmap
    return bitmap

def find_bitmap(action_key, icon_size=0):
    bitmap_key = (action_key, icon_size)
    try:
        bitmap = found_bitmaps[bitmap_key]
    except KeyError:
        try:
            path = find_image_path(action_key + ".png")
        except OSError:
            log.warning(f"No icon found for {action_key}")
            raise KeyError
        else:
            bitmap = wx.Bitmap(wx.Image(path))
            found_bitmaps[bitmap_key] = bitmap
    return bitmap
