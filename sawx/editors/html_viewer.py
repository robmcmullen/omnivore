import os

import wx
import wx.html

from ..editor import SawxEditor
from ..filesystem import fsopen as open

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


class HtmlViewer(SawxEditor):
    editor_id = "html_viewer"

    ui_name = "HTML Viewer"

    toolbar_desc = [
        "open_file", "save_file", None, "copy"
    ]

    @property
    def can_copy(self):
        return bool(self.control.SelectionToText())

    @property
    def can_paste(self):
        return False

    def create_control(self, parent):
        return HtmlWindow(parent)

    def show(self, args=None):
        self.control.SetPage(self.document.raw_data)

    @classmethod
    def can_edit_document_exact(cls, document):
        return document.mime == "text/html" and document.uri != "about://app"


class TitleScreen(HtmlViewer):
    editor_id = "title_screen"

    ui_name = "Title Screen"

    transient = True

    @classmethod
    def can_edit_document_exact(cls, document):
        return document.mime == "text/html" and document.uri == "about://app"
