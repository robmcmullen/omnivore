import os

import wx
import wx.html

from omnivore_framework import OmnivoreEditor
from omnivore_framework.filesystem import fsopen as open

import logging
log = logging.getLogger(__name__)


class HtmlWindow(wx.html.HtmlWindow):
    def __init__(self, parent, prefs=None):
        log.debug("calling HtmlWindow constructor")
        wx.html.HtmlWindow.__init__(self, parent, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        log.debug("setting HtmlWindow fonts")
        if prefs:
            self.SetStandardFonts(prefs.font_size, prefs.normal_face, prefs.fixed_face)

    def OnCellMouseHover(self, cell, x, y):
        # Without access to the task window, search the control hierarchy to
        # find a wx.Frame and set the status text directly
        parent = self.GetParent()
        while parent:
            if hasattr(parent, "SetStatusText"):
                linkinfo = cell.GetLink()
                if linkinfo is not None:
                    parent.SetStatusText(linkinfo.GetHref())
                else:
                    parent.SetStatusText("")
                return
            parent = parent.GetParent()


class HtmlViewer(OmnivoreEditor):
    name = "html_viewer"

    menubar_desc = [
    ["File", "new_file", "open_file", None, "save_file", "save_as", None, "quit"],
    ["Edit", "copy", None, "prefs"],
    ["Help", "about"],
    ]

    toolbar_desc = [
        "new_file", "open_file", "save_file", None, "copy"
    ]

    @property
    def can_copy(self):
        return bool(self.control.SelectionToText())

    def create_control(self, parent):
        return HtmlWindow(parent)

    def load(self, path, mime_info):
        with open(path, 'r') as fh:
            text = fh.read()

        self.control.SetPage(text)
        self.tab_name = os.path.basename(path)

    @classmethod
    def can_edit_mime_exact(cls, mime_type):
        return mime_type == "text/html"


class TitleScreen(HtmlViewer):
    name = "title_screen"

    transient = True

    def create_control(self, parent):
        self.control = HtmlViewer.create_control(self, parent)
        self.load("about://app", None)
        self.tab_name = wx.GetApp().app_name
        return self.control

    @classmethod
    def can_edit_mime_exact(cls, mime_type):
        return False

    @classmethod
    def can_edit_mime_generic(cls, mime_type):
        return False
