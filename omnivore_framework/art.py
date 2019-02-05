import wx

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
